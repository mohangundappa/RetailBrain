import os
import logging
import asyncio
import uuid
import time
import random
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, Response, g, redirect, url_for
from flask_cors import CORS
from prometheus_client import CONTENT_TYPE_LATEST
from brain.intent_handler import IntentHandler
from brain.planner import ExecutionPlanner
from models import db, Conversation, Message, PackageTracking, PasswordReset, StoreLocator, ProductInfo, AgentConfig, AnalyticsData, CustomAgent, AgentTemplate
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
from utils.middleware import MetricsMiddleware

# Configure logging to file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("staples_brain.log")
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "staples-brain-secret-key")

# Enable CORS for API endpoints
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Apply metrics middleware
MetricsMiddleware(app)

# Import API routes
from api.routes import api_bp
app.register_blueprint(api_bp)

# Create database tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created")

# Initialize components
intent_handler = IntentHandler()
planner = ExecutionPlanner(intent_handler)

# Sample data for simulating agent responses
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

@app.route('/')
def index():
    # Get some stats for the home page
    stats = {
        "conversation_count": Conversation.query.count(),
        "package_tracking_count": PackageTracking.query.count(),
        "password_reset_count": PasswordReset.query.count(),
        "available_agents": ["Package Tracking Agent", "Reset Password Agent", "Store Locator Agent", "Product Information Agent"],
        "database_connected": True,
        "llm_integration": os.environ.get("OPENAI_API_KEY") is not None
    }
    
    return render_template('index.html', stats=stats)

@app.route('/api/health', methods=["GET"])
def health_check():
    """Health check endpoint."""
    # Check if LLM integration is available
    has_llm = os.environ.get("OPENAI_API_KEY") is not None
    
    return jsonify({
        "status": "healthy",
        "message": "Staples Brain is running",
        "version": "1.0.0",
        "agents": ["Package Tracking Agent", "Reset Password Agent", "Store Locator Agent", "Product Information Agent"],
        "llm_integration": "available" if has_llm else "unavailable"
    })

@app.route('/api/agents', methods=["GET"])
def list_agents():
    """List all available agents."""
    return jsonify({
        "success": True,
        "agents": ["Package Tracking Agent", "Reset Password Agent", "Store Locator Agent", "Product Information Agent"]
    })

@app.route('/api/conversations', methods=["GET"])
def list_conversations():
    """List all conversations."""
    try:
        # Get session ID from cookie or query parameter
        if 'session_id' in session:
            session_id = session.get('session_id')
        else:
            session_id = request.args.get('session_id')
            
        # If session_id is provided, filter by it
        if session_id:
            conversations = Conversation.query.filter_by(session_id=session_id).order_by(Conversation.created_at.desc()).all()
        else:
            # Otherwise return all conversations (with pagination)
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            conversations = Conversation.query.order_by(Conversation.created_at.desc()).paginate(page=page, per_page=per_page)
            conversations = conversations.items
            
        result = []
        for conv in conversations:
            result.append({
                "id": conv.id,
                "session_id": conv.session_id,
                "user_input": conv.user_input,
                "brain_response": conv.brain_response,
                "intent": conv.intent,
                "confidence": conv.confidence,
                "selected_agent": conv.selected_agent,
                "created_at": conv.created_at.isoformat()
            })
            
        return jsonify({
            "success": True,
            "conversations": result
        })
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
        
