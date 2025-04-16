"""
Prompt Interpreter for Staples Brain.

This module provides a service for interpreting and executing prompts from a database.
It supports template variables and context substitution.
"""
import logging
import json
import re
from typing import Dict, Any, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class PromptInterpreter:
    """
    Service for interpreting and executing prompts from a database.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the prompt interpreter.
        
        Args:
            db_session: Async database session
        """
        self.db = db_session
        logger.info("Initialized PromptInterpreter")
    
    async def get_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """
        Get a prompt by ID.
        
        Args:
            prompt_id: ID of the prompt
            
        Returns:
            Prompt data
        """
        try:
            # Get prompt from database
            result = await self.db.execute(
                """
                SELECT id, name, content, template_variables, created_at, updated_at
                FROM system_prompts
                WHERE id = $1
                """,
                prompt_id
            )
            
            row = result.fetchone()
            if not row:
                return None
                
            # Parse template variables
            template_vars = json.loads(row[3]) if row[3] else []
            
            # Return prompt data
            return {
                'id': row[0],
                'name': row[1],
                'content': row[2],
                'template_variables': template_vars,
                'created_at': row[4].isoformat() if row[4] else None,
                'updated_at': row[5].isoformat() if row[5] else None
            }
        except Exception as e:
            logger.error(f"Error getting prompt {prompt_id}: {str(e)}", exc_info=True)
            raise
    
    def _substitute_variables(self, prompt_content: str, context: Dict[str, Any]) -> str:
        """
        Substitute variables in a prompt template.
        
        Args:
            prompt_content: Prompt template content
            context: Context data with variable values
            
        Returns:
            Prompt with variables substituted
        """
        # Simple variable substitution with {{variable_name}}
        pattern = r'{{([^{}]+)}}'
        
        def replace_var(match):
            var_name = match.group(1).strip()
            if var_name in context:
                return str(context[var_name])
            else:
                logger.warning(f"Variable {var_name} not found in context")
                return f"{{{{MISSING:{var_name}}}}}"
        
        # Replace all variables in the prompt
        return re.sub(pattern, replace_var, prompt_content)
    
    async def interpret_prompt(
        self, 
        prompt_id: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        Interpret a prompt with the given context.
        
        Args:
            prompt_id: ID of the prompt to interpret
            context: Context data for variable substitution
            
        Returns:
            Interpreted prompt content
        """
        try:
            # Get prompt data
            prompt_data = await self.get_prompt(prompt_id)
            if not prompt_data:
                raise ValueError(f"Prompt with ID {prompt_id} not found")
            
            # Substitute variables
            prompt_content = self._substitute_variables(prompt_data['content'], context)
            
            return prompt_content
        except Exception as e:
            logger.error(f"Error interpreting prompt {prompt_id}: {str(e)}", exc_info=True)
            raise
    
    async def interpret_inline_prompt(
        self, 
        prompt_content: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        Interpret an inline prompt with the given context.
        
        Args:
            prompt_content: Prompt template content
            context: Context data for variable substitution
            
        Returns:
            Interpreted prompt content
        """
        try:
            # Substitute variables
            return self._substitute_variables(prompt_content, context)
        except Exception as e:
            logger.error(f"Error interpreting inline prompt: {str(e)}", exc_info=True)
            raise
            
    async def create_prompt(
        self, 
        name: str, 
        content: str, 
        template_variables: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new prompt.
        
        Args:
            name: Name of the prompt
            content: Prompt template content
            template_variables: List of template variable names
            
        Returns:
            Created prompt data
        """
        import uuid
        from datetime import datetime
        
        try:
            prompt_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            # Store prompt in database
            await self.db.execute(
                """
                INSERT INTO system_prompts (id, name, content, template_variables, 
                                          created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                prompt_id,
                name,
                content,
                json.dumps(template_variables or []),
                now,
                now
            )
            
            # Commit the transaction
            await self.db.commit()
            
            # Return created prompt
            return {
                'id': prompt_id,
                'name': name,
                'content': content,
                'template_variables': template_variables or [],
                'created_at': now,
                'updated_at': now
            }
        except Exception as e:
            # Rollback transaction
            await self.db.rollback()
            logger.error(f"Error creating prompt: {str(e)}", exc_info=True)
            raise