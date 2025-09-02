import sys
import os
from dotenv import load_dotenv

# Add the project root to the Python path
# This allows us to import modules from the 'app' directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from pydantic import SecretStr
from app.agent.tools import all_tools
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from app.config import OPENAI_API_KEY, AGENT_MODEL_NAME

def main():
    """
    The main function to run the AI scheduling agent chat application.
    """
    # Load environment variables from .env file (for the API key)
    load_dotenv()
    
    # Initialize the model with tools
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in .env file")
        return
    
    model = ChatOpenAI(api_key=SecretStr(OPENAI_API_KEY), model=AGENT_MODEL_NAME, temperature=0)
    model_with_tools = model.bind_tools(all_tools)
    
    print("AI Medical Scheduler is ready. Type 'exit' to end the conversation.")
    print("="*60)
    
    # This list will hold the conversation history
    conversation_history = []
    
    while True:
        try:
            # Get input from the user
            user_input = input("You: ")
            
            if user_input.lower() == 'exit':
                print("AI: Thank you for using the scheduler. Goodbye!")
                break

            # Add the user's message to the history
            conversation_history.append(HumanMessage(content=user_input))
            
            # Create messages with system prompt
            messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + conversation_history
            
            # Get response from the model
            print("AI is thinking...", end="", flush=True)
            response = model_with_tools.invoke(messages)
            
            # Clear the "thinking" message
            print("\r" + " " * 20 + "\r", end="")
            
            # Add the AI's response to the history
            conversation_history.append(response)
            
            # Print the AI's response
            print(f"AI: {response.content}")
            
            # If there are tool calls, execute them
            if hasattr(response, 'additional_kwargs') and response.additional_kwargs.get('tool_calls'):
                tool_calls = response.additional_kwargs['tool_calls']
                print(f"[Debug: Found {len(tool_calls)} tool calls]")
                
                # Process all tool calls and collect results
                tool_messages = []
                for tool_call in tool_calls:
                    try:
                        print(f"[Debug: Tool call structure: {tool_call}]")
                        
                        # Handle the nested function structure
                        if 'function' in tool_call:
                            tool_name = tool_call['function'].get('name', '')
                            tool_args_str = tool_call['function'].get('arguments', '{}')
                        else:
                            tool_name = tool_call.get('name', '')
                            tool_args_str = tool_call.get('args', '{}')
                        
                        # Parse arguments if they're a string
                        import json
                        try:
                            tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                        except:
                            tool_args = {}
                        
                        # Find the tool function
                        tool_func = None
                        for tool in all_tools:
                            if tool.name == tool_name:
                                tool_func = tool
                                break
                        
                        if tool_func:
                            # Execute the tool
                            result = tool_func.invoke(tool_args)
                            print(f"[Tool {tool_name} executed: {result}]")
                            
                            # Create tool message
                            tool_message = ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call.get('id', '')
                            )
                            tool_messages.append(tool_message)
                        else:
                            print(f"[Tool {tool_name} not found]")
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
                
                # Add all tool messages to conversation history
                conversation_history.extend(tool_messages)
                
                # Get follow-up response from AI with all tool results
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

