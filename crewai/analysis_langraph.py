import json
import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate

class State(TypedDict):
    json_chunk: str
    chunk_number: int
    total_chunks: int
    analysis_results: list
    final_summary: str

# Initialize LLM
llm = Ollama(model="llama3.2:latest", base_url="http://localhost:11434")

def chunk_large_json(file_path, max_chunk_size=2000):
    """Split JSON into manageable text chunks"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Split into chunks by character count
    chunks = []
    for i in range(0, len(content), max_chunk_size):
        chunk = content[i:i + max_chunk_size]
        chunks.append(chunk)
    
    return chunks

def analyze_chunk_node(state: State) -> dict:
    """Analyze a single chunk"""
    template = PromptTemplate.from_template(
        "Analyze this portion of a MITRE security report (chunk {chunk_number}/{total_chunks}):\n\n"
        "{json_chunk}\n\n"
        "Provide a brief analysis focusing on:\n"
        "1. What type of data this chunk contains\n"
        "2. Any security findings or issues\n"
        "3. Key patterns or anomalies\n\n"
        "Keep the analysis concise and factual."
    )
    
    prompt = template.format(
        json_chunk=state["json_chunk"],
        chunk_number=state["chunk_number"],
        total_chunks=state["total_chunks"]
    )
    
    result = llm.invoke(prompt)
    
    # Add to results
    current_results = state.get("analysis_results", [])
    current_results.append(f"Chunk {state['chunk_number']}: {result}")
    
    return {"analysis_results": current_results}

def summarize_node(state: State) -> dict:
    """Create final summary from all chunk analyses"""
    all_analyses = "\n\n".join(state["analysis_results"])
    
    template = PromptTemplate.from_template(
        "Based on these chunk analyses of a MITRE security report:\n\n"
        "{all_analyses}\n\n"
        "Create a comprehensive security assessment summary with:\n"
        "1. Executive Summary\n"
        "2. Key Security Findings\n"
        "3. Risk Assessment\n"
        "4. Recommendations\n\n"
        "Make it actionable and well-structured."
    )
    
    prompt = template.format(all_analyses=all_analyses)
    summary = llm.invoke(prompt)
    
    return {"final_summary": summary}

def process_large_json_file(file_path):
    """Process large JSON file using streaming approach"""
    print(f"🔄 Processing large JSON file: {file_path}")
    
    # Chunk the file
    chunks = chunk_large_json(file_path, max_chunk_size=2000)
    print(f"📊 Split into {len(chunks)} chunks")
    
    # Build graph
    graph = StateGraph(State)
    graph.add_node("analyze", analyze_chunk_node)
    graph.add_node("summarize", summarize_node)
    
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "summarize")
    graph.add_edge("summarize", END)
    
    compiled = graph.compile()
    
    # Process each chunk
    all_results = []
    for i, chunk in enumerate(chunks, 1):
        print(f"🔍 Processing chunk {i}/{len(chunks)}")
        
        try:
            result = compiled.invoke({
                "json_chunk": chunk,
                "chunk_number": i,
                "total_chunks": len(chunks),
                "analysis_results": [],
                "final_summary": ""
            })
            
            all_results.extend(result["analysis_results"])
            
        except Exception as e:
            print(f"❌ Error processing chunk {i}: {e}")
            all_results.append(f"Chunk {i}: Error - {e}")
    
    # Create final summary
    print("📋 Creating final summary...")
    final_result = compiled.invoke({
        "json_chunk": "",
        "chunk_number": 0,
        "total_chunks": len(chunks),
        "analysis_results": all_results,
        "final_summary": ""
    })
    
    return final_result["final_summary"]

# Usage
if __name__ == "__main__":
    json_file = 'mitre-report.json'
    
    if os.path.exists(json_file):
        file_size = os.path.getsize(json_file)
        print(f"📊 File size: {file_size:,} bytes")
        
        if file_size > 100000:  # > 100KB
            summary = process_large_json_file(json_file)
            
            # Save result
            with open('streaming_analysis_result.txt', 'w') as f:
                f.write(str(summary))
            
            print("\n" + "="*50)
            print("FINAL ANALYSIS:")
            print("="*50)
            print(summary)
        else:
            print("File is small enough for normal processing")
    else:
        print(f"❌ File {json_file} not found!")
