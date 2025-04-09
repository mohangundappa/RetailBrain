import os
import logging
import asyncio
from flask import Flask, render_template, jsonify, request
from brain.intent_handler import IntentHandler
from brain.planner import ExecutionPlanner

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "staples-brain-secret-key")

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
    return render_template('index.html')

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

@app.route('/api/process', methods=["POST"])
def process_request():
    """Process a user request with LLM-based intent identification."""
    data = request.json
    
    if not data or "input" not in data:
        return jsonify({
            "success": False,
            "error": "Missing required field: input"
        }), 400
    
    user_input = data["input"]
    context = data.get("context", {})
    
    # Run the async planning process in a new event loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create a plan using the intent handler and planner
        plan_result = loop.run_until_complete(planner.create_plan(user_input))
        loop.close()
        
        intent = plan_result.get("intent", "unknown")
        confidence = plan_result.get("confidence", 0.0)
        
        logger.info(f"Identified intent: {intent} with confidence {confidence}")
        
        # If no suitable intent was found or confidence is too low
        if intent == "unknown" or confidence < 0.3:
            return jsonify({
                "success": False,
                "error": "No suitable agent found",
                "response": "I'm sorry, I don't have the capability to help with that request at the moment. I can assist with package tracking and password reset inquiries.",
                "confidence": confidence
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
                
                llm_response = loop.run_until_complete(chain.ainvoke({
                    "query": user_input,
                    "tracking_info": str(tracking_info)
                }))
                
                response_text = llm_response.content
            else:
                response_text = f"Your package with tracking number {tracking_info['tracking_number']} is currently {tracking_info['status'].replace('_', ' ')} and expected to be delivered on {tracking_info['estimated_delivery']}. It's currently in {tracking_info['current_location']} and should arrive at your location soon."
            
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
                "entities": entities
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
                "entities": entities
            })
        
        else:
            # Should not reach here based on earlier check, but just in case
            return jsonify({
                "success": False,
                "error": "Unsupported intent",
                "response": "I'm sorry, I don't have the capability to help with that request at the moment.",
                "confidence": confidence,
                "intent": intent
            })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "response": "I'm sorry, I encountered an error while processing your request. Please try again or rephrase your question."
        }), 500

@app.route('/api/track-package', methods=["POST"])
def track_package():
    """Track a package directly."""
    data = request.json
    
    # Extract tracking number if provided
    tracking_number = data.get("tracking_number", "TRACK123456") if data else "TRACK123456"
    query = data.get("query", f"Track my package {tracking_number}") if data else f"Track my package {tracking_number}"
    
    # Create a modified copy with the provided tracking number
    tracking_info = PACKAGE_TRACKING_SAMPLE.copy()
    tracking_info["tracking_number"] = tracking_number
    
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
            
            Keep your response concise (50 words max) and conversational, as if you're speaking directly to the customer.
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
        "success": True
    })

@app.route('/api/reset-password', methods=["POST"])
def reset_password():
    """Reset password directly."""
    data = request.json
    
    # Extract email if provided
    email = data.get("email", "user@example.com") if data else "user@example.com"
    query = data.get("query", f"Reset password for {email}") if data else f"Reset password for {email}"
    
    # Generate LLM-based response when available
    if os.environ.get("OPENAI_API_KEY"):
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate
            
            template = """
            You are a helpful customer service assistant at Staples. Generate a friendly, 
            conversational response about password reset based on this information:
            
            Email address: {email}
            
            Keep your response concise (50 words max) and conversational, as if you're speaking directly to the customer.
            Explain that you've sent instructions to reset their password to their email.
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
        "success": True
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
