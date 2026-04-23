"""
Stripe Service

Handles integration with Stripe for payments and customer management.
Implements Requirement 13.5 - Stripe Integration.
"""

import logging
import os
from typing import Dict, Optional, Any, List
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

# Mock stripe library if not installed or for testing
try:
    import stripe
except ImportError:
    stripe = None

logger = logging.getLogger(__name__)

@dataclass
class PaymentResult:
    """Result of a payment operation"""
    success: bool
    transaction_id: str
    amount: Decimal
    currency: str
    status: str
    error_message: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

class StripeService:
    """
    Service for interacting with Stripe API
    
    Handles:
    - Customer management
    - Payment processing
    - Refunds
    - Webhook verification
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Stripe service
        
        Args:
            api_key: Stripe API key (optional, defaults to env var)
        """
        self.api_key = api_key or os.getenv("STRIPE_API_KEY")
        self.logger = logging.getLogger(__name__)
        
        if stripe:
            stripe.api_key = self.api_key
            
        # Mock data for testing without API key
        self._mock_customers = {}
        self._mock_payments = {}
        
    async def create_customer(self, user_id: str, email: str, name: str) -> Optional[str]:
        """
        Create a Stripe customer
        
        Args:
            user_id: Internal user ID
            email: Customer email
            name: Customer name
            
        Returns:
            Stripe customer ID
        """
        if not self.api_key:
            return self._mock_create_customer(user_id, email, name)
            
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={"user_id": user_id}
            )
            return customer.id
        except Exception as e:
            self.logger.error(f"Failed to create Stripe customer: {e}")
            return None

    async def charge_customer(
        self,
        customer_id: str,
        amount: Decimal,
        currency: str,
        description: str
    ) -> PaymentResult:
        """
        Charge a customer
        
        Args:
            customer_id: Stripe customer ID
            amount: Amount to charge
            currency: Currency code (e.g., 'eur')
            description: Charge description
            
        Returns:
            Payment result
        """
        if not self.api_key:
            return self._mock_charge_customer(customer_id, amount, currency, description)
            
        try:
            # Stripe expects amount in cents
            amount_cents = int(amount * 100)
            
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                customer=customer_id,
                description=description,
                confirm=True,  # Attempt to confirm immediately
                automatic_payment_methods={'enabled': True, 'allow_redirects': 'never'}
            )
            
            success = intent.status == 'succeeded'
            
            return PaymentResult(
                success=success,
                transaction_id=intent.id,
                amount=amount,
                currency=currency,
                status=intent.status,
                error_message=intent.last_payment_error.message if intent.last_payment_error else None
            )
            
        except Exception as e:
            self.logger.error(f"Stripe charge failed: {e}")
            return PaymentResult(
                success=False,
                transaction_id="",
                amount=amount,
                currency=currency,
                status="failed",
                error_message=str(e)
            )

    async def process_refund(
        self,
        transaction_id: str,
        amount: Optional[Decimal] = None,
        reason: str = "requested_by_customer"
    ) -> bool:
        """
        Process a refund
        
        Args:
            transaction_id: Original transaction ID
            amount: Amount to refund (None for full refund)
            reason: Refund reason
            
        Returns:
            True if successful
        """
        if not self.api_key:
            return self._mock_process_refund(transaction_id, amount)
            
        try:
            kwargs = {"payment_intent": transaction_id}
            if amount:
                kwargs["amount"] = int(amount * 100)
                
            refund = stripe.Refund.create(**kwargs)
            return refund.status == 'succeeded'
            
        except Exception as e:
            self.logger.error(f"Stripe refund failed: {e}")
            return False

    # Mock implementations for development/testing
    
    def _mock_create_customer(self, user_id: str, email: str, name: str) -> str:
        customer_id = f"cus_mock_{user_id}"
        self._mock_customers[customer_id] = {
            "email": email,
            "name": name,
            "metadata": {"user_id": user_id}
        }
        self.logger.info(f"MOCK: Created customer {customer_id}")
        return customer_id
        
    def _mock_charge_customer(self, customer_id: str, amount: Decimal, currency: str, description: str) -> PaymentResult:
        if customer_id not in self._mock_customers:
            return PaymentResult(
                success=False,
                transaction_id="",
                amount=amount,
                currency=currency,
                status="failed",
                error_message="Customer not found"
            )
            
        transaction_id = f"pi_mock_{len(self._mock_payments) + 1}"
        self._mock_payments[transaction_id] = {
            "customer_id": customer_id,
            "amount": amount,
            "currency": currency,
            "status": "succeeded"
        }
        
        self.logger.info(f"MOCK: Charged {amount} {currency} to {customer_id}")
        
        return PaymentResult(
            success=True,
            transaction_id=transaction_id,
            amount=amount,
            currency=currency,
            status="succeeded"
        )

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        endpoint_secret: str
    ) -> bool:
        """Verify Stripe webhook signature
        
        Args:
            payload: Raw webhook request body
            signature: Stripe-Signature header value
            endpoint_secret: Webhook secret from Stripe dashboard
            
        Returns:
            True if signature is valid
        """
        if not stripe:
            self.logger.warning("stripe library not installed, cannot verify signature")
            return False
            
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                endpoint_secret
            )
            return True
        except stripe.SignatureVerificationError:
            self.logger.error("Webhook signature verification failed")
            return False
        except ValueError:
            self.logger.error("Invalid webhook payload")
            return False
        
    def _mock_process_refund(self, transaction_id: str, amount: Optional[Decimal]) -> bool:
        if transaction_id not in self._mock_payments:
            return False
            
        self.logger.info(f"MOCK: Refunded {transaction_id}")
        return True
