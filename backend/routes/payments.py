from fastapi import APIRouter, Depends, HTTPException, status, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import Optional, List
import stripe
from decouple import config

from models.payments import (
    Payment, CreditTransaction, Subscription, Invoice,
    CreatePaymentIntentRequest, PaymentIntentResponse, CreditPackageInfo,
    PaymentHistoryResponse, SubscriptionResponse, CreateSubscriptionRequest,
    UpdateSubscriptionRequest, UsageStatsResponse, CreditBalanceResponse,
    CreditPackage, PaymentStatus, CREDIT_COSTS
)
from models.user import CreditBalance
from utils.auth import get_current_user_id
from utils.database import ValidationUtils
from services.stripe_service import StripeService
from services.credit_service import CreditService

# Initialize Stripe
stripe.api_key = config('STRIPE_SECRET_KEY', default='sk_test_placeholder')

router = APIRouter()

@router.get("/packages", response_model=List[CreditPackageInfo])
async def get_credit_packages():
    """Get available credit packages"""
    packages = [
        CreditPackageInfo(
            package_type=CreditPackage.STARTER,
            credits=500,
            price_usd=9.99,
            price_per_credit=0.01998,
            description="Perfect for getting started with Jessica AI",
            features=[
                "500 email processing credits",
                "250 draft generations", 
                "Email classification and prioritization",
                "Basic scheduling assistance"
            ]
        ),
        CreditPackageInfo(
            package_type=CreditPackage.PROFESSIONAL,
            credits=2000,
            price_usd=29.99,
            price_per_credit=0.01499,
            description="For professionals who rely on email automation",
            features=[
                "2,000 email processing credits",
                "1,000 draft generations",
                "Advanced AI analysis",
                "Smart scheduling optimization",
                "Priority support"
            ]
        ),
        CreditPackageInfo(
            package_type=CreditPackage.ENTERPRISE,
            credits=10000,
            price_usd=99.99,
            price_per_credit=0.00999,
            description="Maximum automation for power users",
            features=[
                "10,000 email processing credits", 
                "5,000 draft generations",
                "Advanced analytics",
                "Custom automation rules",
                "Priority support",
                "Extended credit validity"
            ]
        )
    ]
    
    return packages

@router.post("/create-payment-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    payment_request: CreatePaymentIntentRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Create Stripe payment intent for credit purchase"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get package details
    package_info = {
        CreditPackage.STARTER: {"credits": 500, "price": 999},  # Price in cents
        CreditPackage.PROFESSIONAL: {"credits": 2000, "price": 2999},
        CreditPackage.ENTERPRISE: {"credits": 10000, "price": 9999}
    }
    
    if payment_request.package_type not in package_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid package type"
        )
    
    package = package_info[payment_request.package_type]
    
    try:
        # Initialize Stripe service
        stripe_service = StripeService()
        
        # Get or create Stripe customer
        user = await database.users.find_one({"id": current_user_id})
        customer_id = await stripe_service.get_or_create_customer(user)
        
        # Create payment intent
        payment_intent = await stripe_service.create_payment_intent(
            amount=package["price"],
            customer_id=customer_id,
            metadata={
                "user_id": current_user_id,
                "package_type": payment_request.package_type,
                "credits": package["credits"]
            }
        )
        
        # Create payment record
        payment = Payment(
            user_id=current_user_id,
            stripe_payment_intent_id=payment_intent.id,
            amount_usd=package["price"] / 100,
            package_type=payment_request.package_type,
            credits_purchased=package["credits"],
            stripe_customer_id=customer_id,
            status=PaymentStatus.PENDING
        )
        
        await database.payments.insert_one(payment.dict())
        
        return PaymentIntentResponse(
            payment_intent_id=payment_intent.id,
            client_secret=payment_intent.client_secret,
            amount=package["price"] / 100,
            credits=package["credits"],
            status=PaymentStatus.PENDING
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment intent: {str(e)}"
        )

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    database: AsyncIOMotorDatabase = request.app.database
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, 
            sig_header, 
            config('STRIPE_WEBHOOK_SECRET', default='whsec_placeholder')
        )
        
        # Initialize services
        stripe_service = StripeService()
        credit_service = CreditService(database)
        
        # Handle different event types
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            await handle_payment_success(
                database, 
                payment_intent, 
                credit_service
            )
        
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            await handle_payment_failure(
                database, 
                payment_intent
            )
        
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            await handle_subscription_payment(
                database,
                invoice,
                credit_service
            )
        
        return {"status": "success"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload"
        )
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )

