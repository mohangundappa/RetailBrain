"""
Example usage of the restructured orchestration system.
This module demonstrates how to initialize and use the new orchestration architecture.
"""
import logging
import asyncio
from typing import Dict, Any

# Import the orchestration system
from brain.restructured import create_orchestration_system

# Import constants and existing classes needed for integration
from config import agent_constants
from brain.staples_brain import StaplesBrain

logger = logging.getLogger(__name__)


def initialize_with_existing_brain(brain: StaplesBrain):
    """
    Initialize the restructured orchestration system with an existing brain instance.
    
    Args:
        brain: Existing StaplesBrain instance
        
    Returns:
        New orchestrator instance
    """
    # Create the orchestration system using the brain's LLM and agent types
    agent_types = ["package_tracking", "reset_password", "store_locator"]
    
    orchestrator = create_orchestration_system(
        llm=brain.llm,
        agent_types=agent_types,
        config_module=agent_constants
    )
    
    return orchestrator


async def process_with_new_orchestrator(orchestrator, user_input: str, context: Dict[str, Any]):
    """
    Process a request using the new orchestrator.
    
    Args:
        orchestrator: New orchestrator instance
        user_input: User's request
        context: Context information
        
    Returns:
        Response from the orchestrator
    """
    logger.info(f"Processing request with new orchestrator: {user_input}")
    response = await orchestrator.process_request(user_input, context)
    return response


async def run_comparison(brain: StaplesBrain, user_input: str):
    """
    Run a comparison between old and new orchestration systems.
    
    Args:
        brain: Existing StaplesBrain instance
        user_input: User's request to process
        
    Returns:
        Dictionary with both responses
    """
    # Create session ID and context
    import uuid
    session_id = str(uuid.uuid4())
    context = {"session_id": session_id}
    
    # Initialize new orchestrator
    new_orchestrator = initialize_with_existing_brain(brain)
    
    # Process with both systems
    old_response = await brain.process_request(user_input, context)
    new_response = await new_orchestrator.process_request(user_input, context)
    
    # Compare results
    logger.info("Comparison results:")
    logger.info(f"Old system agent: {old_response.get('selected_agent')}, "
              f"confidence: {old_response.get('confidence', 0.0):.2f}")
    logger.info(f"New system agent: {new_response.get('selected_agent')}, "
              f"confidence: {new_response.get('confidence', 0.0):.2f}")
    
    return {
        "old_response": old_response,
        "new_response": new_response,
        "same_agent": old_response.get('selected_agent') == new_response.get('selected_agent'),
        "input": user_input
    }


def migrate_to_new_orchestrator(brain: StaplesBrain):
    """
    Migrate an existing brain to use the new orchestration system.
    
    Args:
        brain: Existing StaplesBrain instance
        
    Returns:
        Updated brain instance
    """
    # Create new orchestrator
    new_orchestrator = initialize_with_existing_brain(brain)
    
    # Replace the existing orchestrator
    brain.orchestrator = new_orchestrator
    logger.info("Migrated to new orchestration system")
    
    return brain


# Example usage:
#
# async def main():
#     # Initialize the original brain
#     from brain.staples_brain import initialize_staples_brain
#     brain = initialize_staples_brain()
#     
#     # Test with some example queries
#     examples = [
#         "I want to track my package",
#         "Where is the closest store?",
#         "I forgot my password",
#         "Hello, how are you?",
#         "Can you tell me about office chairs?"
#     ]
#     
#     for example in examples:
#         result = await run_comparison(brain, example)
#         print(f"Input: {result['input']}")
#         print(f"Same agent selected: {result['same_agent']}")
#         print()
#     
#     # Optionally migrate the brain to use the new orchestrator
#     brain = migrate_to_new_orchestrator(brain)
# 
# # Run the example
# if __name__ == "__main__":
#     asyncio.run(main())