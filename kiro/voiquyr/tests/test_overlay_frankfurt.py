"""
Tests for Plan 14-01: Frankfurt Kustomize overlay.

Verifies that `kustomize build --enable-helm kiro/voiquyr/k8s/overlays/frankfurt/`
exits 0 and the output contains:
  - An Ingress with ExternalDNS Route53 annotation aws-set-identifier=frankfurt
  - A Namespace with pod-security.kubernetes.io/enforce=restricted
  - An ExternalDNS Deployment with --aws-region=eu-central-1

Also tests kubectl dry-run (skipped if kubectl not on PATH).

Requires: kustomize binary on PATH (skipped otherwise).
Run from: kiro/voiquyr/ — pytest root.
"""
import shutil
import subprocess
import pathlib
import pytest
import yaml

_KIRO_VOIQUYR = pathlib.Path(__file__).parent.parent  # kiro/voiquyr/
_FRANKFURT_OVERLAY = _KIRO_VOIQUYR / "k8s" / "overlays" / "frankfurt"

_KUSTOMIZE_MISSING = shutil.which("kustomize") is None
_KUBECTL_MISSING = shutil.which("kubectl") is None


def _build_frankfurt_overlay() -> tuple[int, str, str]:
    """Run kustomize build on the frankfurt overlay and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["kustomize", "build", "--enable-helm", str(_FRANKFURT_OVERLAY)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


def _parse_docs(stdout: str) -> list[dict]:
    """Parse all non-None YAML documents from kustomize output."""
    return [d for d in yaml.safe_load_all(stdout) if d is not None]


# ─── Structural / no-binary tests ─────────────────────────────────────────────

def test_frankfurt_overlay_files_exist() -> None:
    """All required Frankfurt overlay files must exist on disk."""
    required_files = [
        "kustomization.yaml",
        "values-frankfurt.yaml",
        "ingress-patch.yaml",
        "namespace-patch.yaml",
        "externaldns-deployment.yaml",
    ]
    for filename in required_files:
        path = _FRANKFURT_OVERLAY / filename
        assert path.exists(), f"Required Frankfurt overlay file missing: {path}"


def test_ingress_patch_has_aws_set_identifier() -> None:
    """ingress-patch.yaml must contain aws-set-identifier: frankfurt."""
    patch_path = _FRANKFURT_OVERLAY / "ingress-patch.yaml"
    content = patch_path.read_text()
    assert "aws-set-identifier" in content, "ingress-patch.yaml missing aws-set-identifier annotation"
    assert "frankfurt" in content, "ingress-patch.yaml missing frankfurt identifier value"


def test_ingress_patch_has_geolocation_annotation() -> None:
    """ingress-patch.yaml must contain EU geolocation annotation."""
    patch_path = _FRANKFURT_OVERLAY / "ingress-patch.yaml"
    content = patch_path.read_text()
    assert "aws-geolocation-continent-code" in content, (
        "ingress-patch.yaml missing aws-geolocation-continent-code annotation"
    )
    assert "EU" in content, "ingress-patch.yaml missing EU geolocation value"


def test_namespace_patch_has_psa_labels() -> None:
    """namespace-patch.yaml must contain Pod Security Admission labels."""
    patch_path = _FRANKFURT_OVERLAY / "namespace-patch.yaml"
    content = patch_path.read_text()
    assert "pod-security.kubernetes.io/enforce" in content, (
        "namespace-patch.yaml missing pod-security.kubernetes.io/enforce label"
    )
    assert "restricted" in content, (
        "namespace-patch.yaml missing restricted PSA value"
    )


def test_externaldns_deployment_has_correct_region() -> None:
    """externaldns-deployment.yaml must target eu-central-1."""
    deployment_path = _FRANKFURT_OVERLAY / "externaldns-deployment.yaml"
    content = deployment_path.read_text()
    assert "--aws-region=eu-central-1" in content, (
        "externaldns-deployment.yaml missing --aws-region=eu-central-1"
    )
    assert "--txt-owner-id=voiquyr-frankfurt" in content, (
        "externaldns-deployment.yaml missing --txt-owner-id=voiquyr-frankfurt"
    )
    assert "--domain-filter=voiquyr.eu" in content, (
        "externaldns-deployment.yaml missing --domain-filter=voiquyr.eu"
    )


def test_externaldns_deployment_yaml_parses() -> None:
    """externaldns-deployment.yaml must be valid YAML with expected resource kinds."""
    deployment_path = _FRANKFURT_OVERLAY / "externaldns-deployment.yaml"
    docs = [d for d in yaml.safe_load_all(deployment_path.read_text()) if d is not None]
    kinds = {d.get("kind") for d in docs}
    assert "Deployment" in kinds, f"No Deployment in externaldns-deployment.yaml. Found: {kinds}"
    assert "ServiceAccount" in kinds, f"No ServiceAccount in externaldns-deployment.yaml. Found: {kinds}"
    assert "ClusterRole" in kinds, f"No ClusterRole in externaldns-deployment.yaml. Found: {kinds}"
    assert "ClusterRoleBinding" in kinds, f"No ClusterRoleBinding in externaldns-deployment.yaml. Found: {kinds}"


# ─── kustomize binary tests ────────────────────────────────────────────────────

@pytest.mark.skipif(_KUSTOMIZE_MISSING, reason="kustomize not installed — skipping overlay build tests")
def test_frankfurt_overlay_exits_zero() -> None:
    """kustomize build --enable-helm of the Frankfurt overlay must exit 0."""
    returncode, _stdout, stderr = _build_frankfurt_overlay()
    assert returncode == 0, (
        f"kustomize build frankfurt overlay failed (exit {returncode}):\n{stderr}"
    )


@pytest.mark.skipif(_KUSTOMIZE_MISSING, reason="kustomize not installed — skipping overlay build tests")
def test_frankfurt_overlay_ingress_has_aws_set_identifier() -> None:
    """Rendered Ingress must have aws-set-identifier: frankfurt annotation."""
    returncode, stdout, stderr = _build_frankfurt_overlay()
    assert returncode == 0, f"kustomize build failed:\n{stderr}"

    docs = _parse_docs(stdout)
    ingresses = [d for d in docs if d.get("kind") == "Ingress"]
    assert ingresses, f"No Ingress in Frankfurt overlay output. Kinds: {[d.get('kind') for d in docs]}"

    ingress = ingresses[0]
    annotations = ingress.get("metadata", {}).get("annotations", {})
    set_id = annotations.get("external-dns.alpha.kubernetes.io/aws-set-identifier")
    assert set_id == "frankfurt", (
        f"Expected aws-set-identifier=frankfurt, got: {set_id}"
    )


@pytest.mark.skipif(_KUSTOMIZE_MISSING, reason="kustomize not installed — skipping overlay build tests")
def test_frankfurt_overlay_namespace_has_psa_labels() -> None:
    """Rendered Namespace must have pod-security.kubernetes.io/enforce=restricted."""
    returncode, stdout, stderr = _build_frankfurt_overlay()
    assert returncode == 0, f"kustomize build failed:\n{stderr}"

    docs = _parse_docs(stdout)
    namespaces = [d for d in docs if d.get("kind") == "Namespace"]
    assert namespaces, f"No Namespace in Frankfurt overlay output"

    voiquyr_ns = next(
        (ns for ns in namespaces if ns.get("metadata", {}).get("name") == "voiquyr"),
        None,
    )
    assert voiquyr_ns is not None, "No voiquyr Namespace found in rendered output"

    labels = voiquyr_ns.get("metadata", {}).get("labels", {})
    enforce_value = labels.get("pod-security.kubernetes.io/enforce")
    assert enforce_value == "restricted", (
        f"Expected pod-security.kubernetes.io/enforce=restricted, got: {enforce_value}"
    )


@pytest.mark.skipif(_KUSTOMIZE_MISSING, reason="kustomize not installed — skipping overlay build tests")
def test_frankfurt_overlay_externaldns_deployment() -> None:
    """Rendered output must contain ExternalDNS Deployment targeting eu-central-1."""
    returncode, stdout, stderr = _build_frankfurt_overlay()
    assert returncode == 0, f"kustomize build failed:\n{stderr}"

    docs = _parse_docs(stdout)
    deployments = [d for d in docs if d.get("kind") == "Deployment"]
    assert deployments, "No Deployments in Frankfurt overlay output"

    edns_deploy = next(
        (
            d for d in deployments
            if d.get("metadata", {}).get("name") == "external-dns"
        ),
        None,
    )
    assert edns_deploy is not None, (
        f"No external-dns Deployment in output. Deployments found: "
        f"{[d.get('metadata', {}).get('name') for d in deployments]}"
    )

    containers = (
        edns_deploy.get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("containers", [])
    )
    assert containers, "external-dns Deployment has no containers"

    args = containers[0].get("args", [])
    assert "--aws-region=eu-central-1" in args, (
        f"--aws-region=eu-central-1 not in ExternalDNS args: {args}"
    )


@pytest.mark.skipif(_KUSTOMIZE_MISSING, reason="kustomize not installed — skipping overlay build tests")
def test_frankfurt_overlay_no_non_eu_references() -> None:
    """Frankfurt overlay output must not reference non-EU regions or UAE."""
    returncode, stdout, stderr = _build_frankfurt_overlay()
    assert returncode == 0, f"kustomize build failed:\n{stderr}"

    non_eu_patterns = ["me-central-1", "ap-southeast", "us-east", "us-west"]
    for pattern in non_eu_patterns:
        assert pattern not in stdout, (
            f"Frankfurt overlay output contains non-EU reference: '{pattern}'"
        )


# ─── kubectl dry-run test ──────────────────────────────────────────────────────

@pytest.mark.skipif(
    _KUSTOMIZE_MISSING or _KUBECTL_MISSING,
    reason="kustomize or kubectl not installed — skipping dry-run test",
)
def test_kubectl_dry_run() -> None:
    """kubectl apply --dry-run=client must accept the Frankfurt overlay manifests."""
    # First build the overlay
    build_result = subprocess.run(
        ["kustomize", "build", "--enable-helm", str(_FRANKFURT_OVERLAY)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build_result.returncode == 0, (
        f"kustomize build failed (exit {build_result.returncode}):\n{build_result.stderr}"
    )

    # Pipe to kubectl dry-run
    apply_result = subprocess.run(
        ["kubectl", "apply", "--dry-run=client", "--validate=true", "-f", "-"],
        input=build_result.stdout,
        capture_output=True,
        text=True,
        check=False,
    )

    assert apply_result.returncode == 0, (
        f"kubectl apply --dry-run failed (exit {apply_result.returncode}):\n"
        f"stderr: {apply_result.stderr}\nstdout: {apply_result.stdout}"
    )
    assert "error validating data" not in apply_result.stderr.lower(), (
        f"kubectl reported validation errors:\n{apply_result.stderr}"
    )
