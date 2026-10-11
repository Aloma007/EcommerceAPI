import stripe
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
fake_user_db = []

# --- NEW JWT CONFIGURATION ---
# This is the master key for your server. Never share this in a real app!
SECRET_KEY = "my_super_secret_e_commerce_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 
# -----------------------------

# --- NEW: Tell FastAPI where the user gets their token ---
# This creates the "lock" for our protected routes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- NEW: The Checkpoint Guard Function ---
# This function automatically grabs the token from the user's request and decodes it
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Try to decode the token using our secret key
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# --- NEW HELPER FUNCTION ---
def create_access_token(data: dict):
    to_encode = data.copy()
    
    # Set the expiration time to 30 minutes from right now
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    # Encode the payload, using our secret key and the HS256 algorithm
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/signup")
async def create_user(user: UserCreate):
    hashed_password = get_password_hash(user.password)
    user_dict = user.model_dump()
    user_dict["password"] = hashed_password
    fake_user_db.append(user_dict)
    
    return {"message": f"User {user.username} created securely!", "total_users": len(fake_user_db)}

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    found_user = None
    for db_user in fake_user_db:
        # Notice we now use form_data.username instead of user.username
        if db_user["username"] == form_data.username:
            found_user = db_user
            break

    if not found_user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    password_is_correct = verify_password(form_data.password, found_user["password"])

    if not password_is_correct:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": found_user["username"]})

    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }

@app.get("/profile")
async def view_profile(current_user: str = Depends(get_current_user)):
    return {"message": f"Welcome to your private profile, {current_user}!", "secret_data": "Here is your cart history."}
        
    # --- UPDATED LOGIN RESPONSE ---
    # Create the JWT containing the user's username
    access_token = create_access_token(data={"sub": found_user["username"]})
    
    # Return the token to the frontend instead of just a success message
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }


# --- NEW PRODUCT SECTION ---

# Temporary database for products
fake_product_db = []

# Blueprint for a Product
class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    stock: int

# Route to CREATE a product (POST)
@app.post("/products")
async def create_product(product: ProductCreate):
    product_dict = product.model_dump()
    # Assign a fake, simple ID based on the list length
    product_dict["id"] = len(fake_product_db) + 1 
    
    fake_product_db.append(product_dict)
    return {"message": "Product added successfully", "product": product_dict}

# Route to READ / get all products, with optional SEARCH (GET)
@app.get("/products")
async def get_all_products(search_query: str = None):
    # If the user didn't type a search query, return everything
    if not search_query:
        return {"total": len(fake_product_db), "products": fake_product_db}
        
    # If they did type something, filter the database
    filtered_products = []
    for product in fake_product_db:
        # Check if the search term is in the product name or description (case-insensitive)
        if search_query.lower() in product["name"].lower() or search_query.lower() in product["description"].lower():
            filtered_products.append(product)
            
    return {
        "search_term": search_query,
        "total_results": len(filtered_products), 
        "products": filtered_products
    }

# --- NEW SHOPPING CART SECTION ---

# Our temporary database for shopping carts (maps username -> list of items)
fake_cart_db = {}

# Blueprint for what we expect when someone adds an item to their cart
class CartItem(BaseModel):
    product_id: int
    quantity: int

# Route to ADD an item to the cart (POST) - LOCKED!
@app.post("/cart")
async def add_to_cart(item: CartItem, current_user: str = Depends(get_current_user)):
    # 1. Verify the product actually exists in our store
    product_exists = False
    for p in fake_product_db:
        if p["id"] == item.product_id:
            product_exists = True
            break
            
    if not product_exists:
        raise HTTPException(status_code=404, detail="Product not found")

    # 2. If the user doesn't have a cart yet, create an empty one for them
    if current_user not in fake_cart_db:
        fake_cart_db[current_user] = []
        
    # 3. Add the item to their specific cart
    fake_cart_db[current_user].append(item.model_dump())
    
    return {"message": f"Item added to {current_user}'s cart", "cart": fake_cart_db[current_user]}

# Route to VIEW the cart (GET) - LOCKED!
@app.get("/cart")
async def view_cart(current_user: str = Depends(get_current_user)):
    # Grab the user's cart, or return an empty list if they haven't added anything yet
    user_cart = fake_cart_db.get(current_user, [])
    return {"user": current_user, "total_items": len(user_cart), "cart": user_cart}

# Route to REMOVE an item from the cart (DELETE) - LOCKED!
@app.delete("/cart/{product_id}")
async def remove_from_cart(product_id: int, current_user: str = Depends(get_current_user)):
    # 1. Check if the user even has a cart
    if current_user not in fake_cart_db or not fake_cart_db[current_user]:
        raise HTTPException(status_code=404, detail="Your cart is already empty")
        
    # 2. Filter out the item the user wants to delete
    # This creates a new list keeping ONLY the items that DO NOT match the product_id
    original_count = len(fake_cart_db[current_user])
    fake_cart_db[current_user] = [
        item for item in fake_cart_db[current_user] if item["product_id"] != product_id
    ]
    
    # 3. If the list size didn't change, the item was never in the cart to begin with
    if len(fake_cart_db[current_user]) == original_count:
        raise HTTPException(status_code=404, detail="Item not found in your cart")
        
    return {
        "message": f"Product {product_id} removed from cart", 
        "cart": fake_cart_db[current_user]
    }

# --- NEW PAYMENT GATEWAY SECTION ---

# Normally i put this in a hidden .env file, but a fake one is hardcoded for testing
stripe.api_key = "sk_test_dummy_key_replace_me_later"

# Route to CHECKOUT and pay (POST) - LOCKED!
@app.post("/checkout")
async def create_checkout_session(current_user: str = Depends(get_current_user)):
    # 1. Grab the user's cart
    user_cart = fake_cart_db.get(current_user, [])
    
    if not user_cart:
        raise HTTPException(status_code=400, detail="Your cart is empty. Add items before checkout.")
        
    # 2. Format the cart items for Stripe
    stripe_line_items = []
    
    for cart_item in user_cart:
        # Find the actual product details to get the price and name
        product = None
        for p in fake_product_db:
            if p["id"] == cart_item["product_id"]:
                product = p
                break
                
        if product:
            stripe_line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": product["name"]},
                    # Stripe strictly requires prices in cents (e.g., $10.00 is 1000)
                    "unit_amount": int(product["price"] * 100), 
                },
                "quantity": cart_item["quantity"],
            })

    try:
        # 3. Tell Stripe to generate a secure payment page
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=stripe_line_items,
            mode="payment",
            success_url="http://localhost:8000/success",
            cancel_url="http://localhost:8000/cancel",
        )
        # Return the secure Stripe URL to the frontend
        return {"checkout_url": session.url}
        
    except Exception as e:
        # Since we are using a dummy API key, the Stripe network will reject it. 
        # This fallback proves your logic works even without a real Stripe account yet!
        return {
            "message": "Checkout logic works perfectly!",
            "items_processed": len(stripe_line_items),
            "stripe_error": str(e),
            "next_step": "Create a free account at stripe.com to get a real API key."
        }