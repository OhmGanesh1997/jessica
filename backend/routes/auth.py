from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional
import httpx
from decouple import config

from models.user import (
    User, UserRegistrationRequest, UserLoginRequest, TokenResponse, 
    UserResponse, PasswordResetRequest, PasswordResetConfirm,
    UserProfile, UserPreferences
)
from utils.auth import (
    verify_password, get_password_hash, create_access_token, 
    verify_token, generate_verification_token, generate_reset_token,
    validate_password_strength, generate_oauth_state, security
)
from utils.database import ValidationUtils

router = APIRouter()

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegistrationRequest, request: Request):
    """Register a new user"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Check if user already exists
    existing_user = await database.users.find_one({"email": user_data.email.lower()})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password strength
    is_strong, message = validate_password_strength(user_data.password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Create user profile
    profile = UserProfile(
        full_name=user_data.full_name,
        job_title=user_data.job_title,
        company=user_data.company
    )
    
    # Create new user
    verification_token = generate_verification_token()
    user = User(
        email=user_data.email.lower(),
        hashed_password=get_password_hash(user_data.password),
        profile=profile,
        verification_token=verification_token
    )
    
    # Insert user into database
    result = await database.users.insert_one(user.dict())
    
    if not result.inserted_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    
    # Convert user to response format
    user_response = UserResponse(**user.dict())
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=1800,  # 30 minutes
        user=user_response
    )

@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLoginRequest, request: Request):
    """Login user with email and password"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Find user by email
    user_data = await database.users.find_one({"email": user_credentials.email.lower()})
    
    if not user_data or not verify_password(user_credentials.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user_data.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Update last login
    await database.users.update_one(
        {"_id": user_data["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create access token
    access_token = create_access_token(data={"sub": user_data["id"], "email": user_data["email"]})
    
    # Convert user to response format
    user_response = UserResponse(**ValidationUtils.convert_objectid_to_str(user_data))
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer", 
        expires_in=1800,
        user=user_response
    )

@router.post("/forgot-password")
async def forgot_password(reset_request: PasswordResetRequest, request: Request):
    """Request password reset"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Find user by email
    user = await database.users.find_one({"email": reset_request.email.lower()})
    
    if not user:
        # Don't reveal if email exists or not for security
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = generate_reset_token()
    reset_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Update user with reset token
    await database.users.update_one(
        {"email": reset_request.email.lower()},
        {
            "$set": {
                "reset_password_token": reset_token,
                "reset_password_expires": reset_expires
            }
        }
    )
    
    # TODO: Send email with reset link
    # For now, return success message
    return {"message": "If the email exists, a reset link has been sent"}

@router.post("/reset-password")
async def reset_password(reset_data: PasswordResetConfirm, request: Request):
    """Reset password using reset token"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Find user by reset token
    user = await database.users.find_one({
        "reset_password_token": reset_data.token,
        "reset_password_expires": {"$gt": datetime.utcnow()}
    })
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Validate new password
    is_strong, message = validate_password_strength(reset_data.new_password)
    if not is_strong:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Update password and clear reset token
    hashed_password = get_password_hash(reset_data.new_password)
    await database.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "hashed_password": hashed_password,
                "updated_at": datetime.utcnow()
            },
            "$unset": {
                "reset_password_token": "",
                "reset_password_expires": ""
            }
        }
    )
    
    return {"message": "Password reset successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user information"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Verify token and get user ID
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    
    # Find user in database
    user = await database.users.find_one({"id": user_id})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**ValidationUtils.convert_objectid_to_str(user))

@router.post("/verify-email")
async def verify_email(token: str, request: Request):
    """Verify user email address"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Find user by verification token
    user = await database.users.find_one({"verification_token": token})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    # Update user as verified
    await database.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "is_verified": True,
                "updated_at": datetime.utcnow()
            },
            "$unset": {"verification_token": ""}
        }
    )
    
    return {"message": "Email verified successfully"}

# OAuth Routes
@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth login"""
    client_id = config('GOOGLE_CLIENT_ID')
    redirect_uri = config('GOOGLE_REDIRECT_URI')
    
    state = generate_oauth_state()
    
    # Store state in session/cache for validation
    # TODO: Implement state storage
    
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid email profile https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/calendar.readonly"
        f"&state={state}"
        "&access_type=offline"
        "&prompt=consent"
    )
    
    return {"auth_url": auth_url}

