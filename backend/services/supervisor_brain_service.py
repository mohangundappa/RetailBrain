"""
Supervisor-based Brain Service for Staples Brain.

This service implements the orchestration logic using LangGraph Supervisors
for agent coordination and state management.
"""
import logging
import time
import json
import uuid
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from backend.config.config import Config
from backend.agents.framework.langgraph.langgraph_agent import LangGraphAgent
from backend.agents.framework.langgraph.langgraph_factory import LangGraphAgentFactory
from backend.agents.framework.langgraph.langgraph_supervisor_factory import LangGraphSupervisorFactory

logger = logging.getLogger(__name__)


class SupervisorBrainService:
    """
    Supervisor-based Brain Service for Staples Brain.
    
    This service manages the orchestration of agents using LangGraph Supervisors
    with database-driven configuration. It supports:
    - Database-driven supervisor configurations
    - Conversation state management
    - Multi-agent workflows with complex routing
    - Conditional graph execution
    """
    
    def __init__(
        self, 
        db_session: AsyncSession,
        config: Optional[Config] = None,
        memory_service: Optional[Any] = None,
        agent_factory: Optional[LangGraphAgentFactory] = None,
        supervisor_factory: Optional[LangGraphSupervisorFactory] = None
    ):
        """
        Initialize the Supervisor Brain Service.
        
        Args:
            db_session: Database session
            config: Application configuration
            memory_service: Optional memory service for persistence
            agent_factory: Factory for creating agents from database
            supervisor_factory: Factory for creating supervisors from database
        """
        self.db_session = db_session
        self.config = config or Config()
        self.memory_service = memory_service
        self.agent_factory = agent_factory
        self.supervisor_factory = supervisor_factory
        
        # LLM for orchestration tasks
        self.llm = ChatOpenAI(
            model="gpt-4o",  # Default to the most capable model
            temperature=0.2  # Lower temperature for more predictable orchestration
        )
        
        # Conversation state management
        self.conversation_states: Dict[str, Dict[str, Any]] = {}
        
        # Agent registry - populated during initialization
        self.agents: Dict[str, LangGraphAgent] = {}
        
        # Supervisor registry
        self.supervisors: Dict[str, Dict[str, Any]] = {}
        
        # Active supervisor graph - set up in initialize()
        self.supervisor_id = None
        self.supervisor_graph = None
        
        logger.info("Initialized SupervisorBrainService")
    
    async def initialize(self) -> bool:
        """
        Initialize the brain service with agents and supervisor from the database.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Initialize agent factory if not provided
            if not self.agent_factory:
                self.agent_factory = LangGraphAgentFactory(self.db_session)
                logger.info("Created LangGraphAgentFactory")
            
            # Initialize supervisor factory if not provided
            if not self.supervisor_factory:
                self.supervisor_factory = LangGraphSupervisorFactory(self.db_session)
                logger.info("Created LangGraphSupervisorFactory")
            
            # Load agents from database
            agents = await self.agent_factory.load_all_active_agents()
            agent_count = len(agents)
            logger.info(f"Loaded {agent_count} agents from database")
            
            # Register agents
            for agent in agents:
                self.agents[agent.id] = agent
                logger.info(f"Registered agent: {agent.name} (ID: {agent.id})")
            
            # Load supervisors from database
            supervisors = await self.supervisor_factory.list_active_supervisors()
            supervisor_count = len(supervisors)
            logger.info(f"Found {supervisor_count} active supervisors")
            
            if supervisor_count > 0:
                # Store supervisor configs
                for supervisor in supervisors:
                    self.supervisors[supervisor["id"]] = supervisor
                
                # Use the first active supervisor
                self.supervisor_id = supervisors[0]["id"]
                logger.info(f"Using supervisor: {supervisors[0]['name']} (ID: {self.supervisor_id})")
                
                # Create the supervisor graph
                self.supervisor_graph = await self.supervisor_factory.create_supervisor_graph(
                    self.supervisor_id,
                    self.agents
                )
                
                if not self.supervisor_graph:
                    logger.error(f"Failed to create supervisor graph for {self.supervisor_id}")
                    return False
                
                logger.info(f"Created supervisor graph for {supervisors[0]['name']}")
            else:
                logger.warning("No active supervisors found. Will fallback to default routing.")
                # Create a fallback graph using default configuration
                await self._create_fallback_graph()
            
            # Verify essential agents
            has_general_agent = any("general conversation" in agent.name.lower() for agent in self.agents.values())
            has_guardrails_agent = any("guardrails" in agent.name.lower() for agent in self.agents.values())
            
            if not has_general_agent:
                logger.warning("General Conversation Agent not found in loaded agents")
            if not has_guardrails_agent:
                logger.warning("Guardrails Agent not found in loaded agents")
            
            logger.info("Supervisor Brain Service initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Error initializing supervisor brain service: {str(e)}", exc_info=True)
            return False
    
    async def _create_fallback_graph(self) -> None:
        """
        Create a fallback graph when no supervisor configurations are available.
        This implements a simple router -> agent -> guardrails flow similar to the 
        original graph_brain_service.
        """
        # Initialize StateGraph with LangGraph 0.3.x requirements
        from typing import Dict as DictType
        
        # For LangGraph 0.3.29, pass the type as the first arg
        builder = StateGraph(DictType)  # State is a dictionary
        
        # Add nodes to the graph
        
        # 1. Router node: Determines which agent should handle the request
        builder.add_node("router", self._route_request)
        
        # 2. Agent executor node: Executes the selected agent
        builder.add_node("agent_executor", self._execute_agent)
        
        # 3. Post-processor node: Applies guardrails and finalizes response
        builder.add_node("post_processor", self._apply_post_processing)
        
        # Define the edges between nodes
        
        # Start with routing
        builder.set_entry_point("router")
        
        # Route to agent execution
        builder.add_edge("router", "agent_executor")
        
        # Apply post-processing after agent execution
        builder.add_edge("agent_executor", "post_processor")
        
        # End after post-processing
        builder.add_edge("post_processor", END)
        
        # Compile the graph
        self.supervisor_graph = builder.compile()
        logger.info("Created fallback LangGraph workflow graph with 3 nodes")
    
    async def _route_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a request to the appropriate agent.
        Used in the fallback graph when no supervisor is configured.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with selected agent
        """
        start_time = time.time()
        user_input = state["user_input"]
        session_id = state["session_id"]
        context = state.get("context", {})
        
        # Track execution
        state["trace"].append({"step": "router", "timestamp": start_time})
        
        # Get conversation history if available
        conversation_history = []
        if self.memory_service and session_id:
            try:
                conversation_history = await self.memory_service.get_conversation_history(session_id)
            except Exception as e:
                logger.error(f"Error retrieving conversation history: {str(e)}")
        
        # First, try pattern matching
        for agent_id, agent in self.agents.items():
            # Check if agent has patterns defined
            if hasattr(agent, 'patterns') and agent.patterns:
                for pattern in agent.patterns:
                    if pattern.lower() in user_input.lower():
                        # Pattern match found
                        logger.info(f"Pattern match found: routing to {agent.name}")
                        state["selected_agent"] = agent
                        state["current_agent_id"] = agent_id
                        state["confidence"] = 1.0
                        state["pattern_match"] = pattern
                        return state
        
        # If no pattern match, use LLM to select agent
        try:
            # Format available agents for prompt
            agent_descriptions = "\n".join([
                f"- {a.name}: {a.description}" for a in self.agents.values()
            ])
            
            # Create agent selection prompt
            agent_selection_prompt = PromptTemplate.from_template("""
            You are an expert agent router for Staples customer service.
            Your job is to analyze the user's query and determine which specialized agent is best equipped to handle it.
            
            Available specialized agents:
            {agent_descriptions}
            
            User query: {user_input}
            
            Select the most appropriate agent based on the nature of the user's query.
            The response should be a JSON object with the following fields:
            - agent_name: The exact name of the selected agent
            - confidence: A number between 0.0 and 1.0 indicating your confidence in this selection
            - reasoning: A brief explanation of why you selected this agent
            
            IMPORTANT: Only include agents from the list provided. Do not invent new agents.
            If no specialized agent is appropriate, select "General Conversation Agent".
            
            Response (in JSON format):
            """)
            
            # Create the chain
            selection_chain = agent_selection_prompt | self.llm | StrOutputParser()
            
            # Execute the chain
            result = await selection_chain.ainvoke({
                "agent_descriptions": agent_descriptions,
                "user_input": user_input
            })
            
            # Parse result
            try:
                # Clean up JSON result
                result = result.strip()
                if result.startswith("```json"):
                    result = result[7:result.rfind("```")]
                elif result.startswith("```"):
                    result = result[3:result.rfind("```")]
                
                selection_data = json.loads(result)
                
                selected_agent_name = selection_data.get("agent_name", "")
                confidence = float(selection_data.get("confidence", 0.5))
                
                # Find the agent by name
                selected_agent = None
                selected_agent_id = None
                
                for agent_id, agent in self.agents.items():
                    if agent.name.lower() == selected_agent_name.lower():
                        selected_agent = agent
                        selected_agent_id = agent_id
                        break
                
                # If agent not found by exact name, try partial match
                if not selected_agent:
                    for agent_id, agent in self.agents.items():
                        if selected_agent_name.lower() in agent.name.lower():
                            selected_agent = agent
                            selected_agent_id = agent_id
                            break
                
                # Fallback to general agent if still not found
                if not selected_agent:
                    general_agent = self._get_general_agent()
                    if general_agent:
                        selected_agent = general_agent
                        # Find the ID for the general agent
                        for agent_id, agent in self.agents.items():
                            if agent == general_agent:
                                selected_agent_id = agent_id
                                break
                    else:
                        # Use the first agent as last resort
                        if self.agents:
                            first_agent_id = next(iter(self.agents.keys()))
                            selected_agent = self.agents[first_agent_id]
                            selected_agent_id = first_agent_id
                
                # Update state with selected agent
                if selected_agent:
                    state["selected_agent"] = selected_agent
                    state["current_agent_id"] = selected_agent_id
                    state["confidence"] = confidence
                    state["selection_method"] = "llm"
                    state["selection_reasoning"] = selection_data.get("reasoning", "")
                    
                    logger.info(f"LLM selected agent: {selected_agent.name} with confidence {confidence}")
                    return state
                else:
                    logger.error("No agent could be selected")
                    raise ValueError("No agent available for selection")
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing agent selection result: {str(e)}")
                logger.debug(f"Problematic result: {result}")
                raise
                
        except Exception as e:
            logger.error(f"Error selecting agent: {str(e)}", exc_info=True)
            
            # Fallback to general agent
            general_agent = self._get_general_agent()
            if general_agent:
                general_agent_id = None
                for agent_id, agent in self.agents.items():
                    if agent == general_agent:
                        general_agent_id = agent_id
                        break
                
                state["selected_agent"] = general_agent
                state["current_agent_id"] = general_agent_id
                state["confidence"] = 0.5
                state["selection_method"] = "fallback"
                return state
            
            # If still no general agent, use the first available agent
            if self.agents:
                first_agent_id = next(iter(self.agents.keys()))
                state["selected_agent"] = self.agents[first_agent_id]
                state["current_agent_id"] = first_agent_id
                state["confidence"] = 0.3
                state["selection_method"] = "last_resort"
                return state
        
        # This should never happen, but just in case
        raise ValueError("No agent available in the system")
    
    async def _execute_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the selected agent.
        Used in the fallback graph when no supervisor is configured.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with agent response
        """
        start_time = time.time()
        selected_agent = state.get("selected_agent")
        user_input = state.get("user_input", "")
        context = state.get("context", {})
        
        # Track execution
        state["trace"].append({
            "step": "agent_execution",
            "agent": selected_agent.name if selected_agent else "unknown",
            "timestamp": start_time
        })
        
        if not selected_agent:
            logger.error("No agent selected for execution")
            state["response"] = "I'm sorry, I'm having trouble processing your request. Please try again."
            state["success"] = False
            state["error"] = "No agent selected"
            return state
        
        try:
            # Process the message with the selected agent
            result = await selected_agent.async_process(user_input, context)
            
            # Update state with the result
            state["response"] = result.get("response", "")
            state["success"] = True
            
            # Add any additional data from the agent response
            if "additional_data" in result:
                state["additional_data"] = result["additional_data"]
            
            # Calculate execution time
            execution_time = time.time() - start_time
            state["execution_time"] = execution_time
            
            logger.info(f"Agent {selected_agent.name} executed successfully in {execution_time:.2f}s")
            return state
            
        except Exception as e:
            logger.error(f"Error executing agent {selected_agent.name}: {str(e)}", exc_info=True)
            
            # Set error response
            state["response"] = "I apologize, but I encountered an error while processing your request. Please try again."
            state["success"] = False
            state["error"] = str(e)
            
            return state
    
    async def _apply_post_processing(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply post-processing to the agent response.
        Used in the fallback graph when no supervisor is configured.
        
        Args:
            state: Current workflow state
            
        Returns:
            Finalized workflow state
        """
        start_time = time.time()
        response = state.get("response", "")
        
        # Track execution
        state["trace"].append({
            "step": "router_complete", 
            "timestamp": start_time
        })
        
        # If no response, set a default
        if not response:
            logger.warning("Empty response after agent execution")
            state["response"] = "I apologize, but I couldn't generate a proper response. Please try again."
            return state
        
        # Apply guardrails via the guardrails agent if available
        guardrails_agent = self._get_guardrails_agent()
        if guardrails_agent and response:
            try:
                guardrails_context = {
                    "original_response": response,
                    "agent_name": state.get("selected_agent").name if state.get("selected_agent") else "Unknown",
                    "confidence": state.get("confidence", 0),
                    "user_input": state.get("user_input", "")
                }
                
                guardrails_result = await guardrails_agent.async_process(
                    response, 
                    guardrails_context
                )
                
                # Check if the response was modified
                guardrails_response = guardrails_result.get("response", "")
                if guardrails_response and guardrails_response != response:
                    logger.info("Guardrails modified the response")
                    state["original_response"] = response
                    state["response"] = guardrails_response
                    state["guardrails_applied"] = True
                    if "policy_violations" in guardrails_result:
                        state["policy_violations"] = guardrails_result["policy_violations"]
            
            except Exception as e:
                logger.error(f"Error applying guardrails: {str(e)}", exc_info=True)
                # Continue with the original response if guardrails fail
        
        # Mark processing as complete
        state["completed"] = True
        state["completion_time"] = time.time()
        
        # Calculate total processing time
        if "processing_start" in state:
            state["total_processing_time"] = time.time() - state["processing_start"]
        
        return state
    
    def _get_general_agent(self) -> Optional[LangGraphAgent]:
        """
        Get the general conversation agent.
        
        Returns:
            General conversation agent or None if not found
        """
        for agent in self.agents.values():
            if "general conversation" in agent.name.lower():
                return agent
        return None
    
    def _get_guardrails_agent(self) -> Optional[LangGraphAgent]:
        """
        Get the guardrails agent.
        
        Returns:
            Guardrails agent or None if not found
        """
        for agent in self.agents.values():
            if "guardrails" in agent.name.lower():
                return agent
        return None
    
    async def _get_or_create_conversation_state(self, session_id: str) -> Dict[str, Any]:
        """
        Get or create a conversation state for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Conversation state dictionary
        """
        # Check if we have a state for this session
        if session_id in self.conversation_states:
            return self.conversation_states[session_id]
        
        # Create a new state
        state = {
            "session_id": session_id,
            "messages": [],
            "context": {"session_id": session_id},
            "agents": self.agents,
            "trace": [],
            "created_at": time.time()
        }
        
        # Add agent patterns if available
        agent_patterns = {}
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'patterns') and agent.patterns:
                agent_patterns[agent_id] = agent.patterns
        
        if agent_patterns:
            state["agent_patterns"] = agent_patterns
        
        # Store the state
        self.conversation_states[session_id] = state
        
        return state
    
    async def _persist_conversation_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """
        Persist the conversation state for a session.
        
        Args:
            session_id: Session identifier
            state: Updated state to persist
        """
        # Update the in-memory state
        self.conversation_states[session_id] = state
        
        # If we have a memory service, store the conversation
        if self.memory_service and session_id:
            try:
                # Store the last message if there are messages
                if state.get("messages") and len(state["messages"]) > 0:
                    last_message = state["messages"][-1]
                    
                    # Store user messages
                    if last_message.get("role") == "user":
                        await self.memory_service.store_message(
                            session_id=session_id,
                            role="user",
                            content=last_message.get("content", ""),
                            metadata={}
                        )
                    
                    # Store assistant messages
                    elif last_message.get("role") == "assistant":
                        metadata = {
                            "agent_id": state.get("current_agent_id", ""),
                            "agent_name": last_message.get("agent_name", ""),
                            "confidence": state.get("confidence", 0),
                            "selection_method": state.get("selection_method", "")
                        }
                        
                        await self.memory_service.store_message(
                            session_id=session_id,
                            role="assistant",
                            content=last_message.get("content", ""),
                            metadata=metadata
                        )
            
            except Exception as e:
                logger.error(f"Error persisting conversation state: {str(e)}", exc_info=True)
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message using the LangGraph supervisor.
        
        Args:
            message: User message
            session_id: Session ID
            context: Optional context
            
        Returns:
            Response dictionary
        """
        if not message:
            return {
                "success": False,
                "error": "Empty message",
                "response": "I couldn't understand your message. Please try again."
            }
            
        if not self.supervisor_graph:
            await self.initialize()
            if not self.supervisor_graph:
                return {
                    "success": False,
                    "error": "Supervisor graph not initialized",
                    "response": "I'm sorry, but I'm not ready to process your request yet."
                }
        
        start_time = time.time()
        
        try:
            # Get or create conversation state
            state = await self._get_or_create_conversation_state(session_id)
            
            # Update the state with the new message and context
            state["user_input"] = message
            state["processing_start"] = start_time
            
            # Add the user message to the messages list
            state["messages"].append({
                "role": "user",
                "content": message
            })
            
            # Update context
            if context:
                state["context"] = {
                    **state.get("context", {}),
                    **context
                }
            
            # Make sure agents are in the state for supervisor
            state["agents"] = self.agents
            
            # Execute the supervisor graph
            result = await self.supervisor_graph.ainvoke(state)
            
            # Persist the updated state
            await self._persist_conversation_state(session_id, result)
            
            # Format the response
            response = {
                "session_id": session_id,
                "response": result.get("response", ""),
                "success": result.get("success", True),
                "agent": {
                    "id": result.get("current_agent_id", ""),
                    "name": result.get("selected_agent").name if result.get("selected_agent") else "",
                    "confidence": result.get("confidence", 0)
                },
                "metadata": {
                    "processing_time": time.time() - start_time,
                    "guardrails_applied": result.get("guardrails_applied", False),
                    "selection_method": result.get("selection_method", ""),
                    "routing_explanation": result.get("routing_explanation", "")
                }
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an unexpected error. Please try again.",
                "session_id": session_id
            }