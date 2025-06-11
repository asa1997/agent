import os
import json
import argparse
import requests
from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama

# =======================
# Custom Tool Definition
# =======================
class JSONLoaderTool:
    name = "JSONLoaderTool"
    description = "Loads JSON content from a local path or a GitHub URL"

    def run(self, input: str) -> str:
        if input.startswith("http"):
            return self._load_from_github(input)
        else:
            return self._load_from_local(input)

    def _load_from_github(self, url: str) -> str:
        try:
            res = requests.get(url)
            res.raise_for_status()
            return res.text
        except Exception as e:
            return f"Failed to fetch from GitHub: {e}"

    def _load_from_local(self, path: str) -> str:
        if not os.path.exists(path):
            return f"File not found: {path}"
        with open(path, 'r') as f:
            return f.read()


# ====================
# Agent Configuration
# ====================
def build_crew(source: str, report_format: str):
    llm = Ollama(model="deepseek-r1:7b", temperature=0.2)

    loader_tool = JSONLoaderTool()

    fetcher = Agent(
        role='Report Fetcher',
        goal='Retrieve JSON security assessment reports',
        backstory='Expert in crawling GitHub and filesystems for structured data.',
        tools=[loader_tool],
        allow_delegation=False,
        verbose=True,
        llm=llm
    )

    analyst = Agent(
        role='Security Analyst L3',
        goal='Identify potential risks and vulnerabilities in JSON reports',
        backstory='Experienced infosec specialist trained in threat modeling and secure architecture.',
        allow_delegation=True,
        verbose=True,
        llm=llm
    )

    writer = Agent(
        role='Summary Reporter',
        goal='Write a clear and structured final report based on findings',
        backstory='Communications expert with a knack for simplifying security topics.',
        allow_delegation=False,
        verbose=True,
        llm=llm
    )

    # Tasks
    task1 = Task(
        description=f"Fetch the JSON reports from '{source}' and return them as strings.",
        expected_output="A list of raw JSON strings representing security assessment data.",
        agent=fetcher
    )

    task2 = Task(
        description="Review the raw JSON reports and identify any critical or notable security issues.",
        expected_output="A structured summary of vulnerabilities or threats found in the reports.",
        agent=analyst
    )

    task3 = Task(
        description=f"Based on the findings, write a final conclusion report in {report_format.upper()} format. Highlight all major security concerns clearly.",
        expected_output="Final structured security summary report.",
        agent=writer
    )

    crew = Crew(
        agents=[fetcher, analyst, writer],
        tasks=[task1, task2, task3],
        process=Process.sequential,
        verbose=True
    )

    return crew


# ====================
# CLI Interface
# ====================
def main():
    parser = argparse.ArgumentParser(description="Run security assessment crew")
    parser.add_argument('--source', type=str, required=True, help="GitHub raw URL or local path to a JSON report")
    parser.add_argument('--format', type=str, choices=['txt', 'md', 'pdf'], default='md', help="Output format for the report")

    args = parser.parse_args()
    os.makedirs("output", exist_ok=True)
    output_file = f"output/conclusion_report.{args.format}"

    print(f"\n🔧 Running crew with model 'deepseek-coder' on input: {args.source}...\n")

    crew = build_crew(args.source, args.format)
    result = crew.kickoff(inputs={"source": args.source})

    with open(output_file, "w") as f:
        f.write(result)

    print(f"\n✅ Final report written to: {output_file}")


if __name__ == "__main__":
    main()
