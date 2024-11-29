from flask import Flask, session, render_template, redirect, url_for, make_response, request
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from PIL import Image
import x
import uuid 
import time
import redis
import os, io

from icecream import ic
ic.configureOutput(prefix=f'***** | ', includeContext=True)

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'  # or 'redis', etc.
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


def get_user_avatars(user_pk):
    avatar_dir = os.path.join('static', 'avatars')
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


# app.secret_key = "your_secret_key"

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
        q = """SELECT coords.*, users.user_name, users.user_avatar 
               FROM coords 
               JOIN users ON coords.restaurant_fk = users.user_pk
               LIMIT %s OFFSET %s"""
        cursor.execute(q, (per_page, offset))
        rows = cursor.fetchall()

        # Fetch total count of restaurants for pagination
        cursor.execute("SELECT COUNT(*) AS total FROM coords")
        total = cursor.fetchone()["total"]

        # Determine next and previous page numbers
        next_page = page + 1 if offset + per_page < total else None
        prev_page = page - 1 if page > 1 else None

        user = session.get("user")

        coords = [
            {
                "coords_pk": row["coords_pk"],
                "coordinates": row["coordinates"],
                "restaurant_fk": row["restaurant_fk"],
                "user_name": row["user_name"],
                "user_avatar": row["user_avatar"],
            }
            for row in rows
        ]

        return render_template(
            "view_index.html",
            coords=coords,
            next_page=next_page,
            prev_page=prev_page,
            user=user
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
    
    msg = request.args.get("msg")
    display_message = messages.get(msg, "")
    
    return render_template(
        "view_login.html", 
        x=x, 
        title="Login", 
        message=display_message
    )


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
@app.get("/partner")
@x.no_cache
def view_partner():
    if not session.get("user", ""): 
        return redirect(url_for("view_login"))
    user = session.get("user")
    if len(user.get("roles", "")) > 1:
        return redirect(url_for("view_choose_role"))
    return response


##############################
@app.get("/admin")
@x.no_cache
def view_admin():
    # Check if user is logged in
    if not session.get("user", ""): 
        return redirect(url_for("view_login"))
    
    user = session.get("user")
    
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
        
        return render_template("view_admin.html", users=users, time=time, user=user, items=items)
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
    return render_template("view_profile.html",x=x, user=user, avatars=avatars)


##############################
@app.get("/users/delete/<user_pk>")
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
@app.get("/items/delete/<item_pk>")
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

        user_role_pk = request.form.get("role")  # Get selected role_pk from the form

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
        
        # First check if the email exists and if it belongs to a deleted user
        cursor.execute("SELECT user_deleted_at FROM users WHERE user_email = %s", (user_email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            if existing_user["user_deleted_at"] == 0:
                # Active user with this email exists
                toast = render_template("___toast.html", message="Email not available")
                return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400
            else:
                # Reactivate deleted user
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
            # New user signup
            q = 'INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
            cursor.execute(q, (user_pk, user_name, user_last_name, user_email, 
                             hashed_password, user_avatar, user_created_at, user_deleted_at, 
                             user_blocked_at, user_updated_at, user_verified_at, 
                             user_verification_key))
                             
            # Add customer role for new user
            cursor.execute("""
                INSERT INTO users_roles (user_role_user_fk, user_role_role_fk)
                VALUES (%s, %s)
            """, (user_pk, user_role_pk))

        email_body = f"""To verify your account, please <a href="http://127.0.0.1/verify/{user_verification_key}">click here</a>"""
        x.send_email(user_email, "Please verify your account", email_body)
        db.commit()


        return """<template mix-redirect="/login?msg=verify_email"></template>""", 201
    
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
              <a href="127.0.0.1/createpassword?id={user_data['user_pk']}">Create new password</a>
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
        if not session.get("user"): x.raise_custom_exception("please login", 401)
        user_pk = x.validate_uuid4(user_pk)
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()
        user_updated_at = int(time.time())
        
        user_avatar = None

        UPLOAD_FOLDER = os.path.join('static', 'avatars')
        ic("Request files:", request.files)

        if 'user_avatar' in request.files:
            file = request.files['user_avatar']
            if file and file.filename:
                if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', 'webp')):
                    x.raise_custom_exception("Invalid file type. Please upload an image.", 400)
                
                optimized_image = optimize_image(file)
                filename = f"avatar_{user_pk}_{int(time.time())}.webp" # This will be stored in DB
                filepath = os.path.join(UPLOAD_FOLDER, filename)  # Full path for saving file
                
                with open(filepath, 'wb') as f:
                    f.write(optimized_image.getvalue())
                
                user_avatar = filename  # Only store filename in DB
       
        db, cursor = x.db()
        if user_avatar:
            q = "UPDATE users SET user_name = %s, user_last_name = %s, user_email = %s, user_updated_at = %s, user_avatar = %s WHERE user_pk = %s"
            cursor.execute(q, (user_name, user_last_name, user_email, user_updated_at, user_avatar, user_pk))
        else:
            q = "UPDATE users SET user_name = %s, user_last_name = %s, user_email = %s, user_updated_at = %s WHERE user_pk = %s"
            cursor.execute(q, (user_name, user_last_name, user_email, user_updated_at, user_pk))
            
        if cursor.rowcount != 1: x.raise_custom_exception("cannot update user", 401)
        db.commit()

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
        print("Type of exception:", type(ex))  # Add this
        print("Exception details:", str(ex))    # Add this
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
        if isinstance(ex, x.mysql.connector.Error):
            if "users.user_email" in str(ex):
                toast = render_template("___toast.html", message="email not available")
                return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400
            return f"<template>Error: {str(ex)}</template>", 500        
        
        # Instead of generic "System under maintenance", let's see the error
        return f"<template>Error: {str(ex)}</template>", 500
   
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.get("/users/block/<user_pk>")
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
@app.get("/users/unblock/<user_pk>")
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
@app.get("/items/block/<item_pk>")
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
@app.get("/items/unblock/<item_pk>")
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

        user = session.get("user")

        # Fetch coordinates associated with the restaurant
        query_coords = """SELECT coordinates 
                          FROM coords 
                          WHERE restaurant_fk = %s"""
        cursor.execute(query_coords, (restaurant_fk,))
        coords = cursor.fetchone()  # Assuming one coordinate per restaurant

        # Render template with the fetched data
        return render_template("view_restaurant.html", 
                               restaurant=restaurant, 
                               items=items, 
                               coords=coords,
                               user=user)
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        toast = render_template("___toast.html", message="Error loading restaurant page.")
        return f"""<template mix-target="#toast">{toast}</template>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()
