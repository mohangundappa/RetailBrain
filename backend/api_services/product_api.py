"""
Product API client for interacting with Staples product services.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.api_services.base_api_client import StaplesApiClient

logger = logging.getLogger(__name__)


class ProductApiClient(StaplesApiClient):
    """Client for Staples Product API services."""

    def __init__(self, *args, **kwargs):
        """Initialize the Product API client."""
        super().__init__(*args, **kwargs)
        self.service_name = "product-api"

    def get_product_by_id(self, product_id: str) -> Dict[str, Any]:
        """
        Get product details by ID.

        Args:
            product_id: Product ID to retrieve.

        Returns:
            Product details.
        """
        endpoint = f"/products/{product_id}"
        
        # Mock response for development/testing
        mock_response = {
            "product_id": product_id,
            "name": "Staples® Arc System Notebook",
            "description": "Customizable Arc notebook with removable pages and premium paper.",
            "category": "office_supplies",
            "sub_category": "notebooks",
            "price": 24.99,
            "currency": "USD",
            "availability": "in_stock",
            "stock_count": 143,
            "images": [
                {
                    "url": "https://example.com/images/arc-notebook-main.jpg",
                    "alt": "Arc Notebook Front View",
                    "is_primary": True
                },
                {
                    "url": "https://example.com/images/arc-notebook-open.jpg",
                    "alt": "Arc Notebook Open View",
                    "is_primary": False
                }
            ],
            "specifications": {
                "dimensions": "8.5\" x 11\"",
                "color": "Black",
                "material": "Poly",
                "page_count": 60,
                "sheet_size": "Letter"
            },
            "features": [
                "Customizable",
                "Removable pages",
                "Premium paper",
                "Durable poly cover"
            ],
            "rating": 4.7,
            "review_count": 128,
            "related_products": ["prod_67891", "prod_67892", "prod_67893"],
            "warranty": "1-year limited warranty",
            "shipping_info": {
                "weight": "1.2 lbs",
                "dimensions": "9\" x 12\" x 1\"",
                "free_shipping_eligible": True
            },
            "item_number": "ARC-001-BLK",
            "manufacturer": "Staples",
            "country_of_origin": "USA"
        }
        
        return self.get(endpoint, mock_response=mock_response)

    def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
        page: int = 1,
        sort_by: str = "relevance",
    ) -> Dict[str, Any]:
        """
        Search for products.

        Args:
            query: Search query.
            category: Filter by category.
            limit: Maximum number of results to return.
            page: Page number for pagination.
            sort_by: Sort results by (relevance, price_asc, price_desc, rating).

        Returns:
            Search results.
        """
        endpoint = "/products/search"
        params = {
            "q": query,
            "category": category,
            "limit": limit,
            "page": page,
            "sort_by": sort_by
        }
        
        # Mock response for development/testing
        mock_response = {
            "query": query,
            "category": category,
            "total_results": 42,
            "page": page,
            "limit": limit,
            "sort_by": sort_by,
            "products": [
                {
                    "product_id": "prod_12345",
                    "name": "Premium Copy Paper, 8.5\" x 11\"",
                    "category": "office_supplies",
                    "price": 19.99,
                    "rating": 4.5,
                    "review_count": 89,
                    "availability": "in_stock",
                    "image_url": "https://example.com/images/paper-main.jpg",
                    "short_description": "Premium white copy paper for everyday printing."
                },
                {
                    "product_id": "prod_67890",
                    "name": "Staples® Arc System Notebook",
                    "category": "office_supplies",
                    "price": 24.99,
                    "rating": 4.7,
                    "review_count": 128,
                    "availability": "in_stock",
                    "image_url": "https://example.com/images/arc-notebook-main.jpg",
                    "short_description": "Customizable Arc notebook with removable pages."
                },
                {
                    "product_id": "prod_23456",
                    "name": "Multi-Purpose Printer Paper",
                    "category": "office_supplies",
                    "price": 15.99,
                    "rating": 4.3,
                    "review_count": 67,
                    "availability": "in_stock",
                    "image_url": "https://example.com/images/printer-paper-main.jpg",
                    "short_description": "Reliable paper for everyday printing needs."
                }
            ]
        }
        
        return self.get(endpoint, params=params, mock_response=mock_response)

    def get_product_availability(self, product_id: str, store_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check product availability.

        Args:
            product_id: Product ID to check.
            store_id: Store ID to check availability at.

        Returns:
            Availability information.
        """
        endpoint = f"/products/{product_id}/availability"
        params = {}
        if store_id:
            params["store_id"] = store_id
        
        # Mock response for development/testing
        mock_response = {
            "product_id": product_id,
            "name": "Staples® Arc System Notebook",
            "online_availability": {
                "status": "in_stock",
                "quantity": 143,
                "estimated_shipping": "1-2 business days",
                "restrictions": None
            },
            "store_availability": [
                {
                    "store_id": "store_123",
                    "store_name": "Staples - Boston Downtown",
                    "status": "in_stock",
                    "quantity": 12,
                    "last_updated": datetime.now().isoformat()
                },
                {
                    "store_id": "store_456",
                    "store_name": "Staples - Cambridge Porter Square",
                    "status": "low_stock",
                    "quantity": 2,
                    "last_updated": datetime.now().isoformat()
                },
                {
                    "store_id": "store_789",
                    "store_name": "Staples - Somerville",
                    "status": "out_of_stock",
                    "quantity": 0,
                    "last_updated": datetime.now().isoformat()
                }
            ]
        }
        
        if store_id:
            # Filter to just the requested store
            store_availability = [s for s in mock_response["store_availability"] if s["store_id"] == store_id]
            mock_response["store_availability"] = store_availability if store_availability else []
        
        return self.get(endpoint, params=params, mock_response=mock_response)

    def get_product_reviews(self, product_id: str, limit: int = 10, page: int = 1) -> Dict[str, Any]:
        """
        Get reviews for a product.

        Args:
            product_id: Product ID to get reviews for.
            limit: Maximum number of reviews to return.
            page: Page number for pagination.

        Returns:
            Product reviews.
        """
        endpoint = f"/products/{product_id}/reviews"
        params = {"limit": limit, "page": page}
        
        # Mock response for development/testing
        mock_response = {
            "product_id": product_id,
            "name": "Staples® Arc System Notebook",
            "average_rating": 4.7,
            "review_count": 128,
            "rating_distribution": {
                "5": 98,
                "4": 20,
                "3": 7,
                "2": 2,
                "1": 1
            },
            "reviews": [
                {
                    "review_id": "rev_12345",
                    "customer_name": "John D.",
                    "rating": 5,
                    "title": "Best notebook system ever",
                    "content": "I've been using the Arc system for years and it's the most versatile notebook I've ever used.",
                    "verified_purchase": True,
                    "date": (datetime.now() - timedelta(days=30)).isoformat(),
                    "helpful_votes": 15
                },
                {
                    "review_id": "rev_23456",
                    "customer_name": "Sarah M.",
                    "rating": 4,
                    "title": "Great but expensive",
                    "content": "Love the flexibility of the system but wish the accessories were more affordable.",
                    "verified_purchase": True,
                    "date": (datetime.now() - timedelta(days=60)).isoformat(),
                    "helpful_votes": 8
                },
                {
                    "review_id": "rev_34567",
                    "customer_name": "Robert T.",
                    "rating": 5,
                    "title": "Perfect for students",
                    "content": "Being able to rearrange pages is a game-changer for organizing my class notes.",
                    "verified_purchase": True,
                    "date": (datetime.now() - timedelta(days=90)).isoformat(),
                    "helpful_votes": 12
                }
            ],
            "page": page,
            "limit": limit,
            "total_pages": 43
        }
        
        return self.get(endpoint, params=params, mock_response=mock_response)

    def get_recommended_products(self, product_id: str, limit: int = 5) -> Dict[str, Any]:
        """
        Get recommended products based on a product.

        Args:
            product_id: Reference product ID.
            limit: Maximum number of recommendations to return.

        Returns:
            Recommended products.
        """
        endpoint = f"/products/{product_id}/recommendations"
        params = {"limit": limit}
        
        # Mock response for development/testing
        mock_response = {
            "product_id": product_id,
            "recommendations": [
                {
                    "product_id": "prod_67891",
                    "name": "Arc System Dividers",
                    "price": 9.99,
                    "image_url": "https://example.com/images/arc-dividers.jpg",
                    "rating": 4.6,
                    "type": "accessory"
                },
                {
                    "product_id": "prod_67892",
                    "name": "Arc System Hole Punch",
                    "price": 39.99,
                    "image_url": "https://example.com/images/arc-punch.jpg",
                    "rating": 4.8,
                    "type": "accessory"
                },
                {
                    "product_id": "prod_67893",
                    "name": "Premium Ruled Filler Paper",
                    "price": 7.99,
                    "image_url": "https://example.com/images/filler-paper.jpg",
                    "rating": 4.5,
                    "type": "consumable"
                },
                {
                    "product_id": "prod_67894",
                    "name": "Arc System Folder Pockets",
                    "price": 12.99,
                    "image_url": "https://example.com/images/arc-pockets.jpg",
                    "rating": 4.3,
                    "type": "accessory"
                },
                {
                    "product_id": "prod_67895",
                    "name": "Arc System Leather Notebook",
                    "price": 34.99,
                    "image_url": "https://example.com/images/arc-leather.jpg",
                    "rating": 4.9,
                    "type": "alternative"
                }
            ],
            "recommendation_type": "frequently_bought_together"
        }
        
        return self.get(endpoint, params=params, mock_response=mock_response)