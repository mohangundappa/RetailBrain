-- Add entity_definitions column to custom_agents table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='custom_agents' AND column_name='entity_definitions'
    ) THEN
        ALTER TABLE custom_agents ADD COLUMN entity_definitions TEXT;
        RAISE NOTICE 'Added entity_definitions column to custom_agents table';
    ELSE
        RAISE NOTICE 'entity_definitions column already exists in custom_agents table';
    END IF;
END $$;

-- Add icon field to custom_agents table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='custom_agents' AND column_name='icon'
    ) THEN
        ALTER TABLE custom_agents ADD COLUMN icon VARCHAR(100);
        RAISE NOTICE 'Added icon column to custom_agents table';
    ELSE
        RAISE NOTICE 'icon column already exists in custom_agents table';
    END IF;
END $$;

-- Add wizard_completed field to custom_agents table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='custom_agents' AND column_name='wizard_completed'
    ) THEN
        ALTER TABLE custom_agents ADD COLUMN wizard_completed BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added wizard_completed column to custom_agents table';
    ELSE
        RAISE NOTICE 'wizard_completed column already exists in custom_agents table';
    END IF;
END $$;