from flask import Flask, session, render_template, redirect, url_for, make_response, request, redirect, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from PIL import Image
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from functools import wraps
from typing import Dict, Tuple, Optional, Union
import x
import uuid
import time
from datetime import datetime, timedelta
import random
import redis
import os, io
from config import config  # Import our configuration

from icecream import ic
ic.configureOutput(prefix=f'***** | ', includeContext=True)




app = Flask(__name__)
app.config.from_object(config)
Session(app)

@app.template_filter('strftime')
def strftime_filter(timestamp, format='%A, %d %B %Y'):
    return time.strftime(format, timestamp)

def optimize_image(file):
    try:
        print("Starting image optimization")  # Debug log
        image = Image.open(file)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        
        # Resize if needed
        max_size = (500, 500)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save as WebP
        output = io.BytesIO()
        image.save(output, format='WebP', quality=90, optimize=True)
        output.seek(0)
        print("Image optimization complete")  # Debug log
        return output
    except Exception as e:
        print(f"Error in optimize_image: {str(e)}")  # Debug log
        raise e



##############################
def get_user_avatars(user_pk):
    avatar_dir = config.AVATAR_FOLDER
    # Get all files that contain user_pk in their name
    avatars = []
    for filename in os.listdir(avatar_dir):
        if f"avatar_{user_pk}_" in filename:
            avatars.append({
                'filename': filename,
                'timestamp': int(filename.split('_')[2].split('.')[0]),  # Extract timestamp from filename
                'path': f"/static/avatars/{filename}"
            })
    # Sort by timestamp, newest first
    return sorted(avatars, key=lambda x: x['timestamp'], reverse=True)




##############################
def calculate_basket_totals(basket):
    """
    Calculate total price and quantity for basket items.
    Returns a tuple of (total_price, total_items)
    """
    if not basket:
        return 0.0, 0
    
    total_price = sum(
        item.get("price", 0) * item.get("quantity", 0) 
        for item in basket
    )
    total_items = sum(item.get("quantity", 0) for item in basket)
    
    return total_price, total_items


def delete_user_avatars(user_pk):
    """
    Helper function to delete all avatar files associated with a user.
    
    Args:
        user_pk: The user's primary key/ID
        
    Returns:
        list: Names of successfully deleted files
    """
    avatar_dir = config.AVATAR_FOLDER
    deleted_files = []
    
    # Find all avatar files for this user
    for filename in os.listdir(avatar_dir):
        if f"avatar_{user_pk}_" in filename:
            try:
                file_path = os.path.join(avatar_dir, filename)
                os.remove(file_path)
                deleted_files.append(filename)
            except OSError as e:
                print(f"Error deleting avatar file {filename}: {e}")
                
    return deleted_files


##############################
def rate_limit_decorator(min_delay: float = 1.0):
    """
    Decorator to ensure minimum delay between API calls to respect rate limits.
    
    Args:
        min_delay (float): Minimum delay in seconds between calls
    """
    last_call = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            if func.__name__ in last_call:
                elapsed = current_time - last_call[func.__name__]
                if elapsed < min_delay:
                    time.sleep(min_delay - elapsed)
            
            result = func(*args, **kwargs)
            last_call[func.__name__] = time.time()
            return result
        return wrapper
    return decorator

class GeocodingHelper:
    def __init__(self, user_agent: str = "my_food_delivery_app"):
        """
        Initialize the geocoding helper with Nominatim geocoder.
        
        Args:
            user_agent (str): User agent string for Nominatim service
        """
        self.geolocator = Nominatim(user_agent=user_agent)
        
    @rate_limit_decorator(min_delay=1.0)
    def get_coordinates(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert an address to coordinates (latitude, longitude).
        Used during restaurant signup to store location data.
        
        Args:
            address (str): Full address string
            
        Returns:
            Optional[Tuple[float, float]]: Tuple of (latitude, longitude) or None if not found
        """
        try:
            location = self.geolocator.geocode(address)
            if location:
                return (location.latitude, location.longitude)
            return None
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            print(f"Geocoding error: {str(e)}")
            return None

    def format_coordinates(self, lat: float, lon: float) -> str:
        """
        Format coordinates as string in required format.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            
        Returns:
            str: Formatted coordinates string
        """
        return f"[{lat}, {lon}]"


##############################
##############################
##############################

def _________GET_________(): pass

##############################
##############################

##############################
@app.get("/")
def view_index():
    try:
        # Get pagination parameters
        page = request.args.get("page", default=1, type=int)
        per_page = 10  # Show 12 restaurants per page
        offset = (page - 1) * per_page

        db, cursor = x.db()
        
        # Query for ALL coordinates (for map)
        cursor.execute("""
            SELECT coords.coordinates, coords.restaurant_fk 
            FROM coords 
            JOIN users ON coords.restaurant_fk = users.user_pk
            WHERE users.user_deleted_at = 0
        """)
        all_coords = cursor.fetchall()
        
        # Query for paginated restaurant list
        cursor.execute("""
            SELECT coords.*, users.user_name, users.user_avatar,
                   coords.street, coords.house_number, coords.postcode, coords.city
            FROM coords 
            JOIN users ON coords.restaurant_fk = users.user_pk
            WHERE users.user_deleted_at = 0
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        paginated_restaurants = cursor.fetchall()

        # Get total count for pagination
        cursor.execute("""
            SELECT COUNT(*) AS total 
            FROM coords 
            JOIN users ON coords.restaurant_fk = users.user_pk
            WHERE users.user_deleted_at = 0
        """)
        total = cursor.fetchone()["total"]

        next_page = page + 1 if offset + per_page < total else None
        prev_page = page - 1 if page > 1 else None

        return render_template(
            "view_index.html",
            coords=paginated_restaurants,  # For restaurant list
            all_coords=all_coords,  # For map
            next_page=next_page,
            prev_page=prev_page,
            user=session.get("user"),
            basket=session.get("basket", []),
            total_price=calculate_basket_totals(session.get("basket", []))[0],
            page_title="Your Favorite Restaurants in One Place"
        )

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException): 
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code    
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            return "<template>System upgrading</template>", 500        
        return "<template>System under maintenance</template>", 500  
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


@app.get("/coordinates")
def get_coordinates():
    try:
        db, cursor = x.db()
        cursor.execute("""
            SELECT 
                coords.coordinates, 
                coords.restaurant_fk,
                users.user_name,
                CONCAT(coords.street, ' ', coords.house_number, ', ', 
                       coords.postcode, ' ', coords.city) as address
            FROM coords 
            JOIN users ON coords.restaurant_fk = users.user_pk
            WHERE users.user_deleted_at = 0
        """)
        coordinates = cursor.fetchall()
        
        # Convert coordinates to a serializable format
        serializable_coords = []
        for coord in coordinates:
            serializable_coords.append({
                'coordinates': coord['coordinates'],
                'restaurant_fk': coord['restaurant_fk'],
                'user_name': coord['user_name'],
                'address': coord['address']
            })
        
        return jsonify(serializable_coords)
        
    except Exception as ex:
        return jsonify({"error": "Failed to fetch coordinates"}), 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/search")
def search_results():
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return redirect(url_for("view_index"))
            
        search_term = f"%{query}%"
        db, cursor = x.db()
        
        # Modified restaurant query to include address information
        restaurant_query = """
            SELECT DISTINCT
                u.user_pk,
                u.user_name,
                u.user_avatar,
                c.coordinates,
                c.street,
                c.house_number,
                c.postcode,
                c.city
            FROM 
                users u
            JOIN 
                users_roles ur ON u.user_pk = ur.user_role_user_fk
            JOIN 
                roles r ON ur.user_role_role_fk = r.role_pk
            LEFT JOIN
                coords c ON u.user_pk = c.restaurant_fk
            WHERE 
                r.role_name = 'restaurant'
                AND u.user_deleted_at = 0
                AND u.user_name LIKE %s
        """
        cursor.execute(restaurant_query, (search_term,))
        restaurants = cursor.fetchall()
        
        items_query = """
            SELECT 
                i.item_pk,
                i.item_title,
                i.item_price,
                i.restaurant_fk,
                u.user_name as restaurant_name
            FROM 
                items i
            JOIN 
                users u ON i.restaurant_fk = u.user_pk
            WHERE 
                i.item_deleted_at = 0 
                AND i.item_blocked_at = 0
                AND i.item_title LIKE %s
        """
        cursor.execute(items_query, (search_term,))
        items = cursor.fetchall()

        # Fetch images for items...
        item_images = {}
        if items:
            item_pks = [item['item_pk'] for item in items]
            format_strings = ','.join(['%s'] * len(item_pks))
            query_images = f"""SELECT item_fk, image 
                           FROM items_image 
                           WHERE item_fk IN ({format_strings})"""
            cursor.execute(query_images, tuple(item_pks))
            images = cursor.fetchall()

            for img in images:
                if img['item_fk'] not in item_images:
                    item_images[img['item_fk']] = img['image']
        
        return render_template(
            "search_results.html",
            query=query,
            restaurants=restaurants,
            items=items,
            item_images=item_images,
            user=session.get("user"),
            basket=session.get("basket", []),
            total_price=calculate_basket_totals(session.get("basket", []))[0],
            page_title=f"""{query} - Wolt Search"""
        )
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
        return "<template>System under maintenance</template>", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/signup")
