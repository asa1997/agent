import os
import json
import argparse
import requests
from crewai import Agent, Task, Crew, Process
from langchain_community.llms.ollama import Ollama

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


# ====================
# Agent & Task Setup
# ====================
def build_crew(json_string: str, report_format: str):
    llm = Ollama(model="deepseek-r1:7b", temperature=0.2)

    analyst = Agent(
        role='Security Analyst',
        goal='Identify vulnerabilities and risks in the report',
        backstory='A seasoned security professional experienced in analyzing JSON-based assessments.',
        allow_delegation=False,
        verbose=True,
        llm=llm
    )

    reporter = Agent(
        role='Security Summary Writer',
        goal='Create a clear, structured conclusion report',
        backstory='An expert communicator who specializes in technical cybersecurity reporting.',
        allow_delegation=False,
        verbose=True,
        llm=llm
    )

    task1 = Task(
        description=(
            "You are given a raw JSON report from a machine learning security assessment. "
            "Below is the JSON content:\n\n"
            f"{json_string}\n\n"
            "Analyze it for security vulnerabilities, risks, and inconsistencies. "
            "Your output should be a bullet-point list of findings including severity and impact."
        ),
        expected_output="A detailed list of findings extracted from the assessment JSON.",
        agent=analyst,
    )

    task2 = Task(
        description=(
            f"Based on the previous analysis, write a conclusion report in {report_format.upper()} format. "
            "Make it clear, professional, and include the most critical findings. Use proper formatting."
        ),
        expected_output=f"A well-formatted security report in {report_format.upper()} format.",
        agent=reporter
    )

    return Crew(
        agents=[analyst, reporter],
        tasks=[task1, task2],
        process=Process.sequential,
        verbose=True
    )


# ====================
# CLI Interface
# ====================
def main():
    parser = argparse.ArgumentParser(description="Run security assessment crew")
    parser.add_argument('--source', type=str, required=True, help="GitHub raw URL or local path to a JSON report")
    parser.add_argument('--format', type=str, choices=['txt', 'md', 'pdf'], default='md', help="Output format for the report")

    args = parser.parse_args()
    output_file = f"output/conclusion_report.{args.format}"
    os.makedirs("output", exist_ok=True)

    # Load JSON manually
    json_string = load_json_source(args.source)
    # print(json_string)
    print(f"✅ JSON string loaded. Length: {len(json_string)} characters.")
    max_chars = 8000
    if len(json_string) > max_chars:
        print(f"⚠️ Truncating JSON input from {len(json_string)} to {max_chars} chars.")
    json_data_truncated = json_string[:max_chars]
    
    print(f"✅ JSON string truncated {json_data_truncated}.")
    # Create and run crew
    crew = build_crew(json_data_truncated, args.format)
    result = crew.kickoff()

    # Write output
    with open(output_file, "w") as f:
        f.write(result)

    print(f"\n✅ Final report written to: {output_file}")


if __name__ == "__main__":
    main()
