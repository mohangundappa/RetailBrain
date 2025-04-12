"""
Utility module to seed the agent database with predefined agents.
This migrates hardcoded agent definitions to the database.
"""
import logging
import asyncio
import uuid
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from backend.database.db import engine as default_engine
from backend.database.agent_schema import (
    AgentDefinition, AgentDeployment, AgentComposition,
    LlmAgentConfiguration, RuleAgentConfiguration, RetrievalAgentConfiguration,
    AgentPattern, AgentPatternEmbedding, AgentTool, AgentResponseTemplate
)
from backend.database.entity_schema import (
    EntityDefinition, EntityEnumValue, AgentEntityMapping,
    EntityExtractionPattern, EntityTransformation
)
from backend.config.agent_constants import (
    PACKAGE_TRACKING_AGENT,
    RESET_PASSWORD_AGENT,
    STORE_LOCATOR_AGENT,
    PRODUCT_INFO_AGENT,
    RETURNS_PROCESSING_AGENT
)

logger = logging.getLogger(__name__)


async def check_agent_exists(session: AsyncSession, agent_type: str) -> bool:
    """
    Check if an agent with the given type already exists in the database.
    
    Args:
        session: An async database session
        agent_type: The type of agent to check for
        
    Returns:
        True if the agent exists, False otherwise
    """
    query = select(AgentDefinition).where(AgentDefinition.agent_type == agent_type)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


async def seed_package_tracking_agent(session: AsyncSession) -> None:
    """
    Seed the database with the package tracking agent.
    
    Args:
        session: An async database session
    """
    # Check if agent already exists
    if await check_agent_exists(session, PACKAGE_TRACKING_AGENT):
        logger.info(f"Agent {PACKAGE_TRACKING_AGENT} already exists, skipping")
        return
    
    # Create agent definition
    agent = AgentDefinition(
        name="Package Tracking Agent",
        description="I can help track your orders, check package status, and provide delivery updates for Staples purchases.",
        agent_type=PACKAGE_TRACKING_AGENT,
        status="active",
        is_system=True,
        version=1,
        created_by="system"
    )
    session.add(agent)
    await session.flush()  # To generate the ID
    
    # Create LLM configuration
    llm_config = LlmAgentConfiguration(
        agent_id=agent.id,
        model_name="gpt-4o",
        temperature=0.7,
        max_tokens=500,
        timeout_seconds=15,  # As defined in AGENT_TIMEOUTS
        confidence_threshold=0.75,
        system_prompt=(
            "You are a Staples Customer Service Representative specializing in package tracking. "
            "You help customers track their orders, check delivery status, and solve shipping issues. "
            "Always maintain a professional, helpful tone while representing Staples."
        )
    )
    session.add(llm_config)
    
    # Create agent patterns for detection
    patterns = [
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="order",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="package",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="tracking",
            priority=2,
            confidence_boost=0.15
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="delivery",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="shipment",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="regex",
            pattern_value=r'\b[A-Za-z0-9]{2,}-?[A-Za-z0-9]{2,}\b',  # Order number pattern
            priority=3,
            confidence_boost=0.2
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="semantic",
            pattern_value="I want to track my Staples order",
            priority=2,
            confidence_boost=0.15
        ),
    ]
    for pattern in patterns:
        session.add(pattern)
    
    # Create response templates
    templates = [
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="order_not_found",
            template_content=(
                "We couldn't find an order with the number {order_number} and zip code {zip_code}. "
                "Please check the information and try again, or contact customer service for assistance."
            ),
            template_type="text",
            language="en",
            tone="apologetic",
            version=1
        ),
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="order_found",
            template_content=(
                "Your order {order_number} is {status}. "
                "The estimated delivery is {delivery_date}. "
                "Current location: {current_location}."
            ),
            template_type="text",
            language="en",
            tone="informative",
            version=1
        ),
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="missing_info",
            template_content=(
                "To track your order, I'll need both your order number and zip code. "
                "Please provide the {missing_field}."
            ),
            template_type="text",
            language="en",
            tone="helpful",
            version=1
        ),
    ]
    for template in templates:
        session.add(template)
    
    # Create entity definitions
    # First check if entities already exist
    order_number_query = select(EntityDefinition).where(EntityDefinition.name == "order_number")
    result = await session.execute(order_number_query)
    order_entity = result.scalar_one_or_none()
    
    if not order_entity:
        order_entity = EntityDefinition(
            name="order_number",
            display_name="Order Number",
            description="Your Staples order number",
            entity_type="text",
            validation_regex=r'^[A-Za-z0-9]{2,}-?[A-Za-z0-9]{2,}$',
            is_required=True
        )
        session.add(order_entity)
        await session.flush()
    
    zip_code_query = select(EntityDefinition).where(EntityDefinition.name == "zip_code")
    result = await session.execute(zip_code_query)
    zip_entity = result.scalar_one_or_none()
    
    if not zip_entity:
        zip_entity = EntityDefinition(
            name="zip_code",
            display_name="Zip Code",
            description="The billing zip code associated with your order",
            entity_type="text",
            validation_regex=r'^\d{5}(-\d{4})?$',
            is_required=True
        )
        session.add(zip_entity)
        await session.flush()
    
    # Create entity mappings
    entity_mappings = [
        AgentEntityMapping(
            agent_id=agent.id,
            entity_id=order_entity.id,
            is_required=True,
            extraction_priority=1,
            prompt_for_missing=True,
            prompt_text="Please provide your order number.",
            extraction_method="regex"
        ),
        AgentEntityMapping(
            agent_id=agent.id,
            entity_id=zip_entity.id,
            is_required=True,
            extraction_priority=2,
            prompt_for_missing=True,
            prompt_text="Please provide the zip code associated with your order.",
            extraction_method="regex"
        )
    ]
    for mapping in entity_mappings:
        session.add(mapping)
    
    # Create extraction patterns for entities
    extraction_patterns = [
        EntityExtractionPattern(
            entity_id=order_entity.id,
            pattern_type="regex",
            pattern_value=r'\b[A-Za-z0-9]{2,}-?[A-Za-z0-9]{2,}\b',
            confidence_value=0.8,
            description="Pattern for order numbers like OD1234567 or STB-987654"
        ),
        EntityExtractionPattern(
            entity_id=zip_entity.id,
            pattern_type="regex",
            pattern_value=r'\b\d{5}(-\d{4})?\b',
            confidence_value=0.8,
            description="Pattern for 5-digit or 9-digit zip codes"
        )
    ]
    for pattern in extraction_patterns:
        session.add(pattern)


