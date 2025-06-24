import json
import os
from crewai import Agent, Task, Crew
from crewai_tools import FileReadTool
import warnings
warnings.filterwarnings('ignore')

def chunk_json_file(input_file, chunk_size=500):
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
        
        # Read chunk content directly to avoid tool parameter issues
        try:
            with open(chunk_file, 'r') as f:
                chunk_content = f.read()
            
            # Truncate if too large for context window
            if len(chunk_content) > 8000:
                chunk_content = chunk_content[:8000] + "\n... [truncated for length]"
            
            print(f"📄 Chunk {i} content length: {len(chunk_content)} characters")
            
        except Exception as e:
            error_msg = f"❌ Error reading chunk {i}: {e}"
            print(error_msg)
            all_results.append(f"=== CHUNK {i} ERROR ===\n{error_msg}\n")
            continue
        
        # Create agent without tools (we'll pass content directly)
        analyst = Agent(
            role=f"MITRE Security Analyst - Chunk {i}",
            goal="Analyze this portion of the MITRE security assessment",
            backstory="You are analyzing a specific section of a larger security report.",
            llm="ollama/llama3.2:latest",
            verbose=True,
            max_rpm=5,  # Reduced to avoid rate limiting
            memory=True,
            respect_context_window=True,
        )
        
        # Create task with content embedded in description
        task = Task(
            description=f"""
            Analyze chunk {i} of the MITRE security report. Here is the JSON content:

            ```json
            {chunk_content}
            ```
            
            Please analyze this data and provide:
            
            1. **Data Structure**: What type of data is in this chunk?
            2. **Security Findings**: Any security issues, vulnerabilities, or threats identified
            3. **Key Patterns**: Important patterns, anomalies, or notable entries
            4. **Summary**: Brief summary of this chunk's contents and significance
            
            Focus only on the data provided above. Be specific and factual.
            """,
            expected_output=f"""
            **Chunk {i} Analysis**:
            
            **Data Structure**: [Description of data type and structure]
            
            **Security Findings**: [List any security issues found]
            
            **Key Patterns**: [Notable patterns or anomalies]
            
            **Summary**: [Brief summary of chunk contents]
            """,
            agent=analyst
        )
        
        # Execute analysis for this chunk
        crew = Crew(agents=[analyst], tasks=[task], verbose=False)
        
        try:
            result = crew.kickoff()
            all_results.append(f"=== CHUNK {i} RESULTS ===\n{result}\n")
            print(f"✅ Chunk {i} analyzed successfully")
            
            # Add a small delay to avoid overwhelming Ollama
            import time
            time.sleep(2)
            
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
    
    # Truncate if too long
    if len(combined_analysis) > 12000:
        combined_analysis = combined_analysis[:12000] + "\n... [truncated for length]"
    
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
        
        Synthesize the findings into a cohesive report with:
        1. **Executive Summary**: Overall security posture and key takeaways
        2. **Critical Findings**: Most important security issues across all chunks
        3. **Risk Assessment**: Risk levels and potential impacts
        4. **Recommendations**: Prioritized action items and strategic improvements
        
        Make it actionable and suitable for both technical and executive audiences.
        """,
        expected_output="""
        **COMPREHENSIVE SECURITY ASSESSMENT REPORT**
        
        **Executive Summary**:
        - Overall security status assessment
        - Most critical findings requiring immediate attention
        - Business impact summary
        
        **Critical Findings**:
        - High-priority security issues identified
        - Vulnerability patterns across the data
        - Threat indicators and attack vectors
        
        **Risk Assessment**:
        - Risk categorization (Critical/High/Medium/Low)
        - Potential business impact
        - Likelihood assessments
        
        **Recommendations**:
        - Immediate actions (0-30 days)
        - Short-term improvements (1-3 months)
        - Long-term strategic initiatives (3-12 months)
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
            
            try:
                # Chunk the file (reduced chunk size for better handling)
                chunks = chunk_json_file(json_file, chunk_size=250)  # Smaller chunks
                
                # Analyze chunks
                print(f"\n🚀 Starting analysis of {len(chunks)} chunks...")
                results = analyze_json_chunks(chunks)
                
                # Create final summary
                print(f"\n📊 Completed chunk analysis. Creating final summary...")
                final_summary = create_final_summary(results)
                
                # Save results
                output_file = 'chunked_analysis_results.txt'
                with open(output_file, 'w') as f:
                    f.write("=== INDIVIDUAL CHUNK RESULTS ===\n\n")
                    f.write("\n".join(results))
                    f.write("\n\n=== FINAL COMPREHENSIVE SUMMARY ===\n\n")
                    f.write(str(final_summary))
                
                print(f"\n✅ Analysis complete! Results saved to {output_file}")
                print(f"📄 Total chunks processed: {len(chunks)}")
                print(f"📄 Results file size: {os.path.getsize(output_file):,} bytes")
                
                print("\n" + "="*60)
                print("FINAL COMPREHENSIVE SUMMARY:")
                print("="*60)
                print(final_summary)
                
            except Exception as e:
                print(f"❌ Error during chunked analysis: {e}")
                import traceback
                traceback.print_exc()
                
        else:
            print("📄 File size is manageable. You can try the original approach.")
    else:
        print(f"❌ File {json_file} not found!")