@router.get("/google/callback")
async def google_callback(code: str, state: str, request: Request):
    """Handle Google OAuth callback"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # TODO: Validate state parameter
    
    client_id = config('GOOGLE_CLIENT_ID')
    client_secret = config('GOOGLE_CLIENT_SECRET')
    redirect_uri = config('GOOGLE_REDIRECT_URI')
    
    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
    
    # Get user info from Google
    access_token = tokens["access_token"]
    async with httpx.AsyncClient() as client:
        user_info_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info_response.raise_for_status()
        google_user = user_info_response.json()
    
    # Find or create user
    user = await database.users.find_one({"email": google_user["email"]})
    
    if user:
        # Update Google tokens
        await database.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "connections.google_connected": True,
                    "connections.google_access_token": access_token,
                    "connections.google_refresh_token": tokens.get("refresh_token"),
                    "connections.google_token_expiry": datetime.utcnow() + timedelta(seconds=tokens["expires_in"]),
                    "last_login": datetime.utcnow()
                }
            }
        )
    else:
        # Create new user from Google profile
        profile = UserProfile(
            full_name=google_user["name"],
            avatar_url=google_user.get("picture")
        )
        
        user = User(
            email=google_user["email"],
            hashed_password="",  # No password for OAuth users
            profile=profile,
            is_verified=True
        )
        user.connections.google_connected = True
        user.connections.google_access_token = access_token
        user.connections.google_refresh_token = tokens.get("refresh_token")
        user.connections.google_token_expiry = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
        
        await database.users.insert_one(user.dict())
    
    # Create JWT token
    jwt_token = create_access_token(data={"sub": user["id"] if user else user.id, "email": google_user["email"]})
    
    # Redirect to frontend with token
    frontend_url = config('FRONTEND_URL', default="http://localhost:3000")
    return {
        "message": "Google authentication successful",
        "access_token": jwt_token,
        "redirect_url": f"{frontend_url}/auth/callback?token={jwt_token}"
    }

@router.get("/microsoft/login")
async def microsoft_login(request: Request):
    """Initiate Microsoft OAuth login"""
    client_id = config('MICROSOFT_CLIENT_ID')
    redirect_uri = config('MICROSOFT_REDIRECT_URI')
    
    state = generate_oauth_state()
    
    auth_url = (
        "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid email profile https://graph.microsoft.com/mail.read "
        "https://graph.microsoft.com/calendars.readwrite offline_access"
        f"&state={state}"
        "&prompt=consent"
    )
    
    return {"auth_url": auth_url}

@router.get("/microsoft/callback")
async def microsoft_callback(code: str, state: str, request: Request):
    """Handle Microsoft OAuth callback"""
    database: AsyncIOMotorDatabase = request.app.database
    
    client_id = config('MICROSOFT_CLIENT_ID')
    client_secret = config('MICROSOFT_CLIENT_SECRET')
    redirect_uri = config('MICROSOFT_REDIRECT_URI')
    
    # Exchange code for tokens
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
    
    # Get user info from Microsoft Graph
    access_token = tokens["access_token"]
    async with httpx.AsyncClient() as client:
        user_info_response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info_response.raise_for_status()
        microsoft_user = user_info_response.json()
    
    # Find or create user (similar to Google flow)
    user = await database.users.find_one({"email": microsoft_user["userPrincipalName"]})
    
    if user:
        # Update Microsoft tokens
        await database.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "connections.microsoft_connected": True,
                    "connections.microsoft_access_token": access_token,
                    "connections.microsoft_refresh_token": tokens.get("refresh_token"),
                    "connections.microsoft_token_expiry": datetime.utcnow() + timedelta(seconds=tokens["expires_in"]),
                    "last_login": datetime.utcnow()
                }
            }
        )
    else:
        # Create new user from Microsoft profile
        profile = UserProfile(
            full_name=microsoft_user["displayName"]
        )
        
        user = User(
            email=microsoft_user["userPrincipalName"],
            hashed_password="",
            profile=profile,
            is_verified=True
        )
        user.connections.microsoft_connected = True
        user.connections.microsoft_access_token = access_token
        user.connections.microsoft_refresh_token = tokens.get("refresh_token")
        user.connections.microsoft_token_expiry = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])
        
        await database.users.insert_one(user.dict())
    
    # Create JWT token
    jwt_token = create_access_token(data={"sub": user["id"] if user else user.id, "email": microsoft_user["userPrincipalName"]})
    
    # Redirect to frontend with token
    frontend_url = config('FRONTEND_URL', default="http://localhost:3000")
    return {
        "message": "Microsoft authentication successful",
        "access_token": jwt_token,
        "redirect_url": f"{frontend_url}/auth/callback?token={jwt_token}"
    }

@router.post("/logout")
async def logout(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user (invalidate token)"""
    # In a production environment, you would add the token to a blacklist
    # For now, just return success as JWTs are stateless
    
    return {"message": "Logged out successfully"}

@router.post("/refresh-token")
async def refresh_token(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Refresh JWT access token"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Verify current token
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    
    # Find user
    user = await database.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Create new token
    new_token = create_access_token(data={"sub": user_id, "email": user["email"]})
    
    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": 1800
    }