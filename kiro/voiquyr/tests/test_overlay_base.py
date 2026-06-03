"""
Tests for Plan 14-01: Kustomize base overlay.

Verifies that `kustomize build --enable-helm kiro/voiquyr/k8s/overlays/base/`
exits 0 and the output contains a Deployment.

Requires: kustomize binary on PATH (skipped otherwise).
Run from: kiro/voiquyr/ — pytest root.
"""
import shutil
import subprocess
import pathlib
import pytest
import yaml

_KIRO_VOIQUYR = pathlib.Path(__file__).parent.parent  # kiro/voiquyr/
_BASE_OVERLAY = _KIRO_VOIQUYR / "k8s" / "overlays" / "base"

_KUSTOMIZE_MISSING = shutil.which("kustomize") is None


@pytest.mark.skipif(_KUSTOMIZE_MISSING, reason="kustomize not installed — skipping overlay build tests")
def _build_base_overlay() -> tuple[int, str, str]:
    """Run kustomize build on the base overlay and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["kustomize", "build", "--enable-helm", str(_BASE_OVERLAY)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.mark.skipif(_KUSTOMIZE_MISSING, reason="kustomize not installed — skipping overlay build tests")
def test_base_overlay_exits_zero() -> None:
    """kustomize build --enable-helm of the base overlay must exit 0."""
    returncode, _stdout, stderr = _build_base_overlay()
    assert returncode == 0, (
        f"kustomize build base overlay failed (exit {returncode}):\n{stderr}"
    )


@pytest.mark.skipif(_KUSTOMIZE_MISSING, reason="kustomize not installed — skipping overlay build tests")
def test_base_overlay_contains_deployment() -> None:
    """Base overlay output must contain at least one Deployment."""
    returncode, stdout, stderr = _build_base_overlay()
    assert returncode == 0, f"kustomize build failed:\n{stderr}"

    docs = [d for d in yaml.safe_load_all(stdout) if d is not None]
    kinds = [d.get("kind") for d in docs]
    assert "Deployment" in kinds, (
        f"No Deployment found in base overlay output. Found kinds: {kinds}"
    )


@pytest.mark.skipif(_KUSTOMIZE_MISSING, reason="kustomize not installed — skipping overlay build tests")
def test_base_overlay_kustomization_file_exists() -> None:
    """base/kustomization.yaml must exist on disk (sanity check)."""
    kustomization = _BASE_OVERLAY / "kustomization.yaml"
    assert kustomization.exists(), f"kustomization.yaml not found at {kustomization}"


def test_base_overlay_directory_structure() -> None:
    """Verify base overlay directory and kustomization.yaml exist (no binary required)."""
    assert _BASE_OVERLAY.is_dir(), f"Base overlay directory missing: {_BASE_OVERLAY}"
    kustomization = _BASE_OVERLAY / "kustomization.yaml"
    assert kustomization.exists(), f"Base kustomization.yaml missing: {kustomization}"

    content = kustomization.read_text()
    assert "helmCharts" in content, "kustomization.yaml must reference helmCharts"
    assert "euvoice-platform" in content, "kustomization.yaml must reference euvoice-platform chart"