@x.no_cache
def view_signup():  
    if session.get("user"):     
        return redirect(url_for("show_profile"))
    
    try:
        db, cursor = x.db()
        # Query roles from the roles table
        query_roles = "SELECT role_pk, role_name FROM roles WHERE role_name != 'admin'"
        cursor.execute(query_roles)
        roles = cursor.fetchall()


        # Render the signup page with roles
        return render_template("view_signup.html", x=x, title="Signup", roles=roles, page_title="Sign up for Wolt")
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        toast = render_template("___toast.html", message="Error loading roles.")
        return f"""<template mix-target="#toast">{toast}</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.get("/login")
@x.no_cache
def view_login():  
    if session.get("user"):
        return redirect(url_for("show_profile"))
    
    messages = {
        "verify_email": "Account created! Please check your email to verify your account.",
        "verified": "Email verified successfully! Please log in.",
        "new_password": "You have successfully created a new password. Please login."
    }
    
    email = request.args.get("email")
    msg = request.args.get("msg")
    display_message = messages.get(msg, "")
    
    return render_template(
        "view_login.html", 
        x=x, 
        title="Login", 
        message=display_message,
        email=email,
        msg=msg,
        page_title="Log in to Wolt"
    )



@app.post("/resend-code")
def resend_verification_code():
    try:
        verification = session.get('verification')
        if not verification:
            return redirect(url_for("view_signup"))
            
        # Generate new code and update expiry
        new_code = ''.join([str(random.randint(0, 9)) for _ in range(config.VERIFICATION_CODE_LENGTH)])
        new_expiry = (datetime.now() + timedelta(minutes=config.VERIFICATION_CODE_EXPIRY)).timestamp()
        
        # Update session
        verification['code'] = new_code
        verification['expiry'] = new_expiry
        session['verification'] = verification
        
        # Send new email
        email_body = f"""
        <h1>New Verification Code</h1>
        <p>Your new verification code is: <strong>{new_code}</strong></p>
        <p>This code will expire in {config.VERIFICATION_CODE_EXPIRY} minutes.</p>
        """
        x.send_email(verification['email'], "New Verification Code", email_body)
        
        return """
            <template mix-target="#verification-message" mix-replace>
                <p class="text-c-green:-14 mt-4">A new verification code has been sent to your email.</p>
            </template>
        """
        
    except Exception as ex:
        ic(ex)
        return """
            <template mix-target="#verification-error">
                <p class="text-c-red:-14 mt-4">Failed to resend verification code. Please try again.</p>
            </template>
        """, 500
    

@app.get("/passwordrecovery")
@x.no_cache
def view_forgot_password():
    if session.get("user"):
        return redirect(url_for("show_profile"))
    return render_template(
        "view_forgot_password.html",
        x=x,
        page_title="Password Recovery"
    )

@app.get("/createpassword")
@x.no_cache
def view_create_password():
    try:
        if session.get("user"):
            return redirect(url_for("show_profile"))
        
        userId = request.args.get("id")
        session["userId"] = userId

        db, cursor = x.db()
        cursor.execute("""
                SELECT user_pk
                FROM 
                    users 
                WHERE 
                    user_pk = %s
            """, (userId,))
        validUser = cursor.fetchone()

        if not validUser:
            return redirect(url_for("view_signup"))

        return render_template(
            "view_create_password.html",
            x=x,
            page_title="Create new password"
        )
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals():
            db.close()



##############################
@app.get("/admin")
@x.no_cache
def view_admin():
    # Check if user is logged in and admin
    user = session.get("user")
    if not user:
        return redirect(url_for("view_login"))
    
    # Then check if user has admin role
    if "admin" not in user.get("roles", []):
        return redirect(url_for("view_login"))
    
    basket = session.get("basket", [])
    total_price, _ = calculate_basket_totals(basket)
    
    
    
    try:
        # Get all users from database
        db, cursor = x.db()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        cursor.execute("""
            SELECT 
                items.*,
                users.user_name as restaurant_name
            FROM 
                items 
            LEFT JOIN 
                users 
            ON 
                items.restaurant_fk = users.user_pk
        """)
        items = cursor.fetchall()
        
        return render_template("view_admin.html", users=users, time=time, user=user, items=items, basket=basket, total_price=total_price, page_title="Admin Dashboard")
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'db' in locals(): db.close()



##############################
@app.get("/profile")
@x.no_cache
def show_profile():
    user = session.get("user")
    if not user:
        return redirect(url_for("view_login"))
        
    avatars = get_user_avatars(session['user']['user_pk'])
    basket = session.get("basket", [])
    total_price, _ = calculate_basket_totals(basket)
    
    coords = None
    if "restaurant" in user["roles"]:
        db, cursor = x.db()
        try:
            cursor.execute("""
                SELECT street, house_number, postcode, city 
                FROM coords 
                WHERE restaurant_fk = %s
            """, (user["user_pk"],))
            coords = cursor.fetchone()
        finally:
            cursor.close()
            db.close()

    return render_template(
        "view_profile.html",
        x=x,
        user=user,
        avatars=avatars,
        coords=coords,
        time=time,
        total_price=total_price,
        basket=basket,
        page_title="Profile"
    )
##############################

@app.get("/checkout")
def view_checkout():
    try:
        
        if not session.get("user"):
            return redirect(url_for("view_login"))
            
        basket = session.get("basket", [])
        ic("Basket after get:", basket)
        
        if not basket:
            return redirect(url_for("view_index"))
        
        # Get totals using helper function
        total_price, total_items = calculate_basket_totals(basket)
        ic("Calculated totals:", total_price, total_items)
        
        # Pass data to template
        return render_template(
            "view_checkout.html",
            basket=basket,
            total_price=total_price,
            user=session.get("user"),
            page_title="Checkout"
        )
                             
    except Exception as ex:
        # Print the full error details
        ic("Checkout error details:")
        ic(type(ex))  # Show the type of exception
        ic(str(ex))   # Show the error message
        ic(ex)        # Show the full exception
        
        toast = render_template("___toast.html", message=f"Error accessing checkout: {str(ex)}")
        return f"""<template mix-target="#toast">{toast}</template>""", 500

##############################
@app.get("/order-confirmation")
def view_order_confirmation():
    if not session.get("user"):
        return redirect(url_for("view_login"))
    
    if not session.get("last_order"):
        return redirect(url_for("view_index"))
        
    return render_template("view_order_confirmation.html", order=session.get("last_order"), user=session.get("user"), page_title="Order Confirmation")



##############################
@app.put("/users/delete/<user_pk>")
def user_delete(user_pk):
    try:
        if not "admin" in session.get("user", {}).get("roles", []): 
            return redirect(url_for("view_login"))

        user = {
            "user_pk": x.validate_uuid4(user_pk),
            "user_deleted_at": int(time.time())
        }

        db, cursor = x.db()
        cursor.execute("""SELECT * FROM users WHERE user_pk = %s""", (user["user_pk"],))
        user_data = cursor.fetchone()
        user_email = user_data["user_email"]
        user_name = user_data["user_name"]
        
        # Delete all avatar files before updating the database
        deleted_avatars = delete_user_avatars(user["user_pk"])
        
        # Update user record and clear avatar field
        cursor.execute("""UPDATE users 
                      SET user_deleted_at = %s,
                          user_avatar = ''
                      WHERE user_pk = %s""", 
                      (user["user_deleted_at"], user["user_pk"]))

        if cursor.rowcount == 0:
            x.raise_custom_exception("User could not be deleted", 404)

        db.commit()

        formatted_date = time.strftime('%A, %d %B %Y', time.localtime(user["user_deleted_at"]))
        deleted_html = f'<div class="d-flex a-items-center text-c-red:-14">Deleted: {formatted_date}</div>'

        toast = render_template("___toast.html", message="User deleted")

        email_body = f"""<h1>Account deleted</h1>
          <p>Hi {user_name}, your account has been deleted. We are sad to see you go.</p>"""
        x.send_email(user_email, "Your account has been deleted", email_body)

        return f"""
            <template mix-target='#actions-{user_pk}'>
                {deleted_html}
            </template>
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, ex.code
        
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            toast = render_template("___toast.html", message="Database error")
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, 500
        
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """, 500

##############################
@app.put("/items/delete/<item_pk>")
def item_delete(item_pk):
    try:
        if not "admin" in session.get("user", {}).get("roles", []): 
            return redirect(url_for("view_login"))

        item = {
            "item_pk": x.validate_uuid4(item_pk),
            "item_deleted_at": int(time.time())
        }

        db, cursor = x.db()

        cursor.execute("""SELECT 
                            items.*, 
                            users.user_name,
                            users.user_email  
                        FROM 
                            items 
                        LEFT JOIN 
                            users ON items.restaurant_fk = users.user_pk
                        WHERE 
                            items.item_pk = %s""", (item["item_pk"],))
        user_data = cursor.fetchone()
        user_email = user_data["user_email"]
        user_name = user_data["user_name"]
    

        cursor.execute("""UPDATE items 
                      SET item_deleted_at = %s 
                      WHERE item_pk = %s""", 
                      (item["item_deleted_at"], item["item_pk"]))
        
        if cursor.rowcount == 0:
            x.raise_custom_exception("Item could not be deleted", 404)
        
        db.commit()
        
        # Format the deleted_at date and create the replacement HTML
        formatted_date = time.strftime('%A, %d %B %Y', time.localtime(item["item_deleted_at"]))
        deleted_html = f'<div class="d-flex a-items-center text-c-red:-14">Deleted: {formatted_date}</div>'
        
        toast = render_template("___toast.html", message="Item deleted")
        
        email_body = f"""<h1>Item deleted</h1>
          <p>Hi {user_name}, your '{user_data["item_title"]}' menu item has been deleted. Please contact support if you have any questions.</p>"""
        x.send_email(user_email, "Your item has been deleted", email_body)
        # Return both the deleted_at text and toast
        return f"""
            <template mix-target='#actions-{item_pk}'>
                {deleted_html}
            </template>
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, ex.code
        
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            toast = render_template("___toast.html", message="Database error")
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, 500
        
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/users/avatars/<user_pk>")
def get_user_avatar_history(user_pk):
    try:
        if not session.get("user"): x.raise_custom_exception("please login", 401)
        avatars = get_user_avatars(user_pk)
        return render_template("user_avatars.html", avatars=avatars, user_pk=user_pk)
    except Exception as ex:
        ic(ex)
        return "<template>System under maintenance</template>", 500



