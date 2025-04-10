"""
Tool service for Staples Brain.

This service provides a standardized interface for tools that can be called
by agents, particularly for interacting with external API services.
"""
import os
import logging
import inspect
import json
from typing import Dict, Any, List, Optional, Union, Callable, Type
from datetime import datetime
import asyncio

from brain.core_services.base_service import CoreService
from api_services.base_api_client import StaplesApiClient
from api_services.order_api import OrderApiClient
from api_services.customer_api import CustomerApiClient
from api_services.product_api import ProductApiClient
from api_services.store_api import StoreApiClient
from utils.observability import record_error

logger = logging.getLogger(__name__)

class Tool:
    """
    Base class for all tools that can be called by agents.
    
    A tool encapsulates a specific operation or functionality that an agent
    can use to accomplish its tasks, particularly for API operations.
    """
    
    def __init__(self, name: str, description: str, api_client: Optional[StaplesApiClient] = None):
        """
        Initialize a tool.
        
        Args:
            name: Tool name
            description: Tool description
            api_client: Optional API client for API-based tools
        """
        self.name = name
        self.description = description
        self.api_client = api_client
        
        # Automatically extract parameter information from __call__
        sig = inspect.signature(self.__call__)
        self.parameters = {}
        for param_name, param in sig.parameters.items():
            if param_name != 'self':
                self.parameters[param_name] = {
                    "name": param_name,
                    "description": "",  # Default empty description
                    "required": param.default == inspect.Parameter.empty,
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                }
        
        # Track usage statistics
        self.call_count = 0
        self.last_called = None
        self.error_count = 0
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """
        Call the tool with the provided arguments.
        
        Args:
            **kwargs: Tool-specific arguments
            
        Returns:
            Tool execution result
        """
        raise NotImplementedError("Tool implementations must override __call__")
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the tool schema for documentation and validation.
        
        Returns:
            Dictionary containing the tool schema
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
    
    def update_parameter_description(self, param_name: str, description: str) -> None:
        """
        Update the description of a parameter.
        
        Args:
            param_name: Parameter name
            description: Parameter description
        """
        if param_name in self.parameters:
            self.parameters[param_name]["description"] = description
    
    def validate_parameters(self, **kwargs) -> bool:
        """
        Validate the parameters provided for the tool call.
        
        Args:
            **kwargs: Parameters to validate
            
        Returns:
            True if parameters are valid, False otherwise
        """
        # Check that all required parameters are provided
        for param_name, param in self.parameters.items():
            if param.get("required", False) and param_name not in kwargs:
                logger.error(f"Missing required parameter: {param_name}")
                return False
        
        return True
    
    def track_call(self, success: bool = True) -> None:
        """
        Track a tool call.
        
        Args:
            success: Whether the call was successful
        """
        self.call_count += 1
        self.last_called = datetime.now()
        if not success:
            self.error_count += 1


