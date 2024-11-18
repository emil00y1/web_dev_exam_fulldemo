import x
import uuid
import time
import random
from werkzeug.security import generate_password_hash
from faker import Faker
 
fake = Faker()
 
from icecream import ic
ic.configureOutput(prefix=f'***** | ', includeContext=True)
 
 
db, cursor = x.db()
 
food_names = [
    "Burger", "Pizza", "Pasta", "Sushi", "Salad", "Sandwich", "Tacos", "Steak",
    "Curry", "Ramen", "Burrito", "Falafel", "Soup", "Hotdog", "Fries", "Kebab",
    "Noodles", "Ice cream", "Brownie", "Cupcake", "Donut", "Cheeseburger", "Lobster",
    "Fried chicken", "Chicken wings", "Spring rolls", "Clams", "Grilled cheese",
    "Waffles", "Peking duck", "Paella", "Lasagna", "Dim sum", "Chicken Parmesan",
    "Fish and chips", "Moussaka", "Goulash", "Chili", "Hot wings", "Pork ribs",
    "Tuna tartare", "Chicken nuggets", "Eggroll", "Frittata", "Gumbo", "Barbecue ribs",
    "Meatballs", "Shawarma", "Gyros", "Tofu stir fry", "Beef Wellington",
    "Chicken fried rice", "Caesar salad", "Baked ziti", "Sausage roll", "Maki rolls",
    "Falafel pita", "Grilled salmon", "Moussaka", "Chicken tikka masala", "Ceviche",
    "Risotto", "Chowder", "Beef stew", "Tortilla chips", "Sloppy Joes", "Cornbread",
    "Steak frites", "Quiche", "Poutine", "Macaroni and cheese", "Pastrami sandwich",
    "Peking pork", "Vegetable stir fry", "Charcuterie board", "Lobster roll",
    "Mozzarella sticks", "Pizza bagels", "Quesadilla", "Currywurst", "Poffertjes",
    "Pavlova", "Piadina", "Beef taco", "Grilled shrimp", "Churros", "Bangers and mash",
    "Chana masala", "Chicken shawarma", "Fish tacos", "Stuffed peppers", "Pumpkin soup",
    "Stuffed mushrooms", "Bagel with lox", "Egg salad", "Pulled pork sandwich",
    "Chicken Caesar wrap", "Fried rice", "Tuna melt", "Pasta primavera", "Hot fudge sundae",
    "Cheese fondue", "Cranberry sauce", "Sashimi", "Tempura", "Pork schnitzel", "Roast chicken",
    "Apple pie", "Potato salad", "Souvlaki", "Pork belly", "Salmon sushi", "Chicken burrito",
    "Vegan burger", "Sweet potato fries", "Chicken kebab", "Vegetarian pizza", "Pastrami on rye"
]
 
 
 
def insert_item(item):
    # Insert the item into the items table
    cursor.execute("""
        INSERT INTO items (item_pk, restaurant_fk, title, price)
        VALUES (%s, %s, %s, %s)
    """, (item["item_pk"], item["restaurant_fk"], item["title"], item["price"]))
 
 
def insert_user(user):       
    q = f"""
        INSERT INTO users
        VALUES (%s, %s ,%s ,%s ,%s ,%s ,%s ,%s ,%s ,%s ,%s ,%s)        
        """
    values = tuple(user.values())
    cursor.execute(q, values)
    
try:
    
    ##############################
  # Drop the items table before dropping the users table
    cursor.execute("DROP TABLE IF EXISTS items")
 
