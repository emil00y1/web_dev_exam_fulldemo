from flask import Flask, session, render_template, redirect, url_for, make_response, request, redirect
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
@app.get("/test-set-redis")
def view_test_set_redis():
    redis_host = "redis"
    redis_port = 6379
    redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)    
    redis_client.set("name", "Santiago", ex=10)
    # name = redis_client.get("name")
    return "name saved"

@app.get("/test-get-redis")
def view_test_get_redis():
    redis_host = "redis"
    redis_port = 6379
    redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)    
    name = redis_client.get("name")
    if not name: name = "no name"
    return name

##############################
@app.get("/")
def view_index():
    try:
        page = request.args.get("page", default=1, type=int)
        per_page = 7
        offset = (page - 1) * per_page

        db, cursor = x.db()
        # Modified query to include address fields
        q = """SELECT coords.*, users.user_name, users.user_avatar,
                      coords.street, coords.house_number, coords.postcode, coords.city
               FROM coords 
               JOIN users ON coords.restaurant_fk = users.user_pk
               LIMIT %s OFFSET %s"""
        cursor.execute(q, (per_page, offset))
        rows = cursor.fetchall()

        # Fetch total count of restaurants for pagination
        cursor.execute("SELECT COUNT(*) AS total FROM coords")
        total = cursor.fetchone()["total"]

        next_page = page + 1 if offset + per_page < total else None
        prev_page = page - 1 if page > 1 else None

        user = session.get("user")
        basket = session.get("basket", [])
        total_price, _ = calculate_basket_totals(basket)

        # Enhanced coords list with address information
        coords = [
            {
                "coords_pk": row["coords_pk"],
                "coordinates": row["coordinates"],
                "restaurant_fk": row["restaurant_fk"],
                "user_name": row["user_name"],
                "user_avatar": row["user_avatar"],
                "street": row["street"],
                "house_number": row["house_number"],
                "postcode": row["postcode"],
                "city": row["city"]
            }
            for row in rows
        ]

        return render_template(
            "view_index.html",
            coords=coords,
            next_page=next_page,
            prev_page=prev_page,
            user=user,
            basket=basket,
            total_price=total_price
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
        
        # Rest of your existing search logic...
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
            total_price=calculate_basket_totals(session.get("basket", []))[0]
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
        return render_template("view_signup.html", x=x, title="Signup", roles=roles)
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
        msg=msg
    )



