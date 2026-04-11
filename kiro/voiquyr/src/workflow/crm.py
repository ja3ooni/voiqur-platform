"""
CRM Integrations — Salesforce, HubSpot, MS Dynamics, SAP, Zoho, Pipedrive.
Implements Requirement 18.2.
"""

import logging
from typing import Any, Dict, List, Optional

import aiohttp


class CRMConnector:
    """Base async CRM connector."""

    def __init__(self, name: str, base_url: str, token: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(f"{__name__}.{name}")

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._auth_headers())
        return self._session

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    async def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        s = await self._get_session()
        async with s.get(f"{self.base_url}{path}", params=params, ssl=False) as r:
            return await r.json() if r.status == 200 else None

    async def _post(self, path: str, data: Dict) -> Any:
        s = await self._get_session()
        async with s.post(f"{self.base_url}{path}", json=data, ssl=False) as r:
            return await r.json() if r.status in (200, 201) else None

    async def _patch(self, path: str, data: Dict) -> Any:
        s = await self._get_session()
        async with s.patch(f"{self.base_url}{path}", json=data, ssl=False) as r:
            return await r.json() if r.status in (200, 204) else None

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # Override in subclasses
    async def get_contact(self, contact_id: str) -> Optional[Dict]:
        raise NotImplementedError

    async def create_contact(self, data: Dict) -> Optional[Dict]:
        raise NotImplementedError

    async def update_contact(self, contact_id: str, data: Dict) -> Optional[Dict]:
        raise NotImplementedError

    async def search_contacts(self, query: str) -> List[Dict]:
        raise NotImplementedError

    async def create_deal(self, data: Dict) -> Optional[Dict]:
        raise NotImplementedError

    async def health_check(self) -> bool:
        raise NotImplementedError


class SalesforceConnector(CRMConnector):
    """Salesforce REST API connector."""

    def __init__(self, instance_url: str, access_token: str):
        super().__init__("salesforce", f"{instance_url}/services/data/v59.0", access_token)

    async def get_contact(self, contact_id: str) -> Optional[Dict]:
        return await self._get(f"/sobjects/Contact/{contact_id}")

    async def create_contact(self, data: Dict) -> Optional[Dict]:
        return await self._post("/sobjects/Contact", data)

    async def update_contact(self, contact_id: str, data: Dict) -> Optional[Dict]:
        return await self._patch(f"/sobjects/Contact/{contact_id}", data)

    async def search_contacts(self, query: str) -> List[Dict]:
        result = await self._get("/query", {"q": f"SELECT Id,Name,Email FROM Contact WHERE Name LIKE '%{query}%'"})
        return result.get("records", []) if result else []

    async def create_deal(self, data: Dict) -> Optional[Dict]:
        return await self._post("/sobjects/Opportunity", data)

    async def health_check(self) -> bool:
        result = await self._get("/limits")
        return result is not None


class HubSpotConnector(CRMConnector):
    """HubSpot API v3 connector."""

    def __init__(self, access_token: str):
        super().__init__("hubspot", "https://api.hubapi.com", access_token)

    async def get_contact(self, contact_id: str) -> Optional[Dict]:
        return await self._get(f"/crm/v3/objects/contacts/{contact_id}")

    async def create_contact(self, data: Dict) -> Optional[Dict]:
        return await self._post("/crm/v3/objects/contacts", {"properties": data})

    async def update_contact(self, contact_id: str, data: Dict) -> Optional[Dict]:
        return await self._patch(f"/crm/v3/objects/contacts/{contact_id}", {"properties": data})

    async def search_contacts(self, query: str) -> List[Dict]:
        result = await self._post("/crm/v3/objects/contacts/search", {
            "filterGroups": [{"filters": [{"propertyName": "email", "operator": "CONTAINS_TOKEN", "value": query}]}]
        })
        return result.get("results", []) if result else []

    async def create_deal(self, data: Dict) -> Optional[Dict]:
        return await self._post("/crm/v3/objects/deals", {"properties": data})

    async def health_check(self) -> bool:
        result = await self._get("/crm/v3/objects/contacts", {"limit": 1})
        return result is not None


class MSDynamicsConnector(CRMConnector):
    """Microsoft Dynamics 365 Web API connector."""

    def __init__(self, org_url: str, access_token: str):
        super().__init__("dynamics", f"{org_url}/api/data/v9.2", access_token)

    async def get_contact(self, contact_id: str) -> Optional[Dict]:
        return await self._get(f"/contacts({contact_id})")

    async def create_contact(self, data: Dict) -> Optional[Dict]:
        return await self._post("/contacts", data)

    async def update_contact(self, contact_id: str, data: Dict) -> Optional[Dict]:
        return await self._patch(f"/contacts({contact_id})", data)

    async def search_contacts(self, query: str) -> List[Dict]:
        result = await self._get("/contacts", {"$filter": f"contains(fullname,'{query}')", "$top": "10"})
        return result.get("value", []) if result else []

    async def create_deal(self, data: Dict) -> Optional[Dict]:
        return await self._post("/opportunities", data)

    async def health_check(self) -> bool:
        result = await self._get("/contacts", {"$top": "1"})
        return result is not None


