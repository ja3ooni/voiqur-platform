"""
Third-Party Integrations

Integration framework for connecting EUVoice AI Platform with external services
including telephony, CRM systems, and messaging platforms.
"""

from .base import BaseIntegration, IntegrationConfig, IntegrationStatus
from .telephony import TwilioIntegration
from .crm import SalesforceIntegration, SAPIntegration
from .messaging import WhatsAppIntegration, TelegramIntegration, SlackIntegration
from .manager import IntegrationManager

__all__ = [
    'BaseIntegration',
    'IntegrationConfig', 
    'IntegrationStatus',
    'TwilioIntegration',
    'SalesforceIntegration',
    'SAPIntegration',
    'WhatsAppIntegration',
    'TelegramIntegration',
    'SlackIntegration',
    'IntegrationManager'
]