@app.get("/resend-verification/<email>")
@x.no_cache
def resend_verification(email):
    try:
        db, cursor = x.db()
        
        cursor.execute("""
            SELECT user_verification_key
            FROM users
            WHERE user_email = %s AND user_verified_at = 0
        """, (email,))
        result = cursor.fetchone()
        
        if not result:
            toast = render_template("___toast.html", message="No unverified account found with this email")
            return f"""<template mix-target="#toast">{toast}</template>""", 404
            
        try:
            verification_key = result["user_verification_key"]
            email_body = f"""To verify your account, please <a href="{config.DOMAIN}/verify/{verification_key}">click here</a>"""
            x.send_email(email, "Please verify your account", email_body)
            return "", 200
            
        except Exception as e:
            ic(e)  # Using project's debug print pattern
            toast = render_template("___toast.html", message=result)
            return f"""<template mix-target="#toast">{toast}</template>""", 500
            
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast">{toast}</template>""", ex.code
            
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            toast = render_template("___toast.html", message="Database error")
            return f"""<template mix-target="#toast">{toast}</template>""", 500
            
        toast = render_template("___toast.html", message="System under maintenance")
        return f"""<template mix-target="#toast">{toast}</template>""", 500
        
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.get("/passwordrecovery")
@x.no_cache
def view_forgot_password():
    if session.get("user"):
        return redirect(url_for("show_profile"))
    return render_template(
        "view_forgot_password.html",
        x=x
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
            x=x
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
    # Check if user is logged in
    if not session.get("user", ""): 
        return redirect(url_for("view_login"))
    
    user = session.get("user")
    basket = session.get("basket", [])
    total_price, _ = calculate_basket_totals(basket)
    
    # Check if user has admin role
    if not "admin" in user.get("roles", ""):
        return redirect(url_for("view_login"))
    
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
        
        return render_template("view_admin.html", users=users, time=time, user=user, items=items, basket=basket, total_price=total_price)
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
        basket=basket
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
            user=session.get("user")
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
        
    return render_template("view_order_confirmation.html", order=session.get("last_order"), user=session.get("user"))



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
        cursor.execute("""UPDATE users 
                      SET user_deleted_at = %s 
                      WHERE user_pk = %s""", 
                      (user["user_deleted_at"], user["user_pk"]))

        if cursor.rowcount == 0:
            x.raise_custom_exception("User could not be deleted", 404)

        db.commit()

        # Format the deleted_at date and create the replacement HTML
        formatted_date = time.strftime('%A, %d %B %Y', time.localtime(user["user_deleted_at"]))
        deleted_html = f'<div class="d-flex a-items-center text-c-red:-14">Deleted: {formatted_date}</div>'

        toast = render_template("___toast.html", message="User deleted")

        email_body = f"""<h1>Account deleted</h1>
          <p>Hi {user_name}, your account has been deleted. We are sad to see you go.</p>"""
        x.send_email(user_email, "Your account has been deleted", email_body)
        # Return both the deleted_at text and toast
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

        modal_html = render_template("___delete_modal.html", user_pk=user_pk)
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
    # session.clear()
    # session.modified = True
    # ic("*"*30)
    # ic(session)
    return redirect(url_for("view_login"))


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
        
        user_pk = str(uuid.uuid4())
        user_avatar = ""
        user_created_at = int(time.time())
        user_deleted_at = 0
        user_blocked_at = 0
        user_updated_at = 0
        user_verified_at = 0
        user_verification_key = str(uuid.uuid4())

        user_role_pk = request.form.get("role")

        db, cursor = x.db()

        # Ensure the selected role is valid and not "admin"
        cursor.execute("""
            SELECT role_name FROM roles WHERE role_pk = %s
        """, (user_role_pk,))
        selected_role = cursor.fetchone()
        
        if not selected_role:
            raise x.CustomException("Invalid role selected", 400)
        
        if selected_role["role_name"].lower() == "admin":
            raise x.CustomException("Unauthorized role selection", 400)
        
        # Check for existing email
        cursor.execute("SELECT user_deleted_at FROM users WHERE user_email = %s", (user_email,))
        existing_user = cursor.fetchone()
        
        if existing_user and existing_user["user_deleted_at"] == 0:
            toast = render_template("___toast.html", message="Email not available")
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400

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
        
        # Insert or update user
        if existing_user:
            cursor.execute("""
                UPDATE users 
                SET user_deleted_at = 0,
                    user_verified_at = 0,
                    user_name = %s,
                    user_last_name = %s,
                    user_password = %s,
                    user_verification_key = %s,
                    user_updated_at = %s
                WHERE user_email = %s
            """, (user_name, user_last_name, hashed_password, 
                 user_verification_key, user_created_at, user_email))
        else:
            cursor.execute(
                'INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (user_pk, user_name, user_last_name, user_email, hashed_password, 
                 user_avatar, user_created_at, user_deleted_at, user_blocked_at, 
                 user_updated_at, user_verified_at, user_verification_key)
            )
            
        # Add user role
        cursor.execute("""
            INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
            VALUES (%s, %s)
        """, (user_pk, user_role_pk))

        # If restaurant, save address and coordinates
        if selected_role["role_name"].lower() == "restaurant":
            coords_pk = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO coords (
                    coords_pk, coordinates, restaurant_fk, 
                    street, house_number, postcode, city, formatted_address
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (coords_pk, formatted_coords, user_pk, street, 
                 house_number, postcode, city, full_address))

        email_body = f"""To verify your account, please <a href="{config.DOMAIN}/verify/{user_verification_key}">click here</a>"""
        x.send_email(user_email, "Please verify your account", email_body)
        db.commit()

        return f"""<template mix-redirect="/login?msg=verify_email&email={user_email}"></template>""", 201
    
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
            toast = render_template("___toast.html", message="User not registered")
            return f"""<template mix-target="#toast">{toast}</template>""", 400     
        # if rows[0]["user_deleted_at"] != 0:
        #     toast = render_template("___toast.html", message="This user does not exist")
        #     return f"""<template mix-target="#toast">{toast}</template>""", 401
        if not check_password_hash(rows[0]["user_password"], user_password):
            toast = render_template("___toast.html", message="Invalid credentials")
            return f"""<template mix-target="#toast">{toast}</template>""", 401
        
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
        return """<template mix-redirect="/profile"></template>"""
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
        if not session.get("user"):
            return redirect(url_for("view_login"))
        
        is_admin = "admin" in session.get("user", {}).get("roles", [])
        current_user_pk = session["user"]["user_pk"]
        
        if not is_admin and current_user_pk != user_pk:
            x.raise_custom_exception("Unauthorized access", 403)

        password = request.form.get('password')
        if not password:
            return """
                <template mix-target="#delete-modal-error">
                    <p class="text-c-red:-14 mt-2">Password is required</p>
                </template>
            """

        db, cursor = x.db()
        try:
            cursor.execute("""SELECT * FROM users WHERE user_pk = %s""", (user_pk,))
            user_data = cursor.fetchone()
            
            if not user_data:
                x.raise_custom_exception("User not found", 404)

            # Verify password
            if not check_password_hash(user_data["user_password"], password):
                return """
                    <template mix-target="#delete-modal-error">
                        <div class="text-c-red:-14 mt-2">Invalid password</div>
                    </template>
                """

            # Proceed with deletion
            deleted_at = int(time.time())
            cursor.execute("""UPDATE users 
                          SET user_deleted_at = %s 
                          WHERE user_pk = %s""", 
                          (deleted_at, user_pk))
            
            if cursor.rowcount == 0:
                x.raise_custom_exception("User could not be deleted", 404)
            
            db.commit()

            # Send confirmation email
            email_body = f"""<h1>Account deleted</h1>
              <p>Hi {user_data['user_name']}, your account has been deleted. We are sad to see you go.</p>"""
            x.send_email(user_data["user_email"], "Your account has been deleted", email_body)

            # Handle response based on who was deleted
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
            
        finally:
            cursor.close()
            db.close()

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


