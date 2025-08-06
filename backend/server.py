from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import os
from decouple import config

# Import all route modules
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.integrations import router as integrations_router
from routes.ai_core import router as ai_core_router
from routes.notifications import router as notifications_router
from routes.payments import router as payments_router
from routes.guidelines import router as guidelines_router
from routes.emails import router as emails_router
from routes.calendar import router as calendar_router
from routes.analytics import router as analytics_router

# Database connection
mongodb_client = None
database = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global mongodb_client, database
    mongodb_client = AsyncIOMotorClient(config('MONGO_URL'))
    database = mongodb_client.jessica_ai
    app.mongodb_client = mongodb_client
    app.database = database
    
    # Test database connection
    try:
        await mongodb_client.admin.command('ismaster')
        print("✅ Connected to MongoDB successfully")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
    
    yield
    
    # Shutdown
    if mongodb_client:
        mongodb_client.close()
        print("📴 Disconnected from MongoDB")

# Initialize FastAPI app
app = FastAPI(
    title="Jessica AI Agent API",
    description="Comprehensive SAAS Platform for Productivity Automation",
    version="1.0.0",
    lifespan=lifespan
)

# Security
security = HTTPBearer()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        config('FRONTEND_URL', default="http://localhost:3000")
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Include all routers with proper prefixes
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users_router, prefix="/api/users", tags=["User Management"])
app.include_router(integrations_router, prefix="/api/integrations", tags=["Third-party Integrations"])
app.include_router(ai_core_router, prefix="/api/ai", tags=["AI Core Services"])
app.include_router(notifications_router, prefix="/api/notifications", tags=["Notification Services"])
app.include_router(payments_router, prefix="/api/payments", tags=["Payment & Credits"])
app.include_router(guidelines_router, prefix="/api/guidelines", tags=["User Guidelines"])
app.include_router(emails_router, prefix="/api/emails", tags=["Email Management"])
app.include_router(calendar_router, prefix="/api/calendar", tags=["Calendar Management"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics & Reporting"])

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Jessica AI Agent API",
        "version": "1.0.0",
        "database": "connected" if mongodb_client else "disconnected"
    }

@app.get("/api")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Jessica AI Agent API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )