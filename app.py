from flask import Flask, session, render_template, redirect, url_for, make_response, request
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import x
import uuid 
import time
import redis
import os

from icecream import ic
ic.configureOutput(prefix=f'***** | ', includeContext=True)

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'  # or 'redis', etc.
Session(app)

@app.template_filter('strftime')
def strftime_filter(timestamp, format='%A, %d %B %Y'):
    return time.strftime(format, timestamp)


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
    ic(session)
    if session.get("user"):
        if len(session.get("user").get("roles")) > 1:
            return redirect(url_for("view_choose_role")) 
        if "admin" in session.get("user").get("roles"):
            return redirect(url_for("view_admin"))
        if "customer" in session.get("user").get("roles"):
            return redirect(url_for("view_customer")) 
        if "partner" in session.get("user").get("roles"):
            return redirect(url_for("view_partner"))         
    return render_template("view_signup.html", x=x, title="Signup")


##############################
@app.get("/login")
@x.no_cache
def view_login():  
    if session.get("user"):
        return redirect(url_for("profile"))
    
    messages = {
        "verify_email": "Account created! Please check your email to verify your account",
        "verified": "Email verified successfully! Please log in"
    }
    
    msg = request.args.get("msg")
    display_message = messages.get(msg, "")
    
    return render_template(
        "view_login.html", 
        x=x, 
        title="Login", 
        message=display_message
    )

##############################
@app.get("/customer")
@x.no_cache
def view_customer():
    if not session.get("user", ""): 
        return redirect(url_for("view_login"))
    user = session.get("user")
    if len(user.get("roles", "")) > 1:
        return redirect(url_for("view_choose_role"))
    return render_template("view_customer.html", user=user)

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
@app.get("/choose-role")
@x.no_cache
def view_choose_role():
    if not session.get("user", ""): 
        return redirect(url_for("view_login"))
    if not len(session.get("user").get("roles")) >= 2:
        return redirect(url_for("view_login"))
    user = session.get("user")
    return render_template("view_choose_role.html", user=user, title="Choose role")


##############################
@app.get("/profile")
@x.no_cache
def show_profile():
    user = session.get("user", "")
    if not user:
        return redirect(url_for("view_login"))
    return render_template("view_profile.html",x=x, user=user)


##############################
@app.get("/users/delete/<user_pk>")
def user_delete(user_pk):
    try:
         # Ensure user is logged in
        if not session.get("user"):
            return redirect(url_for("view_login"))
        
        is_admin = "admin" in session.get("user", {}).get("roles", [])
        current_user_pk = session["user"]["user_pk"]
        
        # Check authorization
        if not is_admin and current_user_pk != user_pk:
            x.raise_custom_exception("Unauthorized access", 403)

        user = {
            "user_pk": x.validate_uuid4(user_pk),
            "user_deleted_at": int(time.time())
        }

        db, cursor = x.db()
        cursor.execute("""SELECT * FROM users WHERE user_pk = %s""", (user["user_pk"],))
        user_data = cursor.fetchone()
        if not user_data:
            x.raise_custom_exception("User not found", 404)

        user_email = user_data["user_email"]
        user_name = user_data["user_name"]

        cursor.execute("""UPDATE users 
                      SET user_deleted_at = %s 
                      WHERE user_pk = %s""", 
                      (user["user_deleted_at"], user["user_pk"]))
        
        if cursor.rowcount == 0:
            x.raise_custom_exception("User could not be deleted", 404)
        
        db.commit()

        # Customize message based on whether it's an admin deletion or self-deletion
        toast_message = "Your account has been deleted" if current_user_pk == user_pk else "User deleted"
        toast = render_template("___toast.html", message=toast_message)
        
        if current_user_pk == user_pk:
            session.clear()
            return """<template mix-redirect="/login"></template>"""


        # Format the deleted_at date and create the replacement HTML
        formatted_date = time.strftime('%A, %d %B %Y', time.localtime(user["user_deleted_at"]))
        deleted_html = f'<div class="d-flex a-items-center text-c-red:-14">Deleted: {formatted_date}</div>'
        
        
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

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

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

        db, cursor = x.db()
        
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
                WHERE user_email = %s"""
        cursor.execute(q, (user_email,))
        rows = cursor.fetchall()
        if not rows:
            toast = render_template("___toast.html", message="user not registered")
            return f"""<template mix-target="#toast">{toast}</template>""", 400     
        if not check_password_hash(rows[0]["user_password"], user_password):
            toast = render_template("___toast.html", message="invalid credentials")
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
        if len(roles) == 1:
            return f"""<template mix-redirect="/{roles[0]}"></template>"""
        return f"""<template mix-redirect="/choose-role"></template>"""
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

# @app.put("/users")
# def user_update():
#     print("update")
#     try:
#         if not session.get("user"): x.raise_custom_exception("please login", 401)

#         user_pk = session.get("user").get("user_pk")
#         user_name = x.validate_user_name()
#         user_last_name = x.validate_user_last_name()
#         user_email = x.validate_user_email()

#         user_updated_at = int(time.time())

#         db, cursor = x.db()
#         q = """ UPDATE users
#                 SET user_name = %s, user_last_name = %s, user_email = %s, user_updated_at = %s
#                 WHERE user_pk = %s
#             """
#         cursor.execute(q, (user_name, user_last_name, user_email, user_updated_at, user_pk))
#         if cursor.rowcount != 1: x.raise_custom_exception("cannot update user", 401)
#         db.commit()
#         return """<template>user updated</template>"""
#     except Exception as ex:
#         ic(ex)
#         if "db" in locals(): db.rollback()
#         if isinstance(ex, x.CustomException): 
#             toast = render_template("___toast.html", message=ex.message)
#             return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
#         if isinstance(ex, x.mysql.connector.Error):
#             if "users.user_email" in str(ex):
#                 toast = render_template("___toast.html", message="email not available")
#                 return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400
#             return "<template>System upgrading</template>", 500        
#         return "<template>System under maintenance</template>", 500    
#     finally:
#         if "cursor" in locals(): cursor.close()
#         if "db" in locals(): db.close()


@app.put("/users/<user_pk>")
def user_update(user_pk):
    try:
        if not session.get("user"): x.raise_custom_exception("please login", 401)
        user_pk = x.validate_uuid4(user_pk)
        user_name = x.validate_user_name()
        user_last_name = x.validate_user_last_name()
        user_email = x.validate_user_email()
        user_updated_at = int(time.time())
       
        db, cursor = x.db()
        q = "UPDATE users SET user_name = %s, user_last_name = %s, user_email = %s, user_updated_at = %s WHERE user_pk = %s"
        cursor.execute(q, (user_name, user_last_name, user_email, user_updated_at, user_pk))
        if cursor.rowcount != 1: x.raise_custom_exception("cannot update user", 401)
        db.commit()

        # Update the session user data
        session['user'].update({
            'user_name': user_name,
            'user_last_name': user_last_name,
            'user_email': user_email,
            'user_updated_at': user_updated_at
        })
        
        toast = render_template("___toast.html", message="Profile updated")
        return f"""<template mix-target="#toast">{toast}</template>"""

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        if isinstance(ex, x.CustomException):
            toast = render_template("___toast.html", message=ex.message)
            return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", ex.code
        if isinstance(ex, x.mysql.connector.Error):
            if "users.user_email" in str(ex):
                toast = render_template("___toast.html", message="email not available")
                return f"""<template mix-target="#toast" mix-bottom>{toast}</template>""", 400
            return "<template>System upgrading</template>", 500        
        return "<template>System under maintenance</template>", 500    
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