# Then drop the users table
    cursor.execute("DROP TABLE IF EXISTS users_roles")
    cursor.execute("DROP TABLE IF EXISTS users")
    q = """
        CREATE TABLE users (
            user_pk CHAR(36),
            user_name VARCHAR(20) NOT NULL,
            user_last_name VARCHAR(20) NOT NULL,
            user_email VARCHAR(100) NOT NULL UNIQUE,
            user_password VARCHAR(255) NOT NULL,
            user_avatar VARCHAR(50),
            user_created_at INTEGER UNSIGNED,
            user_deleted_at INTEGER UNSIGNED,
            user_blocked_at INTEGER UNSIGNED,
            user_updated_at INTEGER UNSIGNED,
            user_verified_at INTEGER UNSIGNED,
            user_verification_key CHAR(36),
            PRIMARY KEY(user_pk)
        )
        """        
    cursor.execute(q)
 
 
    ##############################
    cursor.execute("DROP TABLE IF EXISTS roles")
    q = """
        CREATE TABLE roles (
            role_pk CHAR(36),
            role_name VARCHAR(10) NOT NULL UNIQUE,
            PRIMARY KEY(role_pk)
        );
        """        
    cursor.execute(q)
 
 
    ##############################    
    q = """
        CREATE TABLE users_roles (
            user_role_user_fk CHAR(36),
            user_role_role_fk CHAR(36),
            PRIMARY KEY(user_role_user_fk, user_role_role_fk)
        );
        """        
    cursor.execute(q)
    cursor.execute("ALTER TABLE users_roles ADD FOREIGN KEY (user_role_user_fk) REFERENCES users(user_pk) ON DELETE CASCADE ON UPDATE RESTRICT")
    cursor.execute("ALTER TABLE users_roles ADD FOREIGN KEY (user_role_role_fk) REFERENCES roles(role_pk) ON DELETE CASCADE ON UPDATE RESTRICT")
 
 
    ##############################
    cursor.execute("DROP TABLE IF EXISTS items")
    q = """
        CREATE TABLE items (
    item_pk CHAR(36),
    restaurant_fk CHAR(36),
    title VARCHAR(50),
    price DECIMAL(5,2),
    PRIMARY KEY(item_pk),
    FOREIGN KEY(restaurant_fk) REFERENCES users(user_pk)
    );
    """
    cursor.execute(q)
 
    ##############################
 
    # Create roles
 
    
    q = f"""
        INSERT INTO roles (role_pk, role_name)
        VALUES ("{x.ADMIN_ROLE_PK}", "admin"), ("{x.CUSTOMER_ROLE_PK}", "customer"),
        ("{x.PARTNER_ROLE_PK}", "partner"), ("{x.RESTAURANT_ROLE_PK}", "restaurant")
        """
    cursor.execute(q)
 
    ##############################
    # Create admin user
    user_pk = str(uuid.uuid4())
    user = {
        "user_pk" : user_pk,
        "user_name" : "Emil",
        "user_last_name" : "Abrahamson",
        "user_email" : "admin@fulldemo.com",
        "user_password" : generate_password_hash("password"),
        "user_avatar" : "profile_10.jpg",
        "user_created_at" : int(time.time()),
        "user_deleted_at" : 0,
        "user_blocked_at" : 0,
        "user_updated_at" : 0,
        "user_verified_at" : int(time.time()),
        "user_verification_key" : str(uuid.uuid4())
    }            
    insert_user(user)
    # Assign role to admin user
    q = f"""
        INSERT INTO users_roles (user_role_user_fk, user_role_role_fk) VALUES ("{user_pk}",
        "{x.ADMIN_ROLE_PK}")        
        """    
    cursor.execute(q)    
 
   ##############################
    # Create customer
    user_pk = 'aa699423-fa1b-4d30-810f-24c2ffafd54b'
    user = {
        "user_pk" : user_pk,
        "user_name" : "John",
        "user_last_name" : "Customer",
        "user_email" : "customer@fulldemo.com",
        "user_password" : generate_password_hash("password"),
        "user_avatar" : "profile_11.jpg",
        "user_created_at" : int(time.time()),
        "user_deleted_at" : 0,
        "user_blocked_at" : 0,
        "user_updated_at" : 0,
        "user_verified_at" : int(time.time()),
        "user_verification_key" : str(uuid.uuid4())
    }
    insert_user(user)
   
    # Assign role to customer user
    q = f"""
        INSERT INTO users_roles (user_role_user_fk, user_role_role_fk) VALUES ("{user_pk}",
        "{x.CUSTOMER_ROLE_PK}")        
        """    
    cursor.execute(q)
 
 
   ##############################
    # Create partner
    user_pk = str(uuid.uuid4())
    user = {
        "user_pk" : user_pk,
        "user_name" : "John",
        "user_last_name" : "Partner",
        "user_email" : "partner@fulldemo.com",
        "user_password" : generate_password_hash("password"),
        "user_avatar" : "profile_12.jpg",
        "user_created_at" : int(time.time()),
        "user_deleted_at" : 0,
        "user_blocked_at" : 0,
        "user_updated_at" : 0,
        "user_verified_at" : int(time.time()),
        "user_verification_key" : str(uuid.uuid4())
    }
    insert_user(user)
    # Assign role to partner user
    q = f"""
        INSERT INTO users_roles (user_role_user_fk, user_role_role_fk) VALUES ("{user_pk}",
        "{x.PARTNER_ROLE_PK}")        
        """    
    cursor.execute(q)
 
   ##############################
    # Create restaurant
    user_pk = str(uuid.uuid4())
    user = {
        "user_pk" : user_pk,
        "user_name" : "John",
        "user_last_name" : "Restaurant",
        "user_email" : "restaurant@fulldemo.com",
        "user_password" : generate_password_hash("password"),
        "user_avatar" : "profile_13.jpg",
        "user_created_at" : int(time.time()),
        "user_deleted_at" : 0,
        "user_blocked_at" : 0,
        "user_updated_at" : 0,
        "user_verified_at" : int(time.time()),
        "user_verification_key" : str(uuid.uuid4())
    }
    insert_user(user)
    
    # Assign role to restaurant user
    q = f"""
        INSERT INTO users_roles (user_role_user_fk, user_role_role_fk) VALUES ("{user_pk}",
        "{x.RESTAURANT_ROLE_PK}")        
        """    
    cursor.execute(q)
 
 
    ##############################
    # Create 50 customer
 
    domains = ["example.com", "testsite.org", "mydomain.net", "website.co", "fakemail.io", "gmail.com", "hotmail.com"]
    user_password = hashed_password = generate_password_hash("password")
    for _ in range(50):
        user_pk = str(uuid.uuid4())
        user_verified_at =  0 if random.choice([True, False]) else int(time.time())
        user = {
            "user_pk" : user_pk,
            "user_name" : fake.first_name(),
            "user_last_name" : fake.last_name(),
            "user_email" : fake.unique.user_name() + "@" + random.choice(domains),
            "user_password" : user_password,
            # user_password = hashed_password = generate_password_hash(fake.password(length=20))
            "user_avatar" : "profile_"+ str(random.randint(1, 100)) +".jpg",
            "user_created_at" : int(time.time()),
            "user_deleted_at" : 0,
            "user_blocked_at" : 0,
            "user_updated_at" : 0,
            "user_verified_at" : user_verified_at,
            "user_verification_key" : str(uuid.uuid4())
        }
 
        insert_user(user)
        cursor.execute("""INSERT INTO users_roles (
            user_role_user_fk,
            user_role_role_fk)
            VALUES (%s, %s)""", (user_pk, x.CUSTOMER_ROLE_PK))
 
 
   ##############################
    # Create 50 partners
 
    user_password = hashed_password = generate_password_hash("password")
    for _ in range(50):
        user_pk = str(uuid.uuid4())
        user_verified_at =  0 if random.choice([True, False]) else int(time.time())
        user = {
            "user_pk" : user_pk,
            "user_name" : fake.first_name(),
            "user_last_name" : fake.last_name(),
            "user_email" : fake.unique.email(),
            "user_password" : user_password,
            "user_avatar" : "profile_"+ str(random.randint(1, 100)) +".jpg",
            "user_created_at" : int(time.time()),
            "user_deleted_at" : 0,
            "user_blocked_at" : 0,
            "user_updated_at" : 0,
            "user_verified_at" : 0,
            "user_verification_key" : str(uuid.uuid4())
        }
 
        insert_user(user)
 
        cursor.execute("""
        INSERT INTO users_roles (
            user_role_user_fk,
            user_role_role_fk)
            VALUES (%s, %s)
        """, (user_pk, x.PARTNER_ROLE_PK))
 
    db.commit()
 
   ##############################
    # Create 50 restaurants
 
    user_password = hashed_password = generate_password_hash("password")
    for _ in range(50):
        user_pk = str(uuid.uuid4())
        user_verified_at =  0 if random.choice([True, False]) else int(time.time())
        user = {
            "user_pk" : user_pk,
            "user_name" : fake.first_name(),
            "user_last_name" : "",
            "user_email" : fake.unique.email(),
            "user_password" : user_password,
            "user_avatar" : "profile_"+ str(random.randint(1, 100)) +".jpg",
            "user_created_at" : int(time.time()),
            "user_deleted_at" : 0,
            "user_blocked_at" : 0,
            "user_updated_at" : 0,
            "user_verified_at" : user_verified_at,
            "user_verification_key" : str(uuid.uuid4())
        }
 
        insert_user(user)
 
        cursor.execute("""
        INSERT INTO users_roles (
            user_role_user_fk,
            user_role_role_fk)
            VALUES (%s, %s)
        """, (user_pk, x.RESTAURANT_ROLE_PK))
 
# Seed items only if the user is a restaurant
        if x.RESTAURANT_ROLE_PK:
            for _ in range(10):
                item_pk = str(uuid.uuid4())
                item = {
                    "item_pk": item_pk,
                    "restaurant_fk": user_pk,
                    "title": random.choice(food_names),
                    "price": round(random.uniform(5, 30))  # Random price between 5 and 30
                }
                insert_item(item)
 
    db.commit()
 
 
except Exception as ex:
    ic(ex)
    if "db" in locals(): db.rollback()
 
finally:
    if "cursor" in locals(): cursor.close()
    if "db" in locals(): db.close()