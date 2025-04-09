-- Conversation table
CREATE TABLE conversation (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    user_input TEXT NOT NULL,
    brain_response TEXT NOT NULL,
    intent VARCHAR(64),
    confidence FLOAT,
    selected_agent VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_conversation_session_id ON conversation(session_id);

-- Message table
CREATE TABLE message (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Package Tracking table
CREATE TABLE package_tracking (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    tracking_number VARCHAR(128) NOT NULL,
    shipping_carrier VARCHAR(64),
    order_number VARCHAR(128),
    status VARCHAR(64),
    estimated_delivery VARCHAR(64),
    current_location VARCHAR(128),
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password Reset table
CREATE TABLE password_reset (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    email VARCHAR(128),
    username VARCHAR(128),
    account_type VARCHAR(64),
    issue VARCHAR(128),
    reset_link_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store Locator table
CREATE TABLE store_locator (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    location VARCHAR(128),
    radius INTEGER DEFAULT 10,
    service VARCHAR(128),
    store_id VARCHAR(64),
    store_name VARCHAR(128),
    store_address VARCHAR(256),
    store_phone VARCHAR(64),
    store_hours TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product Info table
CREATE TABLE product_info (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    product_name VARCHAR(256),
    product_id VARCHAR(128),
    category VARCHAR(128),
    price VARCHAR(64),
    availability VARCHAR(64),
    description TEXT,
    specifications TEXT,
    search_query VARCHAR(256),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Config table
CREATE TABLE agent_config (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(64) NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    confidence_threshold FLOAT DEFAULT 0.3,
    description TEXT,
    prompt_template TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Custom Agent table
CREATE TABLE custom_agent (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    creator VARCHAR(128),
    icon VARCHAR(256),
    configuration TEXT,
    entity_definitions TEXT,
    prompt_templates TEXT,
    response_formats TEXT,
    business_rules TEXT,
    wizard_completed BOOLEAN DEFAULT FALSE,
    current_wizard_step INTEGER DEFAULT 1
);

-- Agent Component table
CREATE TABLE agent_component (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES custom_agent(id) ON DELETE CASCADE,
    component_type VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    position_x INTEGER DEFAULT 0,
    position_y INTEGER DEFAULT 0,
    configuration TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Component Connection table
CREATE TABLE component_connection (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES custom_agent(id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES agent_component(id) ON DELETE CASCADE,
    target_id INTEGER NOT NULL REFERENCES agent_component(id) ON DELETE CASCADE,
    connection_type VARCHAR(64) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Component Template table
CREATE TABLE component_template (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    component_type VARCHAR(64) NOT NULL,
    icon VARCHAR(256),
    configuration_template TEXT,
    category VARCHAR(64),
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Template table
CREATE TABLE agent_template (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    category VARCHAR(64),
    icon VARCHAR(256),
    screenshot VARCHAR(256),
    is_featured BOOLEAN DEFAULT FALSE,
    is_system BOOLEAN DEFAULT FALSE,
    configuration TEXT,
    entity_definitions TEXT,
    prompt_templates TEXT,
    response_formats TEXT,
    business_rules TEXT,
    author VARCHAR(128),
    author_email VARCHAR(256),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    downloads INTEGER DEFAULT 0,
    rating FLOAT DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    tags VARCHAR(512)
);

-- Analytics Data table
CREATE TABLE analytics_data (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(64) NOT NULL,
    request_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    avg_confidence FLOAT DEFAULT 0,
    avg_response_time FLOAT DEFAULT 0,
    date DATE NOT NULL,
    CONSTRAINT unique_agent_day UNIQUE(agent_name, date)
);