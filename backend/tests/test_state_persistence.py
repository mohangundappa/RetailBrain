"""
Tests for state persistence mechanisms.

This module tests the functionality of the StatePersistenceManager class 
and related functions in the state_persistence.py module.
"""
import json
import unittest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from backend.brain.native_graph.state_persistence import (
    StatePersistenceManager,
    persist_state,
)


class TestStatePersistenceManager(unittest.IsolatedAsyncioTestCase):
    """Tests for StatePersistenceManager class."""
    
    async def asyncSetUp(self):
        """Set up test fixtures before each test method."""
        # Create mock database session
        self.db_session = AsyncMock(spec=AsyncSession)
        # Mock the execute method to return a result that can be used in first()
        mock_result = AsyncMock()
        mock_result.first.return_value = None  # Default to no results
        self.db_session.execute.return_value = mock_result
        
        # Create persistence manager
        self.persistence_manager = StatePersistenceManager(self.db_session)
    
    async def test_save_state(self):
        """Test saving state to the database."""
        # Arrange
        test_state = {"key": "value", "nested": {"key2": "value2"}}
        session_id = str(uuid.uuid4())
        
        # Set up the mock to return a specific value for the execute method
        self.db_session.execute.return_value = AsyncMock()
        
        # Act
        state_id = await self.persistence_manager.save_state(test_state, session_id)
        
        # Assert
        self.assertIsNotNone(state_id)
        self.assertIsInstance(state_id, str)
        self.assertTrue(self.db_session.execute.called)
        self.assertTrue(self.db_session.commit.called)
    
    async def test_save_state_with_checkpoint(self):
        """Test saving state with a checkpoint name."""
        # Arrange
        test_state = {"key": "value"}
        session_id = str(uuid.uuid4())
        checkpoint_name = "test_checkpoint"
        
        # Act
        state_id = await self.persistence_manager.save_state(test_state, session_id, checkpoint_name)
        
        # Assert
        self.assertIsNotNone(state_id)
        # Verify that the checkpoint name was included in the DB call
        call_kwargs = self.db_session.execute.call_args[1]
        self.assertEqual(call_kwargs['params']['checkpoint_name'], checkpoint_name)
        self.assertTrue(call_kwargs['params']['is_checkpoint'])
    
    async def test_load_state_not_found(self):
        """Test loading state when no state exists."""
        # Arrange
        session_id = str(uuid.uuid4())
        # Mock db result to return None
        mock_result = AsyncMock()
        mock_result.first.return_value = None
        self.db_session.execute.return_value = mock_result
        
        # Act
        state = await self.persistence_manager.load_state(session_id)
        
        # Assert
        self.assertIsNone(state)
        self.assertTrue(self.db_session.execute.called)
    
    async def test_load_state_success(self):
        """Test loading state successfully."""
        # Arrange
        session_id = str(uuid.uuid4())
        test_state = {"key": "value", "nested": {"key2": "value2"}}
        serialized_state = json.dumps({"state_data": test_state})
        
        # Mock db result to return serialized state
        mock_result = AsyncMock()
        mock_result.first.return_value = [serialized_state]
        self.db_session.execute.return_value = mock_result
        
        # Act
        loaded_state = await self.persistence_manager.load_state(session_id)
        
        # Assert
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state, test_state)
    
    async def test_create_checkpoint(self):
        """Test creating a checkpoint."""
        # This test will use mocks from the setUp method
        with patch.object(self.persistence_manager, 'save_state', AsyncMock()) as mock_save_state:
            with patch.object(self.persistence_manager, '_clean_old_checkpoints', AsyncMock()) as mock_clean_checkpoints:
                # Arrange
                test_state = {"key": "value"}
                session_id = str(uuid.uuid4())
                checkpoint_name = "test_checkpoint"
                mock_save_state.return_value = "mock_checkpoint_id"
                
                # Act
                checkpoint_id = await self.persistence_manager.create_checkpoint(
                    test_state, session_id, checkpoint_name
                )
                
                # Assert
                self.assertEqual(checkpoint_id, "mock_checkpoint_id")
                mock_save_state.assert_called_once_with(
                    state=test_state, session_id=session_id, checkpoint_name=checkpoint_name
                )
                mock_clean_checkpoints.assert_called_once_with(session_id)
    
    async def test_rollback_to_checkpoint_not_found(self):
        """Test rolling back to a checkpoint that doesn't exist."""
        # Arrange
        session_id = str(uuid.uuid4())
        checkpoint_name = "nonexistent_checkpoint"
        
        # Mock db result to return None
        mock_result = AsyncMock()
        mock_result.first.return_value = None
        self.db_session.execute.return_value = mock_result
        
        # Act
        state = await self.persistence_manager.rollback_to_checkpoint(session_id, checkpoint_name)
        
        # Assert
        self.assertIsNone(state)
        self.assertTrue(self.db_session.execute.called)
    
    async def test_rollback_to_checkpoint_success(self):
        """Test successfully rolling back to a checkpoint."""
        # Arrange
        session_id = str(uuid.uuid4())
        checkpoint_name = "test_checkpoint"
        test_state = {"key": "checkpoint_value"}
        serialized_state = json.dumps({"state_data": test_state})
        
        # Mock db result to return serialized state
        mock_result = AsyncMock()
        mock_result.first.return_value = [serialized_state]
        self.db_session.execute.return_value = mock_result
        
        # Act
        loaded_state = await self.persistence_manager.rollback_to_checkpoint(session_id, checkpoint_name)
        
        # Assert
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state, test_state)
    
    async def test_clean_expired_states(self):
        """Test cleaning expired states."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.rowcount = 5  # Mock 5 deleted rows
        self.db_session.execute.return_value = mock_result
        
        # Act
        deleted_count = await self.persistence_manager.clean_expired_states(days=7)
        
        # Assert
        self.assertEqual(deleted_count, 5)
        self.assertTrue(self.db_session.execute.called)
        self.assertTrue(self.db_session.commit.called)
    
    async def test_list_checkpoints(self):
        """Test listing available checkpoints."""
        # Arrange
        session_id = str(uuid.uuid4())
        now = datetime.now()
        mock_checkpoints = [
            ("id1", "checkpoint1", now - timedelta(minutes=10)),
            ("id2", "checkpoint2", now - timedelta(minutes=5))
        ]
        
        # Mock result with multiple rows
        mock_result = AsyncMock()
        mock_result.__iter__.return_value = mock_checkpoints
        self.db_session.execute.return_value = mock_result
        
        # Act
        checkpoints = await self.persistence_manager.list_checkpoints(session_id)
        
        # Assert
        self.assertEqual(len(checkpoints), 2)
        self.assertEqual(checkpoints[0]["id"], "id1")
        self.assertEqual(checkpoints[0]["name"], "checkpoint1")
        self.assertIsInstance(checkpoints[0]["created_at"], str)
        self.assertEqual(checkpoints[1]["id"], "id2")
        self.assertEqual(checkpoints[1]["name"], "checkpoint2")
        self.assertIsInstance(checkpoints[1]["created_at"], str)
    
    async def test_clean_old_checkpoints(self):
        """Test cleaning old checkpoints."""
        # Arrange
        session_id = str(uuid.uuid4())
        # Mock first query result to return IDs to keep
        mock_result1 = AsyncMock()
        mock_result1.__iter__.return_value = [("id1",), ("id2",)]
        # Sequence the execute call to return different results
        self.db_session.execute.side_effect = [mock_result1, AsyncMock()]
        
        # Act
        await self.persistence_manager._clean_old_checkpoints(session_id)
        
        # Assert
        self.assertEqual(self.db_session.execute.call_count, 2)
        # Verify that the second call contained the IDs to keep
        _, kwargs = self.db_session.execute.call_args_list[1]
        self.assertIn('ids_to_keep', kwargs['params'])
        self.assertEqual(kwargs['params']['ids_to_keep'], ("id1", "id2"))
        self.assertTrue(self.db_session.commit.called)


class TestPersistState(unittest.IsolatedAsyncioTestCase):
    """Tests for non-class persistence functions."""
    
    async def test_persist_state(self):
        """Test the persist_state function."""
        # Arrange
        mock_state = {"key": "value"}
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Create a mock StatePersistenceManager
        with patch('backend.brain.native_graph.state_persistence.StatePersistenceManager') as MockManager:
            mock_manager_instance = AsyncMock()
            MockManager.return_value = mock_manager_instance
            mock_manager_instance.save_state.return_value = "test_state_id"
            
            # Act
            result = await persist_state(mock_state, mock_session_id, mock_db)
            
            # Assert
            self.assertEqual(result, mock_state)  # The function should return the state unchanged
            mock_manager_instance.save_state.assert_called_once_with(
                state=mock_state,
                session_id=mock_session_id,
                checkpoint_name=None
            )


if __name__ == "__main__":
    unittest.main()