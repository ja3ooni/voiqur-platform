"""
Tool Calling and Integration System
Implements function calling interface, plugin system, and agent integration
"""

import asyncio
import logging
import json
import time
import inspect
from typing import Dict, List, Optional, Any, Callable, Union, Type, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
from abc import ABC, abstractmethod

try:
    from ..core.models import AgentMessage, Task
except ImportError:
    # For direct testing, create minimal models
    from dataclasses import dataclass
    from typing import Dict, Any
    
    @dataclass
    class AgentMessage:
        sender_id: str
        receiver_id: str
        message_type: str
        payload: Dict[str, Any]
    
    @dataclass 
    class Task:
        task_id: str
        description: str


class ToolType(Enum):
    """Types of tools available"""
    FUNCTION = "function"
    API_CALL = "api_call"
    AGENT_INTEGRATION = "agent_integration"
    EXTERNAL_SERVICE = "external_service"
    DATABASE_QUERY = "database_query"
    FILE_OPERATION = "file_operation"


class ToolStatus(Enum):
    """Tool execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ToolParameter:
    """Tool parameter definition"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum_values: Optional[List[Any]] = None
    validation_pattern: Optional[str] = None
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema format"""
        schema = {
            "type": self.type,
            "description": self.description
        }
        
        if self.enum_values:
            schema["enum"] = self.enum_values
        
        if self.validation_pattern:
            schema["pattern"] = self.validation_pattern
        
        if self.default is not None:
            schema["default"] = self.default
        
        return schema


@dataclass
class ToolDefinition:
    """Tool definition with metadata"""
    name: str
    description: str
    tool_type: ToolType
    parameters: List[ToolParameter]
    return_type: str = "object"
    timeout_seconds: int = 30
    requires_confirmation: bool = False
    agent_id: Optional[str] = None
    endpoint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_openai_function(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate parameters against tool definition"""
        errors = []
        
        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in parameters:
                errors.append(f"Missing required parameter: {param.name}")
        
        # Check parameter types and values
        for param_name, param_value in parameters.items():
            param_def = next((p for p in self.parameters if p.name == param_name), None)
            if not param_def:
                errors.append(f"Unknown parameter: {param_name}")
                continue
            
            # Type validation (basic)
            if param_def.type == "string" and not isinstance(param_value, str):
                errors.append(f"Parameter {param_name} must be a string")
            elif param_def.type == "integer" and not isinstance(param_value, int):
                errors.append(f"Parameter {param_name} must be an integer")
            elif param_def.type == "number" and not isinstance(param_value, (int, float)):
                errors.append(f"Parameter {param_name} must be a number")
            elif param_def.type == "boolean" and not isinstance(param_value, bool):
                errors.append(f"Parameter {param_name} must be a boolean")
            
            # Enum validation
            if param_def.enum_values and param_value not in param_def.enum_values:
                errors.append(f"Parameter {param_name} must be one of: {param_def.enum_values}")
        
        return len(errors) == 0, errors


@dataclass
class ToolCall:
    """Tool call execution request"""
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    caller_agent_id: str = ""
    status: ToolStatus = ToolStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def start_execution(self):
        """Mark tool call as started"""
        self.status = ToolStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def complete_execution(self, result: Any):
        """Mark tool call as completed"""
        self.status = ToolStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.result = result
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def fail_execution(self, error_message: str):
        """Mark tool call as failed"""
        self.status = ToolStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()


class BaseTool(ABC):
    """Base class for all tools"""
    
    def __init__(self, definition: ToolDefinition):
        self.definition = definition
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute the tool with given parameters"""
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate parameters"""
        return self.definition.validate_parameters(parameters)


class FunctionTool(BaseTool):
    """Tool that wraps a Python function"""
    
    def __init__(self, definition: ToolDefinition, function: Callable):
        super().__init__(definition)
        self.function = function
        self._validate_function()
    
    def _validate_function(self):
        """Validate that the function signature matches the definition"""
        sig = inspect.signature(self.function)
        func_params = set(sig.parameters.keys())
        def_params = set(param.name for param in self.definition.parameters)
        
        if func_params != def_params:
            self.logger.warning(f"Function signature mismatch for {self.definition.name}")
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute the wrapped function"""
        try:
            # Check if function is async
            if inspect.iscoroutinefunction(self.function):
                return await self.function(**parameters)
            else:
                return self.function(**parameters)
        except Exception as e:
            self.logger.error(f"Function execution failed: {e}")
            raise


class AgentIntegrationTool(BaseTool):
    """Tool that integrates with other agents"""
    
    def __init__(self, definition: ToolDefinition, message_bus):
        super().__init__(definition)
        self.message_bus = message_bus
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute by sending message to target agent"""
        try:
            target_agent_id = self.definition.agent_id
            if not target_agent_id:
                raise ValueError("No target agent specified")
            
            # Create message for target agent
            message = AgentMessage(
                sender_id="llm_agent",
                receiver_id=target_agent_id,
                message_type="tool_request",
                payload={
                    "tool_name": self.definition.name,
                    "parameters": parameters
                }
            )
            
            # Send message and wait for response
            response = await self.message_bus.send_and_wait(message, timeout=self.definition.timeout_seconds)
            
            if response and response.message_type == "tool_response":
                return response.payload.get("result")
            else:
                raise RuntimeError(f"No response from agent {target_agent_id}")
                
        except Exception as e:
            self.logger.error(f"Agent integration failed: {e}")
            raise


