"""
Training System Tests (Task 15.5)

Tests for LoRA fine-tuning, EuroHPC job submission, transfer learning,
data augmentation, and model performance improvements.
Implements Requirements 15.1, 15.2, 15.3, 15.4.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.eurohpc import (
    Cluster,
    ClusterConfig,
    CostEstimate,
    EuroHPCManager,
    JobSpec,
    JobStatus,
    SLURMClient,
)
from src.agents.transfer_learning import (
    LANGUAGE_NAMES,
    LANGUAGE_SIMILARITY_MAP,
    CrossLingualTransfer,
    DataAugmentor,
    FewShotExample,
    FewShotPrompt,
    TransferConfig,
    ZeroShotClassifier,
    get_source_languages,
)


# ---------------------------------------------------------------------------
# 15.1 LoRA fine-tuning (model_training.py already exists — smoke test)
# ---------------------------------------------------------------------------

class TestLoRAConfig:
    def test_training_config_defaults(self):
        from src.agents.model_training import TrainingConfig
        cfg = TrainingConfig()
        assert cfg.use_lora is True
        assert cfg.lora_r == 16
        assert cfg.lora_alpha == 32
        assert cfg.lora_dropout == 0.1
        assert "q_proj" in cfg.lora_target_modules

    def test_training_config_custom(self):
        from src.agents.model_training import TrainingConfig
        cfg = TrainingConfig(lora_r=8, lora_alpha=16, learning_rate=1e-4)
        assert cfg.lora_r == 8
        assert cfg.lora_alpha == 16
        assert cfg.learning_rate == 1e-4

    def test_model_metrics_defaults(self):
        from src.agents.model_training import ModelMetrics
        m = ModelMetrics(model_name="test", dataset_name="ds", language="hr")
        assert m.wer == 0.0
        assert m.timestamp is not None


# ---------------------------------------------------------------------------
# 15.2 EuroHPC Infrastructure Tests
# ---------------------------------------------------------------------------

class TestEuroHPCCostEstimation:
    def setup_method(self):
        self.manager = EuroHPCManager()

    def test_lumi_cheaper_than_aws(self):
        est = self.manager.estimate_cost(Cluster.LUMI, num_gpus=8, wall_time_hours=10)
        assert est.cost_eur < est.cost_aws_equivalent_eur
        assert est.savings_vs_aws_pct > 90  # EuroHPC is ~97% cheaper

    def test_all_clusters_cheaper_than_cloud(self):
        for cluster in Cluster:
            est = self.manager.estimate_cost(cluster, num_gpus=4, wall_time_hours=5)
            assert est.cost_eur < est.cost_aws_equivalent_eur
            assert est.cost_eur < est.cost_gcp_equivalent_eur

    def test_compare_all_clusters_sorted(self):
        estimates = self.manager.compare_all_clusters(num_gpus=4, wall_time_hours=8)
        assert len(estimates) == 3
        costs = [e.cost_eur for e in estimates]
        assert costs == sorted(costs)  # ascending order

    def test_cost_scales_with_gpu_hours(self):
        est1 = self.manager.estimate_cost(Cluster.LUMI, num_gpus=1, wall_time_hours=1)
        est2 = self.manager.estimate_cost(Cluster.LUMI, num_gpus=2, wall_time_hours=1)
        assert abs(est2.cost_eur - 2 * est1.cost_eur) < 0.001

    def test_cost_estimate_to_dict(self):
        est = self.manager.estimate_cost(Cluster.MELUXINA, num_gpus=4, wall_time_hours=2)
        d = est.to_dict()
        assert d["cluster"] == "meluxina"
        assert "savings_vs_aws_pct" in d
        assert "savings_vs_gcp_pct" in d


class TestSLURMScript:
    def test_script_rendering(self):
        config = ClusterConfig(
            cluster=Cluster.LUMI,
            host="lumi.csc.fi",
            username="testuser",
            ssh_key_path="~/.ssh/id_rsa",
            partition="standard-g",
            account="project_123",
        )
        client = SLURMClient(config)
        spec = JobSpec(
            job_name="lora-train-hr",
            script_path="train.py",
            num_gpus=4,
            num_nodes=1,
            wall_time="12:00:00",
            memory_gb=128,
            environment_vars={"HF_HOME": "/scratch/hf"},
            modules=["pytorch/2.2"],
        )
        script = client._render_script(spec)
        assert "#SBATCH --job-name=lora-train-hr" in script
        assert "#SBATCH --gpus-per-node=4" in script
        assert "#SBATCH --time=12:00:00" in script
        assert "#SBATCH --partition=standard-g" in script
        assert "module load pytorch/2.2" in script
        assert "export HF_HOME=/scratch/hf" in script
        assert "srun python train.py" in script

    @pytest.mark.asyncio
    async def test_submit_job_rest(self):
        config = ClusterConfig(
            cluster=Cluster.MARE_NOSTRUM,
            host="mn1.bsc.es",
            username="user",
            ssh_key_path="~/.ssh/id_rsa",
            partition="acc",
            account="bsc123",
        )
        client = SLURMClient(config)
        spec = JobSpec(job_name="test", script_path="train.py")

        # Mock the full aiohttp session + response chain
        mock_resp = MagicMock()
        mock_resp.json = AsyncMock(return_value={"job_id": 42})
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_cm)
        mock_session.closed = False

        with patch.object(client, "_get_session", AsyncMock(return_value=mock_session)):
            job_id = await client.submit_job(spec)

        assert job_id == "42"

    @pytest.mark.asyncio
    async def test_eurohpc_manager_submit(self):
        manager = EuroHPCManager()
        config = ClusterConfig(
            cluster=Cluster.MELUXINA,
            host="login.lxp.lu",
            username="user",
            ssh_key_path="~/.ssh/id_rsa",
            partition="gpu",
            account="lxp_proj",
        )
        manager.register_cluster(config)
        manager._clients[Cluster.MELUXINA].submit_job = AsyncMock(return_value="99")

        spec = JobSpec(job_name="augment-mt", script_path="augment.py", num_gpus=2)
        status = await manager.submit_training_job(Cluster.MELUXINA, spec)
        assert status.job_id == "99"
        assert status.state == "PENDING"
        assert status.cluster == Cluster.MELUXINA

    @pytest.mark.asyncio
    async def test_poll_job_updates_state(self):
        manager = EuroHPCManager()
        config = ClusterConfig(
            cluster=Cluster.LUMI,
            host="lumi.csc.fi",
            username="u",
            ssh_key_path="k",
            partition="p",
            account="a",
        )
        manager.register_cluster(config)
        manager._clients[Cluster.LUMI].get_job_status = AsyncMock(
            return_value={"job_state": "RUNNING"}
        )
        manager._jobs["123"] = JobStatus(
            job_id="123", cluster=Cluster.LUMI,
            state="PENDING", submitted_at=datetime.utcnow()
        )
        status = await manager.poll_job("123")
        assert status.state == "RUNNING"
        assert status.started_at is not None


# ---------------------------------------------------------------------------
# 15.3 Transfer Learning Tests
# ---------------------------------------------------------------------------

class TestLanguageSimilarityMap:
    def test_croatian_sources(self):
        sources = get_source_languages("hr")
        assert "sr" in sources  # Serbian is closest
        assert len(sources) <= 3

    def test_maltese_sources(self):
        sources = get_source_languages("mt")
        assert "ar" in sources  # Arabic component
        assert "it" in sources  # Italian component

    def test_estonian_sources(self):
        sources = get_source_languages("et")
        assert "fi" in sources  # Finnish is closest

    def test_unknown_language_defaults_to_english(self):
        sources = get_source_languages("xx")
        assert sources == ["en"]

    def test_all_target_languages_have_sources(self):
        for lang in LANGUAGE_SIMILARITY_MAP:
            sources = get_source_languages(lang)
            assert len(sources) >= 1

    def test_language_names_coverage(self):
        for lang in LANGUAGE_SIMILARITY_MAP:
            assert lang in LANGUAGE_NAMES, f"Missing name for {lang}"


class TestTransferConfig:
    def test_defaults(self):
        cfg = TransferConfig(source_language="sr", target_language="hr")
        assert cfg.lora_r == 16
        assert cfg.freeze_layers == 12
        assert cfg.ewc_lambda == 5000.0

    def test_gemma_default_model(self):
        cfg = TransferConfig(source_language="fi", target_language="et")
        assert "gemma" in cfg.model_name.lower()


class TestCrossLingualTransfer:
    def test_get_source_languages(self):
        cfg = TransferConfig(source_language="sr", target_language="hr")
        transfer = CrossLingualTransfer(cfg)
        sources = transfer.get_source_languages()
        assert "sr" in sources

    def test_training_args_structure(self):
        cfg = TransferConfig(source_language="fi", target_language="et")
        transfer = CrossLingualTransfer(cfg)
        args = transfer.build_transfer_training_args()
        assert "learning_rate" in args
        assert "num_train_epochs" in args
        assert args["fp16"] is True

    def test_ewc_loss_without_fisher_returns_zero(self):
        cfg = TransferConfig(source_language="sr", target_language="hr")
        transfer = CrossLingualTransfer(cfg)
        loss = transfer.ewc_loss(MagicMock())
        assert loss == 0.0

    def test_freeze_layers_handles_missing_attr(self):
        cfg = TransferConfig(source_language="sr", target_language="hr")
        transfer = CrossLingualTransfer(cfg)
        # Should not raise even with a mock model
        transfer.freeze_base_layers(MagicMock(spec=[]))


class TestFewShotPrompt:
    def test_render_with_examples(self):
        prompt = FewShotPrompt(
            task_description="Translate to Croatian:",
            target_language="hr",
            examples=[
                FewShotExample("Hello", "Zdravo", "en"),
                FewShotExample("Thank you", "Hvala", "en"),
            ],
        )
        rendered = prompt.render("Good morning")
        assert "Zdravo" in rendered
        assert "Hvala" in rendered
        assert "Good morning" in rendered
        assert "Output:" in rendered

    def test_render_no_examples(self):
        prompt = FewShotPrompt(task_description="Classify:", target_language="mt")
        rendered = prompt.render("test input")
        assert "test input" in rendered


class TestZeroShotClassifier:
    def test_fallback_uniform_distribution(self):
        clf = ZeroShotClassifier()
        clf._model = None  # Force fallback
        # Patch sentence_transformers import to fail
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            scores = clf.classify("test", ["cat1", "cat2", "cat3"])
        assert len(scores) == 3
        for v in scores.values():
            assert abs(v - 1 / 3) < 0.01

    def test_returns_all_labels(self):
        clf = ZeroShotClassifier()
        clf._model = None
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            labels = ["billing", "support", "sales"]
            scores = clf.classify("I need help", labels)
        assert set(scores.keys()) == set(labels)


# ---------------------------------------------------------------------------
# 15.4 Data Augmentation Tests
# ---------------------------------------------------------------------------

class TestDataAugmentor:
    def setup_method(self):
        self.aug = DataAugmentor()

    def test_validate_quality_filters_short(self):
        texts = ["hi", "this is a valid sentence with enough words", "ok"]
        valid = self.aug.validate_quality(texts, min_length=5)
        assert "hi" not in valid  # 2 chars < 5
        assert "ok" not in valid  # 2 chars < 5
        assert "this is a valid sentence with enough words" in valid

    def test_validate_quality_deduplication(self):
        texts = ["same sentence here"] * 5 + ["different sentence here"]
        valid = self.aug.validate_quality(texts, dedup=True)
        assert valid.count("same sentence here") == 1

    def test_validate_quality_no_dedup(self):
        texts = ["same sentence here"] * 3
        valid = self.aug.validate_quality(texts, dedup=False)
        assert len(valid) == 3

    def test_back_translate_fallback_when_no_pipeline(self):
        texts = ["Zdravo, kako si?", "Hvala lijepa."]
        # No translation model available in test env → returns originals
        result = self.aug.back_translate(texts, "hr", "en")
        assert len(result) == len(texts)

    def test_paraphrase_fallback(self):
        texts = ["The quick brown fox"]
        result = self.aug.paraphrase(texts, model_name="nonexistent/model")
        assert result == texts  # Falls back to originals

    def test_augment_dataset_returns_at_least_originals(self):
        texts = ["Dobro jutro", "Kako si", "Hvala"]
        result = self.aug.augment_dataset(
            texts, language="hr",
            back_translate=False, paraphrase=False, synthetic_n=0
        )
        # At minimum the originals should be present
        for t in texts:
            assert t in result

    def test_synthetic_generation_fallback(self):
        result = self.aug.generate_synthetic(
            ["test"], language="hr", n_samples=5,
            llm_model="nonexistent/model"
        )
        assert result == []  # Falls back gracefully

    def test_augment_pipeline_no_crash(self):
        texts = ["Labas rytas", "Labas vakaras"]
        # Should not raise even if all augmentation methods fall back
        result = self.aug.augment_dataset(
            texts, language="lt",
            back_translate=True, paraphrase=True, synthetic_n=0
        )
        assert isinstance(result, list)
        assert len(result) >= len(texts)
