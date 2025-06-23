import os
import json
import argparse
import requests
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import FileReadTool, JSONSearchTool
from langchain_openai import ChatOpenAI


os.environ.pop("OPENAI_API_KEY", None)
os.environ["CREWAI_LLM_PROVIDER"] = "ollama"
os.environ["OPENAI_API_KEY"] = "NA"

llm = ChatOpenAI(
    model="ollama/llama3.2:latest",
    base_url="http://localhost:11434/v1",
    temperature=0.3
)

# llm = LLM(
#     model="ollama/llama3.2:latest",
#     stream=False  # Enable streaming
# )

analyst = Agent(
    role='Cybersecurity Analyst L3',
    goal='Identify vulnerabilities and risks in the assessment report and reach a conclusion.',
    backstory='A seasoned security professional experienced in analyzing JSON-based assessments.',
    allow_delegation=False,
    verbose=True,
    llm=llm,
    tools=[
        FileReadTool(file_path="./mitre-report.json"),
        JSONSearchTool(json_path="./mitre-report.json")
    ],
    allow_code_execution=True,
    respect_context_window=True
)

reporter = Agent(
    role='Security Summary Writer',
    goal='Create a clear, structured conclusion report',
    backstory='An expert communicator who specializes in technical cybersecurity reporting.',
    allow_delegation=False,
    verbose=True,
    llm=llm
)


analysis = Task(
    description=(
            "Load and analyze the MITRE assessment JSON file. "
            "Extract key vulnerabilities, impacted assets, severity levels, "
            "and any exploitability or risk indicators. "
            "Process in chunks if needed to stay within context limits."
        ),
        expected_output=(
            "A structured summary (JSON or markdown table) with: "
            "- List of vulnerabilities (IDs + titles)\n"
            "- Affected assets/components\n"
            "- Severity ratings\n"
            "- Brief risk explanation per item\n"
            "- Overall risk assessment conclusion"
        ),
        agent=analyst,
        tools=[FileReadTool(file_path="./mitre-report.json"),
               JSONSearchTool(json_path="./mitre-report.json")],
        markdown=True
)

summarize = Task(
    description=(
            "Using the analyst’s findings, compose a polished conclusion report. "
            "Include executive summary, vulnerability highlights, technical risk details, "
            "and actionable remediation steps."
        ),
        expected_output=(
            "A final markdown report with sections:\n"
            "1. Executive Summary\n"
            "2. Key Findings (with vulnerability list)\n"
            "3. Risk Implications\n"
            "4. Remediation Recommendations\n"
            "5. Final Conclusion"
        ),
        agent=reporter,
        context=[analysis],  # ensures report gets analysis output
        markdown=True,
        output_file="security_assessment_conclusion.md"
)
try:
    crew = Crew(
            agents=[analyst, reporter],
            tasks=[analysis, summarize],
            process=Process.sequential,
            verbose=True
        )
    report = crew.kickoff()

    print(report)
except Exception as e:
    import traceback
    print("❌ An error occurred while generating the report:")
    traceback.print_exc()