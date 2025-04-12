"""
Node functions for the LangGraph-based orchestration system.

This module contains the functions that are used as nodes in the LangGraph 
orchestration flow. Each function takes the current state and returns a modified state,
performing operations like intent classification, agent selection, and message processing.
"""

import logging
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import time

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.brain.native_graph.state_definitions import OrchestrationState
from backend.agents.framework.langgraph.langgraph_agent import LangGraphAgent
from backend.brain.native_graph.error_handling import (
    with_error_handling, 
    parse_json_with_recovery, 
    record_error,
    retry_on_error,
    ErrorType
)

logger = logging.getLogger(__name__)


def initialize_state() -> OrchestrationState:
    """
    Initialize a new orchestration state.
    
    Returns:
        A new OrchestrationState with default values
    """
    now = datetime.now()
    
    return {
        "conversation": {
            "session_id": f"session_{int(time.time())}",
            "messages": [],
            "last_user_message": "",
            "last_assistant_message": None,
            "last_agent": None
        },
        "entities": {
            "entities": {},
            "extracted_this_turn": [],
            "validated": {}
        },
        "agent": {
            "available_agents": [],
            "selected_agent": None,
            "selection_info": None,
            "confidence": 0.0,
            "continue_with_same_agent": False,
            "special_case_detected": False,
            "special_case_type": None,
            "special_case_response": None,
            "agent_configs": {}
        },
        "memory": {
            "working_memory_ids": [],
            "episodic_memory_ids": [],
            "relevant_memory_ids": [],
            "agent_memory_ids": {},
            "memory_last_updated": now
        },
        "execution": {
            "current_node": "start",
            "previous_node": None,
            "execution_path": ["start"],
            "errors": [],
            "request_start_time": now,
            "latencies": {},
            "tools_used": []
        },
        "metadata": {
            "created_at": now.isoformat()
        }
    }


def add_message_to_conversation(
    state: OrchestrationState, 
    message: str, 
    role: str = "user", 
    agent: Optional[str] = None
) -> OrchestrationState:
    """
    Add a message to the conversation history.
    
    Args:
        state: Current orchestration state
        message: Message content
        role: Message role (user or assistant)
        agent: Agent that generated the message (for assistant messages)
        
    Returns:
        Updated state with message added
    """
    # Create a new state to avoid modifying the input
    new_state = {**state}
    
    # Create message object
    message_obj = {
        "role": role,
        "content": message,
        "timestamp": datetime.now().isoformat()
    }
    
    if role == "assistant" and agent:
        message_obj["agent"] = agent
    
    # Update conversation state
    conversation = {**new_state.get("conversation", {})}
    messages = conversation.get("messages", [])
    messages.append(message_obj)
    conversation["messages"] = messages
    
    # Update last message references
    if role == "user":
        conversation["last_user_message"] = message
    else:
        conversation["last_assistant_message"] = message
        if agent:
            conversation["last_agent"] = agent
    
    new_state["conversation"] = conversation
    
    return new_state


def record_execution_step(state: OrchestrationState, node_name: str) -> OrchestrationState:
    """
    Record a step in the execution path.
    
    Args:
        state: Current orchestration state
        node_name: Name of the current node
        
    Returns:
        Updated state with execution step recorded
    """
    # Create a new state to avoid modifying the input
    new_state = {**state}
    
    # Update execution state
    execution = {**new_state.get("execution", {})}
    execution["previous_node"] = execution.get("current_node")
    execution["current_node"] = node_name
    
    # Add to execution path
    path = execution.get("execution_path", [])
    path.append(node_name)
    execution["execution_path"] = path
    
    # Record latency
    start_time = execution.get("request_start_time", datetime.now())
    latency = (datetime.now() - start_time).total_seconds()
    latencies = execution.get("latencies", {})
    latencies[node_name] = latency
    execution["latencies"] = latencies
    
    new_state["execution"] = execution
    
    return new_state


