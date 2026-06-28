# Athena

A FastAPI backend service powered by **LangChain** and **Local AI via Ollama (Llama 3.2:1b)** that takes a topic string and produces four distinct outputs **in parallel**. The results are streamed to a high-density, glassmorphic analytical dashboard via Server-Sent Events (SSE).

| Output          | Description                                      | Format         |
| --------------- | ------------------------------------------------ | -------------- |
| **Explanation** | Detailed, structured breakdown of the topic      | Markdown       |
| **Summary**     | Concise 2-3 sentence overview                    | Plain text     |
| **Keywords**    | 5-15 important terms and key-phrases             | JSON array     |
| **Category**    | Broad academic / professional classification     | Single label   |

## Architecture

```
POST /research/stream { "topic": "..." }
         |
         V
   stream_research() async generator
   +--------------------------------------+
   |  asyncio.create_task() x 4           |
   |  +----------+  +----------+          |
   |  | Summary  |  | Category |  <- fast |
   |  +----+-----+  +----+-----+          |
   |       |             |                |
   |  +----+-----+  +----+----------+     |
   |  | Keywords |  | Explanation   |     |
   |  +----+-----+  +----+----------+     |
   |       |             |                |
   |  asyncio.as_completed() -> yield     |
   +--------------------------------------+
         | SSE events (named: summary, category, keywords, explanation)
         V
   Browser: fetch() + ReadableStream
```

Each chain is a `PromptTemplate -> LLM -> StrOutputParser` pipeline. All four chains run concurrently as independent asyncio tasks.

## Quick Start

### 1. Clone & install

```bash
git clone <repo-url>
cd Athena
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Make sure Ollama is installed and running, then pull the model:
ollama pull llama3.2:1b
```

### 3. Run

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Access Dashboard

Open `http://localhost:8000/` in your browser to access the analytical dashboard.

## API Endpoints

| Method | Path               | Description                               |
| ------ | ------------------ | ----------------------------------------- |
| GET    | `/`                | Serves the frontend dashboard             |
| GET    | `/health`          | Liveness probe                            |
| GET    | `/metrics`         | API usage metrics and performance statistics |
| POST   | `/research/stream` | Stream research results via SSE           |
| POST   | `/research`        | Batch analyse a topic (legacy compatible) |
| GET    | `/docs`            | Interactive Swagger UI                    |
| GET    | `/redoc`           | Alternative API documentation             |

### `POST /research/stream`

**Request body:**

```json
{
  "topic": "Quantum Computing"
}
```

**Response (text/event-stream):**

```text
event: category
data: {"key": "category", "value": "Computer Science"}

event: summary
data: {"key": "summary", "value": "Quantum computing uses quantum-mechanical phenomena..."}

event: keywords
data: {"key": "keywords", "value": ["qubit", "superposition", "entanglement"]}

event: explanation
data: {"key": "explanation", "value": "## Quantum Computing\n\n..."}

event: done
data: {}
```

## Project Structure

```text
Athena/
+-- app/
|   +-- static/         # Frontend dashboard assets (HTML, CSS, JS)
|   +-- __init__.py     # Package marker
|   +-- config.py       # Environment variable loading
|   +-- models.py       # Pydantic request/response schemas
|   +-- prompts.py      # ChatPromptTemplates for each chain
|   +-- chains.py       # LangChain chains + asyncio stream generator
|   +-- metrics.py      # API metrics collection and monitoring
|   +-- main.py         # FastAPI application & endpoints
+-- .env.example        # Environment variable template
+-- .gitignore
+-- requirements.txt
+-- README.md
```

## Configuration

| Variable           | Default                 | Description                         |
| ------------------ | ----------------------- | ----------------------------------- |
| `OLLAMA_BASE_URL`  | `http://localhost:11434`| Ollama server URL                   |
| `LLM_MODEL`        | `llama3.2:1b`           | Ollama model name                   |
| `LLM_TEMPERATURE`  | `0.1`                   | LLM sampling temperature            |

## Features

- FastAPI backend with asynchronous processing
- Local AI integration using Ollama (Llama 3.2:1b)
- Parallel execution using AsyncIO
- Real-time streaming using Server-Sent Events (SSE)
- High-density, glassmorphic UI dashboard with dark mode
- Execution time tracking and LangChain API metrics
- Local search history sidebar with delete functionality
- Downloadable research reports (PDF)
- Automatic summary generation
- Keyword extraction
- Topic categorisation
- Interactive Swagger API documentation

## Future Enhancements

- Authentication and user accounts
- Multiple LLM support
- Citation generation
- Docker deployment
- Cloud deployment

## Video Demo

![Athena Demo](https://github.com/user-attachments/assets/73fce60a-bd65-445f-9c05-7c71dfc71877)
