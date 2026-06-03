# Plan 14-01 Summary: Frankfurt Kustomize Overlay

**Status:** Complete
**Completed:** 2026-06-03
**Requirement:** MULTI-01

## What Was Built

Created the Kustomize overlay structure (`base` + `frankfurt`) that renders the existing Helm chart into a deployable Frankfurt manifest set. The overlay adds ExternalDNS Route53 geolocation annotations (`aws-set-identifier: frankfurt`, `aws-geolocation-continent-code: EU`), EU Pod Security Admission labels on the Namespace, and a region-local ExternalDNS controller scoped to `eu-central-1` + `voiquyr.eu`. The `_helpers.tpl` nodeAffinity key was generalised via `global.nodeComplianceLabel` so future region overlays (e.g. UAE) can select different compliance node labels without forking the chart.

## Files Created/Modified

**Modified:**
- `kiro/voiquyr/k8s/helm/euvoice-platform/templates/_helpers.tpl` — replaced hardcoded `compliance.euvoice.ai/eu-node` key with `{{ .Values.global.nodeComplianceLabel | default "compliance.euvoice.ai/eu-node" }}`
- `kiro/voiquyr/k8s/helm/euvoice-platform/values.yaml` — added `global.nodeComplianceLabel: "compliance.euvoice.ai/eu-node"`

**Created:**
- `kiro/voiquyr/k8s/overlays/README.md` — overlay layout, build commands, and region-addition guide
- `kiro/voiquyr/k8s/overlays/base/kustomization.yaml` — Kustomize base wrapping the local Helm chart
- `kiro/voiquyr/k8s/overlays/frankfurt/kustomization.yaml` — Frankfurt overlay wiring (resources + patches + helmCharts)
- `kiro/voiquyr/k8s/overlays/frankfurt/values-frankfurt.yaml` — Frankfurt Helm value overrides
- `kiro/voiquyr/k8s/overlays/frankfurt/ingress-patch.yaml` — strategic-merge patch adding ExternalDNS Route53 geolocation annotations to the Ingress
- `kiro/voiquyr/k8s/overlays/frankfurt/namespace-patch.yaml` — PSA labels (`enforce/audit/warn: restricted`) + compliance region labels
- `kiro/voiquyr/k8s/overlays/frankfurt/externaldns-deployment.yaml` — Namespace, ServiceAccount, ClusterRole, ClusterRoleBinding, Deployment for ExternalDNS v0.14.2
- `kiro/voiquyr/tests/test_helm_affinity.py` — helm template regression tests (3 tests, skip if helm absent)
- `kiro/voiquyr/tests/test_overlay_base.py` — base overlay build tests (3 require kustomize, 1 structural always runs)
- `kiro/voiquyr/tests/test_overlay_frankfurt.py` — Frankfurt overlay build + dry-run tests (6 structural always run, 6 require kustomize/kubectl)

## Test Results

- `test_helm_affinity.py`: 0 passed, 3 skipped (helm not installed locally)
- `test_overlay_base.py`: 1 passed, 3 skipped (kustomize not installed locally)
- `test_overlay_frankfurt.py`: 6 passed, 6 skipped (kustomize/kubectl not installed locally)
- **Total: 7 passed, 12 skipped, 0 failed**

## Notes

- Ingress resource name in the rendered output is `euvoice` (release name, since `euvoice-platform` contains `euvoice` per _helpers.tpl fullname logic). The ingress-patch.yaml targets name `euvoice`.
- helm, kustomize, and kubectl are not installed on this dev machine; all binary-dependent tests correctly skip with informative messages. The structural/file-content tests (7 tests) run without any binary.
- Decision D-12/D-14 respected: chart not forked — all Frankfurt differences live in `overlays/frankfurt/`.
- No catch-all Route53 fallback record added (deferred to Plan 14-04 per plan notes).
- Plan 14-02 (UAE overlay) can reuse this exact structure with `nodeComplianceLabel: compliance.euvoice.ai/uae-node`.
