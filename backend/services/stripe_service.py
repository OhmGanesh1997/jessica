import stripe
from typing import Dict, Any, Optional
from datetime import datetime
from decouple import config

class StripeService:
    """Service for Stripe payment processing"""
    
    def __init__(self):
        stripe.api_key = config('STRIPE_SECRET_KEY', default='sk_test_placeholder')
        self.webhook_secret = config('STRIPE_WEBHOOK_SECRET', default='whsec_placeholder')
    
    async def get_or_create_customer(self, user: Dict[str, Any]) -> str:
        """Get existing Stripe customer or create new one"""
        
        try:
            # Check if user already has Stripe customer ID
            if user.get("stripe_customer_id"):
                try:
                    # Verify customer exists
                    customer = stripe.Customer.retrieve(user["stripe_customer_id"])
                    return customer.id
                except stripe.error.InvalidRequestError:
                    # Customer doesn't exist, create new one
                    pass
            
            # Create new customer
            customer = stripe.Customer.create(
                email=user["email"],
                name=user.get("profile", {}).get("full_name", ""),
                metadata={
                    "user_id": user["id"],
                    "created_by": "jessica_ai"
                }
            )
            
            return customer.id
            
        except Exception as e:
            print(f"Stripe customer error: {e}")
            raise Exception(f"Failed to get/create Stripe customer: {str(e)}")
    
    async def create_payment_intent(
        self,
        amount: int,  # Amount in cents
        customer_id: str,
        currency: str = "usd",
        metadata: Dict[str, Any] = None
    ) -> stripe.PaymentIntent:
        """Create Stripe payment intent"""
        
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                metadata=metadata or {},
                automatic_payment_methods={"enabled": True},
                receipt_email=None  # Will use customer email
            )
            
            return payment_intent
            
        except Exception as e:
            print(f"Payment intent creation error: {e}")
            raise Exception(f"Failed to create payment intent: {str(e)}")
    
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        payment_method_id: str,
        metadata: Dict[str, Any] = None
    ) -> stripe.Subscription:
        """Create Stripe subscription"""
        
        try:
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                default_payment_method=payment_method_id,
                metadata=metadata or {},
                expand=['latest_invoice.payment_intent']
            )
            
            return subscription
            
        except Exception as e:
            print(f"Subscription creation error: {e}")
            raise Exception(f"Failed to create subscription: {str(e)}")
    
    async def update_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: Optional[bool] = None,
        new_price_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> stripe.Subscription:
        """Update Stripe subscription"""
        
        try:
            update_params = {}
            
            if cancel_at_period_end is not None:
                update_params["cancel_at_period_end"] = cancel_at_period_end
            
            if new_price_id:
                # Get current subscription
                subscription = stripe.Subscription.retrieve(subscription_id)
                
                # Update subscription items
                update_params["items"] = [{
                    "id": subscription.items.data[0].id,
                    "price": new_price_id
                }]
            
            if metadata:
                update_params["metadata"] = metadata
            
            if update_params:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    **update_params
                )
                return subscription
            
            # If no updates, just return current subscription
            return stripe.Subscription.retrieve(subscription_id)
            
        except Exception as e:
            print(f"Subscription update error: {e}")
            raise Exception(f"Failed to update subscription: {str(e)}")
    
    async def cancel_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Cancel Stripe subscription immediately"""
        
        try:
            subscription = stripe.Subscription.delete(subscription_id)
            return subscription
            
        except Exception as e:
            print(f"Subscription cancellation error: {e}")
            raise Exception(f"Failed to cancel subscription: {str(e)}")
    
    async def get_customer_payment_methods(self, customer_id: str) -> Dict[str, Any]:
        """Get customer's payment methods"""
        
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            
            return {
                "payment_methods": [
                    {
                        "id": pm.id,
                        "type": pm.type,
                        "card": {
                            "brand": pm.card.brand,
                            "last4": pm.card.last4,
                            "exp_month": pm.card.exp_month,
                            "exp_year": pm.card.exp_year
                        } if pm.type == "card" else None,
                        "created": pm.created
                    } for pm in payment_methods.data
                ]
            }
            
        except Exception as e:
            print(f"Payment methods retrieval error: {e}")
            return {"payment_methods": []}
    
    async def create_setup_intent(self, customer_id: str) -> stripe.SetupIntent:
        """Create setup intent for saving payment method"""
        
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=["card"],
                usage="off_session"
            )
            
            return setup_intent
            
        except Exception as e:
            print(f"Setup intent creation error: {e}")
            raise Exception(f"Failed to create setup intent: {str(e)}")
    
    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Get invoice details"""
        
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            
            return {
                "id": invoice.id,
                "number": invoice.number,
                "status": invoice.status,
                "amount_due": invoice.amount_due,
                "amount_paid": invoice.amount_paid,
                "currency": invoice.currency,
                "created": invoice.created,
                "due_date": invoice.due_date,
                "period_start": invoice.period_start,
                "period_end": invoice.period_end,
                "pdf_url": invoice.invoice_pdf,
                "hosted_url": invoice.hosted_invoice_url,
                "customer_id": invoice.customer
            }
            
        except Exception as e:
            print(f"Invoice retrieval error: {e}")
            return {"error": str(e)}
    
    async def get_customer_invoices(
        self,
        customer_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get customer's invoices"""
        
        try:
            invoices = stripe.Invoice.list(
                customer=customer_id,
                limit=limit
            )
            
            return {
                "invoices": [
                    {
                        "id": invoice.id,
                        "number": invoice.number,
                        "status": invoice.status,
                        "amount_due": invoice.amount_due,
                        "amount_paid": invoice.amount_paid,
                        "currency": invoice.currency,
                        "created": invoice.created,
                        "due_date": invoice.due_date,
                        "pdf_url": invoice.invoice_pdf,
                        "hosted_url": invoice.hosted_invoice_url
                    } for invoice in invoices.data
                ]
            }
            
        except Exception as e:
            print(f"Customer invoices retrieval error: {e}")
            return {"invoices": []}
    
    async def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> Dict[str, Any]:
        """Create Stripe billing portal session"""
        
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url
            )
            
            return {
                "url": session.url,
                "created": session.created
            }
            
        except Exception as e:
            print(f"Billing portal creation error: {e}")
            raise Exception(f"Failed to create billing portal: {str(e)}")
    
    async def construct_webhook_event(
        self,
        payload: bytes,
        signature: str
    ) -> stripe.Event:
        """Construct and verify Stripe webhook event"""
        
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            
            return event
            
        except ValueError as e:
            print(f"Invalid payload: {e}")
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            print(f"Invalid signature: {e}")
            raise Exception("Invalid signature")
    
    async def get_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """Get payment intent details"""
        
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            return {
                "id": payment_intent.id,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "status": payment_intent.status,
                "customer": payment_intent.customer,
                "metadata": payment_intent.metadata,
                "created": payment_intent.created,
                "last_payment_error": {
                    "code": payment_intent.last_payment_error.code,
                    "message": payment_intent.last_payment_error.message,
                    "type": payment_intent.last_payment_error.type
                } if payment_intent.last_payment_error else None
            }
            
        except Exception as e:
            print(f"Payment intent retrieval error: {e}")
            return {"error": str(e)}
    
    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription details"""
        
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            return {
                "id": subscription.id,
                "status": subscription.status,
                "customer": subscription.customer,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "canceled_at": subscription.canceled_at,
                "trial_start": subscription.trial_start,
                "trial_end": subscription.trial_end,
                "metadata": subscription.metadata,
                "items": [
                    {
                        "id": item.id,
                        "price": {
                            "id": item.price.id,
                            "unit_amount": item.price.unit_amount,
                            "currency": item.price.currency,
                            "recurring": {
                                "interval": item.price.recurring.interval,
                                "interval_count": item.price.recurring.interval_count
                            } if item.price.recurring else None
                        },
                        "quantity": item.quantity
                    } for item in subscription.items.data
                ]
            }
            
        except Exception as e:
            print(f"Subscription retrieval error: {e}")
            return {"error": str(e)}
    
    async def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create refund for payment intent"""
        
        try:
            refund_params = {"payment_intent": payment_intent_id}
            
            if amount:
                refund_params["amount"] = amount
            
            if reason:
                refund_params["reason"] = reason
            
            refund = stripe.Refund.create(**refund_params)
            
            return {
                "id": refund.id,
                "amount": refund.amount,
                "currency": refund.currency,
                "status": refund.status,
                "reason": refund.reason,
                "created": refund.created
            }
            
        except Exception as e:
            print(f"Refund creation error: {e}")
            raise Exception(f"Failed to create refund: {str(e)}")
    
    async def get_usage_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get Stripe usage statistics"""
        
        try:
            # Calculate date range
            end_time = int(datetime.utcnow().timestamp())
            start_time = int((datetime.utcnow() - timedelta(days=days)).timestamp())
            
            # Get payment intents
            payment_intents = stripe.PaymentIntent.list(
                created={"gte": start_time, "lte": end_time},
                limit=100
            )
            
            # Get subscriptions
            subscriptions = stripe.Subscription.list(
                created={"gte": start_time, "lte": end_time},
                limit=100
            )
            
            # Calculate statistics
            total_payments = len(payment_intents.data)
            successful_payments = sum(1 for pi in payment_intents.data if pi.status == "succeeded")
            total_revenue = sum(pi.amount for pi in payment_intents.data if pi.status == "succeeded")
            
            active_subscriptions = sum(1 for sub in subscriptions.data if sub.status == "active")
            
            return {
                "period_days": days,
                "total_payments": total_payments,
                "successful_payments": successful_payments,
                "success_rate": (successful_payments / max(total_payments, 1)) * 100,
                "total_revenue_cents": total_revenue,
                "total_revenue_usd": total_revenue / 100,
                "new_subscriptions": len(subscriptions.data),
                "active_subscriptions": active_subscriptions
            }
            
        except Exception as e:
            print(f"Stripe usage statistics error: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Stripe API health"""
        
        try:
            # Try to retrieve account info
            account = stripe.Account.retrieve()
            
            return {
                "status": "healthy",
                "account_id": account.id,
                "country": account.country,
                "charges_enabled": account.charges_enabled,
                "payouts_enabled": account.payouts_enabled,
                "configured": True
            }
            
        except Exception as e:
            print(f"Stripe health check error: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "configured": False
            }