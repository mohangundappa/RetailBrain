"""
Main application module for Staples Brain.
This is the entry point for the application.

PRODUCTION-READY VERSION:
This version includes configuration for different environments (dev, qa, staging, production)
and follows best practices for deployment in enterprise environments.
"""

# Load environment variables at the very beginning before any other imports
import os
import sys
from pathlib import Path

# Add explicit .env file loading
try:
    from dotenv import load_dotenv
    
    # Look for .env file in the current directory
    dotenv_path = Path('.env')
    if dotenv_path.exists():
        print(f"Loading environment from {dotenv_path.absolute()}")
        load_dotenv(dotenv_path=dotenv_path)
    else:
        print(f".env file not found at {dotenv_path.absolute()}")
        print("Environment variables must be set manually or in a .env file")
        print("For local development, copy .env.example to .env and edit as needed")
except ImportError:
    print("WARNING: python-dotenv package not installed. Environment variables may not load correctly.")
    print("Install with: pip install python-dotenv")

# Import the app from app.py
from app import app as application

# This allows gunicorn to find the app
app = application

# Now import other modules
import logging
import asyncio
import uuid
import time
import random
import json
import traceback
from datetime import datetime, timedelta
import sqlalchemy.exc
from flask import render_template, jsonify, request, session, Response, g, redirect, url_for, flash
from prometheus_client import CONTENT_TYPE_LATEST
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Import from app.py which contains our application factory
from app import app, db

# Import other required modules
from models import Conversation, Message, PackageTracking, PasswordReset, StoreLocator, ProductInfo, AnalyticsData, CustomAgent, AgentTemplate
from utils.memory import ConversationMemory
from utils.observability import (
    get_prometheus_metrics, 
    record_intent_classification, 
    record_agent_selection,
    record_llm_request,
    record_error,
    update_active_conversations,
    get_metrics_summary,
    TimingContext,
    logger
)

# Sample data for simulating agent responses (used for development and testing)
PACKAGE_TRACKING_SAMPLE = {
    "tracking_number": "TRACK123456",
    "shipping_carrier": "UPS",
    "order_number": None,
    "time_frame": "3 days",
    "status": "in_transit",
    "estimated_delivery": "2023-10-15",
    "current_location": "Chicago, IL",
    "last_updated": "2023-10-12 08:30:45",
    "message": "Package is currently in transit",
    "is_simulated": True
}

PASSWORD_RESET_SAMPLE = {
    "email": "user@example.com",
    "username": None,
    "account_type": "Staples.com",
    "issue": "forgot password",
    "status": "instructions_provided",
    "message": "Password reset instructions for your account with email: user@example.com",
    "instructions": [
        "Go to Staples.com and click on 'Sign In' at the top of the page.",
        "Click on 'Forgot Password' below the login form.",
        "Enter your email address associated with your account.",
        "Check your email inbox for a password reset link.",
        "Click the link and follow the instructions to create a new password.",
        "Use your new password to log in."
    ],
    "reset_link_sent": False,
    "is_simulated": True
}

# Store Locator sample data
STORE_LOCATOR_SAMPLE = {
    "location": "10001",
    "radius": 5,
    "service": "Copy & Print",
    "stores": [
        {
            "store_id": "STR-101",
            "store_name": "Staples Midtown",
            "store_address": "1065 Avenue of the Americas, New York, NY 10001",
            "store_phone": "(212) 555-6789",
            "store_hours": "Mon-Fri: 8AM-9PM, Sat: 9AM-9PM, Sun: 10AM-6PM",
            "distance": 0.3,
            "services": ["Copy & Print", "Tech Services", "Shipping"]
        }
    ],
    "message": "Here's the nearest Staples store with Copy & Print services:",
    "is_simulated": True
}

# Product Information sample data
PRODUCT_INFO_SAMPLE = {
    "product_name": "Staples Hyken Mesh Task Chair",
    "product_id": "2257054",
    "category": "Furniture",
    "price": "$249.99",
    "availability": "In Stock",
    "description": "The Staples Hyken mesh task chair offers breathable mesh material and ergonomic support for improved posture and comfort.",
    "specifications": "- Weight capacity: 275 lbs\n- Adjustable height and arms\n- Tilt tension and lockout\n- Headrest included\n- 7-year limited warranty",
    "message": "Here's information about the Staples Hyken Mesh Task Chair:",
    "is_simulated": True
}

# Application routes

@app.route('/')
def index():
    """Render the main page with application statistics."""
    try:
        # Check database and LLM connectivity
        database_connected = db_is_healthy()
        llm_integration = llm_is_healthy()
        
        # Get application statistics
        stats = {
            "total_conversations": Conversation.query.count() if database_connected else 0,
            "conversation_count": Conversation.query.count() if database_connected else 0,
            "total_agents": 4 + CustomAgent.query.filter_by(is_active=True).count() if database_connected else 4,
            "uptime": time.time() - app.config.get("START_TIME", time.time()),
            "environment": os.environ.get("APP_ENV", "development"),
            "database_connected": database_connected,
            "llm_integration": llm_integration,
            "available_agents": ["Package Tracking Agent", "Reset Password Agent", 
                              "Store Locator Agent", "Product Information Agent"]
        }
        
        # Update metrics for active conversations
        active_count = Conversation.query.filter(
            Conversation.created_at >= datetime.now() - timedelta(hours=1)
        ).count()
        update_active_conversations(active_count)
        
        return render_template('index.html', stats=stats)
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return render_template('index.html', stats={"error": str(e)})

@app.route('/api/health', methods=["GET"])
def health_check():
    """Health check endpoint."""
    status = {
        "status": "healthy",
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "environment": os.environ.get("APP_ENV", "development"),
        "database": "connected" if db_is_healthy() else "error",
        "llm_service": "connected" if llm_is_healthy() else "error"
    }
    return jsonify(status)

def db_is_healthy():
    """Check if the database connection is healthy."""
    try:
        # We're already in an app context when this function is called
        # so don't need to create another one which causes the error
        from sqlalchemy import text
        db.session.execute(text("SELECT 1")).fetchall()
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

def llm_is_healthy():
    """Check if the LLM service is healthy."""
    try:
        # Only perform a real check in production-like environments
        if os.environ.get("APP_ENV") in ["production", "staging"]:
            # Create a minimal OpenAI check
            chat = ChatOpenAI()
            chat.invoke("Hello")
        return True
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return False

