"""
Tests for state recovery mechanisms.

This module tests the state recovery and resilience functionality
in the state_recovery.py module.
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call

from sqlalchemy.ext.asyncio import AsyncSession

from backend.brain.native_graph.state_recovery import (
    with_retry,
    resilient_persist_state,
    resilient_recover_state,
    resilient_create_checkpoint,
    resilient_rollback_to_checkpoint,
    process_pending_operations,
    check_db_connection,
    get_most_recent_state
)


class TestWithRetry(unittest.IsolatedAsyncioTestCase):
    """Tests for the with_retry decorator."""
    
    async def test_with_retry_success_first_attempt(self):
        """Test that the decorator returns successfully on first attempt."""
        # Arrange
        mock_func = AsyncMock()
        mock_func.return_value = {"result": "success"}
        decorated_func = with_retry()(mock_func)
        
        # Act
        result = await decorated_func("test_arg", kwarg="test_kwarg")
        
        # Assert
        self.assertEqual(result, {"result": "success"})
        mock_func.assert_called_once_with("test_arg", kwarg="test_kwarg")
    
    async def test_with_retry_success_after_retries(self):
        """Test that the function is retried until it succeeds."""
        # Arrange
        mock_func = AsyncMock()
        # Fail twice, then succeed
        mock_func.side_effect = [
            Exception("Temporary error"), 
            Exception("Temporary error"),
            {"result": "success after retry"}
        ]
        decorated_func = with_retry(max_retries=3, retry_delay=0.01)(mock_func)
        
        # Act
        result = await decorated_func("test_arg")
        
        # Assert
        self.assertEqual(result, {"result": "success after retry"})
        self.assertEqual(mock_func.call_count, 3)
    
    async def test_with_retry_max_attempts_exceeded(self):
        """Test that the decorator gives up after max attempts."""
        # Arrange
        mock_func = AsyncMock()
        mock_func.side_effect = Exception("Persistent error")
        decorated_func = with_retry(max_attempts=2, base_delay=0.01)(mock_func)
        
        # Act & Assert
        with self.assertRaises(Exception) as context:
            await decorated_func("test_arg")
        
        self.assertIn("Persistent error", str(context.exception))
        self.assertEqual(mock_func.call_count, 2)


class TestResilientStatePersistence(unittest.IsolatedAsyncioTestCase):
    """Tests for resilient state persistence functions."""
    
    async def test_resilient_persist_state_success(self):
        """Test successful state persistence."""
        # Arrange
        mock_state = {"key": "value"}
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Create a mock persistence manager via the patch
        with patch('backend.brain.native_graph.state_recovery.persist_state') as mock_persist:
            mock_persist.return_value = mock_state
            
            # Act
            result = await resilient_persist_state(mock_state, mock_session_id, mock_db)
            
            # Assert
            self.assertEqual(result, mock_state)
            mock_persist.assert_called_once_with(
                mock_state, mock_session_id, mock_db, None
            )
    
    async def test_resilient_persist_state_retry_success(self):
        """Test that persistence is retried on temporary failure."""
        # Arrange
        mock_state = {"key": "value"}
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('backend.brain.native_graph.state_recovery.persist_state') as mock_persist:
            # Fail once, then succeed
            mock_persist.side_effect = [
                Exception("Database connection failed"), 
                mock_state
            ]
            
            # Act
            result = await resilient_persist_state(
                mock_state, mock_session_id, mock_db,
                max_retries=2, retry_delay=0.01
            )
            
            # Assert
            self.assertEqual(result, mock_state)
            self.assertEqual(mock_persist.call_count, 2)
    
    async def test_resilient_persist_state_failure(self):
        """Test that persistence fails after max retries."""
        # Arrange
        mock_state = {"key": "value"}
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('backend.brain.native_graph.state_recovery.persist_state') as mock_persist:
            # Always fail
            mock_persist.side_effect = Exception("Persistent database error")
            
            # Act & Assert
            with self.assertRaises(Exception) as context:
                await resilient_persist_state(
                    mock_state, mock_session_id, mock_db,
                    max_retries=2, retry_delay=0.01
                )
            
            self.assertIn("Persistent database error", str(context.exception))
            self.assertEqual(mock_persist.call_count, 3)  # Initial + 2 retries


class TestResilientStateRecovery(unittest.IsolatedAsyncioTestCase):
    """Tests for resilient state recovery functions."""
    
    async def test_resilient_recover_state_success(self):
        """Test successful state recovery."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        expected_state = {"key": "recovered_value"}
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            mock_manager.load_state.return_value = expected_state
            
            # Act
            result = await resilient_recover_state(mock_session_id, mock_db)
            
            # Assert
            self.assertEqual(result, expected_state)
            mock_manager.load_state.assert_called_once_with(mock_session_id)
    
    async def test_resilient_recover_state_retry_success(self):
        """Test that recovery is retried on temporary failure."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        expected_state = {"key": "recovered_value"}
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            # Fail once, then succeed
            mock_manager.load_state.side_effect = [
                Exception("Database connection failed"), 
                expected_state
            ]
            
            # Act
            result = await resilient_recover_state(
                mock_session_id, mock_db,
                max_retries=2, retry_delay=0.01
            )
            
            # Assert
            self.assertEqual(result, expected_state)
            self.assertEqual(mock_manager.load_state.call_count, 2)
    
    async def test_resilient_recover_state_not_found(self):
        """Test recovery when no state exists."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            mock_manager.load_state.return_value = None
            
            # Act
            result = await resilient_recover_state(mock_session_id, mock_db)
            
            # Assert
            self.assertIsNone(result)
            mock_manager.load_state.assert_called_once_with(mock_session_id)
    
    async def test_resilient_recover_state_not_found_with_default(self):
        """Test recovery with a default state when no state exists."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        default_state = {"key": "default_value"}
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            mock_manager.load_state.return_value = None
            
            # Act
            result = await resilient_recover_state(
                mock_session_id, mock_db,
                return_empty_state=default_state
            )
            
            # Assert
            self.assertEqual(result, default_state)
            mock_manager.load_state.assert_called_once_with(mock_session_id)
    
    async def test_resilient_recover_state_failure(self):
        """Test that recovery fails after max retries."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            # Always fail
            mock_manager.load_state.side_effect = Exception("Persistent database error")
            
            # Act & Assert
            with self.assertRaises(Exception) as context:
                await resilient_recover_state(
                    mock_session_id, mock_db,
                    max_retries=2, retry_delay=0.01
                )
            
            self.assertIn("Persistent database error", str(context.exception))
            self.assertEqual(mock_manager.load_state.call_count, 3)  # Initial + 2 retries


