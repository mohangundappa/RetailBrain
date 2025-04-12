"""
Tests for state recovery mechanisms.

This module tests the state recovery and resilience functionality
in the state_recovery.py module.
"""
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
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


class TestWithRetry:
    """Tests for the with_retry decorator."""
    
    @pytest.mark.asyncio
    async def test_with_retry_success_first_attempt(self):
        """Test successful execution on the first attempt."""
        # Arrange
        mock_func = AsyncMock(return_value="success")
        
        # Apply the decorator
        decorated_func = with_retry(
            max_attempts=3,
            retry_interval=0.01,
            exponential_backoff=1.5
        )(mock_func)
        
        # Act
        result = await decorated_func("arg1", key="value")
        
        # Assert
        assert result == "success"
        mock_func.assert_called_once_with("arg1", key="value")
    
    @pytest.mark.asyncio
    async def test_with_retry_success_after_retries(self):
        """Test successful execution after several retries."""
        # Arrange
        mock_func = AsyncMock()
        # Function fails twice, then succeeds
        mock_func.side_effect = [
            Exception("Database error"),
            Exception("Database error"),
            "success"
        ]
        
        # Apply the decorator
        decorated_func = with_retry(
            max_attempts=3,
            retry_interval=0.01,  # Short delay for testing
            exponential_backoff=1.0  # No backoff for faster testing
        )(mock_func)
        
        # Act
        result = await decorated_func()
        
        # Assert
        assert result == "success"
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_with_retry_all_attempts_fail(self):
        """Test behavior when all retry attempts fail."""
        # Arrange
        mock_func = AsyncMock()
        original_error = Exception("Persistent database error")
        # Function always fails
        mock_func.side_effect = original_error
        
        # Apply the decorator
        decorated_func = with_retry(
            max_attempts=2,
            retry_interval=0.01  # Short delay for testing
        )(mock_func)
        
        # Act/Assert
        with pytest.raises(Exception) as excinfo:
            await decorated_func()
        
        # Verify that the original error is propagated
        assert str(excinfo.value) == str(original_error)
        assert mock_func.call_count == 2