@with_error_handling("handle_special_cases")
def handle_special_cases(state: OrchestrationState) -> OrchestrationState:
    """
    Handle special cases like greetings, goodbyes, and human requests.
    
    Args:
        state: Current orchestration state
        
    Returns:
        Updated state with special case detection
    """
    # Get the latest user message
    conversation = state.get("conversation", {})
    user_message = conversation.get("last_user_message", "")
    
    # Create a new state to avoid modifying the input
    new_state = record_execution_step(state, "handle_special_cases")
    
    # Skip if message is empty
    if not user_message:
        return new_state
    
    # Get LLM for special case detection
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2  # Lower temperature for more deterministic classification
    )
    
    # Define special case detection prompt
    special_case_prompt = PromptTemplate.from_template("""
Analyze the user message and determine if it falls into one of these special categories:
1. greeting - A simple greeting or introduction (e.g., "hello", "hi there")
2. goodbye - Ending the conversation (e.g., "bye", "thanks, that's all")
3. human_request - Explicitly asking for a human agent (e.g., "can I speak to a person")
4. none - Not a special case

User message: {message}

First categorize the message as one of: greeting, goodbye, human_request, or none.
Then provide a confidence score between 0.0 and 1.0 for your categorization.
For greetings and goodbyes, also provide an appropriate response.

Output as JSON and ONLY JSON with these fields:
- category: the category name as string
- confidence: a number between 0.0 and 1.0
- response: an appropriate response if category is greeting or goodbye, otherwise null

IMPORTANT: Format your response EXACTLY like this JSON example, with no additional text before or after:
{{"category": "none", "confidence": 0.0, "response": null}}

JSON Output:
""")
    
    # Create and invoke the chain
    special_case_chain = special_case_prompt | llm | StrOutputParser()
    
    # Use retry_on_error for LLM API calls in a synchronous context
    @retry_on_error(
        max_retries=3,
        retry_on=[ErrorType.LLM_RATE_LIMIT, ErrorType.LLM_API_ERROR]
    )
    def invoke_special_case_detection(message: str) -> str:
        return special_case_chain.invoke({"message": message})
    
    # Invoke the chain with retry logic
    result = invoke_special_case_detection(user_message)
    
    # Parse the result as JSON with robust error recovery
    special_case_data = parse_json_with_recovery(
        result,
        default_value={"category": "none", "confidence": 0.0, "response": None}
    )
    
    category = special_case_data.get("category", "none")
    confidence = float(special_case_data.get("confidence", 0.0))
    response = special_case_data.get("response")
    
    if category != "none" and confidence > 0.7:
        # Update agent state to indicate special case
        agent_state = {**new_state.get("agent", {})}
        agent_state["special_case_detected"] = True
        agent_state["special_case_type"] = category
        agent_state["special_case_response"] = response
        new_state["agent"] = agent_state
    
    logger.info(f"Special case detection: {category}, confidence: {confidence}")
    
    return new_state


