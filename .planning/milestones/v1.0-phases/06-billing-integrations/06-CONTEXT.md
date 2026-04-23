# Phase 6: Billing & Integrations - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Stripe handles real payments, Salesforce CRM syncs contacts, and WhatsApp/Slack/Telegram messaging works end-to-end.

</domain>

<decisions>
## Implementation Decisions

### Stripe (Billing)
- **D-01:** Real Stripe SDK as primary for production payments
- **D-02:** Keep mock fallback for development/testing environments
- **D-03:** Environment-based routing: mock in dev, real Stripe in production
- **D-04:** Webhook signature verification enabled for production
- **D-05:** Stripe test mode available for CI/testing

### Salesforce (CRM)
- **D-06:** OAuth2 Username-Password flow as primary (already in code)
- **D-07:** OAuth2 Authorize Code flow as secondary option
- **D-08:** Both OAuth flows available — agent can determine based on use case
- **D-09:** Contact and case creation via REST API

### Messaging
- **D-10:** WhatsApp via Twilio Conversations API
- **D-11:** Slack via Bolt SDK
- **D-12:** Telegram via python-telegram-bot
- **D-13:** All three messaging platforms implemented

### Agent's Discretion
- Specific webhook endpoint paths — agent can design RESTful routes
- Error handling retry strategies — agent can implement per provider
- Rate limiting approach — agent can determine based on provider limits

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code
- `kiro/voiquyr/src/billing/stripe_service.py` — Stripe service (has mock fallback)
- `kiro/voiquyr/src/api/integrations/crm.py` — Salesforce integration (OAuth flows)
- `kiro/voiquyr/src/api/integrations/messaging.py` — WhatsApp, Slack, Telegram
- `kiro/voiquyr/src/channels/messaging.py` — Channel messaging layer
- `kiro/voiquyr/src/workflow/crm.py` — SalesforceConnector class

### Requirements
- `REQUIREMENTS.md` — BILL-01, BILL-02, CRM-01, CRM-02, MSG-01, MSG-02, MSG-03

</canonical_refs>

 </code_context>
## Existing Code Insights

### Reusable Assets
- `StripeService` class in `stripe_service.py` with mock fallback pattern
- `SalesforceIntegration` class with OAuth2 Username-Password flow
- `WhatsAppIntegration`, `SlackIntegration`, `TelegramIntegration` in messaging.py
- `MessagingMessage` data class for standardized message format

### Established Patterns
- Environment-based config (dev vs production)
- Async provider methods across all integrations
- `IntegrationConfig` base class for credentials

### Integration Points
- Billing hooks into billing_service.py for charges
- CRM hooks into workflow/crm.py for contact sync
- Messaging hooks into channels/messaging.py for delivery

</code_context>

<specifics>
## Specific Ideas

User wants environment-based routing: mock in dev, real Stripe in production. Both OAuth flows for Salesforce available.

</specifics>

<deferred>
## Deferred Ideas

- HubSpot CRM — mentioned but not in scope
- Microsoft Dynamics — mentioned but not in scope

</deferred>

---

*Phase: 06-billing-integrations*
*Context gathered: 2026-04-19*