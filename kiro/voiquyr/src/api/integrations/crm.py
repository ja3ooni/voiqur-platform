"""
CRM Integrations

Salesforce and SAP CRM integrations for customer data synchronization
and conversation context management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json
import base64
from urllib.parse import urlencode, quote

from .base import BaseIntegration, IntegrationConfig, IntegrationType, AuthenticationError, IntegrationError
from ..utils.webhook_publisher import get_global_publisher


class SalesforceConfig(IntegrationConfig):
    """Salesforce-specific configuration."""
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = IntegrationType.CRM
        self.provider = "salesforce"
    
    # Salesforce OAuth settings
    client_id: str = ""
    client_secret: str = ""
    username: str = ""
    password: str = ""
    security_token: str = ""
    
    # Instance settings
    instance_url: str = ""
    api_version: str = "v58.0"
    
    # EU compliance
    my_domain: Optional[str] = None  # Custom domain for EU instances
    sandbox: bool = False
    
    # Sync settings
    sync_contacts: bool = True
    sync_accounts: bool = True
    sync_opportunities: bool = True
    sync_cases: bool = True
    
    # Field mappings
    contact_field_mappings: Dict[str, str] = {
        "phone": "Phone",
        "email": "Email", 
        "first_name": "FirstName",
        "last_name": "LastName"
    }


class SAPConfig(IntegrationConfig):
    """SAP CRM-specific configuration."""
    
    def __init__(self, **data):
        super().__init__(**data)
        self.type = IntegrationType.CRM
        self.provider = "sap"
    
    # SAP connection settings
    server_url: str = ""
    client: str = "100"
    username: str = ""
    password: str = ""
    
    # SAP system settings
    system_id: str = ""
    language: str = "EN"
    
    # API settings
    api_type: str = "odata"  # odata, rest, soap
    service_path: str = "/sap/opu/odata/sap/"
    
    # EU compliance
    eu_datacenter: bool = True
    
    # Sync settings
    sync_business_partners: bool = True
    sync_contacts: bool = True
    sync_opportunities: bool = True
    sync_activities: bool = True


class CRMContact:
    """Generic CRM contact representation."""
    
    def __init__(self, contact_data: Dict[str, Any], source: str = "unknown"):
        self.id = contact_data.get("id")
        self.external_id = contact_data.get("external_id")
        self.first_name = contact_data.get("first_name")
        self.last_name = contact_data.get("last_name")
        self.email = contact_data.get("email")
        self.phone = contact_data.get("phone")
        self.mobile = contact_data.get("mobile")
        self.company = contact_data.get("company")
        self.title = contact_data.get("title")
        self.source = source
        self.created_date = contact_data.get("created_date")
        self.modified_date = contact_data.get("modified_date")
        self.custom_fields = contact_data.get("custom_fields", {})


class CRMAccount:
    """Generic CRM account representation."""
    
    def __init__(self, account_data: Dict[str, Any], source: str = "unknown"):
        self.id = account_data.get("id")
        self.external_id = account_data.get("external_id")
        self.name = account_data.get("name")
        self.type = account_data.get("type")
        self.industry = account_data.get("industry")
        self.phone = account_data.get("phone")
        self.website = account_data.get("website")
        self.billing_address = account_data.get("billing_address")
        self.source = source
        self.created_date = account_data.get("created_date")
        self.modified_date = account_data.get("modified_date")
        self.custom_fields = account_data.get("custom_fields", {})


class SalesforceIntegration(BaseIntegration):
    """
    Salesforce CRM integration.
    
    Provides customer data synchronization, lead management,
    and conversation context enrichment.
    """
    
    def __init__(self, config: SalesforceConfig):
        """
        Initialize Salesforce integration.
        
        Args:
            config: Salesforce configuration
        """
        super().__init__(config)
        self.config: SalesforceConfig = config
        
        # Determine instance URL
        if config.instance_url:
            self.instance_url = config.instance_url
        elif config.my_domain:
            self.instance_url = f"https://{config.my_domain}.my.salesforce.com"
        elif config.sandbox:
            self.instance_url = "https://test.salesforce.com"
        else:
            self.instance_url = "https://login.salesforce.com"
        
        # API endpoints
        self.auth_url = f"{self.instance_url}/services/oauth2/token"
        self.api_base = f"{self.instance_url}/services/data/v{config.api_version}"
        
        # Authentication
        self.access_token = None
        self.token_expires_at = None
        
        # Webhook publisher
        self.webhook_publisher = get_global_publisher()
    
    async def initialize(self) -> bool:
        """Initialize Salesforce integration."""
        try:
            self.logger.info("Initializing Salesforce integration")
            
            # Validate configuration
            if not self.config.client_id:
                raise ConfigurationError("Salesforce Client ID is required")
            
            if not self.config.client_secret:
                raise ConfigurationError("Salesforce Client Secret is required")
            
            if not self.config.username:
                raise ConfigurationError("Salesforce Username is required")
            
            if not self.config.password:
                raise ConfigurationError("Salesforce Password is required")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Salesforce integration: {e}")
            return False
    
    async def authenticate(self) -> bool:
        """Authenticate with Salesforce using OAuth2 Username-Password flow."""
        try:
            # Prepare authentication data
            auth_data = {
                "grant_type": "password",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "username": self.config.username,
                "password": f"{self.config.password}{self.config.security_token}"
            }
            
            # Make authentication request
            response = await self._make_request(
                "POST",
                self.auth_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=urlencode(auth_data)
            )
            
            if response["success"]:
                auth_result = response["data"]
                self.access_token = auth_result["access_token"]
                self.instance_url = auth_result["instance_url"]
                self.api_base = f"{self.instance_url}/services/data/v{self.config.api_version}"
                
                # Calculate token expiration (Salesforce tokens typically last 2 hours)
                self.token_expires_at = datetime.utcnow() + timedelta(hours=2)
                
                self.logger.info("Successfully authenticated with Salesforce")
                self._authenticated = True
                return True
            else:
                raise AuthenticationError("Failed to authenticate with Salesforce")
                
        except Exception as e:
            self.logger.error(f"Salesforce authentication failed: {e}")
            self._authenticated = False
            return False
    
    async def health_check(self) -> bool:
        """Perform health check on Salesforce integration."""
        try:
            # Check if token is still valid
            if not self.access_token or (self.token_expires_at and datetime.utcnow() >= self.token_expires_at):
                return await self.authenticate()
            
            # Test API access with a simple query
            response = await self._make_request(
                "GET",
                f"{self.api_base}/sobjects/",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response["success"]:
                self._last_health_check = datetime.utcnow()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Salesforce health check failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from Salesforce."""
        try:
            # Revoke access token
            if self.access_token:
                await self._make_request(
                    "POST",
                    f"{self.instance_url}/services/oauth2/revoke",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data=urlencode({"token": self.access_token})
                )
            
            self.access_token = None
            self.token_expires_at = None
            self._authenticated = False
            
        except Exception as e:
            self.logger.error(f"Error during Salesforce disconnect: {e}")
    
    # Contact Management
    
    async def search_contacts(self, 
                            phone: Optional[str] = None,
                            email: Optional[str] = None,
                            name: Optional[str] = None,
                            limit: int = 10) -> List[CRMContact]:
        """
        Search for contacts in Salesforce.
        
        Args:
            phone: Phone number to search
            email: Email address to search
            name: Name to search
            limit: Maximum results to return
            
        Returns:
            List of CRM contacts
        """
        try:
            # Build SOQL query
            fields = ["Id", "FirstName", "LastName", "Email", "Phone", "MobilePhone", "Account.Name", "Title", "CreatedDate", "LastModifiedDate"]
            query = f"SELECT {','.join(fields)} FROM Contact"
            
            conditions = []
            if phone:
                conditions.append(f"(Phone = '{phone}' OR MobilePhone = '{phone}')")
            if email:
                conditions.append(f"Email = '{email}'")
            if name:
                conditions.append(f"(FirstName LIKE '%{name}%' OR LastName LIKE '%{name}%')")
            
            if conditions:
                query += f" WHERE {' OR '.join(conditions)}"
            
            query += f" LIMIT {limit}"
            
            # Execute query
            response = await self._make_request(
                "GET",
                f"{self.api_base}/query/?q={quote(query)}",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response["success"]:
                contacts = []
                for record in response["data"]["records"]:
                    contact_data = {
                        "id": record["Id"],
                        "external_id": record["Id"],
                        "first_name": record.get("FirstName"),
                        "last_name": record.get("LastName"),
                        "email": record.get("Email"),
                        "phone": record.get("Phone"),
                        "mobile": record.get("MobilePhone"),
                        "company": record.get("Account", {}).get("Name") if record.get("Account") else None,
                        "title": record.get("Title"),
                        "created_date": record.get("CreatedDate"),
                        "modified_date": record.get("LastModifiedDate")
                    }
                    contacts.append(CRMContact(contact_data, "salesforce"))
                
                return contacts
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to search Salesforce contacts: {e}")
            return []
    
    async def create_contact(self, contact_data: Dict[str, Any]) -> Optional[CRMContact]:
        """
        Create a new contact in Salesforce.
        
        Args:
            contact_data: Contact information
            
        Returns:
            Created CRM contact or None if failed
        """
        try:
            # Map fields using configuration
            sf_data = {}
            for local_field, sf_field in self.config.contact_field_mappings.items():
                if local_field in contact_data:
                    sf_data[sf_field] = contact_data[local_field]
            
            # Add any additional fields
            for key, value in contact_data.items():
                if key not in self.config.contact_field_mappings and key not in sf_data:
                    sf_data[key] = value
            
            # Create contact
            response = await self._make_request(
                "POST",
                f"{self.api_base}/sobjects/Contact/",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                json=sf_data
            )
            
            if response["success"]:
                contact_id = response["data"]["id"]
                
                # Fetch the created contact
                contacts = await self.search_contacts()
                for contact in contacts:
                    if contact.id == contact_id:
                        # Emit contact created event
                        if self.webhook_publisher:
                            await self.webhook_publisher.publish_custom_event(
                                event_type="crm.contact.created",
                                data={
                                    "contact_id": contact_id,
                                    "source": "salesforce",
                                    "contact_data": contact_data
                                },
                                source="salesforce_integration"
                            )
                        
                        return contact
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create Salesforce contact: {e}")
            return None
    
    async def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a contact in Salesforce.
        
        Args:
            contact_id: Salesforce contact ID
            updates: Fields to update
            
        Returns:
            True if updated successfully
        """
        try:
            # Map fields using configuration
            sf_updates = {}
            for local_field, sf_field in self.config.contact_field_mappings.items():
                if local_field in updates:
                    sf_updates[sf_field] = updates[local_field]
            
            # Update contact
            response = await self._make_request(
                "PATCH",
                f"{self.api_base}/sobjects/Contact/{contact_id}",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                json=sf_updates
            )
            
            if response["success"]:
                # Emit contact updated event
                if self.webhook_publisher:
                    await self.webhook_publisher.publish_custom_event(
                        event_type="crm.contact.updated",
                        data={
                            "contact_id": contact_id,
                            "source": "salesforce",
                            "updates": updates
                        },
                        source="salesforce_integration"
                    )
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to update Salesforce contact {contact_id}: {e}")
            return False
    
    # Activity Logging
    
    async def log_conversation(self, 
                             contact_id: str,
                             conversation_data: Dict[str, Any]) -> bool:
        """
        Log conversation as an activity in Salesforce.
        
        Args:
            contact_id: Salesforce contact ID
            conversation_data: Conversation details
            
        Returns:
            True if logged successfully
        """
        try:
            # Create task/activity record
            activity_data = {
                "WhoId": contact_id,
                "Subject": f"Voice Conversation - {conversation_data.get('type', 'Call')}",
                "Description": conversation_data.get('summary', 'Voice conversation via EUVoice AI'),
                "Status": "Completed",
                "Priority": "Normal",
                "ActivityDate": datetime.utcnow().date().isoformat(),
                "Type": "Call"
            }
            
            # Add conversation metadata
            if conversation_data.get('duration'):
                activity_data["Description"] += f"\nDuration: {conversation_data['duration']} seconds"
            
            if conversation_data.get('transcript'):
                activity_data["Description"] += f"\nTranscript: {conversation_data['transcript'][:1000]}"
            
            # Create activity
            response = await self._make_request(
                "POST",
                f"{self.api_base}/sobjects/Task/",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                json=activity_data
            )
            
            if response["success"]:
                self.logger.info(f"Logged conversation for contact {contact_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to log conversation for contact {contact_id}: {e}")
            return False


class SAPIntegration(BaseIntegration):
    """
    SAP CRM integration.
    
    Provides integration with SAP CRM systems for customer data
    and business process management.
    """
    
    def __init__(self, config: SAPConfig):
        """
        Initialize SAP integration.
        
        Args:
            config: SAP configuration
        """
        super().__init__(config)
        self.config: SAPConfig = config
        
        # Build API URLs
        self.base_url = config.server_url.rstrip('/')
        if config.api_type == "odata":
            self.api_url = f"{self.base_url}{config.service_path}"
        else:
            self.api_url = f"{self.base_url}/api"
        
        # Authentication
        self.session_id = None
        self.csrf_token = None
        
        # Webhook publisher
        self.webhook_publisher = get_global_publisher()
    
    async def initialize(self) -> bool:
        """Initialize SAP integration."""
        try:
            self.logger.info("Initializing SAP integration")
            
            # Validate configuration
            if not self.config.server_url:
                raise ConfigurationError("SAP Server URL is required")
            
            if not self.config.username:
                raise ConfigurationError("SAP Username is required")
            
            if not self.config.password:
                raise ConfigurationError("SAP Password is required")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SAP integration: {e}")
            return False
    
    async def authenticate(self) -> bool:
        """Authenticate with SAP system."""
        try:
            # Create basic auth header
            credentials = f"{self.config.username}:{self.config.password}"
            auth_header = base64.b64encode(credentials.encode()).decode()
            
            # Test authentication with a simple request
            response = await self._make_request(
                "GET",
                f"{self.api_url}/$metadata",
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Accept": "application/json"
                }
            )
            
            if response["success"]:
                self.logger.info("Successfully authenticated with SAP")
                self._authenticated = True
                return True
            else:
                raise AuthenticationError("Failed to authenticate with SAP")
                
        except Exception as e:
            self.logger.error(f"SAP authentication failed: {e}")
            self._authenticated = False
            return False
    
    async def health_check(self) -> bool:
        """Perform health check on SAP integration."""
        try:
            # Test with a simple metadata request
            credentials = f"{self.config.username}:{self.config.password}"
            auth_header = base64.b64encode(credentials.encode()).decode()
            
            response = await self._make_request(
                "GET",
                f"{self.api_url}/$metadata",
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Accept": "application/json"
                }
            )
            
            if response["success"]:
                self._last_health_check = datetime.utcnow()
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"SAP health check failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from SAP system."""
        try:
            # SAP doesn't require explicit logout for basic auth
            self.session_id = None
            self.csrf_token = None
            self._authenticated = False
            
        except Exception as e:
            self.logger.error(f"Error during SAP disconnect: {e}")
    
    # Business Partner Management
    
    async def search_business_partners(self, 
                                     search_term: str,
                                     partner_type: str = "Person",
                                     limit: int = 10) -> List[CRMContact]:
        """
        Search for business partners in SAP.
        
        Args:
            search_term: Search term (name, phone, email)
            partner_type: Type of partner (Person, Organization)
            limit: Maximum results to return
            
        Returns:
            List of CRM contacts
        """
        try:
            credentials = f"{self.config.username}:{self.config.password}"
            auth_header = base64.b64encode(credentials.encode()).decode()
            
            # Build OData query
            filter_conditions = []
            if search_term:
                filter_conditions.append(f"substringof('{search_term}', BusinessPartnerName)")
            if partner_type:
                filter_conditions.append(f"BusinessPartnerCategory eq '{partner_type}'")
            
            query_params = {
                "$format": "json",
                "$top": str(limit)
            }
            
            if filter_conditions:
                query_params["$filter"] = " and ".join(filter_conditions)
            
            query_string = urlencode(query_params)
            
            # Execute query
            response = await self._make_request(
                "GET",
                f"{self.api_url}/A_BusinessPartner?{query_string}",
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Accept": "application/json"
                }
            )
            
            if response["success"]:
                contacts = []
                results = response["data"].get("d", {}).get("results", [])
                
                for record in results:
                    contact_data = {
                        "id": record.get("BusinessPartner"),
                        "external_id": record.get("BusinessPartner"),
                        "first_name": record.get("FirstName"),
                        "last_name": record.get("LastName"),
                        "email": record.get("EmailAddress"),
                        "phone": record.get("PhoneNumber"),
                        "company": record.get("OrganizationBPName1"),
                        "created_date": record.get("CreationDate"),
                        "modified_date": record.get("LastChangeDate")
                    }
                    contacts.append(CRMContact(contact_data, "sap"))
                
                return contacts
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to search SAP business partners: {e}")
            return []
    
    async def create_business_partner(self, partner_data: Dict[str, Any]) -> Optional[CRMContact]:
        """
        Create a new business partner in SAP.
        
        Args:
            partner_data: Partner information
            
        Returns:
            Created CRM contact or None if failed
        """
        try:
            credentials = f"{self.config.username}:{self.config.password}"
            auth_header = base64.b64encode(credentials.encode()).decode()
            
            # Prepare SAP business partner data
            sap_data = {
                "BusinessPartnerCategory": "1",  # Person
                "FirstName": partner_data.get("first_name", ""),
                "LastName": partner_data.get("last_name", ""),
                "BusinessPartnerName": f"{partner_data.get('first_name', '')} {partner_data.get('last_name', '')}".strip()
            }
            
            # Create business partner
            response = await self._make_request(
                "POST",
                f"{self.api_url}/A_BusinessPartner",
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json=sap_data
            )
            
            if response["success"]:
                partner_id = response["data"]["d"]["BusinessPartner"]
                
                # Emit business partner created event
                if self.webhook_publisher:
                    await self.webhook_publisher.publish_custom_event(
                        event_type="crm.contact.created",
                        data={
                            "contact_id": partner_id,
                            "source": "sap",
                            "contact_data": partner_data
                        },
                        source="sap_integration"
                    )
                
                # Return created contact
                contact_data = {
                    "id": partner_id,
                    "external_id": partner_id,
                    "first_name": partner_data.get("first_name"),
                    "last_name": partner_data.get("last_name"),
                    "email": partner_data.get("email"),
                    "phone": partner_data.get("phone")
                }
                
                return CRMContact(contact_data, "sap")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create SAP business partner: {e}")
            return None
    
    # Activity Management
    
    async def log_interaction(self, 
                            partner_id: str,
                            interaction_data: Dict[str, Any]) -> bool:
        """
        Log interaction/activity in SAP.
        
        Args:
            partner_id: SAP business partner ID
            interaction_data: Interaction details
            
        Returns:
            True if logged successfully
        """
        try:
            credentials = f"{self.config.username}:{self.config.password}"
            auth_header = base64.b64encode(credentials.encode()).decode()
            
            # Create interaction record
            activity_data = {
                "BusinessPartner": partner_id,
                "InteractionType": "CALL",
                "Subject": f"Voice Conversation - {interaction_data.get('type', 'Call')}",
                "Description": interaction_data.get('summary', 'Voice conversation via EUVoice AI'),
                "InteractionDate": datetime.utcnow().isoformat(),
                "Status": "COMPLETED"
            }
            
            # Create activity (this would depend on specific SAP CRM setup)
            response = await self._make_request(
                "POST",
                f"{self.api_url}/A_Interaction",
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json=activity_data
            )
            
            if response["success"]:
                self.logger.info(f"Logged interaction for business partner {partner_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to log SAP interaction for partner {partner_id}: {e}")
            return False