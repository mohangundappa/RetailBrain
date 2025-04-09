import logging
import json
import os
from typing import Dict, Any, Optional, List
import requests
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from agents.base_agent import BaseAgent
from config import PACKAGE_TRACKING_ENDPOINT

logger = logging.getLogger(__name__)

class PackageTrackingAgent(BaseAgent):
    """
    Agent responsible for tracking Staples orders and their associated packages.
    
    This agent can handle queries about order status, package location, estimated delivery dates,
    and other order or shipping-related inquiries. It verifies user identity through order number
    and zip code matching, retrieves comprehensive order data, and provides user-friendly status
    updates with appropriate Staples branding and customer service personality.
    """
    
    def __init__(self, llm):
        """
        Initialize the Package Tracking Agent.
        
        Args:
            llm: The language model to use for this agent
        """
        super().__init__(
            name="Order Tracking",
            description="I can help track your orders, check package status, and provide delivery updates for Staples purchases.",
            llm=llm
        )
        
        # Customize the Staples Customer Service Representative persona for order tracking
        self.persona = {
            "role": "Staples Customer Service Representative",
            "style": "helpful, friendly, and professional",
            "tone": "polite, supportive, and reassuring",
            "knowledge_areas": [
                "Staples order tracking systems",
                "order status terminology",
                "delivery timeframes",
                "package tracking procedures", 
                "order verification processes",
                "shipping carriers (UPS, FedEx, USPS)",
                "delivery exceptions",
                "order and package-related issues",
                "customer account order history"
            ],
            "communication_preferences": [
                "clear", 
                "precise",
                "solution-oriented",
                "sequential information gathering",
                "verification-focused",
                "empathetic with order and shipping concerns"
            ],
            "workflow": [
                "collect order number and zip code",
                "verify customer information",
                "retrieve order details",
                "provide status updates",
                "transfer to human agent when needed"
            ]
        }
        
        # Create specialized chains
        self.classifier_chain = self._create_classifier_chain()
        self.tracking_chain = self._create_tracking_chain()
        self.formatting_chain = self._create_formatting_chain()
    
    def _create_classifier_chain(self) -> LLMChain:
        """
        Create a chain to classify if an input is related to order tracking.
        
        Returns:
            An LLMChain that can classify inputs
        """
        template = """
        You are a Staples Customer Service Representative that determines if a customer query is related to order tracking or package status.
        
        Customer Query: {user_input}
        
        Is this query related to any of the following:
        - Tracking an order
        - Checking order status
        - Finding package location
        - Checking delivery status
        - Inquiring about shipment
        - Questions about order delivery timeline
        - Reporting a missing or delayed delivery
        - Providing order number and/or zip code for tracking
        
        Please answer with a confidence score between 0 and 1, where:
        - 0 means definitely not related to order tracking or package status
        - 1 means definitely related to order tracking or package status
        
        Output only the confidence score as a float between 0 and 1.
        """
        
        return self._create_chain(template, ["user_input"])
    
    def _create_tracking_chain(self) -> LLMChain:
        """
        Create a chain to extract order number and zip code from user input.
        
        Returns:
            An LLMChain that can extract tracking details
        """
        template = """
        You are a Staples Customer Service Representative that extracts package tracking information from customer queries.
        
        Customer Query: {user_input}
        
        Extract the following information if present:
        1. Order number
        2. Zip code
        3. Tracking number (if provided)
        4. Any request to speak with a human agent (yes/no)
        
        IMPORTANT FORMATTING INSTRUCTIONS:
        - Return your answer as a valid, parseable JSON object with ONLY these fields:
        {
          "order_number": string or null,
          "zip_code": string or null,
          "tracking_number": string or null,
          "human_agent_requested": boolean
        }
        
        STRICT GUIDELINES:
        - If information is not available or not provided, use null instead of empty string
        - ONLY include the JSON object in your response, no additional text
        - Set human_agent_requested to true if the customer explicitly asks to speak to a human, representative, agent, or person
        - Format the JSON without extra whitespace in key names
        - Make sure the JSON is valid and can be parsed by json.loads()
        - Do not use line breaks or newlines within the JSON keys
        
        Example valid response:
        {"order_number": "OD1234567", "zip_code": "90210", "tracking_number": null, "human_agent_requested": false}
        """
        
        return self._create_chain(template, ["user_input"])
    
    def _create_formatting_chain(self) -> LLMChain:
        """
        Create a chain to format the tracking information into a user-friendly response
        in the style of a Staples Customer Service Representative.
        
        Returns:
            An LLMChain that can format responses with appropriate customer service persona
        """
        template = """
        You are a Staples Customer Service Representative specializing in package tracking and order status inquiries.

        CUSTOMER SERVICE GUIDELINES:
        - Be helpful, friendly, and professional in all communications
        - Use a polite, supportive, and reassuring tone
        - Express empathy and understanding for the customer's order/shipping concerns
        - Speak as a Staples representative using "we" when referring to Staples
        - Never mention being an AI, language model, or assistant
        - Present information clearly and precisely
        - Offer solutions and next steps when appropriate
        - Be knowledgeable about Staples shipping policies and procedures
        - Focus on resolving the customer's order inquiry efficiently
        - Transfer to a human agent when appropriate

        ORDER AND TRACKING INFORMATION:
        {tracking_info}
        
        ORDER STATUS:
        {package_status}
        
        CUSTOMER QUERY:
        {user_input}
        
        CONVERSATION FLOW RULES:
        1. If human_agent_requested is true OR package_status has transfer_to_human set to true, respond by saying you'll transfer them to a human agent who can help locate their order without an order number. DO NOT ask for more information in this case.
        2. If package_status shows status as "transfer_to_human" or "missing_order_number", tell the customer you're connecting them with a human agent who can help them locate their order using alternative information such as their email address or phone number.
        3. If both order_number and zip_code are missing (and no transfer is needed), politely ask for both.
        4. If order_number is missing but zip_code is provided (and no transfer is needed), ask only for the order number.
        5. If zip_code is missing but order_number is provided (and no transfer is needed), ask only for the zip code.
        6. If there's a delivery issue or the status is "not_found", express concern and offer to connect them with a human agent.
        7. If the status is available, provide a clear summary of the order status in a conversational format.
        
        Respond in a conversational, helpful manner as a Staples Customer Service Representative.
        Include only the most important details about their order/package.
        If suggesting a transfer to a human agent, emphasize that the human agent will have more tools to help.
        """
        
        return self._create_chain(template, ["tracking_info", "package_status", "user_input"])
    
    async def process(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user query related to order tracking with a Staples customer service persona.
        Extracts order details, retrieves order status, and formats a user-friendly response.
        Applies guardrails to ensure appropriate, on-brand responses.
        
        Args:
            user_input: The user's question or request about order tracking
            context: Additional context information (conversation history, user data)
            
        Returns:
            A dictionary containing the agent's response with tracking info, order status, and applied guardrails
        """
        logger.debug(f"Processing order tracking request: {user_input}")
        
        try:
            # Initialize parent class context (for conversation memory)
            await super().process(user_input, context)
            
            # Extract tracking information from user input
            try:
                tracking_result = await self.tracking_chain.arun(user_input=user_input)
                
                # Clean up the tracking result to handle potential whitespace in JSON keys
                tracking_result = tracking_result.replace('\n', '').replace('  ', ' ').strip()
                
                # Try to parse JSON, handle potential formatting issues
                try:
                    tracking_info = json.loads(tracking_result)
                except json.JSONDecodeError as json_err:
                    logger.warning(f"JSON parse error: {json_err}. Attempting to fix malformed JSON")
                    # If JSON parsing fails, try to extract values using regex as fallback
                    tracking_info = {
                        "order_number": None,
                        "zip_code": None,
                        "tracking_number": None,
                        "human_agent_requested": False
                    }
                
                # Check if the user explicitly stated they don't have or can't find their order number
                # This requires checking original input for statements about not having order information
                dont_have_order_number = any(phrase in user_input.lower() for phrase in [
                    "don't have order", "do not have order", "can't find order", 
                    "don't have the order", "don't know order", "lost my order", 
                    "don't have an order", "no order number", "lost order"
                ])
                
                # Set human_agent_requested to True if user doesn't have order number
                if dont_have_order_number:
                    tracking_info["human_agent_requested"] = True
                    package_status = {
                        "status": "transfer_to_human",
                        "message": "Customer doesn't have order number - transferring to agent",
                        "estimated_delivery": None,
                        "current_location": None,
                        "last_updated": None,
                        "transfer_to_human": True,
                        "human_transfer_reason": "missing_order_number"
                    }
                # If no order number is provided, we'll need to handle this gracefully
                elif not tracking_info.get("order_number"):
                    # Instead of failing, continue with a request for the order number
                    package_status = {
                        "status": "information_needed",
                        "message": "Order number required for tracking",
                        "estimated_delivery": None,
                        "current_location": None,
                        "last_updated": None
                    }
                else:
                    # Get package status from external API
                    package_status = self._get_package_status(tracking_info, context)
            
            except Exception as e:
                logger.error(f"Error extracting tracking information: {str(e)}")
                # Provide a fallback status for a more graceful error experience
                tracking_info = {
                    "order_number": None,
                    "zip_code": None,
                    "tracking_number": None,
                    "human_agent_requested": False
                }
                package_status = {
                    "status": "information_needed",
                    "message": "Unable to process tracking request",
                    "estimated_delivery": None,
                    "current_location": None,
                    "last_updated": None
                }
            
            # Format the response with customer service persona
            formatted_response = await self.formatting_chain.arun(
                tracking_info=json.dumps(tracking_info, indent=2),
                package_status=json.dumps(package_status, indent=2),
                user_input=user_input
            )
            
            # Apply guardrails to ensure appropriate responses
            corrected_response, violations = self.apply_response_guardrails(formatted_response)
            
            # Log if any guardrail violations were detected and corrected
            if violations:
                logger.warning(f"Guardrail violations detected in order tracking response: {len(violations)}")
            
            # Create response object with guardrail-corrected response
            response = {
                "agent": self.name,
                "response": corrected_response,
                "tracking_info": tracking_info,
                "package_status": package_status,
                "guardrail_violations": violations,
                "success": True
            }
            
            # Add to memory
            self.add_to_memory({
                "role": "assistant",
                "content": corrected_response,
                "conversation_id": context.get("conversation_id") if context else None,
                "extracted_info": {
                    "order_number": tracking_info.get("order_number"),
                    "zip_code": tracking_info.get("zip_code"),
                    "tracking_number": tracking_info.get("tracking_number"),
                    "order_status": package_status.get("order_status"),
                    "package_status": package_status.get("package_status") or package_status.get("status"),
                    "estimated_delivery": package_status.get("estimated_delivery"),
                    "human_transfer": package_status.get("transfer_to_human", False),
                    "human_transfer_reason": package_status.get("human_transfer_reason")
                }
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing order tracking request: {str(e)}", exc_info=True)
            # Create a customer service-appropriate error message
            error_response = f"I apologize, but I'm having difficulty retrieving the status of your order at the moment. To better assist you, could you please provide your order number and the billing zip code? If you've already provided this information and the issue persists, our customer service team is available at 1-800-STAPLES to assist you further."
            
            # Apply guardrails to error message too
            corrected_error, _ = self.apply_response_guardrails(error_response)
            
            return {
                "agent": self.name,
                "response": corrected_error,
                "success": False,
                "error": str(e)
            }
    
    def can_handle(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        Determine if this agent can handle the given user input.
        
        Args:
            user_input: The user's request or query
            context: Additional context information
            
        Returns:
            A confidence score between 0 and 1
        """
        try:
            # Use the classifier chain to determine confidence
            confidence_str = self.classifier_chain.run(user_input=user_input).strip()
            confidence = float(confidence_str)
            logger.debug(f"Order tracking confidence: {confidence} for input: {user_input}")
            return min(max(confidence, 0.0), 1.0)  # Ensure confidence is between 0 and 1
        except Exception as e:
            logger.error(f"Error determining confidence: {str(e)}", exc_info=True)
            return 0.0
    
    def _get_package_status(self, tracking_info: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get the status of an order from an external API using order number and zip code.
        
        Args:
            tracking_info: Extracted order information (order_number, zip_code, tracking_number)
            context: Additional context information
            
        Returns:
            Order status information with package details and human transfer flags if needed
        """
        try:
            order_number = tracking_info.get("order_number")
            zip_code = tracking_info.get("zip_code")
            human_requested = tracking_info.get("human_agent_requested", False)
            
            # Check if the customer has requested a human agent
            if human_requested:
                return {
                    "status": "transfer_to_human",
                    "message": "Customer has requested transfer to a human agent",
                    "human_transfer_reason": "customer_requested",
                    "transfer_to_human": True
                }
            
            # Check if we have the minimum required information
            if not order_number and not zip_code:
                return {
                    "status": "missing_information",
                    "message": "Order number and zip code are required to track your order",
                    "missing_fields": ["order_number", "zip_code"],
                    "estimated_delivery": None
                }
            elif not order_number:
                return {
                    "status": "missing_information",
                    "message": "Order number is required to track your order",
                    "missing_fields": ["order_number"],
                    "estimated_delivery": None
                }
            elif not zip_code:
                return {
                    "status": "missing_information",
                    "message": "Zip code is required to track your order",
                    "missing_fields": ["zip_code"],
                    "estimated_delivery": None
                }
            
            # If we have both order number and zip code, proceed with API call
            # In a real implementation, this would call an actual order status API
            headers = {"Content-Type": "application/json"}
            api_key = os.environ.get("ORDER_API_KEY")
            
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            payload = {
                "order_number": order_number,
                "zip_code": zip_code
            }
            
            # Add tracking number if available (optional)
            if tracking_info.get("tracking_number"):
                payload["tracking_number"] = tracking_info.get("tracking_number")
            
            # Make API request to order status service
            try:
                ORDER_STATUS_ENDPOINT = "https://api.staples.com/order-status"  # Example endpoint
                response = requests.post(
                    ORDER_STATUS_ENDPOINT,
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                response.raise_for_status()
                api_response = response.json()
                
                # If the API returns a flag to transfer to human, pass it through
                if api_response.get("transfer_to_human", False):
                    api_response["status"] = "transfer_to_human"
                    api_response["human_transfer_reason"] = "api_request"
                
                return api_response
                
            except requests.RequestException as e:
                logger.warning(f"Could not connect to order status API: {str(e)}")
                # For API failures, use simulated data but also set transfer flag
                simulated_data = self._simulate_order_status(order_number, zip_code)
                
                # For a real system, consider transferring to a human agent when API fails
                # Uncomment this if you want API failures to trigger a human transfer
                # simulated_data["transfer_to_human"] = True
                # simulated_data["human_transfer_reason"] = "api_failure" 
                
                return simulated_data
                
        except Exception as e:
            logger.error(f"Error getting order status: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error retrieving order status: {str(e)}",
                "estimated_delivery": None,
                "transfer_to_human": True,
                "human_transfer_reason": "system_error"
            }
    
    def _simulate_order_status(self, order_number: str, zip_code: str) -> Dict[str, Any]:
        """
        Simulate an order status response for demonstration purposes.
        
        Args:
            order_number: The order number to simulate
            zip_code: The zip code for verification
            
        Returns:
            A simulated order status with package tracking information
        """
        import random
        from datetime import datetime, timedelta
        
        # Generate a consistent but random status based on the order number
        # This ensures the same order gets the same status
        random.seed(f"{order_number}_{zip_code}")
        
        # Generate a fake tracking number based on the order number
        tracking_number = f"TRK{order_number.replace('-', '').replace('#', '')}"
        
        # Order statuses
        order_statuses = ["processing", "shipped", "delivered", "backordered", "partially_shipped"]
        order_status = random.choice(order_statuses)
        
        # Package statuses
        if order_status == "shipped":
            pkg_statuses = ["in_transit", "out_for_delivery"]
            pkg_status = random.choice(pkg_statuses)
        elif order_status == "delivered":
            pkg_status = "delivered"
        elif order_status == "partially_shipped":
            pkg_statuses = ["in_transit", "out_for_delivery"]
            pkg_status = random.choice(pkg_statuses)
        else:
            pkg_status = "processing"
        
        # Generate order date (1-10 days in the past)
        order_days_ago = random.randint(1, 10)
        order_date = (datetime.now() - timedelta(days=order_days_ago)).strftime("%Y-%m-%d")
        
        # Generate a delivery date (1-5 days from now)
        delivery_days = random.randint(1, 5)
        estimated_delivery = (datetime.now() + timedelta(days=delivery_days)).strftime("%Y-%m-%d")
        
        # If delivered, set delivery date in the past
        if order_status == "delivered":
            delivery_date = (datetime.now() - timedelta(days=random.randint(1, 3))).strftime("%Y-%m-%d")
        else:
            delivery_date = None
        
        # Shipping locations
        locations = ["Chicago, IL", "New York, NY", "Los Angeles, CA", "Dallas, TX", "Atlanta, GA"]
        current_location = random.choice(locations) if pkg_status == "in_transit" else None
        
        # Generate items for the order
        items = []
        num_items = random.randint(1, 5)
        product_names = [
            "Staples Copy Paper, 8.5\" x 11\"",
            "Hammermill Printer Paper",
            "HP 67 Ink Cartridge",
            "Brother Toner Cartridge",
            "Scotch Magic Tape",
            "Post-it Notes Value Pack",
            "Sharpie Permanent Markers",
            "Staples Arc Notebook",
            "Swingline Stapler",
            "HP OfficeJet Printer"
        ]
        
        for i in range(num_items):
            item_status = order_status
            # For partially shipped orders, make some items shipped and others processing
            if order_status == "partially_shipped":
                item_status = random.choice(["shipped", "processing"])
            
            items.append({
                "item_id": f"ITEM{random.randint(10000, 99999)}",
                "name": random.choice(product_names),
                "quantity": random.randint(1, 3),
                "status": item_status,
                "shipped_date": order_date if item_status in ["shipped", "delivered"] else None
            })
        
        logger.warning(f"Using simulated order status for order: {order_number}, zip: {zip_code}")
        
        return {
            "order_number": order_number,
            "order_date": order_date,
            "order_status": order_status,
            "zip_code": zip_code,
            "tracking_number": tracking_number,
            "package_status": pkg_status,
            "estimated_delivery": estimated_delivery if pkg_status not in ["delivered", "processing"] else None,
            "delivery_date": delivery_date,
            "current_location": current_location,
            "items": items,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "shipping_carrier": random.choice(["UPS", "FedEx", "USPS"]),
            "is_simulated": True
        }
        
    def _simulate_package_status(self, tracking_number: str) -> Dict[str, Any]:
        """
        Simulate a package status response for demonstration purposes.
        
        Args:
            tracking_number: The tracking number to simulate
            
        Returns:
            A simulated package status
        """
        import random
        from datetime import datetime, timedelta
        
        # Generate a consistent but random status based on the tracking number
        # This ensures the same tracking number gets the same status
        random.seed(tracking_number)
        
        statuses = ["in_transit", "delivered", "out_for_delivery", "processing"]
        status = random.choice(statuses)
        
        # Generate a delivery date (1-5 days from now)
        delivery_days = random.randint(1, 5)
        delivery_date = (datetime.now() + timedelta(days=delivery_days)).strftime("%Y-%m-%d")
        
        locations = ["Chicago, IL", "New York, NY", "Los Angeles, CA", "Dallas, TX", "Atlanta, GA"]
        current_location = random.choice(locations)
        
        logger.warning(f"Using simulated tracking data for tracking number: {tracking_number}")
        
        return {
            "tracking_number": tracking_number,
            "status": status,
            "estimated_delivery": delivery_date if status != "delivered" else None,
            "delivery_date": delivery_date if status == "delivered" else None,
            "current_location": current_location if status != "delivered" else None,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": f"Package is currently {status.replace('_', ' ')}",
            "is_simulated": True
        }
