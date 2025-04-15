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


async def extract_email_with_llm(text: str) -> Optional[str]:
    """
    Extract an email address from text using LLM.
    
    Args:
        text: The text to extract the email from
        
    Returns:
        Extracted email or None
    """
    # Skip if no @ symbol to avoid unnecessary LLM call
    if '@' not in text:
        return None
        
    try:
        # Initialize LLM with restrictive temperature
        llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        
        # Create the prompt instructing the LLM to extract email
        system_content = """
        Extract any email address from the text. Follow these rules strictly:
        1. If you find an email address, respond with ONLY the email address, nothing else
        2. If you find multiple email addresses, return only the most likely one based on context
        3. If no email address is found, respond with just "NONE"
        4. Do not make up or hallucinate an email address, only extract what's explicitly present
        5. Ensure the email address is valid (contains @ and domain)
        
        Return the email exactly as written, don't add comments, explanations, or any other text.
        """
        
        # Create the prompt messages
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_content),
            HumanMessage(content=f"Text: {text}\n\nExtract email address:")
        ])
        
        # Execute the LLM call
        start_time = time.time()
        response = await llm.ainvoke(prompt.format_messages())
        extraction_time = time.time() - start_time
        
        # Process the response
        email = response.content.strip()
        logger.info(f"Email extraction with LLM completed in {extraction_time:.2f}s")
        
        # Validate the result
        if email == "NONE" or not '@' in email:
            logger.info("No email found by LLM")
            return None
            
        # Basic validation that this looks like an email
        if '@' in email and '.' in email.split('@')[1]:
            logger.info(f"Valid email extracted: {email}")
            return email
        else:
            logger.warning(f"Invalid email format returned by LLM: {email}")
            return None
            
    except Exception as e:
        logger.error(f"Error in LLM email extraction: {str(e)}", exc_info=True)
        return None


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
        
        # Check if intent is passed in context
        context = state.get("context", {})
        if context.get("intent") == "reset_request":
            logger.info("Using reset_request intent from context")
            intent = "reset_request"
            # Map to enum value and return early
            try:
                intent_enum = ResetPasswordIntent(intent.strip())
                logger.info(f"Using intent from context: {intent_enum.value}")
                return {
                    **state,
                    "reset_intent": intent_enum,
                    "current_step": "intent_classified"
                }
            except ValueError:
                logger.warning(f"Invalid intent value from context '{intent}', will use normal classification")
                # Continue with normal classification below
        
        # Zero-shot intent classification with LLM
        intent = "unknown"
        session_id = state.get("session_id")
        conversation_history = []
        
        # Attempt to retrieve conversation history for context-aware classification
        try:
            if session_id:
                mem0 = await get_mem0()
                if mem0:
                    history = await mem0.get_conversation_history(session_id)
                    if history:
                        conversation_history = history
        except Exception as e:
            logger.error(f"Error retrieving conversation history for intent classification: {str(e)}")
            # Continue even if we can't get history
        
        # Create a context-aware prompt with conversation history if available
        system_content = """
        You are an intent classifier for a password reset workflow. You need to determine the user's intent based on their message and conversation context.
        
        Classify the user's message into one of these intents:
        1. reset_request: User wants to reset their password, is having login issues, or is responding affirmatively to an offer to help with password reset
        2. info_request: User is asking about password policies, requirements, or how to reset their password
        3. account_issue: User is having account-related problems beyond just password reset (security concerns, account access issues, etc.)
        4. unknown: The message doesn't clearly fit any of the above intents
        
        Pay special attention to conversation context. If the assistant previously asked if the user wants to reset their password and the user responds with "yes", "please", etc., classify as reset_request.
        
        Respond with ONLY the intent category (reset_request, info_request, account_issue, or unknown). No explanation or other text.
        """
        
        # Format history if we have it
        conversation_context = ""
        if conversation_history:
            # Format the last few messages for context (up to 3 turns)
            history_snippet = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
            
            for msg in history_snippet:
                role = msg.get("role", "").capitalize()
                content = msg.get("content", "")
                if role and content:
                    conversation_context += f"{role}: {content}\n"
        
        human_content = f"Conversation Context:\n{conversation_context}\n\nCurrent Message: {user_input}\n\nWhat is the user's intent?"
        
        try:
            # Create LLM
            llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
            
            # Create the prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=system_content),
                HumanMessage(content=human_content)
            ])
            
            # Execute the LLM call
            start_time = time.time()
            response = await llm.ainvoke(prompt.format_messages())
            classification_time = time.time() - start_time
            
            # Extract the response content
            intent = response.content.strip().lower()
            
            # Normalize the intent
            if "reset_request" in intent:
                intent = "reset_request"
            elif "info_request" in intent:
                intent = "info_request"
            elif "account_issue" in intent:
                intent = "account_issue"
            else:
                intent = "unknown"
                
            logger.info(f"LLM intent classification completed in {classification_time:.2f}s: {intent}")
            
        except Exception as e:
            logger.error(f"Error in LLM intent classification: {str(e)}", exc_info=True)
            # Default to unknown in case of errors
            intent = "unknown"
        
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
        Extract email address from user input using LLM.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with extracted email or response asking for it
        """
        # First, check for an existing user_email in state
        if state.get("user_email"):
            logger.info(f"Using existing email from state: {state['user_email']}")
            return {
                **state,
                "current_step": "email_provided"
            }
        
        # Get the user input with more robust handling
        user_input = state.get("user_input", "")
        if not user_input:
            messages = state.get("messages", [])
            if messages:
                for msg in reversed(messages):
                    if msg.get("role") == "user" and msg.get("content"):
                        user_input = msg.get("content")
                        break
        
        # First, try a quick check for @ symbol to avoid LLM call if no email is present
        if not user_input or '@' not in user_input:
            # Try to get conversation history to look for email in previous messages
            try:
                session_id = state.get("session_id")
                if session_id:
                    mem0 = await get_mem0()
                    if mem0:
                        history = await mem0.get_conversation_history(session_id)
                        
                        # Construct full conversation context
                        conversation_text = ""
                        if history:
                            for msg in history:
                                role = msg.get("role", "")
                                content = msg.get("content", "")
                                if role and content:
                                    conversation_text += f"{role.capitalize()}: {content}\n"
                            
                            # Only call LLM if there might be an email (@ symbol)
                            if '@' in conversation_text:
                                # Use LLM to extract email from conversation history
                                try:
                                    email = await extract_email_with_llm(conversation_text)
                                    if email:
                                        logger.info(f"Extracted email from conversation history with LLM: {email}")
                                        return {
                                            **state,
                                            "user_email": email,
                                            "current_step": "email_provided"
                                        }
                                except Exception as e:
                                    logger.error(f"Error extracting email from conversation history with LLM: {str(e)}")
            except Exception as e:
                logger.error(f"Error retrieving conversation history for email extraction: {str(e)}")
        
        if not user_input:
            logger.warning("No user input found for email extraction")
            return {
                **state,
                "current_step": "need_email"
            }
        
        # Use LLM to extract email from current message
        logger.info(f"Attempting to extract email from current message with LLM")
        try:
            email = await extract_email_with_llm(user_input)
            if email:
                logger.info(f"Extracted email with LLM: {email}")
                return {
                    **state,
                    "user_email": email,
                    "current_step": "email_provided"
                }
            else:
                logger.info("No email found with LLM extraction")
                return {
                    **state,
                    "current_step": "need_email"
                }
        except Exception as e:
            logger.error(f"Error in LLM email extraction: {str(e)}", exc_info=True)
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