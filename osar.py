import os
# from utils import get_openai_api_key, pretty_print_result
from utils import get_serper_api_key
from crewai import Agent, Task, Crew, LLM

from crewai_tools import JSONSearchTool
# openai_api_key = get_openai_api_key()
# os.environ["OPENAI_MODEL_NAME"] = 'gpt-3.5-turbo'
os.environ["SERPER_API_KEY"] = get_serper_api_key()

json_tool = JSONSearchTool(json_path='/home/ubuntu/besecure-ml-assessment-datastore/models/llama3.1:8b/llm-benchmark/llama3.1:8b-autocomplete-test-detailed-report.json')

llm = LLM(
    model="ollama/llama3.1:8b",
    base_url="http://localhost:11434"
)

security_analyst = Agent(
    role = "Cybersecurity Analyst L3",
    goal = "To find a conclusion and provide insights with "
            "respect to security by reading through security "
            "assessment reports done on open source models and projects.",
    backstory = (
            "You are a certified Cybersecurity Analyst "
            "working on an open source platform called Be-Secure."
            "You need to write a conclusion report from a securiy"
            " standpoint and provide insights"
            " with the information gained from the detailed assessment"
            " report done on open source {type} {name} {version}."
            "Make sure your conclusion report is easy to understand "
            "even for someone from a non-security related background"
    ),
    llm=llm,
    allow_delegation=False,
	verbose=True
)

conclusion = Task(
    description=(
        "A detailed report was generated for {type} {name} {version}."
        "Go through the said detailed report and draw a conclusion"
        " from a security standpoint and write a report of it. "
        " Make sure you gain a complete insight from the detailed report."
        " Do not make assumptions when drawing conclusion. "
        "The final conclusion report should be easy to understand even for some one"
        " from a non-security related background."
    ),
    expected_outcome=(
        "A simple, detailed, informative report that helps someone"
        " understand the state of {name} for that particular assessment."
        " The final report should be easy to understand, that gives the reader"
        " a final insight for the assessment done."
    ),
    tools=[json_tool],
    agent=security_analyst
)

crew = Crew(
  agents=[security_analyst],
  tasks=[conclusion],
  verbose=True
)

inputs = {
    "type": "model",
    "name": "llama3.1",
    "version": "8b"
}
result = crew.kickoff(inputs=inputs)