class APICallTool(BaseTool):
    """Tool that makes HTTP API calls"""
    
    def __init__(self, definition: ToolDefinition):
        super().__init__(definition)
        self.endpoint = definition.endpoint
        self.headers = definition.metadata.get("headers", {})
        self.method = definition.metadata.get("method", "GET")
    
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute HTTP API call"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                if self.method.upper() == "GET":
                    async with session.get(self.endpoint, params=parameters, headers=self.headers) as response:
                        return await response.json()
                elif self.method.upper() == "POST":
                    async with session.post(self.endpoint, json=parameters, headers=self.headers) as response:
                        return await response.json()
                else:
                    raise ValueError(f"Unsupported HTTP method: {self.method}")
                    
        except Exception as e:
            self.logger.error(f"API call failed: {e}")
            raise


class ToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.tool_definitions: Dict[str, ToolDefinition] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_tool(self, tool: BaseTool) -> bool:
        """Register a tool"""
        try:
            tool_name = tool.definition.name
            self.tools[tool_name] = tool
            self.tool_definitions[tool_name] = tool.definition
            self.logger.info(f"Registered tool: {tool_name}")
            return True
        except Exception as e:
            self.logger.error(f"Tool registration failed: {e}")
            return False
    
    def register_function(self, name: str, description: str, function: Callable,
                         parameters: List[ToolParameter], **kwargs) -> bool:
        """Register a Python function as a tool"""
        try:
            definition = ToolDefinition(
                name=name,
                description=description,
                tool_type=ToolType.FUNCTION,
                parameters=parameters,
                **kwargs
            )
            
            tool = FunctionTool(definition, function)
            return self.register_tool(tool)
            
        except Exception as e:
            self.logger.error(f"Function registration failed: {e}")
            return False
    
    def register_agent_integration(self, name: str, description: str, agent_id: str,
                                 parameters: List[ToolParameter], message_bus=None, **kwargs) -> bool:
        """Register an agent integration tool"""
        try:
            definition = ToolDefinition(
                name=name,
                description=description,
                tool_type=ToolType.AGENT_INTEGRATION,
                parameters=parameters,
                agent_id=agent_id,
                **kwargs
            )
            
            tool = AgentIntegrationTool(definition, message_bus)
            return self.register_tool(tool)
            
        except Exception as e:
            self.logger.error(f"Agent integration registration failed: {e}")
            return False
    
    def register_api_tool(self, name: str, description: str, endpoint: str,
                         parameters: List[ToolParameter], method: str = "GET",
                         headers: Optional[Dict[str, str]] = None, **kwargs) -> bool:
        """Register an API call tool"""
        try:
            definition = ToolDefinition(
                name=name,
                description=description,
                tool_type=ToolType.API_CALL,
                parameters=parameters,
                endpoint=endpoint,
                metadata={"method": method, "headers": headers or {}},
                **kwargs
            )
            
            tool = APICallTool(definition)
            return self.register_tool(tool)
            
        except Exception as e:
            self.logger.error(f"API tool registration failed: {e}")
            return False
    
    def unregister_tool(self, tool_name: str) -> bool:
        """Unregister a tool"""
        try:
            if tool_name in self.tools:
                del self.tools[tool_name]
                del self.tool_definitions[tool_name]
                self.logger.info(f"Unregistered tool: {tool_name}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Tool unregistration failed: {e}")
            return False
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(tool_name)
    
    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool definition by name"""
        return self.tool_definitions.get(tool_name)
    
    def list_tools(self) -> List[str]:
        """List all registered tools"""
        return list(self.tools.keys())
    
    def get_tools_by_type(self, tool_type: ToolType) -> List[str]:
        """Get tools by type"""
        return [name for name, definition in self.tool_definitions.items() 
                if definition.tool_type == tool_type]
    
    def get_openai_functions(self) -> List[Dict[str, Any]]:
        """Get all tools in OpenAI function calling format"""
        return [definition.to_openai_function() for definition in self.tool_definitions.values()]


class ToolExecutor:
    """Executes tool calls with proper error handling and monitoring"""
    
    def __init__(self, tool_registry: ToolRegistry, message_bus=None):
        self.tool_registry = tool_registry
        self.message_bus = message_bus
        self.logger = logging.getLogger(__name__)
        
        # Execution tracking
        self.active_calls: Dict[str, ToolCall] = {}
        self.call_history: List[ToolCall] = []
        self.max_history_size = 1000
        
        # Performance metrics
        self.metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "average_execution_time": 0.0,
            "calls_by_tool": {},
            "errors_by_tool": {}
        }
    
    async def execute_tool_call(self, tool_call: ToolCall) -> ToolCall:
        """Execute a tool call"""
        try:
            # Get tool
            tool = self.tool_registry.get_tool(tool_call.tool_name)
            if not tool:
                tool_call.fail_execution(f"Tool {tool_call.tool_name} not found")
                return tool_call
            
            # Validate parameters
            is_valid, errors = tool.validate_parameters(tool_call.parameters)
            if not is_valid:
                tool_call.fail_execution(f"Parameter validation failed: {', '.join(errors)}")
                return tool_call
            
            # Start execution
            tool_call.start_execution()
            self.active_calls[tool_call.call_id] = tool_call
            
            # Inject message bus for agent integration tools
            if isinstance(tool, AgentIntegrationTool) and self.message_bus:
                tool.message_bus = self.message_bus
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    tool.execute(tool_call.parameters),
                    timeout=tool.definition.timeout_seconds
                )
                tool_call.complete_execution(result)
                
            except asyncio.TimeoutError:
                tool_call.status = ToolStatus.TIMEOUT
                tool_call.error_message = f"Tool execution timed out after {tool.definition.timeout_seconds} seconds"
            
            # Update metrics
            self._update_metrics(tool_call)
            
            # Move to history
            if tool_call.call_id in self.active_calls:
                del self.active_calls[tool_call.call_id]
            
            self.call_history.append(tool_call)
            if len(self.call_history) > self.max_history_size:
                self.call_history.pop(0)
            
            return tool_call
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            tool_call.fail_execution(str(e))
            self._update_metrics(tool_call)
            return tool_call
    
    async def execute_multiple_tools(self, tool_calls: List[ToolCall]) -> List[ToolCall]:
        """Execute multiple tool calls concurrently"""
        tasks = [self.execute_tool_call(call) for call in tool_calls]
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    def cancel_tool_call(self, call_id: str) -> bool:
        """Cancel an active tool call"""
        if call_id in self.active_calls:
            tool_call = self.active_calls[call_id]
            tool_call.status = ToolStatus.CANCELLED
            tool_call.completed_at = datetime.utcnow()
            del self.active_calls[call_id]
            self.call_history.append(tool_call)
            return True
        return False
    
    def get_active_calls(self) -> List[ToolCall]:
        """Get currently active tool calls"""
        return list(self.active_calls.values())
    
    def get_call_history(self, limit: int = 50) -> List[ToolCall]:
        """Get recent call history"""
        return self.call_history[-limit:] if limit else self.call_history
    
    def _update_metrics(self, tool_call: ToolCall):
        """Update execution metrics"""
        self.metrics["total_calls"] += 1
        
        if tool_call.status == ToolStatus.COMPLETED:
            self.metrics["successful_calls"] += 1
        else:
            self.metrics["failed_calls"] += 1
            
            # Track errors by tool
            tool_name = tool_call.tool_name
            if tool_name not in self.metrics["errors_by_tool"]:
                self.metrics["errors_by_tool"][tool_name] = 0
            self.metrics["errors_by_tool"][tool_name] += 1
        
        # Track calls by tool
        tool_name = tool_call.tool_name
        if tool_name not in self.metrics["calls_by_tool"]:
            self.metrics["calls_by_tool"][tool_name] = 0
        self.metrics["calls_by_tool"][tool_name] += 1
        
        # Update average execution time
        if tool_call.execution_time > 0:
            total_calls = self.metrics["total_calls"]
            current_avg = self.metrics["average_execution_time"]
            self.metrics["average_execution_time"] = (
                (current_avg * (total_calls - 1) + tool_call.execution_time) / total_calls
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics"""
        success_rate = 0.0
        if self.metrics["total_calls"] > 0:
            success_rate = self.metrics["successful_calls"] / self.metrics["total_calls"]
        
        return {
            **self.metrics,
            "success_rate": success_rate,
            "active_calls": len(self.active_calls)
        }


