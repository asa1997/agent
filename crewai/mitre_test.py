from crewai import Agent, Task, Crew, LLM
from crewai_tools import JSONSearchTool, FileWriteTool
from crewai.knowledge.source.json_knowledge_source import JSONKnowledgeSource

# Configure Ollama LLM
ollama_llm = LLM(
    model="ollama/llama3.2:latest",
    base_url="http://localhost:11434",
    temperature=0.3  # Lower temperature for more focused analysis
)

# Set up tools
json_search_tool = JSONSearchTool(
    json_path='assessment_report.json',
    config={
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "llama3.2:latest",
                "base_url": "http://localhost:11434"
            }
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "mxbai-embed-large",
                "url": "http://localhost:11434/api/embeddings"
            }
        }
    }
)

file_writer = FileWriteTool()

# Create specialized agents
data_analyst = Agent(
    role="JSON Data Analyst",
    goal="Analyze large JSON assessment reports and extract key insights",
    backstory="You are an expert data analyst specializing in processing large JSON datasets and identifying critical patterns and trends.",
    tools=[json_search_tool],
    llm=ollama_llm,
    respect_context_window=True,  # Important for large files
    verbose=True
)

report_writer = Agent(
    role="Technical Report Writer",
    goal="Create comprehensive summary reports from analyzed data",
    backstory="You are a skilled technical writer who excels at creating clear, concise summary reports from complex data analysis.",
    tools=[file_writer],
    llm=ollama_llm,
    verbose=True
)

# Define tasks
analysis_task = Task(
    description="""
    Analyze the large JSON assessment report and extract:
    1. Key metrics and statistics
    2. Critical findings and anomalies
    3. Trends and patterns
    4. Risk factors or areas of concern
    5. Performance indicators
    
    Focus on the most important insights that would be valuable for decision-making.
    """,
    agent=data_analyst,
    expected_output="Detailed analysis with key findings, metrics, and insights from the JSON assessment report"
)

summary_task = Task(
    description="""
    Based on the analysis results, create a comprehensive summary report that includes:
    1. Executive summary
    2. Key findings and insights
    3. Critical metrics and statistics
    4. Recommendations based on the analysis
    5. Areas requiring attention
    
    The report should be well-structured, professional, and actionable.
    Save the final report as 'assessment_summary_report.md'.
    """,
    agent=report_writer,
    expected_output="A comprehensive summary report saved as a markdown file",
    output_file="assessment_summary_report.md"
)

# Create and run the crew
assessment_crew = Crew(
    agents=[data_analyst, report_writer],
    tasks=[analysis_task, summary_task],
    verbose=True,
    memory=True,  # Enable memory for better context retention
    embedder={
        "provider": "ollama",
        "config": {
            "model": "mxbai-embed-large",
            "url": "http://localhost:11434/api/embeddings"
        }
    }
)

# Execute the analysis
try:
    result = assessment_crew.kickoff()
    print("Assessment analysis completed!")
    print(result)
except Exception as e:
    print("An error occurred during the assessment process:")
    print(str(e))
    import traceback
    traceback.print_exc()