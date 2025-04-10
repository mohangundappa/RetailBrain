"""
Base service interfaces for Staples Brain core components.

This module defines the base interfaces and abstract classes for all core services,
establishing a consistent API contract across the system.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

class CoreService(ABC):
    """Base interface for all core services in Staples Brain."""
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the service with required resources.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service.
        
        Returns:
            Dictionary containing service metadata
        """
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the service.
        
        Returns:
            Dictionary containing health status information
        """
        pass


class CoreServiceRegistry:
    """
    Registry for core services to enable discovery and dependency injection.
    
    This class maintains a registry of all core services and provides methods
    to register, discover, and retrieve service instances.
    """
    
    def __init__(self):
        """Initialize the service registry."""
        self._services = {}
        self._service_metadata = {}
        self._startup_time = datetime.now()
    
    def register(self, service_name: str, service: CoreService, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a core service.
        
        Args:
            service_name: Unique name for the service
            service: Service instance
            metadata: Optional metadata about the service
        """
        if service_name in self._services:
            raise ValueError(f"Service '{service_name}' is already registered")
        
        self._services[service_name] = service
        self._service_metadata[service_name] = metadata or {}
        self._service_metadata[service_name]["registered_at"] = datetime.now().isoformat()
    
    def get_service(self, service_name: str) -> Optional[CoreService]:
        """
        Get a service by name.
        
        Args:
            service_name: Service name to retrieve
            
        Returns:
            Service instance or None if not found
        """
        return self._services.get(service_name)
    
    def has_service(self, service_name: str) -> bool:
        """
        Check if a service is registered.
        
        Args:
            service_name: Service name to check
            
        Returns:
            True if the service is registered, False otherwise
        """
        return service_name in self._services
    
    def get_all_services(self) -> Dict[str, CoreService]:
        """
        Get all registered services.
        
        Returns:
            Dictionary mapping service names to instances
        """
        return self._services.copy()
    
    def get_service_names(self) -> List[str]:
        """
        Get names of all registered services.
        
        Returns:
            List of service names
        """
        return list(self._services.keys())
    
    def get_service_metadata(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a service.
        
        Args:
            service_name: Service name
            
        Returns:
            Metadata dictionary or None if service not found
        """
        return self._service_metadata.get(service_name)
    
    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get information about the registry.
        
        Returns:
            Dictionary containing registry metadata
        """
        return {
            "service_count": len(self._services),
            "services": self.get_service_names(),
            "startup_time": self._startup_time.isoformat(),
            "uptime_seconds": (datetime.now() - self._startup_time).total_seconds()
        }


# Global service registry instance
service_registry = CoreServiceRegistry()