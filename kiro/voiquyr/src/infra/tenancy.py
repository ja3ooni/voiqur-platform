"""
Per-Client Data Tenancy

Tenant isolation with geographic data placement, cross-border prevention,
per-tenant encryption keys, and compliance reporting.
Implements Requirements 16.1, 16.5.
"""

import hashlib
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SovereigntyZone(Enum):
    """EU + MEA sovereignty zones — data stays within zone."""
    DE = "de"          # Germany (Frankfurt)
    FR = "fr"          # France (Paris)
    IE = "ie"          # Ireland (Dublin)
    NL = "nl"          # Netherlands (Amsterdam)
    SE = "se"          # Sweden (Stockholm)
    PL = "pl"          # Poland (Warsaw)
    AE = "ae"          # UAE (Dubai)
    SA = "sa"          # Saudi Arabia (Riyadh)


# Primary + standby DC pairs within the same sovereignty zone (no cross-border)
ZONE_DC_PAIRS: Dict[SovereigntyZone, Dict[str, str]] = {
    SovereigntyZone.DE: {"primary": "frankfurt-1", "standby": "frankfurt-2"},
    SovereigntyZone.FR: {"primary": "paris-1",     "standby": "paris-2"},
    SovereigntyZone.IE: {"primary": "dublin-1",    "standby": "dublin-2"},
    SovereigntyZone.NL: {"primary": "amsterdam-1", "standby": "amsterdam-2"},
    SovereigntyZone.SE: {"primary": "stockholm-1", "standby": "stockholm-2"},
    SovereigntyZone.PL: {"primary": "warsaw-1",    "standby": "warsaw-2"},
    SovereigntyZone.AE: {"primary": "dubai-1",     "standby": "dubai-2"},
    SovereigntyZone.SA: {"primary": "riyadh-1",    "standby": "riyadh-2"},
}

# Cross-zone failover map (same sovereignty region, different country only if legally allowed)
CROSS_ZONE_FAILOVER: Dict[SovereigntyZone, SovereigntyZone] = {
    SovereigntyZone.DE: SovereigntyZone.NL,   # Frankfurt → Amsterdam (EU)
    SovereigntyZone.FR: SovereigntyZone.IE,   # Paris → Dublin (EU)
    SovereigntyZone.IE: SovereigntyZone.FR,
    SovereigntyZone.NL: SovereigntyZone.DE,
    SovereigntyZone.SE: SovereigntyZone.PL,
    SovereigntyZone.PL: SovereigntyZone.SE,
    SovereigntyZone.AE: SovereigntyZone.SA,
    SovereigntyZone.SA: SovereigntyZone.AE,
}


