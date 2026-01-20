from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password. Bcrypt has a 72-byte limit, so we truncate if necessary."""
    # Always ensure password is within 72 bytes before passing to passlib
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Truncate to 72 bytes exactly
        password_bytes = password_bytes[:72]
        # Try to decode, but if it fails due to incomplete UTF-8 sequence, remove last bytes
        try:
            password = password_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # If we cut in the middle of a multi-byte character, remove bytes until valid
            while len(password_bytes) > 0:
                try:
                    password = password_bytes.decode('utf-8')
                    break
                except UnicodeDecodeError:
                    password_bytes = password_bytes[:-1]
            else:
                password = password_bytes.decode('utf-8', errors='replace')
    
    try:
        return pwd_context.hash(password)
    except (ValueError, TypeError) as e:
        # Catch passlib validation errors for password length
        error_msg = str(e)
        if "72 bytes" in error_msg or "password cannot be longer" in error_msg.lower():
            # Double-check byte length and truncate more aggressively if needed
            password_bytes = password.encode('utf-8')
            if len(password_bytes) > 71:  # Be conservative, use 71 instead of 72
                password_bytes = password_bytes[:71]
                try:
                    password = password_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    password = password_bytes.decode('utf-8', errors='replace')
                return pwd_context.hash(password)
        raise


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
