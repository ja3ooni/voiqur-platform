"""
Webhook Integration Examples

Examples showing how to integrate webhooks with the EUVoice AI Platform
for real-time event notifications and processing pipeline monitoring.
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional
from datetime import datetime

from ..utils.webhook_publisher import (
    publish_conversation_started, publish_conversation_ended,
    publish_transcription_completed, publish_synthesis_completed,
    publish_pipeline_completed, publish_error_occurred
)


class WebhookIntegrationExample:
    """
    Example class showing webhook integration patterns for voice processing.
    """
    
    def __init__(self, api_base_url: str, auth_token: str):
        """
        Initialize webhook integration example.
        
        Args:
            api_base_url: Base URL of the EUVoice API
            auth_token: Authentication token
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.auth_token = auth_token
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.auth_token}"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def register_webhook_for_conversation_events(self, 
                                                     webhook_url: str,
                                                     secret_token: Optional[str] = None) -> str:
        """
        Register a webhook for conversation lifecycle events.
        
        Args:
            webhook_url: URL to receive webhook notifications
            secret_token: Optional secret for HMAC verification
            
        Returns:
            Webhook ID
        """
        webhook_data = {
            "name": "Conversation Events Webhook",
            "description": "Receives notifications for conversation start/end events",
            "url": webhook_url,
            "event_types": [
                "conversation.started",
                "conversation.ended",
                "conversation.updated"
            ],
            "security": {
                "secret_token": secret_token,
                "verify_ssl": True
            },
            "retry_policy": {
                "max_attempts": 3,
                "initial_delay": 1,
                "max_delay": 60,
                "backoff_multiplier": 2.0
            }
        }
        
        async with self.session.post(
            f"{self.api_base_url}/api/v1/webhooks/",
            json=webhook_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result["webhook_id"]
            else:
                raise Exception(f"Failed to register webhook: {response.status}")
    
    async def register_webhook_for_processing_events(self, 
                                                   webhook_url: str,
                                                   languages: Optional[list] = None) -> str:
        """
        Register a webhook for voice processing events (STT, TTS, pipeline).
        
        Args:
            webhook_url: URL to receive webhook notifications
            languages: Optional list of languages to filter by
            
        Returns:
            Webhook ID
        """
        webhook_data = {
            "name": "Voice Processing Events Webhook",
            "description": "Receives notifications for STT, TTS, and pipeline events",
            "url": webhook_url,
            "event_types": [
                "transcription.completed",
                "transcription.failed",
                "synthesis.completed", 
                "synthesis.failed",
                "pipeline.completed",
                "pipeline.failed"
            ],
            "filters": {
                "languages": languages
            } if languages else None,
            "retry_policy": {
                "max_attempts": 5,
                "initial_delay": 2,
                "max_delay": 300,
                "backoff_multiplier": 2.0
            }
        }
        
        async with self.session.post(
            f"{self.api_base_url}/api/v1/webhooks/",
            json=webhook_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result["webhook_id"]
            else:
                raise Exception(f"Failed to register webhook: {response.status}")
    
    async def register_webhook_for_error_monitoring(self, webhook_url: str) -> str:
        """
        Register a webhook for system error monitoring.
        
        Args:
            webhook_url: URL to receive error notifications
            
        Returns:
            Webhook ID
        """
        webhook_data = {
            "name": "Error Monitoring Webhook",
            "description": "Receives notifications for system errors and alerts",
            "url": webhook_url,
            "event_types": [
                "error.occurred",
                "system.alert",
                "agent.status_changed"
            ],
            "filters": {
                "conditions": {
                    "severity": ["high", "critical"]  # Only high severity errors
                }
            },
            "retry_policy": {
                "max_attempts": 10,  # Critical for error notifications
                "initial_delay": 1,
                "max_delay": 60,
                "backoff_multiplier": 1.5
            }
        }
        
        async with self.session.post(
            f"{self.api_base_url}/api/v1/webhooks/",
            json=webhook_data
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result["webhook_id"]
            else:
                raise Exception(f"Failed to register webhook: {response.status}")
    
    async def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Test a webhook by sending a test event.
        
        Args:
            webhook_id: ID of webhook to test
            
        Returns:
            Test result
        """
        test_data = {
            "event_type": "transcription.completed",
            "test_data": {
                "test": True,
                "message": "This is a test webhook delivery",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        async with self.session.post(
            f"{self.api_base_url}/api/v1/webhooks/{webhook_id}/test",
            json=test_data
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to test webhook: {response.status}")
    
    async def get_webhook_stats(self, webhook_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get webhook delivery statistics.
        
        Args:
            webhook_id: ID of webhook
            days: Number of days for statistics
            
        Returns:
            Webhook statistics
        """
        async with self.session.get(
            f"{self.api_base_url}/api/v1/webhooks/{webhook_id}/stats?days={days}"
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to get webhook stats: {response.status}")
    
    async def simulate_voice_processing_with_webhooks(self, 
                                                    audio_file_path: str,
                                                    conversation_id: str,
                                                    user_id: str) -> Dict[str, Any]:
        """
        Simulate a complete voice processing pipeline with webhook events.
        
        This example shows how webhook events are published during processing.
        
        Args:
            audio_file_path: Path to audio file
            conversation_id: Conversation identifier
            user_id: User identifier
            
        Returns:
            Processing results
        """
        results = {}
        
        try:
            # 1. Start conversation and publish event
            await publish_conversation_started(
                conversation_id=conversation_id,
                user_id=user_id,
                language="en",
                metadata={"source": "api_example"}
            )
            
            # 2. Process STT
            with open(audio_file_path, 'rb') as audio_file:
                files = {'file': audio_file}
                
                async with self.session.post(
                    f"{self.api_base_url}/api/v1/voice/stt/file",
                    data=files
                ) as response:
                    if response.status == 200:
                        stt_result = await response.json()
                        results['stt'] = stt_result
                        
                        # Publish STT completion event
                        await publish_transcription_completed(
                            request_id=stt_result['request_id'],
                            text=stt_result['text'],
                            confidence=stt_result['confidence'],
                            language=stt_result['language'],
                            processing_time_ms=stt_result['processing_time_ms'],
                            user_id=user_id,
                            conversation_id=conversation_id
                        )
                    else:
                        raise Exception(f"STT failed: {response.status}")
            
            # 3. Process LLM
            llm_data = {
                "text": results['stt']['text'],
                "conversation_id": conversation_id,
                "language": "en"
            }
            
            async with self.session.post(
                f"{self.api_base_url}/api/v1/voice/llm",
                json=llm_data
            ) as response:
                if response.status == 200:
                    llm_result = await response.json()
                    results['llm'] = llm_result
                else:
                    raise Exception(f"LLM failed: {response.status}")
            
            # 4. Process TTS
            tts_data = {
                "text": results['llm']['response'],
                "language": "en",
                "emotion": "neutral"
            }
            
            async with self.session.post(
                f"{self.api_base_url}/api/v1/voice/tts",
                json=tts_data
            ) as response:
                if response.status == 200:
                    tts_result = await response.json()
                    results['tts'] = tts_result
                    
                    # Publish TTS completion event
                    await publish_synthesis_completed(
                        request_id=tts_result['request_id'],
                        text=tts_data['text'],
                        voice_id=tts_result['voice_id'],
                        language=tts_result['language'],
                        duration_seconds=tts_result['duration_seconds'],
                        processing_time_ms=tts_result['processing_time_ms'],
                        user_id=user_id,
                        conversation_id=conversation_id
                    )
                else:
                    raise Exception(f"TTS failed: {response.status}")
            
            # 5. Publish pipeline completion event
            total_time = (
                results['stt']['processing_time_ms'] +
                results['llm']['processing_time_ms'] +
                results['tts']['processing_time_ms']
            )
            
            await publish_pipeline_completed(
                request_id=f"pipeline_{conversation_id}",
                input_text=results['stt']['text'],
                output_text=results['llm']['response'],
                total_processing_time_ms=total_time,
                stages=[
                    {
                        "stage": "stt",
                        "processing_time_ms": results['stt']['processing_time_ms'],
                        "success": True
                    },
                    {
                        "stage": "llm", 
                        "processing_time_ms": results['llm']['processing_time_ms'],
                        "success": True
                    },
                    {
                        "stage": "tts",
                        "processing_time_ms": results['tts']['processing_time_ms'],
                        "success": True
                    }
                ],
                user_id=user_id,
                conversation_id=conversation_id
            )
            
            # 6. End conversation
            await publish_conversation_ended(
                conversation_id=conversation_id,
                user_id=user_id,
                duration_seconds=total_time / 1000,  # Convert to seconds
                message_count=1,
                end_reason="completed",
                summary={
                    "total_processing_time_ms": total_time,
                    "stages_completed": 3,
                    "success": True
                }
            )
            
            return results
            
        except Exception as e:
            # Publish error event
            await publish_error_occurred(
                error_code="PIPELINE_ERROR",
                error_message=str(e),
                component="voice_processing_pipeline",
                severity="high",
                user_id=user_id,
                conversation_id=conversation_id
            )
            raise


# Example webhook receiver (for testing)
class WebhookReceiver:
    """
    Example webhook receiver that can be used for testing webhook deliveries.
    """
    
    def __init__(self, port: int = 8080):
        """
        Initialize webhook receiver.
        
        Args:
            port: Port to listen on
        """
        self.port = port
        self.received_events = []
    
    async def start_server(self):
        """Start the webhook receiver server."""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_post('/webhook', self.handle_webhook)
        app.router.add_get('/events', self.get_events)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        print(f"Webhook receiver started on http://localhost:{self.port}")
        print(f"Webhook URL: http://localhost:{self.port}/webhook")
        print(f"Events URL: http://localhost:{self.port}/events")
    
    async def handle_webhook(self, request):
        """Handle incoming webhook."""
        try:
            # Verify content type
            if request.content_type != 'application/json':
                return web.Response(status=400, text="Invalid content type")
            
            # Parse webhook payload
            payload = await request.json()
            
            # Log received event
            event_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "headers": dict(request.headers),
                "payload": payload
            }
            
            self.received_events.append(event_info)
            
            print(f"Received webhook event: {payload.get('event_type', 'unknown')}")
            print(f"Event ID: {payload.get('event_id', 'unknown')}")
            
            # Verify HMAC signature if present
            signature = request.headers.get('X-EUVoice-Signature')
            if signature:
                # In a real implementation, verify the HMAC signature
                print(f"Signature: {signature}")
            
            return web.Response(status=200, text="OK")
            
        except Exception as e:
            print(f"Error handling webhook: {e}")
            return web.Response(status=500, text="Internal Server Error")
    
    async def get_events(self, request):
        """Get received events (for debugging)."""
        return web.json_response({
            "total_events": len(self.received_events),
            "events": self.received_events[-10:]  # Last 10 events
        })


# Usage example
async def main():
    """Example usage of webhook integration."""
    
    # Configuration
    API_BASE_URL = "http://localhost:8000"
    AUTH_TOKEN = "your-auth-token"
    WEBHOOK_URL = "http://localhost:8080/webhook"
    
    # Start webhook receiver
    receiver = WebhookReceiver(port=8080)
    await receiver.start_server()
    
    # Register webhooks and test
    async with WebhookIntegrationExample(API_BASE_URL, AUTH_TOKEN) as integration:
        
        # Register webhooks
        conversation_webhook_id = await integration.register_webhook_for_conversation_events(
            webhook_url=WEBHOOK_URL,
            secret_token="my-secret-token"
        )
        
        processing_webhook_id = await integration.register_webhook_for_processing_events(
            webhook_url=WEBHOOK_URL,
            languages=["en", "fr", "de"]
        )
        
        error_webhook_id = await integration.register_webhook_for_error_monitoring(
            webhook_url=WEBHOOK_URL
        )
        
        print(f"Registered webhooks:")
        print(f"  Conversation events: {conversation_webhook_id}")
        print(f"  Processing events: {processing_webhook_id}")
        print(f"  Error monitoring: {error_webhook_id}")
        
        # Test webhooks
        for webhook_id in [conversation_webhook_id, processing_webhook_id, error_webhook_id]:
            test_result = await integration.test_webhook(webhook_id)
            print(f"Test result for {webhook_id}: {test_result['status']}")
        
        # Simulate voice processing (if audio file available)
        # await integration.simulate_voice_processing_with_webhooks(
        #     audio_file_path="test_audio.wav",
        #     conversation_id="conv_123",
        #     user_id="user_456"
        # )
        
        # Get webhook statistics
        for webhook_id in [conversation_webhook_id, processing_webhook_id]:
            stats = await integration.get_webhook_stats(webhook_id, days=1)
            print(f"Stats for {webhook_id}: {stats['success_rate']:.2%} success rate")


if __name__ == "__main__":
    asyncio.run(main())