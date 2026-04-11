"""
Workflow Automation package
"""
from .builder import (
    Workflow, WorkflowNode, NodeType, Condition, ConditionGroup,
    ConditionOperator, WorkflowVersion,
)
from .engine import (
    WorkflowEngine, WorkflowExecution, ExecutionStatus,
    TriggerType, ActionRegistry, NodeExecutionLog,
)
from .crm import (
    CRMConnector, SalesforceConnector, HubSpotConnector,
    MSDynamicsConnector, SAPConnector, ZohoConnector, PipedriveConnector,
    CRM_CONNECTORS,
)
from .connectors import (
    DBConnector, PostgreSQLConnector, MySQLConnector, MongoDBConnector,
    RESTConnector, DataTransformer,
)
from .templates import get_template, TEMPLATES

__all__ = [
    "Workflow", "WorkflowNode", "NodeType", "Condition", "ConditionGroup",
    "ConditionOperator", "WorkflowVersion",
    "WorkflowEngine", "WorkflowExecution", "ExecutionStatus",
    "TriggerType", "ActionRegistry", "NodeExecutionLog",
    "CRMConnector", "SalesforceConnector", "HubSpotConnector",
    "MSDynamicsConnector", "SAPConnector", "ZohoConnector", "PipedriveConnector",
    "CRM_CONNECTORS",
    "DBConnector", "PostgreSQLConnector", "MySQLConnector", "MongoDBConnector",
    "RESTConnector", "DataTransformer",
    "get_template", "TEMPLATES",
]
