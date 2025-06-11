import os
import json
import argparse
import requests
from crewai import Agent, Task, Crew, Process

# Import LLM providers
from langchain_community.llms import HuggingFaceHub
from langchain_community.llms.bedrock import Bedrock
from langchain_core.language_models import BaseLanguageModel


def load_json_source(source: str) -> str:
    print(f"🔍 Loading JSON from: {source}")
    if source.startswith("http"):
        res = requests.get(source)
        res.raise_for_status()
        return res.text
    else:
        if not os.path.exists(source):
            raise FileNotFoundError(f"File not found: {source}")
        with open(source, 'r') as f:
            return f.read()


def get_llm(provider: str, model: str) -> BaseLanguageModel:
    if provider == "huggingface":
        hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not hf_token:
            raise EnvironmentError("Missing HUGGINGFACEHUB_API_TOKEN")
        return HuggingFaceHub(repo_id=model, huggingfacehub_api_token=hf_token)

    elif provider == "bedrock":
        import boto3
        bedrock_client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1"))
        return Bedrock(
            client=bedrock_client,
            model_id=model,
            model_kwargs={"temperature": 0.2}
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")


def build_crew(json_string: str, report_format: str, llm: BaseLanguageModel):
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


def main():
    parser = argparse.ArgumentParser(description="Run security assessment crew")
    parser.add_argument('--source', required=True, help="Path or URL to the JSON report")
    parser.add_argument('--format', choices=['txt', 'md', 'pdf'], default='md')
    parser.add_argument('--provider', choices=['huggingface', 'bedrock'], required=True)
    parser.add_argument('--model', required=True, help="LLM model ID (e.g. 'meta-llama/Meta-Llama-3-8B' or 'anthropic.claude-3-sonnet-20240229-v1:0')")
    args = parser.parse_args()

    os.makedirs("output", exist_ok=True)
    output_file = f"output/conclusion_report.{args.format}"

    # Load and truncate
    json_string = load_json_source(args.source)
    print(f"✅ JSON string loaded. Length: {len(json_string)} characters.")
    json_cleaned = json_string.replace("```", "").replace("\\n", "\n")
    json_data_truncated = json_cleaned[:8000]

    # Load LLM
    llm = get_llm(args.provider, args.model)

    # Run Crew
    crew = build_crew(json_data_truncated, args.format, llm)
    try:
        result = crew.kickoff()
    except Exception as e:
        import traceback
        traceback.print_exc()
        result = "❌ Crew execution failed. See traceback above."

    with open(output_file, "w") as f:
        f.write(result)

    print(f"\n✅ Final report written to: {output_file}")


if __name__ == "__main__":
    main()