##############################
@app.get("/users/show-delete-modal/<user_pk>")
def show_delete_modal(user_pk):
    try:
        if not session.get("user"):
            return redirect(url_for("view_login"))

        modal_html = render_template("___delete_modal.html", user_pk=user_pk, x=x)
        return f"""
            <template mix-target="body" mix-top>
                {modal_html}
            </template>
        """

    except Exception as ex:
        ic(ex)
        toast = render_template("___toast.html", message=str(ex))
        return f"""
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
        """
    
##############################
@app.get("/users/show-confirm-modal/<user_pk>")
def show_confirm_modal(user_pk):
    try:
        if not session.get("user"):
            return redirect(url_for("view_login"))

        modal_html = render_template("___confirm_modal.html", user_pk=user_pk)
        return f"""
            <template mix-target="body" mix-top>
                {modal_html}
            </template>
        """

    except Exception as ex:
        ic(ex)
        toast = render_template("___toast.html", message=str(ex))
        return f"""
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
        """

##############################

@app.get("/users/show-change-password-modal/<user_pk>")
def show_change_password_modal(user_pk):
    try:
        user = session.get("user")
        if not user:
            return redirect(url_for("view_login"))

        modal_html = render_template("___change_password_modal.html", user=user, x=x)
        return f"""
            <template mix-target="body" mix-top>
                {modal_html}
            </template>
        """
    except Exception as ex:
        ic(ex)
        toast = render_template("___toast.html", message=str(ex))
        return f"""
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
        """

##############################
##############################
##############################

def _________POST_________(): pass

##############################
##############################
##############################

@app.post("/logout")
def logout():
    # ic("#"*30)
    # ic(session)
    session.pop("user", None)
    session.pop("basket", None)  # This clears the basket
    # session.clear()
    # session.modified = True
    # ic("*"*30)
    # ic(session)
    return redirect(url_for("view_index"))


##############################
@app.post("/users")
@x.no_cache
def signup():
    try:
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()
        user_password = x.validate_user_password()
        hashed_password = generate_password_hash(user_password)
        
        user_role_pk = request.form.get("role")
        db, cursor = x.db()

        # First validate the role selection
        cursor.execute("""
            SELECT role_name FROM roles WHERE role_pk = %s
        """, (user_role_pk,))
        selected_role = cursor.fetchone()
        
        if not selected_role:
            raise x.CustomException("Invalid role selected", 400)
        
        if selected_role["role_name"].lower() == "admin":
            raise x.CustomException("Unauthorized role selection", 400)

        # Check for existing email and get user_pk if exists
        cursor.execute("SELECT user_pk, user_deleted_at FROM users WHERE user_email = %s", (user_email,))
        existing_user = cursor.fetchone()
        
        # If user exists and is not deleted, return error
        if existing_user and existing_user["user_deleted_at"] == 0:
            toast = render_template("___toast.html", message="Email not available")
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400

        # Generate verification code
        verification_code = ''.join([str(random.randint(0, 9)) for _ in range(config.VERIFICATION_CODE_LENGTH)])
        verification_expiry = (datetime.now() + timedelta(minutes=config.VERIFICATION_CODE_EXPIRY)).timestamp()
        
        current_time = int(time.time())
        
        if existing_user:
            # Update existing user
            user_pk = existing_user["user_pk"]
            cursor.execute("""
                UPDATE users 
                SET user_deleted_at = 0,
                    user_verified_at = 0,
                    user_name = %s,
                    user_last_name = %s,
                    user_password = %s,
                    user_updated_at = %s
                WHERE user_pk = %s
            """, (user_name, user_last_name, hashed_password, 
                 current_time, user_pk))
                 
            # Update the role
            cursor.execute("""
                UPDATE users_roles 
                SET user_role_role_fk = %s 
                WHERE user_role_user_fk = %s
            """, (user_role_pk, user_pk))
        else:
            # Create new user
            user_pk = str(uuid.uuid4())
            cursor.execute(
                'INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (user_pk, user_name, user_last_name, user_email, hashed_password, 
                 "", current_time, 0, 0, 0, 0)
            )
            
            # Add user role
            cursor.execute("""
                INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
                VALUES (%s, %s)
            """, (user_pk, user_role_pk))

        # Handle restaurant address if role is restaurant
        if selected_role["role_name"].lower() == "restaurant":
            street = request.form.get("street")
            house_number = request.form.get("house_number")
            postcode = request.form.get("postcode")
            city = request.form.get("city")
            
            if not all([street, house_number, postcode, city]):
                toast = render_template("___toast.html", message="All address fields are required for restaurants")
                return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400

            # Get coordinates using geocoding
            full_address = f"{street} {house_number}, {postcode} {city}"
            geocoder = GeocodingHelper()
            coords = geocoder.get_coordinates(full_address)
            
            if not coords:
                toast = render_template("___toast.html", message="Could not validate address")
                return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400
                
            formatted_coords = geocoder.format_coordinates(*coords)

            # Update or insert coordinates
            cursor.execute("""
                SELECT coords_pk FROM coords WHERE restaurant_fk = %s
            """, (user_pk,))
            existing_coords = cursor.fetchone()
            
            if existing_coords:
                cursor.execute("""
                    UPDATE coords 
                    SET coordinates = %s, street = %s, house_number = %s,
                        postcode = %s, city = %s
                    WHERE restaurant_fk = %s
                """, (formatted_coords, street, house_number, 
                      postcode, city, user_pk))
            else:
                coords_pk = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO coords (coords_pk, coordinates, restaurant_fk,
                                      street, house_number, postcode, city)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (coords_pk, formatted_coords, user_pk, street,
                      house_number, postcode, city))

        # Store verification code and expiry in session
        session['verification'] = {
            'code': verification_code,
            'expiry': verification_expiry,
            'user_pk': user_pk,
            'email': user_email
        }

        # Send verification email
        email_body = f"""
        <h1>Verify your email</h1>
        <p>Hi {user_name},</p>
        <p>Your verification code is: <strong>{verification_code}</strong></p>
        <p>This code will expire in {config.VERIFICATION_CODE_EXPIRY} minutes.</p>
        """
        x.send_email(user_email, "Please verify your account", email_body)
        
        db.commit()
        return f"""<template mix-redirect="/verify-code"></template>""", 201
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException): 
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code    
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            return f"""<template mix-target="#toast" mix-bottom>System upgrading</template>""", 500        
        return f"""<template mix-target="#toast" mix-bottom>System under maintenance</template>""", 500    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


