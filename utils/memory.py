"""
Memory management utilities for Staples Brain.

This module provides classes and functions for managing conversation memory
and context persistence between agent interactions.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from models import db, Conversation, Message

logger = logging.getLogger(__name__)

class ConversationMemory:
    """
    Manages persistent conversation memory across sessions and agents.
    
    This class provides an interface for storing and retrieving conversation
    history from the database and maintaining context between agent interactions.
    """
    
    def __init__(self, session_id: str, max_history: int = 20):
        """
        Initialize a conversation memory manager.
        
        Args:
            session_id: The session ID to track conversation history
            max_history: Maximum number of messages to include in history
        """
        self.session_id = session_id
        self.max_history = max_history
        self.working_memory: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {}
        logger.debug(f"Initialized conversation memory for session {session_id}")
        
    def load_conversation_history(self, conversation_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load conversation history from the database.
        
        Args:
            conversation_id: Optional specific conversation ID to load
            
        Returns:
            List of message dictionaries in chronological order
        """
        try:
            if conversation_id:
                # Load messages from a specific conversation
                conversation = Conversation.query.get(conversation_id)
                if not conversation:
                    logger.warning(f"Conversation {conversation_id} not found")
                    return []
                
                messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
            else:
                # Load latest messages from the session
                conversations = Conversation.query.filter_by(session_id=self.session_id).order_by(Conversation.created_at.desc()).limit(5).all()
                conversation_ids = [conv.id for conv in conversations]
                
                if not conversation_ids:
                    return []
                
                messages = Message.query.filter(Message.conversation_id.in_(conversation_ids)).order_by(Message.created_at).limit(self.max_history).all()
            
            # Convert to list of dictionaries
            message_list = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                    "conversation_id": msg.conversation_id
                }
                for msg in messages
            ]
            
            logger.debug(f"Loaded {len(message_list)} messages from history")
            return message_list
            
        except Exception as e:
            logger.error(f"Error loading conversation history: {str(e)}", exc_info=True)
            return []
    
    def add_message(self, role: str, content: str, conversation_id: int) -> bool:
        """
        Add a message to the conversation history.
        
        Args:
            role: The role of the message sender ('user', 'assistant', 'system')
            content: The message content
            conversation_id: The ID of the conversation to add this message to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create and add message to database
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content
            )
            db.session.add(message)
            db.session.commit()
            
            logger.debug(f"Added {role} message to conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding message to history: {str(e)}", exc_info=True)
            db.session.rollback()
            return False
    
    def get_system_prompt(self, agent_name: str) -> str:
        """
        Get a system prompt with context from conversation history.
        
        Args:
            agent_name: The name of the agent requesting the prompt
            
        Returns:
            A system prompt string with relevant context
        """
        # Load the conversation history
        history = self.load_conversation_history()
        
        # Extract agent-specific context
        agent_context = self.get_agent_context(agent_name)
        
        # Prepare a condensed version of the conversation history
        history_summary = self._create_history_summary(history)
        
        # Combine history and context into a system prompt
        system_prompt = f"""You are a helpful Staples assistant specializing in {agent_name}.
        
Conversation history summary:
{history_summary}

Relevant context:
{self._format_context(agent_context)}

Use this information to provide a helpful and contextually relevant response.
"""
        return system_prompt
    
    def _create_history_summary(self, history: List[Dict[str, Any]]) -> str:
        """Create a summary of conversation history."""
        if not history:
            return "No previous conversation."
        
        # Include last few turns of conversation
        recent_turns = history[-min(5, len(history)):]
        history_text = "\n".join([
            f"{msg['role'].title()}: {msg['content']}" 
            for msg in recent_turns
        ])
        
        return history_text
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as a readable string."""
        if not context:
            return "No specific context information available."
        
        lines = []
        for key, value in context.items():
            if isinstance(value, dict):
                lines.append(f"- {key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  - {sub_key}: {sub_value}")
            else:
                lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)
    
    def update_working_memory(self, key: str, value: Any) -> None:
        """
        Update working memory with a key-value pair.
        
        Args:
            key: Memory key
            value: Memory value
        """
        self.working_memory[key] = value
        logger.debug(f"Updated working memory: {key}")
    
    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """
        Get a value from working memory.
        
        Args:
            key: Memory key
            default: Default value to return if key not found
            
        Returns:
            The stored value or default if not found
        """
        return self.working_memory.get(key, default)
    
    def update_context(self, agent_name: str, context_updates: Dict[str, Any]) -> None:
        """
        Update context for a specific agent.
        
        Args:
            agent_name: The name of the agent
            context_updates: Dictionary of context updates
        """
        if agent_name not in self.context:
            self.context[agent_name] = {}
        
        self.context[agent_name].update(context_updates)
        logger.debug(f"Updated context for {agent_name}")
    
    def get_agent_context(self, agent_name: str) -> Dict[str, Any]:
        """
        Get context for a specific agent.
        
        Args:
            agent_name: The name of the agent
            
        Returns:
            The agent's context dictionary
        """
        return self.context.get(agent_name, {})
    
    def get_full_context(self) -> Dict[str, Any]:
        """
        Get the full context across all agents.
        
        Returns:
            The complete context dictionary
        """
        # Combine working memory and agent contexts
        full_context = {
            "working_memory": self.working_memory,
            "agent_contexts": self.context,
            "session_id": self.session_id,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return full_context