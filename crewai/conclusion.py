import os
import json
import argparse
import requests
from crewai import Agent, Task, Crew, Process, LLM
# from langchain_community.llms.ollama import Ollama
# from langchain_ollama import OllamaLLM
from langchain_ollama import OllamaLLM

class CrewCompatibleOllama(OllamaLLM):
    def call(self, prompt, **kwargs):
        return self.invoke(prompt)


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

llm = LLM(
    model="ollama/llama3.2:latest",
    # stream=True  # Enable streaming
)
# ====================
# Agent & Task Setup
# ====================
def build_crew(json_string: str, report_format: str):
    # llm = OllamaLLM(model="llama3", temperature=0.2)
    # llm = CrewCompatibleOllama(model="llama3.2:latest", temperature=0.2)

    analyst = Agent(
        role='Security Analyst',
        goal='Identify vulnerabilities and risks in the report',
        backstory='A seasoned security professional experienced in analyzing JSON-based assessments.',
        allow_delegation=True,
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
    json_cleaned = json_string.replace("```", "")  # Remove markdown code blocks
    json_cleaned = json_cleaned.replace("\\n", "\n")  # Decode escaped newlines
    json_data_truncated = json_cleaned[:max_chars]

    print(f"✅ JSON string truncated {json_data_truncated}.")
    # Create and run crew
    crew = build_crew(json_data_truncated, args.format)
    try:
        result = crew.kickoff()
        print(result)
    except Exception as e:
        import traceback
        print("\n❌ Exception during Crew execution:")
        traceback.print_exc()
        result = "Crew execution failed. See error log above."
        # Write output
    with open(output_file, "w") as f:
        f.write(result)

    print(f"\n✅ Final report written to: {output_file}")


if __name__ == "__main__":
    main()