@app.route("/verify-code", methods=['GET', 'POST'])
@x.no_cache
def verify_code():
    if not session.get('verification'):
        return redirect(url_for("view_signup"))
        
    if request.method == 'POST':
        try:
            verification = session.get('verification')
            submitted_code = request.form.get('verification_code')
            
            # Check if code has expired
            if datetime.now().timestamp() > verification['expiry']:
                session.pop('verification', None)
                return """
                    <template mix-target="#verification-error">
                        <p class="text-c-red:-14">Verification code has expired. Please sign up again.</p>
                    </template>
                """, 400
                
            # Check if code matches
            if submitted_code != verification['code']:
                return """
                    <template mix-target="#verification-error" mix-replace>
                        <p class="text-c-red:-14">Invalid verification code. Please try again.</p>
                    </template>
                """, 400
                
            # Update user verification status
            db, cursor = x.db()
            cursor.execute("""
                UPDATE users 
                SET user_verified_at = %s 
                WHERE user_pk = %s
            """, (int(time.time()), verification['user_pk']))
            db.commit()
            
            # Clear verification from session
            session.pop('verification', None)
            
            # Redirect to login
            return """<template mix-redirect="/login?msg=verified"></template>"""
            
        except Exception as ex:
            ic(ex)
            if "db" in locals(): db.rollback()
            return """
                <template mix-target="#verification-error">
                    <p class="text-c-red:-14">An error occurred. Please try again.</p>
                </template>
            """, 500
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
            
    # GET request - show verification page
    return render_template(
        "verify_code.html",
        email=session['verification']['email'],
        page_title="Verify Your Email"
    )

##############################
@app.post("/login")
def login():
    try:

        user_email = x.validate_user_email()
        user_password = x.validate_user_password()

        db, cursor = x.db()
        q = """ SELECT * FROM users 
                JOIN users_roles 
                ON user_pk = user_role_user_fk 
                JOIN roles
                ON role_pk = user_role_role_fk
                WHERE user_email = %s 
                AND user_deleted_at = 0"""
        cursor.execute(q, (user_email,))
        rows = cursor.fetchall()
        if not rows:
            return f"""<template mix-target="#login-error">User not registered</template>""", 400  
    
        # if rows[0]["user_deleted_at"] != 0:
        #     toast = render_template("___toast.html", message="This user does not exist")
        #     return f"""<template mix-target="#toast">{toast}</template>""", 401
        if not check_password_hash(rows[0]["user_password"], user_password):
            return f"""<template mix-target="#login-error">Invalid credentials</template>""", 400  
        

        # Check if user is verified
        if rows[0]["user_verified_at"] == 0:
            # Store verification info in session
            verification_code = ''.join([str(random.randint(0, 9)) for _ in range(config.VERIFICATION_CODE_LENGTH)])
            verification_expiry = (datetime.now() + timedelta(minutes=config.VERIFICATION_CODE_EXPIRY)).timestamp()
            
            session['verification'] = {
                'code': verification_code,
                'expiry': verification_expiry,
                'user_pk': rows[0]["user_pk"],
                'email': user_email
            }

            # Send verification email
            email_body = f"""
            <h1>Verify your email</h1>
            <p>Hi {rows[0]["user_name"]},</p>
            <p>Your verification code is: <strong>{verification_code}</strong></p>
            <p>This code will expire in {config.VERIFICATION_CODE_EXPIRY} minutes.</p>
            """
            x.send_email(user_email, "Please verify your account", email_body)
    
            return f"""<template mix-target="#login-error" mix-replace>
                <div>
                    <p>Please verify your email before logging in.</p>
                    <a href="/verify-code" class="text-c-tealblue:-5" hover="text-c-tealblue:-8">Verify your email</a>
                </div>
            </template>""", 401


        roles = []
        for row in rows:
            roles.append(row["role_name"])

        user = {
            "user_pk": rows[0]["user_pk"],
            "user_name": rows[0]["user_name"],
            "user_last_name": rows[0]["user_last_name"],
            "user_email": rows[0]["user_email"],
            "roles": roles,
            "user_verified_at": rows[0]["user_verified_at"],
            "user_avatar": rows[0]["user_avatar"]
        }
        ic(user)
        session["user"] = user
        return """<template mix-redirect="/"></template>"""
    except Exception as ex:
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException): 
            return f"""<template mix-target="login-error">{ex.message}</template>""", ex.code    
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            return "<template>System upgrating</template>", 500        
        return "<template>System under maintenance</template>", 500  
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/passwordrecovery")
def passwordrecovery():
    try:
        user_email = x.validate_user_email()

        db, cursor = x.db()

        q = """ SELECT * FROM users 
                WHERE user_email = %s 
                AND user_deleted_at = 0"""
        cursor.execute(q, (user_email,))
        user_data = cursor.fetchone()
        if not user_data:
            return """<template mix-target="#new_password_status">
                        <p class="text-c-red:-14 mt-2">There are no users signed up with this email</p>
                    </template>""", 400     


        email_body = f"""<h1>New password requested</h1>
              <p>Hi {user_data['user_name']}, you have requested a new password. Please click on the link below to create a new password.</p>
              <a href="{config.DOMAIN}/createpassword?id={user_data['user_pk']}">Create new password</a>
              <p>The Wolt Demo Team</p>
              """
        x.send_email(user_data["user_email"], "New password requested", email_body)

        return """
                <template mix-target="#new_password_status" mix-replace>
                    <p class="text-c-green:-14 mt-1 text-w-semibold">Check your email to create a new password</p>
                </template>
            """  
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException): 
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code    
        if isinstance(ex, x.mysql.connector.Error):
            toast = render_template("___toast.html", message=ex)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500      
        toast = render_template("___toast.html", message=ex)
        return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500  
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

############################
@app.put("/createpassword")
def create_password():
    try:
        # user_pk = request.args.get('id')
        # if not user_pk:
        #     x.raise_custom_exception("Invalid request", 400)
        user_pk = session.get("userId")
        password = request.form.get('user_password')
        confirm_password = request.form.get('user_confirm_password')
        
        
        if not password or not confirm_password:
            return """
                <template mix-target="#password_status" mix-replace>
                    <p id="password_status" class="text-c-red:-14 mt-2">Both password fields are required</p>
                </template>
            """
            
        if password != confirm_password:
            return """
                <template mix-target="#password_status" mix-replace>
                    <p id="password_status" class="text-c-red:-14 mt-2">Passwords do not match</p>
                </template>
            """
            
        hashed_password = generate_password_hash(password)
        
        db, cursor = x.db()
        cursor.execute("""
                UPDATE users 
                SET user_password = %s,
                    user_updated_at = %s 
                WHERE user_pk = %s
                AND user_deleted_at = 0
            """, (hashed_password, int(time.time()), user_pk))
            
        if cursor.rowcount != 1:
                x.raise_custom_exception("User not found", 404)
                
        db.commit()
            
        return """
                <template mix-redirect="/login?msg=new_password"></template>
            """
            
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            return f"""
                <template mix-target="#password_status" mix-replace>
                    <p id="password_status" class="text-c-red:-14 mt-2">{ex.message}</p>
                </template>
            """, ex.code
            
        return """
            <template mix-target="#password_status">
                <p id="password_status" class="text-c-red:-14 mt-2">An error occurred. Please try again.</p>
            </template>
        """, 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

############################