@app.route('/api/agents', methods=["GET"])
def list_agents():
    """List all available agents."""
    try:
        # Get all built-in agents
        built_in_agents = [
            {"id": "package-tracking", "name": "Package Tracking", "description": "Track your Staples orders and packages", "is_built_in": True},
            {"id": "reset-password", "name": "Password Reset", "description": "Reset your Staples.com or account password", "is_built_in": True},
            {"id": "store-locator", "name": "Store Locator", "description": "Find Staples stores near you", "is_built_in": True},
            {"id": "product-info", "name": "Product Information", "description": "Get information about Staples products", "is_built_in": True}
        ]
        
        # Get custom agents
        custom_agents = CustomAgent.query.filter_by(is_active=True).all()
        custom_agent_data = [
            {
                "id": f"custom-{agent.id}", 
                "name": agent.name, 
                "description": agent.description or "Custom Agent", 
                "is_built_in": False,
                "creator": agent.creator,
                "created_at": agent.created_at.isoformat() if agent.created_at else None
            } 
            for agent in custom_agents
        ]
        
        # Combine both lists
        all_agents = built_in_agents + custom_agent_data
        
        return jsonify({"agents": all_agents})
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations', methods=["GET"])
def list_conversations():
    """List all conversations."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Limit to 100 per page
        
        # Get paginated conversations
        conversations = Conversation.query.order_by(Conversation.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format the results
        result = {
            "conversations": [],
            "pagination": {
                "page": conversations.page,
                "per_page": conversations.per_page,
                "total": conversations.total,
                "pages": conversations.pages
            }
        }
        
        # Add conversation data
        for conv in conversations.items:
            result["conversations"].append({
                "id": conv.id,
                "session_id": conv.session_id,
                "user_input": conv.user_input,
                "brain_response": conv.brain_response,
                "intent": conv.intent,
                "confidence": conv.confidence,
                "selected_agent": conv.selected_agent,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "has_tracking_data": bool(conv.tracking_data),
                "has_password_reset_data": bool(conv.password_reset_data),
                "has_store_locator_data": bool(conv.store_locator_data),
                "has_product_info_data": bool(conv.product_info_data)
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/conversations/<int:conversation_id>', methods=["GET"])
def get_conversation(conversation_id):
    """Get a specific conversation with all its messages and related data."""
    try:
        # Get the conversation
        conversation = Conversation.query.get_or_404(conversation_id)
        
        # Get messages
        messages = [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in conversation.messages
        ]
        
        # Get package tracking data if available
        tracking_data = None
        if conversation.tracking_data:
            tracking = conversation.tracking_data[0]
            tracking_data = {
                "tracking_number": tracking.tracking_number,
                "shipping_carrier": tracking.shipping_carrier,
                "order_number": tracking.order_number,
                "status": tracking.status,
                "estimated_delivery": tracking.estimated_delivery,
                "current_location": tracking.current_location,
                "last_updated": tracking.last_updated.isoformat() if tracking.last_updated else None
            }
        
        # Get password reset data if available
        password_reset_data = None
        if conversation.password_reset_data:
            reset = conversation.password_reset_data[0]
            password_reset_data = {
                "email": reset.email,
                "username": reset.username,
                "account_type": reset.account_type,
                "issue": reset.issue,
                "reset_link_sent": reset.reset_link_sent
            }
        
        # Get store locator data if available
        store_locator_data = None
        if conversation.store_locator_data:
            store = conversation.store_locator_data[0]
            store_locator_data = {
                "location": store.location,
                "radius": store.radius,
                "service": store.service,
                "store_id": store.store_id,
                "store_name": store.store_name,
                "store_address": store.store_address,
                "store_phone": store.store_phone,
                "store_hours": store.store_hours
            }
        
        # Get product information data if available
        product_info_data = None
        if conversation.product_info_data:
            product = conversation.product_info_data[0]
            product_info_data = {
                "product_name": product.product_name,
                "product_id": product.product_id,
                "category": product.category,
                "price": product.price,
                "availability": product.availability,
                "description": product.description,
                "specifications": product.specifications,
                "search_query": product.search_query
            }
        
        # Format the complete response
        result = {
            "id": conversation.id,
            "session_id": conversation.session_id,
            "user_input": conversation.user_input,
            "brain_response": conversation.brain_response,
            "intent": conversation.intent,
            "confidence": conversation.confidence,
            "selected_agent": conversation.selected_agent,
            "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
            "messages": messages,
            "tracking_data": tracking_data,
            "password_reset_data": password_reset_data,
            "store_locator_data": store_locator_data,
            "product_info_data": product_info_data
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/process', methods=["POST"])
def process_request():
    """Process a user request with LLM-based intent identification."""
    try:
        # Extract request data
        data = request.json
        user_input = data.get('user_input')
        session_id = data.get('session_id', str(uuid.uuid4()))
        explicit_agent = data.get('agent')  # Optional override
        
        if not user_input:
            return jsonify({"error": "Missing required parameter: user_input"}), 400
        
        # Get session context from memory if available
        context = app.staples_brain.memory.get_context(session_id)
        
        # Start timing the processing
        with TimingContext("process_request"):
            # Log the request
            logger.info(f"Processing request: {user_input} [session: {session_id}]")
            
            response = None
            intent = None
            confidence = None
            selected_agent = explicit_agent
            
            # If explicit agent is provided, skip intent identification
            if explicit_agent:
                logger.info(f"Using explicitly requested agent: {explicit_agent}")
                
                # Process with the specified agent
                response = process_with_agent(explicit_agent, user_input, session_id, context)
            else:
                # Identify intent using the Staples Brain
                intent_result = app.staples_brain.identify_intent(user_input, context)
                intent = intent_result.get('intent')
                confidence = intent_result.get('confidence')
                selected_agent = intent_result.get('agent')
                
                # Log the intent identification
                logger.info(f"Identified intent: {intent} (confidence: {confidence}) -> agent: {selected_agent}")
                record_intent_classification(intent, confidence)
                
                # If intent was successfully identified, process with that agent
                if selected_agent:
                    record_agent_selection(selected_agent)
                    response = process_with_agent(selected_agent, user_input, session_id, context)
                else:
                    # Process with the orchestrator directly - it will handle welcome flows
                    # and provide appropriate responses when no specific agent is found
                    try:
                        # First, let's check directly for custom agents 
                        try:
                            custom_agents = CustomAgent.query.filter_by(is_active=True, wizard_completed=True).all()
                            logger.info(f"Found {len(custom_agents)} custom agents in the database from main")
                            for agent in custom_agents:
                                logger.info(f"Custom agent: {agent.id} - {agent.name}")
                        except Exception as e:
                            logger.error(f"Error querying custom agents from main: {str(e)}")
                        
                        # Set up the necessary context for intent handling
                        intent_context = {
                            'session_id': session_id,
                            'intent': intent,
                            'intent_confidence': confidence
                        }
                        
                        # Let the orchestrator handle the welcome flow or fallbacks
                        response = asyncio.run(app.staples_brain.orchestrator.process_request(user_input, intent_context))
                    except Exception as e:
                        # Fallback if orchestrator fails
                        logger.error(f"Error using orchestrator for fallback: {str(e)}")
                        # Try one more time to get custom agents
                        custom_agents = []
                        try:
                            # Using direct SQL for reliability
                            from sqlalchemy import text
                            result = db.session.execute(text("SELECT id, name, description FROM custom_agent WHERE is_active = TRUE AND wizard_completed = TRUE")).fetchall()
                            for row in result:
                                custom_agent = type('CustomAgent', (object,), {
                                    'id': row[0],
                                    'name': row[1],
                                    'description': row[2]
                                })
                                custom_agents.append(custom_agent)
                            logger.info(f"Found {len(custom_agents)} custom agents in fallback handler")
                        except Exception as e:
                            logger.error(f"Error in fallback when getting custom agents: {str(e)}")
                            logger.error(f"Stack trace: {traceback.format_exc()}")
                        
                        # Create the base response
                        welcome_text = "Hello! I'm Staples Brain, here to assist you with various Staples-related services. I can help you with:\n\n" + \
                                  "• Tracking your packages and orders\n" + \
                                  "• Resetting your password or account access\n" + \
                                  "• Finding Staples stores near you\n" + \
                                  "• Getting information about Staples products"
                                  
                        # Add custom agents if available
                        if custom_agents:
                            welcome_text += "\n• Working with custom agents: "
                            welcome_text += ", ".join([agent.name for agent in custom_agents])
                            
                        welcome_text += "\n\nHow can I assist you today?"
                        
                        # Create suggested actions
                        suggested_actions = [
                            {"id": "package-tracking", "name": "Track my package", "description": "Check the status of your order or package"},
                            {"id": "reset-password", "name": "Reset my password", "description": "Get help with account access or password reset"},
                            {"id": "store-locator", "name": "Find a store", "description": "Locate Staples stores near you"},
                            {"id": "product-info", "name": "Product information", "description": "Get details about Staples products"}
                        ]
                        
                        # Add custom agents to suggested actions
                        for agent in custom_agents:
                            suggested_actions.append({
                                "id": f"custom-{agent.id}", 
                                "name": agent.name,
                                "description": agent.description or f"Custom agent: {agent.name}"
                            })
                            
                        response = {
                            "response": welcome_text,
                            "suggested_actions": suggested_actions,
                            "agent": None  # Explicitly show there's no agent selected yet
                        }
            
            # Store the conversation
            conv = Conversation(
                session_id=session_id,
                user_input=user_input,
                brain_response=json.dumps(response),
                intent=intent,
                confidence=confidence,
                selected_agent=selected_agent
            )
            
            # Add message history
            user_message = Message(role="user", content=user_input)
            assistant_message = Message(role="assistant", content=response.get("response", ""))
            conv.messages.append(user_message)
            conv.messages.append(assistant_message)
            
            # Add agent-specific data if available
            if selected_agent == "package-tracking" and "tracking_data" in response:
                track_data = response["tracking_data"]
                tracking = PackageTracking(
                    tracking_number=track_data.get("tracking_number"),
                    shipping_carrier=track_data.get("shipping_carrier"),
                    order_number=track_data.get("order_number"),
                    status=track_data.get("status"),
                    estimated_delivery=track_data.get("estimated_delivery"),
                    current_location=track_data.get("current_location")
                )
                conv.tracking_data.append(tracking)
            
            elif selected_agent == "reset-password" and "password_data" in response:
                pwd_data = response["password_data"]
                reset = PasswordReset(
                    email=pwd_data.get("email"),
                    username=pwd_data.get("username"),
                    account_type=pwd_data.get("account_type"),
                    issue=pwd_data.get("issue"),
                    reset_link_sent=pwd_data.get("reset_link_sent", False)
                )
                conv.password_reset_data.append(reset)
            
            elif selected_agent == "store-locator" and "store_data" in response:
                store_data = response["store_data"]
                store = StoreLocator(
                    location=store_data.get("location"),
                    radius=store_data.get("radius"),
                    service=store_data.get("service"),
                    store_id=store_data.get("store_id"),
                    store_name=store_data.get("store_name"),
                    store_address=store_data.get("store_address"),
                    store_phone=store_data.get("store_phone"),
                    store_hours=store_data.get("store_hours")
                )
                conv.store_locator_data.append(store)
            
            elif selected_agent == "product-info" and "product_data" in response:
                prod_data = response["product_data"]
                product = ProductInfo(
                    product_name=prod_data.get("product_name"),
                    product_id=prod_data.get("product_id"),
                    category=prod_data.get("category"),
                    price=prod_data.get("price"),
                    availability=prod_data.get("availability"),
                    description=prod_data.get("description"),
                    specifications=prod_data.get("specifications"),
                    search_query=prod_data.get("search_query")
                )
                conv.product_info_data.append(product)
            
            # Save to database
            db.session.add(conv)
            db.session.commit()
            
            # Update context in memory
            app.staples_brain.memory.update_context(session_id, conv)
            
            # Add conversation ID to the response
            response["conversation_id"] = conv.id
            response["session_id"] = session_id
            
            return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        record_error("process_request", str(e))
        return jsonify({
            "error": "An error occurred processing your request",
            "details": str(e),
            "response": "I'm sorry, but I encountered an error processing your request. Please try again or contact support if the issue persists."
        }), 500

def process_with_agent(agent_id, user_input, session_id, context=None):
    """Process a request with a specific agent."""
    # Initialize response
    response = {}
    
    try:
        if agent_id == "package-tracking":
            response = process_package_tracking(user_input, context)
        elif agent_id == "reset-password":
            response = process_password_reset(user_input, context)
        elif agent_id == "store-locator":
            response = process_store_locator(user_input, context)
        elif agent_id == "product-info":
            response = process_product_info(user_input, context)
        elif agent_id.startswith("custom-"):
            # Process custom agent
            custom_id = int(agent_id.replace("custom-", ""))
            custom_agent = CustomAgent.query.get(custom_id)
            if custom_agent:
                response = process_custom_agent(custom_agent, user_input, context)
            else:
                response = {"response": "Custom agent not found."}
        else:
            response = {"response": f"Agent {agent_id} not recognized."}
    
    except Exception as e:
        logger.error(f"Error in agent {agent_id}: {e}")
        record_error(f"agent_{agent_id}", str(e))
        response = {
            "response": "I'm sorry, but I encountered an error processing your request. Please try again or contact support if the issue persists.",
            "error": str(e)
        }
    
    return response

def process_package_tracking(user_input, context=None):
    """Process a package tracking request."""
    # In production, this would use real API calls
    # Here we simulate for demo purposes
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    
    try:
        # Extract tracking information
        prompt = ChatPromptTemplate.from_template(
            "Extract package tracking information from this query: {query}\n\n"
            "Extract the following fields:\n"
            "- tracking_number: The package tracking number (if present)\n"
            "- shipping_carrier: The shipping carrier (if specified)\n"
            "- order_number: The order number (if present instead of tracking)\n"
            "- time_frame: Any time frame mentioned (e.g., '3 days')\n\n"
            "Output JSON format with these fields. If a field is not found, set it to null."
        )
        
        llm = ChatOpenAI(temperature=0.0)
        extraction_chain = prompt | llm
        
        with TimingContext("llm_request"):
            result = extraction_chain.invoke({"query": user_input})
            content = result.content
        
        # Record LLM request metrics
        record_llm_request("package_tracking_extraction", len(user_input), len(content))
        
        # Parse the extracted information
        extracted_info = None
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                extracted_json = json_match.group(1)
                extracted_info = json.loads(extracted_json)
            else:
                # Try direct JSON parsing
                extracted_info = json.loads(content)
        except:
            # If JSON parsing fails, create a simple response with the input
            extracted_info = {
                "tracking_number": None,
                "shipping_carrier": None,
                "order_number": None,
                "time_frame": None
            }
            
            # Look for potential tracking numbers
            import re
            tracking_patterns = [
                r'\b([A-Z]{2}\d{9}[A-Z]{2})\b',  # Common UPS format
                r'\b(1Z[0-9A-Z]{16})\b',          # UPS
                r'\b(\d{12,14})\b',               # USPS, FedEx
                r'\b(\d{10})\b',                  # USPS
                r'#\s*(\w{6,20})\b'               # Generic with # prefix
            ]
            
            for pattern in tracking_patterns:
                match = re.search(pattern, user_input)
                if match:
                    extracted_info["tracking_number"] = match.group(1)
                    break
        
        # In production, this would use a real tracking API
        # For this prototype, we use a simulation
        tracking_data = dict(PACKAGE_TRACKING_SAMPLE)  # Clone the sample data
        
        # Update with extracted info
        if extracted_info.get("tracking_number"):
            tracking_data["tracking_number"] = extracted_info["tracking_number"]
        if extracted_info.get("shipping_carrier"):
            tracking_data["shipping_carrier"] = extracted_info["shipping_carrier"]
        if extracted_info.get("order_number"):
            tracking_data["order_number"] = extracted_info["order_number"]
        
        # Generate a response message
        if tracking_data["tracking_number"]:
            if tracking_data["status"] == "delivered":
                message = f"Your package with tracking number {tracking_data['tracking_number']} has been delivered."
            elif tracking_data["status"] == "in_transit":
                message = f"Your package with tracking number {tracking_data['tracking_number']} is in transit. It was last seen in {tracking_data['current_location']} and is expected to be delivered by {tracking_data['estimated_delivery']}."
            else:
                message = f"Your package with tracking number {tracking_data['tracking_number']} is currently {tracking_data['status']}."
        else:
            message = "I couldn't find a valid tracking number in your request. Please provide a tracking number or order number."
        
        # Format the response
        response = {
            "response": message,
            "tracking_data": tracking_data
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in package tracking processing: {e}")
        record_error("package_tracking", str(e))
        return {
            "response": "I'm sorry, I encountered an error while tracking your package. Please verify your tracking number and try again.",
            "error": str(e)
        }

def process_password_reset(user_input, context=None):
    """Process a password reset request."""
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    
    try:
        # Extract password reset information
        prompt = ChatPromptTemplate.from_template(
            "Extract password reset information from this query: {query}\n\n"
            "Extract the following fields:\n"
            "- email: The user's email address (if present)\n"
            "- username: The username (if present)\n"
            "- account_type: The account type (e.g., 'Staples.com', 'Rewards', 'Business')\n"
            "- issue: The specific issue (e.g., 'forgot password', 'account locked')\n\n"
            "Output JSON format with these fields. If a field is not found, set it to null."
        )
        
        llm = ChatOpenAI(temperature=0.0)
        extraction_chain = prompt | llm
        
        with TimingContext("llm_request"):
            result = extraction_chain.invoke({"query": user_input})
            content = result.content
        
        # Record LLM request metrics
        record_llm_request("password_reset_extraction", len(user_input), len(content))
        
        # Parse the extracted information
        extracted_info = None
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                extracted_json = json_match.group(1)
                extracted_info = json.loads(extracted_json)
            else:
                # Try direct JSON parsing
                extracted_info = json.loads(content)
        except:
            # If JSON parsing fails, create a simple response
            extracted_info = {
                "email": None,
                "username": None,
                "account_type": "Staples.com",
                "issue": "forgot password"
            }
            
            # Look for potential email addresses
            import re
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            match = re.search(email_pattern, user_input)
            if match:
                extracted_info["email"] = match.group(0)
        
        # In production, this would use a real password reset API
        # For this prototype, we use a simulation
        password_data = dict(PASSWORD_RESET_SAMPLE)  # Clone the sample data
        
        # Update with extracted info
        if extracted_info.get("email"):
            password_data["email"] = extracted_info["email"]
        if extracted_info.get("username"):
            password_data["username"] = extracted_info["username"]
        if extracted_info.get("account_type"):
            password_data["account_type"] = extracted_info["account_type"]
        if extracted_info.get("issue"):
            password_data["issue"] = extracted_info["issue"]
        
        # Generate a response message
        if password_data["email"]:
            message = f"I've sent password reset instructions to {password_data['email']}. Please check your email and follow the instructions to reset your password."
            password_data["reset_link_sent"] = True
        else:
            message = "I need your email address to send you password reset instructions. Could you please provide it?"
            password_data["reset_link_sent"] = False
        
        # Format the response
        response = {
            "response": message,
            "password_data": password_data
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in password reset processing: {e}")
        record_error("password_reset", str(e))
        return {
            "response": "I'm sorry, I encountered an error while processing your password reset request. Please try again or contact customer support for assistance.",
            "error": str(e)
        }

def process_store_locator(user_input, context=None):
    """Process a store locator request."""
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    
    try:
        # Extract store locator information
        prompt = ChatPromptTemplate.from_template(
            "Extract store locator information from this query: {query}\n\n"
            "Extract the following fields:\n"
            "- location: The location (zip code, city, address)\n"
            "- radius: Search radius in miles (default to 5 if not specified)\n"
            "- service: Specific service looking for (e.g., 'Copy & Print', 'Tech Services')\n\n"
            "Output JSON format with these fields. If a field is not found, set it to null."
        )
        
        llm = ChatOpenAI(temperature=0.0)
        extraction_chain = prompt | llm
        
        with TimingContext("llm_request"):
            result = extraction_chain.invoke({"query": user_input})
            content = result.content
        
        # Record LLM request metrics
        record_llm_request("store_locator_extraction", len(user_input), len(content))
        
        # Parse the extracted information
        extracted_info = None
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                extracted_json = json_match.group(1)
                extracted_info = json.loads(extracted_json)
            else:
                # Try direct JSON parsing
                extracted_info = json.loads(content)
        except:
            # If JSON parsing fails, create a simple response
            extracted_info = {
                "location": None,
                "radius": 5,
                "service": None
            }
            
            # Look for potential zip codes
            import re
            zip_pattern = r'\b\d{5}(?:-\d{4})?\b'
            match = re.search(zip_pattern, user_input)
            if match:
                extracted_info["location"] = match.group(0)
        
        # In production, this would use a real store locator API
        # For this prototype, we use a simulation
        store_data = dict(STORE_LOCATOR_SAMPLE)  # Clone the sample data
        
        # Update with extracted info
        if extracted_info.get("location"):
            store_data["location"] = extracted_info["location"]
        if extracted_info.get("radius"):
            store_data["radius"] = extracted_info["radius"]
        if extracted_info.get("service"):
            store_data["service"] = extracted_info["service"]
        
        # Generate a response message
        if store_data["location"]:
            if store_data["stores"]:
                store = store_data["stores"][0]
                message = f"I found a Staples store near {store_data['location']}:\n\n{store['store_name']}\n{store['store_address']}\nPhone: {store['store_phone']}\nHours: {store['store_hours']}"
                if store_data["service"] and store_data["service"] in store["services"]:
                    message += f"\n\nThis store offers {store_data['service']} services."
            else:
                message = f"I couldn't find any Staples stores within {store_data['radius']} miles of {store_data['location']}."
        else:
            message = "I need a location to find Staples stores near you. Could you please provide a zip code, city, or address?"
        
        # Format the response
        response = {
            "response": message,
            "store_data": store_data
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in store locator processing: {e}")
        record_error("store_locator", str(e))
        return {
            "response": "I'm sorry, I encountered an error while finding stores for you. Please try again with a valid location.",
            "error": str(e)
        }

def process_product_info(user_input, context=None):
    """Process a product information request."""
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    
    try:
        # Extract product information
        prompt = ChatPromptTemplate.from_template(
            "Extract product information query details from this input: {query}\n\n"
            "Extract the following fields:\n"
            "- product_name: The specific product name or description\n"
            "- product_id: The product ID or SKU (if present)\n"
            "- category: The product category (if mentioned)\n"
            "- search_query: The general search query\n\n"
            "Output JSON format with these fields. If a field is not found, set it to null."
        )
        
        llm = ChatOpenAI(temperature=0.0)
        extraction_chain = prompt | llm
        
        with TimingContext("llm_request"):
            result = extraction_chain.invoke({"query": user_input})
            content = result.content
        
        # Record LLM request metrics
        record_llm_request("product_info_extraction", len(user_input), len(content))
        
        # Parse the extracted information
        extracted_info = None
        try:
            # Try to extract JSON from the response
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                extracted_json = json_match.group(1)
                extracted_info = json.loads(extracted_json)
            else:
                # Try direct JSON parsing
                extracted_info = json.loads(content)
        except:
            # If JSON parsing fails, create a simple response
            extracted_info = {
                "product_name": None,
                "product_id": None,
                "category": None,
                "search_query": user_input
            }
        
        # In production, this would use a real product API
        # For this prototype, we use a simulation
        product_data = dict(PRODUCT_INFO_SAMPLE)  # Clone the sample data
        
        # Update with extracted info
        if extracted_info.get("search_query") and not extracted_info.get("product_name"):
            # In a real implementation, this would search the product database
            # For demo, we always return our sample product
            pass
        
        # Generate a response message
        message = f"Here's information about the {product_data['product_name']}:\n\nPrice: {product_data['price']}\nAvailability: {product_data['availability']}\n\n{product_data['description']}\n\nSpecifications:\n{product_data['specifications']}"
        
        # Format the response
        response = {
            "response": message,
            "product_data": product_data
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in product info processing: {e}")
        record_error("product_info", str(e))
        return {
            "response": "I'm sorry, I encountered an error while retrieving product information. Please try again with a different product or search term.",
            "error": str(e)
        }

def process_custom_agent(agent, user_input, context=None):
    """Process a request with a custom agent."""
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    
    try:
        # Get the agent configuration
        if not agent.prompt_templates:
            return {"response": "This custom agent is not properly configured."}
        
        # Parse the agent's prompt templates
        prompt_templates = agent.get_prompt_templates()
        
        # Use the main prompt if available, otherwise use the first available prompt
        main_prompt = None
        for template in prompt_templates:
            if template.get("is_main", False):
                main_prompt = template
                break
        
        if not main_prompt and prompt_templates:
            main_prompt = prompt_templates[0]
        
        if not main_prompt:
            return {"response": "This custom agent has no prompt templates configured."}
        
        # Get the prompt template content
        prompt_content = main_prompt.get("content", "")
        if not prompt_content:
            return {"response": "The agent's prompt template is empty."}
        
        # Create a ChatPromptTemplate
        prompt = ChatPromptTemplate.from_template(prompt_content)
        
        # Get prompt variables
        prompt_vars = {
            "input": user_input,
            "query": user_input,
            "user_input": user_input
        }
        
        # Add context variables if available
        if context:
            prompt_vars["context"] = context
        
        # Create the LLM with the agent's configuration
        temperature = 0.7  # Default temperature
        if agent.configuration:
            try:
                config = json.loads(agent.configuration)
                temperature = config.get("temperature", 0.7)
            except:
                pass
        
        llm = ChatOpenAI(temperature=temperature)
        chain = prompt | llm
        
        # Invoke the chain
        with TimingContext("custom_agent_llm"):
            result = chain.invoke(prompt_vars)
            content = result.content
        
        # Record LLM request metrics
        record_llm_request(f"custom_agent_{agent.id}", len(user_input), len(content))
        
        # Format the response
        response = {
            "response": content,
            "agent_name": agent.name,
            "agent_id": f"custom-{agent.id}"
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Error in custom agent processing: {e}")
        record_error(f"custom_agent_{agent.id}", str(e))
        return {
            "response": "I'm sorry, I encountered an error while processing your request with this custom agent. Please try again or contact support.",
            "error": str(e)
        }

@app.route('/documentation', methods=["GET"])
def documentation():
    """Render the comprehensive user documentation."""
    return render_template('documentation.html')

@app.route('/architecture', methods=["GET"])
def architecture():
    """Render the architecture documentation with block diagrams."""
    return render_template('architecture.html')

@app.route('/setup-guide', methods=["GET"])
def setup_guide():
    """Render the local setup guide."""
    return render_template('setup_guide.html')

@app.route('/dashboard', methods=["GET"])
def dashboard():
    """Render the observability dashboard."""
    return render_template('dashboard.html')

@app.route('/api/metrics', methods=["GET"])
def metrics():
    """Provide Prometheus metrics endpoint."""
    return Response(get_prometheus_metrics(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/api/dashboard-metrics', methods=["GET"])
def dashboard_metrics():
    """Provide metrics for the dashboard."""
    try:
        # Get time period from request
        period = request.args.get('period', 'day')
        metrics = get_metrics_summary(period)
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/agent-builder', methods=["GET"])
def agent_builder():
    """Render the agent builder interface."""
    return render_template('agent_builder.html')

@app.route('/agent-management-docs', methods=["GET"])
def agent_management_docs():
    """Render the agent management documentation."""
    return render_template('agent_management_doc.html')

@app.route('/agent-wizard', methods=["GET"])
@app.route('/agent-wizard/<int:agent_id>', methods=["GET"])
@app.route('/agent-wizard/<int:agent_id>/step/<int:step>', methods=["GET"])
def agent_wizard(agent_id=None, step=1):
    """Render the agent configuration wizard interface."""
    try:
        # For a new agent
        if agent_id is None:
            # Create a new agent
            new_agent = CustomAgent(
                name=f"New Agent {datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                description="Custom agent created through the wizard",
                is_active=False,
                creator=request.args.get('creator', 'Unknown')
            )
            # Store the current step in session instead of model
            session['current_wizard_step'] = 1
            db.session.add(new_agent)
            db.session.commit()
            
            # Use the newly created agent for the rest of this function
            agent_id = new_agent.id
            agent = new_agent
        else:
            # Get the existing agent
            agent = CustomAgent.query.get_or_404(agent_id)
        
        # Ensure valid step
        if step < 1:
            step = 1
        if step > 5:  # assume 5 steps maximum
            step = 5
        
        # Wizard step templates
        wizard_templates = {
            1: 'agent_wizard_step1.html',  # Basic information
            2: 'agent_wizard_step2.html',  # Entity definitions
            3: 'agent_wizard_step3.html',  # Prompt templates
            4: 'agent_wizard_step4.html',  # Response formats
            5: 'agent_wizard_step5.html'   # Review and finalize
        }
        
        # Get data for the current step
        step_data = {}
        if step == 1:
            # Basic information
            step_data = {
                "name": agent.name,
                "description": agent.description,
                "creator": agent.creator,
                "icon": agent.icon
            }
        elif step == 2:
            # Entity definitions
            step_data = {
                "entity_definitions": agent.get_entity_definitions() or []
            }
        elif step == 3:
            # Prompt templates
            step_data = {
                "prompt_templates": agent.get_prompt_templates() or [],
                "prompts": {
                    "system": agent.get_system_prompt() or "",
                    "entity_extraction": agent.get_entity_extraction_prompt() or "",
                    "response_generation": agent.get_response_generation_prompt() or ""
                }
            }
        elif step == 4:
            # Response formats
            step_data = {
                "response_formats": agent.get_response_formats() or []
            }
        elif step == 5:
            # Review all data
            step_data = {
                "name": agent.name,
                "description": agent.description,
                "creator": agent.creator,
                "icon": agent.icon,
                "entity_definitions": agent.get_entity_definitions() or [],
                "prompt_templates": agent.get_prompt_templates() or [],
                "response_formats": agent.get_response_formats() or [],
                "business_rules": agent.get_business_rules() or []
            }
        
        # Get current step from session or use the step parameter
        current_step = session.get('current_wizard_step', step)
        
        return render_template(
            'agent_wizard.html',
            agent=agent,
            agent_id=agent.id if agent else None,  # Pass agent_id explicitly
            step=step,
            current_step=current_step,  # Pass current_step to the template
            step_template=wizard_templates.get(step, 'agent_wizard_step1.html'),
            step_data=step_data,
            total_steps=len(wizard_templates)
        )
        
    except Exception as e:
        logger.error(f"Error in agent wizard: {e}")
        return render_template('error.html', error=str(e))

@app.route('/agent-wizard/step/<int:step>', methods=['POST'])
@app.route('/agent-wizard/<int:agent_id>/step/<int:step>', methods=['POST'])
def agent_wizard_save(agent_id=None, step=1):
    """Save the current step of the agent wizard and move to the next."""
    try:
        # Get the agent or create if agent_id is None or doesn't exist
        if agent_id is None:
            # Create a new agent with a unique timestamp
            unique_timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            agent = CustomAgent(
                name=f"New Agent {unique_timestamp}",
                description="Custom agent created through the wizard",
                is_active=False,
                creator=request.args.get('creator', 'Unknown')
            )
            db.session.add(agent)
            db.session.commit()
            agent_id = agent.id
        else:
            agent = CustomAgent.query.get_or_404(agent_id)
        
        # Process form data based on step
        if step == 1:
            try:
                # Save basic information
                agent.name = request.form.get('name', agent.name)
                agent.description = request.form.get('description', agent.description)
                agent.creator = request.form.get('creator', agent.creator)
                agent.icon = request.form.get('icon', agent.icon)
                
                # Try a flush to check for name uniqueness constraints
                db.session.flush()
            except sqlalchemy.exc.IntegrityError as ie:
                # Roll back the transaction
                db.session.rollback()
                
                # If it's a uniqueness constraint violation
                if "unique constraint" in str(ie).lower() and "custom_agents_name_key" in str(ie):
                    # Make the name unique by appending a timestamp
                    unique_timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                    original_name = request.form.get('name', agent.name)
                    agent.name = f"{original_name} {unique_timestamp}"
                    
                    # Add a flash message
                    flash(f"An agent with the name '{original_name}' already exists. Your agent has been named '{agent.name}' instead.", "warning")
                else:
                    # Re-raise the exception if it's not a name uniqueness issue
                    raise
        
        elif step == 2:
            # Save entity definitions
            entity_definitions = []
            entity_count = int(request.form.get('entity_count', 0))
            
            # Process form data with the new naming convention
            for i in range(entity_count):
                entity_name = request.form.get(f'entities[{i}][name]', '')
                if entity_name:  # Only add entities that have a name
                    entity = {
                        "name": entity_name,
                        "description": request.form.get(f'entities[{i}][description]', ''),
                        "required": request.form.get(f'entities[{i}][required]') == 'on',
                        "validation_pattern": request.form.get(f'entities[{i}][validation_pattern]', ''),
                        "error_message": request.form.get(f'entities[{i}][error_message]', ''),
                        "examples": request.form.get(f'entities[{i}][examples]', '').split(',')
                    }
                    entity_definitions.append(entity)
            
            agent.entity_definitions = json.dumps(entity_definitions)
        
        elif step == 3:
            # Save prompt templates
            prompt_templates = []
            template_count = int(request.form.get('template_count', 0))
            
            for i in range(template_count):
                template = {
                    "name": request.form.get(f'template_name_{i}', ''),
                    "description": request.form.get(f'template_description_{i}', ''),
                    "content": request.form.get(f'template_content_{i}', ''),
                    "is_main": request.form.get(f'template_is_main_{i}') == 'on'
                }
                prompt_templates.append(template)
            
            agent.prompt_templates = json.dumps(prompt_templates)
        
        elif step == 4:
            # Save response formats
            response_formats = []
            format_count = int(request.form.get('format_count', 0))
            
            for i in range(format_count):
                format_obj = {
                    "name": request.form.get(f'format_name_{i}', ''),
                    "description": request.form.get(f'format_description_{i}', ''),
                    "schema": request.form.get(f'format_schema_{i}', ''),
                    "example": request.form.get(f'format_example_{i}', '')
                }
                response_formats.append(format_obj)
            
            agent.response_formats = json.dumps(response_formats)
        
        elif step == 5:
            # Finalize agent
            agent.is_active = request.form.get('activate_agent') == 'on'
            agent.wizard_completed = True
            # Store current step in session
            session['current_wizard_step'] = 5
            
            # Set any additional configuration
            agent_config = {
                "temperature": float(request.form.get('temperature', 0.7)),
                "max_tokens": int(request.form.get('max_tokens', 1000)),
                "top_p": float(request.form.get('top_p', 1.0)),
                "frequency_penalty": float(request.form.get('frequency_penalty', 0.0)),
                "presence_penalty": float(request.form.get('presence_penalty', 0.0))
            }
            agent.configuration = json.dumps(agent_config)
            
            # Redirect to agent builder after completion
            db.session.commit()
            return redirect(url_for('agent_builder'))
        
        # Update wizard progress in session
        session['current_wizard_step'] = step + 1
        
        # Save the agent
        db.session.commit()
        
        # Move to the next step
        return redirect(url_for('agent_wizard', agent_id=agent.id, step=step + 1))
        
    except Exception as e:
        logger.error(f"Error saving agent wizard step: {e}")
        return render_template('error.html', error=str(e))

@app.route('/template-gallery', methods=["GET"])
def template_gallery():
    """Render the agent template gallery."""
    try:
        # Get all templates
        all_templates = AgentTemplate.query.all()
        
        # Filter featured templates
        featured_templates = [t for t in all_templates if t.is_featured]
        
        # Filter remaining templates (not featured)
        templates = [t for t in all_templates if not t.is_featured]
        
        return render_template(
            'template_gallery.html', 
            featured_templates=featured_templates,
            templates=templates
        )
        
    except Exception as e:
        logger.error(f"Error in template gallery: {e}")
        return render_template('error.html', error=str(e))

@app.route('/api/templates', methods=["GET"])
def list_templates():
    """List all agent templates."""
    try:
        templates = AgentTemplate.query.all()
        
        # Format the template data
        template_data = []
        for template in templates:
            template_data.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "icon": template.icon,
                "screenshot": template.screenshot,
                "is_featured": template.is_featured,
                "author": template.author,
                "downloads": template.downloads,
                "rating": template.rating,
                "rating_count": template.rating_count,
                "tags": template.get_tags_list(),
                "created_at": template.created_at.isoformat() if template.created_at else None
            })
        
        return jsonify({"templates": template_data})
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/templates/<int:template_id>', methods=["GET"])
def get_template(template_id):
    """Get a specific agent template with all its configuration data."""
    try:
        template = AgentTemplate.query.get_or_404(template_id)
        
        # Format the complete response
        template_data = {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "icon": template.icon,
            "screenshot": template.screenshot,
            "is_featured": template.is_featured,
            "author": template.author,
            "author_email": template.author_email,
            "downloads": template.downloads,
            "rating": template.rating,
            "rating_count": template.rating_count,
            "tags": template.get_tags_list(),
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
            "entity_definitions": template.get_entity_definitions(),
            "prompt_templates": template.get_prompt_templates(),
            "response_formats": template.get_response_formats(),
            "business_rules": template.get_business_rules()
        }
        
        # Wrap response in success object with template data
        result = {
            "success": True,
            "template": template_data
        }
        
        # Increment download count
        template.downloads += 1
        db.session.commit()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/save-as-template', methods=["POST"])
def save_as_template():
    """Save a custom agent as a reusable template."""
    try:
        data = request.json
        agent_id = data.get('agent_id')
        
        if not agent_id:
            return jsonify({"error": "Missing required parameter: agent_id"}), 400
        
        # Get the agent
        agent = CustomAgent.query.get_or_404(agent_id)
        
        # Create a template configuration from agent data
        template_config = {
            "entity_definitions": agent.get_entity_definitions(),
            "prompt_templates": agent.get_prompt_templates(),
            "response_formats": agent.get_response_formats(),
            "business_rules": agent.get_business_rules(),
            "components": []
        }
        
        # Create a new template
        template = AgentTemplate(
            name=data.get('name', f"Template from {agent.name}"),
            description=data.get('description', agent.description),
            category=data.get('category', "Custom"),
            icon=agent.icon,
            author=data.get('author', agent.creator),
            author_email=data.get('author_email'),
            tags=data.get('tags', ""),
            is_featured=False,
            is_system=False,
            configuration=json.dumps(template_config)
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "template_id": template.id,
            "message": f"Agent saved as template: {template.name}"
        })
        
    except Exception as e:
        logger.error(f"Error saving as template: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download-requirements', methods=["GET"])
def download_requirements():
    """Provide the requirements file for download."""
    try:
        # Get environment from query params
        env = request.args.get('env', 'development')
        
        # Basic requirements that are always needed
        requirements = [
            "flask==2.2.3",
            "flask-sqlalchemy==3.0.3",
            "flask-cors==3.0.10",
            "langchain==0.0.267",
            "langchain_openai==0.0.2.post1",
            "openai==1.3.7",
            "psycopg2-binary==2.9.6",
            "prometheus-client==0.17.1",
            "gunicorn==21.2.0",
            "python-dotenv==1.0.0"
        ]
        
        # Add environment specific requirements
        if env == 'development':
            requirements.extend([
                "pytest==7.3.1",
                "black==23.3.0",
                "flake8==6.0.0"
            ])
        elif env == 'testing':
            requirements.extend([
                "pytest==7.3.1",
                "pytest-flask==1.2.0",
                "selenium==4.9.1",
                "webdriver-manager==3.8.6"
            ])
        
        # Format the requirements
        requirements_text = "\n".join(requirements)
        
        # Return as a downloadable file
        return Response(
            requirements_text,
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment;filename=requirements-{env}.txt"}
        )
        
    except Exception as e:
        logger.error(f"Error generating requirements: {e}")
        return jsonify({"error": str(e)}), 500

# Direct agent endpoints for specific functionality
@app.route('/api/track-package', methods=["POST"])
def track_package():
    """Track a package directly."""
    try:
        data = request.json
        user_input = data.get('user_input')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not user_input:
            return jsonify({"error": "Missing required parameter: user_input"}), 400
        
        # Get session context from memory if available
        context = app.staples_brain.memory.get_context(session_id)
        
        # Process with package tracking agent
        response = process_package_tracking(user_input, context)
        
        # Add conversation ID to the response
        response["session_id"] = session_id
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error tracking package: {e}")
        return jsonify({
            "error": "An error occurred tracking your package",
            "details": str(e),
            "response": "I'm sorry, but I encountered an error tracking your package. Please try again with a valid tracking number."
        }), 500

@app.route('/api/reset-password', methods=["POST"])
def reset_password():
    """Reset password directly."""
    try:
        data = request.json
        user_input = data.get('user_input')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not user_input:
            return jsonify({"error": "Missing required parameter: user_input"}), 400
        
        # Get session context from memory if available
        context = app.staples_brain.memory.get_context(session_id)
        
        # Process with password reset agent
        response = process_password_reset(user_input, context)
        
        # Add session ID to the response
        response["session_id"] = session_id
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        return jsonify({
            "error": "An error occurred resetting your password",
            "details": str(e),
            "response": "I'm sorry, but I encountered an error processing your password reset request. Please try again or contact customer support for assistance."
        }), 500

@app.route('/api/find-store', methods=["POST"])
def find_store():
    """Find store locations directly."""
    try:
        data = request.json
        user_input = data.get('user_input')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not user_input:
            return jsonify({"error": "Missing required parameter: user_input"}), 400
        
        # Get session context from memory if available
        context = app.staples_brain.memory.get_context(session_id)
        
        # Process with store locator agent
        response = process_store_locator(user_input, context)
        
        # Add session ID to the response
        response["session_id"] = session_id
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error finding store: {e}")
        return jsonify({
            "error": "An error occurred finding stores",
            "details": str(e),
            "response": "I'm sorry, but I encountered an error finding stores near you. Please try again with a valid location."
        }), 500

@app.route('/api/product-info', methods=["POST"])
def product_info():
    """Get product information directly."""
    try:
        data = request.json
        user_input = data.get('user_input')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not user_input:
            return jsonify({"error": "Missing required parameter: user_input"}), 400
        
        # Get session context from memory if available
        context = app.staples_brain.memory.get_context(session_id)
        
        # Process with product info agent
        response = process_product_info(user_input, context)
        
        # Add session ID to the response
        response["session_id"] = session_id
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting product info: {e}")
        return jsonify({
            "error": "An error occurred retrieving product information",
            "details": str(e),
            "response": "I'm sorry, but I encountered an error retrieving product information. Please try again with a different product search."
        }), 500