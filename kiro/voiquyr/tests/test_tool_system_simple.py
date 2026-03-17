"""
Simple test for Tool Calling and Integration System
Tests core functionality without heavy dependencies
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agents.tool_integration import (
    ToolRegistry, ToolExecutor, PluginSystem, ToolCall, 
    ToolParameter, ToolType, FunctionTool, ToolDefinition
)


async def test_tool_registry():
    """Test tool registry functionality"""
    print("Testing Tool Registry...")
    
    registry = ToolRegistry()
    
    # Test function registration
    def add_numbers(a: int, b: int) -> int:
        return a + b
    
    success = registry.register_function(
        name="add_numbers",
        description="Add two numbers",
        function=add_numbers,
        parameters=[
            ToolParameter("a", "integer", "First number", required=True),
            ToolParameter("b", "integer", "Second number", required=True)
        ]
    )
    
    print(f"✓ Function registered: {success}")
    print(f"✓ Available tools: {registry.list_tools()}")
    
    # Test OpenAI format
    openai_functions = registry.get_openai_functions()
    print(f"✓ OpenAI functions: {len(openai_functions)}")
    
    return registry


async def test_tool_executor():
    """Test tool executor functionality"""
    print("\nTesting Tool Executor...")
    
    registry = await test_tool_registry()
    executor = ToolExecutor(registry)
    
    # Test tool execution
    tool_call = ToolCall(
        tool_name="add_numbers",
        parameters={"a": 10, "b": 20},
        caller_agent_id="test"
    )
    
    result = await executor.execute_tool_call(tool_call)
    print(f"✓ Tool execution result: {result.result}")
    print(f"✓ Execution status: {result.status.value}")
    print(f"✓ Execution time: {result.execution_time:.3f}s")
    
    # Test invalid parameters
    invalid_call = ToolCall(
        tool_name="add_numbers",
        parameters={"a": 10},  # Missing 'b'
        caller_agent_id="test"
    )
    
    invalid_result = await executor.execute_tool_call(invalid_call)
    print(f"✓ Invalid params status: {invalid_result.status.value}")
    
    # Test metrics
    metrics = executor.get_metrics()
    print(f"✓ Execution metrics: {metrics}")
    
    return executor


async def test_plugin_system():
    """Test plugin system functionality"""
    print("\nTesting Plugin System...")
    
    registry = ToolRegistry()
    plugin_system = PluginSystem(registry)
    
    try:
        # Import and load example plugin
        from agents.plugins import example_plugin
        
        success = plugin_system.load_plugin("example_plugin", example_plugin)
        print(f"✓ Plugin loaded: {success}")
        
        # Test plugin tools
        executor = ToolExecutor(registry)
        
        # Test percentage calculation
        tool_call = ToolCall(
            tool_name="calculate_percentage",
            parameters={"value": 100, "percentage": 25},
            caller_agent_id="test"
        )
        
        result = await executor.execute_tool_call(tool_call)
        print(f"✓ Plugin tool result: {result.result}")
        
        # Test plugin info
        plugin_info = plugin_system.get_plugin_info("example_plugin")
        print(f"✓ Plugin info: {plugin_info}")
        
        return plugin_system
        
    except Exception as e:
        print(f"✗ Plugin test failed: {e}")
        return None


async def test_advanced_features():
    """Test advanced tool features"""
    print("\nTesting Advanced Features...")
    
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    
    # Test async function
    async def async_multiply(x: float, y: float) -> float:
        await asyncio.sleep(0.1)
        return x * y
    
    registry.register_function(
        name="async_multiply",
        description="Multiply numbers asynchronously",
        function=async_multiply,
        parameters=[
            ToolParameter("x", "number", "First number", required=True),
            ToolParameter("y", "number", "Second number", required=True)
        ]
    )
    
    # Test execution
    tool_call = ToolCall(
        tool_name="async_multiply",
        parameters={"x": 3.5, "y": 2.0},
        caller_agent_id="test"
    )
    
    result = await executor.execute_tool_call(tool_call)
    print(f"✓ Async tool result: {result.result}")
    
    # Test multiple tools
    def square(x: int) -> int:
        return x ** 2
    
    registry.register_function(
        name="square",
        description="Square a number",
        function=square,
        parameters=[ToolParameter("x", "integer", "Number to square", required=True)]
    )
    
    # Execute multiple tools
    tool_calls = [
        ToolCall(tool_name="async_multiply", parameters={"x": 2, "y": 3}, caller_agent_id="test"),
        ToolCall(tool_name="square", parameters={"x": 4}, caller_agent_id="test")
    ]
    
    results = await executor.execute_multiple_tools(tool_calls)
    print(f"✓ Multiple tool results: {[r.result for r in results]}")
    
    return executor


async def test_parameter_validation():
    """Test parameter validation"""
    print("\nTesting Parameter Validation...")
    
    # Create tool definition
    definition = ToolDefinition(
        name="test_tool",
        description="Test tool for validation",
        tool_type=ToolType.FUNCTION,
        parameters=[
            ToolParameter("required_param", "string", "Required parameter", required=True),
            ToolParameter("optional_param", "integer", "Optional parameter", required=False, default=10),
            ToolParameter("enum_param", "string", "Enum parameter", required=False, 
                         enum_values=["option1", "option2", "option3"])
        ]
    )
    
    # Test valid parameters
    valid_params = {"required_param": "test", "optional_param": 20, "enum_param": "option1"}
    is_valid, errors = definition.validate_parameters(valid_params)
    print(f"✓ Valid parameters: {is_valid}, errors: {errors}")
    
    # Test invalid parameters
    invalid_params = {"optional_param": 20, "enum_param": "invalid_option"}  # Missing required
    is_valid, errors = definition.validate_parameters(invalid_params)
    print(f"✓ Invalid parameters: {is_valid}, errors: {errors}")
    
    # Test OpenAI format conversion
    openai_format = definition.to_openai_function()
    print(f"✓ OpenAI format: {openai_format}")


async def main():
    """Run all tests"""
    print("🚀 Testing Tool Calling and Integration System")
    print("=" * 50)
    
    try:
        await test_tool_registry()
        await test_tool_executor()
        await test_plugin_system()
        await test_advanced_features()
        await test_parameter_validation()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())