@app.route('/api/conversations/<int:conversation_id>', methods=["GET"])
def get_conversation(conversation_id):
    """Get a specific conversation with all its messages and related data."""
    try:
        # Get the conversation
        conversation = Conversation.query.get(conversation_id)
        
        if not conversation:
            return jsonify({
                "success": False,
                "error": f"Conversation with ID {conversation_id} not found"
            }), 404
            
        # Get messages
        messages = []
        for msg in conversation.messages:
            messages.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            })
            
        # Get tracking data if available
        tracking_data = None
        if conversation.tracking_data:
            tracking = conversation.tracking_data[0]  # Get the first tracking entry
            tracking_data = {
                "id": tracking.id,
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
            reset = conversation.password_reset_data[0]  # Get the first reset entry
            password_reset_data = {
                "id": reset.id,
                "email": reset.email,
                "username": reset.username,
                "account_type": reset.account_type,
                "issue": reset.issue,
                "reset_link_sent": reset.reset_link_sent
            }
            
        # Get store locator data if available
        store_locator_data = None
        if conversation.store_locator_data:
            store = conversation.store_locator_data[0]  # Get the first store entry
            store_locator_data = {
                "id": store.id,
                "location": store.location,
                "radius": store.radius,
                "service": store.service,
                "store_id": store.store_id,
                "store_name": store.store_name,
                "store_address": store.store_address,
                "store_phone": store.store_phone,
                "store_hours": store.store_hours
            }
        
        # Get product info data if available
        product_info_data = None
        if conversation.product_info_data:
            product = conversation.product_info_data[0]  # Get the first product entry
            product_info_data = {
                "id": product.id,
                "product_name": product.product_name,
                "product_id": product.product_id,
                "category": product.category,
                "price": product.price,
                "availability": product.availability,
                "description": product.description,
                "specifications": product.specifications,
                "search_query": product.search_query
            }
            
        # Build the full conversation object
        result = {
            "id": conversation.id,
            "session_id": conversation.session_id,
            "user_input": conversation.user_input,
            "brain_response": conversation.brain_response,
            "intent": conversation.intent,
            "confidence": conversation.confidence,
            "selected_agent": conversation.selected_agent,
            "created_at": conversation.created_at.isoformat(),
            "messages": messages,
            "tracking_data": tracking_data,
            "password_reset_data": password_reset_data,
            "store_locator_data": store_locator_data,
            "product_info_data": product_info_data
        }
            
        return jsonify({
            "success": True,
            "conversation": result
        })
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/process', methods=["POST"])
def process_request():
    """Process a user request with LLM-based intent identification."""
    start_time = time.time()
    data = request.json
    
    if not data or "input" not in data:
        return jsonify({
            "success": False,
            "error": "Missing required field: input"
        }), 400
    
    user_input = data["input"]
    context = data.get("context", {})
    
    # Create or get session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session.get('session_id')
    
    # Add session_id to context
    context['session_id'] = session_id
    
    # Check if we should continue with the same agent from previous conversation
    if data.get('continue_with_same_agent', False):
        context['continue_with_same_agent'] = True
    
    # Run the async planning process in a new event loop
    try:
        # Track the process with metrics
        with TimingContext('intent_classification', {'session_id': session_id}):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create a plan using the intent handler and planner
            plan_result = loop.run_until_complete(planner.create_plan(user_input))
            loop.close()
            
            intent = plan_result.get("intent", "unknown")
            confidence = plan_result.get("confidence", 0.0)
            
            # Record intent classification metrics
            record_intent_classification(intent, confidence)
            
            logger.info(f"Identified intent: {intent} with confidence {confidence}")
        
        # If no suitable intent was found or confidence is too low
        if intent == "unknown" or confidence < 0.3:
            response_text = "I'm sorry, I don't have the capability to help with that request at the moment. I can assist with package tracking, password reset, store location, and product information inquiries."
            
            # Store in database even when no suitable agent is found
            conversation = Conversation(
                session_id=session_id,
                user_input=user_input,
                brain_response=response_text,
                intent="unknown",
                confidence=confidence,
                selected_agent="Unknown"
            )
            db.session.add(conversation)
            
            # Add messages
            user_message = Message(
                conversation=conversation,
                role="user",
                content=user_input
            )
            assistant_message = Message(
                conversation=conversation,
                role="assistant",
                content=response_text
            )
            db.session.add_all([user_message, assistant_message])
            db.session.commit()
            
            # Add conversation ID to the response for memory tracking
            return jsonify({
                "success": False,
                "error": "No suitable agent found",
                "response": response_text,
                "confidence": confidence,
                "conversation_id": conversation.id
            })
        
        # Get the entities extracted by the intent handler
        entities = plan_result.get("entities", {})
        
        # Handle different intents
        if intent == "package_tracking":
            # Update tracking info with extracted entities
            tracking_info = PACKAGE_TRACKING_SAMPLE.copy()
            if entities:
                for key in ["tracking_number", "shipping_carrier", "order_number", "time_frame"]:
                    if key in entities and entities[key]:
                        tracking_info[key] = entities[key]
            
            # Generate LLM-based response when available
            if os.environ.get("OPENAI_API_KEY"):
                # Generate the response text using GPT-4
                from langchain_openai import ChatOpenAI
                from langchain_core.prompts import ChatPromptTemplate
                
                template = """
                You are a helpful customer service assistant at Staples. Generate a friendly, 
                conversational response about package tracking based on this information:
                
                User query: {query}
                
                Package tracking information:
                {tracking_info}
                
                Keep your response concise and conversational, as if you're speaking directly to the customer.
                Focus on the most important details about their package status.
                """
                
                prompt = ChatPromptTemplate.from_template(template)
                llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
                chain = prompt | llm
                
                # Track LLM request metrics
                with TimingContext('llm_request', {'model': 'gpt-4o', 'endpoint': 'completion'}):
                    llm_response = loop.run_until_complete(chain.ainvoke({
                        "query": user_input,
                        "tracking_info": str(tracking_info)
                    }))
                    
                    # Estimate token usage 
                    prompt_tokens = len(template) // 4  # Rough estimate
                    completion_tokens = len(llm_response.content) // 4  # Rough estimate
                    
                    # Record token usage
                    record_llm_request('gpt-4o', 'completion', prompt_tokens, completion_tokens)
                
                response_text = llm_response.content
            else:
                response_text = f"Your package with tracking number {tracking_info['tracking_number']} is currently {tracking_info['status'].replace('_', ' ')} and expected to be delivered on {tracking_info['estimated_delivery']}. It's currently in {tracking_info['current_location']} and should arrive at your location soon."
            
            # Store conversation in database
            conversation = Conversation(
                session_id=session_id,
                user_input=user_input,
                brain_response=response_text,
                intent=intent,
                confidence=confidence,
                selected_agent="Package Tracking Agent"
            )
            db.session.add(conversation)
            
            # Add messages
            user_message = Message(
                conversation=conversation,
                role="user",
                content=user_input
            )
            assistant_message = Message(
                conversation=conversation,
                role="assistant",
                content=response_text
            )
            db.session.add_all([user_message, assistant_message])
            
            # Add package tracking info
            package_tracking = PackageTracking(
                conversation=conversation,
                tracking_number=tracking_info["tracking_number"],
                shipping_carrier=tracking_info["shipping_carrier"],
                order_number=tracking_info["order_number"],
                status=tracking_info["status"],
                estimated_delivery=tracking_info["estimated_delivery"],
                current_location=tracking_info["current_location"],
                last_updated=datetime.utcnow()
            )
            db.session.add(package_tracking)
            db.session.commit()
            
            # Return the response
            return jsonify({
                "agent": "Package Tracking Agent",
                "response": response_text,
                "tracking_info": {
                    "tracking_number": tracking_info["tracking_number"],
                    "shipping_carrier": tracking_info["shipping_carrier"],
                    "order_number": tracking_info["order_number"],
                    "time_frame": tracking_info["time_frame"]
                },
                "package_status": tracking_info,
                "success": True,
                "selected_agent": "Package Tracking Agent",
                "confidence": confidence,
                "intent": intent,
                "entities": entities,
                "conversation_id": conversation.id
            })
            
        elif intent == "password_reset":
            # Update account info with extracted entities
            account_info = {
                "email": PASSWORD_RESET_SAMPLE["email"],
                "username": PASSWORD_RESET_SAMPLE["username"],
                "account_type": PASSWORD_RESET_SAMPLE["account_type"],
                "issue": PASSWORD_RESET_SAMPLE["issue"]
            }
            
            if entities:
                for key in ["email", "username", "account_type", "issue"]:
                    if key in entities and entities[key]:
                        account_info[key] = entities[key]
            
            # Generate LLM-based response when available
            if os.environ.get("OPENAI_API_KEY"):
                # Generate the response text using GPT-4
                from langchain_openai import ChatOpenAI
                from langchain_core.prompts import ChatPromptTemplate
                
                template = """
                You are a helpful customer service assistant at Staples. Generate a friendly, 
                conversational response about password reset based on this information:
                
                User query: {query}
                
                Account information:
                {account_info}
                
                Reset instructions:
                {reset_instructions}
                
                Keep your response concise and conversational, as if you're speaking directly to the customer.
                Explain the password reset process clearly and reassuringly.
                """
                
                prompt = ChatPromptTemplate.from_template(template)
                llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
                chain = prompt | llm
                
                llm_response = loop.run_until_complete(chain.ainvoke({
                    "query": user_input,
                    "account_info": str(account_info),
                    "reset_instructions": str(PASSWORD_RESET_SAMPLE["instructions"])
                }))
                
                response_text = llm_response.content
            else:
                response_text = f"I've sent password reset instructions to your email address ({account_info['email']}). Please check your inbox and follow the instructions to create a new password. The email should arrive within the next few minutes. If you don't see it, please check your spam folder."
            
            # Store conversation in database
            conversation = Conversation(
                session_id=session_id,
                user_input=user_input,
                brain_response=response_text,
                intent=intent,
                confidence=confidence,
                selected_agent="Reset Password Agent"
            )
            db.session.add(conversation)
            
            # Add messages
            user_message = Message(
                conversation=conversation,
                role="user",
                content=user_input
            )
            assistant_message = Message(
                conversation=conversation,
                role="assistant",
                content=response_text
            )
            db.session.add_all([user_message, assistant_message])
            
            # Add password reset info
            password_reset = PasswordReset(
                conversation=conversation,
                email=account_info["email"],
                username=account_info["username"],
                account_type=account_info["account_type"],
                issue=account_info["issue"],
                reset_link_sent=PASSWORD_RESET_SAMPLE["reset_link_sent"]
            )
            db.session.add(password_reset)
            db.session.commit()
            
            # Return the response
            return jsonify({
                "agent": "Reset Password Agent",
                "response": response_text,
                "account_info": account_info,
                "reset_status": {
                    "status": PASSWORD_RESET_SAMPLE["status"],
                    "message": f"Password reset instructions for your account with email: {account_info['email']}",
                    "instructions": PASSWORD_RESET_SAMPLE["instructions"],
                    "reset_link_sent": PASSWORD_RESET_SAMPLE["reset_link_sent"],
                    "is_simulated": PASSWORD_RESET_SAMPLE["is_simulated"]
                },
                "success": True,
                "selected_agent": "Reset Password Agent",
                "confidence": confidence,
                "intent": intent,
                "entities": entities,
                "conversation_id": conversation.id
            })
        
        else:
            # Should not reach here based on earlier check, but just in case
            response_text = "I'm sorry, I don't have the capability to help with that request at the moment."
            
            # Store in database even for unsupported intent
            conversation = Conversation(
                session_id=session_id,
                user_input=user_input,
                brain_response=response_text,
                intent=intent,
                confidence=confidence,
                selected_agent="Unknown"
            )
            db.session.add(conversation)
            
            # Add messages
            user_message = Message(
                conversation=conversation,
                role="user",
                content=user_input
            )
            assistant_message = Message(
                conversation=conversation,
                role="assistant",
                content=response_text
            )
            db.session.add_all([user_message, assistant_message])
            db.session.commit()
            
            return jsonify({
                "success": False,
                "error": "Unsupported intent",
                "response": response_text,
                "confidence": confidence,
                "intent": intent,
                "conversation_id": conversation.id
            })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        response_text = "I'm sorry, I encountered an error while processing your request. Please try again or rephrase your question."
        
        try:
            # Store error in database
            conversation = Conversation(
                session_id=session_id if 'session_id' in session else str(uuid.uuid4()),
                user_input=user_input,
                brain_response=response_text,
                intent="error",
                confidence=0.0,
                selected_agent="Error"
            )
            db.session.add(conversation)
            
            # Add messages
            user_message = Message(
                conversation=conversation,
                role="user",
                content=user_input
            )
            assistant_message = Message(
                conversation=conversation,
                role="assistant",
                content=response_text
            )
            db.session.add_all([user_message, assistant_message])
            db.session.commit()
            conversation_id = conversation.id
        except Exception as db_error:
            logger.error(f"Error storing conversation in database: {str(db_error)}", exc_info=True)
            conversation_id = None
        
        return jsonify({
            "success": False,
            "error": str(e),
            "response": response_text,
            "conversation_id": conversation_id
        }), 500

@app.route('/api/track-package', methods=["POST"])
def track_package():
    """Track a package directly."""
    data = request.json
    
    # Record agent selection metric
    record_agent_selection("Package Tracking Agent")
    
    # Create or get session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session.get('session_id')
    
    # Extract tracking number if provided
    tracking_number = data.get("tracking_number", "TRACK123456") if data else "TRACK123456"
    query = data.get("query", f"Track my package {tracking_number}") if data else f"Track my package {tracking_number}"
    
    # Get or create conversation memory
    from utils.memory import ConversationMemory
    memory = ConversationMemory(session_id)
    
    # Create a modified copy with the provided tracking number
    tracking_info = PACKAGE_TRACKING_SAMPLE.copy()
    tracking_info["tracking_number"] = tracking_number
    
    # Store tracking info in memory
    memory.update_working_memory('current_tracking_number', tracking_number)
    memory.update_working_memory('current_package_status', tracking_info["status"])
    
    # Check if there's conversation history to include
    history_context = ""
    history = memory.load_conversation_history()
    if history:
        # Include only the last 2 messages for context
        recent_history = history[-min(2, len(history)):]
        history_context = "\n".join([
            f"{msg['role'].title()}: {msg['content']}" 
            for msg in recent_history
        ])
    
    # Generate LLM-based response when available
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            
            template = """
            You are a helpful customer service assistant at Staples. Generate a friendly, 
            conversational response about package tracking based on this information:
            
            Tracking number: {tracking_number}
            
            Package status: {status}
            Estimated delivery: {delivery_date}
            Current location: {location}
            """
            
            # Include conversation history context if available
            if history_context:
                template += f"""
                
                Recent conversation history:
                {history_context}
                """
            
            template += """
            
            Keep your response concise (50 words max) and conversational, as if you're speaking directly to the customer.
            If this is a follow-up to a previous conversation, maintain continuity.
            """
            
            prompt = ChatPromptTemplate.from_template(template)
            llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
            chain = prompt | llm
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            llm_response = loop.run_until_complete(chain.ainvoke({
                "tracking_number": tracking_number,
                "status": tracking_info["status"].replace("_", " "),
                "delivery_date": tracking_info["estimated_delivery"],
                "location": tracking_info["current_location"]
            }))
            
            loop.close()
            response_text = llm_response.content
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}", exc_info=True)
            response_text = f"Your package with tracking number {tracking_number} is currently in transit and expected to be delivered in 3 days. It's currently in Chicago, IL and should arrive at your location soon."
    else:
        response_text = f"Your package with tracking number {tracking_number} is currently in transit and expected to be delivered in 3 days. It's currently in Chicago, IL and should arrive at your location soon."
    
    # Store conversation in database
    conversation = Conversation(
        session_id=session_id,
        user_input=query,
        brain_response=response_text,
        intent="package_tracking",
        confidence=1.0,
        selected_agent="Package Tracking Agent"
    )
    db.session.add(conversation)
    
    # Add messages
    user_message = Message(
        conversation=conversation,
        role="user",
        content=query
    )
    assistant_message = Message(
        conversation=conversation,
        role="assistant",
        content=response_text
    )
    db.session.add_all([user_message, assistant_message])
    
    # Add package tracking info
    package_tracking = PackageTracking(
        conversation=conversation,
        tracking_number=tracking_info["tracking_number"],
        shipping_carrier=tracking_info["shipping_carrier"],
        order_number=tracking_info["order_number"],
        status=tracking_info["status"],
        estimated_delivery=tracking_info["estimated_delivery"],
        current_location=tracking_info["current_location"],
        last_updated=datetime.utcnow()
    )
    db.session.add(package_tracking)
    db.session.commit()
    
    # Update agent context with tracking info
    memory.update_context("Package Tracking Agent", {
        "last_tracking": {
            "tracking_number": tracking_number,
            "status": tracking_info["status"],
            "estimated_delivery": tracking_info["estimated_delivery"],
            "conversation_id": conversation.id
        }
    })
    
    return jsonify({
        "agent": "Package Tracking Agent",
        "response": response_text,
        "tracking_info": {
            "tracking_number": tracking_number,
            "shipping_carrier": tracking_info["shipping_carrier"],
            "order_number": tracking_info["order_number"],
            "time_frame": tracking_info["time_frame"]
        },
        "package_status": tracking_info,
        "success": True,
        "conversation_id": conversation.id
    })

