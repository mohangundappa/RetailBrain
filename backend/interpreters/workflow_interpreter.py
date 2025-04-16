"""
Workflow Interpreter for database-stored workflows.
This module loads and executes workflow graphs from the database.
"""
import logging
from typing import Dict, Any, List, Optional
import json
import time
from uuid import UUID

from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

logger = logging.getLogger(__name__)

class WorkflowInterpreter:
    """
    Loads and executes workflow graphs from the database.
    Supports standard node types and conditional branching.
    """
    
    def __init__(self, db_session):
        """
        Initialize the workflow interpreter.
        
        Args:
            db_session: Database session for queries
        """
        self.db = db_session
        self._workflow_cache = {}
        self._node_functions = {
            'prompt': self._execute_prompt_node,
            'response': self._execute_response_node,
            'extraction': self._execute_extraction_node,
            'conditional': self._execute_conditional_node,
            'tool': self._execute_tool_node,
        }
        
    async def load_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Load a workflow and all its components from the database.
        
        Args:
            workflow_id: UUID of the workflow to load
            
        Returns:
            Dict containing complete workflow definition
        """
        if workflow_id in self._workflow_cache:
            return self._workflow_cache[workflow_id]
            
        # Load workflow metadata
        workflow_query = """
            SELECT id, agent_id, name, description, version, entry_node
            FROM workflows 
            WHERE id = $1 AND is_active = true
        """
        
        workflow = await self.db.fetchrow(workflow_query, workflow_id)
        if not workflow:
            raise ValueError(f"No active workflow found with ID {workflow_id}")
            
        workflow_data = dict(workflow)
        
        # Load nodes
        nodes_query = """
            SELECT id, name, node_type, function_name, system_prompt_id, 
                   response_template, config
            FROM workflow_nodes
            WHERE workflow_id = $1
        """
        
        nodes = await self.db.fetch(nodes_query, workflow_id)
        
        # Load edges
        edges_query = """
            SELECT id, source_node_id, target_node_id, condition_type, 
                   condition_value, priority
            FROM workflow_edges
            WHERE workflow_id = $1
            ORDER BY priority
        """
        
        edges = await self.db.fetch(edges_query, workflow_id)
        
        # Build complete workflow
        workflow_data['nodes'] = {str(node['id']): dict(node) for node in nodes}
        
        # Convert edges to an adjacency list
        workflow_data['edges'] = {}
        for edge in edges:
            source_id = str(edge['source_node_id'])
            target_id = str(edge['target_node_id']) if edge['target_node_id'] else 'END'
            
            if source_id not in workflow_data['edges']:
                workflow_data['edges'][source_id] = []
                
            workflow_data['edges'][source_id].append({
                'target': target_id,
                'condition_type': edge['condition_type'],
                'condition_value': edge['condition_value'],
                'priority': edge['priority']
            })
            
        self._workflow_cache[workflow_id] = workflow_data
        return workflow_data
    
    async def build_graph(self, workflow_data: Dict[str, Any], llm, interpreters) -> StateGraph:
        """
        Build a StateGraph from workflow data.
        
        Args:
            workflow_data: Complete workflow definition
            llm: LLM instance to use for execution
            interpreters: Dict of interpreter instances
            
        Returns:
            Compiled StateGraph
        """
        # Define a simple state type for now
        graph = StateGraph(Dict)
        
        # Add nodes to graph
        for node_id, node in workflow_data['nodes'].items():
            node_type = node['node_type']
            
            # Create node function for this node
            async def node_func(state, node_id=node_id, node_type=node_type):
                node_data = workflow_data['nodes'][node_id]
                executor = self._node_functions.get(node_type)
                if not executor:
                    raise ValueError(f"Unknown node type: {node_type}")
                    
                return await executor(
                    state=state,
                    node=node_data,
                    llm=llm,
                    interpreters=interpreters,
                    workflow=workflow_data
                )
                
            graph.add_node(node_id, node_func)
            
        # Set entry point
        entry_node = str(workflow_data['entry_node'])
        graph.set_entry_point(entry_node)
        
        # Add edges
        for source_id, edges in workflow_data['edges'].items():
            for edge in edges:
                target_id = edge['target']
                condition_type = edge['condition_type']
                
                if condition_type == 'direct':
                    # Direct edge
                    if target_id == 'END':
                        graph.add_edge(source_id, END)
                    else:
                        graph.add_edge(source_id, target_id)
                elif condition_type == 'conditional':
                    # Conditional edge
                    condition_value = edge['condition_value']
                    
                    # Simple condition function
                    def condition_func(state, cv=condition_value):
                        # This is a simplistic condition - in a real implementation,
                        # you'd want more sophisticated evaluation
                        if 'extraction_results' in state:
                            result = state['extraction_results'].get('result')
                            if result == cv:
                                return cv
                        return None
                    
                    # Add conditional edge
                    target = END if target_id == 'END' else target_id
                    graph.add_conditional_edges(
                        source_id,
                        condition_func,
                        {condition_value: target}
                    )
                    
        return graph.compile()
        
    async def execute_workflow(self, workflow_data: Dict[str, Any], context: Dict[str, Any], 
                              interpreters: Dict[str, Any], llm=None) -> Dict[str, Any]:
        """
        Execute a workflow using the provided context.
        This is a simplified version for the implementation.
        
        Args:
            workflow_data: Complete workflow definition
            context: Execution context
            interpreters: Dict of interpreter instances
            llm: Optional LLM instance to use
            
        Returns:
            Dict containing execution results
        """
        # Initialize state
        state = {
            'current_node': str(workflow_data['entry_node']),
            'history': [],
            'data': {},
            'context': context,
            'input': context.get('input', ''),
            'output': '',
            'memory': context.get('memory', {}),
            'start_time': time.time()
        }
        
        # Execute until we reach an end state or max iterations
        max_iterations = 20
        iterations = 0
        
        while state['current_node'] != 'END' and iterations < max_iterations:
            iterations += 1
            logger.debug(f"Executing node: {state['current_node']}")
            
            # Get current node
            current_node_id = state['current_node']
            if current_node_id not in workflow_data['nodes']:
                raise ValueError(f"Node not found: {current_node_id}")
                
            node = workflow_data['nodes'][current_node_id]
            state['history'].append(current_node_id)
            
            # Execute node based on type
            node_type = node['node_type']
            executor = self._node_functions.get(node_type)
            
            if not executor:
                raise ValueError(f"Unknown node type: {node_type}")
                
            state = await executor(
                state=state,
                node=node,
                llm=llm,
                interpreters=interpreters,
                workflow=workflow_data
            )
            
            # Determine next node
            if current_node_id in workflow_data['edges']:
                # Check conditional edges first
                conditional_transitions = [
                    e for e in workflow_data['edges'][current_node_id] 
                    if e['condition_type'] == 'conditional'
                ]
                
                direct_transitions = [
                    e for e in workflow_data['edges'][current_node_id] 
                    if e['condition_type'] == 'direct'
                ]
                
                next_node = None
                
                # Check conditional edges
                if conditional_transitions and 'extraction_results' in state:
                    result = state['extraction_results'].get('result')
                    for edge in conditional_transitions:
                        if edge['condition_value'] == result:
                            next_node = edge['target']
                            break
                            
                # If no condition matched, use direct transition
                if next_node is None and direct_transitions:
                    next_node = direct_transitions[0]['target']
                    
                if next_node:
                    state['current_node'] = 'END' if next_node == 'END' else next_node
                else:
                    state['current_node'] = 'END'  # No transition, end
            else:
                state['current_node'] = 'END'  # No outgoing edges, end
            
        # Return final state
        return {
            'response': state.get('output', ''),
            'data': state.get('data', {}),
            'history': state.get('history', []),
            'iterations': iterations,
            'execution_time': time.time() - state['start_time']
        }
    
    async def _execute_prompt_node(self, state: Dict[str, Any], node: Dict[str, Any], 
                                 llm, interpreters: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a prompt node.
        
        Args:
            state: Current workflow state
            node: Node definition
            llm: LLM instance
            interpreters: Dict of interpreter instances
            workflow: Workflow definition
            
        Returns:
            Updated state
        """
        if not llm:
            raise ValueError("LLM required for prompt node execution")
            
        prompt_id = node.get('system_prompt_id')
        if not prompt_id:
            raise ValueError(f"No system prompt ID specified for node {node['id']}")
            
        prompt_interpreter = interpreters.get('prompt')
        if not prompt_interpreter:
            raise ValueError("Prompt interpreter required")
            
        # Load prompt data
        prompt_data = await prompt_interpreter.load_prompt(str(prompt_id))
        
        # Process variables
        variables = {
            'input': state.get('input', ''),
            'context': state.get('context', {}),
            'memory': state.get('memory', {})
        }
        
        # Get processed prompt
        prompt_content = prompt_interpreter.process_prompt(prompt_data, variables)
        
        # Call LLM with the prompt
        messages = [
            SystemMessage(content=prompt_content),
            HumanMessage(content=state.get('input', ''))
        ]
        
        response = await llm.agenerate_response(messages)
        
        # Update state
        state['data']['prompt_response'] = response
        state['output'] = response
        
        return state
        
    async def _execute_response_node(self, state: Dict[str, Any], node: Dict[str, Any], 
                                   llm, interpreters: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a response node.
        
        Args:
            state: Current workflow state
            node: Node definition
            llm: LLM instance
            interpreters: Dict of interpreter instances
            workflow: Workflow definition
            
        Returns:
            Updated state
        """
        template = node.get('response_template', '')
        
        if not template:
            # No template, just use previous output
            return state
            
        # Simple template processing
        variables = {
            'input': state.get('input', ''),
            'context': state.get('context', {}),
            'memory': state.get('memory', {}),
            'data': state.get('data', {})
        }
        
        # Very basic template substitution
        output = template
        for key, value in variables.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    placeholder = f"{{{key}.{subkey}}}"
                    if placeholder in output:
                        output = output.replace(placeholder, str(subvalue))
            else:
                placeholder = f"{{{key}}}"
                if placeholder in output:
                    output = output.replace(placeholder, str(value))
                    
        state['output'] = output
        return state
        
    async def _execute_extraction_node(self, state: Dict[str, Any], node: Dict[str, Any], 
                                     llm, interpreters: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an extraction node.
        
        Args:
            state: Current workflow state
            node: Node definition
            llm: LLM instance
            interpreters: Dict of interpreter instances
            workflow: Workflow definition
            
        Returns:
            Updated state
        """
        if not llm:
            raise ValueError("LLM required for extraction node")
            
        prompt_id = node.get('system_prompt_id')
        if not prompt_id:
            raise ValueError(f"No extraction prompt ID specified for node {node['id']}")
            
        prompt_interpreter = interpreters.get('prompt')
        if not prompt_interpreter:
            raise ValueError("Prompt interpreter required")
            
        # Load prompt data
        prompt_data = await prompt_interpreter.load_prompt(str(prompt_id))
        
        # Process variables
        variables = {
            'input': state.get('input', ''),
            'context': state.get('context', {}),
            'memory': state.get('memory', {})
        }
        
        # Get processed prompt
        prompt_content = prompt_interpreter.process_prompt(prompt_data, variables)
        
        # Call LLM with the prompt
        messages = [
            SystemMessage(content=prompt_content),
            HumanMessage(content=state.get('input', ''))
        ]
        
        extraction_result = await llm.agenerate_response(messages)
        
        # Parse extraction results
        # Assume extraction returns a JSON string
        try:
            result = json.loads(extraction_result)
        except:
            # If not valid JSON, use as-is
            result = {'result': extraction_result}
            
        # Update state
        state['extraction_results'] = result
        state['data']['extraction'] = result
        
        return state
        
    async def _execute_conditional_node(self, state: Dict[str, Any], node: Dict[str, Any], 
                                       llm, interpreters: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a conditional node.
        
        Args:
            state: Current workflow state
            node: Node definition
            llm: LLM instance
            interpreters: Dict of interpreter instances
            workflow: Workflow definition
            
        Returns:
            Updated state
        """
        # This is a placeholder - in a real implementation, 
        # you'd evaluate conditions based on the state
        config = node.get('config', {})
        condition_field = config.get('condition_field', '')
        
        # No actual execution, just passthrough
        return state
        
    async def _execute_tool_node(self, state: Dict[str, Any], node: Dict[str, Any], 
                               llm, interpreters: Dict[str, Any], workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool node.
        
        Args:
            state: Current workflow state
            node: Node definition
            llm: LLM instance
            interpreters: Dict of interpreter instances
            workflow: Workflow definition
            
        Returns:
            Updated state
        """
        # This is a placeholder - in a real implementation, 
        # you'd call registered tools from a tool registry
        function_name = node.get('function_name', '')
        config = node.get('config', {})
        
        logger.info(f"Would execute tool: {function_name} with config: {config}")
        
        # No actual execution for now, just passthrough
        return state