"""
Graph-based orchestrator using LangGraph's native constructs.

This module defines the GraphOrchestrator class which implements a LangGraph-based
orchestration system for routing user requests to appropriate agents.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
from datetime import datetime

from langgraph.graph import StateGraph, END
# AgentNode is not available in the current version, removing it
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

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
        # Check if agent is already registered
        for existing_agent in self.agents:
            if existing_agent.name == agent.name:
                logger.info(f"Agent {agent.name} already registered with orchestrator")
                return True
        
        # Add the agent to the list
        self.agents.append(agent)
        
        # Update the agent configs in the initial state
        logger.info(f"Registered agent {agent.name} with orchestrator")
        return True
    
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
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message and route to the appropriate agent.
        
        Args:
            message: User's message text
            session_id: Session identifier
            context: Additional context for processing
            
        Returns:
            Response with agent output
        """
        logger.info(f"TRACE: Entered GraphOrchestrator.process_message")
        
        # Initialize or get the state
        # For now, we'll always create a new state, but in the future
        # we could retrieve the state from a database based on session_id
        state = initialize_state()
        
        # Update the session ID
        conversation = state.get("conversation", {})
        conversation["session_id"] = session_id
        state["conversation"] = conversation
        
        # Add the user message to the state
        state = initialize_state()
        state["conversation"]["session_id"] = session_id
        state["conversation"]["last_user_message"] = message
        state["conversation"]["messages"] = [{
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }]
        
        # Add available agents and their configs to the state
        agent_state = state.get("agent", {})
        agent_state["available_agents"] = [agent.name for agent in self.agents]
        
        # Add agent configs
        agent_configs = {}
        for agent in self.agents:
            agent_configs[agent.name] = {
                "name": agent.name,
                "description": agent.description,
                "id": agent.id
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
            for event in self.compiled_graph.stream(state):
                # This loop will execute for each step in the graph
                # We could log or track these events if needed
                pass
            
            # Get the final state
            final_state = event.state
            
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
            
            # Return the response
            return {
                "response": response_content,
                "agent": response_agent,
                "confidence": confidence,
                "entities": entities,
                "tools_used": tools_used
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "response": "I encountered an issue while processing your request. Please try again.",
                "agent": "error",
                "confidence": 0.0,
                "error": str(e)
            }