@app.put("/users/update-role/<user_pk>")
@x.no_cache
def update_role(user_pk):
    user = session.get("user")
    if not user:
        return redirect(url_for("view_login"))
    try:
        db, cursor = x.db()

        # First check if the user exists and is not deleted
        cursor.execute("SELECT user_pk FROM users WHERE user_pk = %s AND user_deleted_at = 0", (user_pk,))
        existing_user = cursor.fetchone()
        
        if not existing_user:
            raise x.CustomException("User not found", 404)

        # Get the partner role_pk
        cursor.execute("""
            SELECT role_pk FROM roles WHERE role_name = 'partner'
        """)
        partner_role = cursor.fetchone()
        
        if not partner_role:
            raise x.CustomException("Partner role not found", 400)
        
        # Update the user's role in users_roles table
        cursor.execute("""
            UPDATE users_roles 
            SET user_role_role_fk = %s
            WHERE user_role_user_fk = %s
        """, (partner_role["role_pk"], user_pk))
            
        if cursor.rowcount != 1:
            raise x.CustomException("Error updating user role", 400)
                
        db.commit()

        user["roles"][0] = 'partner'
        session["user"] = user
            
        return f"""<template mix-redirect="/profile"></template>"""
            
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
            
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            return f"""<template mix-target="#toast" mix-bottom>System upgrading</template>""", 500
            
        return f"""<template mix-target="#toast" mix-bottom>System under maintenance</template>""", 500
    
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/users/confirm-delete/<user_pk>")
def confirm_delete(user_pk):
    try:
        # Authentication checks
        if not session.get("user"):
            return redirect(url_for("view_login"))
        
        is_admin = "admin" in session.get("user", {}).get("roles", [])
        current_user_pk = session["user"]["user_pk"]
        
        if not is_admin and current_user_pk != user_pk:
            x.raise_custom_exception("Unauthorized access", 403)

        password = request.form.get('password')
       
        db, cursor = x.db()
        
        # Database operations
        cursor.execute("""SELECT * FROM users WHERE user_pk = %s""", (user_pk,))
        user_data = cursor.fetchone()
        
        if not user_data:
            x.raise_custom_exception("User not found", 404)

        # Password verification
        if not check_password_hash(user_data["user_password"], password):
            return """
                <template mix-target="#delete-modal-error">
                    <div class="text-c-red:-14 mt-2">Invalid password</div>
                </template>
            """

        # Delete avatar files and update user record
        deleted_avatars = delete_user_avatars(user_pk)
        deleted_at = int(time.time())
        
        cursor.execute("""UPDATE users 
                      SET user_deleted_at = %s,
                          user_avatar = ''
                      WHERE user_pk = %s""", 
                      (deleted_at, user_pk))
        
        if cursor.rowcount == 0:
            x.raise_custom_exception("User could not be deleted", 404)
        
        db.commit()

        # Send email and handle response
        email_body = f"""<h1>Account deleted</h1>
          <p>Hi {user_data['user_name']}, your account has been deleted. We are sad to see you go.</p>"""
        x.send_email(user_data["user_email"], "Your account has been deleted", email_body)

        # Return appropriate response based on user type
        toast_message = "Your account has been deleted" if current_user_pk == user_pk else "User deleted"
        toast = render_template("___toast.html", message=toast_message)
        
        if current_user_pk == user_pk:
            session.clear()
            return f"""
                <template mix-target="#delete-modal" mix-replace></template>
                <template mix-redirect="/login"></template>
            """

        formatted_date = time.strftime('%A, %d %B %Y', time.localtime(deleted_at))
        deleted_html = f'<div class="d-flex a-items-center text-c-red:-14">Deleted: {formatted_date}</div>'
        
        return f"""
            <template mix-target="#delete-modal"></template>
            <template mix-target='#actions-{user_pk}'>
                {deleted_html}
            </template>
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
        """

    except Exception as ex:
        if "db" in locals(): 
            db.rollback()
        
        # Error handling based on exception type
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
        
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            toast = render_template("___toast.html", message="Database error")
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500
        
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 500
        
    finally:
        if "cursor" in locals(): 
            cursor.close()
        if "db" in locals(): 
            db.close()

##############################
@app.post("/items")
def create_item():
    try:
        # TODO: validate item_title, item_description, item_price
        file, item_image_name = x.validate_item_image()

        # Save the image
        file.save(os.path.join(x.UPLOAD_ITEM_FOLDER, item_image_name))
        # TODO: if saving the image went wrong, then rollback by going to the exception
        # TODO: Success, commit
        return item_image_name
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException): 
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code    
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            return "<template>System upgrating</template>", 500        
        return "<template>System under maintenance</template>", 500  
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()    


#############################################
# Update the add_to_basket function to maintain consistent data structure
@app.post("/add-to-basket/<item_pk>")
def add_to_basket(item_pk):
    try:
        if not session.get("user"):
            return """<template mix-redirect="/login"></template>"""

            
        # Get quantity from the form (menu item form)
        quantity = int(request.form.get("quantity", 1))
        if quantity < 1:
            raise x.CustomException("Invalid quantity", 400)
            
        # Initialize basket if needed
        if "basket" not in session:
            session["basket"] = []
        
        # Get item details from database
        db, cursor = x.db()
        cursor.execute("""
            SELECT item_pk, item_title, item_price 
            FROM items 
            WHERE item_pk = %s AND item_deleted_at = 0 AND item_blocked_at = 0
        """, (item_pk,))
        item = cursor.fetchone()
        
        if not item:
            raise x.CustomException("Item not found", 404)

        # Find if item already exists in basket
        existing_item = next(
            (item for item in session["basket"] if item["item_pk"] == item_pk), 
            None
        )
                
        if existing_item:
            existing_item["quantity"] += quantity
        else:
            session["basket"].append({
                "item_pk": item_pk,
                "title": item["item_title"],
                "price": float(item["item_price"]),
                "quantity": quantity
            })
        
        session.modified = True
        
        # Calculate totals
        total_items = sum(item["quantity"] for item in session["basket"])
        total_price = sum(item["price"] * item["quantity"] for item in session["basket"])
        
        # Render appropriate template
        if session["basket"]:
            basket_content = render_template("___basket_items.html", 
                                          basket=session["basket"],
                                          total_price=total_price)
        else:
            basket_content = render_template("___empty_basket.html")
            
        
        return f"""
            <template mix-target="#basket-count">
                {total_items}
            </template>
            <template mix-target="#basket-content">
                {basket_content}
            </template>
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
        return """<template mix-target="#toast">System under maintenance</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
#############################################

@app.post("/update-basket/<item_pk>")
def update_basket_quantity(item_pk):
    try:
        if "basket" not in session:
            raise x.CustomException("No basket found", 400)
            
        # Get change value from form hidden input
        change = int(request.form.get("change", 0))
        
        # Find and update item in basket
        item = next((item for item in session["basket"] if item["item_pk"] == item_pk), None)
        if not item:
            raise x.CustomException("Item not found in basket", 404)
            
        # Update quantity but don't let it go below 1
        new_quantity = max(1, item["quantity"] + change)
        item["quantity"] = new_quantity
        
        # Ensure session is marked as modified
        session.modified = True
        
        # Calculate new totals using helper function
        total_price, total_items = calculate_basket_totals(session["basket"])
        
        # Render updated basket content
        basket_content = render_template("___basket_items.html", 
                                      basket=session["basket"], 
                                      total_price=total_price)
            
        # Return templates for ALL parts that need updating
        return f"""
            <template mix-target="#basket-count">{total_items}</template>
            <template mix-target="#basket-content">{basket_content}</template>
        """
        
    except Exception as ex:
        ic(ex)
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
        return """<template mix-target="#toast">System under maintenance</template>""", 500

#############################################

@app.get("/remove-from-basket/<item_pk>")
def remove_from_basket(item_pk):
    try:
        # Find and remove item from list
        item = next((item for item in session["basket"] if item["item_pk"] == item_pk), None)
        if not item:
            raise x.CustomException("Item not found in basket", 404)
            
        session["basket"].remove(item)
        session.modified = True
        
        # Calculate new totals
        total_items = sum(item["quantity"] for item in session["basket"])
        total_price = sum(item["price"] * item["quantity"] for item in session["basket"])
        
        if not session["basket"]:
            basket_content = render_template("___empty_basket.html")
        else:
            basket_content = render_template("___basket_items.html", 
                                          basket=session["basket"], 
                                          total_price=total_price)
            
        
        return f"""
            <template mix-target="#basket-count">{total_items}</template>
            <template mix-target="#basket-content">{basket_content}</template>
        """
        
    except Exception as ex:
        ic(ex)
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
        return """<template mix-target="#toast">System under maintenance</template>""", 500


#############################################

@app.post("/place-order")
def place_order():
    try:
        if not session.get("user"):
            return redirect(url_for("view_login"))
            
        if not session.get("basket"):
            raise x.CustomException("No items in basket", 400)
            
        delivery_name = request.form.get("delivery_name")
        delivery_email = request.form.get("delivery_email")
        
        # Use helper function for totals
        total_price, _ = calculate_basket_totals(session["basket"])
        
        session["last_order"] = {
            "items": session["basket"],  # No need for copy() since we're clearing the basket anyway
            "total": total_price,
            "customer_name": delivery_name,
            "customer_email": delivery_email,
            "order_date": int(time.time())
        }
        
        email_body = f"""
            <h1>Order Confirmation</h1>
            <p>Hi {delivery_name},</p>
            <p>Thank you for your order!</p>
            <h2>Order Details:</h2>
            <ul>
            {''.join(f'<li>{item["title"]} x {item["quantity"]} - ${item["price"] * item["quantity"]:.2f}</li>' 
                     for item in session["basket"])}
            </ul>
            <p><strong>Total: ${total_price:.2f}</strong></p>
        """
                                           
        x.send_email(session["user"]["user_email"], 
                    "Order Confirmation", 
                    email_body)
        
        # Clear basket
        session.pop("basket", None)
        session.modified = True
        
        return """<template mix-redirect="/order-confirmation"></template>"""
        
    except Exception as ex:
        ic(ex)
        ic("Form data:", request.form)  # Debug print
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
        return f"""<template mix-target="#toast">System under maintenance: {str(ex)}</template>""", 500



##############################
##############################
##############################

def _________PUT_________(): pass

##############################
##############################
##############################


