"""
Infrastructure package — Multi-Cloud Disaster Recovery
"""
from .tenancy import (
    TenantRegistry, TenantConfig, SovereigntyZone,
    DataResidencyEvent, EncryptionKeyManager,
    ZONE_DC_PAIRS, CROSS_ZONE_FAILOVER,
)
from .failover import (
    FailoverManager, DRDrillFramework, FailoverEvent,
    DataCenterHealth, ReplicationStatus, DCStatus, ReplicationMode,
    RTO_TARGET_MINUTES, RPO_TARGET_MINUTES,
)
from .single_tenant import (
    SingleTenantProvisioner, TenantCluster, NetworkPolicy,
    StorageConfig, DeploymentTier, ClusterStatus,
)
from .multicloud import (
    MultiCloudManager, CloudProvider, CloudProviderClient,
    OVHCloudClient, ScalewayClient, HetznerClient,
    CloudResource, CloudRegion, CLOUD_REGIONS,
)

__all__ = [
    "TenantRegistry", "TenantConfig", "SovereigntyZone",
    "DataResidencyEvent", "EncryptionKeyManager",
    "ZONE_DC_PAIRS", "CROSS_ZONE_FAILOVER",
    "FailoverManager", "DRDrillFramework", "FailoverEvent",
    "DataCenterHealth", "ReplicationStatus", "DCStatus", "ReplicationMode",
    "RTO_TARGET_MINUTES", "RPO_TARGET_MINUTES",
    "SingleTenantProvisioner", "TenantCluster", "NetworkPolicy",
    "StorageConfig", "DeploymentTier", "ClusterStatus",
    "MultiCloudManager", "CloudProvider", "CloudProviderClient",
    "OVHCloudClient", "ScalewayClient", "HetznerClient",
    "CloudResource", "CloudRegion", "CLOUD_REGIONS",
]
