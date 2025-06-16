Here are some strategies to let an LLM-based agent work with a large JSON file (thousands of lines) without exceeding context limits or losing performance:

1. **Don’t dump the entire file into the prompt at once**
   LLMs have token limits. Instead, break the JSON into manageable pieces or provide access via a tool:

   * **Chunking**: Split the JSON text into chunks under the token limit (e.g., 2–3k tokens each). You can split by top-level keys or by character count.
   * **On-demand retrieval**: Instead of passing everything, let the agent request only the relevant parts via a custom “tool” or function that reads/parses the JSON and returns only the needed excerpt.
   * **Embedding + vector store**: If the goal is to let the agent answer arbitrary questions about the data, index chunks with embeddings (e.g., OpenAIEmbeddings + FAISS/Pinecone). At runtime, for a user question, retrieve top-k relevant chunks and pass them to the LLM.

2. **Example: Python code to chunk & index with LangChain**
   Below is a sketch using LangChain (you can adapt to your setup). It: (a) loads the JSON, (b) serializes into text chunks, (c) embeds and stores in FAISS, (d) defines a simple retrieval function.

   ```python
   from langchain.document_loaders import TextLoader
   from langchain.text_splitter import CharacterTextSplitter
   from langchain.vectorstores import FAISS
   from langchain.embeddings.openai import OpenAIEmbeddings
   import json

   # 1. Load JSON file
   path = "data/large.json"
   with open(path, "r", encoding="utf-8") as f:
       data = json.load(f)

   # 2. Serialize in a structured way
   # For example, if top-level is a list of records:
   records = data if isinstance(data, list) else [data]
   texts = []
   for i, rec in enumerate(records):
       part = json.dumps(rec, ensure_ascii=False, indent=None)
       texts.append(f"[record_{i}]: {part}")

   # 3. Split into chunks (approx 1000–2000 chars each)
   splitter = CharacterTextSplitter(
       separator="\n",
       chunk_size=2000,
       chunk_overlap=200
   )
   docs = []
   for text in texts:
       docs.extend(splitter.split_text(text))

   # 4. Embed & store in FAISS
   embeddings = OpenAIEmbeddings()  # configure your API key etc.
   vectorstore = FAISS.from_texts(docs, embeddings)

   # 5. Define a retrieval function
   def retrieve_json_chunks(query: str, k: int = 4):
       results = vectorstore.similarity_search(query, k=k)
       # results is a list of Documents, each with .page_content
       return [doc.page_content for doc in results]

   # Usage:
   # relevant_chunks = retrieve_json_chunks("find entries where status is 'active'")
   # Then pass those chunks in the prompt to the LLM.
   ```

   * You can wrap `retrieve_json_chunks` as a tool that the agent can call when needed.
   * If the JSON structure is nested, you might first flatten or serialize sub-sections with identifiers so chunks remain self-contained.

3. **Define a custom tool for the agent**
   If you’re using a framework like LangChain or your own agent orchestration:

   * Write a function, e.g. `query_json(query: str) -> str`, which under the hood does retrieval or filtering on the JSON and returns a concise JSON snippet or summary that matches the query.
   * Register this function as a tool in the agent. When the LLM needs to refer to the JSON, it emits a tool call; your function reads from disk or memory, processes, and returns only what’s needed.
   * This avoids ever including the full file in the prompt.

4. **Summarization for very large or complex data**
   If you only need high-level insights (not arbitrary queries), you can:

   * Precompute a summary of the JSON (e.g., aggregate stats, key fields, schema overview).
   * Pass that summary in the prompt.
   * For deeper dives, combine summarization with retrieval: agent uses summary to decide which part to retrieve.

5. **Streaming or progressive loading**
   Some LLM APIs or agent frameworks support “streaming” content or chaining calls:

   * First, send a summary or schema description.
   * Then, if more detail needed, send the next chunk, maintaining a running context (possibly summarizing earlier chunks to stay within window).
   * This is more involved but can handle extremely large files by iterative prompting + summarization.

6. **Practical tips**

   * **Token-count budgeting**: Use a tokenizer (e.g., tiktoken) to measure chunk sizes to ensure they fit within the LLM’s limit.
   * **Metadata**: When chunking, attach metadata (e.g., “this chunk covers records 1000–1999”, or “section: users → preferences”) so retrieval is more precise.
   * **Error handling**: Ensure your tool gracefully handles queries that match nothing.
   * **Security/privacy**: If the JSON contains sensitive data, be careful about what you expose to the LLM; filter or anonymize before indexing.
   * **Local vs. remote**: If the agent runs in an environment without access to the file system, consider uploading the JSON to a database or storage the agent can access.

7. **Example: Simple chunking without LangChain**
   If you don’t want to add dependencies, here’s a minimal approach:

   ```python
   import json

   def load_and_chunk(path, max_chars=2000, overlap=200):
       with open(path, "r", encoding="utf-8") as f:
           text = f.read()
       chunks = []
       start = 0
       length = len(text)
       while start < length:
           end = min(length, start + max_chars)
           chunk = text[start:end]
           chunks.append(chunk)
           start = end - overlap
       return chunks

   # Later: for a query, you can scan chunks for keywords or send top-N chunks to the LLM.
   ```

   This doesn’t provide semantic search, but for simple keyword-based filtering it can work.

8. **If you truly need to pass the raw file in one go**

   * Some platforms allow file uploads; the agent can refer to the file by name and you implement a tool that reads it. The prompt might say: “The file `large.json` is available; call the tool `read_json_section` with a JSONPath or key to extract.”
   * Avoid embedding the whole text in the prompt.

9. **Putting it into an agent workflow**

   * **Step 1**: Agent receives user question: e.g. “List all users created after Jan 1, 2025”
   * **Step 2**: Agent decides to call `query_json("users[?created_at>'2025-01-01']")` (or similar).
   * **Step 3**: Your tool loads/parses JSON (possibly using `jsonpath-ng` or custom filter), returns a JSON snippet or summary.
   * **Step 4**: Agent incorporates that snippet in a follow-up prompt: “Here are the matching entries: …. Now format them as a report.”
     This pattern scales regardless of file size.

10. **Handling very large JSON (GBs)**

    * If the file is extremely large (gigabytes), you likely need a database or streaming parser (e.g., `ijson`) to filter without loading all into memory.
    * Preprocess: Extract relevant fields into a database or smaller files, then index.
    * Use the same retrieval-tool pattern on the processed data.

---

**Summary**: Rather than passing thousands of lines of JSON directly into the LLM prompt, create a tool/function that can read and return only relevant parts (via chunking, semantic retrieval, filtering, or summarization). If you need free-text question-answering over the JSON, index chunks with embeddings and retrieve top matches. Register this as a tool in your agent framework so the agent can “call” it. This keeps prompt sizes manageable, improves performance, and lets you scale to very large files.
