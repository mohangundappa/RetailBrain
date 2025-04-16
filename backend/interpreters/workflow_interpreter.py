"""
Workflow Interpreter for Staples Brain.

This module provides a service for interpreting and executing workflows from a database.
It builds workflow graphs from configuration and executes them with user input.
"""
import logging
import json
import time
from typing import Dict, Any, List, Optional, Union, Callable, TypeVar, Iterator

from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

from sqlalchemy.ext.asyncio import AsyncSession
from backend.interpreters.prompt_interpreter import PromptInterpreter

logger = logging.getLogger(__name__)

# Type definitions for state and nodes
T = TypeVar('T')
State = Dict[str, Any]
NodeFn = Callable[[State], State]

class WorkflowInterpreter:
    """
    Service for interpreting and executing workflows from a database.
    """
    
    def __init__(self, db_session: AsyncSession, llm_service=None):
        """
        Initialize the workflow interpreter.
        
        Args:
            db_session: Async database session
            llm_service: Service for LLM interactions
        """
        self.db = db_session
        self.llm_service = llm_service
        self.prompt_interpreter = PromptInterpreter(db_session)
        logger.info("Initialized WorkflowInterpreter")
    
    async def build_graph(self, workflow_data: Dict[str, Any]) -> StateGraph:
        """
        Build a workflow graph from configuration data.
        
        Args:
            workflow_data: Workflow configuration data
            
        Returns:
            StateGraph object
        """
        try:
            # Extract workflow components
            nodes = workflow_data.get('nodes', {})
            edges = workflow_data.get('edges', {})
            entry_node = workflow_data.get('entry_node')
            
            if not nodes or not entry_node:
                raise ValueError("Workflow must have nodes and an entry node")
            
            # Create node functions
            node_functions = {}
            for node_id, node_config in nodes.items():
                node_functions[node_id] = await self._create_node_function(node_id, node_config)
            
            # Create workflow graph
            workflow = StateGraph(nodes=node_functions)
            
            # Add edges
            for edge_id, edge_config in edges.items():
                source = edge_config.get('source')
                target = edge_config.get('target')
                condition = edge_config.get('condition')
                
                if not source or not target:
                    logger.warning(f"Edge {edge_id} missing source or target")
                    continue
                
                if condition:
                    # Conditional edge
                    workflow.add_conditional_edges(
                        source,
                        self._create_edge_condition(condition),
                        {
                            True: target,
                            False: edge_config.get('fallback', END)
                        }
                    )
                else:
                    # Direct edge
                    workflow.add_edge(source, target)
            
            # Compile the graph
            return workflow.compile()
        except Exception as e:
            logger.error(f"Error building workflow graph: {str(e)}", exc_info=True)
            raise
    
    async def _create_node_function(self, node_id: str, node_config: Dict[str, Any]) -> NodeFn:
        """
        Create a function for a workflow node.
        
        Args:
            node_id: ID of the node
            node_config: Node configuration
            
        Returns:
            Node function
        """
        node_type = node_config.get('type', 'prompt')
        
        if node_type == 'prompt':
            # Create a prompt node function
            return await self._create_prompt_node(node_id, node_config)
        elif node_type == 'function':
            # Create a function node
            return await self._create_function_node(node_id, node_config)
        elif node_type == 'condition':
            # Create a condition node
            return await self._create_condition_node(node_id, node_config)
        elif node_type == 'tool':
            # Create a tool node
            return await self._create_tool_node(node_id, node_config)
        else:
            raise ValueError(f"Unknown node type: {node_type}")
    
    async def _create_prompt_node(self, node_id: str, node_config: Dict[str, Any]) -> NodeFn:
        """
        Create a function for a prompt node.
        
        Args:
            node_id: ID of the node
            node_config: Node configuration
            
        Returns:
            Node function
        """
        prompt_id = node_config.get('prompt_id')
        inline_prompt = node_config.get('prompt')
        output_key = node_config.get('output_key', 'response')
        
        async def node_function(state: State) -> State:
            context = state.get('context', {})
            
            try:
                # Get the prompt content
                prompt_content = None
                if prompt_id:
                    # Use stored prompt
                    prompt_content = await self.prompt_interpreter.interpret_prompt(prompt_id, context)
                elif inline_prompt:
                    # Use inline prompt
                    prompt_content = await self.prompt_interpreter.interpret_inline_prompt(inline_prompt, context)
                else:
                    raise ValueError(f"Node {node_id} missing prompt_id or prompt")
                
                # Create a formatted prompt for the LLM
                messages = [
                    SystemMessage(content=prompt_content),
                    HumanMessage(content=state.get('input_message', ''))
                ]
                
                # Get LLM response
                response = await self._get_llm_response(messages)
                
                # Update state with response
                new_state = state.copy()
                new_state[output_key] = response
                
                # Add to history
                history = new_state.get('history', [])
                history.append({
                    'node': node_id,
                    'prompt': prompt_content,
                    'input': state.get('input_message', ''),
                    'response': response,
                    'timestamp': time.time()
                })
                new_state['history'] = history
                
                return new_state
            except Exception as e:
                logger.error(f"Error executing prompt node {node_id}: {str(e)}", exc_info=True)
                # Return state with error
                new_state = state.copy()
                new_state['error'] = str(e)
                return new_state
        
        return node_function
    
    async def _create_function_node(self, node_id: str, node_config: Dict[str, Any]) -> NodeFn:
        """
        Create a function for a function node.
        
        Args:
            node_id: ID of the node
            node_config: Node configuration
            
        Returns:
            Node function
        """
        function_name = node_config.get('function_name')
        output_key = node_config.get('output_key', 'function_result')
        
        # This is a simple placeholder for functions
        # In a real implementation, you'd register functions and look them up by name
        
        async def node_function(state: State) -> State:
            new_state = state.copy()
            
            # In a real implementation, you'd execute the function here
            # For now, just add a placeholder result
            new_state[output_key] = f"Function {function_name} executed"
            
            # Add to history
            history = new_state.get('history', [])
            history.append({
                'node': node_id,
                'function': function_name,
                'result': new_state[output_key],
                'timestamp': time.time()
            })
            new_state['history'] = history
            
            return new_state
        
        return node_function
    
    async def _create_condition_node(self, node_id: str, node_config: Dict[str, Any]) -> NodeFn:
        """
        Create a function for a condition node.
        
        Args:
            node_id: ID of the node
            node_config: Node configuration
            
        Returns:
            Node function
        """
        condition = node_config.get('condition')
        output_key = node_config.get('output_key', 'condition_result')
        
        async def node_function(state: State) -> State:
            new_state = state.copy()
            
            # Evaluate condition
            # This is a simple implementation that just checks for a fixed condition
            # In a real implementation, you'd evaluate the condition expression
            
            result = False  # Default to false
            try:
                # Simple condition check based on state keys
                if condition == 'has_error':
                    result = 'error' in state
                elif condition.startswith('contains:'):
                    # Check if a value contains a substring
                    key, value = condition.split(':', 1)[1].split('=', 1)
                    result = value in state.get(key, '')
                elif condition.startswith('equals:'):
                    # Check if a value equals a string
                    key, value = condition.split(':', 1)[1].split('=', 1)
                    result = state.get(key, '') == value
                else:
                    # Unknown condition
                    logger.warning(f"Unknown condition: {condition}")
            except Exception as e:
                logger.error(f"Error evaluating condition: {str(e)}")
            
            new_state[output_key] = result
            
            # Add to history
            history = new_state.get('history', [])
            history.append({
                'node': node_id,
                'condition': condition,
                'result': result,
                'timestamp': time.time()
            })
            new_state['history'] = history
            
            return new_state
        
        return node_function
    
    async def _create_tool_node(self, node_id: str, node_config: Dict[str, Any]) -> NodeFn:
        """
        Create a function for a tool node.
        
        Args:
            node_id: ID of the node
            node_config: Node configuration
            
        Returns:
            Node function
        """
        tool_name = node_config.get('tool_name')
        output_key = node_config.get('output_key', 'tool_result')
        
        # This is a simple placeholder for tools
        # In a real implementation, you'd register tools and look them up by name
        
        async def node_function(state: State) -> State:
            new_state = state.copy()
            
            # In a real implementation, you'd execute the tool here
            # For now, just add a placeholder result
            new_state[output_key] = f"Tool {tool_name} executed"
            
            # Add to history
            history = new_state.get('history', [])
            history.append({
                'node': node_id,
                'tool': tool_name,
                'result': new_state[output_key],
                'timestamp': time.time()
            })
            new_state['history'] = history
            
            return new_state
        
        return node_function
    
    def _create_edge_condition(self, condition: Dict[str, Any]) -> Callable[[State], bool]:
        """
        Create a condition function for an edge.
        
        Args:
            condition: Condition configuration
            
        Returns:
            Condition function
        """
        def condition_function(state: State) -> bool:
            # Simple condition check based on state keys
            if 'key' in condition and 'value' in condition:
                # Check if the key has the specified value
                key = condition['key']
                value = condition['value']
                return state.get(key) == value
            elif 'key' in condition:
                # Check if the key exists and is truthy
                return bool(state.get(condition['key']))
            else:
                # Unknown condition, default to true
                return True
        
        return condition_function
    
    async def _get_llm_response(self, messages: List[BaseMessage]) -> str:
        """
        Get a response from the LLM.
        
        Args:
            messages: List of messages for the LLM
            
        Returns:
            LLM response
        """
        if not self.llm_service:
            # Mock response for testing
            return "I'm a placeholder response. LLM service not configured."
        
        # Use the LLM service to get a response
        response = await self.llm_service.generate_response(messages)
        return response
    
    async def execute_workflow(
        self, 
        workflow_data: Dict[str, Any], 
        input_message: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow with the given input.
        
        Args:
            workflow_data: Workflow configuration data
            input_message: User input message
            context: Additional context data
            
        Returns:
            Execution result
        """
        try:
            # Build the workflow graph
            graph = await self.build_graph(workflow_data)
            
            # Prepare initial state
            initial_state = {
                'input_message': input_message,
                'context': context or {},
                'history': [],
                'iterations': 0
            }
            
            # Execute the graph
            # For a real implementation, you'd use the graph's arun method
            # For now, we'll simulate the execution
            
            # Simulate graph execution
            result = await self._simulate_graph_execution(workflow_data, initial_state)
            
            # Return execution result
            return {
                'response': result.get('response', ''),
                'history': result.get('history', []),
                'iterations': result.get('iterations', 0),
                'state': result
            }
        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}", exc_info=True)
            raise
    
    async def _simulate_graph_execution(
        self, 
        workflow_data: Dict[str, Any], 
        initial_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate the execution of a workflow graph.
        
        Args:
            workflow_data: Workflow configuration data
            initial_state: Initial state for the graph
            
        Returns:
            Final state after execution
        """
        # Extract workflow components
        nodes = workflow_data.get('nodes', {})
        edges = workflow_data.get('edges', {})
        entry_node = workflow_data.get('entry_node')
        
        state = initial_state.copy()
        current_node = entry_node
        max_iterations = 10  # Prevent infinite loops
        
        # Execute nodes until we reach an end state or max iterations
        for i in range(max_iterations):
            state['iterations'] = i + 1
            
            if current_node is None or current_node == 'END':
                break
                
            # Execute the current node
            node_config = nodes.get(current_node)
            if not node_config:
                logger.warning(f"Node {current_node} not found")
                break
                
            # Create and execute the node function
            node_fn = await self._create_node_function(current_node, node_config)
            state = await node_fn(state)
            
            # Find the next node
            next_node = None
            for edge_id, edge_config in edges.items():
                if edge_config.get('source') == current_node:
                    condition = edge_config.get('condition')
                    if condition:
                        # Check condition
                        condition_fn = self._create_edge_condition(condition)
                        if condition_fn(state):
                            next_node = edge_config.get('target')
                        else:
                            next_node = edge_config.get('fallback')
                    else:
                        # Direct edge
                        next_node = edge_config.get('target')
                    
                    if next_node:
                        break
            
            # Update current node
            current_node = next_node
            
            # If next node is END, break
            if current_node == 'END' or current_node is None:
                break
        
        return state