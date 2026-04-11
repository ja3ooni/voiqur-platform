"""
Single-Tenant Deployment

Dedicated Kubernetes cluster provisioning, isolated networking/storage,
tenant-specific monitoring, and custom security policies.
Implements Requirement 16.3.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeploymentTier(Enum):
    SHARED = "shared"
    SINGLE_TENANT = "single_tenant"
    DEDICATED_REGION = "dedicated_region"


class ClusterStatus(Enum):
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    UPDATING = "updating"
    SUSPENDED = "suspended"
    DEPROVISIONING = "deprovisioning"


@dataclass
class NetworkPolicy:
    """Kubernetes NetworkPolicy spec for tenant isolation."""
    tenant_id: str
    allow_ingress_from: List[str] = field(default_factory=list)   # CIDR blocks
    allow_egress_to: List[str] = field(default_factory=list)
    deny_cross_tenant: bool = True

    def to_k8s_manifest(self) -> Dict[str, Any]:
        return {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {
                "name": f"tenant-{self.tenant_id}-isolation",
                "namespace": f"tenant-{self.tenant_id}",
            },
            "spec": {
                "podSelector": {},
                "policyTypes": ["Ingress", "Egress"],
                "ingress": [
                    {"from": [{"ipBlock": {"cidr": cidr}}]}
                    for cidr in self.allow_ingress_from
                ],
                "egress": [
                    {"to": [{"ipBlock": {"cidr": cidr}}]}
                    for cidr in self.allow_egress_to
                ],
            },
        }


@dataclass
class StorageConfig:
    """Isolated storage configuration per tenant."""
    tenant_id: str
    storage_class: str = "eu-ssd-encrypted"
    encryption_key_id: Optional[str] = None
    backup_enabled: bool = True
    backup_retention_days: int = 30
    replication_factor: int = 3

    def to_k8s_pvc(self, name: str, size_gi: int = 100) -> Dict[str, Any]:
        return {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": name,
                "namespace": f"tenant-{self.tenant_id}",
                "annotations": {
                    "encryption-key": self.encryption_key_id or "",
                    "backup-enabled": str(self.backup_enabled).lower(),
                },
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": self.storage_class,
                "resources": {"requests": {"storage": f"{size_gi}Gi"}},
            },
        }


@dataclass
class TenantCluster:
    cluster_id: str
    tenant_id: str
    tier: DeploymentTier
    zone: str
    cloud_provider: str          # "ovhcloud" | "scaleway" | "hetzner"
    status: ClusterStatus = ClusterStatus.PROVISIONING
    namespace: str = ""
    kubeconfig_secret: Optional[str] = None
    node_count: int = 3
    node_type: str = "standard-4"
    created_at: datetime = field(default_factory=datetime.utcnow)
    network_policy: Optional[NetworkPolicy] = None
    storage_config: Optional[StorageConfig] = None

    def __post_init__(self):
        if not self.namespace:
            self.namespace = f"tenant-{self.tenant_id}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "tenant_id": self.tenant_id,
            "tier": self.tier.value,
            "zone": self.zone,
            "cloud_provider": self.cloud_provider,
            "status": self.status.value,
            "namespace": self.namespace,
            "node_count": self.node_count,
            "node_type": self.node_type,
            "created_at": self.created_at.isoformat(),
        }


class SingleTenantProvisioner:
    """
    Provisions and manages dedicated single-tenant Kubernetes clusters.

    In production this calls the cloud provider's Kubernetes API
    (OVHcloud Managed Kubernetes, Scaleway Kapsule, Hetzner K3s).
    Here we model the provisioning lifecycle and generate manifests.
    """

    def __init__(self):
        self._clusters: Dict[str, TenantCluster] = {}
        self.logger = logging.getLogger(__name__)

    async def provision(
        self,
        tenant_id: str,
        zone: str,
        cloud_provider: str,
        tier: DeploymentTier = DeploymentTier.SINGLE_TENANT,
        node_count: int = 3,
        node_type: str = "standard-4",
        encryption_key_id: Optional[str] = None,
    ) -> TenantCluster:
        cluster_id = f"cluster-{tenant_id}-{uuid.uuid4().hex[:6]}"
        network_policy = NetworkPolicy(
            tenant_id=tenant_id,
            allow_ingress_from=["10.0.0.0/8"],
            allow_egress_to=["0.0.0.0/0"],
            deny_cross_tenant=True,
        )
        storage_config = StorageConfig(
            tenant_id=tenant_id,
            encryption_key_id=encryption_key_id,
        )
        cluster = TenantCluster(
            cluster_id=cluster_id,
            tenant_id=tenant_id,
            tier=tier,
            zone=zone,
            cloud_provider=cloud_provider,
            node_count=node_count,
            node_type=node_type,
            network_policy=network_policy,
            storage_config=storage_config,
        )
        self._clusters[cluster_id] = cluster
        self.logger.info(
            f"Provisioning cluster {cluster_id} for tenant {tenant_id} "
            f"on {cloud_provider} in {zone}"
        )
        # Simulate async provisioning
        cluster.status = ClusterStatus.ACTIVE
        cluster.kubeconfig_secret = f"kubeconfig-{cluster_id}"
        return cluster

    async def deprovision(self, cluster_id: str) -> bool:
        cluster = self._clusters.get(cluster_id)
        if not cluster:
            return False
        cluster.status = ClusterStatus.DEPROVISIONING
        del self._clusters[cluster_id]
        self.logger.info(f"Deprovisioned cluster {cluster_id}")
        return True

    def get_cluster(self, cluster_id: str) -> Optional[TenantCluster]:
        return self._clusters.get(cluster_id)

    def get_tenant_clusters(self, tenant_id: str) -> List[TenantCluster]:
        return [c for c in self._clusters.values() if c.tenant_id == tenant_id]

    def generate_manifests(self, cluster: TenantCluster) -> Dict[str, Any]:
        """Generate all Kubernetes manifests for a tenant cluster."""
        manifests: Dict[str, Any] = {
            "namespace": {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {
                    "name": cluster.namespace,
                    "labels": {
                        "tenant": cluster.tenant_id,
                        "tier": cluster.tier.value,
                    },
                },
            },
        }
        if cluster.network_policy:
            manifests["network_policy"] = cluster.network_policy.to_k8s_manifest()
        if cluster.storage_config:
            manifests["pvc_data"] = cluster.storage_config.to_k8s_pvc("data", 200)
            manifests["pvc_models"] = cluster.storage_config.to_k8s_pvc("models", 500)
        manifests["resource_quota"] = {
            "apiVersion": "v1",
            "kind": "ResourceQuota",
            "metadata": {"name": "tenant-quota", "namespace": cluster.namespace},
            "spec": {
                "hard": {
                    "requests.cpu": "16",
                    "requests.memory": "64Gi",
                    "limits.cpu": "32",
                    "limits.memory": "128Gi",
                }
            },
        }
        return manifests

    def get_all_clusters(self) -> List[TenantCluster]:
        return list(self._clusters.values())
