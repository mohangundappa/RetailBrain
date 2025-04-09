import os
import logging
import asyncio
import uuid
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, Response, g
from flask_cors import CORS
from prometheus_client import CONTENT_TYPE_LATEST
from brain.intent_handler import IntentHandler
from brain.planner import ExecutionPlanner
from models import db, Conversation, Message, PackageTracking, PasswordReset, AgentConfig, AnalyticsData
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
        "available_agents": ["Package Tracking Agent", "Reset Password Agent"],
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
        "agents": ["Package Tracking Agent", "Reset Password Agent"],
        "llm_integration": "available" if has_llm else "unavailable"
    })

@app.route('/api/agents', methods=["GET"])
def list_agents():
    """List all available agents."""
    return jsonify({
        "success": True,
        "agents": ["Package Tracking Agent", "Reset Password Agent"]
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
            "password_reset_data": password_reset_data
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
            response_text = "I'm sorry, I don't have the capability to help with that request at the moment. I can assist with package tracking and password reset inquiries."
            
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

# Dashboard route
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
