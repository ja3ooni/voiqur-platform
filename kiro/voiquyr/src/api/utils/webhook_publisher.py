"""
Webhook Event Publisher

Utility for publishing webhook events from various services and agents
in the EUVoice AI Platform.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from ..models.webhooks import WebhookEvent, WebhookEventType
from ..services.webhook_service import WebhookService


logger = logging.getLogger(__name__)


class WebhookEventPublisher:
    """
    Publisher for webhook events with convenience methods for different event types.
    
    Provides a simple interface for agents and services to publish events
    without directly interacting with the webhook service.
    """
    
    def __init__(self, webhook_service: WebhookService):
        """
        Initialize webhook event publisher.
        
        Args:
            webhook_service: Webhook service instance
        """
        self.webhook_service = webhook_service
        self.logger = logging.getLogger(__name__)
    
    async def publish_conversation_started(self, 
                                         conversation_id: str,
                                         user_id: str,
                                         language: str = "en",
                                         metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish conversation started event.
        
        Args:
            conversation_id: Unique conversation identifier
            user_id: User who started the conversation
            language: Conversation language
            metadata: Additional conversation metadata
        """
        event_data = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "language": language,
            "started_at": datetime.utcnow().isoformat()
        }
        
        if metadata:
            event_data["metadata"] = metadata
        
        event = WebhookEvent(
            event_type=WebhookEventType.CONVERSATION_STARTED,
            data=event_data,
            user_id=user_id,
            conversation_id=conversation_id,
            source="conversation_manager"
        )
        
        await self._publish_event(event)
    
    async def publish_conversation_ended(self,
                                       conversation_id: str,
                                       user_id: str,
                                       duration_seconds: float,
                                       message_count: int,
                                       end_reason: str = "completed",
                                       summary: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish conversation ended event.
        
        Args:
            conversation_id: Conversation identifier
            user_id: User ID
            duration_seconds: Total conversation duration
            message_count: Number of messages exchanged
            end_reason: Reason for conversation end
            summary: Conversation summary and statistics
        """
        event_data = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "duration_seconds": duration_seconds,
            "message_count": message_count,
            "end_reason": end_reason,
            "ended_at": datetime.utcnow().isoformat()
        }
        
        if summary:
            event_data["summary"] = summary
        
        event = WebhookEvent(
            event_type=WebhookEventType.CONVERSATION_ENDED,
            data=event_data,
            user_id=user_id,
            conversation_id=conversation_id,
            source="conversation_manager"
        )
        
        await self._publish_event(event)
    
    async def publish_transcription_completed(self,
                                            request_id: str,
                                            text: str,
                                            confidence: float,
                                            language: str,
                                            processing_time_ms: float,
                                            user_id: Optional[str] = None,
                                            conversation_id: Optional[str] = None,
                                            metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish transcription completed event.
        
        Args:
            request_id: STT request identifier
            text: Transcribed text
            confidence: Transcription confidence score
            language: Detected/specified language
            processing_time_ms: Processing time in milliseconds
            user_id: Associated user ID
            conversation_id: Associated conversation ID
            metadata: Additional transcription metadata
        """
        event_data = {
            "request_id": request_id,
            "text": text,
            "confidence": confidence,
            "language": language,
            "processing_time_ms": processing_time_ms,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        if metadata:
            event_data.update(metadata)
        
        event = WebhookEvent(
            event_type=WebhookEventType.TRANSCRIPTION_COMPLETED,
            data=event_data,
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            source="stt_agent"
        )
        
        await self._publish_event(event)
    
    async def publish_transcription_failed(self,
                                         request_id: str,
                                         error_message: str,
                                         error_code: str,
                                         user_id: Optional[str] = None,
                                         conversation_id: Optional[str] = None,
                                         metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish transcription failed event.
        
        Args:
            request_id: STT request identifier
            error_message: Error description
            error_code: Error code
            user_id: Associated user ID
            conversation_id: Associated conversation ID
            metadata: Additional error metadata
        """
        event_data = {
            "request_id": request_id,
            "error_message": error_message,
            "error_code": error_code,
            "failed_at": datetime.utcnow().isoformat()
        }
        
        if metadata:
            event_data.update(metadata)
        
        event = WebhookEvent(
            event_type=WebhookEventType.TRANSCRIPTION_FAILED,
            data=event_data,
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            source="stt_agent"
        )
        
        await self._publish_event(event)
    
    async def publish_synthesis_completed(self,
                                        request_id: str,
                                        text: str,
                                        voice_id: str,
                                        language: str,
                                        duration_seconds: float,
                                        processing_time_ms: float,
                                        user_id: Optional[str] = None,
                                        conversation_id: Optional[str] = None,
                                        metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish synthesis completed event.
        
        Args:
            request_id: TTS request identifier
            text: Synthesized text
            voice_id: Voice model used
            language: Synthesis language
            duration_seconds: Audio duration
            processing_time_ms: Processing time in milliseconds
            user_id: Associated user ID
            conversation_id: Associated conversation ID
            metadata: Additional synthesis metadata
        """
        event_data = {
            "request_id": request_id,
            "text": text,
            "voice_id": voice_id,
            "language": language,
            "duration_seconds": duration_seconds,
            "processing_time_ms": processing_time_ms,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        if metadata:
            event_data.update(metadata)
        
        event = WebhookEvent(
            event_type=WebhookEventType.SYNTHESIS_COMPLETED,
            data=event_data,
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            source="tts_agent"
        )
        
        await self._publish_event(event)
    
    async def publish_synthesis_failed(self,
                                     request_id: str,
                                     text: str,
                                     error_message: str,
                                     error_code: str,
                                     user_id: Optional[str] = None,
                                     conversation_id: Optional[str] = None,
                                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish synthesis failed event.
        
        Args:
            request_id: TTS request identifier
            text: Text that failed to synthesize
            error_message: Error description
            error_code: Error code
            user_id: Associated user ID
            conversation_id: Associated conversation ID
            metadata: Additional error metadata
        """
        event_data = {
            "request_id": request_id,
            "text": text,
            "error_message": error_message,
            "error_code": error_code,
            "failed_at": datetime.utcnow().isoformat()
        }
        
        if metadata:
            event_data.update(metadata)
        
        event = WebhookEvent(
            event_type=WebhookEventType.SYNTHESIS_FAILED,
            data=event_data,
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            source="tts_agent"
        )
        
        await self._publish_event(event)
    
    async def publish_pipeline_completed(self,
                                       request_id: str,
                                       input_text: Optional[str],
                                       output_text: str,
                                       total_processing_time_ms: float,
                                       stages: List[Dict[str, Any]],
                                       user_id: Optional[str] = None,
                                       conversation_id: Optional[str] = None,
                                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish pipeline completed event.
        
        Args:
            request_id: Pipeline request identifier
            input_text: Original input text (if text-based)
            output_text: Final output text
            total_processing_time_ms: Total pipeline processing time
            stages: Processing stages with timing and results
            user_id: Associated user ID
            conversation_id: Associated conversation ID
            metadata: Additional pipeline metadata
        """
        event_data = {
            "request_id": request_id,
            "output_text": output_text,
            "total_processing_time_ms": total_processing_time_ms,
            "stages": stages,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        if input_text:
            event_data["input_text"] = input_text
        
        if metadata:
            event_data.update(metadata)
        
        event = WebhookEvent(
            event_type=WebhookEventType.PIPELINE_COMPLETED,
            data=event_data,
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            source="pipeline_orchestrator"
        )
        
        await self._publish_event(event)
    
    async def publish_batch_started(self,
                                  batch_id: str,
                                  operation: str,
                                  total_files: int,
                                  user_id: str,
                                  estimated_completion_time: Optional[datetime] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish batch processing started event.
        
        Args:
            batch_id: Batch job identifier
            operation: Type of batch operation
            total_files: Number of files to process
            user_id: User who started the batch
            estimated_completion_time: Estimated completion time
            metadata: Additional batch metadata
        """
        event_data = {
            "batch_id": batch_id,
            "operation": operation,
            "total_files": total_files,
            "started_at": datetime.utcnow().isoformat()
        }
        
        if estimated_completion_time:
            event_data["estimated_completion_time"] = estimated_completion_time.isoformat()
        
        if metadata:
            event_data.update(metadata)
        
        event = WebhookEvent(
            event_type=WebhookEventType.BATCH_STARTED,
            data=event_data,
            user_id=user_id,
            source="batch_processor"
        )
        
        await self._publish_event(event)
    
    async def publish_batch_progress(self,
                                   batch_id: str,
                                   processed_files: int,
                                   total_files: int,
                                   success_count: int,
                                   error_count: int,
                                   user_id: str,
                                   estimated_completion_time: Optional[datetime] = None) -> None:
        """
        Publish batch processing progress event.
        
        Args:
            batch_id: Batch job identifier
            processed_files: Number of files processed so far
            total_files: Total number of files
            success_count: Number of successful processing
            error_count: Number of failed processing
            user_id: User ID
            estimated_completion_time: Updated completion estimate
        """
        event_data = {
            "batch_id": batch_id,
            "processed_files": processed_files,
            "total_files": total_files,
            "success_count": success_count,
            "error_count": error_count,
            "progress_percentage": (processed_files / total_files) * 100 if total_files > 0 else 0,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if estimated_completion_time:
            event_data["estimated_completion_time"] = estimated_completion_time.isoformat()
        
        event = WebhookEvent(
            event_type=WebhookEventType.BATCH_PROGRESS,
            data=event_data,
            user_id=user_id,
            source="batch_processor"
        )
        
        await self._publish_event(event)
    
    async def publish_batch_completed(self,
                                    batch_id: str,
                                    total_files: int,
                                    success_count: int,
                                    error_count: int,
                                    total_processing_time_ms: float,
                                    user_id: str,
                                    results_summary: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish batch processing completed event.
        
        Args:
            batch_id: Batch job identifier
            total_files: Total number of files processed
            success_count: Number of successful processing
            error_count: Number of failed processing
            total_processing_time_ms: Total processing time
            user_id: User ID
            results_summary: Summary of batch results
        """
        event_data = {
            "batch_id": batch_id,
            "total_files": total_files,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": success_count / total_files if total_files > 0 else 0,
            "total_processing_time_ms": total_processing_time_ms,
            "completed_at": datetime.utcnow().isoformat()
        }
        
        if results_summary:
            event_data["results_summary"] = results_summary
        
        event = WebhookEvent(
            event_type=WebhookEventType.BATCH_COMPLETED,
            data=event_data,
            user_id=user_id,
            source="batch_processor"
        )
        
        await self._publish_event(event)
    
    async def publish_agent_status_changed(self,
                                         agent_id: str,
                                         agent_type: str,
                                         old_status: str,
                                         new_status: str,
                                         reason: Optional[str] = None,
                                         metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish agent status changed event.
        
        Args:
            agent_id: Agent identifier
            agent_type: Type of agent
            old_status: Previous status
            new_status: New status
            reason: Reason for status change
            metadata: Additional agent metadata
        """
        event_data = {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "old_status": old_status,
            "new_status": new_status,
            "changed_at": datetime.utcnow().isoformat()
        }
        
        if reason:
            event_data["reason"] = reason
        
        if metadata:
            event_data.update(metadata)
        
        event = WebhookEvent(
            event_type=WebhookEventType.AGENT_STATUS_CHANGED,
            data=event_data,
            source=f"{agent_type}_agent"
        )
        
        await self._publish_event(event)
    
    async def publish_system_alert(self,
                                 alert_type: str,
                                 severity: str,
                                 message: str,
                                 component: str,
                                 details: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish system alert event.
        
        Args:
            alert_type: Type of alert
            severity: Alert severity (low, medium, high, critical)
            message: Alert message
            component: System component that generated the alert
            details: Additional alert details
        """
        event_data = {
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "component": component,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if details:
            event_data["details"] = details
        
        event = WebhookEvent(
            event_type=WebhookEventType.SYSTEM_ALERT,
            data=event_data,
            source="system_monitor"
        )
        
        await self._publish_event(event)
    
    async def publish_error_occurred(self,
                                   error_code: str,
                                   error_message: str,
                                   component: str,
                                   severity: str = "medium",
                                   user_id: Optional[str] = None,
                                   conversation_id: Optional[str] = None,
                                   request_id: Optional[str] = None,
                                   stack_trace: Optional[str] = None,
                                   metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Publish error occurred event.
        
        Args:
            error_code: Error code
            error_message: Error description
            component: Component where error occurred
            severity: Error severity
            user_id: Associated user ID
            conversation_id: Associated conversation ID
            request_id: Associated request ID
            stack_trace: Error stack trace (for debugging)
            metadata: Additional error metadata
        """
        event_data = {
            "error_code": error_code,
            "error_message": error_message,
            "component": component,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if stack_trace:
            event_data["stack_trace"] = stack_trace
        
        if metadata:
            event_data.update(metadata)
        
        event = WebhookEvent(
            event_type=WebhookEventType.ERROR_OCCURRED,
            data=event_data,
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            source=component
        )
        
        await self._publish_event(event)
    
    async def publish_custom_event(self,
                                 event_type: WebhookEventType,
                                 data: Dict[str, Any],
                                 source: str,
                                 user_id: Optional[str] = None,
                                 conversation_id: Optional[str] = None,
                                 request_id: Optional[str] = None) -> None:
        """
        Publish custom event with arbitrary data.
        
        Args:
            event_type: Type of event
            data: Event data
            source: Event source
            user_id: Associated user ID
            conversation_id: Associated conversation ID
            request_id: Associated request ID
        """
        event = WebhookEvent(
            event_type=event_type,
            data=data,
            user_id=user_id,
            conversation_id=conversation_id,
            request_id=request_id,
            source=source
        )
        
        await self._publish_event(event)
    
    async def _publish_event(self, event: WebhookEvent) -> None:
        """
        Internal method to publish event to webhook service.
        
        Args:
            event: Event to publish
        """
        try:
            await self.webhook_service.publish_event(event)
            self.logger.debug(f"Published webhook event {event.id} of type {event.event_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish webhook event {event.id}: {e}")
            # Don't re-raise to avoid breaking the main application flow


# Global publisher instance (will be initialized by the application)
_global_publisher: Optional[WebhookEventPublisher] = None


def set_global_publisher(publisher: WebhookEventPublisher) -> None:
    """Set the global webhook event publisher instance."""
    global _global_publisher
    _global_publisher = publisher


def get_global_publisher() -> Optional[WebhookEventPublisher]:
    """Get the global webhook event publisher instance."""
    return _global_publisher


# Convenience functions for publishing events without direct publisher access

async def publish_conversation_started(conversation_id: str, user_id: str, **kwargs) -> None:
    """Convenience function to publish conversation started event."""
    if _global_publisher:
        await _global_publisher.publish_conversation_started(conversation_id, user_id, **kwargs)


async def publish_conversation_ended(conversation_id: str, user_id: str, **kwargs) -> None:
    """Convenience function to publish conversation ended event."""
    if _global_publisher:
        await _global_publisher.publish_conversation_ended(conversation_id, user_id, **kwargs)


async def publish_transcription_completed(request_id: str, text: str, **kwargs) -> None:
    """Convenience function to publish transcription completed event."""
    if _global_publisher:
        await _global_publisher.publish_transcription_completed(request_id, text, **kwargs)


async def publish_synthesis_completed(request_id: str, text: str, **kwargs) -> None:
    """Convenience function to publish synthesis completed event."""
    if _global_publisher:
        await _global_publisher.publish_synthesis_completed(request_id, text, **kwargs)


async def publish_error_occurred(error_code: str, error_message: str, component: str, **kwargs) -> None:
    """Convenience function to publish error occurred event."""
    if _global_publisher:
        await _global_publisher.publish_error_occurred(error_code, error_message, component, **kwargs)