from config import config  # Import your configuration
import x
import uuid
import time
import random
from werkzeug.security import generate_password_hash
from faker import Faker
 
fake = Faker()
 
from icecream import ic
ic.configureOutput(prefix=f'***** | ', includeContext=True)

def db():
    return mysql.connector.connect(**config.DB_CONFIG)
 
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

restaurant_names = [
    "Jackson's Grill", "Smith's Bistro", "Lakeview Tavern", "Sunset Café",
    "Harbor House", "Willow & Sage", "Rusty Spoon", "Golden Lantern",
    "Orchard Kitchen", "Mariner's Table", "Scarlet Fork", "Bayside Eatery",
    "Pine & Poppy", "Maple Leaf", "Meadowlark", "Juniper & Thyme",
    "Silver Birch", "Cedar & Stone", "Violet Grill", "Velvet Vine",
    "Oakwood Kitchen", "Foxglove Tavern", "Briarwood", "Aspen Table",
    "Azure Café", "Meadow Grill", "Riverbend", "Golden Stag", "Lavender Grove",
    "Crimson Chalet", "Elm & Ivy", "Seabreeze", "Jade Leaf", "Wildflower",
    "Summit Club", "Bluebell Bistro", "Coastal Bliss", "Morning Frost",
    "Autumn Grill", "Willow Glen", "Scarlet Lantern", "Sapphire Café",
    "Wild Iris", "Hickory Hearth", "Golden Prairie", "Amber Arch",
    "Banyan & Bramble", "Urban Oak", "Blossom Hill", "Wishing Well",
    "Rustic Lantern", "Juniper Clover", "Sunrise Bistro", "Ocean Pearl",
    "Cloverleaf", "Twisted Vine", "Harvest Glow", "Windmill Grill",
    "Vine & Velvet", "Copper Table", "Starry Night", "Golden Horizon",
    "Willow Arch", "Birch & Berry", "Painted Fern", "Horizon Table",
    "Serene Hearth", "Jade Café", "Redberry Retreat", "Cedar Lane",
    "Alpine Haven", "Fox & Fir", "Bramble & Bee", "Lunar Grove",
    "Pinecone Table", "Velvet Hearth", "Morning Glory", "Aurora Haven",
    "Golden Ember", "Seaside Café", "Mountain Ash", "Fern & Feather",
    "Sapphire Wave", "Autumn Glow", "Golden Iris", "Meadow Breeze",
    "Riverside Café", "Willowbrook", "Evergreen", "Amber Flame",
    "Silver Hollow", "Twilight Café", "Crimson Horizon", "Cedar Meadow"
]


coords_list = [
    "[55.6722, 12.5553]", "[55.6784, 12.5131]", "[55.6881, 12.5632]", "[55.7010, 12.5387]",  
    "[55.6678, 12.5609]", "[55.6802, 12.5963]", "[55.7101, 12.5672]", "[55.6950, 12.5843]", 
    "[55.7083, 12.5471]", "[55.6715, 12.5068]", "[55.6849, 12.5503]", "[55.7056, 12.5930]",  
    "[55.6934, 12.5124]", "[55.7112, 12.5867]", "[55.6661, 12.5394]", "[55.6865, 12.6041]", 
    "[55.7078, 12.5773]", "[55.6756, 12.5899]", "[55.7093, 12.5630]", "[55.6789, 12.5008]",  
    "[55.6698, 12.5923]", "[55.7134, 12.5205]", "[55.6745, 12.5777]", "[55.6807, 12.6151]",  
    "[55.6890, 12.4810]", "[55.7171, 12.6056]", "[55.7070, 12.4973]", "[55.6833, 12.6007]",  
    "[55.7108, 12.5661]", "[55.6654, 12.5032]", "[55.6902, 12.5725]", "[55.7076, 12.5852]",  
    "[55.6762, 12.5158]", "[55.6919, 12.5437]", "[55.6728, 12.5083]", "[55.7099, 12.6004]",  
    "[55.6800, 12.5943]", "[55.6753, 12.5586]", "[55.7021, 12.5700]", "[55.6923, 12.5484]", 
    "[55.7050, 12.5627]", "[55.6682, 12.5985]", "[55.6817, 12.5102]", "[55.7003, 12.6029]",  
    "[55.6711, 12.6073]", "[55.7142, 12.5558]", "[55.6786, 12.5244]", "[55.6869, 12.5977]"   
]



