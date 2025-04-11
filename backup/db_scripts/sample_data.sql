-- Sample data insertion script for Staples Brain

-- Insert sample conversations
INSERT INTO conversation (session_id, user_input, brain_response, intent, confidence, selected_agent, created_at)
VALUES
  ('test-session-1', 'Where is my order #ST12345?', 'I''ll help you track your order. The package is currently in transit and expected to be delivered tomorrow.', 'track_package', 0.92, 'Package Tracking Agent', NOW() - INTERVAL '2 hours'),
  ('test-session-2', 'I need to reset my password', 'I can help you reset your password. Could you please provide the email address associated with your account?', 'reset_password', 0.88, 'Reset Password Agent', NOW() - INTERVAL '1 day'),
  ('test-session-3', 'Where is the nearest Staples store?', 'I can help find the nearest Staples store. Could you please share your location or zip code?', 'find_store', 0.95, 'Store Locator Agent', NOW() - INTERVAL '3 days');

-- Insert sample messages for the first conversation
INSERT INTO message (conversation_id, role, content, created_at)
VALUES
  (1, 'user', 'Where is my order #ST12345?', NOW() - INTERVAL '2 hours 5 minutes'),
  (1, 'assistant', 'I''ll help you track your order. Could you confirm the order number is ST12345?', NOW() - INTERVAL '2 hours 4 minutes'),
  (1, 'user', 'Yes, that''s correct', NOW() - INTERVAL '2 hours 3 minutes'),
  (1, 'assistant', 'Thank you. The package is currently in transit and expected to be delivered tomorrow.', NOW() - INTERVAL '2 hours 2 minutes');

-- Insert sample package tracking data
INSERT INTO package_tracking (conversation_id, tracking_number, shipping_carrier, order_number, status, estimated_delivery, current_location, last_updated, created_at)
VALUES
  (1, '1Z999AA10123456784', 'UPS', 'ST12345', 'In Transit', '2025-04-10', 'Distribution Center, Atlanta, GA', NOW() - INTERVAL '6 hours', NOW() - INTERVAL '2 hours');

-- Insert sample store locator data
INSERT INTO store_locator (conversation_id, location, radius, service, store_id, store_name, store_address, store_phone, created_at)
VALUES
  (3, '30308', 10, 'Copy & Print', 'STR-123', 'Staples Atlanta Midtown', '1230 Peachtree St NE, Atlanta, GA 30308', '(404) 555-1234', NOW() - INTERVAL '3 days');

-- Insert sample password reset data
INSERT INTO password_reset (conversation_id, email, account_type, issue, reset_link_sent, created_at)
VALUES
  (2, 'user@example.com', 'customer', 'forgotten password', TRUE, NOW() - INTERVAL '1 day');

-- Insert sample agent config
INSERT INTO agent_config (agent_name, is_active, confidence_threshold, description, prompt_template)
VALUES
  ('Package Tracking Agent', TRUE, 0.6, 'Agent for tracking package deliveries and order status', 'You are a package tracking assistant. Help the user track their package with order number {{order_number}} and tracking number {{tracking_number}}.');

-- Insert sample custom agent
INSERT INTO custom_agent (name, description, is_active, creator, icon, wizard_completed)
VALUES
  ('Customer Support Agent', 'A general customer support agent for handling various inquiries', TRUE, 'admin', 'bi bi-headset', TRUE);