@with_error_handling("classify_intent")
def classify_intent(state: OrchestrationState) -> OrchestrationState:
    """
    Classify the intent of the user message.
    
    Args:
        state: Current orchestration state
        
    Returns:
        Updated state with intent classification
    """
    # Get the latest user message
    conversation = state.get("conversation", {})
    user_message = conversation.get("last_user_message", "")
    
    # Create a new state to avoid modifying the input
    new_state = record_execution_step(state, "classify_intent")
    
    # Skip if message is empty
    if not user_message:
        return new_state
    
    # Check for special case
    agent_state = new_state.get("agent", {})
    if agent_state.get("special_case_detected", False):
        logger.info("Special case detected, skipping intent classification")
        return new_state
    
    # TODO: Implement actual intent classification with LLM
    # In a real implementation, we would have code like:
    # try:
    #     # Get LLM for intent classification
    #     llm = ChatOpenAI(
    #         model="gpt-4o",
    #         temperature=0.2
    #     )
    #     
    #     # Define intent classification prompt
    #     intent_prompt = PromptTemplate.from_template("""
    #     Analyze this user message and determine the primary intent.
    #     
    #     User message: {message}
    #     
    #     Output a JSON object with:
    #     - intent: a single word describing the primary intent (e.g., "track_order", "find_store", "login_help")
    #     - confidence: a number between 0.0 and 1.0
    #     - sub_intent: optional more specific intent if applicable
    #     
    #     JSON Output:
    #     """)
    #     
    #     # Create and invoke the chain with retry logic
    #     intent_chain = intent_prompt | llm | StrOutputParser()
    #     result = intent_chain.invoke({"message": user_message})
    #     
    #     # Parse the result as JSON with robust error recovery
    #     intent_data = parse_json_with_recovery(
    #         result,
    #         default_value={"intent": "unknown", "confidence": 0.0}
    #     )
    #     
    #     # Update metadata with intent information
    #     metadata = {**new_state.get("metadata", {})}
    #     metadata["intent_classification"] = {
    #         "intent": intent_data.get("intent", "unknown"),
    #         "confidence": float(intent_data.get("confidence", 0.0)),
    #         "sub_intent": intent_data.get("sub_intent"),
    #         "timestamp": datetime.now().isoformat()
    #     }
    #     new_state["metadata"] = metadata
    # except Exception as e:
    #     # Record error but continue execution
    #     logger.error(f"Error classifying intent: {str(e)}", exc_info=True)
    #     new_state = record_error(
    #         new_state, 
    #         "classify_intent", 
    #         e, 
    #         error_type=classify_error(e)
    #     )
    
    # For now, we'll just set default values
    metadata = {**new_state.get("metadata", {})}
    metadata["intent_classification"] = {
        "intent": "unknown",
        "confidence": 0.0,
        "timestamp": datetime.now().isoformat()
    }
    new_state["metadata"] = metadata
    
    logger.info("Intent classification completed")
    return new_state