async def seed_reset_password_agent(session: AsyncSession) -> None:
    """
    Seed the database with the reset password agent.
    
    Args:
        session: An async database session
    """
    # Check if agent already exists
    if await check_agent_exists(session, RESET_PASSWORD_AGENT):
        logger.info(f"Agent {RESET_PASSWORD_AGENT} already exists, skipping")
        return
    
    # Create agent definition
    agent = AgentDefinition(
        name="Reset Password Agent",
        description="I can help you reset your password, recover your account, and guide you through the login process for Staples online services.",
        agent_type=RESET_PASSWORD_AGENT,
        status="active",
        is_system=True,
        version=1,
        created_by="system"
    )
    session.add(agent)
    await session.flush()  # To generate the ID
    
    # Create LLM configuration
    llm_config = LlmAgentConfiguration(
        agent_id=agent.id,
        model_name="gpt-4o",
        temperature=0.5,  # Lower for more precise instructions
        max_tokens=400,
        timeout_seconds=8,  # As defined in AGENT_TIMEOUTS
        confidence_threshold=0.7,
        system_prompt=(
            "You are a Staples Customer Service Representative specializing in account support. "
            "You help customers reset passwords and recover access to their Staples online accounts. "
            "Be concise, focus on clear step-by-step instructions, and maintain security best practices."
        )
    )
    session.add(llm_config)
    
    # Create agent patterns for detection
    patterns = [
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="password",
            priority=2,
            confidence_boost=0.2
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="reset",
            priority=1,
            confidence_boost=0.15
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="account",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="login",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="forgot",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="semantic",
            pattern_value="I can't log into my Staples account",
            priority=2,
            confidence_boost=0.15
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="semantic",
            pattern_value="I need to reset my Staples password",
            priority=2,
            confidence_boost=0.2
        ),
    ]
    for pattern in patterns:
        session.add(pattern)
    
    # Create response templates
    templates = [
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="reset_instructions",
            template_content=(
                "To reset your password:\n"
                "1. Go to Staples.com and click 'Sign In'\n"
                "2. Select 'Forgot Password'\n"
                "3. Enter your email address\n"
                "4. Check your email for a reset link\n"
                "5. Click the link and follow the instructions to create a new password"
            ),
            template_type="text",
            language="en",
            tone="instructional",
            version=1
        ),
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="account_recovery",
            template_content=(
                "If you can't access your email, you can verify your account by:\n"
                "1. Calling customer service at 1-800-STAPLES\n"
                "2. Providing your account details and confirming your identity\n"
                "3. Requesting an account recovery"
            ),
            template_type="text",
            language="en",
            tone="helpful",
            version=1
        ),
    ]
    for template in templates:
        session.add(template)
    
    # Create entity definitions
    email_query = select(EntityDefinition).where(EntityDefinition.name == "email")
    result = await session.execute(email_query)
    email_entity = result.scalar_one_or_none()
    
    if not email_entity:
        email_entity = EntityDefinition(
            name="email",
            display_name="Email Address",
            description="The email address associated with your Staples account",
            entity_type="email",
            validation_regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            is_required=True
        )
        session.add(email_entity)
        await session.flush()
    
    # Create entity mappings
    entity_mappings = [
        AgentEntityMapping(
            agent_id=agent.id,
            entity_id=email_entity.id,
            is_required=True,
            extraction_priority=1,
            prompt_for_missing=True,
            prompt_text="What email address is associated with your Staples account?",
            extraction_method="regex"
        )
    ]
    for mapping in entity_mappings:
        session.add(mapping)


