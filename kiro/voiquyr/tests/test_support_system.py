"""
Support System Tests (Task 19.6)
Tests for ticket routing, SLA tracking, escalation, and multi-language support.
"""

import pytest
from datetime import datetime, timedelta

from src.support import (
    TicketingSystem, Ticket, SupportAgent, TicketPriority, TicketStatus, TicketChannel,
    SLA_RESPONSE_MINUTES, SLA_RESOLUTION_MINUTES,
    SLAManager, SLADefinition, UPTIME_TARGET,
    AccountManagementSystem, AccountManager, AccountHealth, AccountTier,
    HealthScore, EscalationLevel,
    OnboardingSystem, OnboardingPlan, TrainingSession, OnboardingStage, TrainingStatus,
    RegionalSupportRouter, RegionalQueue, SUPPORTED_LANGUAGES,
)


# ---------------------------------------------------------------------------
# 19.1 Ticketing System
# ---------------------------------------------------------------------------

class TestTicketingSystem:
    def _system_with_agent(self) -> TicketingSystem:
        ts = TicketingSystem()
        ts.register_agent(SupportAgent("a1", "Alice", "alice@example.com",
                                       languages=["en", "fr"]))
        return ts

    def test_create_ticket(self):
        ts = self._system_with_agent()
        t = ts.create_ticket("Login issue", "Can't log in", TicketPriority.P2)
        assert t.ticket_id is not None
        assert t.priority == TicketPriority.P2
        assert t.status == TicketStatus.OPEN

    def test_auto_assign_to_agent(self):
        ts = self._system_with_agent()
        t = ts.create_ticket("Issue", "Desc", TicketPriority.P3)
        assert t.assigned_agent_id == "a1"

    def test_no_agent_ticket_unassigned(self):
        ts = TicketingSystem()
        t = ts.create_ticket("Issue", "Desc")
        assert t.assigned_agent_id is None

    def test_update_status_resolved(self):
        ts = self._system_with_agent()
        t = ts.create_ticket("Issue", "Desc")
        ts.update_status(t.ticket_id, TicketStatus.RESOLVED)
        assert t.status == TicketStatus.RESOLVED
        assert t.resolved_at is not None

    def test_update_status_decrements_agent_count(self):
        ts = self._system_with_agent()
        t = ts.create_ticket("Issue", "Desc")
        assert ts._agents["a1"].active_tickets == 1
        ts.update_status(t.ticket_id, TicketStatus.RESOLVED)
        assert ts._agents["a1"].active_tickets == 0

    def test_add_comment_sets_first_response(self):
        ts = self._system_with_agent()
        t = ts.create_ticket("Issue", "Desc")
        assert t.first_response_at is None
        t.add_comment("agent", "Working on it")
        assert t.first_response_at is not None

    def test_internal_comment_does_not_set_first_response(self):
        ts = self._system_with_agent()
        t = ts.create_ticket("Issue", "Desc")
        t.add_comment("agent", "Internal note", internal=True)
        assert t.first_response_at is None

    def test_sla_deadlines(self):
        t = Ticket(priority=TicketPriority.P1)
        assert t.response_deadline == t.created_at + timedelta(minutes=15)
        assert t.resolution_deadline == t.created_at + timedelta(minutes=60)

    def test_sla_not_breached_fresh_ticket(self):
        t = Ticket(priority=TicketPriority.P4)
        assert t.response_breached is False
        assert t.resolution_breached is False

    def test_sla_response_breached(self):
        t = Ticket(priority=TicketPriority.P1)
        t.created_at = datetime.utcnow() - timedelta(minutes=30)
        assert t.response_breached is True

    def test_sla_resolution_breached(self):
        t = Ticket(priority=TicketPriority.P1)
        t.created_at = datetime.utcnow() - timedelta(minutes=120)
        assert t.resolution_breached is True

    def test_get_breached_tickets(self):
        ts = TicketingSystem()
        t = ts.create_ticket("Old issue", "Desc", TicketPriority.P1)
        t.created_at = datetime.utcnow() - timedelta(hours=2)
        breached = ts.get_breached_tickets()
        assert t in breached

    def test_agent_dashboard(self):
        ts = self._system_with_agent()
        ts.create_ticket("A", "D", TicketPriority.P1)
        ts.create_ticket("B", "D", TicketPriority.P2)
        dash = ts.get_agent_dashboard("a1")
        assert dash["total_assigned"] == 2
        assert dash["by_priority"]["P1"] == 1

    def test_queue_stats(self):
        ts = self._system_with_agent()
        ts.create_ticket("A", "D", TicketPriority.P1)
        ts.create_ticket("B", "D", TicketPriority.P3)
        stats = ts.get_queue_stats()
        assert stats["total_open"] == 2

    def test_least_loaded_assignment(self):
        ts = TicketingSystem()
        ts.register_agent(SupportAgent("a1", "Alice", "a@e.com", max_tickets=5))
        ts.register_agent(SupportAgent("a2", "Bob", "b@e.com", max_tickets=5))
        t1 = ts.create_ticket("T1", "D")
        t2 = ts.create_ticket("T2", "D")
        # Both agents should get tickets (round-robin via least-loaded)
        assigned = {t1.assigned_agent_id, t2.assigned_agent_id}
        assert len(assigned) == 2

    def test_all_channels_supported(self):
        ts = TicketingSystem()
        for ch in TicketChannel:
            t = ts.create_ticket("T", "D", channel=ch)
            assert t.channel == ch

    def test_ticket_to_dict(self):
        t = Ticket(subject="Test", priority=TicketPriority.P2)
        d = t.to_dict()
        assert d["priority"] == "P2"
        assert "response_deadline" in d
        assert "resolution_breached" in d


