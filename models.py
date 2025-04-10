"""
Database models for the Staples Brain application.
"""
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app import db

# Core Service models

class ServiceRegistry(db.Model):
    """Model for the service registry of registered core services."""
    __tablename__ = 'service_registry'
    
    id = Column(Integer, primary_key=True)
    service_name = Column(String(100), nullable=False, unique=True)
    service_type = Column(String(50), nullable=False)  # 'core', 'integration', 'api', etc.
    configuration = Column(Text, nullable=True)  # JSON string of service configuration
    is_active = Column(Boolean, default=True)
    last_active = Column(DateTime, nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    health_status = Column(Text, nullable=True)  # JSON string of the last health check result
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ServiceRegistry {self.id}: {self.service_name}>"

class ServiceDependency(db.Model):
    """Model for dependencies between services in the registry."""
    __tablename__ = 'service_dependencies'
    
    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey('service_registry.id'), nullable=False)
    dependency_id = Column(Integer, ForeignKey('service_registry.id'), nullable=False)
    dependency_type = Column(String(50), nullable=False)  # 'required', 'optional'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    service = relationship("ServiceRegistry", foreign_keys=[service_id])
    dependency = relationship("ServiceRegistry", foreign_keys=[dependency_id])
    
    def __repr__(self):
        return f"<ServiceDependency {self.id}: {self.service_id} -> {self.dependency_id}>"

class Tool(db.Model):
    """Model for tools that can be used by agents."""
    __tablename__ = 'tools'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    tool_type = Column(String(50), nullable=False)  # 'api', 'function', 'database', etc.
    integration_id = Column(Integer, ForeignKey('service_registry.id'), nullable=True)
    parameters = Column(Text, nullable=True)  # JSON string of parameters
    response_schema = Column(Text, nullable=True)  # JSON string of response schema
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    integration = relationship("ServiceRegistry")
    usage_stats = relationship("ToolUsageStats", back_populates="tool", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tool {self.id}: {self.name}>"

class ToolUsageStats(db.Model):
    """Model for tracking tool usage statistics."""
    __tablename__ = 'tool_usage_stats'
    
    id = Column(Integer, primary_key=True)
    tool_id = Column(Integer, ForeignKey('tools.id'), nullable=False)
    agent_id = Column(Integer, ForeignKey('custom_agents.id'), nullable=True)
    call_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    last_used = Column(DateTime, nullable=True)
    
    # Relationships
    tool = relationship("Tool", back_populates="usage_stats")
    agent = relationship("CustomAgent")
    
    def __repr__(self):
        return f"<ToolUsageStats {self.id}: {self.tool_id} ({self.call_count} calls)>"

class ToolCall(db.Model):
    """Model for individual tool calls."""
    __tablename__ = 'tool_calls'
    
    id = Column(Integer, primary_key=True)
    tool_id = Column(Integer, ForeignKey('tools.id'), nullable=False)
    agent_id = Column(Integer, ForeignKey('custom_agents.id'), nullable=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=True)
    session_id = Column(String(64), nullable=True)
    parameters = Column(Text, nullable=True)  # JSON string of call parameters
    result = Column(Text, nullable=True)  # JSON string of call result
    error = Column(Text, nullable=True)
    latency_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tool = relationship("Tool")
    agent = relationship("CustomAgent")
    conversation = relationship("Conversation")
    
    def __repr__(self):
        return f"<ToolCall {self.id}: {self.tool_id}>"

class Conversation(db.Model):
    """Model representing a conversation with the Staples Brain."""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), nullable=False, index=True)
    user_input = Column(Text, nullable=False)
    brain_response = Column(Text, nullable=True)
    intent = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=True)
    selected_agent = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    tracking_data = relationship("PackageTracking", back_populates="conversation", cascade="all, delete-orphan")
    password_reset_data = relationship("PasswordReset", back_populates="conversation", cascade="all, delete-orphan")
    store_locator_data = relationship("StoreLocator", back_populates="conversation", cascade="all, delete-orphan")
    product_info_data = relationship("ProductInfo", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation {self.id}: {self.intent}>"

class Message(db.Model):
    """Model representing a message in a conversation."""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system', etc.
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message {self.id}: {self.role}>"

class PackageTracking(db.Model):
    """Model for package tracking data."""
    __tablename__ = 'package_tracking'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    tracking_number = Column(String(100), nullable=True)
    shipping_carrier = Column(String(100), nullable=True)
    order_number = Column(String(100), nullable=True)
    status = Column(String(50), nullable=True)
    estimated_delivery = Column(String(50), nullable=True)
    current_location = Column(String(200), nullable=True)
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="tracking_data")
    
    def __repr__(self):
        return f"<PackageTracking {self.id}: {self.tracking_number}>"