async def seed_store_locator_agent(session: AsyncSession) -> None:
    """
    Seed the database with the store locator agent.
    
    Args:
        session: An async database session
    """
    # Check if agent already exists
    if await check_agent_exists(session, STORE_LOCATOR_AGENT):
        logger.info(f"Agent {STORE_LOCATOR_AGENT} already exists, skipping")
        return
    
    # Create agent definition
    agent = AgentDefinition(
        name="Store Locator Agent",
        description="I can help you find Staples stores near you, check store hours, and provide information about store services.",
        agent_type=STORE_LOCATOR_AGENT,
        status="active",
        is_system=True,
        version=1,
        created_by="system"
    )
    session.add(agent)
    await session.flush()  # To generate the ID
    
    # Create LLM configuration
    llm_config = LlmAgentConfiguration(
        agent_id=agent.id,
        model_name="gpt-4o",
        temperature=0.6,
        max_tokens=350,
        timeout_seconds=8,  # As defined in AGENT_TIMEOUTS
        confidence_threshold=0.7,
        system_prompt=(
            "You are a Staples Customer Service Representative specializing in store information. "
            "You help customers find Staples store locations, check store hours, and learn about "
            "in-store services like printing and tech support. Always maintain a welcoming and informative tone."
        )
    )
    session.add(llm_config)
    
    # Create agent patterns for detection
    patterns = [
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="store",
            priority=2,
            confidence_boost=0.15
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="location",
            priority=2,
            confidence_boost=0.15
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="near me",
            priority=2,
            confidence_boost=0.15
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="hours",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="closest",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="semantic",
            pattern_value="Where is the nearest Staples store?",
            priority=2,
            confidence_boost=0.2
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="semantic",
            pattern_value="What are the hours for Staples in my area?",
            priority=2,
            confidence_boost=0.15
        ),
    ]
    for pattern in patterns:
        session.add(pattern)
    
    # Create response templates
    templates = [
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="store_found",
            template_content=(
                "I found the Staples store at {address}, {city}, {state} {zip}. "
                "It's about {distance} miles away and is open {hours} today. "
                "This location offers {services}."
            ),
            template_type="text",
            language="en",
            tone="informative",
            version=1
        ),
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="location_needed",
            template_content=(
                "To find the nearest Staples store, I'll need your location. "
                "Please provide a zip code, city, or address."
            ),
            template_type="text",
            language="en",
            tone="helpful",
            version=1
        ),
    ]
    for template in templates:
        session.add(template)
    
    # Create entity definitions
    location_query = select(EntityDefinition).where(EntityDefinition.name == "location")
    result = await session.execute(location_query)
    location_entity = result.scalar_one_or_none()
    
    if not location_entity:
        location_entity = EntityDefinition(
            name="location",
            display_name="Location",
            description="Your location for finding nearby Staples stores",
            entity_type="text",
            is_required=True
        )
        session.add(location_entity)
        await session.flush()
    
    # Create entity mappings
    entity_mappings = [
        AgentEntityMapping(
            agent_id=agent.id,
            entity_id=location_entity.id,
            is_required=True,
            extraction_priority=1,
            prompt_for_missing=True,
            prompt_text="Please provide your location (zip code, city, or address) to find nearby Staples stores.",
            extraction_method="llm"
        )
    ]
    for mapping in entity_mappings:
        session.add(mapping)


