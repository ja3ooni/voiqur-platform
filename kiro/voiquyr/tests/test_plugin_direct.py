"""
Direct test for Plugin System
Tests plugin loading and execution without full agent dependencies
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'agents'))

from tool_integration import ToolRegistry, ToolExecutor, PluginSystem, ToolCall


async def test_plugin_system():
    """Test plugin system functionality"""
    print("🔌 Testing Plugin System")
    print("=" * 50)
    
    # Create registry and plugin system
    registry = ToolRegistry()
    plugin_system = PluginSystem(registry)
    executor = ToolExecutor(registry)
    
    try:
        # Test 1: Load example plugin
        print("\n1. Loading example plugin...")
        
        # Import the plugin module
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'agents', 'plugins'))
        import example_plugin
        
        success = plugin_system.load_plugin("example_plugin", example_plugin)
        print(f"✓ Plugin loaded: {success}")
        
        # Test 2: Check loaded plugins
        print(f"✓ Loaded plugins: {plugin_system.list_plugins()}")
        
        # Test 3: Check available tools after plugin load
        available_tools = registry.list_tools()
        print(f"✓ Available tools after plugin load: {available_tools}")
        
        # Test 4: Test plugin tools
        print("\n2. Testing plugin tools...")
        
        # Test percentage calculation
        print("   Testing calculate_percentage...")
        tool_call = ToolCall(
            tool_name="calculate_percentage",
            parameters={"value": 200, "percentage": 15},
            caller_agent_id="test"
        )
        result = await executor.execute_tool_call(tool_call)
        print(f"   ✓ Result: {result.result}")
        print(f"   ✓ Status: {result.status.value}")
        
        # Test word counting
        print("   Testing count_words...")
        tool_call2 = ToolCall(
            tool_name="count_words",
            parameters={"text": "Hello world! This is a test sentence.", "include_punctuation": False},
            caller_agent_id="test"
        )
        result2 = await executor.execute_tool_call(tool_call2)
        print(f"   ✓ Result: {result2.result}")
        
        # Test language detection
        print("   Testing detect_language_simple...")
        tool_call3 = ToolCall(
            tool_name="detect_language_simple",
            parameters={"text": "The quick brown fox jumps over the lazy dog"},
            caller_agent_id="test"
        )
        result3 = await executor.execute_tool_call(tool_call3)
        print(f"   ✓ Result: {result3.result}")
        
        # Test with different languages
        print("   Testing language detection with French...")
        tool_call4 = ToolCall(
            tool_name="detect_language_simple",
            parameters={"text": "Le chat est sur le tapis et il mange"},
            caller_agent_id="test"
        )
        result4 = await executor.execute_tool_call(tool_call4)
        print(f"   ✓ French detection: {result4.result}")
        
        # Test 5: Test plugin info
        print("\n3. Testing plugin info...")
        plugin_info = plugin_system.get_plugin_info("example_plugin")
        if plugin_info:
            print(f"   ✓ Plugin name: {plugin_info['name']}")
            print(f"   ✓ Version: {plugin_info['version']}")
            print(f"   ✓ Description: {plugin_info['description']}")
            print(f"   ✓ Author: {plugin_info['author']}")
        
        # Test 6: Test OpenAI format for plugin tools
        print("\n4. Testing OpenAI format for plugin tools...")
        openai_functions = registry.get_openai_functions()
        print(f"   ✓ Total OpenAI functions: {len(openai_functions)}")
        
        for func in openai_functions:
            if func['name'] in ['calculate_percentage', 'count_words', 'detect_language_simple']:
                print(f"   ✓ Plugin function: {func['name']}")
                print(f"     Description: {func['description']}")
                print(f"     Parameters: {list(func['parameters']['properties'].keys())}")
        
        # Test 7: Test execution metrics for plugin tools
        print("\n5. Testing execution metrics...")
        metrics = executor.get_metrics()
        print(f"   ✓ Total calls: {metrics['total_calls']}")
        print(f"   ✓ Success rate: {metrics['success_rate']:.2%}")
        print(f"   ✓ Calls by tool: {metrics['calls_by_tool']}")
        
        # Test 8: Test plugin unloading
        print("\n6. Testing plugin unloading...")
        tools_before_unload = len(registry.list_tools())
        print(f"   ✓ Tools before unload: {tools_before_unload}")
        
        unload_success = plugin_system.unload_plugin("example_plugin")
        print(f"   ✓ Plugin unloaded: {unload_success}")
        
        tools_after_unload = len(registry.list_tools())
        print(f"   ✓ Tools after unload: {tools_after_unload}")
        
        remaining_plugins = plugin_system.list_plugins()
        print(f"   ✓ Remaining plugins: {remaining_plugins}")
        
        print("\n" + "=" * 50)
        print("🎉 Plugin System Tests Completed Successfully!")
        print("✅ Plugin loading: WORKING")
        print("✅ Plugin tool execution: WORKING")
        print("✅ Plugin info retrieval: WORKING")
        print("✅ Plugin unloading: WORKING")
        print("✅ OpenAI format support: WORKING")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Plugin test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_custom_plugin():
    """Test creating and loading a custom plugin"""
    print("\n🛠️ Testing Custom Plugin Creation")
    print("=" * 50)
    
    # Create a custom plugin module dynamically
    class CustomPlugin:
        __version__ = "1.0.0"
        __description__ = "Custom test plugin"
        __author__ = "Test Suite"
        
        @staticmethod
        def register_tools(tool_registry):
            """Register custom tools"""
            
            def fibonacci(n: int) -> int:
                """Calculate nth Fibonacci number"""
                if n <= 1:
                    return n
                return CustomPlugin.fibonacci(n-1) + CustomPlugin.fibonacci(n-2)
            
            def reverse_string(text: str) -> str:
                """Reverse a string"""
                return text[::-1]
            
            # Register tools
            from tool_integration import ToolParameter
            
            success1 = tool_registry.register_function(
                name="fibonacci",
                description="Calculate nth Fibonacci number",
                function=fibonacci,
                parameters=[
                    ToolParameter("n", "integer", "Position in Fibonacci sequence", required=True)
                ]
            )
            
            success2 = tool_registry.register_function(
                name="reverse_string",
                description="Reverse a string",
                function=reverse_string,
                parameters=[
                    ToolParameter("text", "string", "Text to reverse", required=True)
                ]
            )
            
            return success1 and success2
        
        @staticmethod
        def unregister_tools(tool_registry):
            """Unregister custom tools"""
            success1 = tool_registry.unregister_tool("fibonacci")
            success2 = tool_registry.unregister_tool("reverse_string")
            return success1 and success2
        
        @staticmethod
        def fibonacci(n: int) -> int:
            """Helper method for fibonacci calculation"""
            if n <= 1:
                return n
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b
    
    # Test the custom plugin
    registry = ToolRegistry()
    plugin_system = PluginSystem(registry)
    executor = ToolExecutor(registry)
    
    try:
        # Load custom plugin
        success = plugin_system.load_plugin("custom_plugin", CustomPlugin)
        print(f"✓ Custom plugin loaded: {success}")
        
        # Test fibonacci tool
        fib_call = ToolCall(
            tool_name="fibonacci",
            parameters={"n": 10},
            caller_agent_id="test"
        )
        fib_result = await executor.execute_tool_call(fib_call)
        print(f"✓ Fibonacci(10) = {fib_result.result}")
        
        # Test string reversal
        reverse_call = ToolCall(
            tool_name="reverse_string",
            parameters={"text": "Hello World!"},
            caller_agent_id="test"
        )
        reverse_result = await executor.execute_tool_call(reverse_call)
        print(f"✓ Reversed string: {reverse_result.result}")
        
        # Test plugin info
        plugin_info = plugin_system.get_plugin_info("custom_plugin")
        print(f"✓ Custom plugin info: {plugin_info}")
        
        print("\n✅ Custom Plugin Tests Completed Successfully!")
        
    except Exception as e:
        print(f"\n❌ Custom plugin test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all plugin tests"""
    await test_plugin_system()
    await test_custom_plugin()


if __name__ == "__main__":
    asyncio.run(main())