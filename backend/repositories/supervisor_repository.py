"""
Repository for accessing supervisor configurations from the database.

This module implements the data access layer for supervisor definitions and agent mappings.
"""
import uuid
import logging
from typing import List, Dict, Any, Optional, Union, Tuple, TypeVar, Type

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from backend.database.agent_schema import (
    SupervisorConfiguration, 
    SupervisorAgentMapping,
    AgentDefinition
)

logger = logging.getLogger(__name__)

# Type variable for model classes
T = TypeVar('T')


class SupervisorRepository:
    """
    Repository for accessing supervisor configurations from the database.
    
    This class provides methods for CRUD operations on supervisor configurations,
    including agent mappings and related entities.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the supervisor repository.
        
        Args:
            db_session: Database session for queries
        """
        self.db_session = db_session
        logger.info("Initialized SupervisorRepository")
    
    async def get_supervisor_by_id(
        self, 
        supervisor_id: Union[str, uuid.UUID],
        include_mappings: bool = True
    ) -> Optional[SupervisorConfiguration]:
        """
        Get a supervisor configuration by ID.
        
        Args:
            supervisor_id: ID of the supervisor
            include_mappings: Whether to include agent mappings
            
        Returns:
            Supervisor configuration or None if not found
        """
        try:
            # Convert string ID to UUID if necessary
            if isinstance(supervisor_id, str):
                supervisor_id = uuid.UUID(supervisor_id)
            
            # Build query
            query = select(SupervisorConfiguration).where(
                SupervisorConfiguration.id == supervisor_id
            )
            
            # Include mappings if requested
            if include_mappings:
                query = query.options(
                    selectinload(SupervisorConfiguration.agent_mappings)
                    .joinedload(SupervisorAgentMapping.agent)
                )
            
            # Execute query
            result = await self.db_session.execute(query)
            return result.scalars().first()
            
        except Exception as e:
            logger.error(f"Error getting supervisor by ID: {str(e)}", exc_info=True)
            return None
    
    async def get_active_supervisors(self) -> List[SupervisorConfiguration]:
        """
        Get all active supervisor configurations.
        
        Returns:
            List of active supervisor configurations
        """
        try:
            # Build query for active supervisors
            query = select(SupervisorConfiguration).where(
                SupervisorConfiguration.status == "active"
            ).order_by(
                SupervisorConfiguration.created_at.desc()
            )
            
            # Execute query
            result = await self.db_session.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"Error getting active supervisors: {str(e)}", exc_info=True)
            return []
    
    async def create_supervisor(
        self,
        name: str,
        description: Optional[str] = None,
        routing_strategy: str = "vector_search",
        model_name: str = "gpt-4o",
        temperature: float = 0.2,
        routing_prompt: Optional[str] = None,
        nodes: Optional[Dict[str, Any]] = None,
        edges: Optional[Dict[str, Any]] = None,
        edge_conditions: Optional[Dict[str, Any]] = None,
        entry_node: Optional[str] = None,
        pattern_prioritization: bool = True,
        status: str = "active"
    ) -> Optional[SupervisorConfiguration]:
        """
        Create a new supervisor configuration.
        
        Args:
            name: Name of the supervisor
            description: Optional description
            routing_strategy: Routing strategy to use
            model_name: LLM model to use
            temperature: Temperature for LLM calls
            routing_prompt: Prompt for routing decisions
            nodes: Node configurations
            edges: Edge configurations
            edge_conditions: Edge condition configurations
            entry_node: Entry node identifier
            pattern_prioritization: Whether to prioritize pattern matching
            status: Status of the supervisor ('active', 'draft', 'inactive')
            
        Returns:
            Created supervisor configuration or None if creation fails
        """
        try:
            # Create default empty dicts
            nodes = nodes or {}
            edges = edges or {}
            edge_conditions = edge_conditions or {}
            
            # Use 'router' as default entry node if none specified
            entry_node = entry_node or "router"
            
            # Create supervisor configuration
            supervisor = SupervisorConfiguration(
                name=name,
                description=description,
                routing_strategy=routing_strategy,
                model_name=model_name,
                temperature=temperature,
                routing_prompt=routing_prompt,
                nodes=nodes,
                edges=edges,
                edge_conditions=edge_conditions,
                entry_node=entry_node,
                pattern_prioritization=pattern_prioritization,
                status=status
            )
            
            # Add to database
            self.db_session.add(supervisor)
            await self.db_session.flush()
            await self.db_session.commit()
            
            return supervisor
            
        except Exception as e:
            logger.error(f"Error creating supervisor: {str(e)}", exc_info=True)
            await self.db_session.rollback()
            return None
    
    async def update_supervisor(
        self,
        supervisor_id: Union[str, uuid.UUID],
        **update_data
    ) -> Optional[SupervisorConfiguration]:
        """
        Update a supervisor configuration.
        
        Args:
            supervisor_id: ID of the supervisor to update
            **update_data: Fields to update
            
        Returns:
            Updated supervisor or None if update fails
        """
        try:
            # Convert string ID to UUID if necessary
            if isinstance(supervisor_id, str):
                supervisor_id = uuid.UUID(supervisor_id)
            
            # Get the supervisor
            supervisor = await self.get_supervisor_by_id(supervisor_id, include_mappings=False)
            if not supervisor:
                logger.warning(f"Supervisor {supervisor_id} not found for update")
                return None
            
            # Update fields
            for key, value in update_data.items():
                if hasattr(supervisor, key):
                    setattr(supervisor, key, value)
            
            # Commit changes
            await self.db_session.commit()
            
            return supervisor
            
        except Exception as e:
            logger.error(f"Error updating supervisor: {str(e)}", exc_info=True)
            await self.db_session.rollback()
            return None
    
    async def add_agent_mapping(
        self,
        supervisor_id: Union[str, uuid.UUID],
        agent_id: Union[str, uuid.UUID],
        node_id: str,
        execution_order: int = 0,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[SupervisorAgentMapping]:
        """
        Add an agent mapping to a supervisor.
        
        Args:
            supervisor_id: ID of the supervisor
            agent_id: ID of the agent
            node_id: ID of the node in the supervisor graph
            execution_order: Order of execution
            config: Optional configuration for the mapping
            
        Returns:
            Created mapping or None if creation fails
        """
        try:
            # Convert string IDs to UUIDs if necessary
            if isinstance(supervisor_id, str):
                supervisor_id = uuid.UUID(supervisor_id)
            if isinstance(agent_id, str):
                agent_id = uuid.UUID(agent_id)
            
            # Check if mapping already exists
            query = select(SupervisorAgentMapping).where(
                and_(
                    SupervisorAgentMapping.supervisor_id == supervisor_id,
                    SupervisorAgentMapping.agent_id == agent_id,
                    SupervisorAgentMapping.node_id == node_id
                )
            )
            result = await self.db_session.execute(query)
            existing_mapping = result.scalars().first()
            
            if existing_mapping:
                logger.info(f"Mapping already exists for supervisor={supervisor_id}, agent={agent_id}, node={node_id}")
                # Update existing mapping
                if config is not None:
                    existing_mapping.config = config
                existing_mapping.execution_order = execution_order
                await self.db_session.commit()
                return existing_mapping
            
            # Create new mapping
            mapping = SupervisorAgentMapping(
                supervisor_id=supervisor_id,
                agent_id=agent_id,
                node_id=node_id,
                execution_order=execution_order,
                config=config or {}
            )
            
            # Add to database
            self.db_session.add(mapping)
            await self.db_session.flush()
            await self.db_session.commit()
            
            return mapping
            
        except Exception as e:
            logger.error(f"Error adding agent mapping: {str(e)}", exc_info=True)
            await self.db_session.rollback()
            return None
    
    async def remove_agent_mapping(
        self,
        supervisor_id: Union[str, uuid.UUID],
        agent_id: Union[str, uuid.UUID],
        node_id: Optional[str] = None
    ) -> bool:
        """
        Remove an agent mapping from a supervisor.
        
        Args:
            supervisor_id: ID of the supervisor
            agent_id: ID of the agent
            node_id: Optional node ID to specifically target
            
        Returns:
            True if removal was successful
        """
        try:
            # Convert string IDs to UUIDs if necessary
            if isinstance(supervisor_id, str):
                supervisor_id = uuid.UUID(supervisor_id)
            if isinstance(agent_id, str):
                agent_id = uuid.UUID(agent_id)
            
            # Build query
            conditions = [
                SupervisorAgentMapping.supervisor_id == supervisor_id,
                SupervisorAgentMapping.agent_id == agent_id
            ]
            
            if node_id:
                conditions.append(SupervisorAgentMapping.node_id == node_id)
            
            # Delete mappings
            query = select(SupervisorAgentMapping).where(and_(*conditions))
            result = await self.db_session.execute(query)
            mappings = result.scalars().all()
            
            for mapping in mappings:
                await self.db_session.delete(mapping)
            
            await self.db_session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error removing agent mapping: {str(e)}", exc_info=True)
            await self.db_session.rollback()
            return False
    
    async def create_default_supervisor(self) -> Optional[SupervisorConfiguration]:
        """
        Create a default supervisor configuration with a standard agent workflow.
        
        Returns:
            Created supervisor or None if creation fails
        """
        try:
            # Define default nodes
            nodes = {
                "router": {
                    "type": "router",
                    "name": "Request Router",
                    "description": "Routes requests to appropriate agents",
                    "pattern_first": True
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
                },
                "memory_store": {
                    "type": "custom",
                    "custom_type": "memory_store",
                    "name": "Memory Store",
                    "description": "Stores conversation in memory"
                }
            }
            
            # Define default edges
            edges = {
                "router": [
                    {"target": "agent_executor"}
                ],
                "agent_executor": [
                    {"target": "guardrails"}
                ],
                "guardrails": [
                    {"target": "memory_store"}
                ],
                "memory_store": [
                    {"target": "__end__"}
                ]
            }
            
            # Create supervisor
            supervisor = await self.create_supervisor(
                name="Default Supervisor",
                description="Default supervisor with standard agent workflow",
                routing_strategy="vector_search",
                model_name="gpt-4o",
                temperature=0.2,
                nodes=nodes,
                edges=edges,
                entry_node="router",
                pattern_prioritization=True
            )
            
            if not supervisor:
                logger.error("Failed to create default supervisor")
                return None
            
            logger.info(f"Created default supervisor with ID {supervisor.id}")
            return supervisor
            
        except Exception as e:
            logger.error(f"Error creating default supervisor: {str(e)}", exc_info=True)
            return None