@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's current credit balance"""
    database: AsyncIOMotorDatabase = request.app.database
    
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    credits = user.get("credits", {})
    credit_balance = CreditBalance(**credits)
    
    return CreditBalanceResponse(
        total_credits=credit_balance.total_credits,
        used_credits=credit_balance.used_credits,
        remaining_credits=credit_balance.remaining_credits,
        last_purchase_date=credit_balance.last_purchase_date,
        credit_expiry_date=credit_balance.credit_expiry_date,
        needs_refill=credit_balance.remaining_credits < 50
    )

@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    request: Request,
    page: int = 1,
    limit: int = 50,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's payment and transaction history"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get payments
    skip = (page - 1) * limit
    payments = await database.payments.find({"user_id": current_user_id})\
        .sort("created_at", -1)\
        .skip(skip)\
        .limit(limit)\
        .to_list(None)
    
    # Get credit transactions
    transactions = await database.credit_transactions.find({"user_id": current_user_id})\
        .sort("created_at", -1)\
        .skip(skip)\
        .limit(limit)\
        .to_list(None)
    
    # Get total count
    total_count = await database.payments.count_documents({"user_id": current_user_id})
    
    # Convert to response format
    payment_objects = []
    for payment in payments:
        payment_data = ValidationUtils.convert_objectid_to_str(payment)
        payment_objects.append(Payment(**payment_data))
    
    transaction_objects = []
    for transaction in transactions:
        transaction_data = ValidationUtils.convert_objectid_to_str(transaction)
        transaction_objects.append(CreditTransaction(**transaction_data))
    
    return PaymentHistoryResponse(
        payments=payment_objects,
        transactions=transaction_objects,
        total_count=total_count,
        page=page,
        limit=limit
    )

@router.get("/usage-stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    request: Request,
    days: int = 30,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get credit usage statistics"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Get user credits info
    user = await database.users.find_one({"id": current_user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    credits = user.get("credits", {})
    
    # Get usage by action type
    usage_by_action = await database.credit_transactions.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "transaction_type": "usage"
            }
        },
        {
            "$group": {
                "_id": "$action_type",
                "total_credits": {"$sum": {"$abs": "$credits_amount"}}
            }
        }
    ]).to_list(None)
    
    # Get usage by month
    usage_by_month = await database.credit_transactions.aggregate([
        {
            "$match": {
                "user_id": current_user_id,
                "transaction_type": "usage"
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m",
                        "date": "$created_at"
                    }
                },
                "total_credits": {"$sum": {"$abs": "$credits_amount"}}
            }
        },
        {"$sort": {"_id": 1}}
    ]).to_list(None)
    
    # Calculate daily average
    total_days = max(days, 1)
    total_used = credits.get("used_credits", 0)
    average_daily_usage = total_used / total_days
    
    # Project monthly usage
    projected_monthly_usage = int(average_daily_usage * 30)
    
    return UsageStatsResponse(
        total_credits_purchased=credits.get("total_credits", 0),
        total_credits_used=credits.get("used_credits", 0),
        credits_remaining=credits.get("remaining_credits", 0),
        usage_by_action={stat["_id"]: stat["total_credits"] for stat in usage_by_action},
        usage_by_month={stat["_id"]: stat["total_credits"] for stat in usage_by_month},
        average_daily_usage=average_daily_usage,
        projected_monthly_usage=projected_monthly_usage
    )

