"""
Workflow Template Library — pre-built templates for common business processes.
Implements Requirement 18.7.
"""

from .builder import (
    ConditionOperator, NodeType, Workflow, WorkflowNode,
)


def _node(node_type: NodeType, name: str, config: dict = None, **kwargs) -> WorkflowNode:
    return WorkflowNode(node_type=node_type, name=name, config=config or {}, **kwargs)


def lead_qualification() -> Workflow:
    """
    Lead Qualification workflow:
    Trigger → Enrich lead data → Score lead → Condition (qualified?) →
      Yes: Create CRM deal + Notify sales
      No: Add to nurture sequence
    """
    wf = Workflow(name="Lead Qualification")

    trigger = _node(NodeType.TRIGGER, "New Lead Received",
                    {"trigger_type": "webhook", "event": "lead.created"})
    enrich = _node(NodeType.ACTION, "Enrich Lead Data",
                   {"action": "crm.enrich_contact", "fields": ["company", "industry", "size"]})
    score = _node(NodeType.TRANSFORM, "Score Lead",
                  {"operations": [{"type": "enrich", "fields": {"lead_score": 0}}]})
    qualify = _node(NodeType.CONDITION, "Is Lead Qualified?",
                    {"condition_group": {"conditions": [
                        {"field": "lead_score", "operator": "gte", "value": 70}
                    ], "logic": "AND"}})
    create_deal = _node(NodeType.ACTION, "Create CRM Deal",
                        {"action": "crm.create_deal"})
    notify_sales = _node(NodeType.ACTION, "Notify Sales Team",
                         {"action": "notification.send", "channel": "slack"})
    nurture = _node(NodeType.ACTION, "Add to Nurture Sequence",
                    {"action": "email.add_to_sequence", "sequence": "lead_nurture"})
    end = _node(NodeType.END, "End")

    for n in [trigger, enrich, score, qualify, create_deal, notify_sales, nurture, end]:
        wf.add_node(n)

    wf.connect(trigger.node_id, enrich.node_id)
    wf.connect(enrich.node_id, score.node_id)
    wf.connect(score.node_id, qualify.node_id)
    wf.connect(qualify.node_id, create_deal.node_id, "true")
    wf.connect(qualify.node_id, nurture.node_id, "false")
    wf.connect(create_deal.node_id, notify_sales.node_id)
    wf.connect(notify_sales.node_id, end.node_id)
    wf.connect(nurture.node_id, end.node_id)
    wf.tags = ["sales", "crm"]
    return wf


def appointment_booking() -> Workflow:
    """
    Appointment Booking:
    Trigger → Check availability → Condition (slot available?) →
      Yes: Book slot + Send confirmation
      No: Offer alternatives
    """
    wf = Workflow(name="Appointment Booking")

    trigger = _node(NodeType.TRIGGER, "Booking Request",
                    {"trigger_type": "event", "event": "booking.requested"})
    check = _node(NodeType.ACTION, "Check Calendar Availability",
                  {"action": "calendar.check_availability"})
    available = _node(NodeType.CONDITION, "Slot Available?",
                      {"condition_group": {"conditions": [
                          {"field": "slot_available", "operator": "eq", "value": True}
                      ], "logic": "AND"}})
    book = _node(NodeType.ACTION, "Book Appointment",
                 {"action": "calendar.book_slot"})
    confirm = _node(NodeType.ACTION, "Send Confirmation",
                    {"action": "notification.send", "channel": "email"})
    alternatives = _node(NodeType.ACTION, "Offer Alternative Slots",
                         {"action": "calendar.suggest_alternatives"})
    end = _node(NodeType.END, "End")

    for n in [trigger, check, available, book, confirm, alternatives, end]:
        wf.add_node(n)

    wf.connect(trigger.node_id, check.node_id)
    wf.connect(check.node_id, available.node_id)
    wf.connect(available.node_id, book.node_id, "true")
    wf.connect(available.node_id, alternatives.node_id, "false")
    wf.connect(book.node_id, confirm.node_id)
    wf.connect(confirm.node_id, end.node_id)
    wf.connect(alternatives.node_id, end.node_id)
    wf.tags = ["scheduling", "calendar"]
    return wf


