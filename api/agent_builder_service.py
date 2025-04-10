"""
Agent Builder Service for Staples Brain.

This service provides integration between the Agent Builder UI and 
the Staples Brain Core Services architecture.
"""
import os
import re
import logging
import json
from typing import Dict, Any, List, Optional, Union, Type
from datetime import datetime

from flask import jsonify, request, abort

from brain.core_services.base_service import CoreService, service_registry
from brain.core_services.tool_service import tool_service
from agents.base_agent import BaseAgent
from utils.observability import record_error, record_api_call
from utils.langsmith_utils import langsmith_trace

# Import database models
from models import db, CustomAgent, AgentComponent, ComponentConnection, AgentTemplate

logger = logging.getLogger(__name__)

class AgentBuilderService(CoreService):
    """
    Service for managing custom agent creation and configuration.
    
    This service provides the bridge between the Agent Builder UI and
    the underlying Core Services architecture.
    """
    
    def __init__(self):
        """Initialize the agent builder service."""
        self.initialized = False
        self.health_status = {"healthy": False, "last_check": None, "details": {}}
        self.brain_core = None
        self.templates = {}
        self.component_types = {}
        
    def initialize(self) -> bool:
        """
        Initialize the agent builder service.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing Agent Builder Service")
            
            # Get brain core from service registry
            self.brain_core = service_registry.get_service("brain_core")
            if not self.brain_core:
                logger.error("Brain core not found in service registry")
                self.health_status["healthy"] = False
                self.health_status["details"] = {"error": "Brain core not found"}
                return False
            
            # Load available templates and component types
            self._load_templates()
            self._load_component_types()
            
            # Register with service registry
            service_registry.register("agent_builder_service", self, {"type": "api"})
            
            # Initialize database tables if they don't exist
            with db.session.begin():
                db.create_all()
            
            self.initialized = True
            self.health_status["healthy"] = True
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {
                "template_count": len(self.templates),
                "component_type_count": len(self.component_types)
            }
            
            logger.info(f"Agent Builder Service initialized with {len(self.templates)} templates")
            return True
            
        except Exception as e:
            error_message = f"Failed to initialize agent builder service: {str(e)}"
            logger.error(error_message)
            record_error("agent_builder_init", error_message)
            
            self.health_status["healthy"] = False
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {"error": error_message}
            
            return False
    
    def _load_templates(self) -> None:
        """Load available agent templates from the database."""
        try:
            # Load from database
            db_templates = AgentTemplate.query.all()
            
            if db_templates:
                # Convert to dictionary for easy access
                for template in db_templates:
                    self.templates[template.id] = {
                        "id": template.id,
                        "name": template.name,
                        "description": template.description,
                        "category": template.category,
                        "icon": template.icon,
                        "configuration": json.loads(template.configuration) if template.configuration else {},
                        "created_at": template.created_at.isoformat() if template.created_at else None,
                        "updated_at": template.updated_at.isoformat() if template.updated_at else None
                    }
            else:
                # Create default templates if none exist
                self._create_default_templates()
                
            logger.info(f"Loaded {len(self.templates)} agent templates")
            
        except Exception as e:
            logger.error(f"Error loading templates: {str(e)}")
            record_error("template_loading", str(e))
    
    def _create_default_templates(self) -> None:
        """Create default agent templates."""
        try:
            # Define default templates
            default_templates = [
                {
                    "name": "Customer Support Agent",
                    "description": "General purpose customer support agent with FAQ capabilities",
                    "category": "customer_support",
                    "icon": "headset",
                    "configuration": {
                        "system_prompt": "You are a helpful customer support agent for Staples. Answer questions professionally and accurately.",
                        "tools": ["find_store_locations", "get_order_status", "search_products"],
                        "fields": ["name", "description", "prompt_template"]
                    }
                },
                {
                    "name": "Order Tracking Specialist",
                    "description": "Specialized agent for order tracking and shipment inquiries",
                    "category": "orders",
                    "icon": "package",
                    "configuration": {
                        "system_prompt": "You are an order tracking specialist for Staples. Help customers track their orders and provide shipment information.",
                        "tools": ["get_order_status", "get_tracking_info"],
                        "fields": ["name", "description", "prompt_template"]
                    }
                },
                {
                    "name": "Store Finder",
                    "description": "Agent that helps customers find nearby Staples stores",
                    "category": "locations",
                    "icon": "map-pin",
                    "configuration": {
                        "system_prompt": "You are a store finder assistant for Staples. Help customers locate the nearest Staples stores and provide information about services offered.",
                        "tools": ["find_store_locations"],
                        "fields": ["name", "description", "prompt_template"]
                    }
                }
            ]
            
            # Save to database
            for template_data in default_templates:
                template = AgentTemplate(
                    name=template_data["name"],
                    description=template_data["description"],
                    category=template_data["category"],
                    icon=template_data["icon"],
                    configuration=json.dumps(template_data["configuration"])
                )
                db.session.add(template)
                
                # Add to in-memory cache
                self.templates[template.id] = {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "icon": template.icon,
                    "configuration": template_data["configuration"],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            
            db.session.commit()
            logger.info(f"Created {len(default_templates)} default templates")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating default templates: {str(e)}")
            record_error("default_template_creation", str(e))
    
    def _load_component_types(self) -> None:
        """Load available component types for custom agents."""
        try:
            # Define available component types
            self.component_types = {
                "prompt_template": {
                    "name": "Prompt Template",
                    "description": "Customize the agent's prompt template",
                    "icon": "file-text",
                    "fields": [
                        {
                            "name": "template_text",
                            "type": "textarea",
                            "label": "Template Text",
                            "description": "The prompt template text with variable placeholders",
                            "required": True
                        },
                        {
                            "name": "variables",
                            "type": "array",
                            "label": "Template Variables",
                            "description": "Variables used in the template",
                            "required": False
                        }
                    ],
                    "default_config": {
                        "template_text": "You are a helpful Staples assistant. The customer query is: {query}",
                        "variables": ["query"]
                    }
                },
                "tool_config": {
                    "name": "Tool Configuration",
                    "description": "Configure tools available to the agent",
                    "icon": "tool",
                    "fields": [
                        {
                            "name": "tools",
                            "type": "multiselect",
                            "label": "Available Tools",
                            "description": "Tools that the agent can use",
                            "required": True,
                            "options": self._get_available_tool_options()
                        }
                    ],
                    "default_config": {
                        "tools": []
                    }
                },
                "entity_collector": {
                    "name": "Entity Collector",
                    "description": "Configure entities the agent should collect from users",
                    "icon": "list",
                    "fields": [
                        {
                            "name": "entities",
                            "type": "array",
                            "label": "Entities to Collect",
                            "description": "Required information to collect from the user",
                            "required": True,
                            "item_template": {
                                "name": "",
                                "description": "",
                                "required": True,
                                "validation_pattern": ""
                            }
                        }
                    ],
                    "default_config": {
                        "entities": []
                    }
                },
                "guardrail_config": {
                    "name": "Guardrail Configuration",
                    "description": "Configure guardrails for agent responses",
                    "icon": "shield",
                    "fields": [
                        {
                            "name": "banned_phrases",
                            "type": "array",
                            "label": "Banned Phrases",
                            "description": "Phrases that should never appear in responses",
                            "required": False
                        },
                        {
                            "name": "prohibited_topics",
                            "type": "object",
                            "label": "Prohibited Topics",
                            "description": "Topics the agent should not discuss",
                            "required": False
                        },
                        {
                            "name": "service_boundaries",
                            "type": "object",
                            "label": "Service Boundaries",
                            "description": "Services the agent can and cannot offer",
                            "required": False
                        }
                    ],
                    "default_config": {
                        "banned_phrases": [],
                        "prohibited_topics": {},
                        "service_boundaries": {
                            "allowed": [],
                            "not_allowed": []
                        }
                    }
                }
            }
            
            logger.info(f"Loaded {len(self.component_types)} component types")
            
        except Exception as e:
            logger.error(f"Error loading component types: {str(e)}")
            record_error("component_type_loading", str(e))
    
    def _get_available_tool_options(self) -> List[Dict[str, str]]:
        """
        Get available tool options for the tool configuration component.
        
        Returns:
            List of tool options with value and label
        """
        if not tool_service:
            return []
            
        try:
            options = []
            for tool in tool_service.list_tools():
                options.append({
                    "value": tool["name"],
                    "label": tool["name"].replace("_", " ").title(),
                    "description": tool["description"]
                })
            return options
        except Exception as e:
            logger.error(f"Error getting tool options: {str(e)}")
            return []
    
    @langsmith_trace(run_type="chain", name="get_templates", tags=["agent_builder"])
    def get_templates(self) -> List[Dict[str, Any]]:
        """
        Get all available agent templates.
        
        Returns:
            List of agent templates
        """
        record_api_call(system="agent_builder", endpoint="get_templates")
        
        if not self.initialized:
            logger.error("Agent Builder Service not initialized")
            return []
            
        try:
            # Return list of templates
            return list(self.templates.values())
            
        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}")
            record_error("get_templates", str(e))
            return []
    
    @langsmith_trace(run_type="chain", name="get_template_by_id", tags=["agent_builder"])
    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a template by ID.
        
        Args:
            template_id: The ID of the template to get
            
        Returns:
            Template data or None if not found
        """
        record_api_call(system="agent_builder", endpoint="get_template_by_id")
        
        if not self.initialized:
            logger.error("Agent Builder Service not initialized")
            return None
            
        try:
            # Return template if it exists
            return self.templates.get(template_id)
            
        except Exception as e:
            logger.error(f"Error getting template {template_id}: {str(e)}")
            record_error("get_template_by_id", str(e))
            return None
    
    @langsmith_trace(run_type="chain", name="get_component_types", tags=["agent_builder"])
    def get_component_types(self) -> Dict[str, Any]:
        """
        Get all available component types.
        
        Returns:
            Dictionary of component types
        """
        record_api_call(system="agent_builder", endpoint="get_component_types")
        
        if not self.initialized:
            logger.error("Agent Builder Service not initialized")
            return {}
            
        try:
            # Return component types
            return self.component_types
            
        except Exception as e:
            logger.error(f"Error getting component types: {str(e)}")
            record_error("get_component_types", str(e))
            return {}
    
    @langsmith_trace(run_type="chain", name="create_custom_agent", tags=["agent_builder"])
    def create_custom_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new custom agent.
        
        Args:
            agent_data: Data for the new agent
            
        Returns:
            Dictionary with result of creation
        """
        record_api_call(system="agent_builder", endpoint="create_custom_agent")
        
        if not self.initialized:
            logger.error("Agent Builder Service not initialized")
            return {"success": False, "error": "Agent Builder Service not initialized"}
            
        try:
            # Validate required fields
            required_fields = ["name", "description"]
            for field in required_fields:
                if field not in agent_data:
                    return {"success": False, "error": f"Missing required field: {field}"}
            
            # Create custom agent record
            custom_agent = CustomAgent(
                name=agent_data["name"],
                description=agent_data["description"],
                is_active=agent_data.get("is_active", True),
                configuration=json.dumps(agent_data.get("configuration", {})),
                template_id=agent_data.get("template_id")
            )
            
            db.session.add(custom_agent)
            db.session.commit()
            
            logger.info(f"Created custom agent: {custom_agent.name} (ID: {custom_agent.id})")
            
            # Return success response
            return {
                "success": True,
                "agent_id": custom_agent.id,
                "name": custom_agent.name,
                "message": f"Custom agent '{custom_agent.name}' created successfully"
            }
            
        except Exception as e:
            db.session.rollback()
            error_message = f"Error creating custom agent: {str(e)}"
            logger.error(error_message)
            record_error("create_custom_agent", error_message)
            
            return {"success": False, "error": error_message}
    
    @langsmith_trace(run_type="chain", name="update_custom_agent", tags=["agent_builder"])
    def update_custom_agent(self, agent_id: int, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing custom agent.
        
        Args:
            agent_id: ID of the agent to update
            agent_data: Updated agent data
            
        Returns:
            Dictionary with result of update
        """
        record_api_call(system="agent_builder", endpoint="update_custom_agent")
        
        if not self.initialized:
            logger.error("Agent Builder Service not initialized")
            return {"success": False, "error": "Agent Builder Service not initialized"}
            
        try:
            # Get the existing agent
            custom_agent = CustomAgent.query.get(agent_id)
            if not custom_agent:
                return {"success": False, "error": f"Custom agent with ID {agent_id} not found"}
            
            # Update fields
            if "name" in agent_data:
                custom_agent.name = agent_data["name"]
                
            if "description" in agent_data:
                custom_agent.description = agent_data["description"]
                
            if "is_active" in agent_data:
                custom_agent.is_active = agent_data["is_active"]
                
            if "configuration" in agent_data:
                custom_agent.configuration = json.dumps(agent_data["configuration"])
                
            if "template_id" in agent_data:
                custom_agent.template_id = agent_data["template_id"]
            
            custom_agent.updated_at = datetime.now()
            db.session.commit()
            
            logger.info(f"Updated custom agent: {custom_agent.name} (ID: {custom_agent.id})")
            
            # Return success response
            return {
                "success": True,
                "agent_id": custom_agent.id,
                "name": custom_agent.name,
                "message": f"Custom agent '{custom_agent.name}' updated successfully"
            }
            
        except Exception as e:
            db.session.rollback()
            error_message = f"Error updating custom agent: {str(e)}"
            logger.error(error_message)
            record_error("update_custom_agent", error_message)
            
            return {"success": False, "error": error_message}
    
    @langsmith_trace(run_type="chain", name="delete_custom_agent", tags=["agent_builder"])
    def delete_custom_agent(self, agent_id: int) -> Dict[str, Any]:
        """
        Delete a custom agent.
        
        Args:
            agent_id: ID of the agent to delete
            
        Returns:
            Dictionary with result of deletion
        """
        record_api_call(system="agent_builder", endpoint="delete_custom_agent")
        
        if not self.initialized:
            logger.error("Agent Builder Service not initialized")
            return {"success": False, "error": "Agent Builder Service not initialized"}
            
        try:
            # Get the existing agent
            custom_agent = CustomAgent.query.get(agent_id)
            if not custom_agent:
                return {"success": False, "error": f"Custom agent with ID {agent_id} not found"}
            
            # Store name for response
            agent_name = custom_agent.name
            
            # Delete components and connections
            AgentComponent.query.filter_by(agent_id=agent_id).delete()
            ComponentConnection.query.filter_by(agent_id=agent_id).delete()
            
            # Delete the agent
            db.session.delete(custom_agent)
            db.session.commit()
            
            logger.info(f"Deleted custom agent: {agent_name} (ID: {agent_id})")
            
            # Return success response
            return {
                "success": True,
                "message": f"Custom agent '{agent_name}' deleted successfully"
            }
            
        except Exception as e:
            db.session.rollback()
            error_message = f"Error deleting custom agent: {str(e)}"
            logger.error(error_message)
            record_error("delete_custom_agent", error_message)
            
            return {"success": False, "error": error_message}
    
    @langsmith_trace(run_type="chain", name="get_custom_agents", tags=["agent_builder"])
    def get_custom_agents(self) -> List[Dict[str, Any]]:
        """
        Get all custom agents.
        
        Returns:
            List of custom agents
        """
        record_api_call(system="agent_builder", endpoint="get_custom_agents")
        
        if not self.initialized:
            logger.error("Agent Builder Service not initialized")
            return []
            
        try:
            # Get all custom agents
            agents = CustomAgent.query.all()
            
            # Convert to list of dictionaries
            result = []
            for agent in agents:
                result.append({
                    "id": agent.id,
                    "name": agent.name,
                    "description": agent.description,
                    "is_active": agent.is_active,
                    "configuration": json.loads(agent.configuration) if agent.configuration else {},
                    "template_id": agent.template_id,
                    "created_at": agent.created_at.isoformat() if agent.created_at else None,
                    "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
                })
            
            return result
            
        except Exception as e:
            error_message = f"Error getting custom agents: {str(e)}"
            logger.error(error_message)
            record_error("get_custom_agents", error_message)
            
            return []
    
    @langsmith_trace(run_type="chain", name="get_custom_agent_by_id", tags=["agent_builder"])
    def get_custom_agent_by_id(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a custom agent by ID.
        
        Args:
            agent_id: ID of the agent to get
            
        Returns:
            Custom agent data or None if not found
        """
        record_api_call(system="agent_builder", endpoint="get_custom_agent_by_id")
        
        if not self.initialized:
            logger.error("Agent Builder Service not initialized")
            return None
            
        try:
            # Get the agent
            agent = CustomAgent.query.get(agent_id)
            if not agent:
                return None
            
            # Convert to dictionary
            result = {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "is_active": agent.is_active,
                "configuration": json.loads(agent.configuration) if agent.configuration else {},
                "template_id": agent.template_id,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
            }
            
            # Get components and connections
            components = AgentComponent.query.filter_by(agent_id=agent_id).all()
            connections = ComponentConnection.query.filter_by(agent_id=agent_id).all()
            
            # Add components to result
            result["components"] = []
            for component in components:
                result["components"].append({
                    "id": component.id,
                    "type": component.component_type,
                    "name": component.name,
                    "configuration": json.loads(component.configuration) if component.configuration else {},
                    "position_x": component.position_x,
                    "position_y": component.position_y
                })
            
            # Add connections to result
            result["connections"] = []
            for connection in connections:
                result["connections"].append({
                    "id": connection.id,
                    "source_id": connection.source_component_id,
                    "target_id": connection.target_component_id,
                    "configuration": json.loads(connection.configuration) if connection.configuration else {}
                })
            
            return result
            
        except Exception as e:
            error_message = f"Error getting custom agent {agent_id}: {str(e)}"
            logger.error(error_message)
            record_error("get_custom_agent_by_id", error_message)
            
            return None
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service.
        
        Returns:
            Dictionary containing service metadata
        """
        return {
            "name": "agent_builder_service",
            "description": "Service for managing custom agent creation and configuration",
            "version": "1.0.0",
            "initialized": self.initialized,
            "health_status": self.health_status,
            "template_count": len(self.templates),
            "component_type_count": len(self.component_types)
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            # Update health check time
            self.health_status["last_check"] = datetime.now().isoformat()
            
            # Check initialization status
            if not self.initialized:
                self.health_status["healthy"] = False
                self.health_status["details"] = {"error": "Agent Builder Service not initialized"}
                return self.health_status
            
            # Check database connection
            try:
                # Quick query to check database connection
                db.session.execute("SELECT 1").fetchall()
                database_healthy = True
            except Exception as e:
                logger.error(f"Database health check failed: {str(e)}")
                database_healthy = False
            
            # Check brain core connection
            brain_core_healthy = self.brain_core is not None
            
            # Update health status
            self.health_status["healthy"] = database_healthy and brain_core_healthy
            self.health_status["details"] = {
                "database": database_healthy,
                "brain_core": brain_core_healthy,
                "template_count": len(self.templates),
                "component_type_count": len(self.component_types)
            }
            
            return self.health_status
            
        except Exception as e:
            error_message = f"Health check failed: {str(e)}"
            logger.error(error_message)
            
            self.health_status["healthy"] = False
            self.health_status["details"] = {"error": error_message}
            
            return self.health_status


# Create a singleton instance
agent_builder_service = AgentBuilderService()