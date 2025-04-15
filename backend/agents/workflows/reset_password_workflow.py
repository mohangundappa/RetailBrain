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
        Classify the user's intent regarding password reset.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with intent classification
        """
        # Define the intent classifier prompt
        intent_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are an intelligent assistant that classifies user intents for password reset requests. "
                "Determine whether the user is asking for information about password reset, "
                "actually requesting a password reset, or describing another account issue."
            )),
            MessagesPlaceholder(variable_name="messages"),
            HumanMessage(content=(
                "Based on the conversation history and the user's last message, classify their intent as: "
                "1. INFO_REQUEST: User is asking about password policies or reset procedures.\n"
                "2. RESET_REQUEST: User explicitly wants to reset their password.\n"
                "3. ACCOUNT_ISSUE: User has other account-related issues.\n"
                "4. UNKNOWN: Intent cannot be determined.\n\n"
                "Respond with a JSON object containing 'intent' (one of the categories above) and 'reasoning' (your explanation)."
            ))
        ])
        
        # Define the output parser
        intent_output_parser = JsonOutputParser()
        
        # Call the model
        try:
            response = await llm.ainvoke(
                intent_prompt.format(messages=state["messages"])
            )
            
            parsed_response = intent_output_parser.parse(response.content)
            intent = parsed_response.get("intent", "UNKNOWN")
            reasoning = parsed_response.get("reasoning", "No reasoning provided")
            
            # Map to enum value
            try:
                intent_enum = ResetPasswordIntent(intent.strip())
            except ValueError:
                # Default to unknown if invalid intent
                intent_enum = ResetPasswordIntent.UNKNOWN
                
            # Log the intent classification
            logger.info(f"Classified intent: {intent_enum} (Reasoning: {reasoning[:100]}...)")
                
            # Update state with intent
            return {
                **state,
                "reset_intent": intent_enum,
                "current_step": "intent_classified"
            }
        except Exception as e:
            logger.error(f"Error classifying intent: {str(e)}", exc_info=True)
            # Default to unknown intent on error
            return {
                **state,
                "reset_intent": ResetPasswordIntent.UNKNOWN,
                "current_step": "intent_classified"
            }
    
    async def extract_email(state: ResetPasswordState) -> Dict[str, Any]:
        """
        Extract email address from user input or ask for it if needed.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with extracted email or response asking for it
        """
        user_input = state["user_input"]
        
        # Define email extraction prompt
        email_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are an assistant that extracts email addresses from text. "
                "Find any valid email address in the user's message."
            )),
            HumanMessage(content=(
                f"Extract any email address from this text: {user_input}\n\n"
                "Respond with a JSON object containing:\n"
                "- 'email': The extracted email address, or null if not found\n"
                "- 'email_provided': Boolean indicating if an email was found in the text"
            ))
        ])
        
        # Define the output parser
        email_output_parser = JsonOutputParser()
        
        try:
            response = await llm.ainvoke(email_prompt)
            parsed_response = email_output_parser.parse(response.content)
            
            email = parsed_response.get("email")
            email_provided = parsed_response.get("email_provided", False)
            
            if email_provided and email:
                # Store the extracted email
                return {
                    **state,
                    "user_email": email,
                    "current_step": "email_provided"
                }
            else:
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
        
        # Update the memory to store that we've asked for email
        try:
            mem0 = await get_mem0()
            if mem0:
                mem0.add_fact(
                    conversation_id=state["conversation_id"],
                    content="Asked for email address",
                    session_id=state["session_id"],
                    scope=MemoryScope.SHORT_TERM
                )
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
        
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
        email = state["user_email"]
        
        # In a real implementation, this would trigger an actual password reset flow
        # For now, we're simulating the process
        
        # Prepare a response with reset instructions
        response = (
            f"I've sent a password reset link to {email}. Please check your email and follow "
            "the instructions in the reset link. The link will expire in 24 hours.\n\n"
            "If you don't see the email, please check your spam folder. "
            "If you still don't receive it, please let me know and I'll try sending it again."
        )
        
        # Update memory to record that we've sent a reset link
        try:
            mem0 = await get_mem0()
            if mem0:
                mem0.add_fact(
                    conversation_id=state["conversation_id"],
                    content=f"Sent password reset link to {email}",
                    session_id=state["session_id"],
                    scope=MemoryScope.SHORT_TERM
                )
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
        
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
    
    # Create the state graph
    from typing import Dict as DictType
    workflow = StateGraph(DictType)
    
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
    # Initialize with just current message since memory integration is incomplete
    messages = [
        {"role": "user", "content": message}
    ]
    logger.info(f"Initializing workflow for conversation {conversation_id} and session {session_id}")
    
    # Prepare the initial state
    initial_state: ResetPasswordState = {
        "conversation_id": conversation_id,
        "session_id": session_id,
        "user_input": message,
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
                mem0.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=message,
                    session_id=session_id
                )
        except Exception as e:
            logger.error(f"Error saving message to memory: {str(e)}")
        
        # Execute the workflow
        result = await workflow.ainvoke(initial_state)
        
        # Store the agent response in memory if available
        if result.get("response"):
            try:
                mem0 = await get_mem0()
                if mem0:
                    mem0.add_message(
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