# ---------------------------------------------------------------------------
# 19.2 SLA Management
# ---------------------------------------------------------------------------

class TestSLAManager:
    def _sla(self) -> SLADefinition:
        return SLADefinition(
            sla_id="enterprise",
            name="Enterprise SLA",
            monthly_fee_eur=5000.0,
            penalty_pct_per_hour=5.0,
        )

    def test_uptime_target_constant(self):
        assert UPTIME_TARGET == 0.999

    def test_record_uptime_met(self):
        mgr = SLAManager()
        mgr.register_sla(self._sla())
        mgr.assign_sla("t1", "enterprise")
        now = datetime.utcnow()
        record = mgr.record_uptime("t1", now - timedelta(days=30), now, downtime_minutes=30.0)
        assert record.sla_met is True
        assert record.uptime_pct > 0.999

    def test_record_uptime_breached(self):
        mgr = SLAManager()
        mgr.register_sla(self._sla())
        mgr.assign_sla("t1", "enterprise")
        now = datetime.utcnow()
        record = mgr.record_uptime("t1", now - timedelta(days=30), now, downtime_minutes=120.0)
        assert record.sla_met is False
        breaches = mgr.get_breach_report("t1")
        assert len(breaches) == 1
        assert breaches[0]["breach_type"] == "uptime"

    def test_penalty_calculated(self):
        mgr = SLAManager()
        mgr.register_sla(self._sla())
        mgr.assign_sla("t1", "enterprise")
        now = datetime.utcnow()
        mgr.record_uptime("t1", now - timedelta(days=30), now, downtime_minutes=120.0)
        total = mgr.get_total_penalties("t1")
        assert total > 0

    def test_ticket_response_breach(self):
        mgr = SLAManager()
        mgr.register_sla(self._sla())
        mgr.assign_sla("t1", "enterprise")
        t = Ticket(priority=TicketPriority.P1, tenant_id="t1")
        t.created_at = datetime.utcnow() - timedelta(minutes=30)
        t.first_response_at = datetime.utcnow()
        breaches = mgr.check_ticket_sla(t)
        assert any(b.breach_type == "response" for b in breaches)

    def test_no_breach_for_timely_response(self):
        mgr = SLAManager()
        t = Ticket(priority=TicketPriority.P3, tenant_id="t1")
        t.first_response_at = t.created_at + timedelta(minutes=10)
        t.resolved_at = t.created_at + timedelta(minutes=60)
        t.status = TicketStatus.RESOLVED
        breaches = mgr.check_ticket_sla(t)
        assert breaches == []

    def test_uptime_report_structure(self):
        mgr = SLAManager()
        now = datetime.utcnow()
        mgr.record_uptime("t1", now - timedelta(days=30), now, 20.0)
        report = mgr.get_uptime_report("t1")
        assert "overall_uptime_pct" in report
        assert "sla_met" in report
        assert report["sla_met"] is True

    def test_uptime_record_pct(self):
        from src.support.sla import UptimeRecord
        now = datetime.utcnow()
        r = UptimeRecord(now - timedelta(hours=100), now, 6000, 6)
        assert abs(r.uptime_pct - 0.999) < 0.0001


