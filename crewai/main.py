from summary import SecurityAnalysisCrew

def quick_test():
    # Create and run the crew with sample input
    crew = SecurityAnalysisCrew().crew()
    
    result = crew.kickoff(inputs={
        "report_path": "mitre-report.json",
        "instruction": "Analyze the security assessment report"
    })
    
    print("Analysis Result:")
    print(result)

if __name__ == "__main__":
    quick_test()