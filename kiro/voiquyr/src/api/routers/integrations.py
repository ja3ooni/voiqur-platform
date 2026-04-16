"""
Integrations Router

API endpoints for managing third-party integrations including
telephony, CRM, and messaging platform connections.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ..auth import AuthManager, User, get_current_user
from ..integrations.manager import IntegrationManager, get_integration_manager
from ..integrations.base import IntegrationType, IntegrationStatus
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models

class IntegrationCreateRequest(BaseModel):
    """Request model for creating integrations."""
    
    provider: str = Field(description="Integration provider (twilio, salesforce, etc.)")
    name: str = Field(description="Integration name")
    config: Dict[str, Any] = Field(description="Provider-specific configuration")
    auto_start: bool = Field(default=True, description="Auto-start integration after creation")


class IntegrationUpdateRequest(BaseModel):
    """Request model for updating integrations."""
    
    name: Optional[str] = Field(default=None, description="Updated name")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Updated configuration")
    enabled: Optional[bool] = Field(default=None, description="Enable/disable integration")


class IntegrationResponse(BaseModel):
    """Response model for integration information."""
    
    id: str
    name: str
    provider: str
    type: str
    status: str
    enabled: bool
    created_at: str
    updated_at: str
    metrics: Dict[str, Any]


class IntegrationListResponse(BaseModel):
    """Response model for integration listing."""
    
    integrations: List[IntegrationResponse]
    total: int
    active: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]


class MessageRequest(BaseModel):
    """Request model for sending messages."""
    
    recipient: str = Field(description="Message recipient (phone, email, chat ID)")
    message: str = Field(description="Message content")
    message_type: str = Field(default="text", description="Message type")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional options")


class CallRequest(BaseModel):
    """Request model for making calls."""
    
    to_number: str = Field(description="Destination phone number")
    twiml_url: Optional[str] = Field(default=None, description="TwiML URL")
    record: bool = Field(default=False, description="Record the call")
    options: Dict[str, Any] = Field(default_factory=dict, description="Additional options")


class ContactSearchRequest(BaseModel):
    """Request model for contact search."""
    
    phone: Optional[str] = Field(default=None, description="Phone number")
    email: Optional[str] = Field(default=None, description="Email address")
    name: Optional[str] = Field(default=None, description="Name")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results")


def get_integration_manager_dep() -> IntegrationManager:
    """Dependency to get integration manager."""
    manager = get_integration_manager()
    if not manager:
        raise HTTPException(status_code=503, detail="Integration manager not available")
    return manager


# Integration Management Endpoints

@router.post("/", response_model=Dict[str, str])
async def create_integration(
    request: IntegrationCreateRequest,
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Create a new third-party integration.
    
    Supports creating integrations for telephony (Twilio), CRM (Salesforce, SAP),
    and messaging platforms (WhatsApp, Telegram, Slack).
    """
    try:
        # Add user information to config
        config_data = request.config.copy()
        config_data.update({
            "name": request.name,
            "created_by": current_user.id
        })
        
        # Create integration
        integration_id = await manager.create_integration(
            provider=request.provider,
            config_data=config_data,
            auto_start=request.auto_start
        )
        
        return {
            "integration_id": integration_id,
            "status": "created",
            "message": f"{request.provider} integration created successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to create {request.provider} integration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create integration: {str(e)}")