class TestResilientCheckpoint(unittest.IsolatedAsyncioTestCase):
    """Tests for resilient checkpoint functions."""
    
    async def test_resilient_create_checkpoint_success(self):
        """Test successful checkpoint creation."""
        # Arrange
        mock_state = {"key": "value"}
        mock_session_id = "test_session_id"
        mock_checkpoint_name = "test_checkpoint"
        mock_db = AsyncMock(spec=AsyncSession)
        expected_checkpoint_id = "checkpoint_123"
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            mock_manager.create_checkpoint.return_value = expected_checkpoint_id
            
            # Act
            result = await resilient_create_checkpoint(
                mock_state, mock_session_id, mock_checkpoint_name, mock_db
            )
            
            # Assert
            self.assertEqual(result, expected_checkpoint_id)
            mock_manager.create_checkpoint.assert_called_once_with(
                mock_state, mock_session_id, mock_checkpoint_name
            )
    
    async def test_resilient_create_checkpoint_retry_success(self):
        """Test that checkpoint creation is retried on temporary failure."""
        # Arrange
        mock_state = {"key": "value"}
        mock_session_id = "test_session_id"
        mock_checkpoint_name = "test_checkpoint"
        mock_db = AsyncMock(spec=AsyncSession)
        expected_checkpoint_id = "checkpoint_123"
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            # Fail once, then succeed
            mock_manager.create_checkpoint.side_effect = [
                Exception("Database connection failed"), 
                expected_checkpoint_id
            ]
            
            # Act
            result = await resilient_create_checkpoint(
                mock_state, mock_session_id, mock_checkpoint_name, mock_db,
                max_retries=2, retry_delay=0.01
            )
            
            # Assert
            self.assertEqual(result, expected_checkpoint_id)
            self.assertEqual(mock_manager.create_checkpoint.call_count, 2)
    
    async def test_resilient_create_checkpoint_failure(self):
        """Test that checkpoint creation fails after max retries."""
        # Arrange
        mock_state = {"key": "value"}
        mock_session_id = "test_session_id"
        mock_checkpoint_name = "test_checkpoint"
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            # Always fail
            mock_manager.create_checkpoint.side_effect = Exception("Persistent database error")
            
            # Act & Assert
            with self.assertRaises(Exception) as context:
                await resilient_create_checkpoint(
                    mock_state, mock_session_id, mock_checkpoint_name, mock_db,
                    max_retries=2, retry_delay=0.01
                )
            
            self.assertIn("Persistent database error", str(context.exception))
            self.assertEqual(mock_manager.create_checkpoint.call_count, 3)  # Initial + 2 retries


