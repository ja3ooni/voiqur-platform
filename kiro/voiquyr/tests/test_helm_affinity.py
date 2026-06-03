"""
Tests for Plan 14-01: Helm affinity helper generalisation.

Verifies that the rendered API Deployment still has the expected nodeAffinity
requirements after the _helpers.tpl change (nodeComplianceLabel now value-driven).

Requires: helm binary on PATH (skipped otherwise).
Run from: kiro/voiquyr/ — pytest root.
"""
import shutil
import subprocess
import pathlib
import pytest
import yaml

# Repo root is two levels up from kiro/voiquyr/
_KIRO_VOIQUYR = pathlib.Path(__file__).parent.parent  # kiro/voiquyr/
_CHART_PATH = _KIRO_VOIQUYR / "k8s" / "helm" / "euvoice-platform"

_HELM_MISSING = shutil.which("helm") is None


@pytest.mark.skipif(_HELM_MISSING, reason="helm not installed — skipping helm template tests")
def _render_helm_template() -> list[dict]:
    """Run `helm template euvoice <chart>` and return all parsed YAML documents."""
    result = subprocess.run(
        ["helm", "template", "euvoice", str(_CHART_PATH)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"helm template failed (exit {result.returncode}):\n{result.stderr}"
    )
    docs = list(yaml.safe_load_all(result.stdout))
    return [d for d in docs if d is not None]


def _find_api_deployment(docs: list[dict]) -> dict:
    """Return the API Deployment from a list of parsed K8s documents."""
    for doc in docs:
        if doc.get("kind") == "Deployment":
            name: str = doc.get("metadata", {}).get("name", "")
            if "api" in name and "cc" not in name and "command" not in name:
                return doc
    raise AssertionError(
        f"No API Deployment found in rendered documents. Found kinds: "
        f"{[d.get('kind') for d in docs]}"
    )


@pytest.mark.skipif(_HELM_MISSING, reason="helm not installed — skipping helm template tests")
def test_affinity_uses_eu_node_label_by_default() -> None:
    """Default values must produce compliance.euvoice.ai/eu-node affinity."""
    docs = _render_helm_template()
    api_deploy = _find_api_deployment(docs)

    spec = api_deploy.get("spec", {}).get("template", {}).get("spec", {})
    affinity = spec.get("affinity", {})
    node_affinity = affinity.get("nodeAffinity", {})
    required = node_affinity.get("requiredDuringSchedulingIgnoredDuringExecution", {})
    node_selector_terms = required.get("nodeSelectorTerms", [])

    assert node_selector_terms, "No nodeSelectorTerms found in API Deployment affinity"

    # Collect all matchExpression keys across all terms
    all_keys = [
        expr["key"]
        for term in node_selector_terms
        for expr in term.get("matchExpressions", [])
    ]

    assert "compliance.euvoice.ai/eu-node" in all_keys, (
        f"Expected 'compliance.euvoice.ai/eu-node' affinity key. Found keys: {all_keys}"
    )


@pytest.mark.skipif(_HELM_MISSING, reason="helm not installed — skipping helm template tests")
def test_affinity_uses_correct_region() -> None:
    """Default values must produce topology.kubernetes.io/region = eu-central-1 affinity."""
    docs = _render_helm_template()
    api_deploy = _find_api_deployment(docs)

    spec = api_deploy.get("spec", {}).get("template", {}).get("spec", {})
    affinity = spec.get("affinity", {})
    node_affinity = affinity.get("nodeAffinity", {})
    required = node_affinity.get("requiredDuringSchedulingIgnoredDuringExecution", {})
    node_selector_terms = required.get("nodeSelectorTerms", [])

    region_exprs = [
        expr
        for term in node_selector_terms
        for expr in term.get("matchExpressions", [])
        if expr.get("key") == "topology.kubernetes.io/region"
    ]

    assert region_exprs, "No topology.kubernetes.io/region matchExpression found"
    assert "eu-central-1" in region_exprs[0].get("values", []), (
        f"Expected 'eu-central-1' in region values. Got: {region_exprs[0].get('values')}"
    )


@pytest.mark.skipif(_HELM_MISSING, reason="helm not installed — skipping helm template tests")
def test_node_compliance_label_override() -> None:
    """Setting global.nodeComplianceLabel should change the affinity key."""
    result = subprocess.run(
        [
            "helm", "template", "euvoice", str(_CHART_PATH),
            "--set", "global.nodeComplianceLabel=compliance.euvoice.ai/uae-node",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"helm template failed:\n{result.stderr}"

    docs = [d for d in yaml.safe_load_all(result.stdout) if d is not None]
    api_deploy = _find_api_deployment(docs)

    spec = api_deploy.get("spec", {}).get("template", {}).get("spec", {})
    affinity = spec.get("affinity", {})
    node_affinity = affinity.get("nodeAffinity", {})
    required = node_affinity.get("requiredDuringSchedulingIgnoredDuringExecution", {})
    node_selector_terms = required.get("nodeSelectorTerms", [])

    all_keys = [
        expr["key"]
        for term in node_selector_terms
        for expr in term.get("matchExpressions", [])
    ]

    assert "compliance.euvoice.ai/uae-node" in all_keys, (
        f"Expected overridden 'compliance.euvoice.ai/uae-node' key. Found: {all_keys}"
    )
    assert "compliance.euvoice.ai/eu-node" not in all_keys, (
        f"Old hardcoded key 'compliance.euvoice.ai/eu-node' should not appear after override. Found: {all_keys}"
    )
