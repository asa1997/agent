from crewai_tools import JSONSearchTool
from crewai import Agent, Task, Crew

# Configure JSONSearchTool with Ollama models
json_tool = JSONSearchTool(
    json_path='./mitre-report.json',
    config={
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "llama3.2:latest",  # or "codellama:7b" for code analysis
                "temperature": 0.1,
                "top_p": 0.9,
                # "url": "http://localhost:11434"  # Default Ollama URL
            }
        },
        "embedding_model": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text",  # Efficient embedding model
                # "url": "http://localhost:11434/api/embeddings"
            }
        }
    }
)

# Create an agent with Ollama LLM
json_analyst = Agent(
    role="JSON Data Analyst",
    goal="Parse and analyze large JSON files efficiently",
    backstory="Expert in processing large structured data files and extracting meaningful insights from code repositories",
    tools=[json_tool],
    llm="ollama/llama3.2:latest",  # Use Ollama model for the agent
    verbose=True
)

# Define tasks for parsing specific sections
parse_task = Task(
    description="Parse the large JSON file containing 20k lines of code and extract key information about code structure, functions, classes, and dependencies. Focus on identifying patterns and architectural insights.",
    expected_output="A structured summary of the JSON content with key findings including function count, class definitions, import dependencies, and code complexity analysis",
    agent=json_analyst
)

try:
    crew = Crew(
        agents=[json_analyst],
        tasks=[parse_task],
        verbose=True
    )

    result = crew.kickoff()
    print("Analysis Results:", result)
except Exception as e:
    print("An error occurred during the analysis:", str(e))
    import traceback
    traceback.print_exc()