##############################
@app.put("/users/avatar/<user_pk>")
def update_active_avatar(user_pk):
    try:
        if not session.get("user"): x.raise_custom_exception("Please login", 401)
        filename = request.form.get('filename')
        
        db, cursor = x.db()
        q = "UPDATE users SET user_avatar = %s WHERE user_pk = %s"
        cursor.execute(q, (filename, user_pk))
        if cursor.rowcount != 1: x.raise_custom_exception("cannot update avatar", 401)
        db.commit()
        
        session['user']['user_avatar'] = filename
        
        toast = render_template("___toast.html", message="Profile photo updated")
        return f"""
            <template mix-target="#toast">{toast}</template>
            <template mix-redirect="/profile"></template>
        """
        
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
        return "<template>System upgrading</template>", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.put("/users/<user_pk>")
def user_update(user_pk):
    try:
        if not session.get("user"): 
            x.raise_custom_exception("please login", 401)
        
        user_pk = x.validate_uuid4(user_pk)
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()
        user_updated_at = int(time.time())
        
        # Get the current user's roles
        current_user = session.get("user")
        is_restaurant = "restaurant" in current_user.get("roles", [])
        
        db, cursor = x.db()
        cursor.execute("START TRANSACTION")
        
        # Handle avatar upload if present
        user_avatar = None
        if 'user_avatar' in request.files:
            file = request.files['user_avatar']
            if file and file.filename:
                if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', 'webp')):
                    x.raise_custom_exception("Invalid file type. Please upload an image.", 400)
                
                optimized_image = optimize_image(file)
                filename = f"avatar_{user_pk}_{int(time.time())}.webp"
                filepath = os.path.join(config.AVATAR_FOLDER, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(optimized_image.getvalue())
                
                user_avatar = filename
        
        # Update user information
        if user_avatar:
            q = """UPDATE users 
                   SET user_name = %s, user_last_name = %s, user_email = %s, 
                       user_updated_at = %s, user_avatar = %s 
                   WHERE user_pk = %s"""
            cursor.execute(q, (user_name, user_last_name, user_email, 
                             user_updated_at, user_avatar, user_pk))
        else:
            q = """UPDATE users 
                   SET user_name = %s, user_last_name = %s, user_email = %s, 
                       user_updated_at = %s 
                   WHERE user_pk = %s"""
            cursor.execute(q, (user_name, user_last_name, user_email, 
                             user_updated_at, user_pk))
        
        if cursor.rowcount != 1: 
            x.raise_custom_exception("cannot update user", 401)
        
        # Handle restaurant address update if applicable
        if is_restaurant:
            street = request.form.get("street")
            house_number = request.form.get("house_number")
            postcode = request.form.get("postcode")
            city = request.form.get("city")
            
            if all([street, house_number, postcode, city]):
                # Get coordinates using geocoding
                full_address = f"{street} {house_number}, {postcode} {city}"
                geocoder = GeocodingHelper()
                coords = geocoder.get_coordinates(full_address)
                
                if not coords:
                    raise x.CustomException("Could not validate address", 400)
                    
                formatted_coords = geocoder.format_coordinates(*coords)
                
                # Check if coordinates exist for this restaurant
                cursor.execute("""
                    SELECT coords_pk FROM coords WHERE restaurant_fk = %s
                """, (user_pk,))
                existing_coords = cursor.fetchone()
                
                if existing_coords:
                    # Update existing coordinates
                    cursor.execute("""
                        UPDATE coords 
                        SET coordinates = %s, street = %s, house_number = %s, 
                            postcode = %s, city = %s
                        WHERE restaurant_fk = %s
                    """, (formatted_coords, street, house_number, postcode, 
                         city, user_pk))
                else:
                    # Insert new coordinates
                    coords_pk = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO coords (coords_pk, coordinates, restaurant_fk, 
                                          street, house_number, postcode, city)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (coords_pk, formatted_coords, user_pk, street, 
                          house_number, postcode, city))
        
        db.commit()
        
        # Update session
        session_update = {
            'user_name': user_name,
            'user_last_name': user_last_name,
            'user_email': user_email,
            'user_updated_at': user_updated_at
        }
        if user_avatar:
            session_update['user_avatar'] = user_avatar
            
        session['user'].update(session_update)
        
        toast = render_template("___toast.html", message="Profile updated")
        return f"""
            <template mix-target="#toast">{toast}</template>
            {"<template mix-redirect='/profile'></template>" if user_avatar else ""}    
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): 
            db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
        if isinstance(ex, x.mysql.connector.Error):
            if "users.user_email" in str(ex):
                toast = render_template("___toast.html", message="email not available")
                return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400
            return f"<template>Error: {str(ex)}</template>", 500        
        return f"<template>Error: {str(ex)}</template>", 500
   
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.put("/users/block/<user_pk>")
def user_block(user_pk):
    try:
        if not "admin" in session.get("user", {}).get("roles", []): 
            return redirect(url_for("view_login"))

        user = {
            "user_pk": x.validate_uuid4(user_pk),
            "user_blocked_at": int(time.time())
        }

        db, cursor = x.db()

        cursor.execute("""SELECT * FROM users WHERE user_pk = %s""", (user["user_pk"],))

        user_data = cursor.fetchone()
        user_email = user_data["user_email"]
        user_name = user_data["user_name"]

        cursor.execute("""UPDATE users 
                      SET user_blocked_at = %s 
                      WHERE user_pk = %s 
                      AND user_blocked_at = 0""", 
                      (user["user_blocked_at"], user["user_pk"]))
        
        if cursor.rowcount == 0:
            x.raise_custom_exception("User could not be blocked", 404)
        
        db.commit()
        
        # Render both templates
        btn_unblock = render_template("___btn_unblock_user.html", user=user)
        toast = render_template("___toast.html", message="User blocked")
        
        # Send email
      
        email_body = f"""<h1>Account blocked</h1>
          <p>Hi {user_name}, your account has been blocked. Please contact support for more information.</p>"""
        x.send_email(user_email, "Your account has been blocked", email_body)

        # Return both templates with their targets
        return f"""
            <template mix-target='#block-{user_pk}' mix-replace>
                {btn_unblock}
            </template>
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, ex.code
        
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            toast = render_template("___toast.html", message="Database error")
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, 500
        
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.put("/users/unblock/<user_pk>")
def user_unblock(user_pk):
    try:
        if not "admin" in session.get("user", {}).get("roles", []): 
            return redirect(url_for("view_login"))

        user = {
            "user_pk": x.validate_uuid4(user_pk)
        }

        db, cursor = x.db()

        cursor.execute("""SELECT * FROM users WHERE user_pk = %s""", (user["user_pk"],))
        user_data = cursor.fetchone()
        user_email = user_data["user_email"]
        user_name = user_data["user_name"]

        cursor.execute("""UPDATE users 
                      SET user_blocked_at = 0 
                      WHERE user_pk = %s 
                      AND user_blocked_at != 0""", 
                      (user["user_pk"],))
        
        if cursor.rowcount == 0:
            x.raise_custom_exception("User could not be unblocked", 404)
        
        db.commit()
        
        # Render both templates
        btn_block = render_template("___btn_block_user.html", user=user)
        toast = render_template("___toast.html", message="User unblocked")
        
        email_body = f"""<h1>Account unblocked</h1>
          <p>Hi {user_name}, your account has been unblocked. You can now login again.</p>"""
        x.send_email(user_email, "Your account has been unblocked", email_body)

        # Return both templates with their targets
        return f"""
            <template mix-target='#unblock-{user_pk}' mix-replace>
                {btn_block}
            </template>
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, ex.code
        
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            toast = render_template("___toast.html", message="Database error")
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, 500
        
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.put("/items/block/<item_pk>")
def item_block(item_pk):
    try:
        if not "admin" in session.get("user", {}).get("roles", []): 
            return redirect(url_for("view_login"))

        item = {
            "item_pk": x.validate_uuid4(item_pk),
            "item_blocked_at": int(time.time())
        }

        db, cursor = x.db()

        

        cursor.execute("""SELECT 
                            items.*, 
                            users.user_name,
                            users.user_email  
                        FROM 
                            items 
                        LEFT JOIN 
                            users ON items.restaurant_fk = users.user_pk
                        WHERE 
                            items.item_pk = %s""", (item["item_pk"],))
        user_data = cursor.fetchone()
        user_email = user_data["user_email"]
        user_name = user_data["user_name"]

        cursor.execute("""UPDATE items 
                      SET item_blocked_at = %s 
                      WHERE item_pk = %s 
                      AND item_blocked_at = 0""", 
                      (item["item_blocked_at"], item["item_pk"]))
        
        if cursor.rowcount == 0:
            x.raise_custom_exception("Item could not be blocked", 404)
        
        db.commit()
        
        # Render both templates
        btn_unblock = render_template("___btn_unblock_item.html", item=item)
        toast = render_template("___toast.html", message="Item blocked")
        
        email_body = f"""<h1>Item blocked</h1>
          <p>Hi {user_name}, your '{user_data["item_title"]}' menu item has been blocked. Please contact support if you have any questions.</p>"""
        x.send_email(user_email, "Your item has been blocked", email_body)

        # Return both templates with their targets
        return f"""
            <template mix-target='#block-{item_pk}' mix-replace>
                {btn_unblock}
            </template>
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, ex.code
        
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            toast = render_template("___toast.html", message="Database error")
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, 500
        
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.put("/items/unblock/<item_pk>")
def item_unblock(item_pk):
    try:
        if not "admin" in session.get("user", {}).get("roles", []): 
            return redirect(url_for("view_login"))

        item = {
            "item_pk": x.validate_uuid4(item_pk)
        }

        db, cursor = x.db()

        cursor.execute("""SELECT 
                            items.*, 
                            users.user_name,
                            users.user_email  
                        FROM 
                            items 
                        LEFT JOIN 
                            users ON items.restaurant_fk = users.user_pk
                        WHERE 
                            items.item_pk = %s""", (item["item_pk"],))
        user_data = cursor.fetchone()
        user_email = user_data["user_email"]
        user_name = user_data["user_name"]

        cursor.execute("""UPDATE items 
                      SET item_blocked_at = 0 
                      WHERE item_pk = %s 
                      AND item_blocked_at != 0""", 
                      (item["item_pk"],))
        
        if cursor.rowcount == 0:
            x.raise_custom_exception("Item could not be unblocked", 404)
        
        db.commit()
        
        # Render both templates
        btn_block = render_template("___btn_block_item.html", item=item)
        toast = render_template("___toast.html", message="Item unblocked")
        
        email_body = f"""<h1>Item unblocked</h1>
          <p>Hi {user_name}, your '{user_data["item_title"]}' menu item has been unblocked. It is now visible on your menu. Let us know if you have any questions.</p>"""
        x.send_email(user_email, "Your item has been unblocked", email_body)

        # Return both templates with their targets
        return f"""
            <template mix-target='#unblock-{item_pk}' mix-replace>
                {btn_block}
            </template>
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, ex.code
        
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            toast = render_template("___toast.html", message="Database error")
            return f"""
                <template mix-target="#toast" mix-bottom>
                    {toast}
                </template>
                """, 500
        
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""
            <template mix-target="#toast" mix-bottom>
                {toast}
            </template>
            """, 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.put("/users/change-password/<user_pk>")
