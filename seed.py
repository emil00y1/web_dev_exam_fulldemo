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
    "[55.7039, 12.5700]", "[55.6542, 12.5115]", "[55.6105, 12.5312]", "[55.7891, 12.4401]",
    "[55.6587, 12.5859]", "[55.7103, 12.4915]", "[55.7519, 12.6132]", "[55.6743, 12.5923]",
    "[55.6228, 12.4469]", "[55.8357, 12.5420]", "[55.8062, 12.6011]", "[55.7768, 12.4662]",
    "[55.7420, 12.5015]", "[55.7073, 12.4541]", "[55.8314, 12.4943]", "[55.6874, 12.5319]",
    "[55.6675, 12.4820]", "[55.7946, 12.5733]", "[55.7327, 12.4114]", "[55.7510, 12.5385]",
    "[55.7689, 12.5007]", "[55.6806, 12.4984]", "[55.8147, 12.5230]", "[55.7496, 12.4618]",
    "[55.7701, 12.5935]", "[55.7872, 12.5156]", "[55.7611, 12.5468]", "[55.8023, 12.4912]",
    "[55.8141, 12.4685]", "[55.6735, 12.4534]", "[55.7864, 12.6019]", "[55.8219, 12.4352]",
    "[55.7432, 12.5756]", "[55.6779, 12.5062]", "[55.8057, 12.5770]", "[55.7613, 12.4584]",
    "[55.7954, 12.5252]", "[55.7812, 12.5628]", "[55.7318, 12.4494]", "[55.7695, 12.5426]",
    "[55.7608, 12.5901]", "[55.7999, 12.4997]", "[55.7570, 12.5263]", "[55.7257, 12.4698]",
    "[55.7388, 12.4887]", "[55.7562, 12.5775]", "[55.7987, 12.5571]", "[55.6801, 12.5612]",
    "[55.7619, 12.4537]", "[55.7321, 12.5166]", "[55.7945, 12.4831]", "[55.7523, 12.5765]",
    "[55.7119, 12.5538]", "[55.7746, 12.5642]", "[55.6931, 12.5486]", "[55.8112, 12.5353]",
    "[55.7481, 12.4824]", "[55.7457, 12.5242]", "[55.6848, 12.5130]", "[55.7897, 12.5201]",
    "[55.8119, 12.4962]", "[55.7538, 12.5567]", "[55.6992, 12.5669]", "[55.7586, 12.4794]",
    "[55.7175, 12.5367]", "[55.7851, 12.5349]", "[55.7407, 12.5708]", "[55.6725, 12.5461]",
    "[55.7638, 12.5023]", "[55.7102, 12.5238]", "[55.8193, 12.4749]", "[55.7665, 12.5722]",
    "[55.6868, 12.4671]", "[55.7075, 12.5845]", "[55.7430, 12.5123]", "[55.8159, 12.5228]",
    "[55.7499, 12.5623]", "[55.7917, 12.5664]", "[55.6679, 12.5165]", "[55.8068, 12.5472]",
    "[55.7315, 12.5321]", "[55.7503, 12.5905]", "[55.6797, 12.4758]", "[55.7474, 12.5583]",
    "[55.8135, 12.5136]", "[55.7908, 12.4916]", "[55.7580, 12.5527]", "[55.7338, 12.4729]",
    "[55.7687, 12.5094]", "[55.7206, 12.5158]", "[55.8272, 12.4951]", "[55.7826, 12.5788]",
    "[55.6949, 12.5317]", "[55.8054, 12.4691]", "[55.7643, 12.5387]", "[55.7820, 12.5206]",
    "[55.7426, 12.4845]", "[55.8098, 12.5615]", "[55.7817, 12.5674]", "[55.7479, 12.4948]"
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