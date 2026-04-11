"""
Analytics System Tests (Task 22.8)
Tests for metric calculation, journey analysis, predictive models, and BI integration.
"""

import json
import pytest
from datetime import datetime, timedelta

from src.analytics import (
    ConversationAnalyticsEngine, ConversationMetrics, AnalyticsEvent, EventType,
    PredictiveAnalytics, AnomalyAlert,
    BIExporter, ExportFormat, RealtimeDashboard, AlertSeverity,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(event_type: EventType, cid: str = "c1", tenant: str = "t1",
           channel: str = "web_chat", data: dict = None, ts: datetime = None) -> AnalyticsEvent:
    import uuid
    return AnalyticsEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        conversation_id=cid,
        tenant_id=tenant,
        channel=channel,
        timestamp=ts or datetime.utcnow(),
        data=data or {},
    )


_seed_counter = 0

def _seed_engine(engine: ConversationAnalyticsEngine, n: int = 5,
                 completed: bool = True, converted: bool = False) -> None:
    global _seed_counter
    for i in range(n):
        cid = f"c{_seed_counter}"
        _seed_counter += 1
        engine.ingest(_event(EventType.CONVERSATION_START, cid))
        engine.ingest(_event(EventType.MESSAGE_RECEIVED, cid))
        engine.ingest(_event(EventType.MESSAGE_RECEIVED, cid))
        if converted:
            engine.ingest(_event(EventType.CONVERSION, cid))
        engine.ingest(_event(EventType.CONVERSATION_END, cid,
                             data={"completed": completed}))


# ---------------------------------------------------------------------------
# 22.1 Conversation Analytics Engine
# ---------------------------------------------------------------------------

