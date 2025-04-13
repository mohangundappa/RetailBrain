"""
Customer data service for Staples Brain.
This service provides customer data lookup and enrichment functions.
"""
import logging
from typing import Dict, Optional, Any

# Set up logging
logger = logging.getLogger(__name__)


class CustomerDataService:
    """Service for customer data lookups and enrichment"""
    
    def __init__(self):
        """Initialize with mock customer data"""
        self.customers = {
            "cust_12345": {
                "customer_id": "cust_12345",
                "email": "john.doe@example.com",
                "phone": "555-123-4567",
                "type": "individual",
                "tier": "premier",
                "preferred_store_id": "store_boston_downtown",
                "name": "John Doe",
                "address": {
                    "street": "123 Main St",
                    "city": "Boston",
                    "state": "MA",
                    "zip": "02108"
                },
                "recent_orders": [
                    {"order_id": "ORD-987654", "status": "delivered", "date": "2025-04-01"},
                    {"order_id": "ORD-876543", "status": "processing", "date": "2025-04-10"}
                ]
            },
            "cust_67890": {
                "customer_id": "cust_67890",
                "email": "jane.smith@acme.com",
                "phone": "555-987-6543",
                "type": "business",
                "tier": "plus",
                "preferred_store_id": "store_nyc_midtown",
                "name": "Jane Smith",
                "company": "ACME Corp",
                "address": {
                    "street": "456 Park Ave",
                    "city": "New York",
                    "state": "NY",
                    "zip": "10022"
                },
                "recent_orders": [
                    {"order_id": "ORD-112233", "status": "delivered", "date": "2025-03-25"},
                    {"order_id": "ORD-223344", "status": "shipped", "date": "2025-04-08"}
                ]
            }
        }
        
        # Index by email for lookups
        self.email_to_id = {
            "john.doe@example.com": "cust_12345",
            "jane.smith@acme.com": "cust_67890"
        }
        
        logger.info("CustomerDataService initialized")
    
    async def get_customer_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Lookup customer by ID
        
        Args:
            customer_id: The customer ID to lookup
            
        Returns:
            Customer data dict or None if not found
        """
        customer = self.customers.get(customer_id)
        if customer:
            logger.debug(f"Found customer by ID: {customer_id}")
        else:
            logger.debug(f"Customer not found for ID: {customer_id}")
        return customer
    
    async def get_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Lookup customer by email
        
        Args:
            email: The customer email to lookup
            
        Returns:
            Customer data dict or None if not found
        """
        customer_id = self.email_to_id.get(email)
        if customer_id:
            customer = self.customers.get(customer_id)
            logger.debug(f"Found customer by email: {email}")
            return customer
        logger.debug(f"Customer not found for email: {email}")
        return None
    
    async def enrich_customer_data(self, partial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich partial customer data with additional information
        
        Args:
            partial_data: Partial customer data with at least customer_id or email
            
        Returns:
            Enriched customer data dict
        """
        # Try to lookup by ID first
        if "customer_id" in partial_data:
            full_data = await self.get_customer_by_id(partial_data["customer_id"])
            if full_data:
                return {**partial_data, **full_data}
        
        # Try to lookup by email if ID didn't work
        if "email" in partial_data:
            full_data = await self.get_customer_by_email(partial_data["email"])
            if full_data:
                return {**partial_data, **full_data}
        
        # No enrichment possible, return original data
        return partial_data