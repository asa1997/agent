from crewai import Agent, LLM, Task, Crew

# Using string identifier
agent = Agent(
    role='Local AI Expert',
    goal='Process information using a local model',
    backstory="An AI assistant running on local hardware.",
    llm='ollama/llama3.2:latest'
)

# Using LLM class for more control
# llm = LLM(
#     model="ollama/llama3.2:latest",
#     base_url="http://localhost:11434"
# )

# agent = Agent(
#     role='Local AI Expert',
#     llm=llm
# )

plan = Task(
    description=(
        "1. Prioritize the latest trends, key players, "
            "and noteworthy news on {topic}.\n"
        "2. Identify the target audience, considering "
            "their interests and pain points.\n"
        "3. Develop a detailed content outline including "
            "an introduction, key points, and a call to action.\n"
        "4. Include SEO keywords and relevant data or sources."
    ),
    expected_output="A comprehensive content plan document "
        "with an outline, audience analysis, "
        "SEO keywords, and resources.",
    agent=agent,
)

crew = Crew(
    agents=[agent],
    tasks=[plan],
    verbose=True
)

result = crew.kickoff(inputs={"topic": "Artificial Intelligence"})

print(result)