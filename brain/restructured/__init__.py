"""
Restructured orchestration system for the Staples Brain.
This package provides an improved orchestration system with better modularity and testability.
"""
from typing import Optional, Dict, Any, List
import logging

from brain.restructured.config import OrchestratorConfig, IntentMappingConfig
from brain.restructured.memory import OrchestrationMemory
from brain.restructured.confidence import ConfidenceScorer
from brain.restructured.registry import AgentRegistry
from brain.restructured.topic_detection import TopicChangeDetector, create_default_topic_detector
from brain.restructured.logging_utils import OrchestrationLogger
from brain.restructured.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


def create_orchestration_system(llm=None, agent_types=None, config_module=None) -> AgentOrchestrator:
    """
    Create a complete orchestration system with all necessary components.
    
    Args:
        llm: Language model to use for agents
        agent_types: List of agent type identifiers to initialize
        config_module: Module containing configuration constants
        
    Returns:
        Initialized orchestration system
    """
    try:
        # Create the agent registry
        registry = AgentRegistry()
        
        # Register agents
        if llm and agent_types:
            # Create default agent factory registration
            from agents.base_agent import BaseAgent
            for agent_type in agent_types:
                # Use a lambda to capture the current value of agent_type
                factory = lambda llm_instance, agent_type=agent_type: BaseAgent.create_agent(agent_type, llm_instance)
                registry.register_factory(agent_type, factory)
                
            # Create and register all requested agents
            for agent_type in agent_types:
                try:
                    agent = BaseAgent.create_agent(agent_type, llm)
                    registry.register(agent)
                    logger.info(f"Created and registered agent: {agent.name}")
                except Exception as e:
                    logger.error(f"Error creating agent {agent_type}: {str(e)}")
        
        # Create configuration objects
        if config_module:
            orchestrator_config = OrchestratorConfig.from_constants(config_module)
            intent_mapping = IntentMappingConfig.from_constants(config_module)
        else:
            orchestrator_config = OrchestratorConfig()
            intent_mapping = IntentMappingConfig({})
        
        # Create topic detector with intent mapping
        topic_detector = create_default_topic_detector(intent_mapping.intent_mapping)
        
        # Create enhanced logger
        orch_logger = OrchestrationLogger()
        
        # Create and return the orchestrator
        orchestrator = AgentOrchestrator(
            agent_registry=registry,
            config=orchestrator_config,
            intent_mapping=intent_mapping,
            topic_detector=topic_detector,
            logger=orch_logger
        )
        
        agent_count = len(registry.get_all())
        logger.info(f"Created orchestration system with {agent_count} agents")
        
        return orchestrator
    
    except Exception as e:
        logger.error(f"Error creating orchestration system: {str(e)}", exc_info=True)
        raise