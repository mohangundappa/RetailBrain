"""
Reset Password Agent Workflow Definition.

This module defines the LangGraph-based workflow for the Reset Password Agent,
implementing a conversational flow for password reset requests.
"""
import logging
import time
import json
from enum import Enum
from typing import Dict, List, Optional, Any, TypedDict, Literal, cast, Annotated

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from backend.memory.mem0 import Mem0, MemoryEntry, MemoryType, MemoryScope
from backend.memory.factory import get_mem0

logger = logging.getLogger(__name__)


class ResetPasswordIntent(str, Enum):
    """Possible intents in the password reset flow."""
    INFO_REQUEST = "info_request"  # User is asking about password policies or reset process
    RESET_REQUEST = "reset_request"  # User wants to actually reset their password
    ACCOUNT_ISSUE = "account_issue"  # User is having account problems beyond just password reset
    UNKNOWN = "unknown"  # Can't determine user intent


class ResetPasswordState(TypedDict):
    """State object for the password reset workflow."""
    conversation_id: str
    session_id: str
    user_input: str
    user_email: Optional[str]
    reset_intent: Optional[ResetPasswordIntent]
    reset_status: Optional[str]
    current_step: str
    response: Optional[str]
    messages: List[Dict[str, Any]]
    context: Dict[str, Any]


class IntentClassifierOutput(BaseModel):
    """Output schema for the intent classifier node."""
    intent: ResetPasswordIntent = Field(
        ..., 
        description="The classified intent of the user's message"
    )
    reasoning: str = Field(
        ...,
        description="Reasoning for the intent classification"
    )


class EmailExtractionOutput(BaseModel):
    """Output schema for the email extraction node."""
    email: Optional[str] = Field(
        None,
        description="The email address extracted from the user's message, if any"
    )
    email_provided: bool = Field(
        ...,
        description="Whether an email address was provided in the message"
    )


