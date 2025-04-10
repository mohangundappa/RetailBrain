"""
Order API client for interacting with Staples order services.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from api_services.base_api_client import StaplesApiClient

logger = logging.getLogger(__name__)


class OrderApiClient(StaplesApiClient):
    """Client for Staples Order API services."""

    def __init__(self, *args, **kwargs):
        """Initialize the Order API client."""
        super().__init__(*args, **kwargs)
        self.service_name = "order-api"

    def get_order_by_id(self, order_id: str) -> Dict[str, Any]:
        """
        Get order details by ID.

        Args:
            order_id: Order ID to retrieve.

        Returns:
            Order details.
        """
        endpoint = f"/orders/{order_id}"
        
        # Mock response for development/testing
        mock_response = {
            "order_id": order_id,
            "status": "shipped",
            "customer_id": "cust_123456",
            "order_date": (datetime.now() - timedelta(days=3)).isoformat(),
            "estimated_delivery": (datetime.now() + timedelta(days=2)).isoformat(),
            "items": [
                {
                    "item_id": "prod_12345",
                    "name": "Premium Copy Paper, 8.5\" x 11\"",
                    "quantity": 2,
                    "price": 19.99,
                    "status": "shipped"
                },
                {
                    "item_id": "prod_67890",
                    "name": "Staples® Arc System Notebook",
                    "quantity": 1,
                    "price": 24.99,
                    "status": "shipped"
                }
            ],
            "shipping_address": {
                "street": "123 Business Ave",
                "city": "Boston",
                "state": "MA",
                "zip": "02108",
                "country": "USA"
            },
            "shipping_method": "ground",
            "tracking_info": {
                "carrier": "UPS",
                "tracking_number": "1Z9999999999999999",
                "tracking_url": "https://www.ups.com/track?tracknum=1Z9999999999999999"
            },
            "total_amount": 64.97,
            "currency": "USD"
        }
        
        return self.get(endpoint, mock_response=mock_response)

    def get_order_by_tracking_number(self, tracking_number: str) -> Dict[str, Any]:
        """
        Get order details by tracking number.

        Args:
            tracking_number: Tracking number to search for.

        Returns:
            Order details.
        """
        endpoint = "/orders/tracking"
        params = {"tracking_number": tracking_number}
        
        # Mock response for development/testing
        mock_response = {
            "order_id": "ord_987654",
            "status": "shipped",
            "customer_id": "cust_123456",
            "order_date": (datetime.now() - timedelta(days=2)).isoformat(),
            "estimated_delivery": (datetime.now() + timedelta(days=1)).isoformat(),
            "items": [
                {
                    "item_id": "prod_54321",
                    "name": "Staples® Wireless Mouse",
                    "quantity": 1,
                    "price": 29.99,
                    "status": "shipped"
                }
            ],
            "shipping_address": {
                "street": "123 Business Ave",
                "city": "Boston",
                "state": "MA",
                "zip": "02108",
                "country": "USA"
            },
            "shipping_method": "express",
            "tracking_info": {
                "carrier": "UPS",
                "tracking_number": tracking_number,
                "tracking_url": f"https://www.ups.com/track?tracknum={tracking_number}"
            },
            "total_amount": 29.99,
            "currency": "USD"
        }
        
        return self.get(endpoint, params=params, mock_response=mock_response)

    def get_customer_orders(self, customer_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get a list of orders for a customer.

        Args:
            customer_id: Customer ID to retrieve orders for.
            limit: Maximum number of orders to return.

        Returns:
            Dictionary containing a list of order summaries and metadata.
        """
        endpoint = "/orders"
        params = {"customer_id": customer_id, "limit": limit}
        
        # Mock response for development/testing
        mock_response = {
            "orders": [
                {
                    "order_id": "ord_987654",
                    "status": "shipped",
                    "order_date": (datetime.now() - timedelta(days=2)).isoformat(),
                    "total_amount": 29.99,
                    "item_count": 1
                },
                {
                    "order_id": "ord_876543",
                    "status": "delivered",
                    "order_date": (datetime.now() - timedelta(days=10)).isoformat(),
                    "total_amount": 128.45,
                    "item_count": 5
                },
                {
                    "order_id": "ord_765432",
                    "status": "processing",
                    "order_date": (datetime.now() - timedelta(days=1)).isoformat(),
                    "total_amount": 75.99,
                    "item_count": 2
                }
            ],
            "total_count": 3,
            "customer_id": customer_id
        }
        
        return self.get(endpoint, params=params, mock_response=mock_response)

    def create_order_return(self, order_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a return request for an order.

        Args:
            order_id: Order ID to return items from.
            items: List of items to return, with item_id and quantity.

        Returns:
            Return request details.
        """
        endpoint = f"/orders/{order_id}/returns"
        data = {"items": items, "reason": "customer_request"}
        
        # Mock response for development/testing
        mock_response = {
            "return_id": "ret_123456",
            "order_id": order_id,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "items": items,
            "return_label": {
                "url": "https://example.com/return_label.pdf",
                "expires_at": (datetime.now() + timedelta(days=14)).isoformat()
            },
            "estimated_refund": sum([item.get("price", 19.99) * item.get("quantity", 1) for item in items]),
            "currency": "USD"
        }
        
        return self.post(endpoint, data=data, mock_response=mock_response)

    def get_order_shipment_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get detailed shipment status for an order.

        Args:
            order_id: Order ID to check.

        Returns:
            Shipment status details.
        """
        endpoint = f"/orders/{order_id}/shipment"
        
        # Mock response for development/testing
        mock_response = {
            "order_id": order_id,
            "status": "in_transit",
            "estimated_delivery": (datetime.now() + timedelta(days=2)).isoformat(),
            "shipments": [
                {
                    "shipment_id": "ship_12345",
                    "carrier": "UPS",
                    "tracking_number": "1Z9999999999999999",
                    "tracking_url": "https://www.ups.com/track?tracknum=1Z9999999999999999",
                    "status": "in_transit",
                    "status_detail": "Package is in transit to the destination",
                    "location": "Secaucus, NJ",
                    "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
                    "estimated_delivery": (datetime.now() + timedelta(days=2)).isoformat(),
                    "history": [
                        {
                            "status": "shipped",
                            "status_detail": "Package has left the facility",
                            "location": "Edison, NJ",
                            "timestamp": (datetime.now() - timedelta(days=1)).isoformat()
                        },
                        {
                            "status": "processing",
                            "status_detail": "Package is being processed",
                            "location": "Edison, NJ",
                            "timestamp": (datetime.now() - timedelta(days=1, hours=12)).isoformat()
                        }
                    ]
                }
            ]
        }
        
        return self.get(endpoint, mock_response=mock_response)