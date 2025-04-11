-- Insert or update the Enhanced Package Tracking template
DO $$
DECLARE
    template_id UUID;
BEGIN
    -- Check if the template already exists
    SELECT id INTO template_id FROM agent_templates 
    WHERE name = 'Enhanced Package Tracking';
    
    IF FOUND THEN
        -- Update existing template
        UPDATE agent_templates
        SET 
            description = 'Advanced package tracking agent with detailed shipment status and ETA predictions',
            category = 'Customer Service',
            difficulty = 'Intermediate',
            icon = 'package',
            components = jsonb_build_array(
                jsonb_build_object(
                    'name', 'Package Search',
                    'description', 'Searches for package information by tracking number',
                    'template', 'Your task is to help users track their packages. Ask for tracking numbers if not provided.'
                ),
                jsonb_build_object(
                    'name', 'Delivery Estimation',
                    'description', 'Provides accurate delivery time estimates based on current status',
                    'template', 'When a user asks about delivery times, provide the most accurate estimate possible based on the tracking information.'
                ),
                jsonb_build_object(
                    'name', 'Status Explanation',
                    'description', 'Explains shipping status codes and events in plain language',
                    'template', 'Translate shipping status codes and events into clear, customer-friendly explanations.'
                )
            ),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = template_id;
        
        RAISE NOTICE 'Updated Enhanced Package Tracking template';
    ELSE
        -- Insert new template
        INSERT INTO agent_templates (
            name, 
            description,
            category,
            difficulty,
            icon,
            components
        ) VALUES (
            'Enhanced Package Tracking',
            'Advanced package tracking agent with detailed shipment status and ETA predictions',
            'Customer Service',
            'Intermediate',
            'package',
            jsonb_build_array(
                jsonb_build_object(
                    'name', 'Package Search',
                    'description', 'Searches for package information by tracking number',
                    'template', 'Your task is to help users track their packages. Ask for tracking numbers if not provided.'
                ),
                jsonb_build_object(
                    'name', 'Delivery Estimation',
                    'description', 'Provides accurate delivery time estimates based on current status',
                    'template', 'When a user asks about delivery times, provide the most accurate estimate possible based on the tracking information.'
                ),
                jsonb_build_object(
                    'name', 'Status Explanation',
                    'description', 'Explains shipping status codes and events in plain language',
                    'template', 'Translate shipping status codes and events into clear, customer-friendly explanations.'
                )
            )
        );
        
        RAISE NOTICE 'Inserted Enhanced Package Tracking template';
    END IF;
END $$;