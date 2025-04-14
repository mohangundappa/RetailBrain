"""
Graph-based Brain Service for Staples Brain.

This service implements the core orchestration logic using LangGraph for agent coordination
and state management.
"""
import logging
import time
import json
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

logger = logging.getLogger(__name__)


class GraphBrainService:
    """
    Graph-based Brain Service for Staples Brain.
    
    This service manages the orchestration of agents using LangGraph's graph-based
    execution model. It supports:
    - Database-driven agent configurations
    - Conversation state management
    - Multi-agent workflows
    - LangGraph-based agent execution
    """
    
    def __init__(
        self, 
        db_session: AsyncSession,
        config: Optional[Config] = None,
        memory_service: Optional[Any] = None,
        agent_factory: Optional[LangGraphAgentFactory] = None
    ):
        """
        Initialize the Graph Brain Service.
        
        Args:
            db_session: Database session
            config: Application configuration
            memory_service: Optional memory service for persistence
            agent_factory: Factory for creating agents from database
        """
        self.db_session = db_session
        self.config = config or Config()
        self.memory_service = memory_service
        self.agent_factory = agent_factory
        
        # LLM for orchestration tasks
        self.llm = ChatOpenAI(
            model="gpt-4o",  # Default to the most capable model
            temperature=0.2  # Lower temperature for more predictable orchestration
        )
        
        # Conversation state management
        self.conversation_states: Dict[str, Dict[str, Any]] = {}
        
        # Agent registry - populated during initialization
        self.agents: Dict[str, LangGraphAgent] = {}
        
        # Graph definition - set up in initialize()
        self.graph = None
        
        logger.info("Initialized GraphBrainService")
    
    async def initialize(self) -> bool:
        """
        Initialize the brain service with agents from the database.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Initialize agent factory if not provided
            if not self.agent_factory:
                self.agent_factory = LangGraphAgentFactory(self.db_session)
                logger.info("Created LangGraphAgentFactory")
            
            # Load agents from database
            agents = await self.agent_factory.load_all_active_agents()
            agent_count = len(agents)
            logger.info(f"Loaded {agent_count} agents from database")
            
            # Register agents
            for agent in agents:
                self.agents[agent.id] = agent
                logger.info(f"Registered agent: {agent.name} (ID: {agent.id})")
            
            # Create the agent workflow graph
            self.create_workflow_graph()
            
            # Verify special agents
            has_general_agent = any("general conversation" in agent.name.lower() for agent in self.agents.values())
            has_guardrails_agent = any("guardrails" in agent.name.lower() for agent in self.agents.values())
            
            if not has_general_agent:
                logger.warning("General Conversation Agent not found in loaded agents")
            if not has_guardrails_agent:
                logger.warning("Guardrails Agent not found in loaded agents")
            
            logger.info("Graph Brain Service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing graph brain service: {str(e)}", exc_info=True)
            return False
    
    def create_workflow_graph(self):
        """
        Create the LangGraph workflow graph for agent orchestration.
        This defines the execution flow between agents.
        """
        # Initialize StateGraph with LangGraph 0.3.x requirements
        from typing import Dict as DictType
        
        # For LangGraph 0.3.29, pass the type as the first arg
        builder = StateGraph(DictType)  # State is a dictionary
        
        # We'll still maintain documentation of the expected state fields here:
        # - messages: Conversation messages
        # - current_agent_id: Currently active agent
        # - context: Additional context data
        # - session_id: Session identifier
        # - user_input: Original user input
        # - selected_agent: Agent selected for processing
        # - confidence: Confidence in agent selection
        # - processing_start: Processing start timestamp
        # - response: Final response
        # - trace: Execution trace for observability
        # - completed: Whether processing is complete
        
        # Define the expected state keys for documentation
        # This state schema represents the conversation state that flows through the graph
        # - messages: Conversation messages
        # - current_agent_id: Currently active agent
        # - context: Additional context data
        # - session_id: Session identifier
        # - user_input: Original user input
        # - selected_agent: Agent selected for processing
        # - confidence: Confidence in agent selection
        # - processing_start: Processing start timestamp
        # - response: Final response
        # - trace: Execution trace for observability
        # - completed: Whether processing is complete
        
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
        self.graph = builder.compile()
        logger.info("Created LangGraph workflow graph with 3 nodes")
    
    async def _route_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a request to the appropriate agent.
        
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
                history = await self.memory_service.get_conversation_history(session_id)
                if history:
                    conversation_history = history
            except Exception as e:
                logger.error(f"Error retrieving conversation history: {str(e)}")
        
        # Check for conversation continuity with previous agent
        prev_agent_id = state.get("current_agent_id")
        if prev_agent_id and prev_agent_id in self.agents:
            # If we have a previous agent, check if we should continue with it
            continuity_check = await self._check_conversation_continuity(
                user_input, 
                prev_agent_id,
                conversation_history
            )
            
            if continuity_check["continue"] and continuity_check["confidence"] > 0.6:
                state["selected_agent"] = self.agents[prev_agent_id]
                state["confidence"] = continuity_check["confidence"]
                state["trace"].append({
                    "step": "agent_selection",
                    "method": "continuity",
                    "selected": prev_agent_id,
                    "confidence": continuity_check["confidence"]
                })
                return state
        
        # Perform agent selection using intent matching and semantic similarity
        selected_agent, confidence = await self._select_agent(
            user_input, 
            session_id, 
            context,
            conversation_history
        )
        
        state["selected_agent"] = selected_agent
        state["confidence"] = confidence
        
        if selected_agent:
            state["current_agent_id"] = selected_agent.id
            state["trace"].append({
                "step": "agent_selection",
                "method": "intent_matching",
                "selected": selected_agent.id,
                "confidence": confidence
            })
        else:
            # If no agent was selected, try to use a general conversation agent
            general_agent = self._get_general_agent()
            if general_agent:
                state["selected_agent"] = general_agent
                state["current_agent_id"] = general_agent.id
                state["confidence"] = 0.6  # Default confidence for fallback
                state["trace"].append({
                    "step": "agent_selection",
                    "method": "fallback",
                    "selected": general_agent.id,
                    "confidence": 0.6
                })
            else:
                logger.error("No suitable agent found and no general fallback available")
                state["trace"].append({
                    "step": "agent_selection",
                    "method": "failed",
                    "error": "No suitable agent found"
                })
        
        state["trace"].append({
            "step": "router_complete", 
            "duration": time.time() - start_time
        })
        
        return state
    
    async def _execute_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the selected agent against the user input.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with agent response
        """
        start_time = time.time()
        selected_agent = state["selected_agent"]
        user_input = state["user_input"]
        session_id = state["session_id"]
        context = state.get("context", {})
        
        state["trace"].append({"step": "agent_executor", "timestamp": start_time})
        
        if not selected_agent:
            logger.error("No agent selected for execution")
            state["response"] = {
                "message": "I'm sorry, I couldn't find the right specialist to help with your request.",
                "success": False,
                "error": "No agent selected"
            }
            state["trace"].append({
                "step": "agent_execution",
                "status": "failed",
                "error": "No agent selected"
            })
            return state
        
        try:
            # Execute the agent with the user input
            response = await selected_agent.process_message(
                message=user_input,
                session_id=session_id,
                context=context
            )
            
            # Update state with the response
            state["response"] = response
            state["trace"].append({
                "step": "agent_execution",
                "status": "success",
                "agent_id": selected_agent.id,
                "agent_name": selected_agent.name,
                "duration": time.time() - start_time
            })
            
        except Exception as e:
            logger.error(f"Error executing agent {selected_agent.name}: {str(e)}", exc_info=True)
            state["response"] = {
                "message": "I encountered an error while processing your request.",
                "success": False,
                "error": str(e)
            }
            state["trace"].append({
                "step": "agent_execution",
                "status": "failed",
                "agent_id": selected_agent.id,
                "agent_name": selected_agent.name,
                "error": str(e),
                "duration": time.time() - start_time
            })
        
        return state
    
    async def _apply_post_processing(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply post-processing to the agent response, such as guardrails.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with post-processed response
        """
        start_time = time.time()
        response = state.get("response", {})
        
        state["trace"].append({"step": "post_processor", "timestamp": start_time})
        
        # Get the guardrails agent if available
        guardrails_agent = self._get_guardrails_agent()
        
        if guardrails_agent and response:
            try:
                # Apply guardrails to the response
                message_content = response.get("message", "")
                if message_content:
                    guardrails_context = {
                        "original_response": message_content,
                        "session_id": state["session_id"],
                        "user_input": state["user_input"],
                        "agent_id": state.get("current_agent_id"),
                        **state.get("context", {})
                    }
                    
                    # Process through guardrails
                    guardrails_result = await guardrails_agent.process_message(
                        message=message_content,
                        session_id=state["session_id"],
                        context=guardrails_context
                    )
                    
                    # Update the response with guardrails output
                    if guardrails_result and "message" in guardrails_result:
                        response["message"] = guardrails_result["message"]
                        state["response"] = response
                        state["trace"].append({
                            "step": "guardrails",
                            "status": "applied",
                            "modified": guardrails_result.get("modified", False)
                        })
            except Exception as e:
                logger.error(f"Error applying guardrails: {str(e)}", exc_info=True)
                state["trace"].append({
                    "step": "guardrails",
                    "status": "failed",
                    "error": str(e)
                })
                # Continue with the original response
        
        # Mark processing as complete
        state["completed"] = True
        state["trace"].append({
            "step": "post_processing_complete",
            "duration": time.time() - start_time
        })
        
        return state
    
    async def _check_conversation_continuity(
        self, 
        user_input: str,
        prev_agent_id: str,
        conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Determine if the current message continues the conversation with the previous agent.
        
        Args:
            user_input: Current user message
            prev_agent_id: ID of the previous agent
            conversation_history: Previous conversation messages
            
        Returns:
            Dict with continue (bool) and confidence (float)
        """
        # If no previous agent or no conversation history, can't continue
        if not prev_agent_id or not conversation_history:
            return {"continue": False, "confidence": 0.0}
        
        try:
            # Get the previous agent name
            prev_agent_name = "Unknown Agent"
            if prev_agent_id in self.agents:
                prev_agent_name = self.agents[prev_agent_id].name
            
            # Format recent conversation history
            formatted_history = ""
            for item in conversation_history[-4:]:  # Use last 4 exchanges
                role = item.get("role", "")
                content = item.get("content", "")
                if role and content:
                    formatted_history += f"{role.upper()}: {content}\n"
            
            # Define prompt for continuity detection
            continuity_prompt = PromptTemplate.from_template("""
            Consider this conversation history:
            
            {history}
            
            Current user message: {message}
            
            The previous message was handled by the agent: {agent_name}
            
            Determine if the current message is continuing the same conversation topic or intent that the previous agent was handling.
            Output a JSON object with:
            - continue: boolean (true if the conversation is continuing the same topic/intent, false if it's a new topic)
            - confidence: number between 0.0 and 1.0
            - reasoning: brief explanation of your decision
            
            JSON Output:
            """)
            
            # Create and run the continuity detection chain
            continuity_chain = continuity_prompt | self.llm | StrOutputParser()
            
            result = await continuity_chain.ainvoke({
                "history": formatted_history,
                "message": user_input,
                "agent_name": prev_agent_name
            })
            
            # Parse the result
            continuity_data = json.loads(result)
            
            return {
                "continue": continuity_data.get("continue", False),
                "confidence": float(continuity_data.get("confidence", 0.0)),
                "reasoning": continuity_data.get("reasoning", "")
            }
        except Exception as e:
            logger.error(f"Error checking conversation continuity: {str(e)}", exc_info=True)
            return {"continue": False, "confidence": 0.0}
    
    async def _select_agent(
        self, 
        query: str, 
        session_id: str,
        context: Dict[str, Any],
        conversation_history: List[Dict[str, Any]] = None
    ) -> Tuple[Optional[LangGraphAgent], float]:
        """
        Select the best agent for handling a query.
        
        Args:
            query: User query
            session_id: Session identifier
            context: Additional context information
            conversation_history: Previous conversation messages
            
        Returns:
            Tuple of (selected agent, confidence)
        """
        if not self.agents:
            logger.warning("No agents available for selection")
            return None, 0.0
        
        # Format agent descriptions for the selection prompt
        agent_descriptions = "\n".join([
            f"- {agent.name}: {agent.description}" 
            for agent in self.agents.values()
        ])
        
        # Define the agent selection prompt
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
        
        try:
            # Create and run the agent selection chain
            agent_selection_chain = agent_selection_prompt | self.llm | StrOutputParser()
            
            result = await agent_selection_chain.ainvoke({
                "message": query,
                "agent_descriptions": agent_descriptions
            })
            
            # Parse the result with proper error handling
            try:
                # Try to clean up the result to ensure valid JSON
                result = result.strip()
                # If result starts with backticks (e.g., ```json), clean it up
                if result.startswith('```'):
                    # Find the end of the code block
                    end_backticks = result.rfind('```')
                    if end_backticks > 3:  # At least one character between start and end
                        # Extract only the JSON content inside the code block
                        start_content = result.find('\n', 3)  # Skip first line with ```json
                        if start_content != -1 and start_content < end_backticks:
                            result = result[start_content:end_backticks].strip()
                        else:
                            # Fallback: just remove the backticks
                            result = result.replace('```', '').strip()
                
                # Parse the JSON
                scores = json.loads(result)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing agent selection result: {str(e)}")
                logger.debug(f"Raw result from LLM: {result}")
                # Fallback to default scores
                scores = {
                    "General Conversation Agent": 0.8,
                    "Package Tracking Agent": 0.2,
                    "Reset Password Agent": 0.2,
                    "Store Locator Agent": 0.2,
                    "Product Information Agent": 0.2,
                    "Returns Processing Agent": 0.2
                }
            
            # Find the best scoring agent
            best_agent = None
            best_score = 0.0
            
            for agent_name, score in scores.items():
                try:
                    score_float = float(score)
                    # Find matching agent by name
                    matching_agent = next(
                        (a for a in self.agents.values() if a.name == agent_name), 
                        None
                    )
                    
                    if matching_agent and score_float > best_score:
                        best_agent = matching_agent
                        best_score = score_float
                except (ValueError, TypeError):
                    continue
            
            # Apply a threshold for agent selection
            if best_score >= 0.6:
                return best_agent, best_score
            else:
                logger.info(f"No agent passed confidence threshold for query: {query}")
                return None, best_score
                
        except Exception as e:
            logger.error(f"Error selecting agent: {str(e)}", exc_info=True)
            return None, 0.0
    
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
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message using the LangGraph workflow.
        
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
            
        if not self.graph:
            success = await self.initialize()
            if not success:
                return {
                    "success": False,
                    "error": "Initialization failed",
                    "response": "I'm having trouble processing your request. Please try again later."
                }
        
        try:
            # Initialize workflow state
            initial_state = {
                "messages": [],
                "current_agent_id": None,
                "context": context or {},
                "session_id": session_id,
                "user_input": message,
                "selected_agent": None,
                "confidence": 0.0,
                "processing_start": time.time(),
                "response": None,
                "trace": [],
                "completed": False
            }
            
            # Get any existing state for this session
            existing_state = self.conversation_states.get(session_id)
            if existing_state:
                # Transfer continuous values from existing state
                initial_state["current_agent_id"] = existing_state.get("current_agent_id")
                if "messages" in existing_state and existing_state["messages"]:
                    initial_state["messages"] = existing_state["messages"]
            
            # Run the workflow graph
            final_state = await self.graph.ainvoke(initial_state)
            
            # Save state for future interactions
            self.conversation_states[session_id] = final_state
            
            # Generate response from state
            response = final_state.get("response", {})
            message_content = response.get("message", "I'm not sure how to help with that.")
            
            # Update conversation history
            if self.memory_service:
                try:
                    await self.memory_service.add_message(
                        session_id=session_id,
                        role="user",
                        content=message
                    )
                    
                    await self.memory_service.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=message_content,
                        metadata={
                            "agent_id": final_state.get("current_agent_id"),
                            "confidence": final_state.get("confidence", 0.0)
                        }
                    )
                except Exception as e:
                    logger.error(f"Error updating memory: {str(e)}", exc_info=True)
            
            # Prepare final response object
            selected_agent = final_state.get("selected_agent")
            result = {
                "success": True,
                "response": message_content,
                "agent": selected_agent.name if selected_agent else "unknown",
                "agent_id": final_state.get("current_agent_id", ""),
                "confidence": final_state.get("confidence", 0.0),
                "processing_time": time.time() - final_state.get("processing_start", time.time()),
                "trace_id": session_id  # Use session ID as trace ID for observability
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "response": "I encountered an unexpected error. Please try again."
            }
    
    # Alias for API compatibility with existing OptimizedBrainService
    async def process_request(
        self,
        message: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user request (alias to process_message).
        This method is called by the ChatService and ensures API compatibility.
        
        Args:
            message: User message
            session_id: Session ID
            context: Optional context
            
        Returns:
            Response dictionary
        """
        return await self.process_message(message, session_id, context)
    
    async def list_agents(self) -> Dict[str, Any]:
        """
        Get a list of available agents.
        
        Returns:
            Dictionary containing agent information
        """
        agent_list = []
        try:
            # Import agent type mapping
            from backend.config.agent_constants import AGENT_TYPE_MAPPING, AGENT_TYPE_BUILT_IN, AGENT_TYPE_SMALL_TALK
            
            for agent_id, agent in self.agents.items():
                # Get the agent type and ensure it's using our new type system
                agent_type = getattr(agent, "agent_type", "unknown")
                
                # Extract relevant agent information
                agent_detail = {
                    "id": agent_id,
                    "name": agent.name,
                    "description": getattr(agent, "description", ""),
                    "type": agent_type,  # Already updated in database
                    "version": getattr(agent, "version", 1),
                    "status": getattr(agent, "status", "active"),
                    "created_at": getattr(agent, "created_at", datetime.now().isoformat()),
                    "db_driven": True,
                    "loaded": True,
                    "is_system": agent_type == AGENT_TYPE_BUILT_IN or agent_type == AGENT_TYPE_SMALL_TALK
                }
                agent_list.append(agent_detail)
            
            return {
                "success": True,
                "agents": agent_list,
                "count": len(agent_list)
            }
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to list agents: {str(e)}",
                "agents": [],
                "count": 0
            }
    
    async def get_system_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get system statistics.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary containing system statistics
        """
        try:
            # Get basic information about the system
            stats = {
                "agent_count": len(self.agents),
                "agents": [agent.name for agent in self.agents.values()],
                "general_agent": bool(self._get_general_agent()),
                "guardrails_agent": bool(self._get_guardrails_agent()),
                "graph_nodes": 3 if self.graph else 0,  # Router, Executor, PostProcessor
                "days_analyzed": days,
                "timestamp": datetime.now().isoformat()
            }
            
            # If connected to a telemetry service, we could get more detailed stats here
            # For now, return basic system information
            
            return {
                "success": True,
                "data": stats
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to get system statistics: {str(e)}",
                "data": {}
            }