"""
Tests for vLLM server deployment configuration.

SELF-01: vLLM server deployment for Mistral inference.
"""

import os
import yaml
import pytest


VLLM_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "deployments",
    "vllm",
)


class TestDockerfileExists:
    """Dockerfile is present and structurally correct."""

    def test_dockerfile_exists(self):
        path = os.path.join(VLLM_DIR, "Dockerfile")
        assert os.path.isfile(path), "Dockerfile missing in deployments/vllm/"

    def test_dockerfile_uses_vllm_base_image(self):
        path = os.path.join(VLLM_DIR, "Dockerfile")
        content = open(path).read()
        assert "vllm/vllm-openai" in content, "Dockerfile should use vllm/vllm-openai base image"

    def test_dockerfile_exposes_port_8000(self):
        path = os.path.join(VLLM_DIR, "Dockerfile")
        content = open(path).read()
        assert "EXPOSE 8000" in content

    def test_dockerfile_has_healthcheck(self):
        path = os.path.join(VLLM_DIR, "Dockerfile")
        content = open(path).read()
        assert "HEALTHCHECK" in content

    def test_dockerfile_uses_openai_entrypoint(self):
        path = os.path.join(VLLM_DIR, "Dockerfile")
        content = open(path).read()
        assert "vllm.entrypoints.openai.api_server" in content


class TestDockerComposeExists:
    """docker-compose.yml is valid and includes GPU support."""

    def test_compose_exists(self):
        path = os.path.join(VLLM_DIR, "docker-compose.yml")
        assert os.path.isfile(path)

    def test_compose_is_valid_yaml(self):
        path = os.path.join(VLLM_DIR, "docker-compose.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert "services" in data

    def test_compose_has_vllm_service(self):
        path = os.path.join(VLLM_DIR, "docker-compose.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "vllm" in data["services"]

    def test_compose_maps_port_8001_to_8000(self):
        path = os.path.join(VLLM_DIR, "docker-compose.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        ports = data["services"]["vllm"]["ports"]
        assert any("8001" in str(p) for p in ports)

    def test_compose_has_gpu_reservation(self):
        path = os.path.join(VLLM_DIR, "docker-compose.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        deploy = data["services"]["vllm"].get("deploy", {})
        resources = deploy.get("resources", {})
        reservations = resources.get("reservations", {})
        devices = reservations.get("devices", [])
        assert any(d.get("driver") == "nvidia" for d in devices)

    def test_compose_has_huggingface_volume(self):
        path = os.path.join(VLLM_DIR, "docker-compose.yml")
        with open(path) as f:
            data = yaml.safe_load(f)
        volumes = data.get("volumes", {})
        assert "huggingface_cache" in volumes


class TestVLLMConfigExists:
    """config.yaml is present with required fields."""

    def test_config_exists(self):
        path = os.path.join(VLLM_DIR, "config.yaml")
        assert os.path.isfile(path)

    def test_config_is_valid_yaml(self):
        path = os.path.join(VLLM_DIR, "config.yaml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data is not None

    def test_config_has_server_section(self):
        path = os.path.join(VLLM_DIR, "config.yaml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "server" in data

    def test_config_has_model_section(self):
        path = os.path.join(VLLM_DIR, "config.yaml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "model" in data
        assert "name" in data["model"]

    def test_config_has_gpu_memory_utilization(self):
        path = os.path.join(VLLM_DIR, "config.yaml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "gpu" in data
        util = data["gpu"]["memory_utilization"]
        assert 0.5 <= util <= 1.0, "GPU memory utilization should be between 0.5 and 1.0"

    def test_config_default_model_is_mistral(self):
        path = os.path.join(VLLM_DIR, "config.yaml")
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "mistral" in data["model"]["name"].lower()