@with_error_handling("select_agent")
def select_agent(state: OrchestrationState) -> OrchestrationState:
    """
    Select the most appropriate agent for the user message.
    
    Args:
        state: Current orchestration state
        
    Returns:
        Updated state with agent selection
    """
    # Get the latest user message
    conversation = state.get("conversation", {})
    user_message = conversation.get("last_user_message", "")
    last_agent = conversation.get("last_agent")
    messages = conversation.get("messages", [])
    
    # Create a new state to avoid modifying the input
    new_state = record_execution_step(state, "select_agent")
    
    # Skip if message is empty
    if not user_message:
        return new_state
    
    # Check for special case
    agent_state = new_state.get("agent", {})
    if agent_state.get("special_case_detected", False):
        logger.info("Special case detected, skipping agent selection")
        return new_state
    
    # Get available agents
    available_agents = agent_state.get("available_agents", [])
    agent_configs = agent_state.get("agent_configs", {})
    
    if not available_agents:
        logger.warning("No available agents for selection")
        # Update agent state with selection info
        agent_state = {**new_state.get("agent", {})}
        agent_state["selected_agent"] = None
        agent_state["confidence"] = 0.0
        agent_state["selection_info"] = {
            "agent_id": "",
            "agent_name": "",
            "confidence": 0.0,
            "reason": "No available agents"
        }
        new_state["agent"] = agent_state
        return new_state
    
    # Check for conversation continuity if there was a previous agent
    if last_agent and len(messages) >= 2:
        # Get LLM for continuity detection
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.2  # Lower temperature for more deterministic classification
        )
        
        # Define continuity detection prompt
        continuity_prompt = PromptTemplate.from_template("""
Consider this conversation history:

{history}

Current user message: {message}

The previous message was handled by the agent: {last_agent}

Determine if the current message is continuing the same conversation topic that the previous agent was handling.
Output a JSON object with:
- continue_with_same_agent: boolean (true if the conversation is continuing, false if it's a new topic)
- confidence: number between 0.0 and 1.0
- reasoning: brief explanation of your decision

IMPORTANT: Format your response EXACTLY as a valid JSON object with no additional text before or after.
For example:
{{"continue_with_same_agent": true, "confidence": 0.8, "reasoning": "The user is asking for more information about the same topic."}}

JSON Output:
""")
        
        # Format history for the prompt
        formatted_history = "\n".join([
            f"{entry['role'].upper()}: {entry['content']}"
            for entry in messages[-4:]  # Use last 4 messages for context
        ])
        
        # Create and invoke the chain
        continuity_chain = continuity_prompt | llm | StrOutputParser()
        
        # Use retry for LLM API calls
        @retry_on_error(
            max_retries=2,
            retry_on=[ErrorType.LLM_RATE_LIMIT, ErrorType.LLM_API_ERROR]
        )
        def check_conversation_continuity(
            history: str, 
            message: str, 
            last_agent_id: str
        ) -> Dict[str, Any]:
            result = continuity_chain.invoke({
                "history": history,
                "message": message,
                "last_agent": last_agent_id
            })
            
            # Use robust JSON parsing with recovery
            return parse_json_with_recovery(
                result,
                default_value={
                    "continue_with_same_agent": False,
                    "confidence": 0.0,
                    "reasoning": "Failed to determine conversation continuity"
                }
            )
        
        # Check conversation continuity with retry logic and robust parsing
        continuity_data = check_conversation_continuity(
            formatted_history, user_message, last_agent
        )
        
        # Extract data with safe defaults
        continue_with_same_agent = continuity_data.get("continue_with_same_agent", False)
        continuity_confidence = float(continuity_data.get("confidence", 0.0))
        reasoning = continuity_data.get("reasoning", "")
        
        if continue_with_same_agent and continuity_confidence > 0.6:
            # Update agent state with continuity decision
            agent_state = {**new_state.get("agent", {})}
            agent_state["continue_with_same_agent"] = True
            agent_state["selected_agent"] = last_agent
            agent_state["confidence"] = continuity_confidence
            agent_state["selection_info"] = {
                "agent_id": last_agent,
                "agent_name": last_agent,  # Use ID as name for now
                "confidence": continuity_confidence,
                "reason": f"Continuing conversation: {reasoning}"
            }
            new_state["agent"] = agent_state
            
            logger.info(f"Continuing with same agent: {last_agent}, confidence: {continuity_confidence}")
            return new_state
    
    # If not continuing with the same agent, select a new one
    # Get LLM for agent selection
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2  # Lower temperature for more deterministic classification
    )
    
    # Define agent selection prompt
    agent_selection_prompt = PromptTemplate.from_template("""
I need to route a user request to the right specialized agent.

User message: {message}

Available agents:
{agent_descriptions}

For each agent, provide a relevance score between 0.0 and 1.0 indicating how well the agent matches the user's request.
0.0 means completely irrelevant, 1.0 means perfect match.

Output as a JSON object with agent names as keys and scores as values.
Sort in descending order of scores.

IMPORTANT: Format your response EXACTLY as a valid JSON object with no additional text before or after.
For example, if there are two agents "package_tracking" and "store_locator", output should look like:
{{"package_tracking": 0.9, "store_locator": 0.1}}

JSON Output:
""")
    
    # Get agent IDs and configs
    agent_ids = agent_state.get("agent_ids", [])
    agent_configs = agent_state.get("agent_configs", {})
    
    # Format agent descriptions for the prompt
    agent_descriptions = "\n".join([
        f"- {agent_id}: {agent_configs.get(agent_id, {}).get('description', 'No description')}"
        for agent_id in agent_ids
    ])
    
    # Create and invoke the chain
    agent_selection_chain = agent_selection_prompt | llm | StrOutputParser()
    
    # Use retry for LLM API calls
    @retry_on_error(
        max_retries=2,
        retry_on=[ErrorType.LLM_RATE_LIMIT, ErrorType.LLM_API_ERROR]
    )
    def select_best_agent(
        message: str, 
        descriptions: str,
        available_ids: List[str]
    ) -> Tuple[Dict[str, float], str, float]:
        # Call the LLM for agent selection
        result = agent_selection_chain.invoke({
            "message": message,
            "agent_descriptions": descriptions
        })
        
        # Use robust JSON parsing with recovery
        scores = parse_json_with_recovery(result, default_value={})
        
        # If parsing failed or returned empty, use keyword matching as fallback
        if not scores:
            logger.warning("Failed to parse agent selection scores, using keyword matching fallback")
            for agent_id in available_ids:
                if agent_id.lower() in message.lower():
                    scores[agent_id] = 0.9
                else:
                    scores[agent_id] = 0.1
        
        # Find the best scoring agent
        best_agent = None
        best_score = 0.0
        for agent_id in available_ids:
            score = float(scores.get(agent_id, 0.0))
            if score > best_score:
                best_agent = agent_id
                best_score = score
        
        return scores, best_agent, best_score
    
    # Select the best agent with retry logic
    scores, best_agent, best_score = select_best_agent(
        user_message, agent_descriptions, agent_ids
    )
    
    # Update agent state with selection result
    agent_state = {**new_state.get("agent", {})}
    if best_agent and best_score > 0.5:  # Require a minimum confidence
        agent_state["selected_agent"] = best_agent
        agent_state["confidence"] = best_score
        agent_state["selection_info"] = {
            "agent_id": best_agent,
            "agent_name": agent_configs.get(best_agent, {}).get("name", best_agent),
            "confidence": best_score,
            "reason": f"Best match for user request with score {best_score:.2f}"
        }
    else:
        # No confident selection
        agent_state["selected_agent"] = None
        agent_state["confidence"] = best_score
        agent_state["selection_info"] = {
            "agent_id": "",
            "agent_name": "",
            "confidence": best_score,
            "reason": "No agent confidently matched the request"
        }
    
    new_state["agent"] = agent_state
    
    logger.info(f"Selected agent: {best_agent}, confidence: {best_score:.2f}")
    logger.debug(f"Agent selection scores: {scores}")
    
    return new_state