@app.route('/api/reset-password', methods=["POST"])
def reset_password():
    """Reset password directly."""
    data = request.json
    
    # Record agent selection metric
    record_agent_selection("Reset Password Agent")
    
    # Create or get session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session.get('session_id')
    
    # Extract email if provided
    email = data.get("email", "user@example.com") if data else "user@example.com"
    query = data.get("query", f"Reset password for {email}") if data else f"Reset password for {email}"
    
    # Get or create conversation memory
    from utils.memory import ConversationMemory
    memory = ConversationMemory(session_id)
    
    # Store account info in memory
    memory.update_working_memory('current_email', email)
    
    # Check if there's conversation history to include
    history_context = ""
    history = memory.load_conversation_history()
    if history:
        # Include only the last 2 messages for context
        recent_history = history[-min(2, len(history)):]
        history_context = "\n".join([
            f"{msg['role'].title()}: {msg['content']}" 
            for msg in recent_history
        ])
    
    # Generate LLM-based response when available
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            
            template = """
            You are a helpful customer service assistant at Staples. Generate a friendly, 
            conversational response about password reset based on this information:
            
            Email address: {email}
            """
            
            # Include conversation history context if available
            if history_context:
                template += f"""
                
                Recent conversation history:
                {history_context}
                """
            
            template += """
            
            Keep your response concise (50 words max) and conversational, as if you're speaking directly to the customer.
            Explain that you've sent instructions to reset their password to their email.
            If this is a follow-up to a previous conversation, maintain continuity.
            """
            
            prompt = ChatPromptTemplate.from_template(template)
            llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
            chain = prompt | llm
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            llm_response = loop.run_until_complete(chain.ainvoke({
                "email": email
            }))
            
            loop.close()
            response_text = llm_response.content
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}", exc_info=True)
            response_text = f"I've sent password reset instructions to your email address ({email}). Please check your inbox and follow the instructions to create a new password. The email should arrive within the next few minutes."
    else:
        response_text = f"I've sent password reset instructions to your email address ({email}). Please check your inbox and follow the instructions to create a new password. The email should arrive within the next few minutes."
    
    # Store conversation in database
    conversation = Conversation(
        session_id=session_id,
        user_input=query,
        brain_response=response_text,
        intent="password_reset",
        confidence=1.0,
        selected_agent="Reset Password Agent"
    )
    db.session.add(conversation)
    
    # Add messages
    user_message = Message(
        conversation=conversation,
        role="user",
        content=query
    )
    assistant_message = Message(
        conversation=conversation,
        role="assistant",
        content=response_text
    )
    db.session.add_all([user_message, assistant_message])
    
    # Add password reset info
    password_reset = PasswordReset(
        conversation=conversation,
        email=email,
        username=PASSWORD_RESET_SAMPLE["username"],
        account_type=PASSWORD_RESET_SAMPLE["account_type"],
        issue=PASSWORD_RESET_SAMPLE["issue"],
        reset_link_sent=False
    )
    db.session.add(password_reset)
    db.session.commit()
    
    # Update agent context with tracking info
    memory.update_context("Reset Password Agent", {
        "last_reset": {
            "email": email,
            "reset_link_sent": False,
            "conversation_id": conversation.id
        }
    })
    
    return jsonify({
        "agent": "Reset Password Agent",
        "response": response_text,
        "account_info": {
            "email": email,
            "username": None,
            "account_type": "Staples.com",
            "issue": "forgot password"
        },
        "reset_status": {
            "status": "instructions_provided",
            "message": f"Password reset instructions for your account with email: {email}",
            "instructions": PASSWORD_RESET_SAMPLE["instructions"],
            "reset_link_sent": False,
            "is_simulated": True
        },
        "success": True,
        "conversation_id": conversation.id
    })

