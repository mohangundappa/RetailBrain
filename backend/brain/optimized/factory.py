"""
Factory for creating optimized agent selection components.
This module provides factories for creating the optimized router and related components.
"""
import logging
from typing import Dict, List, Optional, Any, Union

from sqlalchemy.ext.asyncio import AsyncSession

from backend.brain.optimized.agent_definition import AgentDefinition, PatternCapability, AgentTool, EntityDefinition as OptEntityDefinition
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
        For testing purposes, this currently creates hardcoded agents.
        
        Returns:
            Number of agents loaded
        """
        if not self.vector_store:
            logger.error("Vector store not initialized")
            return 0
            
        try:
            # Create and index some hardcoded test agents
            count = 0
            
            # Create password reset agent
            password_agent = AgentDefinition(
                id="reset_password_id",
                name="Reset Password Agent",
                description="Helps users reset their password and regain access to their accounts",
                version=1
            )
            password_agent.status = "active"
            password_agent.is_system = True
            
            # Add patterns
            pattern_capability = PatternCapability()
            pattern_capability.add_pattern(
                pattern_type="regex",
                pattern_value=r"(?i).*\b(password|reset|forgot|change|login)\b.*",
                confidence_boost=0.8
            )
            password_agent.add_capability(pattern_capability)
            
            # Add sample entity definitions
            email_entity = OptEntityDefinition(
                name="email",
                entity_type="email",
                description="User's email address",
                validation_regex=r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
            )
            password_agent.add_entity_definition(email_entity)
            
            # Add sample response templates
            password_agent.add_response_template(
                name="reset_instructions",
                template="To reset your password, please check your email at {{email}} for instructions."
            )
            
            # Index the agent
            success = await self.vector_store.index_agent(password_agent)
            if success:
                count += 1
                
            # Create order tracking agent
            order_agent = AgentDefinition(
                id="order_tracking_id",
                name="Order Tracking Agent",
                description="Helps users track their orders and get shipping updates",
                version=1
            )
            order_agent.status = "active"
            order_agent.is_system = True
            
            # Add patterns
            pattern_capability = PatternCapability()
            pattern_capability.add_pattern(
                pattern_type="regex",
                pattern_value=r"(?i).*\b(order|track|package|shipping|delivery|status)\b.*",
                confidence_boost=0.8
            )
            order_agent.add_capability(pattern_capability)
            
            # Add sample entity definitions
            order_number = OptEntityDefinition(
                name="order_number",
                entity_type="string",
                description="User's order number",
                validation_regex=r"^[A-Z0-9]{8,12}$"
            )
            order_agent.add_entity_definition(order_number)
            
            # Add sample response templates
            order_agent.add_response_template(
                name="tracking_info",
                template="Your order {{order_number}} is currently {{status}} and will arrive on {{delivery_date}}."
            )
            
            # Index the agent
            success = await self.vector_store.index_agent(order_agent)
            if success:
                count += 1
                
            logger.info(f"Loaded {count} hardcoded agents for testing")
            return count
        except Exception as e:
            logger.error(f"Error creating test agents: {str(e)}")
            return 0
            
    def _convert_db_agent(self, db_agent: Any) -> Optional[AgentDefinition]:
        """
        Convert a database agent to an internal agent model.
        This is a synchronous method to avoid async context issues.
        
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
                
            # Add entity definitions via entity mappings
            for mapping in db_agent.entity_mappings:
                db_entity = mapping.entity
                entity = OptEntityDefinition(
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