"""
Edge Orchestrator - Jurisdiction-aware call routing service.

Routes calls to appropriate regional endpoints based on data sovereignty
and compliance requirements (GDPR, AI Act, etc.).
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


class Jurisdiction(str, Enum):
    """Supported jurisdictions with data sovereignty requirements."""
    EU = "eu"
    EEA = "eea"
    UK = "uk"
    SWITZERLAND = "ch"
    ASIA = "asia"
    AFRICA = "africa"
    MIDDLE_EAST = "me"


@dataclass
class RegionalEndpoint:
    """Regional endpoint configuration."""
    jurisdiction: Jurisdiction
    endpoint_url: str
    region: str
    available: bool = True
    latency_ms: float = 0.0
    load: int = 0
    max_capacity: int = 1000


@dataclass
class RoutingRule:
    """Routing rule based on jurisdiction requirements."""
    source_country: str
    allowed_jurisdictions: List[Jurisdiction]
    preferred_jurisdiction: Jurisdiction
    requires_gdpr: bool = False
    requires_ai_act: bool = False


@dataclass
class CallContext:
    """Context for routing decision."""
    call_id: str
    source_country: str
    user_id: Optional[str] = None
    language: Optional[str] = None
    requires_gdpr: bool = False
    requires_ai_act: bool = False
    metadata: Dict = None


class EdgeOrchestrator:
    """Jurisdiction-aware call routing orchestrator."""
    
    def __init__(self):
        self.endpoints: Dict[Jurisdiction, List[RegionalEndpoint]] = {}
        self.routing_rules: Dict[str, RoutingRule] = {}
        self._initialize_default_rules()
        
    def _initialize_default_rules(self):
        """Initialize default routing rules for EU/EEA compliance."""
        eu_countries = ["DE", "FR", "IT", "ES", "NL", "BE", "AT", "PL", "SE", "DK", "FI", "IE", "PT", "GR", "CZ", "RO", "HU"]
        
        for country in eu_countries:
            self.routing_rules[country] = RoutingRule(
                source_country=country,
                allowed_jurisdictions=[Jurisdiction.EU, Jurisdiction.EEA],
                preferred_jurisdiction=Jurisdiction.EU,
                requires_gdpr=True,
                requires_ai_act=True
            )
        
        # UK post-Brexit
        self.routing_rules["GB"] = RoutingRule(
            source_country="GB",
            allowed_jurisdictions=[Jurisdiction.UK, Jurisdiction.EU],
            preferred_jurisdiction=Jurisdiction.UK,
            requires_gdpr=True,
            requires_ai_act=False
        )
        
        # Switzerland
        self.routing_rules["CH"] = RoutingRule(
            source_country="CH",
            allowed_jurisdictions=[Jurisdiction.SWITZERLAND, Jurisdiction.EU],
            preferred_jurisdiction=Jurisdiction.SWITZERLAND,
            requires_gdpr=True,
            requires_ai_act=False
        )
    
    def register_endpoint(self, endpoint: RegionalEndpoint):
        """Register a regional endpoint."""
        if endpoint.jurisdiction not in self.endpoints:
            self.endpoints[endpoint.jurisdiction] = []
        self.endpoints[endpoint.jurisdiction].append(endpoint)
        logger.info(f"Registered endpoint: {endpoint.region} ({endpoint.jurisdiction})")
    
    def add_routing_rule(self, rule: RoutingRule):
        """Add or update routing rule for a country."""
        self.routing_rules[rule.source_country] = rule
        logger.info(f"Added routing rule for {rule.source_country}")
    
    async def route_call(self, context: CallContext) -> Optional[RegionalEndpoint]:
        """Route call to appropriate regional endpoint."""
        rule = self.routing_rules.get(context.source_country)
        
        if not rule:
            logger.warning(f"No routing rule for country: {context.source_country}")
            return None
        
        # Validate compliance requirements
        if rule.requires_gdpr and not context.requires_gdpr:
            logger.error(f"GDPR required but not enabled for call {context.call_id}")
            return None
        
        if rule.requires_ai_act and not context.requires_ai_act:
            logger.error(f"AI Act compliance required but not enabled for call {context.call_id}")
            return None
        
        # Try preferred jurisdiction first
        endpoint = await self._select_endpoint(rule.preferred_jurisdiction)
        if endpoint:
            logger.info(f"Routed call {context.call_id} to {endpoint.region}")
            return endpoint
        
        # Fallback to allowed jurisdictions
        for jurisdiction in rule.allowed_jurisdictions:
            if jurisdiction != rule.preferred_jurisdiction:
                endpoint = await self._select_endpoint(jurisdiction)
                if endpoint:
                    logger.info(f"Routed call {context.call_id} to fallback {endpoint.region}")
                    return endpoint
        
        logger.error(f"No available endpoint for call {context.call_id}")
        return None
    
    async def _select_endpoint(self, jurisdiction: Jurisdiction) -> Optional[RegionalEndpoint]:
        """Select best available endpoint in jurisdiction."""
        endpoints = self.endpoints.get(jurisdiction, [])
        available = [e for e in endpoints if e.available and e.load < e.max_capacity]
        
        if not available:
            return None
        
        # Select endpoint with lowest load
        return min(available, key=lambda e: (e.load / e.max_capacity, e.latency_ms))
    
    async def update_endpoint_status(self, region: str, available: bool, latency_ms: float = 0.0, load: int = 0):
        """Update endpoint health status."""
        for endpoints in self.endpoints.values():
            for endpoint in endpoints:
                if endpoint.region == region:
                    endpoint.available = available
                    endpoint.latency_ms = latency_ms
                    endpoint.load = load
                    logger.debug(f"Updated {region}: available={available}, latency={latency_ms}ms, load={load}")
    
    def get_jurisdiction_stats(self) -> Dict:
        """Get statistics for all jurisdictions."""
        stats = {}
        for jurisdiction, endpoints in self.endpoints.items():
            stats[jurisdiction] = {
                "total_endpoints": len(endpoints),
                "available_endpoints": sum(1 for e in endpoints if e.available),
                "total_capacity": sum(e.max_capacity for e in endpoints),
                "current_load": sum(e.load for e in endpoints),
                "avg_latency_ms": sum(e.latency_ms for e in endpoints) / len(endpoints) if endpoints else 0
            }
        return stats


# Global instance
_edge_orchestrator: Optional[EdgeOrchestrator] = None


def get_edge_orchestrator() -> EdgeOrchestrator:
    """Get global edge orchestrator instance."""
    global _edge_orchestrator
    if _edge_orchestrator is None:
        _edge_orchestrator = EdgeOrchestrator()
    return _edge_orchestrator


def set_edge_orchestrator(orchestrator: EdgeOrchestrator) -> None:
    """Set global edge orchestrator instance."""
    global _edge_orchestrator
    _edge_orchestrator = orchestrator