##############################
@app.get("/verify/<verification_key>")
@x.no_cache
def verify_user(verification_key):
    try:
        ic(verification_key)
        verification_key = x.validate_uuid4(verification_key)
        user_verified_at = int(time.time())

        db, cursor = x.db()
        q = """ UPDATE users 
                SET user_verified_at = %s 
                WHERE user_verification_key = %s"""
        cursor.execute(q, (user_verified_at, verification_key))
        if cursor.rowcount != 1: x.raise_custom_exception("cannot verify account", 400)
        db.commit()
        return redirect(url_for("view_login", msg="verified"))

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException): return ex.message, ex.code    
        if isinstance(ex, x.mysql.connector.Error):
            ic(ex)
            return "Database under maintenance", 500        
        return "System under maintenance", 500  
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()    


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
            total_price=total_price
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
        # Ensure the user is logged in
        user = session.get("user")

        #basket
        basket = session.get("basket", [])
        total_price, _ = calculate_basket_totals(basket)

        if not user:
            return "Please log in to access your dashboard.", 401

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
@app.post("/items/<item_pk>/add_image")
def add_item_image(item_pk):
    try:
        # Ensure the user is logged in
        user = session.get("user")
        if not user:
            return "Please log in to add images.", 401

        # Ensure the user has the role "restaurant"
        if "restaurant" not in user.get("roles", []):
            return "Access restricted to restaurant users only.", 403

        # Validate the item_pk (ensure it's a valid UUID)
        item_pk = x.validate_uuid4(item_pk)
        restaurant_fk = user["user_pk"]

        # Image upload folder
        UPLOAD_FOLDER = os.path.join('static', 'dishes')
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        # Check if file is in the request
        if 'item_image' not in request.files:
            return "No image file provided.", 400

        file = request.files['item_image']
        if not file or not file.filename:
            return "No selected file.", 400

        # Validate file type
        if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            return "Invalid file type. Please upload an image.", 400

        # Optimize and save the image
        optimized_image = optimize_image(file)
        filename = f"item_{item_pk}_{int(time.time())}.webp"  # Generate unique filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        with open(filepath, 'wb') as f:
            f.write(optimized_image.getvalue())

        # Save the image reference in the database with the correct item_fk (item_pk)
        db, cursor = x.db()
        query = """INSERT INTO items_image (item_fk, image) VALUES (%s, %s)"""
        cursor.execute(query, (item_pk, filename))  # Save image associated with the specific item
        db.commit()

        print(f"Image successfully added for item {item_pk}.")

        # Redirect back to the item management page
        return redirect("/restaurant")

    except Exception as ex:
        print(f"Error adding item image: {ex}")
        if "db" in locals():
            db.rollback()
        return f"Error adding item image: {ex}", 500

    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.close()


#####

@app.post("/items/<item_pk>/delete_image/<image_filename>")
def delete_item_image(item_pk, image_filename):
    try:
        # Ensure the user is logged in
        user = session.get("user")
        if not user:
            return "Please log in to delete an image.", 401

        # Ensure the user has the role "restaurant"
        if "restaurant" not in user.get("roles", []):
            return "Access restricted to restaurant users only.", 403

        # Ensure the file exists and delete it
        image_path = os.path.join('static', 'dishes', image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

        # Now delete the image record from the database
        db, cursor = x.db()
        query_delete_image = """DELETE FROM items_image 
                                WHERE item_fk = %s AND image = %s"""
        cursor.execute(query_delete_image, (item_pk, image_filename))
        db.commit()

        print(f"Image {image_filename} deleted for item {item_pk}.")
        return redirect(url_for('restaurant_dashboard'))

    except Exception as ex:
        print(f"Error deleting image {image_filename} for item {item_pk}: {ex}")
        if "db" in locals():
            db.rollback()
        return f"Error deleting image {image_filename} for item {item_pk}: {ex}", 500
    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.close()
