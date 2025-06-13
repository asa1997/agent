import os
import json
import argparse
import requests

# LangGraph and LangChain imports
from langgraph.graph import Graph, START
from langgraph.nodes import LLMNode
# from langchain.chat_models import Ollama
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

llm = init_chat_model(
        # "anthropic.claude-3-sonnet-20240229-v1:0",
        "meta.llama3-8b-instruct-v1:0",
        model_provider="bedrock",
        region="ap-south-1"
    )

def analysis_node(inputs):
    json_input = inputs["json_input"]
    prompt = (
        "You are a seasoned security analyst. "
        "Given the following JSON-based machine learning security assessment:\n\n"
        f"{json_input}\n\n"
        "Analyze it for security vulnerabilities, risks, and inconsistencies. "
        "Produce a bullet-point list of findings, each with severity and impact."
    )
    result = llm.invoke(prompt)
    return {"analysis_output": result}
# ====================
# Build LangGraph Workflow
# ====================
def build_langgraph(json_string: str, report_format: str):
    """
    Constructs a LangGraph Graph with two nodes:
    - analysis_node: analyzes the JSON for security findings.
    - report_node: summarizes the analysis into the desired format.
    """

    # Instantiate the LLM client (using OllamaLLM via LangChain)
    # llm = Ollama(model="llama3", temperature=0.2)
    



    # # Prompt for analysis step
    # analysis_template = PromptTemplate.from_template(
    #     "You are a seasoned security analyst. "
    #     "Given the following JSON-based machine learning security assessment:\n\n"
    #     "{json_input}\n\n"
    #     "Analyze it for security vulnerabilities, risks, and inconsistencies. "
    #     "Produce a bullet-point list of findings, each with severity and impact."
    # )
    # analysis_node = LLMNode(
    #     llm=llm,
    #     prompt=analysis_template,
    #     input_keys=["json_input"],
    #     output_key="analysis_output"
    # )

    # Prompt for reporting step
    report_template = PromptTemplate.from_template(
        "You are a security summary writer. "
        "Based on the security analysis below, write a clear, structured conclusion report in {report_format} format. "
        "Include the most critical findings, formatted professionally."
        "\n\nSecurity Analysis:\n{analysis_output}"
    )
    report_node = LLMNode(
        llm=llm,
        prompt=report_template,
        input_keys=["analysis_output", "report_format"],
        output_key="report_output"
    )

    # Build graph
    graph = Graph()
    graph.add_node("analysis", analysis_node)
    graph.add_node("report", report_node)

    # Wire outputs: analysis_output feeds into report node’s input
    graph.add_edge("analysis", "report", mapping={"analysis_output": "analysis_output"})
    # Also wire report_format into report node from root inputs
    # LangGraph automatically passes unchanged inputs if the node’s input_keys include them
    # So ensure when running, we supply both json_input and report_format

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

    # Load JSON manually
    json_string = load_json_source(args.source)
    print(f"✅ JSON string loaded. Length: {len(json_string)} characters.")
    max_chars = 8000
    if len(json_string) > max_chars:
        print(f"⚠️ Truncating JSON input from {len(json_string)} to {max_chars} chars.")
    json_cleaned = json_string.replace("```", "").replace("\\n", "\n")
    json_data_truncated = json_cleaned[:max_chars]

    # Build and run the graph
    graph = build_langgraph(json_data_truncated, args.format)
    try:
        # graph.run takes a dict of root inputs matching input_keys used by nodes
        result = graph.run({
            "json_input": json_data_truncated,
            "report_format": args.format
        })
        report = result["report_output"]
        print(report)
    except Exception as e:
        import traceback
        print("\n❌ Exception during LangGraph execution:")
        traceback.print_exc()
        report = "LangGraph execution failed. See error log above."

    # Write output
    with open(output_file, "w") as f:
        f.write(report)
    print(f"\n✅ Final report written to: {output_file}")

if __name__ == "__main__":
    main()
