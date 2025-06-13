import os
import argparse
import requests

from langgraph.graph import Graph, START, END
from langchain.chat_models import init_chat_model
from langchain.prompts import PromptTemplate

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
        with open(source, 'r') as f:
            return f.read()

# Instantiate the LLM client once
llm = init_chat_model(
    "meta.llama3-8b-instruct-v1:0",
    model_provider="bedrock",
    region="ap-south-1"
)

# ====================
# Node functions
# ====================
def analysis_node(inputs: dict) -> dict:
    """
    Expects inputs["json_input"] → returns {"analysis_output": ...}
    """
    json_input = inputs.get("json_input", "")
    prompt_text = (
        "You are a seasoned security analyst. "
        "Given the following JSON-based machine learning security assessment:\n\n"
        f"{json_input}\n\n"
        "Analyze it for security vulnerabilities, risks, and inconsistencies. "
        "Produce a bullet-point list of findings, each with severity and impact."
    )
    result = llm.invoke(prompt_text)
    return {"analysis_output": result}

def report_node(inputs: dict) -> dict:
    """
    Expects inputs["analysis_output"] and inputs["report_format"] → returns {"report_output": ...}
    """
    analysis_output = inputs.get("analysis_output", "")
    report_format = inputs.get("report_format", "md")
    report_template = PromptTemplate.from_template(
        "You are a security summary writer. "
        "Based on the security analysis below, write a clear, structured conclusion report in {report_format} format. "
        "Include the most critical findings, formatted professionally."
        "\n\nSecurity Analysis:\n{analysis_output}"
    )
    prompt_text = report_template.format(
        analysis_output=analysis_output,
        report_format=report_format
    )
    result = llm.invoke(prompt_text)
    return {"report_output": result}

# ====================
# Build LangGraph Workflow
# ====================
def build_langgraph() -> Graph:
    """
    Constructs a LangGraph Graph with two function nodes:
    - "analysis": calls analysis_node
    - "report": calls report_node
    """
    graph = Graph()
    # Depending on your LangGraph version, you may need to specify input_keys/output_keys:
    try:
        graph.add_node("analysis", analysis_node,
                       input_keys=["json_input"],
                       output_keys=["analysis_output"])
        graph.add_node("report", report_node,
                       input_keys=["analysis_output", "report_format"],
                       output_keys=["report_output"])
    except TypeError:
        # If add_node doesn’t accept input_keys/output_keys, register simply
        graph.add_node("analysis", analysis_node)
        graph.add_node("report", report_node)

    # Now add the edge from analysis → report. Try positional key signature.
    try:
        # common signature: add_edge(src_name, dest_name, src_key, dest_key)
        graph.add_edge(START, "analysis")
        
        graph.add_edge("analysis", "report", "analysis_output", "analysis_output")
    except TypeError:
        # If that fails, inspect signature or try alternative forms:
        # For some versions: add_edge(src, dest)
        try:
            graph.add_edge("analysis", "report")
            # In this case LangGraph may auto-wire matching keys by name.
        except Exception as e:
            print("⚠️ Warning: could not add explicit edge mapping:", e)
            # Let it run; if auto-wiring is supported, it may still work.

    return graph

# ====================
# CLI Interface
# ====================
def main():
    parser = argparse.ArgumentParser(description="Run security assessment via LangGraph")
    parser.add_argument('--source', type=str, required=True, help="GitHub raw URL or local path to a JSON report")
    parser.add_argument('--format', type=str, choices=['txt', 'md', 'pdf'], default='md', help="Output format for the report")
    args = parser.parse_args()

    output_file = f"output/conclusion_report.{args.format}"
    os.makedirs("output", exist_ok=True)

    json_string = load_json_source(args.source)
    print(f"✅ JSON string loaded. Length: {len(json_string)} characters.")
    max_chars = 8000
    if len(json_string) > max_chars:
        print(f"⚠️ Truncating JSON input from {len(json_string)} to {max_chars} chars.")
    json_cleaned = json_string.replace("```", "").replace("\\n", "\n")
    json_data_truncated = json_cleaned[:max_chars]

    graph = build_langgraph()
    try:
        compiled = graph.compile()
        result = compiled.invoke({
            "json_input": json_data_truncated,
            "report_format": args.format
        })
        report = result.get("report_output", "")
        print(report)
    except Exception as e:
        import traceback
        print("\n❌ Exception during LangGraph execution:")
        traceback.print_exc()
        report = "LangGraph execution failed. See error log above."

    # Handle PDF conversion if needed; here we just write text/markdown
    with open(output_file, "w") as f:
        f.write(report)
    print(f"\n✅ Final report written to: {output_file}")

if __name__ == "__main__":
    main()
