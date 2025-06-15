import os
from tavily import TavilyClient

# Step 1. Instantiating your TavilyClient
api_key = os.environ.get("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=api_key)

# Step 2. Executing a simple search query
response = tavily_client.search("Who is Leo Messi?")

# Step 3. That's it! You've done a Tavily Search!
print(response)