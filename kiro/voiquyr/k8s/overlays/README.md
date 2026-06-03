# Kustomize Overlays

## Layout

```
overlays/
├── base/                  # Kustomize base — wraps the local Helm chart with default values
│   └── kustomization.yaml
├── frankfurt/             # EU/Frankfurt sovereign region overlay
│   ├── kustomization.yaml
│   ├── values-frankfurt.yaml         # Frankfurt-specific Helm value overrides
│   ├── ingress-patch.yaml            # ExternalDNS Route53 geolocation annotations
│   ├── namespace-patch.yaml          # Pod Security Admission + compliance labels
│   └── externaldns-deployment.yaml   # Region-local ExternalDNS controller (eu-central-1)
└── README.md              # This file
```

## Building

**IMPORTANT:** All overlay builds require `--enable-helm` because the base wraps a local Helm chart.

```bash
# Render the base (default Frankfurt values)
kustomize build --enable-helm kiro/voiquyr/k8s/overlays/base/

# Render the Frankfurt overlay
kustomize build --enable-helm kiro/voiquyr/k8s/overlays/frankfurt/

# Dry-run against a cluster
kustomize build --enable-helm kiro/voiquyr/k8s/overlays/frankfurt/ | kubectl apply --dry-run=client --validate=true -f -

# Deploy to Frankfurt
kustomize build --enable-helm kiro/voiquyr/k8s/overlays/frankfurt/ | kubectl apply -f -
```

## Adding a New Region

1. Copy `frankfurt/` to `<region>/`.
2. Update `values-<region>.yaml` with the region-specific `global.region`, `global.nodeComplianceLabel`, `global.dataResidency`, and ingress hosts.
3. Update `ingress-patch.yaml`: change `aws-set-identifier`, `aws-geolocation-*`, and TXT prefix.
4. Update `externaldns-deployment.yaml`: change `--aws-region`, `--txt-owner-id`, `--txt-prefix`, and `--domain-filter`.
5. Update `namespace-patch.yaml`: change `compliance.euvoice.ai/region` and `compliance.euvoice.ai/jurisdiction`.
6. Wire in the new `kustomization.yaml`.

## Overlay Pattern

Each region overlay:
- Inherits all resources from `base` (which renders the Helm chart with default values).
- Adds a region-local ExternalDNS controller as a direct resource.
- Patches the rendered Ingress to add Route53 geolocation annotations.
- Patches the Namespace to apply Pod Security Admission labels and compliance metadata.
- Overrides Helm values via a region-specific `values-<region>.yaml`.

Data sovereignty is enforced by `Edge_Orchestrator`: it rejects calls rather than rerouting to a
different jurisdiction if the designated edge node is unavailable.
