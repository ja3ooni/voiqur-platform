"""
Multi-Cloud Management

Unified management interface for OVHcloud, Scaleway, and Hetzner EU cloud providers.
Implements Requirement 16.7.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class CloudProvider(Enum):
    OVHCLOUD = "ovhcloud"
    SCALEWAY = "scaleway"
    HETZNER = "hetzner"


@dataclass
class CloudRegion:
    provider: CloudProvider
    region_id: str
    display_name: str
    country: str
    sovereignty_zone: str   # maps to SovereigntyZone values


# EU cloud regions per provider
CLOUD_REGIONS: List[CloudRegion] = [
    # OVHcloud
    CloudRegion(CloudProvider.OVHCLOUD, "gra11", "Gravelines (FR)", "FR", "fr"),
    CloudRegion(CloudProvider.OVHCLOUD, "de1",   "Frankfurt (DE)",  "DE", "de"),
    CloudRegion(CloudProvider.OVHCLOUD, "uk1",   "London (UK)",     "GB", "ie"),
    # Scaleway
    CloudRegion(CloudProvider.SCALEWAY, "fr-par", "Paris (FR)",      "FR", "fr"),
    CloudRegion(CloudProvider.SCALEWAY, "nl-ams", "Amsterdam (NL)",  "NL", "nl"),
    CloudRegion(CloudProvider.SCALEWAY, "pl-waw", "Warsaw (PL)",     "PL", "pl"),
    # Hetzner
    CloudRegion(CloudProvider.HETZNER, "nbg1",  "Nuremberg (DE)",  "DE", "de"),
    CloudRegion(CloudProvider.HETZNER, "fsn1",  "Falkenstein (DE)","DE", "de"),
    CloudRegion(CloudProvider.HETZNER, "hel1",  "Helsinki (FI)",   "FI", "se"),
]


@dataclass
class CloudResource:
    resource_id: str
    provider: CloudProvider
    region_id: str
    resource_type: str    # "server" | "k8s" | "volume" | "lb"
    name: str
    status: str
    tenant_id: Optional[str] = None
    cost_per_hour_eur: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "provider": self.provider.value,
            "region_id": self.region_id,
            "resource_type": self.resource_type,
            "name": self.name,
            "status": self.status,
            "tenant_id": self.tenant_id,
            "cost_per_hour_eur": self.cost_per_hour_eur,
            "created_at": self.created_at.isoformat(),
        }


class CloudProviderClient:
    """Base async client for EU cloud provider APIs."""

    def __init__(self, provider: CloudProvider, api_key: str, base_url: str):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(f"{__name__}.{provider.value}")

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self._auth_headers()
            )
        return self._session

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def list_resources(self, region_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    async def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    async def health_check(self) -> bool:
        raise NotImplementedError


class OVHCloudClient(CloudProviderClient):
    def __init__(self, api_key: str, app_key: str = "", app_secret: str = ""):
        super().__init__(
            CloudProvider.OVHCLOUD, api_key,
            "https://eu.api.ovh.com/v1"
        )
        self.app_key = app_key
        self.app_secret = app_secret

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "X-Ovh-Application": self.app_key,
            "X-Ovh-Consumer": self.api_key,
        }

    async def list_resources(self, region_id: str) -> List[Dict[str, Any]]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/cloud/project", ssl=False
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            self.logger.warning(f"OVHcloud list_resources failed: {e}")
        return []

    async def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/cloud/project/{resource_id}", ssl=False
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            self.logger.warning(f"OVHcloud get_resource failed: {e}")
        return None

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/status/task", ssl=False
            ) as resp:
                return resp.status == 200
        except Exception:
            return False


class ScalewayClient(CloudProviderClient):
    def __init__(self, api_key: str, org_id: str = ""):
        super().__init__(
            CloudProvider.SCALEWAY, api_key,
            "https://api.scaleway.com"
        )
        self.org_id = org_id

    def _auth_headers(self) -> Dict[str, str]:
        return {"X-Auth-Token": self.api_key}

    async def list_resources(self, region_id: str) -> List[Dict[str, Any]]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/k8s/v1/regions/{region_id}/clusters",
                ssl=False,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("clusters", [])
        except Exception as e:
            self.logger.warning(f"Scaleway list_resources failed: {e}")
        return []

    async def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/k8s/v1/clusters/{resource_id}", ssl=False
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            self.logger.warning(f"Scaleway get_resource failed: {e}")
        return None

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/account/v3/projects", ssl=False
            ) as resp:
                return resp.status in (200, 401)  # 401 = reachable but bad key
        except Exception:
            return False


class HetznerClient(CloudProviderClient):
    def __init__(self, api_key: str):
        super().__init__(
            CloudProvider.HETZNER, api_key,
            "https://api.hetzner.cloud/v1"
        )

    async def list_resources(self, region_id: str) -> List[Dict[str, Any]]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/servers?location={region_id}", ssl=False
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("servers", [])
        except Exception as e:
            self.logger.warning(f"Hetzner list_resources failed: {e}")
        return []

    async def get_resource(self, resource_id: str) -> Optional[Dict[str, Any]]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/servers/{resource_id}", ssl=False
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("server")
        except Exception as e:
            self.logger.warning(f"Hetzner get_resource failed: {e}")
        return None

    async def health_check(self) -> bool:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/datacenters", ssl=False
            ) as resp:
                return resp.status in (200, 401)
        except Exception:
            return False


class MultiCloudManager:
    """
    Unified management interface across OVHcloud, Scaleway, and Hetzner.
    Provides cross-cloud resource inventory, health monitoring, and cost tracking.
    """

    def __init__(self):
        self._clients: Dict[CloudProvider, CloudProviderClient] = {}
        self._resources: Dict[str, CloudResource] = {}
        self.logger = logging.getLogger(__name__)

    def register_provider(self, client: CloudProviderClient) -> None:
        self._clients[client.provider] = client
        self.logger.info(f"Registered cloud provider: {client.provider.value}")

    def register_resource(self, resource: CloudResource) -> None:
        self._resources[resource.resource_id] = resource

    async def health_check_all(self) -> Dict[str, bool]:
        results = {}
        tasks = {
            provider.value: client.health_check()
            for provider, client in self._clients.items()
        }
        for name, coro in tasks.items():
            try:
                results[name] = await coro
            except Exception:
                results[name] = False
        return results

    async def list_all_resources(self) -> List[CloudResource]:
        """Fetch resources from all registered providers."""
        all_resources: List[CloudResource] = []
        for provider, client in self._clients.items():
            regions = [r for r in CLOUD_REGIONS if r.provider == provider]
            for region in regions:
                try:
                    raw = await client.list_resources(region.region_id)
                    for item in raw:
                        resource = CloudResource(
                            resource_id=str(item.get("id", "")),
                            provider=provider,
                            region_id=region.region_id,
                            resource_type=item.get("type", "unknown"),
                            name=item.get("name", ""),
                            status=item.get("status", "unknown"),
                            metadata=item,
                        )
                        self._resources[resource.resource_id] = resource
                        all_resources.append(resource)
                except Exception as e:
                    self.logger.warning(
                        f"Failed to list resources for {provider.value}/{region.region_id}: {e}"
                    )
        return all_resources

    def get_resources_by_tenant(self, tenant_id: str) -> List[CloudResource]:
        return [r for r in self._resources.values() if r.tenant_id == tenant_id]

    def get_resources_by_provider(self, provider: CloudProvider) -> List[CloudResource]:
        return [r for r in self._resources.values() if r.provider == provider]

    def get_cost_summary(self) -> Dict[str, Any]:
        """Aggregate hourly cost across all providers."""
        by_provider: Dict[str, float] = {}
        by_tenant: Dict[str, float] = {}
        total = 0.0
        for r in self._resources.values():
            by_provider[r.provider.value] = (
                by_provider.get(r.provider.value, 0.0) + r.cost_per_hour_eur
            )
            if r.tenant_id:
                by_tenant[r.tenant_id] = (
                    by_tenant.get(r.tenant_id, 0.0) + r.cost_per_hour_eur
                )
            total += r.cost_per_hour_eur
        return {
            "total_hourly_eur": round(total, 4),
            "total_monthly_eur": round(total * 24 * 30, 2),
            "by_provider": {k: round(v, 4) for k, v in by_provider.items()},
            "by_tenant": {k: round(v, 4) for k, v in by_tenant.items()},
        }

    def get_unified_dashboard(self) -> Dict[str, Any]:
        return {
            "providers": list(self._clients.keys()),
            "total_resources": len(self._resources),
            "resources_by_provider": {
                p.value: len(self.get_resources_by_provider(p))
                for p in CloudProvider
            },
            "available_regions": [
                {"provider": r.provider.value, "region": r.region_id,
                 "country": r.country, "zone": r.sovereignty_zone}
                for r in CLOUD_REGIONS
            ],
            "cost_summary": self.get_cost_summary(),
        }

    async def close(self) -> None:
        for client in self._clients.values():
            await client.close()