# ---------------------------------------------------------------------------
# 19.3 Account Management
# ---------------------------------------------------------------------------

class TestAccountManagement:
    def _system(self) -> AccountManagementSystem:
        ams = AccountManagementSystem()
        ams.register_manager(AccountManager("tam1", "Tom TAM", "tam@e.com", role="TAM"))
        ams.register_manager(AccountManager("csm1", "Carol CSM", "csm@e.com", role="CSM"))
        return ams

    def test_assign_managers(self):
        ams = self._system()
        assignment = ams.assign_managers("tenant-1", tam_id="tam1", csm_id="csm1")
        assert assignment["TAM"] == "tam1"
        assert assignment["CSM"] == "csm1"

    def test_auto_assign_enterprise(self):
        ams = self._system()
        assignment = ams.auto_assign("tenant-2", AccountTier.ENTERPRISE)
        assert "TAM" in assignment
        assert "CSM" in assignment

    def test_auto_assign_starter_skipped(self):
        ams = self._system()
        assignment = ams.auto_assign("tenant-3", AccountTier.STARTER)
        assert assignment == {}

    def test_health_score_healthy(self):
        ams = self._system()
        h = AccountHealth(tenant_id="t1", uptime_pct=100.0, open_p1_tickets=0)
        ams.update_health(h)
        assert h.health_status == HealthScore.HEALTHY
        assert h.score >= 80

    def test_health_score_critical(self):
        h = AccountHealth(tenant_id="t1", uptime_pct=95.0, open_p1_tickets=3)
        h.recalculate()
        assert h.health_status in (HealthScore.AT_RISK, HealthScore.CRITICAL)

    def test_get_at_risk_accounts(self):
        ams = self._system()
        h = AccountHealth(tenant_id="t1", uptime_pct=95.0, open_p1_tickets=3)
        ams.update_health(h)
        at_risk = ams.get_at_risk_accounts()
        assert any(a.tenant_id == "t1" for a in at_risk)

    def test_escalation_created(self):
        ams = self._system()
        ams.assign_managers("t1", tam_id="tam1")
        e = ams.escalate("t1", EscalationLevel.L2, "P1 ticket unresolved", "agent1")
        assert e.escalation_id is not None
        assert e.level == EscalationLevel.L2
        assert e.resolved_at is None

    def test_escalation_resolved(self):
        ams = self._system()
        e = ams.escalate("t1", EscalationLevel.L3, "Critical issue", "agent1")
        result = ams.resolve_escalation(e.escalation_id)
        assert result is True
        assert e.resolved_at is not None

    def test_dashboard_structure(self):
        ams = self._system()
        dash = ams.get_dashboard()
        assert "total_accounts" in dash
        assert "healthy" in dash
        assert "open_escalations" in dash

    def test_exec_escalation_target(self):
        ams = self._system()
        e = ams.escalate("t1", EscalationLevel.EXEC, "Major outage", "ceo")
        assert e.escalated_to == "executive_team"


# ---------------------------------------------------------------------------
# 19.4 Onboarding & Training
# ---------------------------------------------------------------------------