@app.route('/api/find-store', methods=["POST"])
def find_store():
    """Find store locations directly."""
    data = request.json
    
    # Record agent selection metric
    record_agent_selection("Store Locator Agent")
    
    # Create or get session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session.get('session_id')
    
    # Extract location if provided
    query = data.get('query', '')
    location = data.get('location', '')
    radius = data.get('radius', 10)
    service = data.get('service', None)
    
    # Initialize conversation memory
    memory = ConversationMemory(session_id=session_id)
    
    # Create store info structure
    STORE_LOCATOR_SAMPLE = {
        "location": location or "sample location",
        "radius": radius,
        "service": service,
        "store_id": f"store-{random.randint(100, 999)}",
        "store_name": f"Staples #{random.randint(1000, 9999)}",
        "store_address": f"{random.randint(100, 999)} Main St, {location or 'Anytown'}, CA",
        "store_phone": f"({random.randint(100, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
        "is_simulated": True
    }
    
    try:
        # Generate LLM-based response if API key available
        if os.environ.get("OPENAI_API_KEY"):
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            
            template = """
            You are a helpful Staples customer service assistant. Generate a friendly response about 
            nearby Staples stores based on this information:
            
            User query: {query}
            Location: {location}
            Radius: {radius} miles
            
            Create a helpful response that provides store location information in a clear, conversational way.
            If specific services were requested, mention those services are available at the store.
            Include the store address, phone number, and brief store hours information.
            """
            
            prompt = ChatPromptTemplate.from_template(template)
            llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
            chain = prompt | llm
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            llm_response = loop.run_until_complete(chain.ainvoke({
                "query": query,
                "location": location or "the requested location",
                "radius": radius
            }))
            
            loop.close()
            response_text = llm_response.content
        else:
            response_text = f"I found a Staples store near {location or 'your location'} at {STORE_LOCATOR_SAMPLE['store_address']}. You can call them at {STORE_LOCATOR_SAMPLE['store_phone']}. They're open from 8:00 AM to 9:00 PM Monday to Friday, and 10:00 AM to 7:00 PM on weekends."
    except Exception as e:
        logger.error(f"Error generating LLM response: {str(e)}", exc_info=True)
        response_text = f"I found a Staples store near {location or 'your location'} at {STORE_LOCATOR_SAMPLE['store_address']}. You can call them at {STORE_LOCATOR_SAMPLE['store_phone']}. They're open from 8:00 AM to 9:00 PM Monday to Friday, and 10:00 AM to 7:00 PM on weekends."
    
    # Store conversation in database
    conversation = Conversation(
        session_id=session_id,
        user_input=query,
        brain_response=response_text,
        intent="store_locator",
        confidence=1.0,
        selected_agent="Store Locator Agent"
    )
    db.session.add(conversation)
    
    # Add messages
    user_message = Message(
        conversation=conversation,
        role="user",
        content=query
    )
    assistant_message = Message(
        conversation=conversation,
        role="assistant",
        content=response_text
    )
    db.session.add_all([user_message, assistant_message])
    
    # Add store locator info
    store_locator = StoreLocator(
        conversation=conversation,
        location=location,
        radius=radius,
        service=service,
        store_id=STORE_LOCATOR_SAMPLE["store_id"],
        store_name=STORE_LOCATOR_SAMPLE["store_name"],
        store_address=STORE_LOCATOR_SAMPLE["store_address"],
        store_phone=STORE_LOCATOR_SAMPLE["store_phone"]
    )
    db.session.add(store_locator)
    db.session.commit()
    
    # Update agent context with store info
    memory.update_context("Store Locator Agent", {
        "last_store_search": {
            "location": location,
            "radius": radius,
            "service": service,
            "conversation_id": conversation.id
        }
    })
    
    return jsonify({
        "agent": "Store Locator Agent",
        "response": response_text,
        "store_info": {
            "location": location,
            "radius": radius,
            "service": service
        },
        "store_details": STORE_LOCATOR_SAMPLE,
        "success": True,
        "conversation_id": conversation.id
    })