def create_reset_password_workflow(model_name: str = "gpt-4o", temperature: float = 0.2) -> StateGraph:
    """
    Create a workflow graph for password reset conversations.
    
    Args:
        model_name: LLM model name
        temperature: Model temperature parameter
        
    Returns:
        Compiled StateGraph for the workflow
    """
    # Initialize the LLM
    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature
    )
    
    # Define workflow nodes
    
    async def classify_intent(state: ResetPasswordState) -> Dict[str, Any]:
        """
        Zero-shot intent classification using pattern matching.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with intent classification
        """
        # Get the user input with more robust handling
        direct_message = state.get("messages", [{}])[0].get("content", "") if state.get("messages") else ""
        if direct_message:
            state["user_input"] = direct_message  # Force set the user_input in state
            
        user_input = state.get("user_input", "")
        
        # If no direct user input, try to get from messages
        if not user_input:
            messages = state.get("messages", [])
            if messages:
                for msg in reversed(messages):
                    if msg.get("role") == "user" and msg.get("content"):
                        user_input = msg.get("content")
                        break
        
        # Last resort fallback
        if not user_input:
            logger.warning("No user input found in state or messages, using default")
            user_input = "Need help with password"
            
        # Log the user input with better formatting
        truncated = user_input[:75] + ('...' if len(user_input) > 75 else '')
        logger.info(f"Zero-shot intent classification for message: '{truncated}'")
        
        # Zero-shot intent classification with pattern matching
        message_lower = user_input.lower()
        intent = "unknown"
        
        # Define pattern sets for each intent type
        reset_patterns = [
            "reset password", "forgot password", "change password", 
            "can't login", "login problem", "password not working",
            "locked out", "reset my password", "new password", 
            "change my password", "lost password", "recover password"
        ]
        
        info_patterns = [
            "password requirements", "password policy", "how to reset", 
            "password rules", "secure password", "password instructions",
            "how do i", "what are the steps", "explain how",
            "password criteria", "password strength"
        ]
        
        account_patterns = [
            "account locked", "account stolen", "hacked account",
            "suspicious activity", "security breach", "account compromise",
            "account access", "someone else", "account help", 
            "verify identity", "account issues", "can't access"
        ]
        
        # Check patterns in order of priority
        for pattern in reset_patterns:
            if pattern in message_lower:
                intent = "reset_request"
                logger.info(f"Pattern match: Found '{pattern}' in message, classified as {intent}")
                break
                
        # If no reset patterns matched, check info patterns
        if intent == "unknown":
            for pattern in info_patterns:
                if pattern in message_lower:
                    intent = "info_request"
                    logger.info(f"Pattern match: Found '{pattern}' in message, classified as {intent}")
                    break
        
        # If still no match, check account issue patterns
        if intent == "unknown":
            for pattern in account_patterns:
                if pattern in message_lower:
                    intent = "account_issue"
                    logger.info(f"Pattern match: Found '{pattern}' in message, classified as {intent}")
                    break
        
        # If password is mentioned but no specific pattern matched, default to reset_request
        if intent == "unknown" and "password" in message_lower:
            intent = "reset_request"
            logger.info("Default password mention match: User mentioned 'password', defaulting to reset_request")
        
        # Map to enum value
        try:
            intent_enum = ResetPasswordIntent(intent.strip())
            logger.info(f"Final intent classification: {intent_enum.value}")
        except ValueError:
            # Default to unknown if invalid intent
            logger.warning(f"Invalid intent value '{intent}', defaulting to UNKNOWN")
            intent_enum = ResetPasswordIntent.UNKNOWN
        
        # Update state with intent
        return {
            **state,
            "reset_intent": intent_enum,
            "current_step": "intent_classified"
        }
    
    async def extract_email(state: ResetPasswordState) -> Dict[str, Any]:
        """
        Extract email address from user input using regex pattern matching.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with extracted email or response asking for it
        """
        import re
        
        # Get the user input with more robust handling
        user_input = state.get("user_input", "")
        if not user_input:
            messages = state.get("messages", [])
            if messages:
                for msg in reversed(messages):
                    if msg.get("role") == "user" and msg.get("content"):
                        user_input = msg.get("content")
                        break
            
        if not user_input:
            logger.warning("No user input found for email extraction")
            return {
                **state,
                "current_step": "need_email"
            }
            
        logger.info(f"Extracting email from: '{user_input[:50]}...'")
        
        # Use regex to find email pattern
        # This pattern matches most standard email formats
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        
        try:
            # Search for email in the text
            matches = re.findall(email_pattern, user_input)
            
            if matches:
                email = matches[0]  # Take the first email found
                logger.info(f"Extracted email: {email}")
                
                # Store the extracted email
                return {
                    **state,
                    "user_email": email,
                    "current_step": "email_provided"
                }
            else:
                logger.info("No email found in user input")
                # No email found, need to ask
                return {
                    **state,
                    "current_step": "need_email"
                }
        except Exception as e:
            logger.error(f"Error extracting email: {str(e)}", exc_info=True)
            # Error case, need to ask for email
            return {
                **state,
                "current_step": "need_email"
            }
    
    async def request_email(state: ResetPasswordState) -> Dict[str, Any]:
        """
        Generate a response asking for the user's email address.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with response asking for email
        """
        # Prepare a message asking for email
        response = (
            "To reset your password, I'll need your email address associated with your Staples account. "
            "Please provide your email address so I can help you with the password reset process."
        )
        
        # For now, we'll skip memory fact storage since it's not implemented
        # Just log that we asked for email
        logger.info(f"Asked for email address for conversation {state['conversation_id']}")
        
        # Return updated state
        return {
            **state,
            "response": response,
            "current_step": "awaiting_email"
        }
    
    async def process_password_reset(state: ResetPasswordState) -> Dict[str, Any]:
        """
        Process the password reset request with the provided email.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with reset instructions
        """
        email = state.get("user_email")
        if not email:
            # Fallback if no email provided somehow
            email = "your email address"
        
        # In a real implementation, this would trigger an actual password reset flow
        # For now, we're simulating the process
        
        # Prepare a response with reset instructions
        response = (
            f"I've sent a password reset link to {email}. Please check your email and follow "
            "the instructions in the reset link. The link will expire in 24 hours.\n\n"
            "If you don't see the email, please check your spam folder. "
            "If you still don't receive it, please let me know and I'll try sending it again."
        )
        
        # For now, we'll skip memory fact storage since it's not implemented
        # Just log that we sent a reset link
        logger.info(f"Sent password reset link to {email} for conversation {state['conversation_id']}")
        
        # Return updated state
        return {
            **state,
            "response": response,
            "reset_status": "link_sent",
            "current_step": "completed"
        }
    
    async def provide_reset_info(state: ResetPasswordState) -> Dict[str, Any]:
        """
        Provide information about the password reset process.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with informational response
        """
        # Prepare an informational response about password reset
        response = (
            "Here's how the password reset process works:\n\n"
            "1. Go to Staples.com and click 'Sign In'\n"
            "2. Select 'Forgot Password'\n"
            "3. Enter your email address\n"
            "4. Check your email for a reset link\n"
            "5. Click the link and follow the instructions to create a new password\n\n"
            "Would you like me to help you reset your password now?"
        )
        
        # Return updated state
        return {
            **state,
            "response": response,
            "current_step": "info_provided"
        }
    
    async def handle_account_issue(state: ResetPasswordState) -> Dict[str, Any]:
        """
        Handle other account-related issues.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with response for account issues
        """
        # Prepare a response for account issues
        response = (
            "I understand you're having account issues beyond just password reset. "
            "For account-related problems, you have a few options:\n\n"
            "1. Call customer service at 1-800-STAPLES\n"
            "2. Visit your local Staples store for in-person assistance\n"
            "3. Use the 'Contact Us' form on Staples.com\n\n"
            "Would you like me to help with a specific aspect of your account issue?"
        )
        
        # Return updated state
        return {
            **state,
            "response": response,
            "current_step": "account_issue_handled"
        }
    
    # Create the state graph with type annotation
    workflow = StateGraph(ResetPasswordState)
    
    # Add nodes to the graph
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("extract_email", extract_email)
    workflow.add_node("request_email", request_email)
    workflow.add_node("process_password_reset", process_password_reset)
    workflow.add_node("provide_reset_info", provide_reset_info)
    workflow.add_node("handle_account_issue", handle_account_issue)
    
    # Define the edges (transitions)
    
    # From entry, first classify the intent
    workflow.set_entry_point("classify_intent")
    
    # After intent classification, route based on intent type
    workflow.add_conditional_edges(
        "classify_intent",
        lambda state: state["reset_intent"].value if state.get("reset_intent") else "unknown",
        {
            ResetPasswordIntent.INFO_REQUEST.value: "provide_reset_info",
            ResetPasswordIntent.RESET_REQUEST.value: "extract_email",
            ResetPasswordIntent.ACCOUNT_ISSUE.value: "handle_account_issue",
            # Default to info request if unknown
            ResetPasswordIntent.UNKNOWN.value: "provide_reset_info"
        }
    )
    
    # After email extraction, either process reset or ask for email
    workflow.add_conditional_edges(
        "extract_email",
        lambda state: "email_provided" if state.get("user_email") else "need_email",
        {
            "email_provided": "process_password_reset",
            "need_email": "request_email"
        }
    )
    
    # Final steps lead to end
    workflow.add_edge("provide_reset_info", END)
    workflow.add_edge("process_password_reset", END)
    workflow.add_edge("handle_account_issue", END)
    workflow.add_edge("request_email", END)  # End after asking for email, next user message starts new workflow run
    
    # Compile the graph
    return workflow.compile()


