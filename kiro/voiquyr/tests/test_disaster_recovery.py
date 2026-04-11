"""
DR System Tests (Task 16.5)

Tests for failover automation, data replication, tenant isolation,
and recovery procedures.
Implements Requirements 16.1, 16.2, 16.3.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.infra import (
    TenantRegistry, TenantConfig, SovereigntyZone,
    EncryptionKeyManager, ZONE_DC_PAIRS, CROSS_ZONE_FAILOVER,
    FailoverManager, DRDrillFramework, FailoverEvent,
    DataCenterHealth, ReplicationStatus, DCStatus, ReplicationMode,
    RTO_TARGET_MINUTES, RPO_TARGET_MINUTES,
    SingleTenantProvisioner, TenantCluster, NetworkPolicy,
    StorageConfig, DeploymentTier, ClusterStatus,
    MultiCloudManager, CloudProvider,
    OVHCloudClient, ScalewayClient, HetznerClient,
    CloudResource, CLOUD_REGIONS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tenant(
    tenant_id: str = "t1",
    zone: SovereigntyZone = SovereigntyZone.DE,
    tier: str = "shared",
) -> TenantConfig:
    return TenantConfig(
        tenant_id=tenant_id,
        name=f"Tenant {tenant_id}",
        zone=zone,
        tier=tier,
    )


# ---------------------------------------------------------------------------
# 16.1 Tenant Isolation Tests
# ---------------------------------------------------------------------------

class TestTenantRegistry:
    def test_register_tenant_creates_encryption_key(self):
        registry = TenantRegistry()
        tenant = registry.register_tenant(make_tenant("t1", SovereigntyZone.DE))
        assert tenant.encryption_key_id is not None
        assert "t1" in tenant.encryption_key_id

    def test_get_tenant(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t2", SovereigntyZone.FR))
        t = registry.get_tenant("t2")
        assert t is not None
        assert t.zone == SovereigntyZone.FR

    def test_data_placement_allowed_same_zone(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t3", SovereigntyZone.DE))
        assert registry.check_data_placement("t3", SovereigntyZone.DE) is True

    def test_data_placement_blocked_cross_zone(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t4", SovereigntyZone.DE))
        # FR is not in allowed_zones for a DE tenant
        assert registry.check_data_placement("t4", SovereigntyZone.FR) is False

    def test_data_placement_unknown_tenant_blocked(self):
        registry = TenantRegistry()
        assert registry.check_data_placement("unknown", SovereigntyZone.DE) is False

    def test_cross_border_violation_is_audited(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t5", SovereigntyZone.NL))
        registry.check_data_placement("t5", SovereigntyZone.AE)
        report = registry.get_compliance_report("t5")
        assert report["violations"] >= 1
        assert report["compliant"] is False

    def test_compliant_tenant_report(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t6", SovereigntyZone.FR))
        registry.check_data_placement("t6", SovereigntyZone.FR)
        report = registry.get_compliance_report("t6")
        assert report["violations"] == 0
        assert report["compliant"] is True

    def test_compliance_report_structure(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t7", SovereigntyZone.SE))
        report = registry.get_compliance_report("t7")
        assert "sovereignty_zone" in report
        assert "primary_dc" in report
        assert "standby_dc" in report
        assert "encryption_key_id" in report

    def test_get_primary_and_standby_dc(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t8", SovereigntyZone.DE))
        primary = registry.get_primary_dc("t8")
        standby = registry.get_standby_dc("t8")
        assert primary == ZONE_DC_PAIRS[SovereigntyZone.DE]["primary"]
        assert standby == ZONE_DC_PAIRS[SovereigntyZone.DE]["standby"]

    def test_multi_tenant_isolation(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("de-tenant", SovereigntyZone.DE))
        registry.register_tenant(make_tenant("fr-tenant", SovereigntyZone.FR))
        # DE tenant cannot write to FR zone
        assert registry.check_data_placement("de-tenant", SovereigntyZone.FR) is False
        # FR tenant cannot write to DE zone
        assert registry.check_data_placement("fr-tenant", SovereigntyZone.DE) is False

    def test_allowed_zones_can_be_extended(self):
        registry = TenantRegistry()
        tenant = make_tenant("t9", SovereigntyZone.DE)
        tenant.allowed_zones = [SovereigntyZone.DE, SovereigntyZone.NL]
        registry.register_tenant(tenant)
        assert registry.check_data_placement("t9", SovereigntyZone.NL) is True


class TestEncryptionKeyManager:
    def test_create_key(self):
        km = EncryptionKeyManager()
        key_id = km.create_key("tenant-1")
        assert key_id is not None
        key = km.get_key(key_id)
        assert key is not None
        assert len(key) == 32  # AES-256

    def test_rotate_key(self):
        km = EncryptionKeyManager()
        key_id = km.create_key("tenant-2")
        new_key_id = km.rotate_key(key_id)
        assert new_key_id != key_id
        assert km.get_key(new_key_id) is not None

    def test_delete_key(self):
        km = EncryptionKeyManager()
        key_id = km.create_key("tenant-3")
        assert km.delete_key(key_id) is True
        assert km.get_key(key_id) is None

    def test_delete_nonexistent_key(self):
        km = EncryptionKeyManager()
        assert km.delete_key("nonexistent") is False


# ---------------------------------------------------------------------------
# 16.2 Failover System Tests
# ---------------------------------------------------------------------------

class TestFailoverManager:
    def _make_registry_with_tenant(self, zone=SovereigntyZone.DE) -> TenantRegistry:
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t1", zone))
        return registry

    @pytest.mark.asyncio
    async def test_execute_failover_success(self):
        registry = self._make_registry_with_tenant()
        manager = FailoverManager(registry)
        manager.set_failover_fn(AsyncMock(return_value=True))

        primary = registry.get_primary_dc("t1")
        standby = registry.get_standby_dc("t1")
        event = await manager.execute_failover("t1", primary, standby, "test")

        assert event.success is True
        assert event.rto_seconds is not None
        assert event.completed_at is not None

    @pytest.mark.asyncio
    async def test_failover_rto_tracked(self):
        registry = self._make_registry_with_tenant()
        manager = FailoverManager(registry)
        manager.set_failover_fn(AsyncMock(return_value=True))

        primary = registry.get_primary_dc("t1")
        standby = registry.get_standby_dc("t1")
        event = await manager.execute_failover("t1", primary, standby)

        # In tests failover is near-instant, so RTO should be met
        assert event.rto_met is True

    @pytest.mark.asyncio
    async def test_failover_failure_handled(self):
        registry = self._make_registry_with_tenant()
        manager = FailoverManager(registry)
        manager.set_failover_fn(AsyncMock(return_value=False))

        primary = registry.get_primary_dc("t1")
        standby = registry.get_standby_dc("t1")
        event = await manager.execute_failover("t1", primary, standby)

        assert event.success is False

    @pytest.mark.asyncio
    async def test_failover_without_fn_succeeds(self):
        registry = self._make_registry_with_tenant()
        manager = FailoverManager(registry)
        # No failover_fn set — simulated success
        primary = registry.get_primary_dc("t1")
        standby = registry.get_standby_dc("t1")
        event = await manager.execute_failover("t1", primary, standby)
        assert event.success is True

    def test_replication_status_rpo(self):
        registry = self._make_registry_with_tenant()
        manager = FailoverManager(registry)
        primary = registry.get_primary_dc("t1")
        standby = registry.get_standby_dc("t1")

        manager.update_replication_status(primary, standby, lag_seconds=30.0)
        rep = manager.get_replication_status(primary, standby)
        assert rep is not None
        assert rep.rpo_met is True  # 30s << 5min

    def test_replication_rpo_violation(self):
        registry = self._make_registry_with_tenant()
        manager = FailoverManager(registry)
        primary = registry.get_primary_dc("t1")
        standby = registry.get_standby_dc("t1")

        manager.update_replication_status(primary, standby, lag_seconds=400.0)
        rep = manager.get_replication_status(primary, standby)
        assert rep.rpo_met is False  # 400s > 300s (5min)

    def test_system_status_structure(self):
        registry = self._make_registry_with_tenant()
        manager = FailoverManager(registry)
        status = manager.get_system_status()
        assert "total_dcs" in status
        assert "healthy_dcs" in status
        assert "replication_links" in status

    @pytest.mark.asyncio
    async def test_failover_history(self):
        registry = self._make_registry_with_tenant()
        manager = FailoverManager(registry)
        manager.set_failover_fn(AsyncMock(return_value=True))
        primary = registry.get_primary_dc("t1")
        standby = registry.get_standby_dc("t1")

        await manager.execute_failover("t1", primary, standby)
        await manager.execute_failover("t1", primary, standby)

        history = manager.get_failover_history("t1")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_start_stop(self):
        registry = self._make_registry_with_tenant()
        manager = FailoverManager(registry, health_check_interval=0.1)
        await manager.start()
        assert manager._running is True
        await manager.stop()
        assert manager._running is False

    def test_rto_rpo_constants(self):
        assert RTO_TARGET_MINUTES == 15
        assert RPO_TARGET_MINUTES == 5


class TestDRDrillFramework:
    @pytest.mark.asyncio
    async def test_drill_completes(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t1", SovereigntyZone.DE))
        manager = FailoverManager(registry)
        manager.set_failover_fn(AsyncMock(return_value=True))
        drill = DRDrillFramework(manager)

        result = await drill.run_drill("t1")
        assert result["success"] is True
        assert "rto_met" in result
        assert "rpo_met" in result
        assert "playbook" in result

    @pytest.mark.asyncio
    async def test_drill_generates_playbook(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t1", SovereigntyZone.FR))
        manager = FailoverManager(registry)
        manager.set_failover_fn(AsyncMock(return_value=True))
        drill = DRDrillFramework(manager)

        result = await drill.run_drill("t1")
        playbook = result["playbook"]
        assert "steps" in playbook
        assert len(playbook["steps"]) >= 5

    @pytest.mark.asyncio
    async def test_drill_history_recorded(self):
        registry = TenantRegistry()
        registry.register_tenant(make_tenant("t1", SovereigntyZone.NL))
        manager = FailoverManager(registry)
        manager.set_failover_fn(AsyncMock(return_value=True))
        drill = DRDrillFramework(manager)

        await drill.run_drill("t1")
        await drill.run_drill("t1")
        assert len(drill.get_drill_history()) == 2

    @pytest.mark.asyncio
    async def test_drill_unknown_tenant(self):
        registry = TenantRegistry()
        manager = FailoverManager(registry)
        drill = DRDrillFramework(manager)
        result = await drill.run_drill("nonexistent")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# 16.3 Single-Tenant Deployment Tests
# ---------------------------------------------------------------------------

class TestSingleTenantProvisioner:
    @pytest.mark.asyncio
    async def test_provision_cluster(self):
        provisioner = SingleTenantProvisioner()
        cluster = await provisioner.provision(
            tenant_id="bank-1",
            zone="de",
            cloud_provider="hetzner",
            tier=DeploymentTier.SINGLE_TENANT,
        )
        assert cluster.status == ClusterStatus.ACTIVE
        assert cluster.tenant_id == "bank-1"
        assert cluster.namespace == "tenant-bank-1"
        assert cluster.kubeconfig_secret is not None

    @pytest.mark.asyncio
    async def test_provision_creates_network_policy(self):
        provisioner = SingleTenantProvisioner()
        cluster = await provisioner.provision("gov-1", "fr", "ovhcloud")
        assert cluster.network_policy is not None
        assert cluster.network_policy.deny_cross_tenant is True

    @pytest.mark.asyncio
    async def test_provision_creates_storage_config(self):
        provisioner = SingleTenantProvisioner()
        cluster = await provisioner.provision("health-1", "nl", "scaleway")
        assert cluster.storage_config is not None
        assert cluster.storage_config.backup_enabled is True

    @pytest.mark.asyncio
    async def test_deprovision_cluster(self):
        provisioner = SingleTenantProvisioner()
        cluster = await provisioner.provision("t1", "de", "hetzner")
        result = await provisioner.deprovision(cluster.cluster_id)
        assert result is True
        assert provisioner.get_cluster(cluster.cluster_id) is None

    @pytest.mark.asyncio
    async def test_deprovision_nonexistent(self):
        provisioner = SingleTenantProvisioner()
        assert await provisioner.deprovision("nonexistent") is False

    @pytest.mark.asyncio
    async def test_get_tenant_clusters(self):
        provisioner = SingleTenantProvisioner()
        await provisioner.provision("t1", "de", "hetzner")
        await provisioner.provision("t1", "fr", "ovhcloud")
        await provisioner.provision("t2", "nl", "scaleway")
        clusters = provisioner.get_tenant_clusters("t1")
        assert len(clusters) == 2

    def test_generate_manifests(self):
        provisioner = SingleTenantProvisioner()
        cluster = TenantCluster(
            cluster_id="c1", tenant_id="t1",
            tier=DeploymentTier.SINGLE_TENANT,
            zone="de", cloud_provider="hetzner",
            network_policy=NetworkPolicy("t1", ["10.0.0.0/8"], ["0.0.0.0/0"]),
            storage_config=StorageConfig("t1"),
        )
        manifests = provisioner.generate_manifests(cluster)
        assert "namespace" in manifests
        assert "network_policy" in manifests
        assert "pvc_data" in manifests
        assert "resource_quota" in manifests

    def test_network_policy_k8s_manifest(self):
        policy = NetworkPolicy(
            tenant_id="t1",
            allow_ingress_from=["10.0.0.0/8"],
            allow_egress_to=["0.0.0.0/0"],
        )
        manifest = policy.to_k8s_manifest()
        assert manifest["kind"] == "NetworkPolicy"
        assert manifest["metadata"]["namespace"] == "tenant-t1"

    def test_storage_pvc_manifest(self):
        storage = StorageConfig(tenant_id="t1", encryption_key_id="key-123")
        pvc = storage.to_k8s_pvc("data", 200)
        assert pvc["kind"] == "PersistentVolumeClaim"
        assert pvc["spec"]["resources"]["requests"]["storage"] == "200Gi"


# ---------------------------------------------------------------------------
# 16.4 Multi-Cloud Management Tests
# ---------------------------------------------------------------------------

class TestMultiCloudManager:
    def test_register_provider(self):
        manager = MultiCloudManager()
        client = HetznerClient(api_key="test-key")
        manager.register_provider(client)
        assert CloudProvider.HETZNER in manager._clients

    def test_register_resource(self):
        manager = MultiCloudManager()
        resource = CloudResource(
            resource_id="r1",
            provider=CloudProvider.HETZNER,
            region_id="nbg1",
            resource_type="server",
            name="voiquyr-node-1",
            status="running",
            tenant_id="t1",
            cost_per_hour_eur=0.05,
        )
        manager.register_resource(resource)
        assert len(manager.get_resources_by_tenant("t1")) == 1

    def test_cost_summary(self):
        manager = MultiCloudManager()
        for i, provider in enumerate(CloudProvider):
            manager.register_resource(CloudResource(
                resource_id=f"r{i}",
                provider=provider,
                region_id="test",
                resource_type="server",
                name=f"node-{i}",
                status="running",
                cost_per_hour_eur=1.0,
            ))
        summary = manager.get_cost_summary()
        assert summary["total_hourly_eur"] == 3.0
        assert summary["total_monthly_eur"] == pytest.approx(3.0 * 24 * 30, rel=0.01)

    def test_unified_dashboard_structure(self):
        manager = MultiCloudManager()
        dashboard = manager.get_unified_dashboard()
        assert "available_regions" in dashboard
        assert "cost_summary" in dashboard
        assert "resources_by_provider" in dashboard

    def test_cloud_regions_coverage(self):
        providers = {r.provider for r in CLOUD_REGIONS}
        assert CloudProvider.OVHCLOUD in providers
        assert CloudProvider.SCALEWAY in providers
        assert CloudProvider.HETZNER in providers

    def test_all_regions_have_sovereignty_zone(self):
        for region in CLOUD_REGIONS:
            assert region.sovereignty_zone, f"Missing zone for {region.region_id}"

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        manager = MultiCloudManager()
        client = HetznerClient(api_key="test")
        client.health_check = AsyncMock(return_value=True)
        manager.register_provider(client)
        results = await manager.health_check_all()
        assert results.get("hetzner") is True

    def test_get_resources_by_provider(self):
        manager = MultiCloudManager()
        manager.register_resource(CloudResource(
            resource_id="r1", provider=CloudProvider.SCALEWAY,
            region_id="fr-par", resource_type="k8s",
            name="cluster-1", status="ready",
        ))
        manager.register_resource(CloudResource(
            resource_id="r2", provider=CloudProvider.HETZNER,
            region_id="nbg1", resource_type="server",
            name="node-1", status="running",
        ))
        assert len(manager.get_resources_by_provider(CloudProvider.SCALEWAY)) == 1
        assert len(manager.get_resources_by_provider(CloudProvider.HETZNER)) == 1


# ---------------------------------------------------------------------------
# Cross-zone failover map completeness
# ---------------------------------------------------------------------------

class TestZoneConfiguration:
    def test_all_zones_have_dc_pairs(self):
        for zone in SovereigntyZone:
            assert zone in ZONE_DC_PAIRS, f"Missing DC pair for {zone.value}"
            assert "primary" in ZONE_DC_PAIRS[zone]
            assert "standby" in ZONE_DC_PAIRS[zone]

    def test_cross_zone_failover_map(self):
        for zone in SovereigntyZone:
            assert zone in CROSS_ZONE_FAILOVER, f"Missing failover for {zone.value}"
            target = CROSS_ZONE_FAILOVER[zone]
            assert target != zone  # Must failover to a different zone
