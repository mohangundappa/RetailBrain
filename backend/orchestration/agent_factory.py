"""
Factory for creating optimized agent selection components.
This module provides factories for creating the optimized router and related components.
"""
import logging
from typing import Dict, List, Optional, Any, Union

from sqlalchemy.ext.asyncio import AsyncSession

from backend.orchestration.agent_definition import AgentDefinition
from backend.orchestration.agent_definition import PatternCapability, AgentTool, EntityDefinition as OptEntityDefinition
from backend.orchestration.embedding_service import EmbeddingService
from backend.orchestration.agent_vector_store import AgentVectorStore
from backend.orchestration.agent_router import OptimizedAgentRouter

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
            # First, create and load hardcoded test agents for backwards compatibility
            hardcoded_count = await self._load_hardcoded_test_agents()
            logger.info(f"Loaded {hardcoded_count} hardcoded agents for testing")
            
            # Now load agents from the database
            from backend.repositories.agent_repository import AgentRepository
            agent_repository = AgentRepository(self.db_session)
            
            # Get all active agents from the database
            logger.info("Loading agents from database...")
            db_agents = await agent_repository.get_all_active_agents()
            
            # Count of database agents successfully loaded
            db_count = 0
            
            # Load and index each agent
            for db_agent in db_agents:
                try:
                    # Convert database model to internal representation
                    agent = self._convert_db_agent(db_agent)
                    
                    if agent:
                        # Index the agent in vector store
                        success = await self.vector_store.index_agent(agent)
                        if success:
                            db_count += 1
                            logger.info(f"Indexed agent from database: {agent.name} (ID: {agent.id})")
                        else:
                            logger.warning(f"Failed to index agent: {agent.name} (ID: {agent.id})")
                except Exception as agent_error:
                    logger.error(f"Error loading agent {getattr(db_agent, 'name', 'unknown')}: {str(agent_error)}")
            
            # Log combined results
            total_count = hardcoded_count + db_count
            logger.info(f"Loaded total of {total_count} agents ({hardcoded_count} hardcoded, {db_count} from database)")
            
            return total_count
        except Exception as e:
            logger.error(f"Error loading agents from database: {str(e)}", exc_info=True)
            return 0
            
    async def _load_hardcoded_test_agents(self) -> int:
        """
        Load hardcoded test agents for testing purposes.
        
        Returns:
            Number of hardcoded agents loaded
        """
        if not self.vector_store:
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
                entity_type="order_number",
                description="User's order number",
                validation_regex=r"[A-Z0-9#-]{3,15}"
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
            
            return count
        except Exception as e:
            logger.error(f"Error creating hardcoded test agents: {str(e)}")
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
            
    def list_available_agents(self) -> List[Dict[str, Any]]:
        """
        Get a list of all available agents in the vector store.
        
        Returns:
            List of agent information dictionaries
        """
        if not self.vector_store:
            logger.error("Vector store not initialized")
            return []
            
        agents = []
        for agent_id, agent in self.vector_store.agent_data.items():
            agents.append({
                "id": agent_id,
                "name": agent.name,
                "description": agent.description,
                "status": agent.status,
                "version": agent.version,
                "is_system": agent.is_system,
                "type": getattr(agent, "agent_type", "standard")
            })
            
        return agents