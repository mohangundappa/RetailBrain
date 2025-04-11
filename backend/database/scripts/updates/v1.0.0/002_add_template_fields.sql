-- Add new fields to agent_templates table if they don't exist
DO $$
BEGIN
    -- Add description field
    IF NOT EXISTS (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='agent_templates' AND column_name='description'
    ) THEN
        ALTER TABLE agent_templates ADD COLUMN description TEXT;
        RAISE NOTICE 'Added description column to agent_templates table';
    ELSE
        RAISE NOTICE 'description column already exists in agent_templates table';
    END IF;

    -- Add category field
    IF NOT EXISTS (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='agent_templates' AND column_name='category'
    ) THEN
        ALTER TABLE agent_templates ADD COLUMN category VARCHAR(100);
        RAISE NOTICE 'Added category column to agent_templates table';
    ELSE
        RAISE NOTICE 'category column already exists in agent_templates table';
    END IF;

    -- Add difficulty field
    IF NOT EXISTS (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='agent_templates' AND column_name='difficulty'
    ) THEN
        ALTER TABLE agent_templates ADD COLUMN difficulty VARCHAR(50);
        RAISE NOTICE 'Added difficulty column to agent_templates table';
    ELSE
        RAISE NOTICE 'difficulty column already exists in agent_templates table';
    END IF;

    -- Add icon field
    IF NOT EXISTS (
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='agent_templates' AND column_name='icon'
    ) THEN
        ALTER TABLE agent_templates ADD COLUMN icon VARCHAR(100);
        RAISE NOTICE 'Added icon column to agent_templates table';
    ELSE
        RAISE NOTICE 'icon column already exists in agent_templates table';
    END IF;
END $$;