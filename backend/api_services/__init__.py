"""
Staples API Services module.
This module provides access to Staples internal API services.
"""

from api_services.base_api_client import StaplesApiClient
from api_services.order_api import OrderApiClient
from api_services.customer_api import CustomerApiClient
from api_services.product_api import ProductApiClient
from api_services.store_api import StoreApiClient

__all__ = [
    "StaplesApiClient",
    "OrderApiClient",
    "CustomerApiClient",
    "ProductApiClient",
    "StoreApiClient",
]