"""
Factory for creating optimized agent selection components.
This module provides factories for creating the optimized router and related components.
"""
import logging
from typing import Dict, List, Optional, Any, Union

from sqlalchemy.ext.asyncio import AsyncSession

from backend.brain.optimized.agent_definition import AgentDefinition, PatternCapability, AgentTool, EntityDefinition
from backend.brain.optimized.embedding_service import EmbeddingService
from backend.brain.optimized.vector_store import AgentVectorStore
from backend.brain.optimized.router import OptimizedAgentRouter

logger = logging.getLogger(__name__)


class OptimizedAgentFactory:
    """
    Factory for creating optimized agent selection components.
    
    This factory:
    1. Creates EmbeddingService, AgentVectorStore, and OptimizedAgentRouter
    2. Loads agents from the database
    3. Converts between database models and internal models
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the factory.
        
        Args:
            db_session: Database session for loading agents
        """
        self.db_session = db_session
        self.embedding_service: Optional[EmbeddingService] = None
        self.vector_store: Optional[AgentVectorStore] = None
        self.router: Optional[OptimizedAgentRouter] = None
        
    async def create_components(self, memory_service: Optional[Any] = None) -> OptimizedAgentRouter:
        """
        Create all optimized components (embedding service, vector store, router).
        
        Args:
            memory_service: Optional memory service for conversation context
            
        Returns:
            Configured OptimizedAgentRouter
        """
        # Create embedding service
        self.embedding_service = EmbeddingService()
        
        # Create vector store
        self.vector_store = AgentVectorStore(self.embedding_service)
        
        # Create router
        self.router = OptimizedAgentRouter(
            agent_vector_store=self.vector_store,
            embedding_service=self.embedding_service,
            memory_service=memory_service
        )
        
        logger.info("Created optimized agent selection components")
        return self.router
        
    async def load_agents_from_database(self) -> int:
        """
        Load all active agents from the database and index them.
        
        Returns:
            Number of agents loaded
        """
        if not self.vector_store:
            logger.error("Vector store not initialized")
            return 0
            
        try:
            # Import the necessary models
            from backend.database.agent_schema import AgentDefinition as DbAgentDefinition
            from backend.database.agent_schema import AgentPattern, AgentTool as DbAgentTool
            from backend.database.agent_schema import EntityDefinition as DbEntityDefinition
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            
            # Query all active agents with their patterns, tools, and entities
            query = (
                select(DbAgentDefinition)
                .where(DbAgentDefinition.status == "active")
                .options(
                    selectinload(DbAgentDefinition.patterns),
                    selectinload(DbAgentDefinition.tools),
                    selectinload(DbAgentDefinition.entity_definitions)
                )
            )
            
            result = await self.db_session.execute(query)
            db_agents = result.scalars().all()
            
            count = 0
            for db_agent in db_agents:
                # Convert database agent to internal agent model
                agent = await self._convert_db_agent(db_agent)
                
                # Index the agent
                if agent:
                    success = await self.vector_store.index_agent(agent)
                    if success:
                        count += 1
                        
            logger.info(f"Loaded {count} agents from database")
            return count
        except Exception as e:
            logger.error(f"Error loading agents from database: {str(e)}")
            return 0
            
    async def _convert_db_agent(self, db_agent: Any) -> Optional[AgentDefinition]:
        """
        Convert a database agent to an internal agent model.
        
        Args:
            db_agent: Database agent model
            
        Returns:
            Converted AgentDefinition or None if conversion failed
        """
        try:
            # Create the agent
            agent = AgentDefinition(
                id=str(db_agent.id),
                name=db_agent.name,
                description=db_agent.description or "",
                version=db_agent.version
            )
            
            agent.status = db_agent.status
            agent.is_system = db_agent.is_system
            
            # Add patterns as capabilities
            pattern_capability = PatternCapability()
            for pattern in db_agent.patterns:
                pattern_capability.add_pattern(
                    pattern_type=pattern.pattern_type,
                    pattern_value=pattern.pattern_value,
                    confidence_boost=pattern.confidence_boost
                )
                
            if pattern_capability.patterns:
                agent.add_capability(pattern_capability)
                
            # Add tools
            for db_tool in db_agent.tools:
                tool = AgentTool(
                    name=db_tool.name,
                    description=db_tool.description or "",
                    schema=db_tool.schema,
                    function=db_tool.function_name,
                    auth_required=db_tool.requires_auth
                )
                agent.add_tool(tool)
                
            # Add entity definitions
            for db_entity in db_agent.entity_definitions:
                entity = EntityDefinition(
                    name=db_entity.name,
                    entity_type=db_entity.entity_type,
                    description=db_entity.description,
                    validation_regex=db_entity.validation_regex
                )
                
                # Add enum values if available
                for enum_value in db_entity.enum_values:
                    entity.add_enum_value(
                        value=enum_value.value,
                        description=enum_value.description
                    )
                    
                agent.add_entity_definition(entity)
                
            # Add domain examples if available
            # (This would require extending the database schema)
            
            # Add any configuration
            if hasattr(db_agent, 'llm_config'):
                agent.set_llm_configuration(db_agent.llm_config or {})
                
            # Add response templates if available
            for db_template in getattr(db_agent, 'response_templates', []):
                agent.add_response_template(
                    name=db_template.name,
                    template=db_template.template_text
                )
                
            return agent
        except Exception as e:
            logger.error(f"Error converting agent {db_agent.name}: {str(e)}")
            return None
            
    async def get_agent_by_id(self, agent_id: str) -> Optional[AgentDefinition]:
        """
        Get an agent by ID from the vector store.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            AgentDefinition or None if not found
        """
        if not self.vector_store:
            logger.error("Vector store not initialized")
            return None
            
        if agent_id in self.vector_store.agent_data:
            return self.vector_store.agent_data[agent_id]
            
        return None