class PasswordReset(db.Model):
    """Model for password reset data."""
    __tablename__ = 'password_reset'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    email = Column(String(100), nullable=True)
    username = Column(String(100), nullable=True)
    account_type = Column(String(50), nullable=True)
    issue = Column(String(100), nullable=True)
    reset_link_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="password_reset_data")
    
    def __repr__(self):
        return f"<PasswordReset {self.id}: {self.email}>"

class StoreLocator(db.Model):
    """Model for store locator data."""
    __tablename__ = 'store_locator'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    location = Column(String(100), nullable=True)
    radius = Column(Float, nullable=True)
    service = Column(String(100), nullable=True)
    store_id = Column(String(20), nullable=True)
    store_name = Column(String(100), nullable=True)
    store_address = Column(String(200), nullable=True)
    store_phone = Column(String(20), nullable=True)
    store_hours = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="store_locator_data")
    
    def __repr__(self):
        return f"<StoreLocator {self.id}: {self.store_name}>"

class ProductInfo(db.Model):
    """Model for product information data."""
    __tablename__ = 'product_info'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    product_name = Column(String(200), nullable=True)
    product_id = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)
    price = Column(String(50), nullable=True)
    availability = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    specifications = Column(Text, nullable=True)
    search_query = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="product_info_data")
    
    def __repr__(self):
        return f"<ProductInfo {self.id}: {self.product_name}>"

class AnalyticsData(db.Model):
    """Model for analytics data."""
    __tablename__ = 'analytics_data'
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    dimensions = Column(Text, nullable=True)  # JSON string of dimension key/values
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    def get_dimensions(self):
        """Get dimensions as a dictionary."""
        if self.dimensions:
            return json.loads(self.dimensions)
        return {}
    
    def set_dimensions(self, dimensions_dict):
        """Set dimensions from a dictionary."""
        self.dimensions = json.dumps(dimensions_dict)
    
    def __repr__(self):
        return f"<AnalyticsData {self.id}: {self.metric_name}={self.metric_value}>"

class CustomAgent(db.Model):
    """Model for custom agents created through the builder interface."""
    __tablename__ = 'custom_agents'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    configuration = Column(Text, nullable=True)  # JSON string of the complete agent configuration
    is_active = Column(Boolean, default=True)
    wizard_completed = Column(Boolean, default=False)  # Whether the setup wizard has been completed
    creator = Column(String(100), nullable=True)
    icon = Column(String(100), nullable=True, default="fas fa-robot")  # Font Awesome icon class
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    components = relationship("AgentComponent", back_populates="agent", cascade="all, delete-orphan")
    connections = relationship("ComponentConnection", back_populates="agent", cascade="all, delete-orphan")
    
    def get_entity_definitions(self):
        """Get entity definitions from configuration."""
        try:
            if not self.configuration:
                return []
            config = json.loads(self.configuration)
            return config.get('entity_definitions', [])
        except:
            return []
    
    def get_prompt_templates(self):
        """Get prompt templates from configuration."""
        try:
            if not self.configuration:
                return []
            config = json.loads(self.configuration)
            return config.get('prompt_templates', [])
        except:
            return []
    
    def get_response_formats(self):
        """Get response formats from configuration."""
        try:
            if not self.configuration:
                return []
            config = json.loads(self.configuration)
            return config.get('response_formats', [])
        except:
            return []
    
    def get_business_rules(self):
        """Get business rules from configuration."""
        try:
            if not self.configuration:
                return []
            config = json.loads(self.configuration)
            return config.get('business_rules', [])
        except:
            return []
            
    def __repr__(self):
        return f"<CustomAgent {self.id}: {self.name}>"

