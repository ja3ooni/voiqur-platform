# Phase 14: Multi-Region Deployment — Research

**Researched:** 2026-06-03
**Researcher:** gsd-phase-researcher

---

## Summary

The existing Helm chart has everything needed: `global.region`, `global.dataResidency`, node affinity pinned to `topology.kubernetes.io/region`, compliance env vars injected by `_helpers.tpl`, and `global.storageClass` already parameterised. Kustomize overlays over a Helm-rendered base are the right approach — one `kustomization.yaml` per region that patches values, annotations, and adds ExternalDNS configuration without forking the chart. The ExternalDNS annotation format for Cloudflare (most likely provider for UAE/EU dual-region) is `external-dns.alpha.kubernetes.io/hostname` on the Ingress resource, which the existing ingress template already supports via the `annotations` values key.

---

## 1. Kustomize Overlay Structure

### Recommended layout

The existing `kiro/voiquyr/k8s/` tree is grouped by concern (`helm/`, `security/`, `monitoring/`, etc.). Overlays should live inside a new `k8s/overlays/` directory, with one sub-directory per region. The Helm chart is the `base`; overlays patch its rendered output.

```
kiro/voiquyr/k8s/
├── helm/euvoice-platform/          # unchanged base chart
├── overlays/
│   ├── base/                       # helm template renders + shared kustomization
│   │   └── kustomization.yaml      # helmCharts source or pre-rendered manifests
│   ├── frankfurt/
│   │   ├── kustomization.yaml      # patches + resources for EU/Frankfurt
│   │   ├── values-frankfurt.yaml   # Helm values override (region, storageClass, hosts)
│   │   ├── ingress-patch.yaml      # ExternalDNS annotations, EU TLS hosts
│   │   ├── namespace-patch.yaml    # compliance labels: gdpr=true, ai-act=true
│   │   ├── network-policy-egress-restriction.yaml  # block non-EU egress CIDRs
│   │   └── externaldns-deployment.yaml             # ExternalDNS for EU provider
│   └── uae/
│       ├── kustomization.yaml
│       ├── values-uae.yaml         # region, storageClass, hosts for UAE
│       ├── ingress-patch.yaml      # ExternalDNS annotations, UAE TLS hosts
│       ├── namespace-patch.yaml    # compliance labels: uae-pdpl=true
│       ├── network-policy-egress-restriction.yaml  # block non-UAE egress CIDRs
│       └── externaldns-deployment.yaml             # ExternalDNS for UAE provider
├── security/                       # existing files, unchanged
├── istio/                          # existing files, unchanged
└── monitoring/                     # existing files, unchanged
```

### How Kustomize references the Helm chart

Use Kustomize's `helmCharts` generator (kustomize v4.1+) in the `base/kustomization.yaml`:

```yaml
# k8s/overlays/base/kustomization.yaml
helmCharts:
  - name: euvoice-platform
    releaseName: euvoice
    namespace: voiquyr
    version: 0.1.0
    repo: oci://local-registry/charts   # or local path
    valuesFile: ../../helm/euvoice-platform/values.yaml
```

Each region overlay extends base and adds JSON/strategic-merge patches:

```yaml
# k8s/overlays/frankfurt/kustomization.yaml
resources:
  - ../base
patches:
  - path: ingress-patch.yaml
    target:
      kind: Ingress
      name: euvoice-platform-euvoice
  - path: namespace-patch.yaml
    target:
      kind: Namespace
      name: voiquyr
helmCharts:
  - name: euvoice-platform
    releaseName: euvoice
    namespace: voiquyr
    valuesFile: values-frankfurt.yaml
```

**Key constraint (D-14):** Never duplicate the chart tree. All region differences are expressed as Kustomize patches or Helm values files.

---

## 2. ExternalDNS Geo-Routing

### Provider selection

The existing ingress is AWS NLB (annotations in `k8s/load-balancing/nginx-ingress.yaml`), and the encryption config references `eu-central-1` KMS keys — strong signal that Frankfurt runs on AWS. UAE likely runs on AWS `me-central-1` (UAE region, launched 2022) or possibly Azure UAE North for sovereign cloud requirements.

**Recommended: Route53 with latency/geolocation routing for both regions.** This is the simplest operational choice given the AWS-first signals in the codebase.

Fallback: Cloudflare with `cloudflare-proxied: "false"` is valid if a single DNS provider is needed across clouds.

