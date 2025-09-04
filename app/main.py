import sys
import os
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from pydantic import SecretStr
from app.agent.tools import all_tools
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.config import OPENAI_API_KEY, AGENT_MODEL_NAME

def main() -> None:
    load_dotenv()
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set")
        return
    
    model = ChatOpenAI(
        api_key=SecretStr(OPENAI_API_KEY),
        model=AGENT_MODEL_NAME,
        temperature=0
    )
    model_with_tools = model.bind_tools(all_tools)
    
    print("AI Medical Scheduler CLI. Type 'exit' to end.")
    conversation_history = []
    
    while True:
        try:
            user_input = input("You: ")
            
            if user_input.lower() == 'exit':
                print("AI: Thank you for using the scheduler. Goodbye!")
                break

            conversation_history.append(HumanMessage(content=user_input))
            messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + conversation_history
            response = model_with_tools.invoke(messages)
            conversation_history.append(response)
            print(f"AI: {response.content}")
            
            # If there are tool calls, execute them
            if hasattr(response, 'additional_kwargs') and response.additional_kwargs.get('tool_calls'):
                tool_calls = response.additional_kwargs['tool_calls']
                # Process tool calls and collect results
                tool_messages = []
                for tool_call in tool_calls:
                    try:
                        # Handle nested function structure
                        if 'function' in tool_call:
                            tool_name = tool_call['function'].get('name', '')
                            tool_args_str = tool_call['function'].get('arguments', '{}')
                        else:
                            tool_name = tool_call.get('name', '')
                            tool_args_str = tool_call.get('args', '{}')
                        
                        import json
                        try:
                            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                        except:
                            tool_args = {}
                        tool_func = next((t for t in all_tools if t.name == tool_name), None)
                        
                        if tool_func:
                            result = tool_func.invoke(tool_args)
                            tool_message = ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call.get('id', '')
                            )
                            tool_messages.append(tool_message)
                        else:
                            tool_message = ToolMessage(
                                content=f"Tool {tool_name} not found",
                                tool_call_id=tool_call.get('id', '')
                            )
                            tool_messages.append(tool_message)
                            
                    except Exception as e:
                        print(f"[Tool call error: {str(e)}]")
                        tool_message = ToolMessage(
                            content=f"Tool call error: {str(e)}",
                            tool_call_id=tool_call.get('id', '')
                        )
                        tool_messages.append(tool_message)
                
                conversation_history.extend(tool_messages)
                follow_up_messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + conversation_history
                follow_up_response = model_with_tools.invoke(follow_up_messages)
                conversation_history.append(follow_up_response)
                print(f"AI: {follow_up_response.content}")

        except KeyboardInterrupt:
            print("\nAI: Conversation ended. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            break

if __name__ == "__main__":
    main()

