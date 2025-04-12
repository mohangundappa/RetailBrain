"""
Graph-based orchestrator using LangGraph's native constructs.

This module defines the GraphOrchestrator class which implements a LangGraph-based
orchestration system for routing user requests to appropriate agents.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
from datetime import datetime

from langgraph.graph import StateGraph, END
# AgentNode is not available in the current version, removing it
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.brain.native_graph.state_definitions import OrchestrationState
from backend.brain.native_graph.node_functions import (
    initialize_state,
    handle_special_cases,
    classify_intent,
    select_agent,
    process_with_agent,
    update_memory,
)
from backend.brain.agents.langgraph_agent import LangGraphAgent

logger = logging.getLogger(__name__)


class GraphOrchestrator:
    """
    Graph-based orchestrator for routing user requests to appropriate agents.
    
    This class builds and manages a LangGraph StateGraph for orchestrating
    conversations across multiple specialized agents.
    """
    
    def __init__(
        self,
        agents: Optional[List[LangGraphAgent]] = None,
        llm: Optional[ChatOpenAI] = None
    ):
        """
        Initialize the graph orchestrator.
        
        Args:
            agents: List of agent instances to coordinate
            llm: Language model for orchestration tasks
        """
        self.agents = agents or []
        
        # Set default LLM if not provided
        self.llm = llm or ChatOpenAI(
            model="gpt-4o",
            temperature=0.2  # Lower temperature for more deterministic routing
        )
        
        # Build the graph
        self.graph = self._build_graph()
        
        # Compile the graph
        self.compiled_graph = self.graph.compile()
        
        logger.info(f"Initialized GraphOrchestrator with {len(self.agents)} agents")
    
    def _build_graph(self) -> StateGraph:
        """
        Build the orchestration graph.
        
        Returns:
            Compiled StateGraph
        """
        # Create the graph
        graph = StateGraph(OrchestrationState)
        
        # Add nodes
        graph.add_node("handle_special_cases", handle_special_cases)
        graph.add_node("classify_intent", classify_intent)
        graph.add_node("select_agent", select_agent)
        graph.add_node("process_with_agent", process_with_agent)
        graph.add_node("update_memory", update_memory)
        
        # Add edges
        graph.add_edge("handle_special_cases", "classify_intent")
        graph.add_edge("classify_intent", "select_agent")
        
        # Add conditional edge based on special case detection
        def route_after_special_case(state: OrchestrationState) -> str:
            """Determine if we should process with agent or skip to response"""
            agent_state = state.get("agent", {})
            if agent_state.get("special_case_detected", False):
                # Skip to process_with_agent for special cases
                return "process_with_agent"
            # Normal flow to select_agent
            return "select_agent"
        
        graph.add_conditional_edges(
            "handle_special_cases",
            route_after_special_case,
            {
                "process_with_agent": "process_with_agent",
                "select_agent": "classify_intent"
            }
        )
        
        # Add conditional edge based on agent selection
        def route_after_selection(state: OrchestrationState) -> str:
            """Determine what to do after agent selection"""
            agent_state = state.get("agent", {})
            selected_agent = agent_state.get("selected_agent")
            if selected_agent:
                # We have a selected agent, proceed to processing
                return "process"
            # No agent selected, end the flow
            return "end"
        
        graph.add_conditional_edges(
            "select_agent",
            route_after_selection,
            {
                "process": "process_with_agent",
                "end": END
            }
        )
        
        # Complete the flow
        graph.add_edge("process_with_agent", "update_memory")
        graph.add_edge("update_memory", END)
        
        # Set the entry point
        graph.set_entry_point("handle_special_cases")
        
        return graph
    
    def register_agent(self, agent: LangGraphAgent) -> bool:
        """
        Register a new agent with the orchestrator.
        
        Args:
            agent: The agent to register
            
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            # Check if agent is already registered
            for existing_agent in self.agents:
                if existing_agent.get_id() == agent.get_id():
                    logger.info(f"Agent {agent.get_name()} already registered with orchestrator")
                    return True
            
            # Add the agent to the list
            self.agents.append(agent)
            
            # We don't need to update the state here as initialize_state is called
            # each time process_message is invoked
            
            logger.info(f"Registered agent {agent.get_name()} with orchestrator")
            return True
        except Exception as e:
            logger.error(f"Error registering agent: {str(e)}", exc_info=True)
            return False
    
    def list_agents(self) -> List[str]:
        """
        List all registered agents.
        
        Returns:
            List of agent names
        """
        return [agent.name for agent in self.agents]
    
    async def process_message(
        self, 
        message: str, 
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        db_session: Optional[AsyncSession] = None,
        recover_state: bool = True
    ) -> Dict[str, Any]:
        """
        Process a message and route to the appropriate agent.
        
        Args:
            message: User's message text
            session_id: Session identifier
            context: Additional context for processing
            db_session: Optional database session for state persistence
            recover_state: Whether to attempt to recover state from previous session
            
        Returns:
            Response with agent output
        """
        logger.info(f"TRACE: Entered GraphOrchestrator.process_message")
        
        # Attempt to recover state from previous conversation if enabled
        state = None
        if recover_state and db_session:
            try:
                from backend.brain.native_graph.state_recovery import (
                    resilient_recover_state, 
                    process_pending_operations,
                    check_db_connection
                )
                
                logger.info(f"Attempting to recover state for session {session_id}")
                
                # First, check if the database connection is available
                db_available = await check_db_connection(db_session)
                if not db_available:
                    logger.warning("Database connection unavailable for state recovery, starting with fresh state")
                else:
                    # Try to recover state with resilient function
                    state = await resilient_recover_state(session_id, db_session)
                    
                    if state:
                        logger.info(f"Successfully recovered state for session {session_id}")
                        
                        # Process any pending operations that might have failed in previous interactions
                        state = await process_pending_operations(state, session_id, db_session)
                        
                        # Add the new user message to the recovered state
                        state["conversation"]["last_user_message"] = message
                        state["conversation"]["messages"].append({
                            "role": "user",
                            "content": message,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        logger.info(f"No previous state found for session {session_id}, starting fresh")
            except Exception as e:
                logger.warning(f"Error recovering state: {str(e)}", exc_info=True)
                state = None
        
        # Initialize new state if recovery failed or was disabled
        if not state:
            # Initialize the state
            state = initialize_state()
            
            # Update the session ID
            conversation = state.get("conversation", {})
            conversation["session_id"] = session_id
            state["conversation"] = conversation
            
            # Add the user message to the state
            state["conversation"]["last_user_message"] = message
            state["conversation"]["messages"] = [{
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            }]
        
        # Add available agents and their configs to the state
        agent_state = state.get("agent", {})
        
        # Store agent instances directly in the state for node functions to access
        available_agents = {}
        for agent in self.agents:
            agent_id = agent.get_id()
            available_agents[agent_id] = agent
        agent_state["available_agents"] = available_agents
        
        # Add agent IDs for reference
        agent_state["agent_ids"] = [agent.get_id() for agent in self.agents]
        
        # Add agent configs
        agent_configs = {}
        for agent in self.agents:
            agent_id = agent.get_id()
            agent_configs[agent_id] = {
                "name": agent.get_name(),
                "description": agent.get_description(),
                "id": agent_id
            }
        agent_state["agent_configs"] = agent_configs
        state["agent"] = agent_state
        
        # Add context to metadata
        if context:
            metadata = state.get("metadata", {})
            metadata["context"] = context
            state["metadata"] = metadata
        
        # Process the message through the graph
        try:
            # Execute the graph with the initial state
            start_time = time.time()
            events = list(self.compiled_graph.stream(state))
            execution_time = time.time() - start_time
            
            # Get the final state from the last event
            if events:
                # Convert dict_values to a dictionary
                final_state = dict(zip(events[-1].keys(), events[-1].values()))
                
                # Update execution info with total execution time
                execution = final_state.get("execution", {})
                execution["total_execution_time"] = execution_time
                final_state["execution"] = execution
                
                # Log performance information
                logger.info(f"Graph execution completed in {execution_time:.4f} seconds")
                
                # Persist the final state to the database if a session was provided
                if db_session:
                    try:
                        from backend.brain.native_graph.state_recovery import (
                            resilient_persist_state, 
                            resilient_create_checkpoint,
                            process_pending_operations
                        )
                        
                        # Get session ID
                        session_id = final_state.get("conversation", {}).get("session_id")
                        if session_id:
                            logger.info(f"Persisting final state for session {session_id}")
                            
                            # First, try to process any pending operations that may have failed previously
                            final_state = await process_pending_operations(final_state, session_id, db_session)
                            
                            # Save the state with resilient persistence
                            final_state = await resilient_persist_state(final_state, session_id, db_session)
                            
                            # Create a checkpoint after every complete interaction
                            message_count = len(final_state.get("conversation", {}).get("messages", []))
                            if message_count >= 2:  # Only create checkpoint if we have at least one exchange
                                checkpoint_name = f"interaction_{message_count//2}"
                                final_state = await resilient_create_checkpoint(
                                    final_state, 
                                    session_id, 
                                    checkpoint_name, 
                                    db_session
                                )
                                logger.info(f"Created checkpoint '{checkpoint_name}' for session {session_id}")
                    except Exception as persist_error:
                        logger.warning(f"Error persisting state: {str(persist_error)}", exc_info=True)
                
                # Check for errors in execution state
                errors = execution.get("errors", [])
                if errors:
                    error_count = len(errors)
                    logger.warning(f"Graph execution completed with {error_count} errors")
                    for error in errors:
                        logger.debug(f"Error in node {error.get('node')}: {error.get('error')}, "
                                     f"type: {error.get('error_type')}")
            else:
                # Return default response if no events were generated
                logger.error("No events generated during graph execution")
                return {
                    "response": "I'm unable to process your request at this time. No agents are available.",
                    "agent": "error",
                    "confidence": 0.0,
                    "error": "No events generated during processing",
                    "error_type": "orchestration_error"
                }
            
            # Extract the response information
            conversation = final_state.get("conversation", {})
            messages = conversation.get("messages", [])
            
            # Find the last assistant message
            assistant_messages = [m for m in messages if m.get("role") == "assistant"]
            if assistant_messages:
                last_message = assistant_messages[-1]
                response_content = last_message.get("content", "")
                response_agent = last_message.get("agent", "unknown")
            else:
                response_content = "No response generated"
                response_agent = "error"
            
            # Get confidence from agent state
            agent_state = final_state.get("agent", {})
            confidence = agent_state.get("confidence", 0.0)
            
            # Get entities and tools used
            entities = final_state.get("entities", {}).get("entities", {})
            execution = final_state.get("execution", {})
            tools_used = execution.get("tools_used", [])
            
            # Include errors in the response if any occurred
            errors = execution.get("errors", [])
            
            # Build response
            response = {
                "response": response_content,
                "agent": response_agent,
                "confidence": confidence,
                "entities": entities,
                "tools_used": tools_used,
                "execution_time": execution_time,
                "execution_path": execution.get("execution_path", [])
            }
            
            # Add errors to response if they occurred
            if errors:
                response["errors"] = [
                    {
                        "node": error.get("node"),
                        "error_type": error.get("error_type", "unknown"),
                        "timestamp": error.get("timestamp")
                    }
                    for error in errors
                ]
            
            return response
            
        except Exception as e:
            # Classify the error type
            from backend.brain.native_graph.error_handling import classify_error, ErrorType
            error_type = classify_error(e)
            
            logger.error(
                f"Error processing message: {str(e)} (type: {error_type})", 
                exc_info=True
            )
            
            # Generate appropriate user-facing error message
            user_message = "I encountered an issue while processing your request. Please try again."
            
            if error_type == ErrorType.LLM_RATE_LIMIT:
                user_message = "I'm experiencing a lot of requests right now. Please try again in a moment."
            elif error_type == ErrorType.LLM_CONTEXT_LIMIT:
                user_message = "Your request is too complex for me to process right now. Could you try with a shorter message?"
            elif error_type == ErrorType.LLM_API_ERROR:
                user_message = "I'm having trouble connecting to my knowledge base. Please try again shortly."
            
            return {
                "response": user_message,
                "agent": "error",
                "confidence": 0.0,
                "error": str(e),
                "error_type": error_type
            }