class AgentComponent(db.Model):
    """Model for components of a custom agent."""
    __tablename__ = 'agent_components'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('custom_agents.id'), nullable=False)
    component_type = Column(String(50), nullable=False)  # 'prompt', 'llm', 'output_parser', etc.
    name = Column(String(100), nullable=False)
    position_x = Column(Float, nullable=True)
    position_y = Column(Float, nullable=True)
    configuration = Column(Text, nullable=True)  # JSON string of component-specific configuration
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = relationship("CustomAgent", back_populates="components")
    outgoing_connections = relationship("ComponentConnection", foreign_keys="ComponentConnection.source_id", 
                                       back_populates="source_component", cascade="all, delete-orphan")
    incoming_connections = relationship("ComponentConnection", foreign_keys="ComponentConnection.target_id", 
                                       back_populates="target_component", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentComponent {self.id}: {self.name} ({self.component_type})>"

class ComponentConnection(db.Model):
    """Model for connections between components in a custom agent."""
    __tablename__ = 'component_connections'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('custom_agents.id'), nullable=False)
    source_id = Column(Integer, ForeignKey('agent_components.id'), nullable=False)
    target_id = Column(Integer, ForeignKey('agent_components.id'), nullable=False)
    connection_type = Column(String(50), default='default')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent = relationship("CustomAgent", back_populates="connections")
    source_component = relationship("AgentComponent", foreign_keys=[source_id], back_populates="outgoing_connections")
    target_component = relationship("AgentComponent", foreign_keys=[target_id], back_populates="incoming_connections")
    
    def __repr__(self):
        return f"<ComponentConnection {self.id}: {self.source_id} -> {self.target_id}>"

class ComponentTemplate(db.Model):
    """Model for predefined component templates that can be used in the agent builder."""
    __tablename__ = 'component_templates'
    
    id = Column(Integer, primary_key=True)
    template_type = Column(String(50), nullable=False)  # 'prompt', 'llm', 'output_parser', etc.
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    configuration = Column(Text, nullable=False)  # JSON string of template configuration
    icon = Column(String(100), nullable=True)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ComponentTemplate {self.id}: {self.name} ({self.template_type})>"

class AgentTemplate(db.Model):
    """Model for predefined agent templates."""
    __tablename__ = 'agent_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    configuration = Column(Text, nullable=False)  # JSON string of complete agent configuration
    category = Column(String(50), nullable=True)
    icon = Column(String(100), nullable=True)
    tags = Column(Text, nullable=True)  # Comma-separated tags for filtering
    is_system = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    screenshot = Column(String(255), nullable=True)
    author = Column(String(100), nullable=True)
    author_email = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_tags_list(self):
        """Get tags as a list."""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',')]
    
    def get_entity_definitions(self):
        """Get entity definitions from configuration."""
        try:
            config = json.loads(self.configuration)
            return config.get('entity_definitions', [])
        except:
            return []
    
    def get_prompt_templates(self):
        """Get prompt templates from configuration."""
        try:
            config = json.loads(self.configuration)
            prompts = [c for c in config.get('components', []) if c.get('type') == 'prompt']
            return prompts
        except:
            return []
    
    def get_response_formats(self):
        """Get response formats from configuration."""
        try:
            config = json.loads(self.configuration)
            parsers = [c for c in config.get('components', []) if c.get('type') == 'output_parser']
            return parsers
        except:
            return []
    
    def get_business_rules(self):
        """Get business rules from configuration."""
        try:
            config = json.loads(self.configuration)
            return config.get('business_rules', [])
        except:
            return []
    
    def __repr__(self):
        return f"<AgentTemplate {self.id}: {self.name}>"