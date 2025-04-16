"""
Agent Runner for database-driven agents.
This module serves as the main entry point for executing database-defined agents.
"""
import logging
import time
from typing import Dict, Any, Optional
import json
import uuid

from .prompt_interpreter import PromptInterpreter
from .workflow_interpreter import WorkflowInterpreter

logger = logging.getLogger(__name__)

class AgentRunner:
    """
    Main entry point for executing database-defined agents.
    This class coordinates the loading and execution of agents from the database.
    """
    
    def __init__(self, db_session, llm_service, telemetry_service=None):
        """
        Initialize the agent runner.
        
        Args:
            db_session: Database session for queries
            llm_service: LLM service to use for agent execution
            telemetry_service: Optional telemetry service for logging
        """
        self.db = db_session
        self.llm = llm_service
        self.telemetry = telemetry_service
        
        # Initialize interpreters
        self.interpreters = {
            'prompt': PromptInterpreter(db_session),
            'workflow': WorkflowInterpreter(db_session),
        }
        
        # Cache for loaded agents
        self._agent_cache = {}
        
    async def load_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Load an agent definition from the database.
        
        Args:
            agent_id: UUID of the agent to load
            
        Returns:
            Dict containing the complete agent definition
        """
        if agent_id in self._agent_cache:
            return self._agent_cache[agent_id]
            
        # Load agent metadata
        query = """
            SELECT id, name, description, agent_type, version, status, 
                   is_system, workflow_id, prompt_config
            FROM agent_definitions 
            WHERE id = $1 AND status = 'active'
        """
        
        agent = await self.db.fetchrow(query, agent_id)
        if not agent:
            raise ValueError(f"No active agent found with ID {agent_id}")
            
        agent_data = dict(agent)
        
        # Load workflow if specified
        if agent_data.get('workflow_id'):
            workflow_interpreter = self.interpreters['workflow']
            agent_data['workflow'] = await workflow_interpreter.load_workflow(str(agent_data['workflow_id']))
        
        # Load prompts
        prompt_interpreter = self.interpreters['prompt']
        agent_data['prompts'] = await prompt_interpreter.load_agent_prompts(agent_id)
        
        # Load patterns
        patterns_query = """
            SELECT pattern_type, pattern_value, priority, confidence_boost
            FROM agent_patterns
            WHERE agent_id = $1
            ORDER BY priority
        """
        
        patterns = await self.db.fetch(patterns_query, agent_id)
        agent_data['patterns'] = [dict(p) for p in patterns]
        
        # Load response templates
        templates_query = """
            SELECT template_key, template_content, template_type, 
                   scenario, language, tone, is_fallback
            FROM agent_response_templates
            WHERE agent_id = $1
        """
        
        templates = await self.db.fetch(templates_query, agent_id)
        agent_data['response_templates'] = [dict(t) for t in templates]
        
        # Cache the agent
        self._agent_cache[agent_id] = agent_data
        return agent_data
        
    async def execute(self, agent_id: str, input_message: str, 
                     conversation_id: str = None, session_id: str = None, 
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute an agent with the given input message.
        
        Args:
            agent_id: UUID of the agent to execute
            input_message: Input message from the user
            conversation_id: Optional conversation ID
            session_id: Optional session ID
            context: Optional additional context
            
        Returns:
            Dict containing execution results
        """
        start_time = time.time()
        conversation_id = conversation_id or str(uuid.uuid4())
        session_id = session_id or str(uuid.uuid4())
        
        # Initialize execution context
        exec_context = {
            'agent_id': agent_id,
            'conversation_id': conversation_id,
            'session_id': session_id,
            'input': input_message,
            'context': context or {},
            'memory': {},  # This would be loaded from a memory service
            'start_time': start_time,
        }
        
        # Log execution start
        if self.telemetry:
            await self.telemetry.log_agent_execution_start(exec_context)
        
        try:
            # Load agent
            agent = await self.load_agent(agent_id)
            logger.info(f"Executing agent: {agent['name']} (ID: {agent_id})")
            
            # Check if the agent has a workflow
            if 'workflow' in agent:
                # Execute workflow
                workflow_interpreter = self.interpreters['workflow']
                result = await workflow_interpreter.execute_workflow(
                    workflow_data=agent['workflow'],
                    context=exec_context,
                    interpreters=self.interpreters,
                    llm=self.llm
                )
                
                response = result.get('response', '')
            else:
                # Fallback to direct prompt execution
                default_prompt = None
                for prompt_type, prompt in agent['prompts'].items():
                    if prompt_type == 'default' or prompt_type == 'main':
                        default_prompt = prompt
                        break
                
                if not default_prompt:
                    raise ValueError(f"No default/main prompt found for agent {agent_id}")
                
                # Process prompt
                prompt_interpreter = self.interpreters['prompt']
                prompt_content = prompt_interpreter.process_prompt(
                    default_prompt, 
                    {'input': input_message, 'context': exec_context}
                )
                
                # Call LLM
                messages = [
                    {"role": "system", "content": prompt_content},
                    {"role": "user", "content": input_message}
                ]
                
                response = await self.llm.generate_response(messages)
                result = {
                    'response': response,
                    'execution_time': time.time() - start_time
                }
            
            # Process result
            execution_time = time.time() - start_time
            if self.telemetry:
                await self.telemetry.log_agent_execution_complete(exec_context, result, execution_time)
            
            return {
                'agent_id': agent_id,
                'agent_name': agent['name'],
                'response': result.get('response', ''),
                'execution_time': execution_time,
                'status': 'success',
                'metadata': {
                    'conversation_id': conversation_id,
                    'session_id': session_id,
                    'history': result.get('history', []),
                    'iterations': result.get('iterations', 0)
                }
            }
            
        except Exception as e:
            # Handle execution error
            logger.exception(f"Error executing agent {agent_id}: {str(e)}")
            execution_time = time.time() - start_time
            
            if self.telemetry:
                await self.telemetry.log_agent_execution_error(exec_context, str(e), execution_time)
            
            return {
                'agent_id': agent_id,
                'response': f"I encountered an issue processing your request: {str(e)}",
                'execution_time': execution_time,
                'status': 'error',
                'error': str(e),
                'metadata': {
                    'conversation_id': conversation_id,
                    'session_id': session_id
                }
            }