class TestConversationAnalyticsEngine:
    def test_ingest_start_creates_metrics(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1"))
        assert "c1" in engine._conversations

    def test_turn_count_increments(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1"))
        engine.ingest(_event(EventType.MESSAGE_RECEIVED, "c1"))
        engine.ingest(_event(EventType.MESSAGE_RECEIVED, "c1"))
        assert engine._conversations["c1"].turn_count == 2

    def test_completion_tracked(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1"))
        engine.ingest(_event(EventType.CONVERSATION_END, "c1", data={"completed": True}))
        assert engine._conversations["c1"].completed is True

    def test_conversion_tracked(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1"))
        engine.ingest(_event(EventType.CONVERSION, "c1"))
        assert engine._conversations["c1"].converted is True

    def test_intent_tracked(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1"))
        engine.ingest(_event(EventType.INTENT_MATCHED, "c1", data={"intent": "billing"}))
        assert "billing" in engine._conversations["c1"].intents

    def test_satisfaction_tracked(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1"))
        engine.ingest(_event(EventType.SATISFACTION_RATED, "c1", data={"score": 4.5}))
        assert engine._conversations["c1"].satisfaction_score == 4.5

    def test_volume_metrics_completion_rate(self):
        engine = ConversationAnalyticsEngine()
        _seed_engine(engine, n=4, completed=True)
        _seed_engine(engine, n=1, completed=False)
        metrics = engine.get_volume_metrics("t1")
        assert metrics["total_conversations"] == 5
        assert metrics["completion_rate"] == pytest.approx(0.8)

    def test_volume_metrics_conversion_rate(self):
        engine = ConversationAnalyticsEngine()
        _seed_engine(engine, n=3, completed=True, converted=True)
        _seed_engine(engine, n=2, completed=True, converted=False)
        metrics = engine.get_volume_metrics("t1")
        assert metrics["conversion_rate"] == pytest.approx(0.6)

    def test_intent_analytics(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1"))
        engine.ingest(_event(EventType.INTENT_MATCHED, "c1", data={"intent": "billing"}))
        engine.ingest(_event(EventType.CONVERSATION_START, "c2"))
        engine.ingest(_event(EventType.INTENT_MATCHED, "c2", data={"intent": "billing"}))
        engine.ingest(_event(EventType.CONVERSATION_START, "c3"))
        engine.ingest(_event(EventType.INTENT_MATCHED, "c3", data={"intent": "support"}))
        intents = engine.get_intent_analytics("t1")
        assert intents["billing"] == 2
        assert intents["support"] == 1

    def test_channel_filter(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1", channel="sms"))
        engine.ingest(_event(EventType.CONVERSATION_START, "c2", channel="web_chat"))
        metrics = engine.get_volume_metrics("t1", channel="sms")
        assert metrics["total_conversations"] == 1


# ---------------------------------------------------------------------------
# 22.2 Customer Journey Analysis
# ---------------------------------------------------------------------------

class TestCustomerJourneyAnalysis:
    def test_drop_off_analysis(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1"))
        engine.ingest(_event(EventType.CONVERSATION_END, "c1", data={"completed": False}))
        engine._conversations["c1"].drop_off_node = "node-faq"
        drop_offs = engine.get_drop_off_analysis("t1")
        assert "node-faq" in drop_offs

    def test_conversion_funnel(self):
        engine = ConversationAnalyticsEngine()
        for i in range(5):
            cid = f"c{i}"
            engine.ingest(_event(EventType.CONVERSATION_START, cid))
            engine._conversations[cid].node_path = ["start", "intent", "response"]
        for i in range(3):
            engine._conversations[f"c{i}"].node_path.append("checkout")

        funnel = engine.get_conversion_funnel("t1", ["start", "intent", "checkout"])
        assert funnel[0]["count"] == 5
        assert funnel[2]["count"] == 3

    def test_cohort_analysis(self):
        engine = ConversationAnalyticsEngine()
        now = datetime.utcnow()
        for i in range(3):
            cid = f"c{i}"
            engine.ingest(_event(EventType.CONVERSATION_START, cid, ts=now))
            engine.ingest(_event(EventType.CONVERSATION_END, cid, data={"completed": True}))
        cohorts = engine.get_cohort_analysis("t1")
        assert len(cohorts) >= 1
        assert cohorts[0]["completion_rate"] == 1.0

    def test_journey_paths(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1"))
        engine._conversations["c1"].node_path = ["start", "intent", "response"]
        paths = engine.get_journey_paths("t1")
        assert len(paths) == 1
        assert paths[0]["node_path"] == ["start", "intent", "response"]


# ---------------------------------------------------------------------------
# 22.3 Sentiment Analytics
# ---------------------------------------------------------------------------

class TestSentimentAnalytics:
    def test_record_sentiment(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1"))
        engine.record_sentiment("c1", 0.8)
        engine.record_sentiment("c1", 0.6)
        assert engine._conversations["c1"].avg_sentiment == pytest.approx(0.7)

    def test_sentiment_trends(self):
        engine = ConversationAnalyticsEngine()
        now = datetime.utcnow()
        for i in range(3):
            cid = f"c{i}"
            engine.ingest(_event(EventType.CONVERSATION_START, cid, ts=now))
            engine.record_sentiment(cid, 0.5 + i * 0.1)
        trends = engine.get_sentiment_trends("t1")
        assert len(trends) >= 1
        assert "avg_sentiment" in trends[0]

    def test_sentiment_by_channel(self):
        engine = ConversationAnalyticsEngine()
        engine.ingest(_event(EventType.CONVERSATION_START, "c1", channel="sms"))
        engine.record_sentiment("c1", 0.8)
        engine.ingest(_event(EventType.CONVERSATION_START, "c2", channel="web_chat"))
        engine.record_sentiment("c2", 0.3)
        by_channel = engine.get_sentiment_by_channel("t1")
        assert "sms" in by_channel
        assert "web_chat" in by_channel
        assert by_channel["sms"] > by_channel["web_chat"]


# ---------------------------------------------------------------------------
# 22.4 Business Outcome / KPI Tracking
# ---------------------------------------------------------------------------

class TestKPITracking:
    def test_track_and_summarize_kpi(self):
        engine = ConversationAnalyticsEngine()
        engine.track_kpi("t1", "revenue_eur", 150.0)
        engine.track_kpi("t1", "revenue_eur", 200.0)
        engine.track_kpi("t1", "appointments_booked", 1.0)
        summary = engine.get_kpi_summary("t1")
        assert summary["revenue_eur"]["total"] == pytest.approx(350.0)
        assert summary["revenue_eur"]["count"] == 2
        assert "appointments_booked" in summary

    def test_kpi_avg(self):
        engine = ConversationAnalyticsEngine()
        engine.track_kpi("t1", "csat", 4.0)
        engine.track_kpi("t1", "csat", 5.0)
        summary = engine.get_kpi_summary("t1")
        assert summary["csat"]["avg"] == pytest.approx(4.5)


# ---------------------------------------------------------------------------
# 22.5 Predictive Analytics
# ---------------------------------------------------------------------------

class TestPredictiveAnalytics:
    def test_churn_high_risk(self):
        pa = PredictiveAnalytics()
        pred = pa.predict_churn(
            user_id="u1", tenant_id="t1",
            days_since_last_login=45,
            satisfaction_avg=2.5,
            open_tickets=5,
            feature_adoption_pct=10,
            conversations_last_30d=0,
        )
        assert pred.risk_level == "high"
        assert pred.churn_probability >= 0.6
        assert len(pred.factors) > 0

    def test_churn_low_risk(self):
        pa = PredictiveAnalytics()
        pred = pa.predict_churn(
            user_id="u2", tenant_id="t1",
            days_since_last_login=2,
            satisfaction_avg=4.5,
            open_tickets=0,
            feature_adoption_pct=80,
            conversations_last_30d=20,
        )
        assert pred.risk_level == "low"
        assert pred.churn_probability < 0.3

    def test_success_score_range(self):
        pa = PredictiveAnalytics()
        score = pa.score_conversation_success(
            turn_count=5, avg_sentiment=0.5,
            intent_match_rate=0.9, channel="web_chat",
        )
        assert 0.0 <= score <= 1.0

    def test_success_score_high_sentiment(self):
        pa = PredictiveAnalytics()
        high = pa.score_conversation_success(5, 0.8, 0.9, "web_chat")
        low = pa.score_conversation_success(5, -0.5, 0.3, "sms")
        assert high > low

    def test_intervention_handoff(self):
        pa = PredictiveAnalytics()
        result = pa.detect_intervention_point(
            turn_count=8,
            sentiment_trend=[-0.5, -0.6, -0.7],
            time_in_conversation_s=100,
        )
        assert result == "handoff_to_agent"

    def test_intervention_none_for_good_conversation(self):
        pa = PredictiveAnalytics()
        result = pa.detect_intervention_point(
            turn_count=3,
            sentiment_trend=[0.5, 0.6, 0.7],
            time_in_conversation_s=60,
        )
        assert result is None

    def test_capacity_forecast_trend(self):
        pa = PredictiveAnalytics()
        history = [100, 110, 120, 130, 140]
        forecast = pa.forecast_capacity(history, forecast_periods=3)
        assert len(forecast) == 3
        assert forecast[0] >= 140  # upward trend

    def test_capacity_forecast_flat(self):
        pa = PredictiveAnalytics()
        history = [100, 100, 100, 100, 100]
        forecast = pa.forecast_capacity(history, forecast_periods=3)
        assert all(f == 100 for f in forecast)

    def test_anomaly_detection_normal(self):
        pa = PredictiveAnalytics()
        for v in [10, 11, 10, 9, 10, 11, 10]:
            alert = pa.record_metric("error_rate", v)
        assert alert is None

    def test_anomaly_detection_spike(self):
        pa = PredictiveAnalytics()
        for v in [9, 11, 10, 9, 11, 10, 9]:
            pa.record_metric("error_rate", v)
        alert = pa.record_metric("error_rate", 100.0)
        assert alert is not None
        assert alert.z_score > 3.0

    def test_anomaly_severity_critical(self):
        pa = PredictiveAnalytics()
        for v in [1.0, 1.1, 0.9, 1.0, 1.1, 0.9, 1.0]:
            pa.record_metric("latency", v)
        alert = pa.record_metric("latency", 1000.0)
        assert alert is not None
        assert alert.severity == "critical"


# ---------------------------------------------------------------------------
# 22.6 BI Tool Integration
# ---------------------------------------------------------------------------

class TestBIExporter:
    def _sample_data(self) -> list:
        return [
            {"conversation_id": "c1", "channel": "sms", "turns": 3, "completed": True},
            {"conversation_id": "c2", "channel": "web_chat", "turns": 5, "completed": False},
        ]

    def test_export_csv(self):
        exporter = BIExporter()
        export = exporter.export_conversations(self._sample_data(), ExportFormat.CSV, "t1")
        assert export.row_count == 2
        assert "conversation_id" in export.content
        assert "c1" in export.content

    def test_export_json(self):
        exporter = BIExporter()
        export = exporter.export_conversations(self._sample_data(), ExportFormat.JSON, "t1")
        data = json.loads(export.content)
        assert len(data) == 2

    def test_export_empty(self):
        exporter = BIExporter()
        export = exporter.export_conversations([], ExportFormat.CSV, "t1")
        assert export.row_count == 0

    def test_tableau_extract(self):
        exporter = BIExporter()
        result = exporter.get_tableau_extract(self._sample_data())
        assert result["type"] == "tableau_extract"
        assert "schema" in result
        assert result["row_count"] == 2

    def test_power_bi_dataset(self):
        exporter = BIExporter()
        result = exporter.get_power_bi_dataset(self._sample_data(), "Test Dataset")
        assert result["name"] == "Test Dataset"
        assert len(result["tables"]) == 1
        assert result["tables"][0]["name"] == "Conversations"

    def test_looker_explore(self):
        exporter = BIExporter()
        result = exporter.get_looker_explore(self._sample_data())
        assert result["model"] == "voiquyr"
        assert "fields" in result
        assert len(result["data"]) == 2


# ---------------------------------------------------------------------------
# 22.7 Real-time Dashboard
# ---------------------------------------------------------------------------

class TestRealtimeDashboard:
    def test_live_conversation_count(self):
        dash = RealtimeDashboard()
        dash.conversation_started("c1", "sms", "t1")
        dash.conversation_started("c2", "web_chat", "t1")
        assert dash.get_live_count() == 2

    def test_live_count_by_tenant(self):
        dash = RealtimeDashboard()
        dash.conversation_started("c1", "sms", "t1")
        dash.conversation_started("c2", "sms", "t2")
        assert dash.get_live_count("t1") == 1

    def test_conversation_ended_decrements(self):
        dash = RealtimeDashboard()
        dash.conversation_started("c1", "sms", "t1")
        dash.conversation_ended("c1")
        assert dash.get_live_count() == 0

    def test_queue_update(self):
        dash = RealtimeDashboard()
        dash.update_queue("sms", depth=10, avg_wait=30.0)
        assert dash._queue_metrics["sms"].depth == 10

    def test_queue_alert_fired(self):
        dash = RealtimeDashboard()
        dash.set_threshold("queue_depth", 5)
        dash.update_queue("sms", depth=10)
        alerts = dash.get_active_alerts()
        assert len(alerts) >= 1
        assert any(a.metric == "queue_depth" for a in alerts)

    def test_alert_deduplication(self):
        dash = RealtimeDashboard()
        dash.set_threshold("queue_depth", 5)
        dash.update_queue("sms", depth=10)
        dash.update_queue("sms", depth=11)
        alerts = [a for a in dash.get_active_alerts() if a.metric == "queue_depth"]
        assert len(alerts) == 1

    def test_resolve_alert(self):
        dash = RealtimeDashboard()
        dash.set_threshold("queue_depth", 5)
        dash.update_queue("sms", depth=10)
        alert = dash.get_active_alerts()[0]
        assert dash.resolve_alert(alert.alert_id) is True
        assert len(dash.get_active_alerts()) == 0

    def test_agent_summary(self):
        dash = RealtimeDashboard()
        dash.update_agent("a1", "available", 0)
        dash.update_agent("a2", "busy", 2)
        dash.update_agent("a3", "offline", 0)
        summary = dash.get_agent_summary()
        assert summary["available"] == 1
        assert summary["busy"] == 1
        assert summary["offline"] == 1

    def test_system_health_alert(self):
        dash = RealtimeDashboard()
        dash.update_health("cpu_pct", 95.0)
        alerts = dash.get_active_alerts()
        assert any(a.metric == "cpu_pct" for a in alerts)

    def test_dashboard_snapshot(self):
        dash = RealtimeDashboard()
        dash.conversation_started("c1", "sms", "t1")
        dash.update_queue("sms", 5)
        dash.update_agent("a1", "available", 0)
        snap = dash.get_snapshot()
        assert snap["live_conversations"] == 1
        assert "queues" in snap
        assert "agents" in snap
        assert "snapshot_at" in snap
