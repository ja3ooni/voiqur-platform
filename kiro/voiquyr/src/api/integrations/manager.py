"""
Integration Manager

Central manager for all third-party integrations with the EUVoice AI Platform.
Handles integration lifecycle, configuration, and coordination.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Type, Union
from datetime import datetime
import json

from .base import BaseIntegration, IntegrationConfig, IntegrationType, IntegrationStatus, IntegrationError
from .telephony import TwilioIntegration, TwilioConfig
from .crm import SalesforceIntegration, SAPIntegration, SalesforceConfig, SAPConfig
from .messaging import WhatsAppIntegration, TelegramIntegration, SlackIntegration, WhatsAppConfig, TelegramConfig, SlackConfig


class IntegrationManager:
    """
    Central manager for all third-party integrations.
    
    Provides unified interface for managing integrations, handling events,
    and coordinating between different integration types.
    """
    
    def __init__(self):
        """Initialize integration manager."""
        self.logger = logging.getLogger(__name__)
        
        # Integration registry
        self.integrations: Dict[str, BaseIntegration] = {}
        self.integration_configs: Dict[str, IntegrationConfig] = {}
        
        # Integration type mappings
        self.integration_classes = {
            "twilio": TwilioIntegration,
            "salesforce": SalesforceIntegration,
            "sap": SAPIntegration,
            "whatsapp": WhatsAppIntegration,
            "telegram": TelegramIntegration,
            "slack": SlackIntegration
        }
        
        self.config_classes = {
            "twilio": TwilioConfig,
            "salesforce": SalesforceConfig,
            "sap": SAPConfig,
            "whatsapp": WhatsAppConfig,
            "telegram": TelegramConfig,
            "slack": SlackConfig
        }
        
        # Event handlers
        self.event_handlers = {}
        
        # Background tasks
        self.health_check_task = None
        self.is_running = False
    
    async def start(self) -> None:
        """Start the integration manager."""
        try:
            self.logger.info("Starting Integration Manager")
            self.is_running = True
            
            # Start background health checks
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            self.logger.info("Integration Manager started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Integration Manager: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the integration manager."""
        try:
            self.logger.info("Stopping Integration Manager")
            self.is_running = False
            
            # Cancel background tasks
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            # Stop all integrations
            for integration in list(self.integrations.values()):
                await integration.stop()
            
            self.integrations.clear()
            self.integration_configs.clear()
            
            self.logger.info("Integration Manager stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping Integration Manager: {e}")
    
    # Integration Lifecycle Management
    
    async def create_integration(self, 
                               provider: str,
                               config_data: Dict[str, Any],
                               auto_start: bool = True) -> str:
        """
        Create a new integration.
        
        Args:
            provider: Integration provider (twilio, salesforce, etc.)
            config_data: Configuration data
            auto_start: Whether to start the integration automatically
            
        Returns:
            Integration ID
        """
        try:
            # Validate provider
            if provider not in self.integration_classes:
                raise IntegrationError(f"Unknown integration provider: {provider}")
            
            # Create configuration
            config_class = self.config_classes[provider]
            config = config_class(**config_data)
            
            # Create integration instance
            integration_class = self.integration_classes[provider]
            integration = integration_class(config)
            
            # Store integration
            integration_id = config.id
            self.integrations[integration_id] = integration
            self.integration_configs[integration_id] = config
            
            # Register event handlers
            integration.register_event_handler("*", self._handle_integration_event)
            
            # Start integration if requested
            if auto_start:
                success = await integration.start()
                if not success:
                    # Remove failed integration
                    del self.integrations[integration_id]
                    del self.integration_configs[integration_id]
                    raise IntegrationError(f"Failed to start {provider} integration")
            
            self.logger.info(f"Created {provider} integration: {integration_id}")
            return integration_id
            
        except Exception as e:
            self.logger.error(f"Failed to create {provider} integration: {e}")
            raise
    
    async def start_integration(self, integration_id: str) -> bool:
        """
        Start an integration.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            True if started successfully
        """
        try:
            if integration_id not in self.integrations:
                raise IntegrationError(f"Integration not found: {integration_id}")
            
            integration = self.integrations[integration_id]
            success = await integration.start()
            
            if success:
                self.logger.info(f"Started integration: {integration_id}")
            else:
                self.logger.error(f"Failed to start integration: {integration_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error starting integration {integration_id}: {e}")
            return False
    
    async def stop_integration(self, integration_id: str) -> bool:
        """
        Stop an integration.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            True if stopped successfully
        """
        try:
            if integration_id not in self.integrations:
                raise IntegrationError(f"Integration not found: {integration_id}")
            
            integration = self.integrations[integration_id]
            await integration.stop()
            
            self.logger.info(f"Stopped integration: {integration_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping integration {integration_id}: {e}")
            return False
    
    async def delete_integration(self, integration_id: str) -> bool:
        """
        Delete an integration.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            True if deleted successfully
        """
        try:
            if integration_id not in self.integrations:
                raise IntegrationError(f"Integration not found: {integration_id}")
            
            # Stop integration first
            await self.stop_integration(integration_id)
            
            # Remove from registry
            del self.integrations[integration_id]
            del self.integration_configs[integration_id]
            
            self.logger.info(f"Deleted integration: {integration_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting integration {integration_id}: {e}")
            return False
    
    async def update_integration_config(self, 
                                      integration_id: str,
                                      updates: Dict[str, Any]) -> bool:
        """
        Update integration configuration.
        
        Args:
            integration_id: Integration ID
            updates: Configuration updates
            
        Returns:
            True if updated successfully
        """
        try:
            if integration_id not in self.integrations:
                raise IntegrationError(f"Integration not found: {integration_id}")
            
            integration = self.integrations[integration_id]
            success = await integration.update_config(updates)
            
            if success:
                # Update stored config
                config = self.integration_configs[integration_id]
                for key, value in updates.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
                config.updated_at = datetime.utcnow()
                
                self.logger.info(f"Updated integration config: {integration_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating integration config {integration_id}: {e}")
            return False
    
    # Integration Information and Status
    
    def list_integrations(self, 
                         integration_type: Optional[IntegrationType] = None,
                         status: Optional[IntegrationStatus] = None) -> List[Dict[str, Any]]:
        """
        List all integrations with optional filtering.
        
        Args:
            integration_type: Filter by integration type
            status: Filter by status
            
        Returns:
            List of integration information
        """
        integrations = []
        
        for integration_id, integration in self.integrations.items():
            config = self.integration_configs[integration_id]
            
            # Apply filters
            if integration_type and config.type != integration_type:
                continue
            
            if status and integration.status != status:
                continue
            
            integrations.append(integration.get_status())
        
        return integrations
    
    def get_integration(self, integration_id: str) -> Optional[BaseIntegration]:
        """
        Get integration by ID.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            Integration instance or None if not found
        """
        return self.integrations.get(integration_id)
    
    def get_integration_config(self, integration_id: str) -> Optional[IntegrationConfig]:
        """
        Get integration configuration by ID.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            Integration configuration or None if not found
        """
        return self.integration_configs.get(integration_id)
    
    def get_integration_status(self, integration_id: str) -> Optional[Dict[str, Any]]:
        """
        Get integration status information.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            Status information or None if not found
        """
        if integration_id not in self.integrations:
            return None
        
        integration = self.integrations[integration_id]
        return integration.get_status()
    
    async def test_integration(self, integration_id: str) -> Dict[str, Any]:
        """
        Test an integration connection.
        
        Args:
            integration_id: Integration ID
            
        Returns:
            Test results
        """
        try:
            if integration_id not in self.integrations:
                raise IntegrationError(f"Integration not found: {integration_id}")
            
            integration = self.integrations[integration_id]
            return await integration.test_connection()
            
        except Exception as e:
            self.logger.error(f"Error testing integration {integration_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Integration Operations
    
    async def send_message(self, 
                          integration_id: str,
                          recipient: str,
                          message: str,
                          **kwargs) -> bool:
        """
        Send message through an integration.
        
        Args:
            integration_id: Integration ID
            recipient: Message recipient
            message: Message content
            **kwargs: Additional parameters
            
        Returns:
            True if sent successfully
        """
        try:
            integration = self.get_integration(integration_id)
            if not integration:
                raise IntegrationError(f"Integration not found: {integration_id}")
            
            # Check if integration supports messaging
            if not hasattr(integration, 'send_message'):
                raise IntegrationError(f"Integration {integration_id} does not support messaging")
            
            result = await integration.send_message(recipient, message, **kwargs)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Error sending message through integration {integration_id}: {e}")
            return False
    
    async def make_call(self, 
                       integration_id: str,
                       to_number: str,
                       **kwargs) -> bool:
        """
        Make a call through a telephony integration.
        
        Args:
            integration_id: Integration ID
            to_number: Destination number
            **kwargs: Additional parameters
            
        Returns:
            True if call initiated successfully
        """
        try:
            integration = self.get_integration(integration_id)
            if not integration:
                raise IntegrationError(f"Integration not found: {integration_id}")
            
            # Check if integration supports calling
            if not hasattr(integration, 'make_call'):
                raise IntegrationError(f"Integration {integration_id} does not support calling")
            
            result = await integration.make_call(to_number, **kwargs)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Error making call through integration {integration_id}: {e}")
            return False
    
    async def search_contacts(self, 
                            integration_id: str,
                            **search_params) -> List[Any]:
        """
        Search contacts through a CRM integration.
        
        Args:
            integration_id: Integration ID
            **search_params: Search parameters
            
        Returns:
            List of contacts
        """
        try:
            integration = self.get_integration(integration_id)
            if not integration:
                raise IntegrationError(f"Integration not found: {integration_id}")
            
            # Check if integration supports contact search
            if not hasattr(integration, 'search_contacts'):
                raise IntegrationError(f"Integration {integration_id} does not support contact search")
            
            return await integration.search_contacts(**search_params)
            
        except Exception as e:
            self.logger.error(f"Error searching contacts through integration {integration_id}: {e}")
            return []
    
    # Event Handling
    
    def register_event_handler(self, event_type: str, handler):
        """
        Register global event handler.
        
        Args:
            event_type: Event type to handle
            handler: Event handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def _handle_integration_event(self, event):
        """Handle events from integrations."""
        try:
            event_type = event.event_type
            
            # Call registered handlers
            if event_type in self.event_handlers:
                for handler in self.event_handlers[event_type]:
                    try:
                        await handler(event)
                    except Exception as e:
                        self.logger.error(f"Error in event handler for {event_type}: {e}")
            
            # Call wildcard handlers
            if "*" in self.event_handlers:
                for handler in self.event_handlers["*"]:
                    try:
                        await handler(event)
                    except Exception as e:
                        self.logger.error(f"Error in wildcard event handler: {e}")
            
        except Exception as e:
            self.logger.error(f"Error handling integration event: {e}")
    
    # Webhook Handling
    
    async def handle_webhook(self, 
                           integration_id: str,
                           webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle webhook from an integration.
        
        Args:
            integration_id: Integration ID
            webhook_data: Webhook payload
            
        Returns:
            Response data
        """
        try:
            integration = self.get_integration(integration_id)
            if not integration:
                return {"status": "error", "message": f"Integration not found: {integration_id}"}
            
            # Check if integration supports webhooks
            if not hasattr(integration, 'handle_webhook'):
                return {"status": "error", "message": f"Integration {integration_id} does not support webhooks"}
            
            return await integration.handle_webhook(webhook_data)
            
        except Exception as e:
            self.logger.error(f"Error handling webhook for integration {integration_id}: {e}")
            return {"status": "error", "message": str(e)}
    
    # Background Tasks
    
    async def _health_check_loop(self) -> None:
        """Background task for health checking integrations."""
        while self.is_running:
            try:
                # Check health of all active integrations
                for integration_id, integration in self.integrations.items():
                    if integration.status == IntegrationStatus.ACTIVE:
                        try:
                            healthy = await integration.health_check()
                            if not healthy:
                                self.logger.warning(f"Health check failed for integration {integration_id}")
                                integration.status = IntegrationStatus.ERROR
                        except Exception as e:
                            self.logger.error(f"Health check error for integration {integration_id}: {e}")
                            integration.status = IntegrationStatus.ERROR
                
                # Wait before next check
                await asyncio.sleep(300)  # 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(60)
    
    # Utility Methods
    
    def get_integrations_by_type(self, integration_type: IntegrationType) -> List[BaseIntegration]:
        """
        Get all integrations of a specific type.
        
        Args:
            integration_type: Integration type
            
        Returns:
            List of integrations
        """
        integrations = []
        
        for integration_id, integration in self.integrations.items():
            config = self.integration_configs[integration_id]
            if config.type == integration_type:
                integrations.append(integration)
        
        return integrations
    
    def get_active_integrations(self) -> List[BaseIntegration]:
        """
        Get all active integrations.
        
        Returns:
            List of active integrations
        """
        return [
            integration for integration in self.integrations.values()
            if integration.status == IntegrationStatus.ACTIVE
        ]
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """
        Get integration manager statistics.
        
        Returns:
            Manager statistics
        """
        stats = {
            "total_integrations": len(self.integrations),
            "active_integrations": len([
                i for i in self.integrations.values() 
                if i.status == IntegrationStatus.ACTIVE
            ]),
            "integrations_by_type": {},
            "integrations_by_status": {},
            "is_running": self.is_running
        }
        
        # Count by type
        for config in self.integration_configs.values():
            type_name = config.type.value
            stats["integrations_by_type"][type_name] = stats["integrations_by_type"].get(type_name, 0) + 1
        
        # Count by status
        for integration in self.integrations.values():
            status_name = integration.status.value
            stats["integrations_by_status"][status_name] = stats["integrations_by_status"].get(status_name, 0) + 1
        
        return stats


# Global integration manager instance
_integration_manager: Optional[IntegrationManager] = None


def get_integration_manager() -> Optional[IntegrationManager]:
    """Get the global integration manager instance."""
    return _integration_manager


def set_integration_manager(manager: IntegrationManager) -> None:
    """Set the global integration manager instance."""
    global _integration_manager
    _integration_manager = manager