@app.route('/api/product-info', methods=["POST"])
def product_info():
    """Get product information directly."""
    data = request.json
    
    # Record agent selection metric
    record_agent_selection("Product Information Agent")
    
    # Create or get session ID
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session.get('session_id')
    
    # Extract product info if provided
    query = data.get('query', '')
    product_name = data.get('product_name', '')
    category = data.get('category', None)
    
    # Initialize conversation memory
    memory = ConversationMemory(session_id=session_id)
    
    # Create product info structure
    PRODUCT_INFO_SAMPLE = {
        "product_name": product_name or "sample product",
        "product_id": f"P{random.randint(100000, 999999)}",
        "category": category or "Office Supplies",
        "price": f"${random.randint(5, 100)}.99",
        "availability": "In Stock",
        "description": f"High-quality {product_name or 'product'} for home or office use.",
        "specifications": "Brand: Staples, Color: Black, Quantity: 1",
        "is_simulated": True
    }
    
    try:
        # Generate LLM-based response if API key available
        if os.environ.get("OPENAI_API_KEY"):
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            
            template = """
            You are a helpful Staples customer service assistant. Generate a friendly response about 
            a product based on this information:
            
            User query: {query}
            Product: {product_name}
            Category: {category}
            
            Create a helpful response that provides product information in a clear, conversational way.
            Include price, availability, and key specifications.
            """
            
            prompt = ChatPromptTemplate.from_template(template)
            llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
            chain = prompt | llm
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            llm_response = loop.run_until_complete(chain.ainvoke({
                "query": query,
                "product_name": product_name or "the requested product",
                "category": category or "Office Supplies"
            }))
            
            loop.close()
            response_text = llm_response.content
        else:
            response_text = f"The {product_name or 'requested product'} is available for {PRODUCT_INFO_SAMPLE['price']} and is currently {PRODUCT_INFO_SAMPLE['availability']}. It's a high-quality item that's perfect for both home and office use. Would you like more information about this product?"
    except Exception as e:
        logger.error(f"Error generating LLM response: {str(e)}", exc_info=True)
        response_text = f"The {product_name or 'requested product'} is available for {PRODUCT_INFO_SAMPLE['price']} and is currently {PRODUCT_INFO_SAMPLE['availability']}. It's a high-quality item that's perfect for both home and office use. Would you like more information about this product?"
    
    # Store conversation in database
    conversation = Conversation(
        session_id=session_id,
        user_input=query,
        brain_response=response_text,
        intent="product_info",
        confidence=1.0,
        selected_agent="Product Information Agent"
    )
    db.session.add(conversation)
    
    # Add messages
    user_message = Message(
        conversation=conversation,
        role="user",
        content=query
    )
    assistant_message = Message(
        conversation=conversation,
        role="assistant",
        content=response_text
    )
    db.session.add_all([user_message, assistant_message])
    
    # Add product info
    product_info_data = ProductInfo(
        conversation=conversation,
        product_name=product_name,
        product_id=PRODUCT_INFO_SAMPLE["product_id"],
        category=category or PRODUCT_INFO_SAMPLE["category"],
        price=PRODUCT_INFO_SAMPLE["price"],
        availability=PRODUCT_INFO_SAMPLE["availability"],
        description=PRODUCT_INFO_SAMPLE["description"],
        specifications=PRODUCT_INFO_SAMPLE["specifications"],
        search_query=query
    )
    db.session.add(product_info_data)
    db.session.commit()
    
    # Update agent context with product info
    memory.update_context("Product Information Agent", {
        "last_product_search": {
            "product_name": product_name,
            "category": category,
            "conversation_id": conversation.id
        }
    })
    
    return jsonify({
        "agent": "Product Information Agent",
        "response": response_text,
        "product_info": {
            "product_name": product_name,
            "category": category
        },
        "product_details": PRODUCT_INFO_SAMPLE,
        "success": True,
        "conversation_id": conversation.id
    })