def change_password(user_pk):
    try:
        if not session.get("user"):
            return redirect(url_for("view_login"))

        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_new_password = request.form.get("confirm_new_password")

        # First validate that all fields are filled
        if not all([current_password, new_password, confirm_new_password]):
            return """
                <template mix-target="#password-change-error">
                    <div class="text-c-red:-6 mt-2">All fields are required</div>
                </template>
            """, 400

        # Then check if new passwords match before proceeding
        if new_password != confirm_new_password:
            return """
                <template mix-target="#password-change-error">
                    <div class="text-c-red:-6 mt-2">New passwords do not match</div>
                </template>
            """, 400

        db, cursor = x.db()
        
        # Next verify the current password is correct
        cursor.execute("""SELECT user_password, user_email, user_name FROM users WHERE user_pk = %s""", 
                      (user_pk,))
        user_data = cursor.fetchone()
        
        if not check_password_hash(user_data["user_password"], current_password):
            return """
                <template mix-target="#password-change-error">
                    <div class="text-c-red:-6 mt-2">Current password is incorrect</div>
                </template>
            """, 400

        # If all validations pass, update the password
        hashed_password = generate_password_hash(new_password)
        cursor.execute("""
            UPDATE users 
            SET user_password = %s,
                user_updated_at = %s 
            WHERE user_pk = %s
        """, (hashed_password, int(time.time()), user_pk))
        
        db.commit()

        # Send confirmation email
        email_body = f"""<h1>Password Changed</h1>
            <p>Hi {user_data['user_name']}, your password has been successfully changed.</p>
            <p>If you did not make this change, please contact support immediately.</p>
        """
        x.send_email(user_data["user_email"], "Password Changed Successfully", email_body)

        # On success, remove the modal and show success toast
        toast = render_template("___toast.html", message="Password updated successfully")
        return f"""
            <template mix-target="#change-password-modal" mix-replace></template>
            <template mix-target="#toast" mix-bottom>{toast}</template>
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return """
            <template mix-target="#password-change-error">
                <div class="text-c-red:-14 mt-2">An error occurred. Please try again.</div>
            </template>
        """, 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
##############################
##############################
##############################

def _________DELETE_________(): pass

##############################
##############################
##############################


##############################
##############################
##############################

def _________BRIDGE_________(): pass

##############################
##############################
##############################


####################ROUTE##############################


@app.route("/restaurant/<restaurant_fk>")
@x.no_cache
def view_restaurant(restaurant_fk):
    try:
        db, cursor = x.db()

        # Fetch restaurant details from the `users` table
        query_restaurant = """SELECT user_pk, user_name, user_avatar 
                              FROM users 
                              WHERE user_pk = %s"""
        cursor.execute(query_restaurant, (restaurant_fk,))
        restaurant = cursor.fetchone()
        if not restaurant:
            toast = render_template("___toast.html", message="Restaurant not found.")
            return f"""<template mix-target="#toast">{toast}</template>""", 404

            


        # Fetch items associated with the restaurant
        query_items = """SELECT item_pk, item_title, item_price 
                         FROM items 
                         WHERE restaurant_fk = %s 
                         AND item_deleted_at = 0 
                         AND item_blocked_at = 0"""
        cursor.execute(query_items, (restaurant_fk,))
        items = cursor.fetchall()

        # Fetch images for the items
        item_images = {}
        if items:
            item_pks = [item['item_pk'] for item in items]
            format_strings = ','.join(['%s'] * len(item_pks))
            query_images = f"""SELECT item_fk, image 
                               FROM items_image 
                               WHERE item_fk IN ({format_strings})"""
            cursor.execute(query_images, tuple(item_pks))
            images = cursor.fetchall()

            # Group images by item_fk
            for img in images:
                if img['item_fk'] not in item_images:
                    item_images[img['item_fk']] = []
                item_images[img['item_fk']].append(img['image'])

        user = session.get("user")
        basket = session.get("basket", [])
        total_price, _ = calculate_basket_totals(basket)

        # Fetch coordinates associated with the restaurant
        query_coords = """SELECT coordinates, formatted_address, street, house_number, postcode, city 
                            FROM coords 
                            WHERE restaurant_fk = %s"""
        cursor.execute(query_coords, (restaurant_fk,))
        coords = cursor.fetchone()  # Assuming one coordinate per restaurant

        # Render template with the fetched data
        return render_template(
            "view_restaurant.html",
            restaurant=restaurant,
            items=items,
            coords=coords,
            item_images=item_images,
            user=user,
            basket=basket,
            total_price=total_price,
            page_title=restaurant["user_name"]
        )
    except Exception as ex:
        ic(ex)
        if "db" in locals():
            db.rollback()
        toast = render_template("___toast.html", message="Error loading restaurant page.")
        return f"""<template mix-target="#toast">{toast}</template>""", 500
    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.close()


#######################################################
@app.get("/restaurant")
@x.no_cache
def restaurant_dashboard():
    try:
        user = session.get("user")
        if not user:
            return redirect(url_for("view_login"))
        
        # Then check if user has admin role
        if "restaurant" not in user.get("roles", []):
            return redirect(url_for("view_login"))

        #basket
        basket = session.get("basket", [])
        total_price, _ = calculate_basket_totals(basket)


        # Ensure the user has the role "restaurant"
        if "restaurant" not in user.get("roles", []):
            return "Access restricted to restaurant users only.", 403

        restaurant_fk = user["user_pk"]

        db, cursor = x.db()

        # Fetch restaurant details from the `users` table
        query_restaurant = """SELECT user_pk, user_name, user_avatar 
                              FROM users 
                              WHERE user_pk = %s"""
        cursor.execute(query_restaurant, (restaurant_fk,))
        restaurant = cursor.fetchone()
        if not restaurant:
            toast = render_template("___toast.html", message="Restaurant not found.")
            return f"""<template mix-target="#toast">{toast}</template>""", 404

        # Fetch items associated with the restaurant
        query_items = """SELECT item_pk, item_title, item_price, item_updated_at 
                         FROM items 
                         WHERE restaurant_fk = %s 
                         AND item_deleted_at = 0 
                         AND item_blocked_at = 0"""
        cursor.execute(query_items, (restaurant_fk,))
        items = cursor.fetchall()

        # Fetch images for the items (we'll use the image filename here)
        item_images = {}
        if items:
            item_pks = [item['item_pk'] for item in items]
            format_strings = ','.join(['%s'] * len(item_pks))
            query_images = f"""SELECT item_fk, image 
                               FROM items_image 
                               WHERE item_fk IN ({format_strings})"""
            cursor.execute(query_images, tuple(item_pks))
            images = cursor.fetchall()

            for img in images:
                item_fk = img['item_fk']
                if item_fk not in item_images:
                    item_images[item_fk] = []
                item_images[item_fk].append(img['image'])  # Store the image filename

        # Fetch coordinates associated with the restaurant
        query_coords = """SELECT coordinates, street, house_number, postcode, city
                  FROM coords 
                  WHERE restaurant_fk = %s"""
        cursor.execute(query_coords, (restaurant_fk,))
        coords = cursor.fetchone()  # Assuming one coordinate per restaurant

        # Render the dashboard template
        return render_template(
            "restaurant_dashboard.html",
            restaurant=restaurant,
            items=items,
            item_images=item_images,
            coords=coords,
            user=user,
            time=time,
            basket=basket,
            total_price=total_price
        )

    except Exception as ex:
        print("Error loading restaurant dashboard:", ex)  # Log the actual error
        if "db" in locals():
            db.rollback()
        return f"Error loading restaurant dashboard: {ex}", 500
    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.close()



@app.post("/restaurant/add_item")
def add_item():
    try:
        # Ensure the user is logged in
        user = session.get("user")
        if not user:
            return "Please log in to add items.", 401

        # Ensure the user has the role "restaurant"
        if "restaurant" not in user.get("roles", []):
            return "Access restricted to restaurant users only.", 403

        restaurant_fk = user["user_pk"]

        # Get form data
        item_title = request.form.get("item_title")
        item_price = request.form.get("item_price")

        if not item_title or not item_price:
            return "Item title and price are required.", 400

        # Generate UUID for item_pk
        item_pk = str(uuid.uuid4())

        db, cursor = x.db()

        # Insert the new item
        query_add_item = """INSERT INTO items (item_pk, restaurant_fk, item_title, item_price, item_deleted_at, item_blocked_at, item_updated_at) 
                            VALUES (%s, %s, %s, %s, 0, 0, 0)"""
        cursor.execute(query_add_item, (item_pk, restaurant_fk, item_title, item_price))
        db.commit()

        print("Item successfully added.")

        # Redirect to the restaurant dashboard
        return redirect("/restaurant")

    except Exception as ex:
        print("Error adding item:", ex)
        if "db" in locals():
            db.rollback()
        return "Error adding item.", 500
    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.close()


@app.post("/restaurant/delete_item/<item_pk>")
def delete_item(item_pk):
    try:
        # Ensure the user is logged in
        user = session.get("user")
        if not user:
            return "Please log in to delete items.", 401

        # Ensure the user has the role "restaurant"
        if "restaurant" not in user.get("roles", []):
            return "Access restricted to restaurant users only.", 403

        # Get the restaurant_fk (user's ID)
        restaurant_fk = user["user_pk"]

        # Get the current Unix timestamp
        deleted_at_timestamp = int(time.time())

        db, cursor = x.db()

        # Debugging: Check the item_pk, restaurant_fk, and deleted_at values
        print(f"Attempting to delete item with item_pk: {item_pk} for restaurant_fk: {restaurant_fk}. Setting item_deleted_at to: {deleted_at_timestamp}")

        # Update the item to mark it as deleted
        query_delete_item = """UPDATE items 
                               SET item_deleted_at = %s 
                               WHERE item_pk = %s AND restaurant_fk = %s"""
        cursor.execute(query_delete_item, (deleted_at_timestamp, item_pk, restaurant_fk))
        db.commit()

        print(f"Item {item_pk} successfully marked as deleted.")

        # Redirect back to the restaurant dashboard
        return redirect("/restaurant")

    except Exception as ex:
        # Log detailed error to console
        print(f"Error deleting item: {ex}")
        if "db" in locals():
            db.rollback()
        return f"Error deleting item: {ex}", 500
    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.close()

@app.post("/restaurant/edit_item/<item_pk>")
def edit_item(item_pk):
    try:
        # Ensure the user is logged in
        user = session.get("user")
        if not user:
            return "Please log in to edit items.", 401

        # Ensure the user has the role "restaurant"
        if "restaurant" not in user.get("roles", []):
            return "Access restricted to restaurant users only.", 403

        restaurant_fk = user["user_pk"]

        # Get form data
        item_title = request.form.get("item_title")
        item_price = request.form.get("item_price")

        if not item_title and not item_price:
            return "At least one of item title or price must be provided.", 400

        db, cursor = x.db()

        # Build the query dynamically based on provided fields
        query_update = "UPDATE items SET "
        update_fields = []
        values = []

        if item_title:
            update_fields.append("item_title = %s")
            values.append(item_title)
        if item_price:
            update_fields.append("item_price = %s")
            values.append(item_price)

        # Set item_updated_at to current timestamp (in seconds)
        update_fields.append("item_updated_at = %s")
        values.append(int(time.time()))  # Current Unix timestamp

        query_update += ", ".join(update_fields) + " WHERE item_pk = %s AND restaurant_fk = %s"
        values.extend([item_pk, restaurant_fk])

        cursor.execute(query_update, tuple(values))
        db.commit()

        print(f"Item {item_pk} successfully updated.")

        # Redirect back to the restaurant dashboard
        return redirect("/restaurant")

    except Exception as ex:
        print(f"Error editing item: {ex}")
        if "db" in locals():
            db.rollback()
        return f"Error editing item: {ex}", 500
    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.close()


############# ADD IMAGE ITEMS ################
@app.post("/restaurant/add_item_image/<item_pk>")
def add_item_image(item_pk):
    try:
        if not "restaurant" in session.get("user", {}).get("roles", []): 
            return redirect(url_for("view_login"))

        if 'item_image' not in request.files:
            return f"""
                <template mix-target="#image-error-{item_pk}">
                    <span class="text-c-red:-14">No image file provided</span>
                </template>
            """, 400

        file = request.files['item_image']
        if not file or not file.filename:
            return f"""
                <template mix-target="#image-error-{item_pk}">
                    <span class="text-c-red:-14">No selected file</span>
                </template>
            """, 400

        # Check file type
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return f"""
                <template mix-target="#image-error-{item_pk}">
                    <span class="text-c-red:-14">Invalid file type. Please upload an image</span>
                </template>
            """, 400

        db, cursor = x.db()
        
        # Check number of existing images
        cursor.execute("""
            SELECT COUNT(*) as count FROM items_image WHERE item_fk = %s
        """, (item_pk,))
        result = cursor.fetchone()
        
        if result['count'] >= 3:
            return f"""
                <template mix-target="#image-error-{item_pk}">
                    <span class="text-c-red:-14">Maximum of 3 images allowed per item</span>
                </template>
            """, 400

        # Process and save the image
        optimized_image = optimize_image(file)
        filename = f"item_{item_pk}_{int(time.time())}.webp"
        # Changed this line to use the static/dishes path directly
        filepath = os.path.join(config.UPLOAD_FOLDER, filename)

        with open(filepath, 'wb') as f:
            f.write(optimized_image.getvalue())

        # Save to database
        cursor.execute("""
            INSERT INTO items_image (image_pk, item_fk, image)
            VALUES (%s, %s, %s)
        """, (str(uuid.uuid4()), item_pk, filename))


        cursor.execute("""
            UPDATE items 
            SET item_updated_at = %s 
            WHERE item_pk = %s
        """, (int(time.time()), item_pk))
        
        db.commit()

        # Clear any existing error message and redirect
        return f"""
            <template mix-target="#image-error-{item_pk}">
                <span></span>
            </template>
            <template mix-redirect="/restaurant"></template>
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        return f"""
            <template mix-target="#image-error-{item_pk}">
                <span class="text-c-red:-14">An error occurred while uploading the image: {str(ex)}</span>
            </template>
        """, 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.delete("/restaurant/delete_item_image/<item_pk>/<image_filename>")