class TestResilientStatePersistence:
    """Tests for resilient state persistence functions."""
    
    @pytest.fixture
    def db_session(self):
        """Mock database session fixture."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_resilient_persist_state_success(self, db_session):
        """Test successful state persistence."""
        # Arrange
        test_state = {"key": "value"}
        session_id = "test_session_id"
        
        # Mock the persist_state function
        with patch('backend.brain.native_graph.state_recovery.persist_state') as mock_persist:
            mock_persist.return_value = test_state  # persist_state returns the state
            
            # Act
            result = await resilient_persist_state(test_state, session_id, db_session)
            
            # Assert
            assert result == test_state
            mock_persist.assert_called_once_with(test_state, session_id, db_session, None)
    
    @pytest.mark.asyncio
    async def test_resilient_persist_state_db_error_with_retry(self, db_session):
        """Test persistence with DB error that succeeds after retry."""
        # Arrange
        test_state = {"key": "value"}
        session_id = "test_session_id"
        
        # Mock the persist_state function to fail once then succeed
        with patch('backend.brain.native_graph.state_recovery.persist_state') as mock_persist:
            mock_persist.side_effect = [
                Exception("Database error"),  # First call fails
                test_state  # Second call succeeds
            ]
            
            # Mock check_db_connection to return True (DB is available)
            with patch('backend.brain.native_graph.state_recovery.check_db_connection') as mock_check:
                mock_check.return_value = True
                
                # Act
                result = await resilient_persist_state(
                    test_state, 
                    session_id, 
                    db_session,
                    max_retries=2,
                    retry_delay=0.01  # Short delay for testing
                )
                
                # Assert
                assert result == test_state
                assert mock_persist.call_count == 2
                mock_check.assert_called_once_with(db_session)
    
    @pytest.mark.asyncio
    async def test_resilient_persist_state_db_unavailable(self, db_session):
        """Test persistence when DB is unavailable and recovery mode is enabled."""
        # Arrange
        test_state = {"key": "value"}
        session_id = "test_session_id"
        
        # Mock the persist_state function to always fail
        with patch('backend.brain.native_graph.state_recovery.persist_state') as mock_persist:
            mock_persist.side_effect = Exception("Database error")
            
            # Mock check_db_connection to return False (DB is unavailable)
            with patch('backend.brain.native_graph.state_recovery.check_db_connection') as mock_check:
                mock_check.return_value = False
                
                # Mock cache operations
                with patch('backend.brain.native_graph.state_recovery.store_in_recovery_cache') as mock_store:
                    # Act
                    result = await resilient_persist_state(
                        test_state, 
                        session_id, 
                        db_session,
                        max_retries=1,
                        retry_delay=0.01,  # Short delay for testing
                        enable_recovery_mode=True
                    )
                    
                    # Assert
                    assert result == test_state  # Should return the original state
                    mock_persist.assert_called_once()
                    mock_check.assert_called_once_with(db_session)
                    mock_store.assert_called_once()  # Verify operation was cached


class TestResilientStateRecovery:
    """Tests for resilient state recovery functions."""
    
    @pytest.fixture
    def db_session(self):
        """Mock database session fixture."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_resilient_recover_state_success(self, db_session):
        """Test successful state recovery."""
        # Arrange
        session_id = "test_session_id"
        expected_state = {"key": "value"}
        
        # Mock the load_state function
        with patch('backend.brain.native_graph.state_recovery.load_state') as mock_load:
            mock_load.return_value = expected_state
            
            # Act
            result = await resilient_recover_state(session_id, db_session)
            
            # Assert
            assert result == expected_state
            mock_load.assert_called_once_with(session_id, None, db_session)
    
    @pytest.mark.asyncio
    async def test_resilient_recover_state_db_error_with_retry(self, db_session):
        """Test recovery with DB error that succeeds after retry."""
        # Arrange
        session_id = "test_session_id"
        expected_state = {"key": "value"}
        
        # Mock the load_state function to fail once then succeed
        with patch('backend.brain.native_graph.state_recovery.load_state') as mock_load:
            mock_load.side_effect = [
                Exception("Database error"),  # First call fails
                expected_state  # Second call succeeds
            ]
            
            # Mock check_db_connection to return True (DB is available)
            with patch('backend.brain.native_graph.state_recovery.check_db_connection') as mock_check:
                mock_check.return_value = True
                
                # Act
                result = await resilient_recover_state(
                    session_id, 
                    db_session,
                    max_retries=2,
                    retry_delay=0.01  # Short delay for testing
                )
                
                # Assert
                assert result == expected_state
                assert mock_load.call_count == 2
                mock_check.assert_called_once_with(db_session)
    
    @pytest.mark.asyncio
    async def test_resilient_recover_state_not_found_returning_empty(self, db_session):
        """Test recovery when state is not found and return_empty_state is True."""
        # Arrange
        session_id = "test_session_id"
        
        # Mock the load_state function to return None (state not found)
        with patch('backend.brain.native_graph.state_recovery.load_state') as mock_load:
            mock_load.return_value = None
            
            # Act
            result = await resilient_recover_state(
                session_id, 
                db_session,
                return_empty_state=True
            )
            
            # Assert
            assert result == {}  # Should return empty dict
            mock_load.assert_called_once()