class TestResilientRollback(unittest.IsolatedAsyncioTestCase):
    """Tests for resilient rollback functions."""
    
    async def test_resilient_rollback_to_checkpoint_success(self):
        """Test successful rollback to checkpoint."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_checkpoint_name = "test_checkpoint"
        mock_db = AsyncMock(spec=AsyncSession)
        expected_state = {"key": "checkpoint_value"}
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            mock_manager.rollback_to_checkpoint.return_value = expected_state
            
            # Act
            result = await resilient_rollback_to_checkpoint(
                mock_session_id, mock_checkpoint_name, mock_db
            )
            
            # Assert
            self.assertEqual(result, expected_state)
            mock_manager.rollback_to_checkpoint.assert_called_once_with(
                mock_session_id, mock_checkpoint_name
            )
    
    async def test_resilient_rollback_to_checkpoint_retry_success(self):
        """Test that rollback is retried on temporary failure."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_checkpoint_name = "test_checkpoint"
        mock_db = AsyncMock(spec=AsyncSession)
        expected_state = {"key": "checkpoint_value"}
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            # Fail once, then succeed
            mock_manager.rollback_to_checkpoint.side_effect = [
                Exception("Database connection failed"), 
                expected_state
            ]
            
            # Act
            result = await resilient_rollback_to_checkpoint(
                mock_session_id, mock_checkpoint_name, mock_db,
                max_retries=2, retry_delay=0.01
            )
            
            # Assert
            self.assertEqual(result, expected_state)
            self.assertEqual(mock_manager.rollback_to_checkpoint.call_count, 2)
    
    async def test_resilient_rollback_to_checkpoint_not_found(self):
        """Test rollback when checkpoint doesn't exist."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_checkpoint_name = "nonexistent_checkpoint"
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            mock_manager.rollback_to_checkpoint.return_value = None
            
            # Act
            result = await resilient_rollback_to_checkpoint(
                mock_session_id, mock_checkpoint_name, mock_db
            )
            
            # Assert
            self.assertIsNone(result)
            mock_manager.rollback_to_checkpoint.assert_called_once_with(
                mock_session_id, mock_checkpoint_name
            )
    
    async def test_resilient_rollback_to_checkpoint_failure(self):
        """Test that rollback fails after max retries."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_checkpoint_name = "test_checkpoint"
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('backend.brain.native_graph.state_recovery.StatePersistenceManager') as MockManager:
            mock_manager = AsyncMock()
            MockManager.return_value = mock_manager
            # Always fail
            mock_manager.rollback_to_checkpoint.side_effect = Exception("Persistent database error")
            
            # Act & Assert
            with self.assertRaises(Exception) as context:
                await resilient_rollback_to_checkpoint(
                    mock_session_id, mock_checkpoint_name, mock_db,
                    max_retries=2, retry_delay=0.01
                )
            
            self.assertIn("Persistent database error", str(context.exception))
            self.assertEqual(mock_manager.rollback_to_checkpoint.call_count, 3)  # Initial + 2 retries


class TestRecoveryOperations(unittest.IsolatedAsyncioTestCase):
    """Tests for recovery operations."""
    
    async def test_check_db_connection_success(self):
        """Test successful database connection check."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.return_value = AsyncMock()
        
        # Act
        result = await check_db_connection(mock_db)
        
        # Assert
        self.assertTrue(result)
        mock_db.execute.assert_called_once()
    
    async def test_check_db_connection_failure(self):
        """Test failed database connection check."""
        # Arrange
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.side_effect = Exception("Connection error")
        
        # Act
        result = await check_db_connection(mock_db)
        
        # Assert
        self.assertFalse(result)
        mock_db.execute.assert_called_once()
    
    async def test_get_most_recent_state_success(self):
        """Test successful retrieval of most recent state."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        expected_state = {"key": "most_recent_value"}
        
        with patch('backend.brain.native_graph.state_recovery.resilient_recover_state') as mock_recover:
            mock_recover.return_value = expected_state
            
            # Act
            result = await get_most_recent_state(mock_session_id, mock_db)
            
            # Assert
            self.assertEqual(result, expected_state)
            mock_recover.assert_called_once_with(session_id=mock_session_id, db=mock_db)
    
    async def test_get_most_recent_state_fallback_to_recovery(self):
        """Test fallback to recovery when no state exists."""
        # Arrange
        mock_session_id = "test_session_id"
        mock_db = AsyncMock(spec=AsyncSession)
        expected_state = {"key": "recovered_value"}
        
        with patch('backend.brain.native_graph.state_recovery.resilient_recover_state') as mock_recover:
            # First call returns None (no state), second call with recovery option returns state
            mock_recover.side_effect = [None, expected_state]
            
            # Act
            result = await get_most_recent_state(mock_session_id, mock_db)
            
            # Assert
            self.assertEqual(result, expected_state)
            self.assertEqual(mock_recover.call_count, 2)
    
    async def test_process_pending_operations_with_checkpoints(self):
        """Test processing of pending checkpoint operations."""
        # Arrange
        mock_state = {
            "execution": {
                "pending_checkpoints": [
                    {"state": {"key": "value1"}, "session_id": "session1", "name": "checkpoint1"},
                    {"state": {"key": "value2"}, "session_id": "session2", "name": "checkpoint2"}
                ]
            }
        }
        
        with patch('backend.brain.native_graph.state_recovery.resilient_create_checkpoint') as mock_create:
            mock_create.return_value = "checkpoint_id"
            
            # Act
            processed_state = await process_pending_operations(mock_state)
            
            # Assert
            # Verify the checkpoints were processed and removed
            self.assertNotIn("pending_checkpoints", processed_state["execution"])
            # Verify the create_checkpoint was called for each pending checkpoint
            self.assertEqual(mock_create.call_count, 2)


if __name__ == "__main__":
    unittest.main()