class SAPConnector(CRMConnector):
    """SAP OData connector (SAP S/4HANA Business Partner API)."""

    def __init__(self, base_url: str, username: str, password: str):
        super().__init__("sap", base_url, "")
        self._username = username
        self._password = password

    def _auth_headers(self) -> Dict[str, str]:
        import base64
        creds = base64.b64encode(f"{self._username}:{self._password}".encode()).decode()
        return {"Authorization": f"Basic {creds}", "Accept": "application/json"}

    async def get_contact(self, contact_id: str) -> Optional[Dict]:
        return await self._get(f"/API_BUSINESS_PARTNER/A_BusinessPartner('{contact_id}')")

    async def create_contact(self, data: Dict) -> Optional[Dict]:
        return await self._post("/API_BUSINESS_PARTNER/A_BusinessPartner", data)

    async def update_contact(self, contact_id: str, data: Dict) -> Optional[Dict]:
        return await self._patch(f"/API_BUSINESS_PARTNER/A_BusinessPartner('{contact_id}')", data)

    async def search_contacts(self, query: str) -> List[Dict]:
        result = await self._get("/API_BUSINESS_PARTNER/A_BusinessPartner",
                                  {"$filter": f"contains(BusinessPartnerFullName,'{query}')", "$top": "10"})
        return result.get("value", []) if result else []

    async def create_deal(self, data: Dict) -> Optional[Dict]:
        return await self._post("/API_SALES_ORDER_SRV/A_SalesOrder", data)

    async def health_check(self) -> bool:
        result = await self._get("/API_BUSINESS_PARTNER/A_BusinessPartner", {"$top": "1"})
        return result is not None


class ZohoConnector(CRMConnector):
    """Zoho CRM v3 connector."""

    def __init__(self, access_token: str, region: str = "com"):
        super().__init__("zoho", f"https://www.zohoapis.{region}/crm/v3", access_token)

    async def get_contact(self, contact_id: str) -> Optional[Dict]:
        result = await self._get(f"/Contacts/{contact_id}")
        return result.get("data", [None])[0] if result else None

    async def create_contact(self, data: Dict) -> Optional[Dict]:
        return await self._post("/Contacts", {"data": [data]})

    async def update_contact(self, contact_id: str, data: Dict) -> Optional[Dict]:
        return await self._patch(f"/Contacts/{contact_id}", {"data": [data]})

    async def search_contacts(self, query: str) -> List[Dict]:
        result = await self._get("/Contacts/search", {"criteria": f"(Email:contains:{query})"})
        return result.get("data", []) if result else []

    async def create_deal(self, data: Dict) -> Optional[Dict]:
        return await self._post("/Deals", {"data": [data]})

    async def health_check(self) -> bool:
        result = await self._get("/Contacts", {"per_page": "1"})
        return result is not None


class PipedriveConnector(CRMConnector):
    """Pipedrive REST API connector."""

    def __init__(self, api_token: str):
        super().__init__("pipedrive", "https://api.pipedrive.com/v1", api_token)

    def _auth_headers(self) -> Dict[str, str]:
        return {}  # Pipedrive uses api_token query param

    async def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        p = {"api_token": self.token, **(params or {})}
        s = await self._get_session()
        async with s.get(f"{self.base_url}{path}", params=p, ssl=False) as r:
            return await r.json() if r.status == 200 else None

    async def _post(self, path: str, data: Dict) -> Any:
        s = await self._get_session()
        async with s.post(f"{self.base_url}{path}", json=data,
                          params={"api_token": self.token}, ssl=False) as r:
            return await r.json() if r.status in (200, 201) else None

    async def get_contact(self, contact_id: str) -> Optional[Dict]:
        result = await self._get(f"/persons/{contact_id}")
        return result.get("data") if result else None

    async def create_contact(self, data: Dict) -> Optional[Dict]:
        return await self._post("/persons", data)

    async def update_contact(self, contact_id: str, data: Dict) -> Optional[Dict]:
        s = await self._get_session()
        async with s.put(f"{self.base_url}/persons/{contact_id}", json=data,
                         params={"api_token": self.token}, ssl=False) as r:
            return await r.json() if r.status == 200 else None

    async def search_contacts(self, query: str) -> List[Dict]:
        result = await self._get("/persons/search", {"term": query})
        return result.get("data", {}).get("items", []) if result else []

    async def create_deal(self, data: Dict) -> Optional[Dict]:
        return await self._post("/deals", data)

    async def health_check(self) -> bool:
        result = await self._get("/users/me")
        return result is not None


# Registry
CRM_CONNECTORS = {
    "salesforce": SalesforceConnector,
    "hubspot": HubSpotConnector,
    "dynamics": MSDynamicsConnector,
    "sap": SAPConnector,
    "zoho": ZohoConnector,
    "pipedrive": PipedriveConnector,
}
