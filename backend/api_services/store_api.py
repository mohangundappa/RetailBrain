"""
Store API client for interacting with Staples store services.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional

from api_services.base_api_client import StaplesApiClient

logger = logging.getLogger(__name__)


class StoreApiClient(StaplesApiClient):
    """Client for Staples Store API services."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        mock_mode: bool = True,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
    ):
        """
        Initialize the Store API client with circuit breaker protection.
        
        Args:
            base_url: Base URL for the API endpoint. If None, will use environment variable.
            api_key: API key for authentication. If None, will use environment variable.
            timeout: Request timeout in seconds.
            mock_mode: If True, will use mock data instead of making actual API calls.
            failure_threshold: Number of failures before opening the circuit breaker.
            recovery_timeout: Seconds to wait before trying to recover a failed circuit.
        """
        # Initialize with service-specific settings
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            mock_mode=mock_mode,
            service_name="store-api",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    def get_store_by_id(self, store_id: str) -> Dict[str, Any]:
        """
        Get store details by ID.

        Args:
            store_id: Store ID to retrieve.

        Returns:
            Store details.
        """
        endpoint = f"/stores/{store_id}"
        
        # Mock response for development/testing
        mock_response = {
            "store_id": store_id,
            "name": "Staples - Boston Downtown",
            "address": {
                "street": "101 Washington St",
                "city": "Boston",
                "state": "MA",
                "zip": "02108",
                "country": "USA"
            },
            "phone": "+1 (617) 542-5225",
            "email": "store123@staples.com",
            "hours": {
                "monday": {"open": "08:00", "close": "21:00"},
                "tuesday": {"open": "08:00", "close": "21:00"},
                "wednesday": {"open": "08:00", "close": "21:00"},
                "thursday": {"open": "08:00", "close": "21:00"},
                "friday": {"open": "08:00", "close": "21:00"},
                "saturday": {"open": "09:00", "close": "20:00"},
                "sunday": {"open": "10:00", "close": "18:00"}
            },
            "services": [
                "Printing & Marketing",
                "Tech Services",
                "Self-Service Copying",
                "Shipping Services",
                "Free Wi-Fi"
            ],
            "coordinates": {
                "latitude": 42.3567,
                "longitude": -71.0585
            },
            "open_now": True,
            "distance": None,
            "rating": 4.2,
            "review_count": 156,
            "store_image_url": "https://example.com/images/stores/boston-downtown.jpg",
            "special_hours": [],
            "parking_info": "Street parking and nearby paid garages available.",
            "manager": "John Thompson"
        }
        
        return self.get(endpoint, mock_response=mock_response)

    def find_stores_by_location(
        self,
        location: str,
        radius: float = 10.0,
        services: Optional[List[str]] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Find stores near a location.

        Args:
            location: Address, city, state, or zip code.
            radius: Search radius in miles.
            services: Filter by available services.
            limit: Maximum number of results to return.

        Returns:
            List of nearby stores.
        """
        endpoint = "/stores/near"
        params = {"location": location, "radius": radius, "limit": limit}
        if services:
            params["services"] = ",".join(services)
        
        # Mock response for development/testing
        mock_response = {
            "location": location,
            "radius": radius,
            "stores": [
                {
                    "store_id": "store_123",
                    "name": "Staples - Boston Downtown",
                    "address": {
                        "street": "101 Washington St",
                        "city": "Boston",
                        "state": "MA",
                        "zip": "02108",
                        "country": "USA"
                    },
                    "phone": "+1 (617) 542-5225",
                    "hours": {
                        "today": {"open": "08:00", "close": "21:00"},
                        "tomorrow": {"open": "08:00", "close": "21:00"}
                    },
                    "services": [
                        "Printing & Marketing",
                        "Tech Services",
                        "Self-Service Copying",
                        "Shipping Services",
                        "Free Wi-Fi"
                    ],
                    "distance": 0.3,
                    "open_now": True
                },
                {
                    "store_id": "store_456",
                    "name": "Staples - Cambridge Porter Square",
                    "address": {
                        "street": "77 Massachusetts Ave",
                        "city": "Cambridge",
                        "state": "MA",
                        "zip": "02139",
                        "country": "USA"
                    },
                    "phone": "+1 (617) 234-5678",
                    "hours": {
                        "today": {"open": "08:00", "close": "20:00"},
                        "tomorrow": {"open": "08:00", "close": "20:00"}
                    },
                    "services": [
                        "Printing & Marketing",
                        "Self-Service Copying",
                        "Free Wi-Fi"
                    ],
                    "distance": 2.1,
                    "open_now": True
                },
                {
                    "store_id": "store_789",
                    "name": "Staples - Somerville",
                    "address": {
                        "street": "145 Middlesex Ave",
                        "city": "Somerville",
                        "state": "MA",
                        "zip": "02145",
                        "country": "USA"
                    },
                    "phone": "+1 (617) 987-6543",
                    "hours": {
                        "today": {"open": "08:00", "close": "21:00"},
                        "tomorrow": {"open": "08:00", "close": "21:00"}
                    },
                    "services": [
                        "Printing & Marketing",
                        "Tech Services",
                        "Self-Service Copying",
                        "Shipping Services",
                        "Free Wi-Fi"
                    ],
                    "distance": 3.5,
                    "open_now": True
                }
            ],
            "total_count": 3
        }
        
        # Filter by services if specified
        if services:
            filtered_stores = []
            for store in mock_response["stores"]:
                if all(service in store["services"] for service in services):
                    filtered_stores.append(store)
            mock_response["stores"] = filtered_stores
            mock_response["total_count"] = len(filtered_stores)
        
        return self.get(endpoint, params=params, mock_response=mock_response)

    def get_store_services(self, store_id: str) -> Dict[str, Any]:
        """
        Get detailed information about services offered at a store.

        Args:
            store_id: Store ID to retrieve services for.

        Returns:
            Store services information.
        """
        endpoint = f"/stores/{store_id}/services"
        
        # Mock response for development/testing
        mock_response = {
            "store_id": store_id,
            "name": "Staples - Boston Downtown",
            "services": [
                {
                    "name": "Printing & Marketing",
                    "description": "Professional printing, copying, and design services.",
                    "availability": "Available during store hours",
                    "details": [
                        "Business cards",
                        "Flyers and brochures",
                        "Posters and banners",
                        "Custom promotional items",
                        "Document binding"
                    ],
                    "pricing": "Varies by service",
                    "queue_time": "Approximately 15 minutes"
                },
                {
                    "name": "Tech Services",
                    "description": "Computer repair, setup, and support services.",
                    "availability": "Available 9am-7pm daily",
                    "details": [
                        "Computer repair and virus removal",
                        "Data backup and recovery",
                        "Device setup and installation",
                        "Software troubleshooting",
                        "Network setup"
                    ],
                    "pricing": "Starting at $49.99",
                    "queue_time": "Approximately 30 minutes"
                },
                {
                    "name": "Self-Service Copying",
                    "description": "DIY copying, printing, and scanning.",
                    "availability": "Available during store hours",
                    "details": [
                        "Black and white copies",
                        "Color copies",
                        "Scanning to email or USB",
                        "Single or double-sided printing"
                    ],
                    "pricing": "B&W: $0.12/page, Color: $0.49/page",
                    "queue_time": "No wait"
                },
                {
                    "name": "Shipping Services",
                    "description": "Package shipping via UPS, FedEx, and USPS.",
                    "availability": "Available during store hours",
                    "details": [
                        "UPS shipping",
                        "FedEx shipping",
                        "USPS shipping",
                        "Package drop-off",
                        "Packaging supplies"
                    ],
                    "pricing": "Varies by carrier and package",
                    "queue_time": "Approximately 10 minutes"
                }
            ]
        }
        
        return self.get(endpoint, mock_response=mock_response)

    def get_store_inventory(self, store_id: str, product_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check inventory at a specific store.

        Args:
            store_id: Store ID to check inventory at.
            product_id: Optional product ID to check specific product availability.

        Returns:
            Store inventory information.
        """
        endpoint = f"/stores/{store_id}/inventory"
        params = {}
        if product_id:
            params["product_id"] = product_id
        
        # Mock response for development/testing
        if product_id:
            mock_response = {
                "store_id": store_id,
                "store_name": "Staples - Boston Downtown",
                "product": {
                    "product_id": product_id,
                    "name": "Staples® Arc System Notebook",
                    "status": "in_stock",
                    "quantity": 12,
                    "aisle": "B5",
                    "price": 24.99,
                    "last_updated": datetime.now().isoformat(),
                    "alternative_stores": [
                        {
                            "store_id": "store_456",
                            "name": "Staples - Cambridge Porter Square",
                            "distance": 2.1,
                            "quantity": 8
                        },
                        {
                            "store_id": "store_789",
                            "name": "Staples - Somerville",
                            "distance": 3.5,
                            "quantity": 5
                        }
                    ]
                }
            }
        else:
            mock_response = {
                "store_id": store_id,
                "store_name": "Staples - Boston Downtown",
                "categories": [
                    {
                        "name": "Office Supplies",
                        "status": "well_stocked",
                        "notable_items": [
                            {
                                "product_id": "prod_12345",
                                "name": "Premium Copy Paper, 8.5\" x 11\"",
                                "status": "in_stock",
                                "quantity": 50,
                                "aisle": "A3"
                            },
                            {
                                "product_id": "prod_67890",
                                "name": "Staples® Arc System Notebook",
                                "status": "in_stock",
                                "quantity": 12,
                                "aisle": "B5"
                            }
                        ]
                    },
                    {
                        "name": "Technology",
                        "status": "well_stocked",
                        "notable_items": [
                            {
                                "product_id": "prod_23456",
                                "name": "HP OfficeJet Pro 9015",
                                "status": "low_stock",
                                "quantity": 2,
                                "aisle": "C2"
                            },
                            {
                                "product_id": "prod_34567",
                                "name": "Logitech MX Master 3",
                                "status": "in_stock",
                                "quantity": 8,
                                "aisle": "C4"
                            }
                        ]
                    }
                ],
                "last_updated": datetime.now().isoformat()
            }
        
        return self.get(endpoint, params=params, mock_response=mock_response)

    def get_in_store_promotion(self, store_id: str) -> Dict[str, Any]:
        """
        Get current in-store promotions.

        Args:
            store_id: Store ID to get promotions for.

        Returns:
            In-store promotion information.
        """
        endpoint = f"/stores/{store_id}/promotions"
        
        # Mock response for development/testing
        mock_response = {
            "store_id": store_id,
            "store_name": "Staples - Boston Downtown",
            "promotions": [
                {
                    "promotion_id": "promo_12345",
                    "title": "Back to School Sale",
                    "description": "Save up to 50% on school supplies",
                    "start_date": (datetime.now() - timedelta(days=7)).isoformat(),
                    "end_date": (datetime.now() + timedelta(days=21)).isoformat(),
                    "categories": ["School Supplies", "Backpacks", "Laptops"],
                    "featured_products": [
                        {
                            "product_id": "prod_45678",
                            "name": "Student Backpack",
                            "regular_price": 39.99,
                            "sale_price": 24.99,
                            "discount_percent": 38
                        },
                        {
                            "product_id": "prod_56789",
                            "name": "Composition Notebooks (12-pack)",
                            "regular_price": 15.99,
                            "sale_price": 7.99,
                            "discount_percent": 50
                        }
                    ],
                    "coupon_code": "SCHOOL2025",
                    "terms_conditions": "While supplies last. Cannot be combined with other offers."
                },
                {
                    "promotion_id": "promo_23456",
                    "title": "Tech Upgrade Event",
                    "description": "Tech trade-in and recycling event with special discounts",
                    "start_date": (datetime.now() - timedelta(days=3)).isoformat(),
                    "end_date": (datetime.now() + timedelta(days=4)).isoformat(),
                    "categories": ["Computers", "Printers", "Monitors"],
                    "featured_products": [
                        {
                            "product_id": "prod_67890",
                            "name": "HP Laptop 15\"",
                            "regular_price": 649.99,
                            "sale_price": 499.99,
                            "discount_percent": 23
                        }
                    ],
                    "coupon_code": None,
                    "terms_conditions": "Trade-in value varies by item condition."
                }
            ],
            "last_updated": datetime.now().isoformat()
        }
        
        return self.get(endpoint, mock_response=mock_response)

    def make_service_appointment(
        self,
        store_id: str,
        service_type: str,
        date: str,
        time_slot: str,
        customer_info: Dict[str, Any],
        service_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Make an appointment for in-store services.

        Args:
            store_id: Store ID to make appointment at.
            service_type: Type of service (printing, tech, etc.).
            date: Appointment date (YYYY-MM-DD).
            time_slot: Appointment time slot.
            customer_info: Customer contact information.
            service_details: Details about the requested service.

        Returns:
            Appointment confirmation.
        """
        endpoint = f"/stores/{store_id}/appointments"
        data = {
            "service_type": service_type,
            "date": date,
            "time_slot": time_slot,
            "customer_info": customer_info,
            "service_details": service_details
        }
        
        # Mock response for development/testing
        mock_response = {
            "appointment_id": "appt_123456",
            "store_id": store_id,
            "store_name": "Staples - Boston Downtown",
            "service_type": service_type,
            "date": date,
            "time_slot": time_slot,
            "estimated_duration": "1 hour",
            "customer_info": customer_info,
            "service_details": service_details,
            "confirmation_code": "STAPLES123456",
            "created_at": datetime.now().isoformat(),
            "status": "confirmed",
            "check_in_instructions": "Please arrive 10 minutes before your appointment. Check in at the customer service desk."
        }
        
        return self.post(endpoint, data=data, mock_response=mock_response)