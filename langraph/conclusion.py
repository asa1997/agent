import os
import argparse
import requests
from typing_extensions import TypedDict
from typing import Annotated

from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate

from langgraph.graph import StateGraph, START, END
# Built-in reducer to append to a list safely
from langgraph.graph.message import add_messages

# =======================
# Manual JSON Loader
# =======================
def load_json_source(source: str) -> str:
    print(f"🔍 Loading JSON from: {source}")
    if source.startswith("http"):
        try:
            res = requests.get(source)
            res.raise_for_status()
            return res.text
        except Exception as e:
            return f"Failed to fetch from GitHub: {e}"
    else:
        if not os.path.exists(source):
            return f"File not found: {source}"
        with open(source, "r") as f:
            return f.read()

# =======================
# Define Graph State
# =======================
class State(TypedDict):
    json_input: str
    report_format: str
    analysis_output: str
    report_output: str
    messages: Annotated[list, add_messages]

# =======================
# LLM Client (Bedrock-backed Llama3)
llm = init_chat_model(
    "meta.llama3-8b-instruct-v1:0",
    model_provider="bedrock",
    region="ap-south-1"
)

# ====================
# Nodes
# ====================
def analysis_node(state: State) -> dict:
    prompt = (
        "You are a seasoned Cybersecurity Analyst with years of experience in the industry. "
        "Your task is to analyze a raw JSON report from a security assessment done on an LLM. "
        "Given is the raw JSON report of the security assessment on the LLM :\n\n"
        f"{state['json_input']}\n\n"
        "Analyze from a security standpoint and draw a conclusion regarding the safety of using this LLM."
        "Your findings should be useful for both organizations and individuals who are considering using this LLM."
    )
    out = llm.invoke(prompt)
    return {"analysis_output": out}

def report_node(state: State) -> dict:
    template = PromptTemplate.from_template(
        "You are a security summary writer. "
        "Based on this analysis:\n\n{analysis_output}\n\n"
        "Write a clear, structured conclusion report in {report_format} format."
        "The report should be concise, actionable, and suitable for all kinds of audience."
        "Ensure it includes all critical findings and recommendations."
        
    )
    prompt = template.format(
        analysis_output=state["analysis_output"],
        report_format=state["report_format"]
    )
    out = llm.invoke(prompt)
    return {"report_output": out}

# ====================
# Build StateGraph
# ====================
def build_langgraph() -> StateGraph:
    graph = StateGraph(State)
    graph.add_node("analysis", analysis_node)
    graph.add_node("report", report_node)

    graph.add_edge(START, "analysis")
    graph.add_edge("analysis", "report")
    graph.add_edge("report", END)

    return graph

# ====================
# CLI Interface
# ====================
def main():
    parser = argparse.ArgumentParser(description="Run security assessment via LangGraph")
    parser.add_argument("--source", type=str, required=True)
    parser.add_argument("--format", choices=["txt", "md", "pdf"], default="md")
    args = parser.parse_args()

    raw = load_json_source(args.source)
    print(f"✅ JSON loaded. Length: {len(raw)} chars.")
    clean = raw.replace("```", "").replace("\\n", "\n")
    truncated = clean[:8000]

    graph = build_langgraph()
    compiled = graph.compile()

    try:
        result = compiled.invoke({
            "json_input": truncated,
            "report_format": args.format,
            "messages": []
        })
        report_msg = result["report_output"]
        if hasattr(report_msg, "content"):
            report = report_msg.content
        elif hasattr(report_msg, "text"):
            report = report_msg.text()
        else:
            report = str(report_msg)
        print(report)
    except Exception as e:
        import traceback
        print("\n❌ LangGraph execution error:")
        traceback.print_exc()
        report = "Execution failed."

    outpath = f"output/conclusion_report.{args.format}"
    os.makedirs("output", exist_ok=True)
    with open(outpath, "w") as f:
        f.write(report)
    print(f"\n✅ Final report written to: {outpath}")

if __name__ == "__main__":
    main()