# Dashboard route
@app.route('/agent-builder', methods=["GET"])
def agent_builder():
    """Render the agent builder interface."""
    agent_id = request.args.get('id')
    return render_template('agent_builder.html', agent_id=agent_id)

@app.route('/agent-management-docs', methods=["GET"])
def agent_management_docs():
    """Render the agent management documentation."""
    return render_template('agent_management_doc.html')

@app.route('/agent-wizard', methods=["GET"])
@app.route('/agent-wizard/<int:agent_id>', methods=["GET"])
@app.route('/agent-wizard/<int:agent_id>/step/<int:step>', methods=["GET"])
def agent_wizard(agent_id=None, step=1):
    """Render the agent configuration wizard interface."""
    if step < 1 or step > 5:
        step = 1
    
    # Check if we're starting from a template
    template_id = request.args.get('template_id')
    template = None
    if template_id:
        template = AgentTemplate.query.get(template_id)
        # Increment the download count
        if template:
            template.downloads += 1
            db.session.commit()
    
    # If no agent_id, we're creating a new agent
    if agent_id is None:
        # Set up default values
        name = "New Agent"
        description = ""
        configuration = json.dumps({"agent_type": "custom"})
        entity_definitions = json.dumps([])
        prompt_templates = json.dumps({})
        response_formats = json.dumps({})
        business_rules = json.dumps([])
        
        # If we're using a template, copy its values
        if template:
            name = f"Copy of {template.name}"
            description = template.description
            configuration = template.configuration or configuration
            entity_definitions = template.entity_definitions or entity_definitions
            prompt_templates = template.prompt_templates or prompt_templates
            response_formats = template.response_formats or response_formats
            business_rules = template.business_rules or business_rules
        
        # Create a new agent with the values
        new_agent = CustomAgent(
            name=name,
            description=description,
            is_active=True,
            configuration=configuration,
            entity_definitions=entity_definitions,
            prompt_templates=prompt_templates,
            response_formats=response_formats,
            business_rules=business_rules
        )
        
        # Save to get an ID
        db.session.add(new_agent)
        db.session.commit()
        
        # Redirect to the wizard with the new agent ID
        return redirect(url_for('agent_wizard', agent_id=new_agent.id, step=1))
    
    # Fetch existing agent
    agent = CustomAgent.query.get_or_404(agent_id)
    
    # Prepare template variables based on the current step
    entities = []
    prompts = {}
    response_format = {}
    
    if step == 2:
        # Entity Definitions
        entities = agent.get_entity_definitions()
        # Add a default entity if none exist
        if not entities:
            entities = [{
                "name": "entity1",
                "description": "First required entity",
                "validation_pattern": ".*",
                "error_message": "Please provide a valid value",
                "examples": ["example1", "example2"],
                "required": True
            }]
    
    elif step == 3:
        # Prompt Templates
        prompts = agent.get_prompt_templates()
        if not prompts or not prompts.get("system"):
            prompts = {
                "system": "You are a helpful assistant.",
                "entity_extraction": "Extract the following entities from the user query:",
                "response_generation": "Generate a helpful response based on the extracted entities."
            }
    
    elif step == 4:
        # Response Format
        response_format = agent.get_response_formats()
        if not response_format or not response_format.get("schema"):
            response_format = {
                "schema": '{\n  "response": "string",\n  "confidence": "number"\n}',
                "enforce_schema": True,
                "template": "{{ response }}"
            }
    
    # Parse configuration
    try:
        agent_config = json.loads(agent.configuration) if agent.configuration else {}
    except:
        agent_config = {}
    
    # Set agent.configuration for accessing in the template
    agent.configuration = agent_config
    
    return render_template(
        'agent_wizard.html', 
        agent=agent,
        current_step=step,
        agent_id=agent_id,
        entities=entities,
        prompts=prompts,
        response_format=response_format
    )

