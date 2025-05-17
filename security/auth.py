from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
from typing import Optional, List

from api.schemas import TokenData, User

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "replace_with_secure_random_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "tasks:read": "Read tasks",
        "tasks:write": "Create and modify tasks",
        "admin": "Admin access",
    },
)

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Mock user database - in production, this would be a real database
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@example.com",
        "hashed_password": pwd_context.hash("admin"),
        "disabled": False,
        "scopes": ["tasks:read", "tasks:write", "admin"],
    },
    "user": {
        "username": "user",
        "full_name": "Regular User",
        "email": "user@example.com",
        "hashed_password": pwd_context.hash("user"),
        "disabled": False,
        "scopes": ["tasks:read", "tasks:write"],
    },
    "readonly": {
        "username": "readonly",
        "full_name": "Read Only User",
        "email": "readonly@example.com",
        "hashed_password": pwd_context.hash("readonly"),
        "disabled": False,
        "scopes": ["tasks:read"],
    },
}


def verify_password(plain_password, hashed_password):
    """
    Verify a password against a hash.
    
    Args:
        plain_password (str): Plain text password
        hashed_password (str): Hashed password
        
    Returns:
        bool: True if password matches hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    """
    Hash a password.
    
    Args:
        password (str): Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def get_user(db, username: str):
    """
    Get a user from the database.
    
    Args:
        db: Database connection
        username (str): Username to look up
        
    Returns:
        User: User object if found, None otherwise
    """
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return User(**user_dict)


def authenticate_user(db, username: str, password: str):
    """
    Authenticate a user.
    
    Args:
        db: Database connection
        username (str): Username to authenticate
        password (str): Password to verify
        
    Returns:
        User: User object if authentication successful, False otherwise
    """
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, fake_users_db[username]["hashed_password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token.
    
    Args:
        data (dict): Data to encode in the token
        expires_delta (timedelta, optional): Token expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(security_scopes: SecurityScopes, token: str = Depends(oauth2_scheme)):
    """
    Get the current user from a JWT token.
    
    Args:
        security_scopes (SecurityScopes): Required security scopes
        token (str): JWT token
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If authentication fails
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except (JWTError, ValidationError):
        logger.error("JWT validation error", exc_info=True)
        raise credentials_exception
        
    user = get_user(None, username=token_data.username)
    if user is None:
        raise credentials_exception
        
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: {scope}",
                headers={"WWW-Authenticate": authenticate_value},
            )
            
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    Get the current active user.
    
    Args:
        current_user (User): Current user
        
    Returns:
        User: Current active user
        
    Raises:
        HTTPException: If user is disabled
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