class TestOnboardingSystem:
    def test_create_plan(self):
        sys = OnboardingSystem()
        plan = sys.create_plan("t1", tier="enterprise", specialist="Jane")
        assert plan.stage == OnboardingStage.KICKOFF
        assert plan.completion_pct() == 0.0

    def test_advance_stage(self):
        sys = OnboardingSystem()
        plan = sys.create_plan("t1")
        plan.advance_stage()
        assert plan.stage == OnboardingStage.SETUP
        assert "kickoff" in plan.completed_stages

    def test_completion_pct_increases(self):
        sys = OnboardingSystem()
        plan = sys.create_plan("t1")
        plan.advance_stage()
        plan.advance_stage()
        assert plan.completion_pct() > 0

    def test_schedule_training(self):
        sys = OnboardingSystem()
        sys.create_plan("t1")
        session = TrainingSession(tenant_id="t1", title="Platform Intro",
                                  scheduled_at=datetime.utcnow())
        sys.schedule_training(session)
        plan = sys.get_plan("t1")
        assert len(plan.training_sessions) == 1

    def test_complete_training(self):
        sys = OnboardingSystem()
        sys.create_plan("t1")
        session = TrainingSession(tenant_id="t1", title="Advanced")
        sys.schedule_training(session)
        result = sys.complete_training(session.session_id, "https://rec.example.com/vid")
        assert result is True
        assert session.status == TrainingStatus.COMPLETED

    def test_issue_certification_pass(self):
        sys = OnboardingSystem()
        cert = sys.issue_certification("user1", "t1", "VoiQyr Admin", score=85.0)
        assert cert is not None
        assert cert.score == 85.0

    def test_issue_certification_fail(self):
        sys = OnboardingSystem()
        cert = sys.issue_certification("user1", "t1", "VoiQyr Admin", score=60.0)
        assert cert is None

    def test_success_metrics(self):
        sys = OnboardingSystem()
        sys.create_plan("t1")
        session = TrainingSession(tenant_id="t1", title="T1")
        sys.schedule_training(session)
        sys.complete_training(session.session_id)
        sys.issue_certification("u1", "t1", "Admin", 90.0)
        metrics = sys.get_success_metrics("t1")
        assert metrics["training_sessions_completed"] == 1
        assert metrics["certifications_issued"] == 1


# ---------------------------------------------------------------------------
# 19.5 Regional Support
# ---------------------------------------------------------------------------

class TestRegionalSupport:
    def _router(self) -> RegionalSupportRouter:
        router = RegionalSupportRouter()
        router.register_queue(RegionalQueue("eu-west", "en", agent_ids=["a1"]))
        router.register_queue(RegionalQueue("eu-west", "fr", agent_ids=["a2"]))
        router.register_queue(RegionalQueue("mea", "ar", agent_ids=["a3"]))
        router.register_queue(RegionalQueue("global", "en", agent_ids=["a4"]))
        return router

    def test_route_exact_match(self):
        router = self._router()
        key = router.route_ticket("t1", "fr", "eu-west")
        assert key == "eu-west:fr"

    def test_route_language_fallback(self):
        router = self._router()
        key = router.route_ticket("t1", "ar", "eu-west")
        assert key == "mea:ar"

    def test_route_global_fallback(self):
        router = self._router()
        key = router.route_ticket("t1", "zh", "eu-west")
        assert key == "global:en"

    def test_route_no_match_returns_none(self):
        router = RegionalSupportRouter()
        key = router.route_ticket("t1", "zh", "apac")
        assert key is None

    def test_queue_depth_increases(self):
        router = self._router()
        router.route_ticket("t1", "en", "eu-west")
        router.route_ticket("t2", "en", "eu-west")
        q = router._queues["eu-west:en"]
        assert len(q.ticket_ids) == 2

    def test_supported_languages(self):
        router = self._router()
        langs = router.get_supported_languages()
        assert "en" in langs
        assert "fr" in langs
        assert "ar" in langs
        assert len(langs) >= 9

    def test_queue_status(self):
        router = self._router()
        status = router.get_queue_status()
        assert len(status) == 4
        assert all("region" in q for q in status)

    def test_all_eu_languages_supported(self):
        for lang in ["en", "fr", "de", "es", "it", "nl"]:
            assert lang in SUPPORTED_LANGUAGES
