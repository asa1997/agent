from crewai import Agent, Task, Crew
from crewai_tools import JSONSearchTool, FileReadTool


tool = JSONSearchTool(
    json_path='mitre-report.json',
    config={
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "llama3.2:latest",
                "base_url": "http://localhost:11434",
            }
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "mxbai-embed-large:latest",
                # "url": "http://localhost:11434/api/embeddings"
            }
        }
    }
)


# JSON analyst using Ollama
json_analyst = Agent(
    role="JSON Data Analyst",
    goal="Analyze large JSON reports and extract meaningful insights",
    backstory="Expert at processing and analyzing structured JSON data with focus on pattern recognition",
    tools=[tool(), FileReadTool(file_path='mitre-report.json')],
    llm="ollama/llama3.2:latest",  # Use Ollama with Llama 3.2
    verbose=True,
    memory=True,  # Enable memory for context retention
    respect_context_window=True,  # Manage context efficiently
    max_rpm=10,
)

conclusion = Task(
    description=(
        "A detailed report was generated for a model."
        "Go through the said detailed report and draw a conclusion"
        " from a security standpoint and write a report of it. "
        " Make sure you gain a complete insight from the detailed report."
        " Do not make assumptions when drawing conclusion. "
        "The final conclusion report should be easy to understand even for some one"
        " from a non-security related background."
    ),
    expected_outcome=(
        "A simple, detailed, informative report that helps someone"
        " understand the state of the model for that particular assessment."
        " The final report should be easy to understand, that gives the reader"
        " a final insight for the assessment done."
    ),
    tools=[tool, FileReadTool(file_path='mitre-report.json')],
    agent=json_analyst
)

crew = Crew(
  agents=[json_analyst],
  tasks=[conclusion],
  verbose=True
)


result = crew.kickoff()

print(result)