@app.route('/agent-wizard/<int:agent_id>/step/<int:step>', methods=['POST'])
def agent_wizard_save(agent_id, step):
    """Save the current step of the agent wizard and move to the next."""
    agent = CustomAgent.query.get_or_404(agent_id)
    
    if step == 1:
        # Save Basic Info
        agent.name = request.form.get('name', 'New Agent')
        agent.description = request.form.get('description', '')
        agent.is_active = 'is_active' in request.form
        
        # Update configuration with agent type
        config = json.loads(agent.configuration) if agent.configuration else {}
        config['agent_type'] = request.form.get('agent_type', 'custom')
        agent.configuration = json.dumps(config)
        
    elif step == 2:
        # Save Entity Definitions
        entities_data = []
        entity_count = 0
        
        # Count how many entities are in the form
        for key in request.form:
            if key.startswith('entities[') and key.endswith('][name]'):
                entity_count = max(entity_count, int(key.split('[')[1].split(']')[0]) + 1)
        
        # Process each entity
        for i in range(entity_count):
            name_key = f'entities[{i}][name]'
            if name_key in request.form and request.form[name_key].strip():
                # Get entity fields from form
                entity = {
                    'name': request.form.get(f'entities[{i}][name]', '').strip(),
                    'description': request.form.get(f'entities[{i}][description]', '').strip(),
                    'validation_pattern': request.form.get(f'entities[{i}][validation_pattern]', '.*').strip(),
                    'error_message': request.form.get(f'entities[{i}][error_message]', '').strip(),
                    'required': f'entities[{i}][required]' in request.form,
                    'examples': [ex.strip() for ex in request.form.get(f'entities[{i}][examples]', '').split(',') if ex.strip()]
                }
                entities_data.append(entity)
        
        # Save to the database
        agent.entity_definitions = json.dumps(entities_data)
        
    elif step == 3:
        # Save Prompt Templates
        prompts = {
            'system': request.form.get('prompts[system]', '').strip(),
            'entity_extraction': request.form.get('prompts[entity_extraction]', '').strip(),
            'response_generation': request.form.get('prompts[response_generation]', '').strip()
        }
        agent.prompt_templates = json.dumps(prompts)
        
    elif step == 4:
        # Save Response Format
        response_format = {
            'schema': request.form.get('response_format[schema]', '').strip(),
            'enforce_schema': 'response_format[enforce_schema]' in request.form,
            'template': request.form.get('response_format[template]', '').strip()
        }
        agent.response_formats = json.dumps(response_format)
        
    elif step == 5:
        # Complete the wizard
        agent.wizard_completed = True
        # Redirect to the agent builder interface
        db.session.commit()
        return redirect(url_for('agent_builder', id=agent_id))
    
    # Update wizard progress
    agent.current_wizard_step = step + 1
    db.session.commit()
    
    # Redirect to the next step
    return redirect(url_for('agent_wizard', agent_id=agent_id, step=step+1))

@app.route('/template-gallery', methods=["GET"])
def template_gallery():
    """Render the agent template gallery."""
    # Get featured templates
    featured_templates = AgentTemplate.query.filter_by(is_featured=True).all()
    
    # Get all templates
    templates = AgentTemplate.query.filter_by(is_featured=False).all()
    
    return render_template('template_gallery.html', 
                          featured_templates=featured_templates,
                          templates=templates)

