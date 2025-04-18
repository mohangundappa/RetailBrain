"""
LangGraph Supervisor Factory for Staples Brain.

This module provides a factory class for creating LangGraph supervisors
from database configurations.
"""
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Union, Tuple, TypeVar, Type

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from backend.database.agent_schema import (
    SupervisorConfiguration, 
    SupervisorAgentMapping,
    AgentDefinition
)
from backend.agents.framework.langgraph.langgraph_agent import LangGraphAgent

logger = logging.getLogger(__name__)


class LangGraphSupervisorFactory:
    """
    Factory class for creating LangGraph supervisors from database configurations.
    
    This class loads supervisor configurations from the database and constructs
    LangGraph state graphs that orchestrate agent interactions based on those
    configurations.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the supervisor factory.
        
        Args:
            db_session: Database session for queries
        """
        self.db_session = db_session
        logger.info("Initialized LangGraphSupervisorFactory")
    
    async def list_active_supervisors(self) -> List[Dict[str, Any]]:
        """
        Get a list of all active supervisor configurations.
        
        Returns:
            List of supervisor configuration dictionaries
        """
        try:
            # Build query for active supervisors
            query = sa.select(SupervisorConfiguration).where(
                SupervisorConfiguration.status == "active"
            ).order_by(
                SupervisorConfiguration.created_at.desc()
            )
            
            # Execute query
            result = await self.db_session.execute(query)
            supervisors = result.scalars().all()
            
            # Convert to dictionaries
            return [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "description": s.description,
                    "routing_strategy": s.routing_strategy,
                    "model_name": s.model_name,
                    "temperature": s.temperature,
                    "entry_node": s.entry_node or "router",
                    "pattern_prioritization": s.pattern_prioritization,
                    "status": s.status
                }
                for s in supervisors
            ]
            
        except Exception as e:
            logger.error(f"Error listing active supervisors: {str(e)}", exc_info=True)
            return []
    
    async def get_supervisor_with_mappings(
        self, 
        supervisor_id: Union[str, uuid.UUID]
    ) -> Optional[Dict[str, Any]]:
        """
        Get a supervisor configuration with agent mappings.
        
        Args:
            supervisor_id: ID of the supervisor
            
        Returns:
            Supervisor configuration dictionary or None if not found
        """
        try:
            # Convert string ID to UUID if necessary
            if isinstance(supervisor_id, str):
                supervisor_id = uuid.UUID(supervisor_id)
            
            # Build query
            query = sa.select(SupervisorConfiguration).where(
                SupervisorConfiguration.id == supervisor_id
            ).options(
                selectinload(SupervisorConfiguration.agent_mappings)
                .selectinload(SupervisorAgentMapping.agent)
            )
            
            # Execute query
            result = await self.db_session.execute(query)
            supervisor = result.scalars().first()
            
            if not supervisor:
                return None
            
            # Convert to dictionary
            supervisor_dict = {
                "id": str(supervisor.id),
                "name": supervisor.name,
                "description": supervisor.description,
                "routing_strategy": supervisor.routing_strategy,
                "model_name": supervisor.model_name,
                "temperature": supervisor.temperature,
                "routing_prompt": supervisor.routing_prompt,
                "nodes": supervisor.nodes or {},
                "edges": supervisor.edges or {},
                "edge_conditions": supervisor.edge_conditions or {},
                "entry_node": supervisor.entry_node or "router",
                "pattern_prioritization": supervisor.pattern_prioritization,
                "status": supervisor.status,
                "agent_mappings": []
            }
            
            # Add agent mappings
            for mapping in supervisor.agent_mappings:
                agent = mapping.agent
                mapping_dict = {
                    "id": str(mapping.id),
                    "node_id": mapping.node_id,
                    "execution_order": mapping.execution_order,
                    "config": mapping.config or {},
                    "agent": {
                        "id": str(agent.id),
                        "name": agent.name,
                        "description": agent.description,
                        "agent_type": agent.agent_type,
                        "version": agent.version,
                        "status": agent.status
                    }
                }
                supervisor_dict["agent_mappings"].append(mapping_dict)
            
            return supervisor_dict
            
        except Exception as e:
            logger.error(f"Error getting supervisor with mappings: {str(e)}", exc_info=True)
            return None
    
    async def create_supervisor_graph(
        self,
        supervisor_id: Union[str, uuid.UUID],
        agents: Dict[str, LangGraphAgent]
    ) -> Optional[Any]:
        """
        Create a LangGraph supervisor state graph from a database configuration.
        
        Args:
            supervisor_id: ID of the supervisor configuration
            agents: Dictionary of LangGraphAgent instances by ID
            
        Returns:
            Compiled LangGraph state graph or None if creation fails
        """
        try:
            # Get supervisor configuration with mappings
            supervisor = await self.get_supervisor_with_mappings(supervisor_id)
            
            if not supervisor:
                logger.error(f"Supervisor {supervisor_id} not found")
                return None
            
            # Create LLM for supervisor
            llm = ChatOpenAI(
                model=supervisor["model_name"],
                temperature=supervisor["temperature"]
            )
            
            # Initialize StateGraph with LangGraph 0.3.x requirements
            from typing import Dict as DictType
            
            # For LangGraph 0.3.29, pass the type as the first arg
            builder = StateGraph(DictType)  # State is a dictionary
            
            # Add nodes to the graph
            nodes = supervisor["nodes"]
            
            # If nodes is empty, create default nodes
            if not nodes:
                logger.warning(f"No nodes defined for supervisor {supervisor_id}, using defaults")
                nodes = {
                    "router": {
                        "type": "router",
                        "name": "Request Router",
                        "description": "Routes requests to appropriate agents"
                    },
                    "agent_executor": {
                        "type": "agent",
                        "name": "Agent Executor",
                        "description": "Executes the selected agent"
                    },
                    "guardrails": {
                        "type": "guardrails",
                        "name": "Guardrails",
                        "description": "Ensures responses meet policy requirements"
                    }
                }
            
            # Map node types to handler functions
            node_handlers = {
                "router": self._create_router_node,
                "agent": self._create_agent_node,
                "guardrails": self._create_guardrails_node,
                "memory_store": self._create_memory_node,
                "conditional": self._create_conditional_node
            }
            
            # Get agent mappings by node ID
            node_to_agents = {}
            for mapping in supervisor["agent_mappings"]:
                node_id = mapping["node_id"]
                agent_id = mapping["agent"]["id"]
                
                if node_id not in node_to_agents:
                    node_to_agents[node_id] = []
                
                if agent_id in agents:
                    node_to_agents[node_id].append({
                        "agent": agents[agent_id],
                        "agent_id": agent_id,
                        "config": mapping["config"],
                        "execution_order": mapping["execution_order"]
                    })
            
            # Add nodes to the graph
            for node_id, node_config in nodes.items():
                node_type = node_config.get("type", "unknown")
                custom_type = node_config.get("custom_type")
                
                handler_key = custom_type if custom_type and custom_type in node_handlers else node_type
                
                if handler_key in node_handlers:
                    # Get mapped agents for this node
                    node_agents = node_to_agents.get(node_id, [])
                    
                    # Create the node handler
                    node_handler = node_handlers[handler_key](
                        node_id=node_id,
                        node_config=node_config,
                        supervisor_config=supervisor,
                        agents=node_agents,
                        llm=llm
                    )
                    
                    # Add the node to the graph
                    builder.add_node(node_id, node_handler)
                    logger.debug(f"Added node {node_id} with type {node_type}")
                else:
                    logger.warning(f"Unknown node type {node_type} for node {node_id}")
            
            # Get edges
            edges = supervisor["edges"]
            
            # If edges is empty, create default edges
            if not edges:
                logger.warning(f"No edges defined for supervisor {supervisor_id}, using defaults")
                # Default to linear flow: router -> agent_executor -> guardrails -> end
                if "router" in nodes and "agent_executor" in nodes and "guardrails" in nodes:
                    edges = {
                        "router": [{"target": "agent_executor"}],
                        "agent_executor": [{"target": "guardrails"}],
                        "guardrails": [{"target": "__end__"}]
                    }
            
            # Set entry point
            entry_node = supervisor["entry_node"]
            if entry_node in nodes:
                builder.set_entry_point(entry_node)
            else:
                # Fallback to first node or "router"
                if "router" in nodes:
                    builder.set_entry_point("router")
                elif nodes:
                    builder.set_entry_point(next(iter(nodes.keys())))
                else:
                    logger.error(f"No valid entry point found for supervisor {supervisor_id}")
                    return None
            
            # Add edges
            for source_node, targets in edges.items():
                for edge_config in targets:
                    target_node = edge_config.get("target")
                    
                    # Handle end node
                    if target_node == "__end__":
                        builder.add_edge(source_node, END)
                        logger.debug(f"Added edge {source_node} -> END")
                        continue
                    
                    # Check if target node exists
                    if target_node not in nodes:
                        logger.warning(f"Target node {target_node} not found for edge from {source_node}")
                        continue
                    
                    # Add the edge
                    builder.add_edge(source_node, target_node)
                    logger.debug(f"Added edge {source_node} -> {target_node}")
            
            # Compile the graph
            compiled_graph = builder.compile()
            logger.info(f"Created supervisor graph for {supervisor['name']} with {len(nodes)} nodes")
            
            return compiled_graph
            
        except Exception as e:
            logger.error(f"Error creating supervisor graph: {str(e)}", exc_info=True)
            return None
    
    def _create_router_node(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        supervisor_config: Dict[str, Any],
        agents: List[Dict[str, Any]],
        llm: Any
    ) -> Any:
        """
        Create a router node handler.
        
        Args:
            node_id: Node identifier
            node_config: Node configuration
            supervisor_config: Supervisor configuration
            agents: List of agents mapped to this node
            llm: LLM instance
            
        Returns:
            Router node handler function
        """
        # Get router configuration
        pattern_first = node_config.get("pattern_first", True)
        routing_prompt = supervisor_config.get("routing_prompt")
        
        # Default routing prompt if not provided
        if not routing_prompt:
            routing_prompt = """
            You are an expert agent router for Staples customer service.
            Your job is to analyze the user's query and determine which specialized agent is best equipped to handle it.
            
            Available specialized agents:
            {agent_descriptions}
            
            User query: {user_input}
            
            Select the most appropriate agent based on the nature of the user's query.
            The response should be a JSON object with the following fields:
            - agent_id: The ID of the selected agent
            - confidence: A number between 0.0 and 1.0 indicating your confidence in this selection
            - reasoning: A brief explanation of why you selected this agent
            
            IMPORTANT: Only include agents from the list provided. Do not invent new agents.
            If no specialized agent is appropriate, select the general conversation agent.
            
            Response (in JSON format):
            """
        
        async def router_handler(state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Router node handler function.
            
            Args:
                state: Current workflow state
                
            Returns:
                Updated workflow state with selected agent
            """
            user_input = state.get("user_input", "")
            all_agents = state.get("agents", {})
            trace = state.get("trace", [])
            
            # Add to trace
            trace.append({
                "node": node_id,
                "type": "router",
                "timestamp": state.get("timestamp", 0)
            })
            state["trace"] = trace
            
            # 1. If pattern_first is True, try pattern matching first
            if pattern_first and "agent_patterns" in state:
                agent_patterns = state.get("agent_patterns", {})
                for agent_id, patterns in agent_patterns.items():
                    if agent_id in all_agents:
                        for pattern in patterns:
                            if pattern.lower() in user_input.lower():
                                # Pattern match found
                                agent = all_agents[agent_id]
                                state["selected_agent"] = agent
                                state["current_agent_id"] = agent_id
                                state["confidence"] = 1.0
                                state["selection_method"] = "pattern"
                                state["pattern_match"] = pattern
                                state["routing_explanation"] = f"Pattern match found: '{pattern}'"
                                
                                logger.info(f"Pattern match routing to agent {agent.name} with pattern '{pattern}'")
                                return state
            
            # 2. If no pattern match or pattern_first is False, use LLM
            try:
                # Format available agents for prompt
                agent_descriptions = []
                for agent_id, agent in all_agents.items():
                    agent_descriptions.append(
                        f"- {agent.name} (ID: {agent_id}): {agent.description}"
                    )
                
                agent_descriptions_str = "\n".join(agent_descriptions)
                
                # Create and execute the selection chain
                selection_prompt = PromptTemplate.from_template(routing_prompt)
                
                selection_chain = selection_prompt | llm | StrOutputParser()
                
                result = await selection_chain.ainvoke({
                    "agent_descriptions": agent_descriptions_str,
                    "user_input": user_input
                })
                
                # Parse JSON result
                try:
                    # Clean up JSON result
                    result = result.strip()
                    if result.startswith("```json"):
                        result = result[7:result.rfind("```")]
                    elif result.startswith("```"):
                        result = result[3:result.rfind("```")]
                    
                    selection_data = json.loads(result)
                    
                    selected_agent_id = selection_data.get("agent_id", "")
                    confidence = float(selection_data.get("confidence", 0.5))
                    reasoning = selection_data.get("reasoning", "")
                    
                    # Get the agent by ID
                    if selected_agent_id in all_agents:
                        selected_agent = all_agents[selected_agent_id]
                        
                        # Update state with selected agent
                        state["selected_agent"] = selected_agent
                        state["current_agent_id"] = selected_agent_id
                        state["confidence"] = confidence
                        state["selection_method"] = "llm"
                        state["routing_explanation"] = reasoning
                        
                        logger.info(f"LLM selected agent: {selected_agent.name} (ID: {selected_agent_id}) with confidence {confidence}")
                        return state
                    
                    # If agent not found by ID, try to find by name
                    selected_agent_name = selection_data.get("agent_name", "")
                    if selected_agent_name:
                        for agent_id, agent in all_agents.items():
                            if agent.name.lower() == selected_agent_name.lower():
                                # Update state with selected agent
                                state["selected_agent"] = agent
                                state["current_agent_id"] = agent_id
                                state["confidence"] = confidence
                                state["selection_method"] = "llm_name_match"
                                state["routing_explanation"] = reasoning
                                
                                logger.info(f"LLM selected agent by name: {agent.name} with confidence {confidence}")
                                return state
                    
                    # If still no match, fall back to general agent
                    logger.warning(f"No agent found with ID {selected_agent_id} or name {selected_agent_name}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing agent selection result: {str(e)}")
                    logger.debug(f"Problematic result: {result}")
                
            except Exception as e:
                logger.error(f"Error in router selection: {str(e)}", exc_info=True)
            
            # 3. Fall back to general conversation agent
            for agent_id, agent in all_agents.items():
                if "general conversation" in agent.name.lower():
                    state["selected_agent"] = agent
                    state["current_agent_id"] = agent_id
                    state["confidence"] = 0.5
                    state["selection_method"] = "fallback"
                    state["routing_explanation"] = "No matching agent found, using general conversation agent"
                    
                    logger.info(f"Fallback to general conversation agent: {agent.name}")
                    return state
            
            # 4. If no general agent, use the first available agent
            if all_agents:
                first_agent_id = next(iter(all_agents.keys()))
                first_agent = all_agents[first_agent_id]
                
                state["selected_agent"] = first_agent
                state["current_agent_id"] = first_agent_id
                state["confidence"] = 0.1
                state["selection_method"] = "default"
                state["routing_explanation"] = "No matching or general agent found, using first available agent"
                
                logger.warning(f"Defaulting to first available agent: {first_agent.name}")
                return state
            
            # 5. If no agents available, set error
            state["error"] = "No agents available"
            state["selected_agent"] = None
            state["success"] = False
            
            logger.error("No agents available for routing")
            return state
            
        return router_handler
    
    def _create_agent_node(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        supervisor_config: Dict[str, Any],
        agents: List[Dict[str, Any]],
        llm: Any
    ) -> Any:
        """
        Create an agent execution node handler.
        
        Args:
            node_id: Node identifier
            node_config: Node configuration
            supervisor_config: Supervisor configuration
            agents: List of agents mapped to this node
            llm: LLM instance
            
        Returns:
            Agent node handler function
        """
        async def agent_handler(state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Agent execution node handler function.
            
            Args:
                state: Current workflow state
                
            Returns:
                Updated workflow state with agent response
            """
            selected_agent = state.get("selected_agent")
            user_input = state.get("user_input", "")
            context = state.get("context", {})
            trace = state.get("trace", [])
            
            # Add to trace
            trace.append({
                "node": node_id,
                "type": "agent_execution",
                "agent": selected_agent.name if selected_agent else "unknown",
                "timestamp": state.get("timestamp", 0)
            })
            state["trace"] = trace
            
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
                
                logger.info(f"Agent {selected_agent.name} executed successfully")
                return state
                
            except Exception as e:
                logger.error(f"Error executing agent {selected_agent.name}: {str(e)}", exc_info=True)
                
                # Set error response
                state["response"] = "I apologize, but I encountered an error while processing your request. Please try again."
                state["success"] = False
                state["error"] = str(e)
                
                return state
        
        return agent_handler
    
    def _create_guardrails_node(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        supervisor_config: Dict[str, Any],
        agents: List[Dict[str, Any]],
        llm: Any
    ) -> Any:
        """
        Create a guardrails node handler.
        
        Args:
            node_id: Node identifier
            node_config: Node configuration
            supervisor_config: Supervisor configuration
            agents: List of agents mapped to this node
            llm: LLM instance
            
        Returns:
            Guardrails node handler function
        """
        # Find guardrails agent if specified
        guardrails_agent = None
        if agents:
            # Sort by execution order
            sorted_agents = sorted(agents, key=lambda a: a.get("execution_order", 0))
            guardrails_agent = sorted_agents[0]["agent"]
        
        async def guardrails_handler(state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Guardrails node handler function.
            
            Args:
                state: Current workflow state
                
            Returns:
                Updated workflow state with guardrails applied
            """
            response = state.get("response", "")
            trace = state.get("trace", [])
            
            # Add to trace
            trace.append({
                "node": node_id,
                "type": "guardrails",
                "timestamp": state.get("timestamp", 0)
            })
            state["trace"] = trace
            
            # If no response, set a default
            if not response:
                logger.warning("Empty response before guardrails")
                state["response"] = "I apologize, but I couldn't generate a proper response. Please try again."
                return state
            
            # Use dedicated guardrails agent if available
            if guardrails_agent:
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
            else:
                # If no guardrails agent, use built-in LLM-based guardrails
                try:
                    guardrails_prompt = """
                    You are a guardrails system that ensures all responses meet Staples policy requirements and maintain a professional tone.
                    
                    Review the following response for any policy violations, inappropriate content, or unprofessional language.
                    If any issues are found, provide a corrected version that maintains the same meaning but fixes the issues.
                    If no issues are found, return the original response unchanged.
                    
                    Original response: {response}
                    
                    Corrected response (return unchanged if no issues):
                    """
                    
                    # Create and execute the guardrails chain
                    prompt_template = PromptTemplate.from_template(guardrails_prompt)
                    
                    guardrails_chain = prompt_template | llm | StrOutputParser()
                    
                    result = await guardrails_chain.ainvoke({
                        "response": response
                    })
                    
                    # If the result is different from the original, update it
                    if result.strip() != response.strip():
                        logger.info("Built-in guardrails modified the response")
                        state["original_response"] = response
                        state["response"] = result.strip()
                        state["guardrails_applied"] = True
                
                except Exception as e:
                    logger.error(f"Error in built-in guardrails: {str(e)}", exc_info=True)
                    # Continue with the original response
            
            return state
        
        return guardrails_handler
    
    def _create_memory_node(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        supervisor_config: Dict[str, Any],
        agents: List[Dict[str, Any]],
        llm: Any
    ) -> Any:
        """
        Create a memory store node handler.
        
        Args:
            node_id: Node identifier
            node_config: Node configuration
            supervisor_config: Supervisor configuration
            agents: List of agents mapped to this node
            llm: LLM instance
            
        Returns:
            Memory node handler function
        """
        async def memory_handler(state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Memory node handler function.
            
            Args:
                state: Current workflow state
                
            Returns:
                Updated workflow state with memory operations applied
            """
            trace = state.get("trace", [])
            
            # Add to trace
            trace.append({
                "node": node_id,
                "type": "memory_store",
                "timestamp": state.get("timestamp", 0)
            })
            state["trace"] = trace
            
            # Memory operations are handled by the supervisor brain service
            # This node is primarily a marker in the graph
            
            # Mark processing as complete
            state["completed"] = True
            state["completion_time"] = state.get("timestamp", 0)
            
            return state
        
        return memory_handler
    
    def _create_conditional_node(
        self,
        node_id: str,
        node_config: Dict[str, Any],
        supervisor_config: Dict[str, Any],
        agents: List[Dict[str, Any]],
        llm: Any
    ) -> Any:
        """
        Create a conditional routing node handler.
        
        Args:
            node_id: Node identifier
            node_config: Node configuration
            supervisor_config: Supervisor configuration
            agents: List of agents mapped to this node
            llm: LLM instance
            
        Returns:
            Conditional node handler function
        """
        # Get condition configuration
        condition = node_config.get("condition", {})
        condition_type = condition.get("type", "llm")
        
        async def conditional_handler(state: Dict[str, Any]) -> Dict[str, Any]:
            """
            Conditional node handler function.
            
            Args:
                state: Current workflow state
                
            Returns:
                Updated workflow state with conditional result
            """
            trace = state.get("trace", [])
            
            # Add to trace
            trace.append({
                "node": node_id,
                "type": "conditional",
                "condition_type": condition_type,
                "timestamp": state.get("timestamp", 0)
            })
            state["trace"] = trace
            
            # Default condition result (true path)
            state["condition_result"] = "true"
            
            # Different condition types
            if condition_type == "confidence":
                # Route based on agent selection confidence
                threshold = condition.get("threshold", 0.7)
                confidence = state.get("confidence", 0)
                
                if confidence < threshold:
                    state["condition_result"] = "false"
                    logger.info(f"Condition {node_id} evaluates to false (confidence {confidence} < {threshold})")
                else:
                    logger.info(f"Condition {node_id} evaluates to true (confidence {confidence} >= {threshold})")
                
            elif condition_type == "llm":
                # Use LLM to evaluate condition
                prompt_template = condition.get("prompt", """
                Based on the conversation context below, answer the following question with only 'yes' or 'no'.
                
                User: {user_input}
                
                Question: {condition_question}
                
                Answer (only 'yes' or 'no'):
                """)
                
                question = condition.get("question", "Is this a complex question?")
                
                try:
                    # Create and execute the condition chain
                    prompt = PromptTemplate.from_template(prompt_template)
                    
                    condition_chain = prompt | llm | StrOutputParser()
                    
                    result = await condition_chain.ainvoke({
                        "user_input": state.get("user_input", ""),
                        "condition_question": question,
                        "response": state.get("response", ""),
                        "selected_agent": state.get("selected_agent").name if state.get("selected_agent") else "Unknown"
                    })
                    
                    # Normalize result
                    result = result.strip().lower()
                    if result in ["no", "false", "n"]:
                        state["condition_result"] = "false"
                        logger.info(f"LLM condition {node_id} evaluates to false (answer: {result})")
                    else:
                        logger.info(f"LLM condition {node_id} evaluates to true (answer: {result})")
                
                except Exception as e:
                    logger.error(f"Error evaluating LLM condition: {str(e)}", exc_info=True)
                    # Default to true on error
            
            elif condition_type == "pattern":
                # Check for pattern in user input
                patterns = condition.get("patterns", [])
                user_input = state.get("user_input", "").lower()
                
                pattern_found = False
                for pattern in patterns:
                    if pattern.lower() in user_input:
                        pattern_found = True
                        logger.info(f"Pattern condition {node_id} found match: {pattern}")
                        break
                
                if not pattern_found:
                    state["condition_result"] = "false"
                    logger.info(f"Pattern condition {node_id} found no matches")
            
            # Add condition result to state
            state["conditions"] = state.get("conditions", {})
            state["conditions"][node_id] = state["condition_result"]
            
            return state
        
        return conditional_handler