class TestResilientCheckpoint:
    """Tests for resilient checkpoint functions."""
    
    @pytest.fixture
    def db_session(self):
        """Mock database session fixture."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_resilient_create_checkpoint_success(self, db_session):
        """Test successful checkpoint creation."""
        # Arrange
        test_state = {"key": "value"}
        session_id = "test_session_id"
        checkpoint_name = "test_checkpoint"
        expected_checkpoint_id = "checkpoint_123"
        
        # Mock the create_checkpoint function
        with patch('backend.brain.native_graph.state_recovery.create_checkpoint') as mock_create:
            mock_create.return_value = expected_checkpoint_id
            
            # Act
            result = await resilient_create_checkpoint(
                test_state, 
                session_id, 
                checkpoint_name, 
                db_session
            )
            
            # Assert
            assert result == expected_checkpoint_id
            mock_create.assert_called_once_with(
                test_state, 
                session_id, 
                checkpoint_name, 
                db_session
            )
    
    @pytest.mark.asyncio
    async def test_resilient_create_checkpoint_db_error_with_retry(self, db_session):
        """Test checkpoint creation with DB error that succeeds after retry."""
        # Arrange
        test_state = {"key": "value"}
        session_id = "test_session_id"
        checkpoint_name = "test_checkpoint"
        expected_checkpoint_id = "checkpoint_123"
        
        # Mock the create_checkpoint function to fail once then succeed
        with patch('backend.brain.native_graph.state_recovery.create_checkpoint') as mock_create:
            mock_create.side_effect = [
                Exception("Database error"),  # First call fails
                expected_checkpoint_id  # Second call succeeds
            ]
            
            # Mock check_db_connection to return True (DB is available)
            with patch('backend.brain.native_graph.state_recovery.check_db_connection') as mock_check:
                mock_check.return_value = True
                
                # Act
                result = await resilient_create_checkpoint(
                    test_state, 
                    session_id, 
                    checkpoint_name, 
                    db_session,
                    max_retries=2,
                    retry_delay=0.01  # Short delay for testing
                )
                
                # Assert
                assert result == expected_checkpoint_id
                assert mock_create.call_count == 2
                mock_check.assert_called_once_with(db_session)


class TestResilientRollback:
    """Tests for resilient rollback functions."""
    
    @pytest.fixture
    def db_session(self):
        """Mock database session fixture."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_resilient_rollback_to_checkpoint_success(self, db_session):
        """Test successful rollback to checkpoint."""
        # Arrange
        session_id = "test_session_id"
        checkpoint_name = "test_checkpoint"
        expected_state = {"key": "checkpoint_value"}
        
        # Mock the rollback_to_checkpoint function
        with patch('backend.brain.native_graph.state_recovery.rollback_to_checkpoint') as mock_rollback:
            mock_rollback.return_value = expected_state
            
            # Act
            result = await resilient_rollback_to_checkpoint(
                session_id, 
                db_session,
                checkpoint_name
            )
            
            # Assert
            assert result == expected_state
            mock_rollback.assert_called_once_with(
                session_id, 
                checkpoint_name, 
                db_session
            )
    
    @pytest.mark.asyncio
    async def test_resilient_rollback_to_checkpoint_db_error_with_retry(self, db_session):
        """Test rollback with DB error that succeeds after retry."""
        # Arrange
        session_id = "test_session_id"
        checkpoint_name = "test_checkpoint"
        expected_state = {"key": "checkpoint_value"}
        
        # Mock the rollback_to_checkpoint function to fail once then succeed
        with patch('backend.brain.native_graph.state_recovery.rollback_to_checkpoint') as mock_rollback:
            mock_rollback.side_effect = [
                Exception("Database error"),  # First call fails
                expected_state  # Second call succeeds
            ]
            
            # Mock check_db_connection to return True (DB is available)
            with patch('backend.brain.native_graph.state_recovery.check_db_connection') as mock_check:
                mock_check.return_value = True
                
                # Act
                result = await resilient_rollback_to_checkpoint(
                    session_id, 
                    db_session,
                    checkpoint_name,
                    max_retries=2,
                    retry_delay=0.01  # Short delay for testing
                )
                
                # Assert
                assert result == expected_state
                assert mock_rollback.call_count == 2
                mock_check.assert_called_once_with(db_session)
    
    @pytest.mark.asyncio
    async def test_resilient_rollback_to_checkpoint_not_found(self, db_session):
        """Test rollback when checkpoint is not found."""
        # Arrange
        session_id = "test_session_id"
        checkpoint_name = "nonexistent_checkpoint"
        
        # Mock the rollback_to_checkpoint function to return None (checkpoint not found)
        with patch('backend.brain.native_graph.state_recovery.rollback_to_checkpoint') as mock_rollback:
            mock_rollback.return_value = None
            
            # Act
            result = await resilient_rollback_to_checkpoint(
                session_id, 
                db_session,
                checkpoint_name
            )
            
            # Assert
            assert result is None
            mock_rollback.assert_called_once()