@app.route('/api/templates', methods=["GET"])
def list_templates():
    """List all agent templates."""
    try:
        # Get filter parameters
        category = request.args.get('category')
        tags = request.args.get('tags')
        sort_by = request.args.get('sort_by', 'featured')
        
        # Start with basic query
        query = AgentTemplate.query
        
        # Apply filters
        if category:
            query = query.filter_by(category=category)
            
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            for tag in tag_list:
                query = query.filter(AgentTemplate.tags.like(f'%{tag}%'))
                
        # Apply sorting
        if sort_by == 'featured':
            query = query.order_by(AgentTemplate.is_featured.desc(), AgentTemplate.name)
        elif sort_by == 'downloads':
            query = query.order_by(AgentTemplate.downloads.desc())
        elif sort_by == 'rating':
            query = query.order_by(AgentTemplate.rating.desc())
        elif sort_by == 'newest':
            query = query.order_by(AgentTemplate.created_at.desc())
        else:
            query = query.order_by(AgentTemplate.name)
            
        # Get templates
        templates = query.all()
        
        # Format the results
        result = []
        for template in templates:
            result.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "icon": template.icon,
                "screenshot": template.screenshot,
                "is_featured": template.is_featured,
                "tags": template.tags,
                "downloads": template.downloads,
                "rating": template.rating,
                "rating_count": template.rating_count,
                "author": template.author,
                "created_at": template.created_at.isoformat()
            })
            
        return jsonify({
            "success": True,
            "templates": result,
            "count": len(result)
        })
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/templates/<int:template_id>', methods=["GET"])
def get_template(template_id):
    """Get a specific agent template with all its configuration data."""
    try:
        # Get the template
        template = AgentTemplate.query.get(template_id)
        
        if not template:
            return jsonify({
                "success": False,
                "error": f"Template with ID {template_id} not found"
            }), 404
            
        # Format template data
        result = {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "icon": template.icon,
            "screenshot": template.screenshot,
            "is_featured": template.is_featured,
            "tags": template.tags,
            "downloads": template.downloads,
            "rating": template.rating,
            "rating_count": template.rating_count,
            "author": template.author,
            "created_at": template.created_at.isoformat(),
            "entity_definitions": template.entity_definitions,
            "prompt_templates": template.prompt_templates,
            "response_formats": template.response_formats,
            "business_rules": template.business_rules
        }
        
        # Increment download count when explicitly requested
        if request.args.get('track_view') == 'true':
            template.downloads += 1
            db.session.commit()
            
        return jsonify({
            "success": True,
            "template": result
        })
    except Exception as e:
        logger.error(f"Error getting template: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
        
@app.route('/api/save-as-template', methods=["POST"])
def save_as_template():
    """Save a custom agent as a reusable template."""
    try:
        data = request.json
        
        if not data or "agent_id" not in data:
            return jsonify({
                "success": False,
                "error": "Missing required field: agent_id"
            }), 400
            
        agent_id = data.get("agent_id")
        agent = CustomAgent.query.get(agent_id)
        
        if not agent:
            return jsonify({
                "success": False,
                "error": f"Agent with ID {agent_id} not found"
            }), 404
            
        # Create a new template from the agent
        template = AgentTemplate(
            name=data.get("name") or f"Template: {agent.name}",
            description=data.get("description") or agent.description,
            category=data.get("category", "custom"),
            icon=data.get("icon", "fas fa-robot"),
            tags=data.get("tags", "custom"),
            is_featured=False,
            is_system=False,
            configuration=agent.configuration,
            entity_definitions=agent.entity_definitions,
            prompt_templates=agent.prompt_templates,
            response_formats=agent.response_formats,
            business_rules=agent.business_rules,
            author=data.get("author", "User"),
            downloads=0,
            rating=0,
            rating_count=0
        )
        
        db.session.add(template)
        db.session.commit()
        
        # Return the new template ID
        return jsonify({
            "success": True,
            "template_id": template.id,
            "message": f"Successfully saved agent '{agent.name}' as template '{template.name}'"
        })
    except Exception as e:
        logger.error(f"Error saving template: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/documentation', methods=["GET"])
def documentation():
    """Render the comprehensive user documentation."""
    return render_template('documentation.html')

@app.route('/setup-guide', methods=["GET"])
def setup_guide():
    """Render the local setup guide."""
    return render_template('setup_guide.html')

@app.route('/dashboard', methods=["GET"])
def dashboard():
    """Render the observability dashboard."""
    return render_template('dashboard.html')

# Prometheus metrics endpoint
@app.route('/metrics', methods=["GET"])
def metrics():
    """Provide Prometheus metrics endpoint."""
    return Response(get_prometheus_metrics()[0], mimetype=CONTENT_TYPE_LATEST)

# Dashboard metrics API endpoint
@app.route('/api/metrics/dashboard', methods=["GET"])
def dashboard_metrics():
    """Provide metrics for the dashboard."""
    try:
        metrics_data = get_metrics_summary()
        
        # Add LLM integration status
        metrics_data['llm_integration'] = os.environ.get("OPENAI_API_KEY") is not None
        
        # Add Databricks integration status
        metrics_data['databricks_integration'] = (
            os.environ.get("DATABRICKS_HOST") is not None 
            and os.environ.get("DATABRICKS_TOKEN") is not None
        )
        
        # Add LangSmith integration status
        metrics_data['langsmith_integration'] = os.environ.get("LANGSMITH_API_KEY") is not None
        
        # Add current active conversations (simulate for now)
        active_count = Conversation.query.filter(Conversation.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)).count()
        update_active_conversations(active_count)
        
        return jsonify({
            "success": True,
            "metrics": metrics_data
        })
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# File download endpoint for setup guide
@app.route('/api/download/requirements-local.txt', methods=["GET"])
def download_requirements():
    """Provide the requirements file for download."""
    try:
        return Response(
            open('requirements-local.txt', 'r').read(),
            mimetype='text/plain',
            headers={"Content-Disposition": "attachment;filename=requirements-local.txt"}
        )
    except Exception as e:
        logger.error(f"Error downloading requirements file: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
