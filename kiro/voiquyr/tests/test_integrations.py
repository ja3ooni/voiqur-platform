"""
Test Third-Party Integrations

Comprehensive test suite for telephony, CRM, and messaging integrations
in the EUVoice AI Platform.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

# Import integration classes
from src.api.integrations.base import IntegrationConfig, IntegrationType, IntegrationStatus
from src.api.integrations.telephony import TwilioIntegration, TwilioConfig
from src.api.integrations.crm import SalesforceIntegration, SAPIntegration, SalesforceConfig, SAPConfig
from src.api.integrations.messaging import WhatsAppIntegration, TelegramIntegration, SlackIntegration, WhatsAppConfig, TelegramConfig, SlackConfig
from src.api.integrations.manager import IntegrationManager


class MockHTTPResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, success: bool = True, data: Dict[str, Any] = None, status: int = 200):
        self.success = success
        self.data = data or {}
        self.status = status

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        return getattr(self, key, default)


async def test_twilio_integration():
    """Test Twilio telephony integration."""
    print("Testing Twilio Integration...")
    
    # Create Twilio configuration
    config = TwilioConfig(
        name="Test Twilio",
        account_sid="test_account_sid",
        auth_token="test_auth_token",
        phone_number="+1234567890",
        eu_region=True,
        edge_location="dublin"
    )
    
    # Create integration
    twilio = TwilioIntegration(config)
    
    # Mock HTTP requests
    twilio._make_request = AsyncMock()
    
    # Test initialization
    assert await twilio.initialize() == True
    print("✓ Twilio initialization passed")
    
    # Test authentication
    twilio._make_request.return_value = MockHTTPResponse(
        success=True,
        data={"friendly_name": "Test Account", "status": "active"}
    )
    
    assert await twilio.authenticate() == True
    assert twilio._authenticated == True
    print("✓ Twilio authentication passed")
    
    # Test health check
    assert await twilio.health_check() == True
    print("✓ Twilio health check passed")
    
    # Test making a call
    twilio._make_request.return_value = MockHTTPResponse(
        success=True,
        data={
            "sid": "test_call_sid",
            "from": "+1234567890",
            "to": "+0987654321",
            "status": "queued",
            "direction": "outbound"
        }
    )
    
    call = await twilio.make_call(
        to_number="+0987654321",
        twiml="<Response><Say>Hello World</Say></Response>"
    )
    
    assert call is not None
    assert call.sid == "test_call_sid"
    print("✓ Twilio call creation passed")
    
    # Test sending SMS
    twilio._make_request.return_value = MockHTTPResponse(
        success=True,
        data={
            "sid": "test_message_sid",
            "from": "+1234567890",
            "to": "+0987654321",
            "body": "Test message",
            "status": "queued"
        }
    )
    
    message = await twilio.send_sms(
        to_number="+0987654321",
        message="Test message"
    )
    
    assert message is not None
    assert message.sid == "test_message_sid"
    print("✓ Twilio SMS sending passed")
    
    # Test TwiML generation
    twiml = twilio.generate_voice_twiml(
        text="Hello, this is a test message",
        voice="alice",
        language="en-US"
    )
    
    assert "<Say" in twiml
    assert "Hello, this is a test message" in twiml
    print("✓ Twilio TwiML generation passed")


async def test_salesforce_integration():
    """Test Salesforce CRM integration."""
    print("\nTesting Salesforce Integration...")
    
    # Create Salesforce configuration
    config = SalesforceConfig(
        name="Test Salesforce",
        client_id="test_client_id",
        client_secret="test_client_secret",
        username="test@example.com",
        password="test_password",
        security_token="test_token",
        sandbox=True
    )
    
    # Create integration
    salesforce = SalesforceIntegration(config)
    
    # Mock HTTP requests
    salesforce._make_request = AsyncMock()
    
    # Test initialization
    assert await salesforce.initialize() == True
    print("✓ Salesforce initialization passed")
    
    # Test authentication
    salesforce._make_request.return_value = MockHTTPResponse(
        success=True,
        data={
            "access_token": "test_access_token",
            "instance_url": "https://test.salesforce.com"
        }
    )
    
    assert await salesforce.authenticate() == True
    assert salesforce.access_token == "test_access_token"
    print("✓ Salesforce authentication passed")
    
    # Test health check
    salesforce._make_request.return_value = MockHTTPResponse(
        success=True,
        data={"sobjects": []}
    )
    
    assert await salesforce.health_check() == True
    print("✓ Salesforce health check passed")
    
    # Test contact search
    salesforce._make_request.return_value = MockHTTPResponse(
        success=True,
        data={
            "records": [
                {
                    "Id": "test_contact_id",
                    "FirstName": "John",
                    "LastName": "Doe",
                    "Email": "john.doe@example.com",
                    "Phone": "+1234567890",
                    "Account": {"Name": "Test Company"}
                }
            ]
        }
    )
    
    contacts = await salesforce.search_contacts(email="john.doe@example.com")
    
    assert len(contacts) == 1
    assert contacts[0].first_name == "John"
    assert contacts[0].email == "john.doe@example.com"
    print("✓ Salesforce contact search passed")
    
    # Test contact creation
    salesforce._make_request.return_value = MockHTTPResponse(
        success=True,
        data={"id": "new_contact_id"}
    )
    
    new_contact = await salesforce.create_contact({
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "phone": "+0987654321"
    })
    
    assert new_contact is not None
    assert new_contact.id == "new_contact_id"
    print("✓ Salesforce contact creation passed")


async def test_whatsapp_integration():
    """Test WhatsApp messaging integration."""
    print("\nTesting WhatsApp Integration...")
    
    # Create WhatsApp configuration
    config = WhatsAppConfig(
        name="Test WhatsApp",
        access_token="test_access_token",
        phone_number_id="test_phone_number_id",
        business_account_id="test_business_account_id"
    )
    
    # Create integration
    whatsapp = WhatsAppIntegration(config)
    
    # Mock HTTP requests
    whatsapp._make_request = AsyncMock()
    
    # Test initialization
    assert await whatsapp.initialize() == True
    print("✓ WhatsApp initialization passed")
    
    # Test authentication
    whatsapp._make_request.return_value = MockHTTPResponse(
        success=True,
        data={
            "display_phone_number": "+1234567890",
            "status": "CONNECTED"
        }
    )
    
    assert await whatsapp.authenticate() == True
    print("✓ WhatsApp authentication passed")
    
    # Test health check
    assert await whatsapp.health_check() == True
    print("✓ WhatsApp health check passed")
    
    # Test sending message
    whatsapp._make_request.return_value = MockHTTPResponse(
        success=True,
        data={
            "messages": [{"id": "test_message_id"}]
        }
    )
    
    message = await whatsapp.send_message(
        to_number="+0987654321",
        message="Hello from WhatsApp!"
    )
    
    assert message is not None
    assert message.id == "test_message_id"
    print("✓ WhatsApp message sending passed")


async def test_telegram_integration():
    """Test Telegram messaging integration."""
    print("\nTesting Telegram Integration...")
    
    # Create Telegram configuration
    config = TelegramConfig(
        name="Test Telegram",
        bot_token="test_bot_token",
        bot_username="test_bot"
    )
    
    # Create integration
    telegram = TelegramIntegration(config)
    
    # Mock HTTP requests
    telegram._make_request = AsyncMock()
    
    # Test initialization
    assert await telegram.initialize() == True
    print("✓ Telegram initialization passed")
    
    # Test authentication
    telegram._make_request.return_value = MockHTTPResponse(
        success=True,
        data={
            "ok": True,
            "result": {
                "username": "test_bot",
                "first_name": "Test Bot"
            }
        }
    )
    
    assert await telegram.authenticate() == True
    print("✓ Telegram authentication passed")
    
    # Test health check
    assert await telegram.health_check() == True
    print("✓ Telegram health check passed")
    
    # Test sending message
    telegram._make_request.return_value = MockHTTPResponse(
        success=True,
        data={
            "ok": True,
            "result": {
                "message_id": 123,
                "text": "Hello from Telegram!"
            }
        }
    )
    
    message = await telegram.send_message(
        chat_id="test_chat_id",
        message="Hello from Telegram!"
    )
    
    assert message is not None
    assert message.id == "123"
    print("✓ Telegram message sending passed")


async def test_integration_manager():
    """Test Integration Manager functionality."""
    print("\nTesting Integration Manager...")
    
    # Create integration manager
    manager = IntegrationManager()
    
    # Start manager
    await manager.start()
    assert manager.is_running == True
    print("✓ Integration Manager startup passed")
    
    # Test creating Twilio integration
    twilio_config = {
        "name": "Test Twilio Manager",
        "account_sid": "test_account_sid",
        "auth_token": "test_auth_token",
        "phone_number": "+1234567890"
    }
    
    # Mock the integration creation to avoid actual API calls
    original_classes = manager.integration_classes.copy()
    
    class MockTwilioIntegration:
        def __init__(self, config):
            self.config = config
            self.status = IntegrationStatus.INACTIVE
            self._authenticated = False
        
        async def start(self):
            self.status = IntegrationStatus.ACTIVE
            return True
        
        async def stop(self):
            self.status = IntegrationStatus.INACTIVE
        
        def register_event_handler(self, event_type, handler):
            pass
        
        def get_status(self):
            return {
                "id": self.config.id,
                "name": self.config.name,
                "provider": "twilio",
                "type": "telephony",
                "status": self.status.value,
                "enabled": True
            }
    
    manager.integration_classes["twilio"] = MockTwilioIntegration
    
    try:
        integration_id = await manager.create_integration(
            provider="twilio",
            config_data=twilio_config,
            auto_start=True
        )
        
        assert integration_id is not None
        print("✓ Integration Manager creation passed")
        
        # Test listing integrations
        integrations = manager.list_integrations()
        assert len(integrations) == 1
        assert integrations[0]["provider"] == "twilio"
        print("✓ Integration Manager listing passed")
        
        # Test getting integration status
        status = manager.get_integration_status(integration_id)
        assert status is not None
        assert status["status"] == "active"
        print("✓ Integration Manager status retrieval passed")
        
        # Test stopping integration
        success = await manager.stop_integration(integration_id)
        assert success == True
        print("✓ Integration Manager stop passed")
        
        # Test deleting integration
        success = await manager.delete_integration(integration_id)
        assert success == True
        print("✓ Integration Manager deletion passed")
        
    finally:
        # Restore original classes
        manager.integration_classes = original_classes
    
    # Stop manager
    await manager.stop()
    assert manager.is_running == False
    print("✓ Integration Manager shutdown passed")


def test_integration_configs():
    """Test integration configuration models."""
    print("\nTesting Integration Configurations...")
    
    # Test Twilio config
    twilio_config = TwilioConfig(
        name="Test Twilio Config",
        account_sid="test_sid",
        auth_token="test_token",
        phone_number="+1234567890",
        eu_region=True
    )
    
    assert twilio_config.type == IntegrationType.TELEPHONY
    assert twilio_config.provider == "twilio"
    assert twilio_config.eu_region == True
    print("✓ Twilio configuration passed")
    
    # Test Salesforce config
    sf_config = SalesforceConfig(
        name="Test Salesforce Config",
        client_id="test_client_id",
        client_secret="test_client_secret",
        username="test@example.com",
        password="test_password"
    )
    
    assert sf_config.type == IntegrationType.CRM
    assert sf_config.provider == "salesforce"
    print("✓ Salesforce configuration passed")
    
    # Test WhatsApp config
    wa_config = WhatsAppConfig(
        name="Test WhatsApp Config",
        access_token="test_token",
        phone_number_id="test_phone_id"
    )
    
    assert wa_config.type == IntegrationType.MESSAGING
    assert wa_config.provider == "whatsapp"
    print("✓ WhatsApp configuration passed")


async def main():
    """Run all integration tests."""
    print("🚀 Starting Third-Party Integration Tests...\n")
    
    try:
        # Test configurations
        test_integration_configs()
        
        # Test individual integrations
        await test_twilio_integration()
        await test_salesforce_integration()
        await test_whatsapp_integration()
        await test_telegram_integration()
        
        # Test integration manager
        await test_integration_manager()
        
        print("\n✅ All third-party integration tests passed!")
        
        # Display integration capabilities
        print("\n📋 Third-Party Integration Capabilities:")
        print("  🔗 Telephony Integration (Twilio EU)")
        print("    • Voice calls with TwiML support")
        print("    • SMS and WhatsApp messaging")
        print("    • Call recording and webhooks")
        print("    • EU data residency compliance")
        
        print("  🏢 CRM Integration (Salesforce & SAP)")
        print("    • Contact and account management")
        print("    • Lead tracking and opportunity management")
        print("    • Activity logging and conversation history")
        print("    • Real-time data synchronization")
        
        print("  💬 Messaging Platforms")
        print("    • WhatsApp Business API")
        print("    • Telegram Bot API")
        print("    • Slack App integration")
        print("    • Multi-channel message routing")
        
        print("\n🎯 Integration Use Cases:")
        print("  • Voice-enabled customer support")
        print("  • CRM-integrated conversation tracking")
        print("  • Multi-channel customer engagement")
        print("  • Automated lead qualification")
        print("  • Real-time customer data enrichment")
        
        print("\n🔒 Compliance Features:")
        print("  • EU GDPR compliance")
        print("  • Data residency controls")
        print("  • Audit logging and monitoring")
        print("  • Secure credential management")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())