### ExternalDNS annotation format (provider-neutral)

ExternalDNS reads the following annotations from `Ingress` or `Service` objects:

```yaml
annotations:
  # Primary: hostname(s) to register in DNS
  external-dns.alpha.kubernetes.io/hostname: "api.voiquyr.eu"

  # For Route53 geolocation policy (residency-first)
  external-dns.alpha.kubernetes.io/aws-geolocation-country-code: "DE"  # Frankfurt → EU
  # or for UAE:
  external-dns.alpha.kubernetes.io/aws-geolocation-country-code: "AE"  # UAE cluster

  # TTL
  external-dns.alpha.kubernetes.io/ttl: "60"

  # For weighted routing (used alongside geolocation for health-based failover)
  external-dns.alpha.kubernetes.io/aws-weight: "100"

  # Set identifier to distinguish records from two regions
  external-dns.alpha.kubernetes.io/aws-set-identifier: "frankfurt"   # or "uae"
```

**Residency-first behaviour with Route53 geolocation:** Route53 geolocation routing sends traffic by source IP country. EU countries route to Frankfurt; GCC/ME countries route to UAE. A `*` default record can point to Frankfurt as the legal fallback — but given D-02, the default record should return a 403 or route to neither if no match, not silently failover cross-region. Implement this with a weighted record (weight=0) for the default or omit the default entirely.

### ExternalDNS deployment (per region)

Each region runs its own ExternalDNS controller scoped to its cluster and DNS zone:

```yaml
# k8s/overlays/frankfurt/externaldns-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: external-dns
  namespace: external-dns
spec:
  template:
    spec:
      containers:
      - name: external-dns
        image: registry.k8s.io/external-dns/external-dns:v0.14.2
        args:
        - --source=ingress
        - --source=service
        - --domain-filter=voiquyr.eu      # Frankfurt scoped to .eu zone
        - --provider=aws
        - --aws-zone-type=public
        - --registry=txt
        - --txt-owner-id=voiquyr-frankfurt
        - --txt-prefix=frankfurt-
        - --policy=sync                    # Reconcile deletions
        - --aws-region=eu-central-1
```

For UAE:
```yaml
        args:
        - --domain-filter=voiquyr.ae       # UAE scoped to .ae zone
        - --provider=aws
        - --aws-zone-type=public
        - --txt-owner-id=voiquyr-uae
        - --txt-prefix=uae-
        - --aws-region=me-central-1
```

**Isolation guarantee:** `--txt-owner-id` and `--txt-prefix` are different per region, so each ExternalDNS instance only manages and deletes its own TXT ownership records. Frankfurt cannot accidentally delete UAE DNS records.

---

## 3. Sovereign Region Components — What to Patch per Region

The existing `_helpers.tpl` injects `REGION`, `DATA_RESIDENCY`, `EU_COMPLIANCE_MODE`, `AI_ACT_COMPLIANCE` into every pod via `euvoice-platform.complianceEnv`. Node affinity is already pinned to `topology.kubernetes.io/region = .Values.global.region` with a required `compliance.euvoice.ai/eu-node: "true"` label.

