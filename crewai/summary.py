from crewai.flow.flow import Flow, listen, start
from crewai import Agent, Crew, Task, LLM, Process
from crewai_tools import JSONSearchTool, FileReadTool
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import json
import warnings
warnings.filterwarnings('ignore')
# Define structured output models (same as before)
class SecurityFinding(BaseModel):
    severity: str = Field(description="Critical, High, Medium, Low")
    category: str = Field(description="Vulnerability category")
    description: str = Field(description="Finding description")
    affected_systems: List[str] = Field(description="List of affected systems")
    recommendation: str = Field(description="Remediation recommendation")
    cvss_score: Optional[float] = Field(description="CVSS score if available")

class SecuritySummary(BaseModel):
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    top_risks: List[SecurityFinding]
    executive_summary: str
    key_recommendations: List[str]

class SecurityAssessmentState(BaseModel):
    report_path: str = ""
    raw_data: Dict = {}
    findings: List[SecurityFinding] = []
    summary: SecuritySummary = None

class SecurityAnalysisCrew:
    def __init__(self):
        # Configure Ollama LLMs
        self.agent_llm = LLM(
            model="ollama/llama3.2:latest",
            base_url="http://localhost:11434"  # Default Ollama URL
        )
        
        # Use a different Ollama model for tools (you can experiment with different models)
        self.tool_llm = LLM(
            model="ollama/llama3.2:latest",  # or try "ollama/codellama" for better JSON parsing
            base_url="http://localhost:11434"
        )
        
        # Configure tools with Ollama models
        self.json_tool = JSONSearchTool(
            config={
                "llm": {
                    "provider": "ollama",
                    "config": {
                        "model": "llama3.2:latest",
                        "base_url": "http://localhost:11434",
                        "temperature": 0.1,  # Lower temperature for more consistent JSON parsing
                    }
                },
                "embedding_model": {
                    "provider": "ollama",
                    "config": {
                        "model": "nomic-embed-text",  # Good embedding model for Ollama
                        "base_url": "http://localhost:11434"
                    }
                }
            }
        )
        
        self.file_tool = FileReadTool()
        
    def create_agents(self):
        # Security analyst for finding extraction
        security_analyst = Agent(
            role="Senior Security Analyst",
            goal="Extract and categorize security findings from assessment reports with high accuracy",
            backstory="""You are an expert cybersecurity analyst with 15+ years of experience 
            in vulnerability assessment and penetration testing. You excel at parsing complex 
            security reports, identifying critical risks, and working with JSON data structures. 
            You are methodical and thorough in your analysis.""",
            tools=[self.json_tool, self.file_tool],
            llm=self.agent_llm,
            verbose=True,
            max_iter=10,  # Allow more iterations for complex analysis
            memory=True
        )
        
        # Risk assessor for prioritization
        risk_assessor = Agent(
            role="Risk Assessment Specialist", 
            goal="Prioritize security findings based on business impact, exploitability, and industry best practices",
            backstory="""You specialize in risk quantification and business impact analysis. 
            You understand CVSS scoring, threat modeling, and how to translate technical 
            vulnerabilities into business risks. You have deep knowledge of security frameworks 
            like NIST, ISO 27001, and OWASP.""",
            llm=self.agent_llm,
            verbose=True,
            max_iter=8,
            memory=True
        )
        
        # Report writer for executive summary
        report_writer = Agent(
            role="Security Report Writer",
            goal="Create clear, actionable executive summaries and technical reports for security leadership",
            backstory="""You excel at translating complex technical security findings into 
            clear, actionable reports for executives and stakeholders. You understand both 
            technical and business language, and can create compelling narratives around 
            security posture and risk management.""",
            llm=self.agent_llm,
            verbose=True,
            max_iter=6,
            memory=True
        )
        
        return [security_analyst, risk_assessor, report_writer]
    
    def create_tasks(self, agents):
        security_analyst, risk_assessor, report_writer = agents
        
        # Task 1: Extract findings from JSON
        extract_task = Task(
            description="""Analyze the security assessment JSON report systematically and extract all security findings.
            
            Your analysis should focus on:
            1. Vulnerability details and descriptions
            2. Severity levels and CVSS scores  
            3. Affected systems and components
            4. Current status of findings
            5. Any remediation information provided
            
            Parse through the JSON structure methodically. Look for common security report sections like:
            - vulnerabilities, findings, issues, alerts
            - scan_results, assessment_results, security_findings
            - Any nested objects containing security data
            
            For each finding, extract:
            - Severity (Critical/High/Medium/Low)
            - Category/Type of vulnerability
            - Detailed description
            - Affected systems/hosts/services
            - Remediation recommendations
            - CVSS score if available
            
            Be thorough and don't miss any findings. If the JSON structure is complex, 
            break it down section by section.""",
            expected_output="""A comprehensive structured list of all security findings with complete details.
            Each finding should include severity, category, description, affected systems, 
            recommendations, and CVSS score where available. Format as a detailed analysis 
            that can be used for further processing.""",
            agent=security_analyst,
            tools=[self.json_tool, self.file_tool]
        )
        
        # Task 2: Risk prioritization
        prioritize_task = Task(
            description="""Analyze the extracted security findings and prioritize them based on comprehensive risk assessment.
            
            Consider these factors for prioritization:
            1. Severity level and CVSS scores
            2. Exploitability and attack complexity
            3. Business impact potential
            4. Current exposure level and attack surface
            5. Ease of remediation vs. impact
            
            Create a risk matrix and identify:
            - Top 10 most critical risks requiring immediate attention
            - Medium-term risks that need planning
            - Lower priority items for future consideration
            
            For each high-priority risk, provide:
            - Business impact assessment
            - Likelihood of exploitation
            - Recommended timeline for remediation
            - Resource requirements estimate""",
            expected_output="""A prioritized risk assessment with:
            1. Risk matrix categorization
            2. Top 10 critical risks with detailed business impact analysis
            3. Recommended remediation timeline
            4. Resource allocation suggestions
            Format as a structured analysis suitable for executive review.""",
            agent=risk_assessor,
            context=[extract_task]
        )
        
        # Task 3: Executive summary
        summary_task = Task(
            description="""Create a comprehensive executive summary and final report based on the security analysis.
            
            The summary should include:
            1. Executive Overview
               - Overall security posture assessment
               - Key statistics (total findings by severity)
               - Risk level summary
            
            2. Critical Findings
               - Top 5 critical risks requiring immediate attention
               - Business impact for each critical finding
               - Immediate action items
            
            3. Strategic Recommendations
               - Short-term remediation priorities (0-30 days)
               - Medium-term security improvements (1-6 months)
               - Long-term strategic initiatives (6+ months)
            
            4. Resource Requirements
               - Estimated effort for critical fixes
               - Budget considerations
               - Staffing recommendations
            
            5. Compliance and Regulatory Impact
               - Any compliance violations identified
               - Regulatory reporting requirements
            
            Write in clear, executive-friendly language while maintaining technical accuracy.""",
            expected_output="""A comprehensive executive summary in structured format including:
            - Executive dashboard metrics
            - Critical findings summary
            - Prioritized action plan
            - Resource and timeline recommendations
            - Compliance impact assessment
            Format suitable for C-level presentation and technical team implementation.""",
            agent=report_writer,
            context=[extract_task, prioritize_task],
            output_json={
                "type": "object",
                "properties": {
                    "executive_summary": {"type": "string"},
                    "total_findings": {"type": "integer"},
                    "critical_count": {"type": "integer"},
                    "high_count": {"type": "integer"},
                    "medium_count": {"type": "integer"},
                    "low_count": {"type": "integer"},
                    "top_risks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "severity": {"type": "string"},
                                "category": {"type": "string"},
                                "description": {"type": "string"},
                                "affected_systems": {"type": "array", "items": {"type": "string"}},
                                "recommendation": {"type": "string"},
                                "cvss_score": {"type": "number"}
                            }
                        }
                    },
                    "key_recommendations": {"type": "array", "items": {"type": "string"}}
                }
            }
        )
        
        return [extract_task, prioritize_task, summary_task]
    
    def crew(self):
        agents = self.create_agents()
        tasks = self.create_tasks(agents)
        
        return Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,  # Enable memory for large document processing
            max_rpm=30,  # Adjust based on your Ollama server capacity
            function_calling_llm=self.tool_llm  # Use tool LLM for function calls
        )


class SecurityReportAnalysisFlow(Flow[SecurityAssessmentState]):
    
    def __init__(self):
        super().__init__()
        # Configure Ollama LLM for direct calls in the flow
        self.flow_llm = LLM(
            model="ollama/llama3.2:latest",
            base_url="http://localhost:11434"
        )
    
    @start()
    def load_and_validate_report(self):
        """Load and validate the security assessment report"""
        print("🔍 Loading security assessment report...")
        
        # In practice, get this from user input or configuration
        self.state.report_path = input("Enter path to security assessment JSON file: ").strip()
        
        if not self.state.report_path:
            self.state.report_path = "security_assessment.json"  # Default for testing
        
        # Load and validate JSON structure
        try:
            with open(self.state.report_path, 'r', encoding='utf-8') as f:
                self.state.raw_data = json.load(f)
            
            data_size = len(json.dumps(self.state.raw_data))
            print(f"✅ Successfully loaded report with {data_size:,} characters")
            print(f"📊 JSON structure has {len(self.state.raw_data)} top-level keys")
            
            # Log top-level structure for debugging
            if isinstance(self.state.raw_data, dict):
                print(f"🔑 Top-level keys: {list(self.state.raw_data.keys())[:10]}")
            
        except FileNotFoundError:
            print(f"❌ Error: File '{self.state.report_path}' not found")
            raise
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON format - {e}")
            raise
        except Exception as e:
            print(f"❌ Error loading report: {e}")
            raise
            
        return "Report loaded and validated successfully"
    
    @listen(load_and_validate_report)
    def preprocess_large_report(self, _):
        """Preprocess the report for optimal analysis"""
        print("🔧 Preprocessing large security report...")
        
        # For very large reports, create a summary of structure
        data_str = json.dumps(self.state.raw_data, indent=2)
        
        if len(data_str) > 100000:  # If larger than 100KB
            print("📋 Large report detected, creating structure summary...")
            
            # Use direct LLM call to understand JSON structure
            structure_prompt = f"""
            Analyze this JSON security report structure and provide a summary of its organization.
            
            JSON Keys and Structure (first 5000 characters):
            {data_str[:5000]}
            
            Please identify:
            1. Main sections that likely contain security findings
            2. The structure of individual findings/vulnerabilities
            3. Key fields that contain severity, description, affected systems
            4. Any nested structures that need special attention
            
            Provide a concise analysis of how to navigate this JSON for security analysis.
            """
            
            structure_analysis = self.flow_llm.call(structure_prompt)
            print(f"📝 Structure Analysis:\n{structure_analysis}")
            
            # Store analysis for agents to use
            self.state.raw_data['_structure_analysis'] = structure_analysis
        
        return "Report preprocessing completed"
    
    @listen(preprocess_large_report)
    def analyze_security_findings(self, _):
        """Run the security analysis crew on the report"""
        print("🔍 Starting comprehensive security analysis...")
        
        # Prepare input data for the crew
        # Limit the JSON size for context window management
        json_data = json.dumps(self.state.raw_data, indent=2)
        
        # If too large, chunk it or provide a summary
        if len(json_data) > 50000:
            print("📊 Large dataset detected, providing structured input to crew...")
            crew_input = {
                "report_path": self.state.report_path,
                "report_structure": self.state.raw_data.get('_structure_analysis', 'No structure analysis available'),
                "sample_data": json_data[:30000] + "\n... [truncated for context management]",
                "total_size": len(json_data),
                "instruction": "Use the JSONSearchTool to systematically search through the full report file for security findings"
            }
        else:
            crew_input = {
                "report_path": self.state.report_path,
                "report_data": json_data,
                "instruction": "Analyze the complete security assessment report provided"
            }
        
        # Run the security analysis crew
        try:
            crew = SecurityAnalysisCrew().crew()
            result = crew.kickoff(inputs=crew_input)
            
            print("✅ Security analysis completed successfully")
            return result
            
        except Exception as e:
            print(f"❌ Error during security analysis: {e}")
            raise
    
    @listen(analyze_security_findings)
    def generate_final_report(self, analysis_result):
        """Generate the final security assessment summary"""
        print("📝 Generating final security assessment report...")
        
        try:
            # Extract structured data from crew result
            summary_data = {}
            
            if hasattr(analysis_result, 'json_dict') and analysis_result.json_dict:
                summary_data = analysis_result.json_dict
                print("✅ Extracted structured JSON output from analysis")
            elif hasattr(analysis_result, 'raw'):
                summary_data = {'raw_output': analysis_result.raw}
        except Exception as e:
            import traceback
            traceback.print_exc()