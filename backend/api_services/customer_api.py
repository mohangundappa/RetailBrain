"""
Customer API client for interacting with Staples customer services.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.api_services.base_api_client import StaplesApiClient

logger = logging.getLogger(__name__)


class CustomerApiClient(StaplesApiClient):
    """Client for Staples Customer API services."""

    def __init__(self, *args, **kwargs):
        """Initialize the Customer API client."""
        super().__init__(*args, **kwargs)
        self.service_name = "customer-api"

    def get_customer_by_id(self, customer_id: str) -> Dict[str, Any]:
        """
        Get customer details by ID.

        Args:
            customer_id: Customer ID to retrieve.

        Returns:
            Customer details.
        """
        endpoint = f"/customers/{customer_id}"
        
        # Mock response for development/testing
        mock_response = {
            "customer_id": customer_id,
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com",
            "phone": "+1 (555) 123-4567",
            "membership_tier": "premium",
            "membership_since": (datetime.now() - timedelta(days=365)).isoformat(),
            "addresses": [
                {
                    "type": "billing",
                    "street": "123 Business Ave",
                    "city": "Boston",
                    "state": "MA",
                    "zip": "02108",
                    "country": "USA",
                    "is_default": True
                },
                {
                    "type": "shipping",
                    "street": "456 Home Street",
                    "city": "Boston",
                    "state": "MA",
                    "zip": "02108",
                    "country": "USA",
                    "is_default": True
                }
            ],
            "preferences": {
                "communication": {
                    "email": True,
                    "sms": False,
                    "mail": False
                },
                "categories": ["office_supplies", "technology", "furniture"]
            },
            "account_status": "active",
            "last_login": (datetime.now() - timedelta(days=3)).isoformat(),
            "total_orders": 27,
            "total_spend": 2458.93,
            "rewards_points": 3250
        }
        
        return self.get(endpoint, mock_response=mock_response)

    def get_customer_by_email(self, email: str) -> Dict[str, Any]:
        """
        Get customer details by email address.

        Args:
            email: Customer email to search for.

        Returns:
            Customer details.
        """
        endpoint = "/customers/lookup"
        params = {"email": email}
        
        # Mock response for development/testing
        mock_response = {
            "customer_id": "cust_123456",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": email,
            "phone": "+1 (555) 123-4567",
            "membership_tier": "premium",
            "membership_since": (datetime.now() - timedelta(days=365)).isoformat(),
            "addresses": [
                {
                    "type": "billing",
                    "street": "123 Business Ave",
                    "city": "Boston",
                    "state": "MA",
                    "zip": "02108",
                    "country": "USA",
                    "is_default": True
                },
                {
                    "type": "shipping",
                    "street": "456 Home Street",
                    "city": "Boston",
                    "state": "MA",
                    "zip": "02108",
                    "country": "USA",
                    "is_default": True
                }
            ],
            "account_status": "active",
            "last_login": (datetime.now() - timedelta(days=3)).isoformat()
        }
        
        return self.get(endpoint, params=params, mock_response=mock_response)

    def get_membership_details(self, customer_id: str) -> Dict[str, Any]:
        """
        Get membership details for a customer.

        Args:
            customer_id: Customer ID to retrieve membership details for.

        Returns:
            Membership details.
        """
        endpoint = f"/customers/{customer_id}/membership"
        
        # Mock response for development/testing
        mock_response = {
            "customer_id": customer_id,
            "membership_tier": "premium",
            "membership_since": (datetime.now() - timedelta(days=365)).isoformat(),
            "membership_expires": (datetime.now() + timedelta(days=365)).isoformat(),
            "auto_renew": True,
            "benefits": [
                "Free next-day shipping",
                "5% back in rewards",
                "Free tech support",
                "Extended return period (60 days)"
            ],
            "rewards_points": 3250,
            "rewards_points_value": 32.50,
            "rewards_history": [
                {
                    "date": (datetime.now() - timedelta(days=30)).isoformat(),
                    "points": 250,
                    "action": "purchase",
                    "order_id": "ord_123456"
                },
                {
                    "date": (datetime.now() - timedelta(days=60)).isoformat(),
                    "points": 500,
                    "action": "purchase",
                    "order_id": "ord_123457"
                }
            ]
        }
        
        return self.get(endpoint, mock_response=mock_response)

    def update_customer_preferences(self, customer_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update customer preferences.

        Args:
            customer_id: Customer ID to update.
            preferences: New preferences to set.

        Returns:
            Updated customer preferences.
        """
        endpoint = f"/customers/{customer_id}/preferences"
        
        # Mock response for development/testing
        mock_response = {
            "customer_id": customer_id,
            "preferences": preferences,
            "updated_at": datetime.now().isoformat()
        }
        
        return self.put(endpoint, data=preferences, mock_response=mock_response)

    def initiate_password_reset(self, email: str) -> Dict[str, Any]:
        """
        Initiate a password reset for a customer.

        Args:
            email: Customer email address.

        Returns:
            Password reset confirmation details.
        """
        endpoint = "/customers/password-reset"
        data = {"email": email}
        
        # Mock response for development/testing
        mock_response = {
            "success": True,
            "message": "Password reset email sent",
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        return self.post(endpoint, data=data, mock_response=mock_response)

    def check_account_status(self, customer_id: str) -> Dict[str, Any]:
        """
        Check account status for a customer.

        Args:
            customer_id: Customer ID to check.

        Returns:
            Account status details.
        """
        endpoint = f"/customers/{customer_id}/status"
        
        # Mock response for development/testing
        mock_response = {
            "customer_id": customer_id,
            "account_status": "active",
            "last_login": (datetime.now() - timedelta(days=3)).isoformat(),
            "recent_activity": [
                {
                    "action": "login",
                    "timestamp": (datetime.now() - timedelta(days=3)).isoformat(),
                    "ip_address": "192.168.1.1",
                    "device": "desktop"
                },
                {
                    "action": "order_placed",
                    "timestamp": (datetime.now() - timedelta(days=3, hours=1)).isoformat(),
                    "order_id": "ord_123456"
                }
            ],
            "account_flags": [],
            "account_restrictions": []
        }
        
        return self.get(endpoint, mock_response=mock_response)