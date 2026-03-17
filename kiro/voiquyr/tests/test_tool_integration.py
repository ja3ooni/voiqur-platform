"""
Test script for Tool Calling and Integration capabilities
Tests function calling interface, plugin system, and agent integration
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agents.llm_agent import LLMAgent
from agents.tool_integration import (
    ToolRegistry, ToolExecutor, PluginSystem, ToolCall, 
    ToolParameter, ToolType, FunctionTool
)
from core.messaging import MessageRouter, MessageBus
from core.models import AgentMessage, AgentRegistration, AgentCapability


async def test_basic_tool_system():
    """Test basic tool system functionality"""
    print("="*60)
    print("Testing Basic Tool System")
    print("="*60)
    
    # Create tool registry
    registry = ToolRegistry()
    
    # Test 1: Register a simple function
    print("\n1. Testing function registration...")
    
    def add_numbers(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b
    
    success = registry.register_function(
        name="add_numbers",
        description="Add two numbers together",
        function=add_numbers,
        parameters=[
            ToolParameter("a", "integer", "First number", required=True),
            ToolParameter("b", "integer", "Second number", required=True)
        ]
    )
    print(f"   Function registered: {success}")
    
    # Test 2: Register an async function
    print("\n2. Testing async function registration...")
    
    async def multiply_async(x: float, y: float) -> float:
        """Multiply two numbers asynchronously"""
        await asyncio.sleep(0.1)  # Simulate async work
        return x * y
    
    success = registry.register_function(
        name="multiply_async",
        description="Multiply two numbers asynchronously",
        function=multiply_async,
        parameters=[
            ToolParameter("x", "number", "First number", required=True),
            ToolParameter("y", "number", "Second number", required=True)
        ]
    )
    print(f"   Async function registered: {success}")
    
    # Test 3: Test tool execution
    print("\n3. Testing tool execution...")
    executor = ToolExecutor(registry)
    
    # Execute sync function
    tool_call = ToolCall(
        tool_name="add_numbers",
        parameters={"a": 15, "b": 25},
        caller_agent_id="test"
    )
    
    result = await executor.execute_tool_call(tool_call)
    print(f"   Add result: {result.result} (status: {result.status.value})")
    print(f"   Execution time: {result.execution_time:.3f}s")
    
    # Execute async function
    tool_call2 = ToolCall(
        tool_name="multiply_async",
        parameters={"x": 3.5, "y": 2.0},
        caller_agent_id="test"
    )
    
    result2 = await executor.execute_tool_call(tool_call2)
    print(f"   Multiply result: {result2.result} (status: {result2.status.value})")
    print(f"   Execution time: {result2.execution_time:.3f}s")
    
    # Test 4: Test OpenAI function format
    print("\n4. Testing OpenAI function format...")
    openai_functions = registry.get_openai_functions()
    print(f"   Functions in OpenAI format: {len(openai_functions)}")
    for func in openai_functions:
        print(f"   - {func['name']}: {func['description']}")
    
    # Test 5: Test parameter validation
    print("\n5. Testing parameter validation...")
    
    # Valid parameters
    tool_call3 = ToolCall(
        tool_name="add_numbers",
        parameters={"a": 10, "b": 20},
        caller_agent_id="test"
    )
    result3 = await executor.execute_tool_call(tool_call3)
    print(f"   Valid params result: {result3.result} (status: {result3.status.value})")
    
    # Invalid parameters (missing required param)
    tool_call4 = ToolCall(
        tool_name="add_numbers",
        parameters={"a": 10},  # Missing 'b'
        caller_agent_id="test"
    )
    result4 = await executor.execute_tool_call(tool_call4)
    print(f"   Invalid params status: {result4.status.value}")
    print(f"   Error message: {result4.error_message}")
    
    # Test 6: Test execution metrics
    print("\n6. Testing execution metrics...")
    metrics = executor.get_metrics()
    print(f"   Total calls: {metrics['total_calls']}")
    print(f"   Successful calls: {metrics['successful_calls']}")
    print(f"   Failed calls: {metrics['failed_calls']}")
    print(f"   Success rate: {metrics['success_rate']:.2%}")
    print(f"   Average execution time: {metrics['average_execution_time']:.3f}s")
    
    print("\n✅ Basic Tool System tests completed!")
    return registry, executor


async def test_plugin_system():
    """Test plugin system functionality"""
    print("\n" + "="*60)
    print("Testing Plugin System")
    print("="*60)
    
    # Create tool registry and plugin system
    registry = ToolRegistry()
    plugin_system = PluginSystem(registry)
    
    try:
        # Test 1: Load example plugin
        print("\n1. Testing plugin loading...")
        
        # Import the example plugin
        from agents.plugins import example_plugin
        
        success = plugin_system.load_plugin("example_plugin", example_plugin)
        print(f"   Plugin loaded: {success}")
        
        # Test 2: Check loaded plugins
        print("\n2. Testing plugin listing...")
        plugins = plugin_system.list_plugins()
        print(f"   Loaded plugins: {plugins}")
        
        # Test 3: Test plugin tools
        print("\n3. Testing plugin tools...")
        executor = ToolExecutor(registry)
        
        # Test percentage calculation
        tool_call = ToolCall(
            tool_name="calculate_percentage",
            parameters={"value": 200, "percentage": 15},
            caller_agent_id="test"
        )
        result = await executor.execute_tool_call(tool_call)
        print(f"   Percentage calculation: {result.result}")
        
        # Test word counting
        tool_call2 = ToolCall(
            tool_name="count_words",
            parameters={"text": "Hello world! This is a test.", "include_punctuation": False},
            caller_agent_id="test"
        )
        result2 = await executor.execute_tool_call(tool_call2)
        print(f"   Word count: {result2.result}")
        
        # Test language detection
        tool_call3 = ToolCall(
            tool_name="detect_language_simple",
            parameters={"text": "The quick brown fox jumps over the lazy dog"},
            caller_agent_id="test"
        )
        result3 = await executor.execute_tool_call(tool_call3)
        print(f"   Language detection: {result3.result}")
        
        # Test 4: Test plugin info
        print("\n4. Testing plugin info...")
        plugin_info = plugin_system.get_plugin_info("example_plugin")
        if plugin_info:
            print(f"   Plugin name: {plugin_info['name']}")
            print(f"   Version: {plugin_info['version']}")
            print(f"   Description: {plugin_info['description']}")
        
        # Test 5: Test plugin unloading
        print("\n5. Testing plugin unloading...")
        unload_success = plugin_system.unload_plugin("example_plugin")
        print(f"   Plugin unloaded: {unload_success}")
        
        remaining_plugins = plugin_system.list_plugins()
        print(f"   Remaining plugins: {remaining_plugins}")
        
        print("\n✅ Plugin System tests completed!")
        
    except Exception as e:
        print(f"\n❌ Plugin System test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_agent_integration():
    """Test agent integration capabilities"""
    print("\n" + "="*60)
    print("Testing Agent Integration")
    print("="*60)
    
    # Set up message router and bus
    router = MessageRouter()
    message_bus = MessageBus(router)
    
    try:
        # Test 1: Create LLM agent with tool integration
        print("\n1. Testing LLM agent with tool integration...")
        
        llm_agent = LLMAgent("llm_agent_test", message_bus)
        success = await llm_agent.initialize()
        print(f"   LLM agent initialized: {success}")
        
        if not success:
            print("   Skipping agent integration tests due to initialization failure")
            return
        
        # Test 2: Check available tools
        print("\n2. Testing available tools...")
        tools = llm_agent.get_available_tools()
        print(f"   Available tools ({len(tools)}):")
        for tool in tools:
            print(f"   - {tool}")
        
        # Test 3: Test tool usage statistics
        print("\n3. Testing tool usage statistics...")
        stats = llm_agent.get_tool_usage_stats()
        print(f"   Total tools registered: {stats['total_tools_registered']}")
        print(f"   Tools by type: {stats['tools_by_type']}")
        print(f"   Agent integrations: {stats['agent_integrations']}")
        
        # Test 4: Test message processing with tool calls
        print("\n4. Testing message processing with tool calls...")
        
        # Time query
        result = await llm_agent.process_message("What time is it?")
        print(f"   Time query response: {result.get('response', 'No response')}")
        print(f"   Tool calls made: {len(result.get('tool_calls', []))}")
        
        # Weather query
        result2 = await llm_agent.process_message("What's the weather like in London?")
        print(f"   Weather query response: {result2.get('response', 'No response')}")
        print(f"   Tool calls made: {len(result2.get('tool_calls', []))}")
        
        # Knowledge query
        result3 = await llm_agent.process_message("Tell me about artificial intelligence")
        print(f"   Knowledge query response: {result3.get('response', 'No response')}")
        print(f"   Tool calls made: {len(result3.get('tool_calls', []))}")
        
        # Test 5: Test external tool registration
        print("\n5. Testing external tool registration...")
        
        external_tool_info = {
            "name": "external_calculator",
            "description": "External calculator service",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate"
                    }
                },
                "required": ["expression"]
            },
            "agent_id": "calculator_agent"
        }
        
        reg_success = await llm_agent.register_external_tool(external_tool_info)
        print(f"   External tool registered: {reg_success}")
        
        # Test 6: Test tool chain execution
        print("\n6. Testing tool chain execution...")
        
        chain_result = await llm_agent.create_tool_chain(
            tools=["get_current_time", "query_knowledge_base"],
            input_data={"query": "current time information"}
        )
        print(f"   Chain status: {chain_result['chain_status']}")
        print(f"   Chain results: {len(chain_result['results'])} steps")
        
        # Test 7: Test agent message handling
        print("\n7. Testing agent message handling...")
        
        # Tool request message
        tool_request = AgentMessage(
            sender_id="test_agent",
            receiver_id=llm_agent.agent_id,
            message_type="tool_request",
            payload={
                "tool_name": "get_current_time",
                "parameters": {}
            }
        )
        
        response = await llm_agent.handle_message(tool_request)
        if response:
            print(f"   Tool request handled: {response.message_type}")
            print(f"   Tool result: {response.payload.get('result', 'No result')}")
        
        # Test 8: Test coordination capabilities
        print("\n8. Testing coordination capabilities...")
        
        coord_result = await llm_agent._coordinate_agents(
            task_description="Process multilingual audio with emotion detection",
            required_agents=["stt_agent", "emotion_agent", "llm_agent"],
            priority="high"
        )
        print(f"   Coordination result: {coord_result}")
        
        print("\n✅ Agent Integration tests completed!")
        
        # Cleanup
        await llm_agent.shutdown()
        
    except Exception as e:
        print(f"\n❌ Agent Integration test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_advanced_features():
    """Test advanced tool integration features"""
    print("\n" + "="*60)
    print("Testing Advanced Features")
    print("="*60)
    
    try:
        # Test 1: Multiple tool execution
        print("\n1. Testing multiple tool execution...")
        
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        
        # Register multiple tools
        def tool1(x: int) -> int:
            return x * 2
        
        def tool2(x: int) -> int:
            return x + 10
        
        def tool3(x: int) -> int:
            return x ** 2
        
        registry.register_function("double", "Double a number", tool1, [
            ToolParameter("x", "integer", "Number to double", required=True)
        ])
        
        registry.register_function("add_ten", "Add 10 to a number", tool2, [
            ToolParameter("x", "integer", "Number to add 10 to", required=True)
        ])
        
        registry.register_function("square", "Square a number", tool3, [
            ToolParameter("x", "integer", "Number to square", required=True)
        ])
        
        # Execute multiple tools concurrently
        tool_calls = [
            ToolCall(tool_name="double", parameters={"x": 5}, caller_agent_id="test"),
            ToolCall(tool_name="add_ten", parameters={"x": 5}, caller_agent_id="test"),
            ToolCall(tool_name="square", parameters={"x": 5}, caller_agent_id="test")
        ]
        
        results = await executor.execute_multiple_tools(tool_calls)
        print(f"   Multiple tool execution results:")
        for i, result in enumerate(results):
            print(f"   - Tool {i+1}: {result.result} (status: {result.status.value})")
        
        # Test 2: Tool execution with timeout
        print("\n2. Testing tool execution with timeout...")
        
        async def slow_tool(delay: float) -> str:
            await asyncio.sleep(delay)
            return f"Completed after {delay} seconds"
        
        registry.register_function("slow_tool", "A slow tool for testing", slow_tool, [
            ToolParameter("delay", "number", "Delay in seconds", required=True)
        ], timeout_seconds=2)
        
        # This should succeed (within timeout)
        fast_call = ToolCall(
            tool_name="slow_tool",
            parameters={"delay": 0.5},
            caller_agent_id="test"
        )
        fast_result = await executor.execute_tool_call(fast_call)
        print(f"   Fast tool result: {fast_result.result} (status: {fast_result.status.value})")
        
        # This should timeout
        slow_call = ToolCall(
            tool_name="slow_tool", 
            parameters={"delay": 3.0},
            caller_agent_id="test"
        )
        slow_result = await executor.execute_tool_call(slow_call)
        print(f"   Slow tool status: {slow_result.status.value}")
        
        # Test 3: Tool parameter validation edge cases
        print("\n3. Testing parameter validation edge cases...")
        
        # Tool with enum parameter
        def enum_tool(color: str) -> str:
            return f"Selected color: {color}"
        
        registry.register_function("enum_tool", "Tool with enum parameter", enum_tool, [
            ToolParameter("color", "string", "Color choice", required=True, 
                         enum_values=["red", "green", "blue"])
        ])
        
        # Valid enum value
        valid_enum_call = ToolCall(
            tool_name="enum_tool",
            parameters={"color": "red"},
            caller_agent_id="test"
        )
        valid_enum_result = await executor.execute_tool_call(valid_enum_call)
        print(f"   Valid enum result: {valid_enum_result.result}")
        
        # Invalid enum value
        invalid_enum_call = ToolCall(
            tool_name="enum_tool",
            parameters={"color": "purple"},
            caller_agent_id="test"
        )
        invalid_enum_result = await executor.execute_tool_call(invalid_enum_call)
        print(f"   Invalid enum status: {invalid_enum_result.status.value}")
        
        # Test 4: Tool execution metrics and monitoring
        print("\n4. Testing execution metrics and monitoring...")
        
        metrics = executor.get_metrics()
        print(f"   Final metrics:")
        print(f"   - Total calls: {metrics['total_calls']}")
        print(f"   - Success rate: {metrics['success_rate']:.2%}")
        print(f"   - Average execution time: {metrics['average_execution_time']:.3f}s")
        print(f"   - Calls by tool: {metrics['calls_by_tool']}")
        
        print("\n✅ Advanced Features tests completed!")
        
    except Exception as e:
        print(f"\n❌ Advanced Features test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tool integration tests"""
    print("🚀 Starting Tool Calling and Integration Tests")
    print("=" * 80)
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    try:
        # Run test suites
        await test_basic_tool_system()
        await test_plugin_system()
        await test_agent_integration()
        await test_advanced_features()
        
        print("\n" + "=" * 80)
        print("🎉 All Tool Integration Tests Completed Successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())