def insert_item(item):
    # Insert the item into the items table
    cursor.execute("""
        INSERT INTO items (item_pk, restaurant_fk, item_title, item_price, item_deleted_at, item_blocked_at, item_updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (item["item_pk"], item["restaurant_fk"], item["item_title"], item["item_price"],item["item_deleted_at"],item["item_blocked_at"], item["item_updated_at"]))

def insert_item_image(image):
    # Insert the item into the items table
    cursor.execute("""
        INSERT INTO items_image (item_fk, image)
        VALUES (%s, %s)
    """, (image["item_fk"], image["image"]))

def insert_coords(coord):
    try:
        cursor.execute("""
            INSERT INTO coords (coords_pk, coordinates, restaurant_fk)
            VALUES (%s, %s, %s)
        """, (coord["coords_pk"], coord["coordinates"], coord["restaurant_fk"]))
    except Exception as e:
        print(f"Error inserting coordinates: {e}")
 
 
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
    cursor.execute("DROP TABLE IF EXISTS items_image")
    cursor.execute("DROP TABLE IF EXISTS items")
    cursor.execute("DROP TABLE IF EXISTS coords")
 
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
            user_avatar VARCHAR(100),
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
    item_title VARCHAR(50),
    item_price DECIMAL(5,2),
    item_deleted_at INTEGER UNSIGNED,
    item_blocked_at INTEGER UNSIGNED,
    item_updated_at INTEGER UNSIGNED,
    PRIMARY KEY(item_pk),
    FOREIGN KEY(restaurant_fk) REFERENCES users(user_pk)
    );
    """
    cursor.execute(q)

    cursor.execute("DROP TABLE IF EXISTS items_image")
    q = """
        CREATE TABLE items_image (
    item_fk CHAR(36),
    image VARCHAR(100),
    FOREIGN KEY(item_fk) REFERENCES items(item_pk)
    );
    """
    cursor.execute(q)
 
    ##############################

    cursor.execute("DROP TABLE IF EXISTS coords")
    q = """
        CREATE TABLE coords (
    coords_pk CHAR(36),
    coordinates CHAR(100),
    restaurant_fk CHAR(36),
    PRIMARY KEY(coords_pk),
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
        "user_verification_key" : str(uuid.uuid4()),
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
            "user_name" : random.choice(restaurant_names),
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
                    "item_title": random.choice(food_names),
                    "item_price": round(random.uniform(5, 30)),  # Random price between 5 and 30
                    "item_deleted_at": 0,
                    "item_blocked_at": 0,
                    "item_updated_at": 0,
                }
                insert_item(item)



# Seed coords only if the user is a restaurant
        if x.RESTAURANT_ROLE_PK:
                coords_pk = str(uuid.uuid4())
                coord = {
                    "coords_pk": coords_pk,
                    "coordinates": random.choice(coords_list),
                    "restaurant_fk": user_pk,
                }
                insert_coords(coord)
                
 
    db.commit()

                
    cursor.execute("SELECT item_pk FROM items")
    items = cursor.fetchall()

    for item in items:  
        item_pk = item["item_pk"] 
        for _ in range(3):  # Generate and insert 3 images per item
            image = {
            "item_fk": item_pk,
            "image": "dish_" + str(random.randint(1, 100)) + ".jpg",
            }
        insert_item_image(image)  # Insert the image into the database

# Commit all changes after processing all items
    db.commit()


except Exception as ex:
    ic(ex)
    if "db" in locals(): db.rollback()
 
finally:
    if "cursor" in locals(): cursor.close()
    if "db" in locals(): db.close()