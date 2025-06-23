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

# Create an agent with clear tool usage instructions
json_analyst = Agent(
    role="JSON Data Analyst",
    goal="Parse and analyze large JSON files efficiently",
    backstory="""Expert in processing large structured data files and extracting meaningful insights from code repositories. 
    You know how to use search tools properly by providing clear, specific search queries as strings.""",
    tools=[json_tool],
    llm="ollama/llama3.1:8b",
    verbose=True
)

# Define task with explicit instructions for tool usage
parse_task = Task(
    description="""Parse the large JSON file containing 20k lines of code and extract key information.

    Use the JSON search tool with specific search queries like:
    - "function" to find function definitions
    - "class" to find class definitions  
    - "import" to find import statements
    - "def " to find Python function definitions
    - "async def" to find async functions
    
    Search systematically through different aspects of the code structure.""",
    expected_output="""A comprehensive analysis including:
    - Total number of functions found
    - List of main function names
    - Class definitions identified
    - Import dependencies discovered
    - Code structure insights""",
    agent=json_analyst
)

crew = Crew(
    agents=[json_analyst],
    tasks=[parse_task],
    verbose=True
)

result = crew.kickoff()
print("Analysis Results:", result)