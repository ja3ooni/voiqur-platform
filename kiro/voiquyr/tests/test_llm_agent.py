"""
Test script for LLM Agent implementation
Tests dialog management, tool calling, and integration capabilities
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agents.llm_agent import LLMAgent
from core.messaging import MessageBus
from core.models import AgentMessage


async def test_llm_agent():
    """Test LLM Agent functionality"""
    print("Testing LLM Agent Implementation...")
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create message bus (mock)
    message_bus = MessageBus()
    
    # Create LLM agent
    agent = LLMAgent("llm_agent_test", message_bus)
    
    try:
        # Test 1: Initialize agent
        print("\n1. Testing agent initialization...")
        success = await agent.initialize()
        print(f"   Initialization: {'SUCCESS' if success else 'FAILED'}")
        
        if not success:
            print("   Agent initialization failed, stopping tests")
            return
        
        # Test 2: Process simple message
        print("\n2. Testing simple message processing...")
        result = await agent.process_message("Hello, how are you?")
        print(f"   Response: {result.get('response', 'No response')}")
        print(f"   Intent: {result.get('intent', 'No intent')}")
        print(f"   Session ID: {result.get('session_id', 'No session')}")
        
        # Test 3: Process message with tool calling
        print("\n3. Testing tool calling...")
        result = await agent.process_message("What time is it?")
        print(f"   Response: {result.get('response', 'No response')}")
        print(f"   Tool calls: {len(result.get('tool_calls', []))}")
        print(f"   Tool results: {len(result.get('tool_results', []))}")
        
        # Test 4: Test weather query
        print("\n4. Testing weather query...")
        result = await agent.process_message("What's the weather like in Paris?")
        print(f"   Response: {result.get('response', 'No response')}")
        print(f"   Intent: {result.get('intent', 'No intent')}")
        print(f"   Entities: {result.get('entities', {})}")
        
        # Test 5: Test session continuity
        print("\n5. Testing session continuity...")
        session_id = result.get('session_id')
        if session_id:
            result2 = await agent.process_message("And what about tomorrow?", session_id=session_id)
            print(f"   Follow-up response: {result2.get('response', 'No response')}")
            print(f"   Same session: {result2.get('session_id') == session_id}")
        
        # Test 6: Test interruption handling
        print("\n6. Testing interruption handling...")
        if session_id:
            interruption_result = await agent.handle_interruption(
                session_id, "Actually, tell me a joke instead"
            )
            print(f"   Interruption response: {interruption_result.get('response', 'No response')}")
            print(f"   Context switched: {interruption_result.get('interruption_handled', False)}")
        
        # Test 7: Test available tools
        print("\n7. Testing tool registry...")
        tools = agent.get_available_tools()
        print(f"   Available tools: {tools}")
        
        # Test 8: Test performance metrics
        print("\n8. Testing performance metrics...")
        metrics = agent.get_performance_metrics()
        print(f"   Total messages processed: {metrics.get('total_messages_processed', 0)}")
        print(f"   Average response time: {metrics.get('average_response_time', 0):.3f}s")
        print(f"   Tool success rate: {metrics.get('tool_success_rate', 0):.2%}")
        
        # Test 9: Test agent message handling
        print("\n9. Testing agent message handling...")
        test_message = AgentMessage(
            sender_id="test_agent",
            receiver_id=agent.agent_id,
            message_type="status_request",
            payload={}
        )
        
        response_message = await agent.handle_message(test_message)
        if response_message:
            print(f"   Message handled: {response_message.message_type}")
            print(f"   Response payload keys: {list(response_message.payload.keys())}")
        
        # Test 10: Test session cleanup
        print("\n10. Testing session cleanup...")
        await agent.cleanup_expired_sessions()
        print("   Session cleanup completed")
        
        print("\n✅ All LLM Agent tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await agent.shutdown()
        print("\n🔄 Agent shutdown completed")


async def test_dialog_manager():
    """Test Dialog Manager functionality"""
    print("\n" + "="*50)
    print("Testing Dialog Manager...")
    
    from agents.dialog_manager import DialogManager
    
    dialog_manager = DialogManager()
    
    try:
        # Test 1: Create session
        print("\n1. Testing session creation...")
        session = dialog_manager.create_session(user_id="test_user", language="en")
        print(f"   Session created: {session.session_id}")
        
        # Test 2: Process turns
        print("\n2. Testing turn processing...")
        result = await dialog_manager.process_turn(
            session.session_id, 
            "I want to book a table for dinner",
            intent="booking"
        )
        print(f"   Action: {result['action']['action']}")
        print(f"   Dialog state: {result['dialog_state']}")
        
        # Test 3: Process follow-up
        print("\n3. Testing follow-up turn...")
        result = await dialog_manager.process_turn(
            session.session_id,
            "For 4 people at 7 PM tomorrow",
            entities={"number": ["4"], "time": ["7 PM"], "date": ["tomorrow"]}
        )
        print(f"   Action: {result['action']['action']}")
        print(f"   Dialog state: {result['dialog_state']}")
        
        # Test 4: Get context
        print("\n4. Testing context retrieval...")
        context = dialog_manager.get_session_context(session.session_id)
        if context:
            print(f"   Turn count: {context['session_summary']['turn_count']}")
            print(f"   Current frame: {context['current_frame']['task_type'] if context['current_frame'] else 'None'}")
        
        print("\n✅ Dialog Manager tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Dialog Manager test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_tool_system():
    """Test Tool System functionality"""
    print("\n" + "="*50)
    print("Testing Tool System...")
    
    from agents.tool_integration import ToolRegistry, ToolExecutor, ToolParameter, ToolCall
    
    try:
        # Test 1: Create tool registry
        print("\n1. Testing tool registry...")
        registry = ToolRegistry()
        
        # Test 2: Register a simple function
        print("\n2. Testing function registration...")
        
        def simple_add(a: int, b: int) -> int:
            return a + b
        
        success = registry.register_function(
            name="add_numbers",
            description="Add two numbers together",
            function=simple_add,
            parameters=[
                ToolParameter("a", "integer", "First number", required=True),
                ToolParameter("b", "integer", "Second number", required=True)
            ]
        )
        print(f"   Function registered: {success}")
        
        # Test 3: Test tool execution
        print("\n3. Testing tool execution...")
        executor = ToolExecutor(registry)
        
        tool_call = ToolCall(
            tool_name="add_numbers",
            parameters={"a": 5, "b": 3},
            caller_agent_id="test"
        )
        
        result = await executor.execute_tool_call(tool_call)
        print(f"   Execution status: {result.status.value}")
        print(f"   Result: {result.result}")
        print(f"   Execution time: {result.execution_time:.3f}s")
        
        # Test 4: Test OpenAI format
        print("\n4. Testing OpenAI function format...")
        openai_functions = registry.get_openai_functions()
        print(f"   Functions in OpenAI format: {len(openai_functions)}")
        if openai_functions:
            print(f"   First function: {openai_functions[0]['name']}")
        
        # Test 5: Test metrics
        print("\n5. Testing execution metrics...")
        metrics = executor.get_metrics()
        print(f"   Total calls: {metrics['total_calls']}")
        print(f"   Success rate: {metrics['success_rate']:.2%}")
        
        print("\n✅ Tool System tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Tool System test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    async def main():
        await test_llm_agent()
        await test_dialog_manager()
        await test_tool_system()
    
    asyncio.run(main())