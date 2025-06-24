import json
import os
from crewai import Agent, Task, Crew
from crewai_tools import FileReadTool
import warnings
warnings.filterwarnings('ignore')

def chunk_json_file(input_file, chunk_size=1000):
    """Split large JSON into smaller chunks"""
    print(f"📂 Chunking {input_file}...")
    
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Create chunks directory
    os.makedirs('json_chunks', exist_ok=True)
    
    chunks = []
    if isinstance(data, list):
        # If JSON is an array, split by items
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            chunk_file = f'json_chunks/chunk_{i//chunk_size + 1}.json'
            with open(chunk_file, 'w') as f:
                json.dump(chunk, f, indent=2)
            chunks.append(chunk_file)
            print(f"✅ Created {chunk_file} with {len(chunk)} items")
    
    elif isinstance(data, dict):
        # If JSON is an object, split by keys
        keys = list(data.keys())
        for i in range(0, len(keys), chunk_size):
            chunk_keys = keys[i:i + chunk_size]
            chunk = {k: data[k] for k in chunk_keys}
            chunk_file = f'json_chunks/chunk_{i//chunk_size + 1}.json'
            with open(chunk_file, 'w') as f:
                json.dump(chunk, f, indent=2)
            chunks.append(chunk_file)
            print(f"✅ Created {chunk_file} with {len(chunk_keys)} keys")
    
    return chunks

def analyze_json_chunks(chunk_files):
    """Analyze each chunk separately"""
    all_results = []
    
    for i, chunk_file in enumerate(chunk_files, 1):
        print(f"\n🔍 Analyzing chunk {i}/{len(chunk_files)}: {chunk_file}")
        
        # Create agent for this chunk
        analyst = Agent(
            role=f"MITRE Security Analyst - Chunk {i}",
            goal="Analyze this portion of the MITRE security assessment",
            backstory="You are analyzing a specific section of a larger security report.",
            tools=[FileReadTool(file_path=chunk_file)],
            llm="ollama/llama3.2:latest",
            verbose=True,
            max_rpm=10,
            memory=True,
            respect_context_window=True
        )
        
        # Create task for this chunk
        task = Task(
            description=f"""
            Analyze chunk {i} of the MITRE security report.
            
            1. Read and understand the data in this chunk
            2. Identify any security findings, vulnerabilities, or threats
            3. Note any important patterns or anomalies
            4. Provide a summary of this chunk's contents
            
            Focus only on the data in this specific chunk.
            """,
            expected_output=f"""
            **Chunk {i} Analysis Summary**:
            - Data type and structure found
            - Key security findings (if any)
            - Notable patterns or issues
            - Brief summary of contents
            """,
            agent=analyst
        )
        
        # Execute analysis for this chunk
        crew = Crew(agents=[analyst], tasks=[task], verbose=False)
        
        try:
            result = crew.kickoff()
            all_results.append(f"=== CHUNK {i} RESULTS ===\n{result}\n")
            print(f"✅ Chunk {i} analyzed successfully")
        except Exception as e:
            error_msg = f"❌ Error analyzing chunk {i}: {e}"
            print(error_msg)
            all_results.append(f"=== CHUNK {i} ERROR ===\n{error_msg}\n")
    
    return all_results

def create_final_summary(chunk_results):
    """Create a final summary from all chunk results"""
    print("\n📋 Creating final summary...")
    
    # Combine all chunk results
    combined_analysis = "\n".join(chunk_results)
    
    # Create summary agent
    summary_agent = Agent(
        role="Security Report Synthesizer",
        goal="Create a comprehensive summary from multiple analysis chunks",
        backstory="You synthesize security findings from multiple report sections into a cohesive summary.",
        llm="ollama/llama3.2:latest",
        verbose=True
    )
    
    # Create summary task
    summary_task = Task(
        description=f"""
        Based on the following chunk analyses, create a comprehensive security assessment summary:
        
        {combined_analysis}
        
        Synthesize the findings into:
        1. Overall security posture assessment
        2. Critical findings across all chunks
        3. Common patterns or themes
        4. Prioritized recommendations
        """,
        expected_output="""
        **COMPREHENSIVE SECURITY ASSESSMENT**
        
        **Executive Summary**:
        - Overall security status
        - Most critical findings
        
        **Key Findings**:
        - Major security issues identified
        - Risk assessment
        
        **Recommendations**:
        - Top priority actions
        - Strategic improvements needed
        """,
        agent=summary_agent
    )
    
    crew = Crew(agents=[summary_agent], tasks=[summary_task], verbose=True)
    return crew.kickoff()

# Main execution
if __name__ == "__main__":
    json_file = 'mitre-report.json'
    
    # Check file size first
    if os.path.exists(json_file):
        file_size = os.path.getsize(json_file)
        print(f"📊 File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
        
        if file_size > 1024 * 1024:  # > 1MB
            print("⚠️  Large file detected. Using chunked analysis...")
            
            # Chunk the file
            chunks = chunk_json_file(json_file, chunk_size=500)  # Adjust chunk_size as needed
            
            # Analyze chunks
            results = analyze_json_chunks(chunks)
            
            # Create final summary
            final_summary = create_final_summary(results)
            
            # Save results
            with open('chunked_analysis_results.txt', 'w') as f:
                f.write("=== INDIVIDUAL CHUNK RESULTS ===\n\n")
                f.write("\n".join(results))
                f.write("\n\n=== FINAL SUMMARY ===\n\n")
                f.write(str(final_summary))
            
            print(f"\n✅ Analysis complete! Results saved to chunked_analysis_results.txt")
            print("\n" + "="*50)
            print("FINAL SUMMARY:")
            print("="*50)
            print(final_summary)
            
        else:
            print("📄 File size is manageable. You can try the original approach.")
    else:
        print(f"❌ File {json_file} not found!")
