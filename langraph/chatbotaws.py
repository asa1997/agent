from typing import Annotated
from typing_extensions import TypedDict

from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from langchain_core.messages import ToolMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
import json

# 🚀 Tools setup
tool = TavilySearch(max_results=2)
tools = [tool]

# 📦 Graph State
class State(TypedDict):
    messages: Annotated[list, add_messages]

# ⛓️ Build Tool Executor Node
class BasicToolNode:
    def __init__(self, tools: list):
        self.tools = {t.name: t for t in tools}

    def __call__(self, state: State) -> dict:
        last: AIMessage = state["messages"][-1]
        if not getattr(last, "tool_calls", []):
            print("🧭 No tool_call found; skipping tool node.")
            return {"messages": []}
        outputs = []
        for call in last.tool_calls:
            print(f"🧩 Executing tool: {call['name']} with args {call['args']}")
            res = self.tools[call["name"]].invoke(call["args"])
            outputs.append(ToolMessage(content=json.dumps(res), name=call["name"], tool_call_id=call["id"]))
        return {"messages": outputs}

tool_node = BasicToolNode(tools)

# 💬 LLM & bound tools
# llm = init_chat_model(
#     "meta.llama3-8b-instruct-v1:0",
#     model_provider="bedrock",
#     region="ap-south-1"
# )
llm = init_chat_model(
    "llama3.2:latest",
    model_provider="ollama",
)
llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State) -> dict:
    msgs = state["messages"]
    response: AIMessage = llm_with_tools.invoke(msgs)
    if getattr(response, "tool_calls", None):
        print("🤖 Model issued tool_calls:", response.tool_calls)
    else:
        print("🤖 Model responded with no tool_calls.")
    return {"messages": [response]}

# 🧠 Routing logic
def route_tools(state: State):
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END

# 🔁 Build and compile the graph
graph = StateGraph(State)
graph.add_node("chatbot", chatbot)
graph.add_node("tools", tool_node)
graph.add_edge(START, "chatbot")
graph.add_conditional_edges("chatbot", route_tools, {"tools": "tools", END: END})
graph.add_edge("tools", "chatbot")
compiled = graph.compile()

# 🎤 Interactive loop
def stream_graph_updates(user_input: str):
    # Use stream_mode="values" to emit full state
    for event in compiled.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        stream_mode="values"
    ):
        # Each event is a dict with state keys
        if "messages" in event and event["messages"]:
            last_msg = event["messages"][-1]
            print("Assistant:", last_msg.content)


if __name__ == "__main__":
    while True:
        ui = input("User: ")
        if ui.lower() in ("quit", "exit"):
            break
        stream_graph_updates(ui)