@dataclass
class TenantConfig:
    tenant_id: str
    name: str
    zone: SovereigntyZone
    tier: str = "shared"          # "shared" | "single-tenant"
    allowed_zones: List[SovereigntyZone] = field(default_factory=list)
    encryption_key_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.allowed_zones:
            self.allowed_zones = [self.zone]
        if not self.encryption_key_id:
            self.encryption_key_id = f"key-{self.tenant_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "zone": self.zone.value,
            "tier": self.tier,
            "allowed_zones": [z.value for z in self.allowed_zones],
            "encryption_key_id": self.encryption_key_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DataResidencyEvent:
    """Audit log entry for data placement / access."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str = ""
    operation: str = ""       # "read" | "write" | "replicate" | "access"
    source_zone: Optional[SovereigntyZone] = None
    target_zone: Optional[SovereigntyZone] = None
    allowed: bool = True
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "operation": self.operation,
            "source_zone": self.source_zone.value if self.source_zone else None,
            "target_zone": self.target_zone.value if self.target_zone else None,
            "allowed": self.allowed,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


class EncryptionKeyManager:
    """
    Per-tenant encryption key management.
    In production this wraps AWS KMS / HashiCorp Vault / Azure Key Vault.
    """

    def __init__(self):
        self._keys: Dict[str, bytes] = {}

    def create_key(self, tenant_id: str) -> str:
        key_id = f"key-{tenant_id}-{uuid.uuid4().hex[:8]}"
        self._keys[key_id] = os.urandom(32)   # AES-256
        logger.info(f"Created encryption key {key_id} for tenant {tenant_id}")
        return key_id

    def get_key(self, key_id: str) -> Optional[bytes]:
        return self._keys.get(key_id)

    def rotate_key(self, key_id: str) -> str:
        """Rotate key — returns new key_id."""
        tenant_id = key_id.split("-")[1] if "-" in key_id else key_id
        new_key_id = self.create_key(tenant_id)
        logger.info(f"Rotated key {key_id} → {new_key_id}")
        return new_key_id

    def delete_key(self, key_id: str) -> bool:
        if key_id in self._keys:
            del self._keys[key_id]
            return True
        return False


class TenantRegistry:
    """
    Central registry for tenant isolation and data placement enforcement.
    """

    def __init__(self):
        self._tenants: Dict[str, TenantConfig] = {}
        self._audit_log: List[DataResidencyEvent] = []
        self._key_manager = EncryptionKeyManager()
        self.logger = logging.getLogger(__name__)

    def register_tenant(self, config: TenantConfig) -> TenantConfig:
        if not config.encryption_key_id or config.encryption_key_id == f"key-{config.tenant_id}":
            config.encryption_key_id = self._key_manager.create_key(config.tenant_id)
        self._tenants[config.tenant_id] = config
        self.logger.info(
            f"Registered tenant {config.tenant_id} in zone {config.zone.value}"
        )
        return config

    def get_tenant(self, tenant_id: str) -> Optional[TenantConfig]:
        return self._tenants.get(tenant_id)

    def check_data_placement(
        self,
        tenant_id: str,
        target_zone: SovereigntyZone,
        operation: str = "write",
    ) -> bool:
        """
        Enforce cross-border prevention.
        Returns True if the operation is allowed, False if it would violate sovereignty.
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            self._audit(tenant_id, operation, None, target_zone, False, "Unknown tenant")
            return False

        allowed = target_zone in tenant.allowed_zones
        reason = "allowed" if allowed else f"Zone {target_zone.value} not in tenant allowed zones"
        self._audit(tenant_id, operation, tenant.zone, target_zone, allowed, reason)

        if not allowed:
            self.logger.warning(
                f"Cross-border violation blocked: tenant={tenant_id} "
                f"zone={tenant.zone.value} → {target_zone.value}"
            )
        return allowed

    def get_primary_dc(self, tenant_id: str) -> Optional[str]:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None
        return ZONE_DC_PAIRS[tenant.zone]["primary"]

    def get_standby_dc(self, tenant_id: str) -> Optional[str]:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None
        return ZONE_DC_PAIRS[tenant.zone]["standby"]

    def get_compliance_report(self, tenant_id: str) -> Dict[str, Any]:
        """Generate data residency compliance report for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}

        events = [e for e in self._audit_log if e.tenant_id == tenant_id]
        violations = [e for e in events if not e.allowed]
        zone_pair = ZONE_DC_PAIRS[tenant.zone]

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "sovereignty_zone": tenant.zone.value,
            "primary_dc": zone_pair["primary"],
            "standby_dc": zone_pair["standby"],
            "allowed_zones": [z.value for z in tenant.allowed_zones],
            "encryption_key_id": tenant.encryption_key_id,
            "total_data_events": len(events),
            "violations": len(violations),
            "compliant": len(violations) == 0,
            "report_generated_at": datetime.utcnow().isoformat(),
            "recent_violations": [v.to_dict() for v in violations[-10:]],
        }

    def get_all_tenants(self) -> List[TenantConfig]:
        return list(self._tenants.values())

    def _audit(
        self,
        tenant_id: str,
        operation: str,
        source: Optional[SovereigntyZone],
        target: Optional[SovereigntyZone],
        allowed: bool,
        reason: str,
    ) -> None:
        self._audit_log.append(DataResidencyEvent(
            tenant_id=tenant_id,
            operation=operation,
            source_zone=source,
            target_zone=target,
            allowed=allowed,
            reason=reason,
        ))
