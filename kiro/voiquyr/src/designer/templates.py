"""
Conversation Template Library — industry-specific templates and reusable modules.
Implements Requirements 21.6, 21.8.
"""

from .canvas import ConvNode, ConvNodeType, ConversationFlow, ConditionGroup, ConvCondition, CondOp


def _n(node_type: ConvNodeType, name: str, **kwargs) -> ConvNode:
    return ConvNode(node_type=node_type, name=name, **kwargs)


def customer_support() -> ConversationFlow:
    """Customer support flow: greet → detect intent → route to FAQ/agent."""
    flow = ConversationFlow(name="Customer Support")
    start = _n(ConvNodeType.START, "Start")
    greet = _n(ConvNodeType.RESPONSE, "Greeting",
               response_text="Hello! How can I help you today?",
               response_variants=["Hello! How can I help?", "Hi there! What can I do for you?"])
    intent = _n(ConvNodeType.INTENT, "Detect Intent",
                intents=["billing", "technical", "general", "cancel"])
    cond = _n(ConvNodeType.CONDITION, "Is Complex?",
              condition_group=ConditionGroup(
                  conditions=[ConvCondition("_intent", CondOp.CONTAINS, "technical")],
                  logic="OR"
              ))
    faq = _n(ConvNodeType.RESPONSE, "FAQ Response",
             response_text="Here's what I found in our knowledge base.")
    handoff = _n(ConvNodeType.HANDOFF, "Transfer to Agent")
    end = _n(ConvNodeType.END, "End")

    for n in [start, greet, intent, cond, faq, handoff, end]:
        flow.add_node(n)
    flow.connect(start.node_id, greet.node_id)
    flow.connect(greet.node_id, intent.node_id)
    flow.connect(intent.node_id, cond.node_id)
    flow.connect(cond.node_id, handoff.node_id, "true")
    flow.connect(cond.node_id, faq.node_id, "false")
    flow.connect(faq.node_id, end.node_id)
    flow.connect(handoff.node_id, end.node_id)
    flow.tags = ["support", "customer-service"]
    return flow


def appointment_booking() -> ConversationFlow:
    """Appointment booking: collect date/time slots, confirm."""
    flow = ConversationFlow(name="Appointment Booking")
    start = _n(ConvNodeType.START, "Start")
    greet = _n(ConvNodeType.RESPONSE, "Greeting",
               response_text="I can help you book an appointment. What date works for you?")
    collect_date = _n(ConvNodeType.SLOT_FILLING, "Collect Date", slots=["date", "time"])
    confirm = _n(ConvNodeType.RESPONSE, "Confirm Booking",
                 response_text="Great! I've booked your appointment.")
    end = _n(ConvNodeType.END, "End")

    for n in [start, greet, collect_date, confirm, end]:
        flow.add_node(n)
    flow.connect(start.node_id, greet.node_id)
    flow.connect(greet.node_id, collect_date.node_id)
    flow.connect(collect_date.node_id, confirm.node_id)
    flow.connect(confirm.node_id, end.node_id)
    flow.tags = ["scheduling", "booking"]
    return flow


def lead_qualification() -> ConversationFlow:
    """Lead qualification: collect contact info, score, route."""
    flow = ConversationFlow(name="Lead Qualification")
    start = _n(ConvNodeType.START, "Start")
    intro = _n(ConvNodeType.RESPONSE, "Introduction",
               response_text="Hi! I'd love to learn more about your needs.")
    collect = _n(ConvNodeType.SLOT_FILLING, "Collect Info",
                 slots=["company_size", "budget", "timeline"])
    score = _n(ConvNodeType.ACTION, "Score Lead", action_name="crm.score_lead")
    qualified = _n(ConvNodeType.CONDITION, "Qualified?",
                   condition_group=ConditionGroup(
                       conditions=[ConvCondition("lead_score", CondOp.GTE, 70)],
                   ))
    hot = _n(ConvNodeType.RESPONSE, "Hot Lead Response",
             response_text="Excellent! Let me connect you with our sales team.")
    nurture = _n(ConvNodeType.RESPONSE, "Nurture Response",
                 response_text="Thanks! We'll be in touch with some resources.")
    end = _n(ConvNodeType.END, "End")

    for n in [start, intro, collect, score, qualified, hot, nurture, end]:
        flow.add_node(n)
    flow.connect(start.node_id, intro.node_id)
    flow.connect(intro.node_id, collect.node_id)
    flow.connect(collect.node_id, score.node_id)
    flow.connect(score.node_id, qualified.node_id)
    flow.connect(qualified.node_id, hot.node_id, "true")
    flow.connect(qualified.node_id, nurture.node_id, "false")
    flow.connect(hot.node_id, end.node_id)
    flow.connect(nurture.node_id, end.node_id)
    flow.tags = ["sales", "lead-gen"]
    return flow


def faq_bot() -> ConversationFlow:
    """Simple FAQ bot with fallback."""
    flow = ConversationFlow(name="FAQ Bot")
    start = _n(ConvNodeType.START, "Start")
    greet = _n(ConvNodeType.RESPONSE, "Greeting",
               response_text="Hello! Ask me anything.")
    intent = _n(ConvNodeType.INTENT, "Match FAQ Intent",
                intents=["pricing", "features", "trial", "contact"])
    answer = _n(ConvNodeType.RESPONSE, "FAQ Answer",
                response_text="Here's the answer to your question.")
    fallback = _n(ConvNodeType.FALLBACK, "Fallback",)
    fallback_resp = _n(ConvNodeType.RESPONSE, "Fallback Response",
                       response_text="I'm not sure about that. Let me connect you with support.")
    end = _n(ConvNodeType.END, "End")

    for n in [start, greet, intent, answer, fallback, fallback_resp, end]:
        flow.add_node(n)
    flow.connect(start.node_id, greet.node_id)
    flow.connect(greet.node_id, intent.node_id)
    flow.connect(intent.node_id, answer.node_id)
    flow.connect(answer.node_id, end.node_id)
    flow.connect(fallback.node_id, fallback_resp.node_id)
    flow.connect(fallback_resp.node_id, end.node_id)
    flow.tags = ["faq", "self-service"]
    return flow


CONV_TEMPLATES = {
    "customer_support": customer_support,
    "appointment_booking": appointment_booking,
    "lead_qualification": lead_qualification,
    "faq_bot": faq_bot,
}


def get_conv_template(name: str) -> ConversationFlow:
    fn = CONV_TEMPLATES.get(name)
    if not fn:
        raise KeyError(f"Unknown template: {name}. Available: {list(CONV_TEMPLATES)}")
    return fn()