| Resource | Frankfurt value | UAE value | Mechanism |
|---|---|---|---|
| `global.region` | `eu-central-1` | `me-central-1` | `values-<region>.yaml` |
| `global.dataResidency` | `eu` | `uae` | `values-<region>.yaml` |
| `global.gdprCompliance` | `true` | `false` (UAE PDPL applies) | `values-<region>.yaml` |
| `global.aiActCompliance` | `true` | `false` | `values-<region>.yaml` |
| `global.storageClass` | `gp3-encrypted` (AWS) | `gp3-encrypted-uae` or Azure equivalent | `values-<region>.yaml` |
| `ingress.hosts[*].host` | `api.voiquyr.eu`, `app.voiquyr.eu` | `api.voiquyr.ae`, `app.voiquyr.ae` | `values-<region>.yaml` |
| `ingress.annotations` | ExternalDNS EU + Route53 geo `DE` | ExternalDNS UAE + Route53 geo `AE` | `ingress-patch.yaml` |
| `ingress.tls[*].secretName` | `voiquyr-tls-eu` | `voiquyr-tls-uae` | `values-<region>.yaml` |
| `namespace.labels` | `compliance: gdpr`, `region: eu` | `compliance: uae-pdpl`, `region: uae` | `namespace-patch.yaml` |
| `namespace.annotations` | `compliance.euvoice.ai/gdpr: enabled` | `compliance.euvoice.ai/uae-pdpl: enabled` | `namespace-patch.yaml` |
| Node affinity `eu-node: "true"` label | `eu-node: "true"` | `uae-node: "true"` (rename label key) | `ingress-patch.yaml` on Deployment |
| GDPR cleanup CronJob S3 bucket | `euvoice-data-eu-central-1` | `euvoice-data-me-central-1` | patch on CronJob |
| Vault/KMS KMS key ARN | `arn:aws:kms:eu-central-1:...` | `arn:aws:kms:me-central-1:...` | `values-<region>.yaml` or secrets patch |
| Prometheus retention | `30d` | `30d` | shared default (keep) |
| Alertmanager Slack channel | `#voiquyr-alerts-eu` | `#voiquyr-alerts-uae` | `values-<region>.yaml` |
| cert-manager ClusterIssuer | `letsencrypt-prod` (Let's Encrypt) | `letsencrypt-prod` or regional CA | `values-<region>.yaml` |
| ExternalDNS `--domain-filter` | `voiquyr.eu` | `voiquyr.ae` | overlay Deployment |
| `security.auditLogging.retention` | `7y` (GDPR) | `7y` (UAE PDPL) | keep shared default |

**Node label convention:** Frankfurt nodes carry `compliance.euvoice.ai/eu-node: "true"`. UAE nodes should carry `compliance.euvoice.ai/uae-node: "true"`. The `_helpers.tpl` affinity block hard-codes `eu-node` — this must be made a values key or patched per region:

```yaml
# values-uae.yaml
affinity:
  nodeAffinityLabelKey: compliance.euvoice.ai/uae-node
  region: me-central-1
```

Or patch the Deployment `spec.template.spec.affinity` directly via a JSON patch in the Kustomize overlay.

---

## 4. Data Residency Enforcement (K8s-Native)

### What already exists

- **NetworkPolicies** in `k8s/security/network-policies.yaml`: default deny-all, per-component egress rules. Currently allow HTTPS (port 443) to all destinations (`to: []`). This must be tightened per-region.
- **Node affinity** in `_helpers.tpl`: `requiredDuringSchedulingIgnoredDuringExecution` on `topology.kubernetes.io/region`. Hard guarantee that pods never schedule outside the region.
- **Compliance env vars** injected into every container via `euvoice-platform.complianceEnv`.
- **RBAC**: per-component least-privilege roles in `k8s/security/rbac.yaml`.
- **Istio mTLS** `STRICT` mode in `k8s/istio/security-policies.yaml`: all pod-to-pod traffic is mutually authenticated.

### What needs to be added

**1. Egress CIDR restriction (NetworkPolicy)**

The existing STT/LLM/TTS NetworkPolicies allow `port 443` egress to all destinations. For sovereignty, the `to: []` rule must be replaced with CIDR blocks limited to the cloud provider's regional IPs:

```yaml
# network-policy-egress-restriction.yaml (Frankfurt overlay)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: euvoice-restrict-cross-region-egress
  namespace: voiquyr
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 10.0.0.0/8        # Cluster-internal
  - to:
    - ipBlock:
        cidr: 52.28.0.0/14      # AWS eu-central-1 range (example)
    ports:
    - port: 443
      protocol: TCP
  # Explicitly DENY other public CIDRs
```

AWS publishes its IP ranges at `https://ip-ranges.amazonaws.com/ip-ranges.json`. For Frankfurt, only `eu-central-1` IPs; for UAE, only `me-central-1` IPs.

**2. OPA/Gatekeeper constraint (admission-time)**

Add a `ConstraintTemplate` + `Constraint` that rejects any Pod without the correct `DATA_RESIDENCY` env var and node affinity label for the region. This enforces at admission time (not just runtime):

```yaml
# gatekeeper-data-residency-constraint.yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: VoiquyrDataResidency
metadata:
  name: require-region-affinity
spec:
  match:
    kinds:
    - apiGroups: ["apps"]
      kinds: ["Deployment"]
    namespaces: ["voiquyr"]
  parameters:
    requiredRegion: "eu-central-1"     # varies per overlay
    requiredDataResidency: "eu"
```

**3. StorageClass pinning**

The existing StorageClass `gp3-encrypted` uses `ebs.csi.aws.com` provisioner with `eu-central-1` KMS key. UAE needs a parallel StorageClass with the UAE KMS key. The chart already uses `global.storageClass` as a values key — patch this per overlay.

**4. Namespace-level Pod Security Admission**

Add `pod-security.kubernetes.io/enforce: restricted` label to the namespace in each overlay's `namespace-patch.yaml`. This is already enforced at the pod level via `_helpers.tpl` security contexts but namespace-level enforcement adds a belt-and-suspenders admission gate.

**Summary matrix:**

| Mechanism | What it prevents | Already present | Needs overlay |
|---|---|---|---|
| Node affinity (required) | Pod scheduled outside region | Yes (eu only) | UAE variant needed |
| NetworkPolicy egress CIDR | Data exfiltration via direct IP | Partial (port only) | CIDR scope needed per region |
| OPA/Gatekeeper constraint | Misconfigured deployments admitted | No | New for both regions |
| StorageClass KMS key | Data at rest in wrong region | Yes (eu-central-1) | UAE KMS key variant |
| Istio mTLS STRICT | Unencrypted lateral movement | Yes | Keep as-is |
| Namespace PSA enforce | Privilege escalation | No (only pod-level) | Add to namespace labels |

---

## 5. Cross-Region Control-Plane Sync Pattern

### What may cross sovereignty boundaries

Per D-08/D-09, only:
- Region health status (up/down, p95 latency)
- Deployment version/state (what image is running)
- Aggregate metrics (non-PII: request counts, error rates)
- Routing/policy configuration (which jurisdictions each region serves)

### Recommended pattern: Pull-based aggregation via Prometheus federation

Prometheus federation is already in the stack. A lightweight "global view" Prometheus (running in a neutral management plane) scrapes only aggregate metrics from regional Prometheus endpoints:

```yaml
# global-prometheus scrape config (management plane only)
scrape_configs:
  - job_name: 'frankfurt-federation'
    honor_labels: true
    metrics_path: '/federate'
    params:
      match[]:
        - '{job=~"voiquyr.*"}'                    # aggregate metrics only
        - 'voiquyr_call_latency_ms_bucket'
        - 'voiquyr_flash_mode_hit_rate'
        # NO: audio content, user IDs, session tokens
    static_configs:
      - targets: ['prometheus.voiquyr-frankfurt.svc:9090']
  - job_name: 'uae-federation'
    static_configs:
      - targets: ['prometheus.voiquyr-uae.svc:9090']
```

**Why pull (not push):** Each region's Prometheus is the authority. The global Prometheus requests only what it needs. No region agent pushes data it shouldn't. If the global plane is compromised, it cannot write into regional state.

### Health/routing metadata

The `EdgeOrchestrator` (`src/core/edge_orchestrator.py`) already maintains per-region `RegionalEndpoint` objects with `available`, `latency_ms`, and `load`. The `update_endpoint_status` method is the integration point. 

Pattern: Each region exposes a `/admin/v1/region/status` endpoint (JSON) reporting aggregate health only. The global control plane polls this endpoint via mTLS, checks that `available`, `latency_ms`, and `load` are within SLA, and updates routing policy. No user-content fields are included.

### Config sync (routing policy)

Routing rules (which countries allowed per jurisdiction) are currently hardcoded in `EdgeOrchestrator._initialize_default_rules`. For runtime admin override (D-15/D-17), these should be loaded from a ConfigMap or API, not hardcoded. The config object travels control-plane only — it contains country codes and jurisdiction mappings, never PII.

**Cross-region rule distribution:** A push from the global admin API to each region's admin endpoint using mTLS client certificates. Regions validate the config against their local sovereignty guardrails before applying.

---

## 6. Admin Runtime Policy API

### Current APIConfig shape (from `src/api/config.py`)

```python
class APIConfig(BaseModel):
    eu_data_residency: bool = True
    gdpr_mode: bool = True
    environment: str
    vllm_enabled: bool
    # ... (no region-aware routing policy fields yet)
```

### Fields to add

```python
class RegionPolicy(BaseModel):
    """Per-region routing and residency enforcement policy."""
    region_id: str                          # "frankfurt" | "uae"
    jurisdiction: str                       # "eu" | "uae" | "me"
    allowed_source_countries: list[str]     # ["DE", "FR", ...] or ["AE", "SA", ...]
    deny_cross_region_audio: bool = True    # hard guardrail, must stay True
    deny_cross_region_transcripts: bool = True
    max_metadata_retention_days: int = 30
    compliance_framework: str              # "gdpr" | "uae-pdpl" | "india-dpdp"
    erasure_sla_days: int                  # 30 for EU/UAE

class APIConfig(BaseModel):
    # ... existing fields ...
    region_policy: RegionPolicy = Field(
        default_factory=lambda: RegionPolicy(
            region_id=os.getenv("REGION_ID", "frankfurt"),
            jurisdiction=os.getenv("DATA_RESIDENCY", "eu"),
            allowed_source_countries=json.loads(
                os.getenv("ALLOWED_SOURCE_COUNTRIES", '["DE","FR","NL","BE","AT","PL","SE","DK","FI","IE","PT","GR","CZ","RO","HU","IT","ES"]')
            ),
        )
    )
```

### Enforcement flow

1. Helm values sets `REGION_ID`, `DATA_RESIDENCY`, `ALLOWED_SOURCE_COUNTRIES` env vars per region via `values-frankfurt.yaml` / `values-uae.yaml`.
2. `APIConfig` loads `RegionPolicy` from env at startup — immutable at runtime.
3. `EdgeOrchestrator.route_call()` checks `CallContext.source_country` against `RegionPolicy.allowed_source_countries` and rejects/returns None if not in list.
4. Admin API endpoint `/admin/v1/routing-policy` (new) returns the current effective policy (read-only for audit). Write operations require a new signed config pushed from the global control plane, validated against the hard guardrail fields (`deny_cross_region_audio` cannot be set to False by any admin).

### Admin endpoint shape

```python
# GET /admin/v1/routing-policy
{
  "region_id": "frankfurt",
  "jurisdiction": "eu",
  "allowed_source_countries": ["DE", "FR", ...],
  "deny_cross_region_audio": true,
  "deny_cross_region_transcripts": true,
  "compliance_framework": "gdpr",
  "erasure_sla_days": 30
}
```

No admin action can flip `deny_cross_region_audio` to `false` — these are compile-time constants validated at startup with a startup assertion.

---

## 7. Existing Patterns to Reuse

The following chart features are immediately reusable in overlays — no reimplementation needed:

| Feature | Where | How overlays use it |
|---|---|---|
| `global.region` value key | `values.yaml` line 12, used in `_helpers.tpl` labels and affinity | Override in `values-<region>.yaml` |
| `global.dataResidency` | `values.yaml` line 13, injected as `DATA_RESIDENCY` env var | Override in `values-<region>.yaml` |
| `global.gdprCompliance` / `aiActCompliance` | `values.yaml` line 14-15, injected as `EU_COMPLIANCE_MODE` | Set `false` for UAE in `values-uae.yaml` |
| `global.storageClass` | `values.yaml` line 22, used in PostgreSQL + Redis PVCs | Override per region |
| `ingress.annotations` map | `templates/ingress.yaml` — toYaml passthrough | Add ExternalDNS annotations in `values-<region>.yaml` |
| `ingress.hosts` list | `templates/ingress.yaml` | Set region hostnames in `values-<region>.yaml` |
| `euvoice-platform.complianceEnv` helper | `_helpers.tpl` lines 82-93 | Automatically picks up `global.*` overrides |
| `euvoice-platform.affinity` helper | `_helpers.tpl` lines 143-168 | Needs value-ification of node label key (currently hardcoded `eu-node`) |
| `namespace.labels` / `namespace.annotations` | `templates/namespace.yaml` | Override in `values-<region>.yaml` for jurisdiction labels |
| `monitoring.alertmanager.channel` | `values.yaml` line 265 | Set per-region Slack channel |
| `security.auditLogging.enabled` / `retention` | `values.yaml` line 283-284 | Keep shared default |
| `secrets.*` keys | `templates/secrets.yaml` — built from values | Use External Secrets Operator per region (ref `k8s/security/encryption.yaml`) |
| GDPR cleanup CronJob | `k8s/security/gdpr-compliance.yaml` | Patch S3 bucket name per region in overlay |
| NetworkPolicy templates | `k8s/security/network-policies.yaml` | Add CIDR-scope patch per region |

**One gap:** The `euvoice-platform.affinity` helper in `_helpers.tpl` hardcodes `compliance.euvoice.ai/eu-node: "true"` as the node label requirement. This must be refactored to use `{{ .Values.global.nodeComplianceLabel | default "compliance.euvoice.ai/eu-node" }}` before the UAE overlay can specify `uae-node: "true"` without patching the Deployment spec directly.

---

## 8. Recommended Plan Structure (for Planner)

### Plan 14-01: Frankfurt Kustomize Overlay + ExternalDNS (MULTI-01, MULTI-03 partial)

**Scope:** Create `k8s/overlays/frankfurt/` with `values-frankfurt.yaml`, `kustomization.yaml`, `ingress-patch.yaml` (ExternalDNS EU annotations), and `externaldns-deployment.yaml`. Fix the hardcoded `eu-node` affinity label to use a values key. Verify `helm template | kubectl apply --dry-run` produces a valid Frankfurt manifest set.

**Deliverables:** `k8s/overlays/frankfurt/` directory, updated `_helpers.tpl`, test script.

### Plan 14-02: UAE Kustomize Overlay + ExternalDNS (MULTI-02, MULTI-03 partial)

**Scope:** Create `k8s/overlays/uae/` mirroring Frankfurt structure with UAE-specific values (`me-central-1`, `uae-pdpl`, UAE hostnames, UAE ExternalDNS instance). Add UAE StorageClass manifest with UAE KMS key reference. Verify dry-run.

**Deliverables:** `k8s/overlays/uae/` directory, UAE StorageClass, UAE ExternalDNS deployment.

### Plan 14-03: Data Residency Enforcement (MULTI-04)

**Scope:** Add CIDR-scoped egress NetworkPolicy overlays for both regions. Add OPA/Gatekeeper ConstraintTemplate + Constraint for region affinity enforcement. Add namespace PSA labels to both overlays. Extend `APIConfig` with `RegionPolicy` and add the `EdgeOrchestrator` country-allowlist check. Add admin read endpoint `/admin/v1/routing-policy`.

**Deliverables:** `network-policy-egress-restriction.yaml` (both regions), Gatekeeper manifests, updated `src/api/config.py`, updated `src/core/edge_orchestrator.py`, new admin router.

### Plan 14-04: DNS Geo-Routing Completion + Cross-Region Sync (MULTI-03, MULTI-04)

**Scope:** Complete ExternalDNS Route53 geolocation configuration (geolocation routing records, TXT ownership, set-identifiers). Define the Prometheus federation scrape config for the global control plane. Document and test the health metadata endpoint (`/admin/v1/region/status`). Write integration tests covering residency guardrails and routing rejections.

**Deliverables:** ExternalDNS geo-routing working configs (both regions), Prometheus federation config, integration tests for MULTI-03/MULTI-04 acceptance criteria.

---

## Open Questions

1. **UAE cloud provider:** AWS `me-central-1` (UAE region) or Azure UAE North? The codebase shows AWS NLB and AWS KMS annotations everywhere — this suggests AWS for both regions, but UAE sovereign cloud requirements may mandate a local provider. The planner should confirm and choose one for the StorageClass KMS key ARN.

2. **Node label for UAE affinity:** The `_helpers.tpl` hardcodes `compliance.euvoice.ai/eu-node: "true"`. Should this be generalized to `compliance.euvoice.ai/sovereign-node: "true"` (same label, all sovereign regions) or kept region-specific (`eu-node`, `uae-node`)? Region-specific is more auditable; shared label is simpler.

3. **DNS zones:** Frankfurt uses `voiquyr.eu` (already in ingress values). UAE zone is not defined anywhere — `voiquyr.ae` is the obvious choice. Confirm domain ownership before plan execution.

4. **OPA/Gatekeeper vs. Kyverno:** Gatekeeper is the CNCF-graduated choice with the widest adoption. Kyverno is simpler to write policies for. Neither is currently in the stack — the planner must choose one to introduce.

5. **Sovereignty guardrail for default Route53 record:** Route53 geolocation routing requires a default record for unmatched source IPs. The system must either (a) return `NXDOMAIN` / no default record (rejecting unmatched traffic), or (b) route to Frankfurt as the legal default and rely on the app layer to reject. Option (a) is cleaner for sovereignty but may break legitimate traffic. The planner should decide.

6. **External Secrets Operator vs. sealed-secrets:** Both exist in `k8s/security/encryption.yaml`. The planner should pick one per region and stick with it — mixing creates operational confusion.