class PluginSystem:
    """Plugin system for extensible tool capabilities"""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.plugins: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
    
    def load_plugin(self, plugin_name: str, plugin_module: Any) -> bool:
        """Load a plugin module"""
        try:
            # Check if plugin has required interface
            if not hasattr(plugin_module, 'register_tools'):
                raise ValueError("Plugin must have 'register_tools' function")
            
            # Register plugin tools
            plugin_module.register_tools(self.tool_registry)
            
            self.plugins[plugin_name] = plugin_module
            self.logger.info(f"Loaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Plugin loading failed: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin"""
        try:
            if plugin_name in self.plugins:
                plugin_module = self.plugins[plugin_name]
                
                # Unregister plugin tools if supported
                if hasattr(plugin_module, 'unregister_tools'):
                    plugin_module.unregister_tools(self.tool_registry)
                
                del self.plugins[plugin_name]
                self.logger.info(f"Unloaded plugin: {plugin_name}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Plugin unloading failed: {e}")
            return False
    
    def list_plugins(self) -> List[str]:
        """List loaded plugins"""
        return list(self.plugins.keys())
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get plugin information"""
        if plugin_name in self.plugins:
            plugin_module = self.plugins[plugin_name]
            return {
                "name": plugin_name,
                "version": getattr(plugin_module, '__version__', 'unknown'),
                "description": getattr(plugin_module, '__description__', 'No description'),
                "author": getattr(plugin_module, '__author__', 'Unknown')
            }
        return None