@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_user_subscriptions(
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's active subscriptions"""
    database: AsyncIOMotorDatabase = request.app.database
    
    subscriptions = await database.subscriptions.find({"user_id": current_user_id})\
        .sort("created_at", -1)\
        .to_list(None)
    
    subscription_responses = []
    for subscription in subscriptions:
        subscription_data = ValidationUtils.convert_objectid_to_str(subscription)
        subscription_responses.append(SubscriptionResponse(**subscription_data))
    
    return subscription_responses

@router.post("/subscriptions", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_request: CreateSubscriptionRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Create a new subscription"""
    database: AsyncIOMotorDatabase = request.app.database
    
    try:
        # Initialize Stripe service
        stripe_service = StripeService()
        
        # Get user
        user = await database.users.find_one({"id": current_user_id})
        customer_id = await stripe_service.get_or_create_customer(user)
        
        # Create Stripe subscription
        stripe_subscription = await stripe_service.create_subscription(
            customer_id=customer_id,
            price_id=subscription_request.price_id,
            payment_method_id=subscription_request.payment_method_id
        )
        
        # Create subscription record
        subscription = Subscription(
            user_id=current_user_id,
            stripe_subscription_id=stripe_subscription.id,
            stripe_customer_id=customer_id,
            stripe_price_id=subscription_request.price_id,
            plan_name="Jessica AI Pro",  # This would come from price data
            credits_per_period=2000,  # This would come from price metadata
            amount_usd=29.99,  # This would come from price data
            current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end)
        )
        
        await database.subscriptions.insert_one(subscription.dict())
        
        return SubscriptionResponse(**subscription.dict())
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create subscription: {str(e)}"
        )

@router.patch("/subscriptions/{subscription_id}")
async def update_subscription(
    subscription_id: str,
    subscription_update: UpdateSubscriptionRequest,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Update subscription settings"""
    database: AsyncIOMotorDatabase = request.app.database
    
    # Find subscription
    subscription = await database.subscriptions.find_one({
        "id": subscription_id,
        "user_id": current_user_id
    })
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    try:
        # Initialize Stripe service
        stripe_service = StripeService()
        
        # Update Stripe subscription
        if subscription_update.cancel_at_period_end is not None:
            await stripe_service.update_subscription(
                subscription["stripe_subscription_id"],
                cancel_at_period_end=subscription_update.cancel_at_period_end
            )
        
        # Update local record
        update_fields = {}
        if subscription_update.cancel_at_period_end is not None:
            update_fields["cancel_at_period_end"] = subscription_update.cancel_at_period_end
        if subscription_update.cancel_at_period_end:
            update_fields["canceled_at"] = datetime.utcnow()
        
        if update_fields:
            await database.subscriptions.update_one(
                {"id": subscription_id},
                {"$set": update_fields}
            )
        
        return {"message": "Subscription updated successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update subscription: {str(e)}"
        )

@router.get("/credit-costs")
async def get_credit_costs():
    """Get current credit costs for different actions"""
    return {
        "credit_costs": CREDIT_COSTS,
        "description": {
            "email_processing": "Analyze and classify an email",
            "draft_generation": "Generate AI draft response",
            "calendar_analysis": "Analyze calendar event for optimization", 
            "urgent_notification": "Send urgent SMS/WhatsApp notification",
            "smart_scheduling": "Get AI scheduling suggestions",
            "ai_analysis": "General AI analysis tasks",
            "auto_reply": "Send automated email reply",
            "meeting_scheduling": "Schedule meeting automatically"
        }
    }

# Helper functions for webhook handling
async def handle_payment_success(
    database: AsyncIOMotorDatabase,
    payment_intent: dict,
    credit_service: CreditService
):
    """Handle successful payment"""
    try:
        # Find payment record
        payment = await database.payments.find_one({
            "stripe_payment_intent_id": payment_intent["id"]
        })
        
        if not payment:
            print(f"Payment not found for intent: {payment_intent['id']}")
            return
        
        # Update payment status
        await database.payments.update_one(
            {"stripe_payment_intent_id": payment_intent["id"]},
            {
                "$set": {
                    "status": PaymentStatus.SUCCEEDED,
                    "paid_at": datetime.utcnow()
                }
            }
        )
        
        # Add credits to user account
        await credit_service.add_credits(
            user_id=payment["user_id"],
            credits=payment["credits_purchased"],
            transaction_type="purchase",
            description=f"Credit purchase - {payment['package_type']}",
            payment_intent_id=payment_intent["id"]
        )
        
        print(f"Successfully processed payment for user {payment['user_id']}")
        
    except Exception as e:
        print(f"Failed to handle payment success: {e}")

async def handle_payment_failure(
    database: AsyncIOMotorDatabase,
    payment_intent: dict
):
    """Handle failed payment"""
    try:
        # Update payment status
        await database.payments.update_one(
            {"stripe_payment_intent_id": payment_intent["id"]},
            {
                "$set": {
                    "status": PaymentStatus.FAILED,
                    "failure_reason": payment_intent.get("last_payment_error", {}).get("message"),
                    "failure_code": payment_intent.get("last_payment_error", {}).get("code")
                }
            }
        )
        
        print(f"Payment failed for intent: {payment_intent['id']}")
        
    except Exception as e:
        print(f"Failed to handle payment failure: {e}")

async def handle_subscription_payment(
    database: AsyncIOMotorDatabase,
    invoice: dict,
    credit_service: CreditService
):
    """Handle subscription payment success"""
    try:
        # Find subscription
        subscription = await database.subscriptions.find_one({
            "stripe_customer_id": invoice["customer"]
        })
        
        if not subscription:
            print(f"Subscription not found for customer: {invoice['customer']}")
            return
        
        # Add monthly credits
        await credit_service.add_credits(
            user_id=subscription["user_id"],
            credits=subscription["credits_per_period"],
            transaction_type="subscription",
            description=f"Monthly subscription credits - {subscription['plan_name']}",
            stripe_invoice_id=invoice["id"]
        )
        
        print(f"Added subscription credits for user {subscription['user_id']}")
        
    except Exception as e:
        print(f"Failed to handle subscription payment: {e}")