async def execute_reset_password_workflow(
    workflow: StateGraph,
    message: str,
    conversation_id: str,
    session_id: str,
    context: Optional[Dict[str, Any]] = None,
    email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute the password reset workflow with a user message.
    
    Args:
        workflow: Compiled workflow graph
        message: User message
        conversation_id: Conversation ID
        session_id: Session ID
        context: Optional context
        email: Optional pre-known email
        
    Returns:
        Execution result
    """
    # Ensure message is not None or empty
    if not message:
        message = "I need help with my password"
        logger.warning(f"Empty message received, using default: {message}")
    
    # Log the message being processed
    logger.info(f"Initializing workflow for conversation {conversation_id} and session {session_id}")
    logger.info(f"Processing message: '{message[:100]}...'")
    
    # Initialize with the current message
    messages = [
        {"role": "user", "content": message}
    ]
    
    # Prepare the initial state
    initial_state: ResetPasswordState = {
        "conversation_id": conversation_id,
        "session_id": session_id,
        "user_input": message,  # Explicitly set the user_input
        "user_email": email,
        "reset_intent": None,
        "reset_status": None,
        "current_step": "start",
        "response": None,
        "messages": messages,
        "context": context or {}
    }
    
    try:
        # Add the current user message to memory
        try:
            mem0 = await get_mem0()
            if mem0:
                await mem0.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=message,
                    session_id=session_id
                )
        except Exception as e:
            logger.error(f"Error saving message to memory: {str(e)}")
        
        # Execute the workflow
        logger.info(f"Invoking workflow with state: {initial_state}")
        result = await workflow.ainvoke(initial_state)
        logger.info(f"Workflow result: {result}")
        
        # Store the agent response in memory if available
        if result.get("response"):
            try:
                mem0 = await get_mem0()
                if mem0:
                    await mem0.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=result["response"],
                        session_id=session_id
                    )
            except Exception as e:
                logger.error(f"Error saving response to memory: {str(e)}")
        
        return result
    except Exception as e:
        logger.error(f"Error executing password reset workflow: {str(e)}", exc_info=True)
        return {
            "conversation_id": conversation_id,
            "session_id": session_id,
            "response": "I'm having trouble processing your request. Please try again later.",
            "error": str(e)
        }