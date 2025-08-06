from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from decouple import config
import secrets
import string

# Security configuration
JWT_SECRET_KEY = config('JWT_SECRET_KEY')
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(config('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', default=30))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def generate_verification_token() -> str:
    """Generate a secure verification token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def generate_reset_token() -> str:
    """Generate a secure password reset token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract and validate user ID from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_id

def create_reset_token_with_expiry(user_id: str, expires_in_hours: int = 1) -> tuple[str, datetime]:
    """Create a password reset token with expiry"""
    token = generate_reset_token()
    expiry = datetime.utcnow() + timedelta(hours=expires_in_hours)
    return token, expiry

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"

# OAuth utilities
def generate_oauth_state() -> str:
    """Generate OAuth state parameter for security"""
    return secrets.token_urlsafe(32)

def create_oauth_tokens(user_id: str, provider: str, access_token: str, 
                       refresh_token: str, expires_at: datetime) -> Dict[str, Any]:
    """Create standardized OAuth token storage format"""
    return {
        "user_id": user_id,
        "provider": provider,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "created_at": datetime.utcnow()
    }

class TokenManager:
    """Centralized token management for various services"""
    
    @staticmethod
    def create_user_session(user_id: str, additional_claims: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a complete user session with JWT token"""
        token_data = {
            "sub": user_id,
            "type": "access_token"
        }
        
        if additional_claims:
            token_data.update(additional_claims)
        
        access_token = create_access_token(token_data)
        expires_in = JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "created_at": datetime.utcnow()
        }
    
    @staticmethod
    def decode_user_session(token: str) -> Dict[str, Any]:
        """Decode and validate user session token"""
        try:
            payload = verify_token(token)
            return {
                "user_id": payload.get("sub"),
                "token_type": payload.get("type"),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0)),
                "issued_at": datetime.fromtimestamp(payload.get("iat", 0))
            }
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )