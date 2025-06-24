from crewai import Agent, Task, Crew
from crewai_tools import JSONSearchTool, FileReadTool
import warnings
warnings.filterwarnings('ignore')
# Configure JSON search tool with Ollama
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
        "embedder": {  # This is correct - "embedder" not "embedding_model"
            "provider": "ollama",
            "config": {
                "model": "mxbai-embed-large",
                # "base_url": "http://localhost:11434"  # Add this if needed
            }
        }
    }
)

# JSON analyst using Ollama
json_analyst = Agent(
    role="MITRE Security Assessment Analyst",
    goal="Analyze MITRE security assessment reports and extract meaningful security insights",
    backstory="""You are an expert cybersecurity analyst specializing in MITRE ATT&CK framework assessments. 
    You excel at interpreting complex security data, identifying vulnerabilities, threat patterns, and 
    translating technical security findings into clear, actionable insights for both technical and 
    non-technical stakeholders.""",
    tools=[tool, FileReadTool(file_path='mitre-report.json')],  # Remove () from tool
    llm="ollama/llama3.2:latest",
    verbose=True,
    memory=True,
    respect_context_window=True,
    max_rpm=10,
)

# Security analysis task
conclusion = Task(
    description="""
    Analyze the MITRE security assessment report and create a comprehensive security conclusion:
    
    1. **Security Posture Analysis**:
       - Review all security findings and assessments
       - Identify critical vulnerabilities and threats
       - Analyze attack vectors and potential impact
    
    2. **Risk Assessment**:
       - Categorize risks by severity (Critical, High, Medium, Low)
       - Identify the most pressing security concerns
       - Assess potential business impact
    
    3. **Threat Landscape**:
       - Map identified threats to MITRE ATT&CK framework
       - Understand attack patterns and techniques
       - Identify gaps in current security controls
    
    4. **Executive Summary**:
       - Provide clear, non-technical summary of findings
       - Explain security implications in business terms
       - Offer prioritized recommendations
    
    Base your analysis strictly on the data in the report. Do not make assumptions 
    or add information not present in the source material.
    """,
    expected_output="""
    A comprehensive security assessment report containing:
    
    **Executive Summary** (for non-technical readers):
    - Overall security posture rating
    - Top 3-5 critical findings in plain language
    - Business impact summary
    
    **Technical Findings**:
    - Detailed vulnerability analysis
    - Threat vector identification
    - Security control effectiveness assessment
    
    **Risk Matrix**:
    - Prioritized list of security risks
    - Impact and likelihood ratings
    - Recommended remediation timeline
    
    **Actionable Recommendations**:
    - Immediate actions required
    - Short-term improvements (1-3 months)
    - Long-term security strategy (3-12 months)
    
    The report should be clear, factual, and actionable for both security teams and business leadership.
    """,
    agent=json_analyst
)

# Create and execute crew
crew = Crew(
    agents=[json_analyst],
    tasks=[conclusion],
    verbose=True
)

# Run the analysis

try:
    result = crew.kickoff()
    print("Analysis completed successfully!")
    print(result)
except Exception as e:
    print(f"Error during analysis: {e}")
    import traceback
    traceback.print_exc()
