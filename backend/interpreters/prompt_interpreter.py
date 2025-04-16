"""
Prompt Interpreter for database-stored system prompts.
This module loads, caches, and processes system prompts from the database.
"""
import logging
from typing import Dict, Optional, Any, List
import json

logger = logging.getLogger(__name__)

class PromptInterpreter:
    """
    Loads and processes system prompts from the database.
    Provides caching and variable substitution capabilities.
    """
    
    def __init__(self, db_session):
        """
        Initialize the prompt interpreter.
        
        Args:
            db_session: Database session for queries
        """
        self.db = db_session
        self._prompt_cache = {}
        
    async def load_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """
        Load a specific prompt by ID.
        
        Args:
            prompt_id: UUID of the prompt to load
            
        Returns:
            Dict containing prompt data
        """
        if prompt_id in self._prompt_cache:
            return self._prompt_cache[prompt_id]
            
        query = """
            SELECT id, agent_id, prompt_type, content, description, 
                   version, variables
            FROM system_prompts 
            WHERE id = $1 AND is_active = true
        """
        
        result = await self.db.fetchrow(query, prompt_id)
        if not result:
            raise ValueError(f"No active prompt found with ID {prompt_id}")
            
        prompt_data = dict(result)
        self._prompt_cache[prompt_id] = prompt_data
        return prompt_data
        
    async def load_agent_prompts(self, agent_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Load all prompts for a specific agent.
        
        Args:
            agent_id: UUID of the agent to load prompts for
            
        Returns:
            Dict of prompt_type -> prompt_data
        """
        query = """
            SELECT id, agent_id, prompt_type, content, description, 
                   version, variables
            FROM system_prompts 
            WHERE agent_id = $1 AND is_active = true
        """
        
        results = await self.db.fetch(query, agent_id)
        
        prompts = {}
        for record in results:
            prompt_data = dict(record)
            prompt_type = prompt_data['prompt_type']
            self._prompt_cache[prompt_data['id']] = prompt_data
            prompts[prompt_type] = prompt_data
            
        return prompts
        
    async def get_prompt_by_type(self, agent_id: str, prompt_type: str) -> Dict[str, Any]:
        """
        Get a specific prompt by type for an agent.
        
        Args:
            agent_id: UUID of the agent
            prompt_type: Type of prompt to retrieve
            
        Returns:
            Dict containing prompt data
        """
        query = """
            SELECT id, agent_id, prompt_type, content, description, 
                   version, variables
            FROM system_prompts 
            WHERE agent_id = $1 AND prompt_type = $2 AND is_active = true
            ORDER BY version DESC LIMIT 1
        """
        
        result = await self.db.fetchrow(query, agent_id, prompt_type)
        if not result:
            raise ValueError(f"No active {prompt_type} prompt found for agent {agent_id}")
            
        prompt_data = dict(result)
        self._prompt_cache[prompt_data['id']] = prompt_data
        return prompt_data
        
    def process_prompt(self, prompt: Dict[str, Any], variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a prompt by substituting variables.
        
        Args:
            prompt: Prompt data dictionary
            variables: Variables to substitute in the prompt
            
        Returns:
            Processed prompt string
        """
        content = prompt['content']
        
        if variables:
            # Simple variable substitution
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                if placeholder in content:
                    content = content.replace(placeholder, str(value))
                    
        return content