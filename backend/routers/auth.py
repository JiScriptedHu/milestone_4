from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
import json
import os

router = APIRouter()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
USERS_FILE = "users.json"

# -----------------------------
# Pydantic Models
# -----------------------------
class UserAuth(BaseModel):
    username: str
    password: str

# -----------------------------
# Helper Functions
# -----------------------------
def load_users() -> dict:
    """Load users from JSON file."""
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_users(users: dict):
    """Save users to JSON file."""
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

# -----------------------------
# API Endpoints
# -----------------------------
@router.post("/signup")
async def signup(user: UserAuth):
    """Register a new user."""
    users = load_users()
    if user.username in users:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    users[user.username] = {"password": get_password_hash(user.password)}
    save_users(users)
    
    return {"message": "User created successfully"}

@router.post("/login")
async def login(user: UserAuth):
    """Authenticate a user."""
    users = load_users()
    if user.username not in users:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    stored_password = users[user.username]["password"]
    if not verify_password(user.password, stored_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    # Note: Replace with real JWT token in production
    return {
        "message": "Login successful",
        "username": user.username,
        "token": "fake-jwt-token-for-demo"
    }