def order_processing() -> Workflow:
    """
    Order Processing:
    Trigger → Validate order → Check inventory → Process payment →
    Condition (payment ok?) → Yes: Fulfill + Notify / No: Notify failure
    """
    wf = Workflow(name="Order Processing")

    trigger = _node(NodeType.TRIGGER, "Order Received",
                    {"trigger_type": "webhook", "event": "order.created"})
    validate = _node(NodeType.ACTION, "Validate Order",
                     {"action": "order.validate"})
    inventory = _node(NodeType.ACTION, "Check Inventory",
                      {"action": "inventory.check"})
    payment = _node(NodeType.ACTION, "Process Payment",
                    {"action": "payment.charge"})
    paid = _node(NodeType.CONDITION, "Payment Successful?",
                 {"condition_group": {"conditions": [
                     {"field": "payment_status", "operator": "eq", "value": "success"}
                 ], "logic": "AND"}})
    fulfill = _node(NodeType.ACTION, "Fulfill Order",
                    {"action": "fulfillment.ship"})
    notify_ok = _node(NodeType.ACTION, "Send Order Confirmation",
                      {"action": "notification.send", "template": "order_confirmed"})
    notify_fail = _node(NodeType.ACTION, "Notify Payment Failure",
                        {"action": "notification.send", "template": "payment_failed"})
    end = _node(NodeType.END, "End")

    for n in [trigger, validate, inventory, payment, paid, fulfill, notify_ok, notify_fail, end]:
        wf.add_node(n)

    wf.connect(trigger.node_id, validate.node_id)
    wf.connect(validate.node_id, inventory.node_id)
    wf.connect(inventory.node_id, payment.node_id)
    wf.connect(payment.node_id, paid.node_id)
    wf.connect(paid.node_id, fulfill.node_id, "true")
    wf.connect(paid.node_id, notify_fail.node_id, "false")
    wf.connect(fulfill.node_id, notify_ok.node_id)
    wf.connect(notify_ok.node_id, end.node_id)
    wf.connect(notify_fail.node_id, end.node_id)
    wf.tags = ["ecommerce", "payments"]
    return wf


def customer_onboarding() -> Workflow:
    """
    Customer Onboarding:
    Trigger → Create account → Send welcome email → Schedule kickoff →
    Delay 1 day → Send getting-started guide → End
    """
    wf = Workflow(name="Customer Onboarding")

    trigger = _node(NodeType.TRIGGER, "New Customer Signed Up",
                    {"trigger_type": "event", "event": "customer.created"})
    create = _node(NodeType.ACTION, "Create Account",
                   {"action": "account.provision"})
    welcome = _node(NodeType.ACTION, "Send Welcome Email",
                    {"action": "email.send", "template": "welcome"})
    kickoff = _node(NodeType.ACTION, "Schedule Kickoff Call",
                    {"action": "calendar.schedule_kickoff"})
    delay = _node(NodeType.DELAY, "Wait 1 Day", {"seconds": 86400})
    guide = _node(NodeType.ACTION, "Send Getting Started Guide",
                  {"action": "email.send", "template": "getting_started"})
    end = _node(NodeType.END, "End")

    for n in [trigger, create, welcome, kickoff, delay, guide, end]:
        wf.add_node(n)

    wf.connect(trigger.node_id, create.node_id)
    wf.connect(create.node_id, welcome.node_id)
    wf.connect(welcome.node_id, kickoff.node_id)
    wf.connect(kickoff.node_id, delay.node_id)
    wf.connect(delay.node_id, guide.node_id)
    wf.connect(guide.node_id, end.node_id)
    wf.tags = ["onboarding", "customer-success"]
    return wf


def support_ticket_creation() -> Workflow:
    """
    Support Ticket Creation:
    Trigger → Classify issue → Condition (urgent?) →
      Yes: Page on-call + Create P1 ticket
      No: Create standard ticket + Assign to queue
    """
    wf = Workflow(name="Support Ticket Creation")

    trigger = _node(NodeType.TRIGGER, "Support Request Received",
                    {"trigger_type": "event", "event": "support.request"})
    classify = _node(NodeType.ACTION, "Classify Issue",
                     {"action": "ai.classify_intent"})
    urgent = _node(NodeType.CONDITION, "Is Urgent?",
                   {"condition_group": {"conditions": [
                       {"field": "priority", "operator": "eq", "value": "urgent"}
                   ], "logic": "AND"}})
    page = _node(NodeType.ACTION, "Page On-Call Engineer",
                 {"action": "pagerduty.trigger"})
    p1 = _node(NodeType.ACTION, "Create P1 Ticket",
               {"action": "ticketing.create", "priority": "P1"})
    standard = _node(NodeType.ACTION, "Create Standard Ticket",
                     {"action": "ticketing.create", "priority": "P3"})
    assign = _node(NodeType.ACTION, "Assign to Queue",
                   {"action": "ticketing.assign_queue"})
    end = _node(NodeType.END, "End")

    for n in [trigger, classify, urgent, page, p1, standard, assign, end]:
        wf.add_node(n)

    wf.connect(trigger.node_id, classify.node_id)
    wf.connect(classify.node_id, urgent.node_id)
    wf.connect(urgent.node_id, page.node_id, "true")
    wf.connect(urgent.node_id, standard.node_id, "false")
    wf.connect(page.node_id, p1.node_id)
    wf.connect(p1.node_id, end.node_id)
    wf.connect(standard.node_id, assign.node_id)
    wf.connect(assign.node_id, end.node_id)
    wf.tags = ["support", "ticketing"]
    return wf


TEMPLATES = {
    "lead_qualification": lead_qualification,
    "appointment_booking": appointment_booking,
    "order_processing": order_processing,
    "customer_onboarding": customer_onboarding,
    "support_ticket_creation": support_ticket_creation,
}


def get_template(name: str) -> Workflow:
    fn = TEMPLATES.get(name)
    if not fn:
        raise KeyError(f"Unknown template: {name}. Available: {list(TEMPLATES)}")
    return fn()
