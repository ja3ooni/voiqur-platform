"""
EuroHPC Infrastructure Integration

Supports job submission to LUMI (Finland), MareNostrum (Spain),
and Meluxina (Luxembourg) supercomputers via SLURM.
Implements Requirement 15.2, 15.7.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class Cluster(Enum):
    LUMI = "lumi"               # CSC, Finland — AMD MI250X GPUs
    MARE_NOSTRUM = "marenostrum" # BSC, Spain — NVIDIA H100
    MELUXINA = "meluxina"        # LuxProvide, Luxembourg — NVIDIA A100


@dataclass
class ClusterConfig:
    cluster: Cluster
    host: str
    username: str
    ssh_key_path: str
    partition: str
    account: str
    max_gpus: int = 8
    gpu_type: str = "gpu"


# Default cluster endpoints (users override via env / config)
CLUSTER_DEFAULTS: Dict[Cluster, Dict[str, Any]] = {
    Cluster.LUMI: {
        "host": "lumi.csc.fi",
        "partition": "standard-g",
        "gpu_type": "MI250X",
        "max_gpus": 8,
    },
    Cluster.MARE_NOSTRUM: {
        "host": "mn1.bsc.es",
        "partition": "acc",
        "gpu_type": "H100",
        "max_gpus": 4,
    },
    Cluster.MELUXINA: {
        "host": "login.lxp.lu",
        "partition": "gpu",
        "gpu_type": "A100",
        "max_gpus": 4,
    },
}


@dataclass
class JobSpec:
    """SLURM job specification for a training run."""
    job_name: str
    script_path: str
    num_gpus: int = 1
    num_nodes: int = 1
    wall_time: str = "24:00:00"
    memory_gb: int = 64
    environment_vars: Dict[str, str] = field(default_factory=dict)
    modules: List[str] = field(default_factory=list)
    extra_sbatch: Dict[str, str] = field(default_factory=dict)


@dataclass
class JobStatus:
    job_id: str
    cluster: Cluster
    state: str          # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    submitted_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    stdout_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "cluster": self.cluster.value,
            "state": self.state,
            "submitted_at": self.submitted_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "exit_code": self.exit_code,
        }


@dataclass
class CostEstimate:
    cluster: Cluster
    gpu_hours: float
    cost_eur: float
    cost_aws_equivalent_eur: float
    cost_gcp_equivalent_eur: float
    savings_vs_aws_pct: float
    savings_vs_gcp_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster": self.cluster.value,
            "gpu_hours": self.gpu_hours,
            "cost_eur": round(self.cost_eur, 2),
            "cost_aws_equivalent_eur": round(self.cost_aws_equivalent_eur, 2),
            "cost_gcp_equivalent_eur": round(self.cost_gcp_equivalent_eur, 2),
            "savings_vs_aws_pct": round(self.savings_vs_aws_pct, 1),
            "savings_vs_gcp_pct": round(self.savings_vs_gcp_pct, 1),
        }


# Cost per GPU-hour in EUR (approximate 2025 rates)
_EUROHPC_COST_PER_GPU_HOUR = {
    Cluster.LUMI: 0.10,          # ~0.10 EUR/GPU-h (allocation-based)
    Cluster.MARE_NOSTRUM: 0.12,
    Cluster.MELUXINA: 0.15,
}
_AWS_P4D_COST_PER_GPU_HOUR = 3.20   # p4d.24xlarge / 8 A100s
_GCP_A100_COST_PER_GPU_HOUR = 2.93  # a2-highgpu-1g


class SLURMClient:
    """
    Async SLURM REST API client (SLURM 22+ slurmrestd).
    Falls back to SSH subprocess for older clusters.
    """

    def __init__(self, config: ClusterConfig):
        self.config = config
        self._rest_base = f"https://{config.host}:6820/slurm/v0.0.40"
        self._session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(f"{__name__}.{config.cluster.value}")

    async def _get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            token = os.environ.get(
                f"EUROHPC_{self.config.cluster.value.upper()}_TOKEN", ""
            )
            self._session = aiohttp.ClientSession(
                headers={"X-SLURM-USER-TOKEN": token,
                         "X-SLURM-USER-NAME": self.config.username}
            )
        return self._session

    async def submit_job(self, spec: JobSpec) -> str:
        """Submit a SLURM job. Returns job ID."""
        script = self._render_script(spec)
        try:
            session = await self._get_session()
            payload = {"script": script}
            async with session.post(
                f"{self._rest_base}/job/submit",
                json=payload,
                ssl=False,
            ) as resp:
                data = await resp.json()
                job_id = str(data.get("job_id", ""))
                self.logger.info(f"Submitted job {job_id} to {self.config.cluster.value}")
                return job_id
        except Exception as e:
            self.logger.error(f"REST submit failed ({e}), falling back to SSH")
            return await self._ssh_submit(script)

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        try:
            session = await self._get_session()
            async with session.get(
                f"{self._rest_base}/job/{job_id}", ssl=False
            ) as resp:
                data = await resp.json()
                jobs = data.get("jobs", [{}])
                return jobs[0] if jobs else {}
        except Exception as e:
            self.logger.warning(f"Could not get job status: {e}")
            return {}

    async def cancel_job(self, job_id: str) -> bool:
        try:
            session = await self._get_session()
            async with session.delete(
                f"{self._rest_base}/job/{job_id}", ssl=False
            ) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _render_script(self, spec: JobSpec) -> str:
        lines = ["#!/bin/bash"]
        lines += [
            f"#SBATCH --job-name={spec.job_name}",
            f"#SBATCH --nodes={spec.num_nodes}",
            f"#SBATCH --gpus-per-node={spec.num_gpus}",
            f"#SBATCH --time={spec.wall_time}",
            f"#SBATCH --mem={spec.memory_gb}G",
            f"#SBATCH --partition={self.config.partition}",
            f"#SBATCH --account={self.config.account}",
        ]
        for k, v in spec.extra_sbatch.items():
            lines.append(f"#SBATCH --{k}={v}")
        lines.append("")
        for mod in spec.modules:
            lines.append(f"module load {mod}")
        for k, v in spec.environment_vars.items():
            lines.append(f"export {k}={v}")
        lines += ["", f"srun python {spec.script_path}"]
        return "\n".join(lines)

    async def _ssh_submit(self, script: str) -> str:
        """Fallback: write script to temp file and submit via SSH subprocess."""
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as f:
            f.write(script)
            tmp_path = f.name
        proc = await asyncio.create_subprocess_exec(
            "ssh",
            "-i", self.config.ssh_key_path,
            f"{self.config.username}@{self.config.host}",
            f"sbatch < {tmp_path}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        # "Submitted batch job 12345"
        parts = stdout.decode().strip().split()
        return parts[-1] if parts else ""


class EuroHPCManager:
    """
    High-level manager for EuroHPC job lifecycle and cost tracking.
    """

    def __init__(self):
        self._clients: Dict[Cluster, SLURMClient] = {}
        self._jobs: Dict[str, JobStatus] = {}
        self.logger = logging.getLogger(__name__)

    def register_cluster(self, config: ClusterConfig) -> None:
        self._clients[config.cluster] = SLURMClient(config)
        self.logger.info(f"Registered cluster: {config.cluster.value}")

    async def submit_training_job(
        self,
        cluster: Cluster,
        spec: JobSpec,
    ) -> JobStatus:
        client = self._clients.get(cluster)
        if not client:
            raise ValueError(f"Cluster {cluster.value} not registered")

        job_id = await client.submit_job(spec)
        status = JobStatus(
            job_id=job_id,
            cluster=cluster,
            state="PENDING",
            submitted_at=datetime.utcnow(),
        )
        self._jobs[job_id] = status
        return status

    async def poll_job(self, job_id: str) -> JobStatus:
        status = self._jobs.get(job_id)
        if not status:
            raise KeyError(f"Unknown job: {job_id}")

        client = self._clients[status.cluster]
        raw = await client.get_job_status(job_id)

        slurm_state = raw.get("job_state", status.state)
        status.state = slurm_state

        if slurm_state == "RUNNING" and not status.started_at:
            status.started_at = datetime.utcnow()
        if slurm_state in ("COMPLETED", "FAILED", "CANCELLED"):
            if not status.finished_at:
                status.finished_at = datetime.utcnow()
            status.exit_code = raw.get("exit_code", 0)

        return status

    async def wait_for_completion(
        self, job_id: str, poll_interval: float = 60.0
    ) -> JobStatus:
        while True:
            status = await self.poll_job(job_id)
            if status.state in ("COMPLETED", "FAILED", "CANCELLED"):
                return status
            await asyncio.sleep(poll_interval)

    def estimate_cost(
        self,
        cluster: Cluster,
        num_gpus: int,
        wall_time_hours: float,
    ) -> CostEstimate:
        gpu_hours = num_gpus * wall_time_hours
        eurohpc_cost = gpu_hours * _EUROHPC_COST_PER_GPU_HOUR[cluster]
        aws_cost = gpu_hours * _AWS_P4D_COST_PER_GPU_HOUR
        gcp_cost = gpu_hours * _GCP_A100_COST_PER_GPU_HOUR
        return CostEstimate(
            cluster=cluster,
            gpu_hours=gpu_hours,
            cost_eur=eurohpc_cost,
            cost_aws_equivalent_eur=aws_cost,
            cost_gcp_equivalent_eur=gcp_cost,
            savings_vs_aws_pct=(1 - eurohpc_cost / aws_cost) * 100,
            savings_vs_gcp_pct=(1 - eurohpc_cost / gcp_cost) * 100,
        )

    def compare_all_clusters(
        self, num_gpus: int, wall_time_hours: float
    ) -> List[CostEstimate]:
        return sorted(
            [
                self.estimate_cost(c, num_gpus, wall_time_hours)
                for c in Cluster
            ],
            key=lambda e: e.cost_eur,
        )

    async def close(self) -> None:
        for client in self._clients.values():
            await client.close()