async def seed_product_info_agent(session: AsyncSession) -> None:
    """
    Seed the database with the product info agent.
    
    Args:
        session: An async database session
    """
    # Check if agent already exists
    if await check_agent_exists(session, PRODUCT_INFO_AGENT):
        logger.info(f"Agent {PRODUCT_INFO_AGENT} already exists, skipping")
        return
    
    # Create agent definition
    agent = AgentDefinition(
        name="Product Information Agent",
        description="I can help you find information about Staples products, check product availability, and answer questions about features and compatibility.",
        agent_type=PRODUCT_INFO_AGENT,
        status="active",
        is_system=True,
        version=1,
        created_by="system"
    )
    session.add(agent)
    await session.flush()  # To generate the ID
    
    # Create LLM configuration
    llm_config = LlmAgentConfiguration(
        agent_id=agent.id,
        model_name="gpt-4o",
        temperature=0.7,
        max_tokens=500,
        timeout_seconds=12,  # As defined in AGENT_TIMEOUTS
        confidence_threshold=0.7,
        system_prompt=(
            "You are a Staples Customer Service Representative specializing in product information. "
            "You help customers find products, answer questions about product features, check availability, "
            "and provide information about compatibility and specifications. Always maintain a knowledgeable and helpful tone."
        )
    )
    session.add(llm_config)
    
    # Create agent patterns for detection
    patterns = [
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="product",
            priority=2,
            confidence_boost=0.15
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="item",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="availability",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="features",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="compatible",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="specifications",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="semantic",
            pattern_value="Tell me about this Staples product",
            priority=2,
            confidence_boost=0.15
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="semantic",
            pattern_value="Is this printer compatible with my computer?",
            priority=2,
            confidence_boost=0.15
        ),
    ]
    for pattern in patterns:
        session.add(pattern)
    
    # Create response templates
    templates = [
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="product_found",
            template_content=(
                "I found {product_name} (Item #{item_number}). "
                "Key features: {features}. "
                "Price: ${price}. "
                "It's currently {availability} in stores and online."
            ),
            template_type="text",
            language="en",
            tone="informative",
            version=1
        ),
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="product_not_found",
            template_content=(
                "I couldn't find a product matching your description. "
                "Could you provide more details or a specific item number?"
            ),
            template_type="text",
            language="en",
            tone="apologetic",
            version=1
        ),
    ]
    for template in templates:
        session.add(template)
    
    # Create entity definitions
    product_query = select(EntityDefinition).where(EntityDefinition.name == "product_identifier")
    result = await session.execute(product_query)
    product_entity = result.scalar_one_or_none()
    
    if not product_entity:
        product_entity = EntityDefinition(
            name="product_identifier",
            display_name="Product Identifier",
            description="The name, description, or item number of the product you're looking for",
            entity_type="text",
            is_required=True
        )
        session.add(product_entity)
        await session.flush()
    
    # Create entity mappings
    entity_mappings = [
        AgentEntityMapping(
            agent_id=agent.id,
            entity_id=product_entity.id,
            is_required=True,
            extraction_priority=1,
            prompt_for_missing=True,
            prompt_text="What product are you looking for? Please provide a name, description, or item number.",
            extraction_method="llm"
        )
    ]
    for mapping in entity_mappings:
        session.add(mapping)