def delete_item_image(item_pk, image_filename):
    try:
        if not "restaurant" in session.get("user", {}).get("roles", []): 
            return redirect(url_for("view_login"))

        db, cursor = x.db()
        
        # First verify the image belongs to the restaurant's item
        cursor.execute("""
            SELECT i.image_pk
            FROM items_image i
            JOIN items it ON i.item_fk = it.item_pk
            WHERE it.restaurant_fk = %s AND i.item_fk = %s AND i.image = %s
        """, (session["user"]["user_pk"], item_pk, image_filename))
        
        if not cursor.fetchone():
            toast = render_template("___toast.html", message="Image not found or unauthorized")
            return f"""<template mix-target="#toast">{toast}</template>""", 404

        # Delete the physical file from the dishes folder inside static
        image_path = os.path.join(config.UPLOAD_FOLDER, image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

        # Delete from database
        cursor.execute("""
            DELETE FROM items_image 
            WHERE item_fk = %s AND image = %s
        """, (item_pk, image_filename))
        
        cursor.execute("""
            UPDATE items 
            SET item_updated_at = %s 
            WHERE item_pk = %s
        """, (int(time.time()), item_pk))

        db.commit()
        
        return """<template mix-redirect="/restaurant"></template>"""

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        toast = render_template("___toast.html", message=str(ex))
        return f"""<template mix-target="#toast">{toast}</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()