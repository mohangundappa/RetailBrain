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
from backend.brain.agents.langgraph_agent import LangGraphAgent

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

Output as JSON with these fields:
- category: the category name
- confidence: a number between 0.0 and 1.0
- response: an appropriate response if category is greeting or goodbye, otherwise null

JSON Output:
""")
    
    # Create and invoke the chain
    special_case_chain = special_case_prompt | llm | StrOutputParser()
    
    try:
        result = special_case_chain.invoke({"message": user_message})
        
        # Parse the result as JSON
        special_case_data = json.loads(result)
        
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
        
    except Exception as e:
        logger.error(f"Error checking special cases: {str(e)}", exc_info=True)
        # Record error in execution state
        execution = {**new_state.get("execution", {})}
        errors = execution.get("errors", [])
        errors.append({
            "node": "handle_special_cases",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        execution["errors"] = errors
        new_state["execution"] = execution
    
    return new_state


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
    
    # TODO: Implement actual intent classification
    # For now, we'll just set default values
    
    # Update metadata with intent information
    metadata = {**new_state.get("metadata", {})}
    metadata["intent_classification"] = {
        "intent": "unknown",
        "confidence": 0.0,
        "timestamp": datetime.now().isoformat()
    }
    new_state["metadata"] = metadata
    
    logger.info("Intent classification completed")
    return new_state


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

JSON Output:
""")
        
        # Format history for the prompt
        formatted_history = "\n".join([
            f"{entry['role'].upper()}: {entry['content']}"
            for entry in messages[-4:]  # Use last 4 messages for context
        ])
        
        # Create and invoke the chain
        continuity_chain = continuity_prompt | llm | StrOutputParser()
        
        try:
            result = continuity_chain.invoke({
                "history": formatted_history,
                "message": user_message,
                "last_agent": last_agent
            })
            
            # Parse the result as JSON
            continuity_data = json.loads(result)
            
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
                
        except Exception as e:
            logger.error(f"Error checking conversation continuity: {str(e)}", exc_info=True)
            # Record error in execution state
            execution = {**new_state.get("execution", {})}
            errors = execution.get("errors", [])
            errors.append({
                "node": "select_agent",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            execution["errors"] = errors
            new_state["execution"] = execution
    
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

JSON Output:
""")
    
    # Format agent descriptions for the prompt
    agent_descriptions = "\n".join([
        f"- {agent_id}: {agent_configs.get(agent_id, {}).get('description', 'No description')}"
        for agent_id in available_agents
    ])
    
    # Create and invoke the chain
    agent_selection_chain = agent_selection_prompt | llm | StrOutputParser()
    
    try:
        result = agent_selection_chain.invoke({
            "message": user_message,
            "agent_descriptions": agent_descriptions
        })
        
        # Parse the result as JSON
        scores = json.loads(result)
        
        # Find the best scoring agent
        best_agent = None
        best_score = 0.0
        for agent_id in available_agents:
            score = scores.get(agent_id, 0.0)
            if score > best_score:
                best_agent = agent_id
                best_score = score
        
        # Update agent state with selection result
        agent_state = {**new_state.get("agent", {})}
        if best_agent and best_score > 0.5:  # Require a minimum confidence
            agent_state["selected_agent"] = best_agent
            agent_state["confidence"] = best_score
            agent_state["selection_info"] = {
                "agent_id": best_agent,
                "agent_name": best_agent,  # Use ID as name for now
                "confidence": best_score,
                "reason": f"Best match for user request with score {best_score}"
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
        
        logger.info(f"Selected agent: {best_agent}, confidence: {best_score}")
        
    except Exception as e:
        logger.error(f"Error selecting agent: {str(e)}", exc_info=True)
        # Record error in execution state
        execution = {**new_state.get("execution", {})}
        errors = execution.get("errors", [])
        errors.append({
            "node": "select_agent",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })
        execution["errors"] = errors
        new_state["execution"] = execution
    
    return new_state


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
    
    # TODO: Actually implement agent processing
    # For now, we'll use a placeholder response
    
    # Generate placeholder response
    placeholder_response = f"This is a placeholder response from agent {selected_agent_id}. In a real implementation, this would be the result of processing your message: '{user_message}'"
    
    # Add placeholder response to conversation
    new_state = add_message_to_conversation(
        new_state, 
        placeholder_response, 
        role="assistant", 
        agent=selected_agent_id
    )
    
    # Add to tools used if any
    execution = {**new_state.get("execution", {})}
    tools_used = execution.get("tools_used", [])
    tools_used.append("placeholder_tool")
    execution["tools_used"] = tools_used
    new_state["execution"] = execution
    
    logger.info(f"Processed message with agent {selected_agent_id}")
    return new_state


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
    
    # For now, just update the timestamp
    memory = {**new_state.get("memory", {})}
    memory["memory_last_updated"] = datetime.now()
    new_state["memory"] = memory
    
    logger.info("Memory updated")
    return new_state