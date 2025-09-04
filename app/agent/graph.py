# The agent now uses direct model invocation in main.py instead of LangGraph.

# If you want to use LangGraph in the future, you can uncomment and modify this code.

"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from pydantic import SecretStr
from app.agent.state import AgentState
from app.agent.tools import all_tools
from app.agent.prompts import AGENT_SYSTEM_PROMPT
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.config import OPENAI_API_KEY, AGENT_MODEL_NAME

# Initialize the Language Model and Tools
model = ChatOpenAI(api_key=SecretStr(OPENAI_API_KEY), model=AGENT_MODEL_NAME, temperature=0)
model_with_tools = model.bind_tools(all_tools)
tool_node = ToolNode(all_tools)

def agent_node(state: AgentState):
    messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + state['messages']
    response = model_with_tools.invoke(messages)
    return {"messages": [response]}

def router_node(state: AgentState):
    last_message = state['messages'][-1]
    if hasattr(last_message, 'additional_kwargs') and last_message.additional_kwargs.get('tool_calls'):
        return "call_tools"
    else:
        return "end"

# Build the Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", router_node, {"call_tools": "tools", "end": END})
workflow.add_edge("tools", "agent")
agent_graph = workflow.compile()
"""