async def seed_returns_processing_agent(session: AsyncSession) -> None:
    """
    Seed the database with the returns processing agent.
    
    Args:
        session: An async database session
    """
    # Check if agent already exists
    if await check_agent_exists(session, RETURNS_PROCESSING_AGENT):
        logger.info(f"Agent {RETURNS_PROCESSING_AGENT} already exists, skipping")
        return
    
    # Create agent definition
    agent = AgentDefinition(
        name="Returns Processing Agent",
        description="I can help you process returns, understand the return policy, and provide information about return status for Staples purchases.",
        agent_type=RETURNS_PROCESSING_AGENT,
        status="active",
        is_system=True,
        version=1,
        created_by="system"
    )
    session.add(agent)
    await session.flush()  # To generate the ID
    
    # Create LLM configuration
    llm_config = LlmAgentConfiguration(
        agent_id=agent.id,
        model_name="gpt-4o",
        temperature=0.6,
        max_tokens=450,
        timeout_seconds=10,
        confidence_threshold=0.7,
        system_prompt=(
            "You are a Staples Customer Service Representative specializing in returns. "
            "You help customers understand the return policy, initiate returns, and check return status. "
            "Always be clear, helpful, and informative about the return process and policy details."
        )
    )
    session.add(llm_config)
    
    # Create agent patterns for detection
    patterns = [
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="return",
            priority=2,
            confidence_boost=0.2
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="refund",
            priority=2,
            confidence_boost=0.15
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="exchange",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="keyword",
            pattern_value="policy",
            priority=1,
            confidence_boost=0.1
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="semantic",
            pattern_value="I want to return something I bought at Staples",
            priority=2,
            confidence_boost=0.2
        ),
        AgentPattern(
            agent_id=agent.id,
            pattern_type="semantic",
            pattern_value="What's the status of my refund?",
            priority=2,
            confidence_boost=0.15
        ),
    ]
    for pattern in patterns:
        session.add(pattern)
    
    # Create response templates
    templates = [
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="return_policy",
            template_content=(
                "Staples return policy allows most items to be returned within 30 days of purchase with a receipt. "
                "Electronics and furniture have a 14-day return period. "
                "Items must be in original packaging with all components. "
                "You can return items in-store or by mail with a return shipping label."
            ),
            template_type="text",
            language="en",
            tone="informative",
            version=1
        ),
        AgentResponseTemplate(
            agent_id=agent.id,
            template_key="return_initiated",
            template_content=(
                "I've initiated a return for order {order_number}. "
                "Your return reference number is {return_id}. "
                "Your refund of ${refund_amount} will be processed to your original payment method within 3-5 business days after we receive the returned items."
            ),
            template_type="text",
            language="en",
            tone="confirmational",
            version=1
        ),
    ]
    for template in templates:
        session.add(template)
    
    # Reuse order_number entity from package tracking if it exists
    order_number_query = select(EntityDefinition).where(EntityDefinition.name == "order_number")
    result = await session.execute(order_number_query)
    order_entity = result.scalar_one_or_none()
    
    if not order_entity:
        order_entity = EntityDefinition(
            name="order_number",
            display_name="Order Number",
            description="Your Staples order number",
            entity_type="text",
            validation_regex=r'^[A-Za-z0-9]{2,}-?[A-Za-z0-9]{2,}$',
            is_required=True
        )
        session.add(order_entity)
        await session.flush()
    
    # Create entity for return reason
    return_reason_query = select(EntityDefinition).where(EntityDefinition.name == "return_reason")
    result = await session.execute(return_reason_query)
    reason_entity = result.scalar_one_or_none()
    
    if not reason_entity:
        reason_entity = EntityDefinition(
            name="return_reason",
            display_name="Return Reason",
            description="Reason for returning the item",
            entity_type="enum",
            is_required=True
        )
        session.add(reason_entity)
        await session.flush()
        
        # Add enum values for return reasons
        enum_values = [
            EntityEnumValue(
                entity_id=reason_entity.id,
                value="defective",
                display_text="Item is defective or damaged",
                is_default=False
            ),
            EntityEnumValue(
                entity_id=reason_entity.id,
                value="wrong_item",
                display_text="Received wrong item",
                is_default=False
            ),
            EntityEnumValue(
                entity_id=reason_entity.id,
                value="not_needed",
                display_text="No longer needed",
                is_default=True
            ),
            EntityEnumValue(
                entity_id=reason_entity.id,
                value="not_as_described",
                display_text="Item not as described",
                is_default=False
            ),
            EntityEnumValue(
                entity_id=reason_entity.id,
                value="other",
                display_text="Other reason",
                is_default=False
            ),
        ]
        for enum_value in enum_values:
            session.add(enum_value)
    
    # Create entity mappings
    entity_mappings = [
        AgentEntityMapping(
            agent_id=agent.id,
            entity_id=order_entity.id,
            is_required=True,
            extraction_priority=1,
            prompt_for_missing=True,
            prompt_text="Please provide your order number for the return.",
            extraction_method="regex"
        ),
        AgentEntityMapping(
            agent_id=agent.id,
            entity_id=reason_entity.id,
            is_required=True,
            extraction_priority=2,
            prompt_for_missing=True,
            prompt_text="What is the reason for your return?",
            extraction_method="llm",
            extraction_config={"use_enum_values": True}
        )
    ]
    for mapping in entity_mappings:
        session.add(mapping)


async def seed_all_agents(engine: Optional[AsyncEngine] = None) -> None:
    """
    Seed the database with all predefined agents.
    
    Args:
        engine: The database engine to use, defaults to the main engine
    """
    engine = engine or default_engine
    
    # Create a session factory
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    
    # Use a session to add all agents
    async with async_session() as session:
        try:
            # Begin a transaction
            async with session.begin():
                # Seed each agent
                await seed_package_tracking_agent(session)
                await seed_reset_password_agent(session)
                await seed_store_locator_agent(session)
                await seed_product_info_agent(session)
                await seed_returns_processing_agent(session)
            
            logger.info("All agents seeded successfully")
        except Exception as e:
            logger.error(f"Error seeding agents: {str(e)}")
            raise


async def main() -> None:
    """
    Main function to run the agent seeding.
    """
    logging.basicConfig(level=logging.INFO)
    await seed_all_agents()


if __name__ == "__main__":
    asyncio.run(main())