class OrderTrackingTool(Tool):
    """Tool for tracking order status."""
    
    def __init__(self, api_client: OrderApiClient):
        """
        Initialize the order tracking tool.
        
        Args:
            api_client: Order API client
        """
        super().__init__(
            name="get_order_status",
            description="Get the status of an order by order ID",
            api_client=api_client
        )
        
        # Update parameter descriptions
        self.update_parameter_description("order_id", "Order ID to check status for")
    
    def __call__(self, order_id: str) -> Dict[str, Any]:
        """
        Get the status of an order.
        
        Args:
            order_id: Order ID to check status for
            
        Returns:
            Order status information
        """
        try:
            # Track the call
            self.track_call()
            
            # Call the API client
            result = self.api_client.get_order_details(order_id)
            
            return {
                "status": "success",
                "order": result
            }
            
        except Exception as e:
            self.track_call(success=False)
            logger.error(f"Error in order tracking tool: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }


class TrackingInfoTool(Tool):
    """Tool for getting package tracking information."""
    
    def __init__(self, api_client: OrderApiClient):
        """
        Initialize the tracking info tool.
        
        Args:
            api_client: Order API client
        """
        super().__init__(
            name="get_tracking_info",
            description="Get package tracking information by order ID or tracking number",
            api_client=api_client
        )
        
        # Update parameter descriptions
        self.update_parameter_description("order_id", "Order ID to get tracking for (optional if tracking_number provided)")
        self.update_parameter_description("tracking_number", "Tracking number to get information for (optional if order_id provided)")
    
    def __call__(self, order_id: Optional[str] = None, tracking_number: Optional[str] = None) -> Dict[str, Any]:
        """
        Get package tracking information.
        
        Args:
            order_id: Order ID to get tracking for (optional if tracking_number provided)
            tracking_number: Tracking number to get information for (optional if order_id provided)
            
        Returns:
            Tracking information
        """
        try:
            # Track the call
            self.track_call()
            
            # Validate parameters
            if not order_id and not tracking_number:
                return {
                    "status": "error",
                    "error": "Either order_id or tracking_number must be provided"
                }
            
            # Call the appropriate API method based on provided parameters
            if order_id:
                result = self.api_client.get_order_shipment_status(order_id)
            else:
                # Assuming this method exists or will be implemented
                result = self.api_client.get_tracking_by_number(tracking_number)
            
            return {
                "status": "success",
                "tracking": result
            }
            
        except Exception as e:
            self.track_call(success=False)
            logger.error(f"Error in tracking info tool: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }


class StoreLocatorTool(Tool):
    """Tool for finding store locations."""
    
    def __init__(self, api_client: StoreApiClient):
        """
        Initialize the store locator tool.
        
        Args:
            api_client: Store API client
        """
        super().__init__(
            name="find_store_locations",
            description="Find Staples store locations by location and radius",
            api_client=api_client
        )
        
        # Update parameter descriptions
        self.update_parameter_description("location", "Location to search near (city, state, zip code)")
        self.update_parameter_description("radius", "Search radius in miles")
        self.update_parameter_description("service", "Optional service to filter by (e.g., 'printing', 'tech')")
    
    def __call__(self, location: str, radius: float = 10, service: Optional[str] = None) -> Dict[str, Any]:
        """
        Find store locations.
        
        Args:
            location: Location to search near (city, state, zip code)
            radius: Search radius in miles
            service: Optional service to filter by
            
        Returns:
            List of store locations
        """
        try:
            # Track the call
            self.track_call()
            
            # Call the API client
            result = self.api_client.find_stores(location, radius, service)
            
            return {
                "status": "success",
                "stores": result
            }
            
        except Exception as e:
            self.track_call(success=False)
            logger.error(f"Error in store locator tool: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }


class ProductSearchTool(Tool):
    """Tool for searching products."""
    
    def __init__(self, api_client: ProductApiClient):
        """
        Initialize the product search tool.
        
        Args:
            api_client: Product API client
        """
        super().__init__(
            name="search_products",
            description="Search for products by keyword, category, or product ID",
            api_client=api_client
        )
        
        # Update parameter descriptions
        self.update_parameter_description("query", "Search query or keywords")
        self.update_parameter_description("category", "Optional category to filter by")
        self.update_parameter_description("product_id", "Optional specific product ID to retrieve")
        self.update_parameter_description("limit", "Maximum number of results to return")
    
    def __call__(self, query: str, category: Optional[str] = None, 
               product_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Search for products.
        
        Args:
            query: Search query or keywords
            category: Optional category to filter by
            product_id: Optional specific product ID to retrieve
            limit: Maximum number of results to return
            
        Returns:
            List of matching products
        """
        try:
            # Track the call
            self.track_call()
            
            # If product_id is provided, get the specific product
            if product_id:
                result = self.api_client.get_product_details(product_id)
                return {
                    "status": "success",
                    "product": result
                }
            
            # Otherwise, search for products
            result = self.api_client.search_products(query, category, limit)
            
            return {
                "status": "success",
                "products": result
            }
            
        except Exception as e:
            self.track_call(success=False)
            logger.error(f"Error in product search tool: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }


class CustomerInfoTool(Tool):
    """Tool for retrieving customer information."""
    
    def __init__(self, api_client: CustomerApiClient):
        """
        Initialize the customer info tool.
        
        Args:
            api_client: Customer API client
        """
        super().__init__(
            name="get_customer_info",
            description="Retrieve customer information by ID or email",
            api_client=api_client
        )
        
        # Update parameter descriptions
        self.update_parameter_description("customer_id", "Customer ID to retrieve (optional if email provided)")
        self.update_parameter_description("email", "Customer email to retrieve (optional if customer_id provided)")
    
    def __call__(self, customer_id: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve customer information.
        
        Args:
            customer_id: Customer ID to retrieve (optional if email provided)
            email: Customer email to retrieve (optional if customer_id provided)
            
        Returns:
            Customer information
        """
        try:
            # Track the call
            self.track_call()
            
            # Validate parameters
            if not customer_id and not email:
                return {
                    "status": "error",
                    "error": "Either customer_id or email must be provided"
                }
            
            # Call the appropriate API method based on provided parameters
            if customer_id:
                result = self.api_client.get_customer_details(customer_id)
            else:
                # Assuming this method exists or will be implemented
                result = self.api_client.get_customer_by_email(email)
            
            return {
                "status": "success",
                "customer": result
            }
            
        except Exception as e:
            self.track_call(success=False)
            logger.error(f"Error in customer info tool: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }


class ToolService(CoreService):
    """
    Service for managing tools that can be called by agents.
    
    This service provides a central registry for tools and offers a
    standardized interface for agent tool calling.
    """
    
    def __init__(self):
        """Initialize the tool service."""
        self.tools = {}
        self.api_clients = {}
        self.health_status = {"healthy": False, "last_check": None, "details": {}}
    
    def initialize(self) -> bool:
        """
        Initialize the tool service with required resources.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Initialize API clients
            self._initialize_api_clients()
            
            # Register default tools
            self._register_default_tools()
            
            logger.info(f"Tool service initialized with {len(self.tools)} tools")
            
            self.health_status["healthy"] = True
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {
                "tool_count": len(self.tools),
                "registered_tools": list(self.tools.keys())
            }
            
            return True
            
        except Exception as e:
            error_message = f"Failed to initialize tool service: {str(e)}"
            logger.error(error_message)
            record_error("tool_service_init", error_message)
            
            self.health_status["healthy"] = False
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {"error": error_message}
            
            return False
    
    def _initialize_api_clients(self) -> None:
        """Initialize API clients for tools."""
        # Use mock mode for development (will use real API in production)
        mock_mode = os.environ.get("USE_MOCK_API", "true").lower() in ("true", "1", "yes")
        
        # Initialize API clients with common base URL and API key
        base_url = os.environ.get("STAPLES_API_URL", "https://api.staples.com/v1/")
        api_key = os.environ.get("STAPLES_API_KEY", "mock-api-key")
        
        # Create API clients
        self.api_clients["order"] = OrderApiClient(base_url=base_url, api_key=api_key, mock_mode=mock_mode)
        self.api_clients["customer"] = CustomerApiClient(base_url=base_url, api_key=api_key, mock_mode=mock_mode)
        self.api_clients["product"] = ProductApiClient(base_url=base_url, api_key=api_key, mock_mode=mock_mode)
        self.api_clients["store"] = StoreApiClient(base_url=base_url, api_key=api_key, mock_mode=mock_mode)
        
        logger.info(f"Initialized API clients with mock_mode={mock_mode}")
    
    def _register_default_tools(self) -> None:
        """Register default tools."""
        # Order tools
        self.register_tool(OrderTrackingTool(self.api_clients["order"]))
        self.register_tool(TrackingInfoTool(self.api_clients["order"]))
        
        # Store tools
        self.register_tool(StoreLocatorTool(self.api_clients["store"]))
        
        # Product tools
        self.register_tool(ProductSearchTool(self.api_clients["product"]))
        
        # Customer tools
        self.register_tool(CustomerInfoTool(self.api_clients["customer"]))
    
    def register_tool(self, tool: Tool) -> None:
        """
        Register a tool with the service.
        
        Args:
            tool: Tool instance to register
        """
        tool_name = tool.name
        if tool_name in self.tools:
            logger.warning(f"Tool '{tool_name}' is already registered. Replacing.")
        
        self.tools[tool_name] = tool
        logger.info(f"Registered tool: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Tool name to retrieve
            
        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all registered tools with their schemas.
        
        Returns:
            List of tool schemas
        """
        return [tool.get_schema() for tool in self.tools.values()]
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the schema for a specific tool.
        
        Args:
            tool_name: Tool name
            
        Returns:
            Tool schema or None if tool not found
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return None
        
        return tool.get_schema()
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a tool by name with the provided arguments.
        
        Args:
            tool_name: Tool name
            **kwargs: Tool-specific arguments
            
        Returns:
            Tool execution result
        """
        try:
            tool = self.get_tool(tool_name)
            if not tool:
                logger.error(f"Tool not found: {tool_name}")
                return {
                    "status": "error",
                    "error": f"Tool not found: {tool_name}"
                }
            
            # Validate parameters
            if not tool.validate_parameters(**kwargs):
                logger.error(f"Invalid parameters for tool: {tool_name}")
                return {
                    "status": "error",
                    "error": f"Invalid parameters for tool: {tool_name}"
                }
            
            # Call the tool (wrapping in loop.run_in_executor for CPU-bound or blocking operations)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: tool(**kwargs))
            
            return result
            
        except Exception as e:
            error_message = f"Error calling tool {tool_name}: {str(e)}"
            logger.error(error_message)
            record_error("tool_call", error_message)
            
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service.
        
        Returns:
            Dictionary containing service metadata
        """
        tool_usage = {}
        for name, tool in self.tools.items():
            tool_usage[name] = {
                "call_count": tool.call_count,
                "error_count": tool.error_count,
                "last_called": tool.last_called.isoformat() if tool.last_called else None
            }
        
        return {
            "name": "tool_service",
            "description": "Tool registry and execution service",
            "version": "1.0.0",
            "registered_tools": list(self.tools.keys()),
            "tool_usage": tool_usage,
            "health_status": self.health_status
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            # Update health check time
            self.health_status["last_check"] = datetime.now().isoformat()
            
            # Check if tools are registered
            if not self.tools:
                self.health_status["healthy"] = False
                self.health_status["details"] = {"error": "No tools registered"}
                return self.health_status
            
            # Check if API clients are initialized
            if not self.api_clients:
                self.health_status["healthy"] = False
                self.health_status["details"] = {"error": "API clients not initialized"}
                return self.health_status
            
            # All checks passed
            self.health_status["healthy"] = True
            self.health_status["details"] = {
                "tool_count": len(self.tools),
                "api_client_count": len(self.api_clients)
            }
            
            return self.health_status
            
        except Exception as e:
            error_message = f"Health check failed: {str(e)}"
            logger.error(error_message)
            
            self.health_status["healthy"] = False
            self.health_status["details"] = {"error": error_message}
            
            return self.health_status


# Create singleton instance
tool_service = ToolService()