class TestRecoveryOperations:
    """Tests for recovery operations and cache mechanisms."""
    
    @pytest.fixture
    def db_session(self):
        """Mock database session fixture."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_process_pending_operations_empty_cache(self, db_session):
        """Test processing when there are no pending operations in the cache."""
        # Mock the get_recovery_cache function to return empty cache
        with patch('backend.brain.native_graph.state_recovery.get_recovery_cache') as mock_get_cache:
            mock_get_cache.return_value = []
            
            # Mock the clear_recovery_cache function
            with patch('backend.brain.native_graph.state_recovery.clear_recovery_cache') as mock_clear:
                # Act
                processed = await process_pending_operations(db_session)
                
                # Assert
                assert processed == 0
                mock_get_cache.assert_called_once()
                mock_clear.assert_not_called()  # Cache wasn't cleared because it was empty
    
    @pytest.mark.asyncio
    async def test_process_pending_operations_with_items(self, db_session):
        """Test processing when there are pending operations in the cache."""
        # Create mock operations in the cache
        mock_operations = [
            {"type": "persist_state", "state": {"key": "value1"}, "session_id": "session1"},
            {"type": "create_checkpoint", "state": {"key": "value2"}, "session_id": "session2", "checkpoint_name": "cp1"}
        ]
        
        # Mock the get_recovery_cache function to return operations
        with patch('backend.brain.native_graph.state_recovery.get_recovery_cache') as mock_get_cache:
            mock_get_cache.return_value = mock_operations
            
            # Mock operation functions
            with patch('backend.brain.native_graph.state_recovery.persist_state') as mock_persist:
                with patch('backend.brain.native_graph.state_recovery.create_checkpoint') as mock_checkpoint:
                    # Mock clear_recovery_cache
                    with patch('backend.brain.native_graph.state_recovery.clear_recovery_cache') as mock_clear:
                        # Act
                        processed = await process_pending_operations(db_session)
                        
                        # Assert
                        assert processed == 2
                        mock_get_cache.assert_called_once()
                        mock_persist.assert_called_once()
                        mock_checkpoint.assert_called_once()
                        mock_clear.assert_called_once()  # Cache was cleared after processing
    
    @pytest.mark.asyncio
    async def test_check_db_connection_success(self, db_session):
        """Test DB connection check when connection is successful."""
        # Mock db.execute to succeed
        query_result = AsyncMock()
        db_session.execute.return_value = query_result
        
        # Act
        result = await check_db_connection(db_session)
        
        # Assert
        assert result is True
        db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_db_connection_failure(self, db_session):
        """Test DB connection check when connection fails."""
        # Mock db.execute to fail
        db_session.execute.side_effect = Exception("Connection refused")
        
        # Act
        result = await check_db_connection(db_session)
        
        # Assert
        assert result is False
        db_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_most_recent_state_success(self, db_session):
        """Test getting the most recent state successfully."""
        # Arrange
        session_id = "test_session_id"
        expected_state = {"key": "latest_value"}
        
        # Mock the load_state function
        with patch('backend.brain.native_graph.state_recovery.load_state') as mock_load:
            mock_load.return_value = expected_state
            
            # Act
            result = await get_most_recent_state(session_id, db_session)
            
            # Assert
            assert result == expected_state
            mock_load.assert_called_once_with(session_id, None, db_session)
    
    @pytest.mark.asyncio
    async def test_get_most_recent_state_from_checkpoint(self, db_session):
        """Test falling back to most recent checkpoint when normal state loading fails."""
        # Arrange
        session_id = "test_session_id"
        checkpoint_state = {"key": "checkpoint_value"}
        
        # Mock load_state to fail, then mock rollback_to_checkpoint to succeed
        with patch('backend.brain.native_graph.state_recovery.load_state') as mock_load:
            mock_load.return_value = None  # No regular state found
            
            with patch('backend.brain.native_graph.state_recovery.rollback_to_checkpoint') as mock_rollback:
                mock_rollback.return_value = checkpoint_state
                
                # Act
                result = await get_most_recent_state(session_id, db_session)
                
                # Assert
                assert result == checkpoint_state
                mock_load.assert_called_once()
                mock_rollback.assert_called_once_with(session_id, None, db_session)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])