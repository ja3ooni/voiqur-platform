"""
Telephony Provider Registry

Manages registration and discovery of telephony providers.
Implements provider factory pattern for creating provider instances.
"""

import logging
from typing import Dict, List, Optional, Type
from .base import TelephonyProvider, ProviderType, ProviderConfig, HealthStatus

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry for telephony providers
    
    Manages provider registration, instantiation, and discovery.
    """
    
    def __init__(self):
        """Initialize provider registry"""
        self._provider_classes: Dict[ProviderType, Type[TelephonyProvider]] = {}
        self._provider_instances: Dict[str, TelephonyProvider] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_provider_class(
        self,
        provider_type: ProviderType,
        provider_class: Type[TelephonyProvider]
    ) -> None:
        """
        Register a provider class
        
        Args:
            provider_type: Type of provider
            provider_class: Provider class to register
        """
        if not issubclass(provider_class, TelephonyProvider):
            raise ValueError(
                f"Provider class must inherit from TelephonyProvider"
            )
        
        self._provider_classes[provider_type] = provider_class
        self.logger.info(
            f"Registered provider class: {provider_type.value} -> "
            f"{provider_class.__name__}"
        )
    
    def create_provider(
        self,
        config: ProviderConfig
    ) -> TelephonyProvider:
        """
        Create a provider instance
        
        Args:
            config: Provider configuration
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider type not registered
        """
        provider_class = self._provider_classes.get(config.provider_type)
        
        if not provider_class:
            raise ValueError(
                f"Provider type {config.provider_type.value} not registered. "
                f"Available types: {[t.value for t in self._provider_classes.keys()]}"
            )
        
        provider = provider_class(config)
        self._provider_instances[config.provider_id] = provider
        
        self.logger.info(
            f"Created provider instance: {config.provider_id} "
            f"({config.provider_type.value})"
        )
        
        return provider
    
    def get_provider(self, provider_id: str) -> Optional[TelephonyProvider]:
        """
        Get a provider instance by ID
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Provider instance or None
        """
        return self._provider_instances.get(provider_id)
    
    def get_all_providers(self) -> List[TelephonyProvider]:
        """Get all registered provider instances"""
        return list(self._provider_instances.values())
    
    def get_providers_by_type(
        self,
        provider_type: ProviderType
    ) -> List[TelephonyProvider]:
        """
        Get all providers of a specific type
        
        Args:
            provider_type: Provider type to filter by
            
        Returns:
            List of matching providers
        """
        return [
            p for p in self._provider_instances.values()
            if p.config.provider_type == provider_type
        ]
    
    def get_healthy_providers(self) -> List[TelephonyProvider]:
        """Get all healthy providers"""
        return [
            p for p in self._provider_instances.values()
            if p.health_status == HealthStatus.HEALTHY
        ]
    
    def remove_provider(self, provider_id: str) -> bool:
        """
        Remove a provider instance
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            True if removed, False if not found
        """
        if provider_id in self._provider_instances:
            del self._provider_instances[provider_id]
            self.logger.info(f"Removed provider: {provider_id}")
            return True
        return False
    
    def get_registered_types(self) -> List[ProviderType]:
        """Get list of registered provider types"""
        return list(self._provider_classes.keys())
    
    def is_type_registered(self, provider_type: ProviderType) -> bool:
        """Check if a provider type is registered"""
        return provider_type in self._provider_classes


# Global registry instance
_global_registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    """Get the global provider registry"""
    return _global_registry


def register_provider(
    provider_type: ProviderType,
    provider_class: Type[TelephonyProvider]
) -> None:
    """
    Register a provider class with the global registry
    
    Args:
        provider_type: Type of provider
        provider_class: Provider class to register
    """
    _global_registry.register_provider_class(provider_type, provider_class)