@router.get("/", response_model=IntegrationListResponse)
async def list_integrations(
    type: Optional[str] = Query(None, description="Filter by integration type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    List all integrations for the current user.
    
    Returns comprehensive information about all configured integrations
    including status, metrics, and configuration details.
    """
    try:
        # Parse filters
        integration_type = None
        if type:
            try:
                integration_type = IntegrationType(type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid integration type: {type}")
        
        integration_status = None
        if status:
            try:
                integration_status = IntegrationStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        # Get integrations
        integrations_data = manager.list_integrations(
            integration_type=integration_type,
            status=integration_status
        )
        
        # Filter by user (if user-specific integrations are implemented)
        # For now, return all integrations
        
        # Convert to response format
        integrations = []
        for integration_data in integrations_data:
            integrations.append(IntegrationResponse(
                id=integration_data["id"],
                name=integration_data["name"],
                provider=integration_data["provider"],
                type=integration_data["type"],
                status=integration_data["status"],
                enabled=integration_data["enabled"],
                created_at=integration_data.get("created_at", datetime.utcnow().isoformat()),
                updated_at=integration_data.get("updated_at", datetime.utcnow().isoformat()),
                metrics=integration_data.get("metrics", {})
            ))
        
        # Get manager stats
        stats = manager.get_manager_stats()
        
        return IntegrationListResponse(
            integrations=integrations,
            total=stats["total_integrations"],
            active=stats["active_integrations"],
            by_type=stats["integrations_by_type"],
            by_status=stats["integrations_by_status"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list integrations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list integrations: {str(e)}")


@router.get("/{integration_id}")
async def get_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Get detailed information about a specific integration.
    
    Returns configuration, status, metrics, and operational details
    for the specified integration.
    """
    try:
        status_info = manager.get_integration_status(integration_id)
        
        if not status_info:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get integration: {str(e)}")


@router.put("/{integration_id}")
async def update_integration(
    integration_id: str,
    request: IntegrationUpdateRequest,
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Update integration configuration.
    
    Allows updating integration settings, credentials, and operational parameters.
    Changes take effect immediately for active integrations.
    """
    try:
        # Prepare updates
        updates = {}
        
        if request.name is not None:
            updates["name"] = request.name
        
        if request.config is not None:
            updates.update(request.config)
        
        if request.enabled is not None:
            updates["enabled"] = request.enabled
        
        # Update integration
        success = await manager.update_integration_config(integration_id, updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Integration not found or update failed")
        
        return {
            "integration_id": integration_id,
            "status": "updated",
            "message": "Integration updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update integration: {str(e)}")


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Delete an integration.
    
    Stops the integration and removes all configuration.
    This action cannot be undone.
    """
    try:
        success = await manager.delete_integration(integration_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Integration not found")
        
        return {
            "integration_id": integration_id,
            "status": "deleted",
            "message": "Integration deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete integration: {str(e)}")


# Integration Control Endpoints

@router.post("/{integration_id}/start")
async def start_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Start an integration.
    
    Initializes the integration, performs authentication, and begins
    active monitoring and event processing.
    """
    try:
        success = await manager.start_integration(integration_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to start integration")
        
        return {
            "integration_id": integration_id,
            "status": "started",
            "message": "Integration started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start integration: {str(e)}")


@router.post("/{integration_id}/stop")
async def stop_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Stop an integration.
    
    Gracefully shuts down the integration, closes connections,
    and stops event processing.
    """
    try:
        success = await manager.stop_integration(integration_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to stop integration")
        
        return {
            "integration_id": integration_id,
            "status": "stopped",
            "message": "Integration stopped successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop integration: {str(e)}")


@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: str,
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Test integration connection.
    
    Performs connectivity and authentication tests to verify
    the integration is properly configured and operational.
    """
    try:
        test_result = await manager.test_integration(integration_id)
        
        return {
            "integration_id": integration_id,
            "test_result": test_result
        }
        
    except Exception as e:
        logger.error(f"Failed to test integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test integration: {str(e)}")


# Integration Operations Endpoints

@router.post("/{integration_id}/message")
async def send_message(
    integration_id: str,
    request: MessageRequest,
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Send message through integration.
    
    Sends text, media, or interactive messages through messaging
    platform integrations (WhatsApp, Telegram, Slack).
    """
    try:
        success = await manager.send_message(
            integration_id=integration_id,
            recipient=request.recipient,
            message=request.message,
            message_type=request.message_type,
            **request.options
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to send message")
        
        return {
            "integration_id": integration_id,
            "status": "sent",
            "message": "Message sent successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message through integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.post("/{integration_id}/call")
async def make_call(
    integration_id: str,
    request: CallRequest,
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Make voice call through telephony integration.
    
    Initiates outbound voice calls through telephony integrations
    like Twilio with support for TwiML and call recording.
    """
    try:
        success = await manager.make_call(
            integration_id=integration_id,
            to_number=request.to_number,
            twiml_url=request.twiml_url,
            record=request.record,
            **request.options
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to make call")
        
        return {
            "integration_id": integration_id,
            "status": "initiated",
            "message": "Call initiated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to make call through integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to make call: {str(e)}")


@router.post("/{integration_id}/contacts/search")
async def search_contacts(
    integration_id: str,
    request: ContactSearchRequest,
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Search contacts through CRM integration.
    
    Searches customer contacts in CRM systems (Salesforce, SAP)
    using phone, email, or name criteria.
    """
    try:
        # Prepare search parameters
        search_params = {}
        if request.phone:
            search_params["phone"] = request.phone
        if request.email:
            search_params["email"] = request.email
        if request.name:
            search_params["name"] = request.name
        search_params["limit"] = request.limit
        
        contacts = await manager.search_contacts(
            integration_id=integration_id,
            **search_params
        )
        
        # Convert contacts to dict format
        contacts_data = []
        for contact in contacts:
            if isinstance(contact, dict):
                contacts_data.append(contact)
            else:
                contacts_data.append({
                    "id": contact.id,
                    "external_id": getattr(contact, "external_id", None),
                    "first_name": getattr(contact, "first_name", None),
                    "last_name": getattr(contact, "last_name", None),
                    "email": getattr(contact, "email", None),
                    "phone": getattr(contact, "phone", None),
                    "mobile": getattr(contact, "mobile", None),
                    "company": getattr(contact, "company", None),
                    "title": getattr(contact, "title", None),
                    "source": getattr(contact, "source", None),
                    "created_date": getattr(contact, "created_date", None),
                    "modified_date": getattr(contact, "modified_date", None),
                })
        
        return {
            "integration_id": integration_id,
            "contacts": contacts_data,
            "total": len(contacts_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search contacts through integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search contacts: {str(e)}")


# Webhook Endpoints

@router.post("/{integration_id}/webhook")
async def handle_integration_webhook(
    integration_id: str,
    webhook_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Handle webhook from third-party integration.
    
    Processes incoming webhooks from integrated services for
    real-time event notifications and status updates.
    """
    try:
        # Process webhook in background to avoid blocking
        background_tasks.add_task(
            manager.handle_webhook,
            integration_id,
            webhook_data
        )
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Failed to handle webhook for integration {integration_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to handle webhook: {str(e)}")


# System Information Endpoints

@router.get("/system/info")
async def get_integrations_info():
    """
    Get integration system information.
    
    Returns supported integration types, providers, and capabilities
    available in the EUVoice AI Platform.
    """
    return {
        "service": "EUVoice AI Integration System",
        "version": "1.0.0",
        "supported_integrations": {
            "telephony": {
                "providers": ["twilio"],
                "capabilities": ["voice_calls", "sms", "whatsapp", "call_recording", "twiml"],
                "regions": ["eu", "us", "ap"]
            },
            "crm": {
                "providers": ["salesforce", "sap"],
                "capabilities": ["contact_management", "lead_tracking", "activity_logging", "data_sync"],
                "compliance": ["gdpr", "eu_data_residency"]
            },
            "messaging": {
                "providers": ["whatsapp", "telegram", "slack"],
                "capabilities": ["text_messages", "media_messages", "interactive_messages", "group_chat"],
                "features": ["real_time_events", "delivery_receipts", "read_receipts"]
            }
        },
        "features": {
            "real_time_events": "Webhook-based event notifications",
            "multi_channel": "Unified interface across platforms",
            "eu_compliance": "GDPR-compliant data handling",
            "high_availability": "Automatic failover and retry logic",
            "monitoring": "Comprehensive health checks and metrics"
        },
        "compliance": {
            "gdpr": True,
            "data_residency": "EU/EEA only",
            "audit_logging": True,
            "encryption": "TLS 1.3 + AES-256"
        }
    }


@router.get("/system/stats")
async def get_system_stats(
    current_user: User = Depends(get_current_user),
    manager: IntegrationManager = Depends(get_integration_manager_dep)
):
    """
    Get integration system statistics.
    
    Returns operational metrics, usage statistics, and health
    information for the integration system.
    """
    try:
        stats = manager.get_manager_stats()
        
        return {
            "system_status": "healthy" if stats["is_running"] else "unhealthy",
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")