@with_error_handling("process_with_agent")
def process_with_agent(state: OrchestrationState) -> OrchestrationState:
    """
    Process the user message with the selected agent.
    
    Args:
        state: Current orchestration state
        
    Returns:
        Updated state with agent response
    """
    # Get the latest user message and selected agent
    conversation = state.get("conversation", {})
    user_message = conversation.get("last_user_message", "")
    
    agent_state = state.get("agent", {})
    selected_agent_id = agent_state.get("selected_agent")
    special_case_detected = agent_state.get("special_case_detected", False)
    special_case_response = agent_state.get("special_case_response")
    
    # Create a new state to avoid modifying the input
    new_state = record_execution_step(state, "process_with_agent")
    
    # Skip if message is empty
    if not user_message:
        return new_state
    
    # Handle special cases
    if special_case_detected and special_case_response:
        logger.info(f"Handling special case response: {special_case_response}")
        # Add response to conversation
        new_state = add_message_to_conversation(
            new_state, 
            special_case_response, 
            role="assistant", 
            agent="special_case_handler"
        )
        return new_state
    
    # Check if we have a selected agent
    if not selected_agent_id:
        logger.warning("No agent selected, using fallback response")
        # Generate fallback response
        fallback_response = "I'm sorry, I'm not sure how to help with that request. Could you please provide more details or try asking in a different way?"
        
        # Add fallback response to conversation
        new_state = add_message_to_conversation(
            new_state, 
            fallback_response, 
            role="assistant", 
            agent="fallback"
        )
        return new_state
    
    # Get the agent instance from the agent state
    available_agents = agent_state.get("available_agents", {})
    agent_instance = available_agents.get(selected_agent_id)
    
    if not agent_instance:
        # Agent instance not found, record error and use a generic response
        logger.warning(f"Agent {selected_agent_id} instance not found, using generic response")
        
        # Record specific error type
        new_state = record_error(
            new_state,
            "process_with_agent",
            Exception(f"Agent instance '{selected_agent_id}' not found"),
            error_type=ErrorType.AGENT_NOT_FOUND,
            additional_info={"agent_id": selected_agent_id}
        )
        
        generic_response = f"I understand you're asking about '{user_message}'. Let me help you with that."
        
        # Add generic response to conversation
        new_state = add_message_to_conversation(
            new_state,
            generic_response,
            role="assistant",
            agent=selected_agent_id
        )
        return new_state
    
    # Use retry for agent processing
    @retry_on_error(
        max_retries=2,
        retry_on=[ErrorType.AGENT_EXECUTION_ERROR, ErrorType.LLM_API_ERROR]
    )
    def process_with_agent_instance(
        agent: Any, 
        message: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Process message with agent instance with retry and error recovery."""
        # Track any tools used during processing
        tools_used = []
        
        logger.info(f"Processing message with agent {selected_agent_id}")
        
        # Since this isn't an async function, we need to handle async agents differently
        # For now, we'll just call the agent directly and assume it's synchronous
        response = None
        if hasattr(agent, 'process'):
            if callable(agent.process):
                # Just call the method directly for now
                response = agent.process(message)
                
                # If response contains tools used, extract them
                if isinstance(response, dict) and "tools_used" in response:
                    tools_used = response.get("tools_used", [])
        
        # Extract the response text
        if isinstance(response, dict):
            response_text = response.get("response", "")
        else:
            response_text = str(response) if response is not None else ""
        
        return response_text, {"tools_used": tools_used}
    
    try:
        # Process the message with the agent, with retry logic
        response_text, metadata = process_with_agent_instance(agent_instance, user_message)
        
        # Add the response to the conversation
        new_state = add_message_to_conversation(
            new_state,
            response_text,
            role="assistant",
            agent=selected_agent_id
        )
        
        # Add to tools used if any
        execution = {**new_state.get("execution", {})}
        tools_used = execution.get("tools_used", [])
        tools_used.extend(metadata.get("tools_used", []))
        execution["tools_used"] = tools_used
        new_state["execution"] = execution
    
    except Exception as e:
        # All retries failed, generate a user-friendly error response
        error_type = classify_error(e)
        logger.error(
            f"Error processing with agent {selected_agent_id}: {str(e)} "
            f"(type: {error_type})",
            exc_info=True
        )
        
        # Record error in state
        new_state = record_error(
            new_state,
            "process_with_agent",
            e,
            error_type=error_type,
            additional_info={"agent_id": selected_agent_id, "message": user_message}
        )
        
        # Get an appropriate error recovery response
        recovery_response = get_error_recovery_response(new_state, e, error_type)
        
        # Add recovery response to conversation
        new_state = add_message_to_conversation(
            new_state,
            recovery_response,
            role="assistant",
            agent=f"{selected_agent_id}_error"
        )
    
    logger.info(f"Processed message with agent {selected_agent_id}")
    return new_state


@with_error_handling("update_memory")
def update_memory(state: OrchestrationState) -> OrchestrationState:
    """
    Update memory with the latest conversation information.
    
    Args:
        state: Current orchestration state
        
    Returns:
        Updated state with memory updated
    """
    # Create a new state to avoid modifying the input
    new_state = record_execution_step(state, "update_memory")
    
    # Get conversation for memory update
    conversation = state.get("conversation", {})
    messages = conversation.get("messages", [])
    
    # Skip if there are no messages to store
    if not messages:
        logger.debug("No messages to store in memory")
        return new_state
    
    # For now, just update the timestamp
    # In future implementations, we would connect to a memory storage system
    # and store the conversation data
    memory = {**new_state.get("memory", {})}
    memory["memory_last_updated"] = datetime.now()
    
    # In a real implementation, we would have code like:
    # try:
    #     # Store memory in database or external memory system
    #     memory_ids = await memory_service.store_conversation(messages)
    #     memory["working_memory_ids"].append(memory_ids["working_memory"])
    #     memory["episodic_memory_ids"].append(memory_ids["episodic_memory"])
    # except Exception as e:
    #     logger.error(f"Error updating memory: {str(e)}", exc_info=True)
    #     # Record error but continue execution
    #     new_state = record_error(
    #         new_state, 
    #         "update_memory", 
    #         e, 
    #         error_type=ErrorType.MEMORY_ERROR
    #     )
    
    new_state["memory"] = memory
    
    logger.info("Memory updated")
    return new_state