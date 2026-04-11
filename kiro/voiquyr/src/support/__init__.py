"""
Support package
"""
from .ticketing import (
    TicketingSystem, Ticket, SupportAgent, TicketPriority,
    TicketStatus, TicketChannel, SLA_RESPONSE_MINUTES, SLA_RESOLUTION_MINUTES,
)
from .sla import (
    SLAManager, SLADefinition, SLABreach, UptimeRecord, UPTIME_TARGET,
)
from .account_management import (
    AccountManagementSystem, AccountManager, AccountHealth, EscalationRecord,
    AccountTier, HealthScore, EscalationLevel,
)
from .onboarding import (
    OnboardingSystem, OnboardingPlan, TrainingSession, CertificationRecord,
    OnboardingStage, TrainingStatus,
    RegionalSupportRouter, RegionalQueue, SUPPORTED_LANGUAGES, REGIONAL_HOURS,
)

__all__ = [
    "TicketingSystem", "Ticket", "SupportAgent", "TicketPriority",
    "TicketStatus", "TicketChannel", "SLA_RESPONSE_MINUTES", "SLA_RESOLUTION_MINUTES",
    "SLAManager", "SLADefinition", "SLABreach", "UptimeRecord", "UPTIME_TARGET",
    "AccountManagementSystem", "AccountManager", "AccountHealth", "EscalationRecord",
    "AccountTier", "HealthScore", "EscalationLevel",
    "OnboardingSystem", "OnboardingPlan", "TrainingSession", "CertificationRecord",
    "OnboardingStage", "TrainingStatus",
    "RegionalSupportRouter", "RegionalQueue", "SUPPORTED_LANGUAGES", "REGIONAL_HOURS",
]
