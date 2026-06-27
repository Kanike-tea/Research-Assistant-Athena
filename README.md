# 🔬 Research Assistant

A FastAPI backend service powered by **LangChain** and **Google Gemini** that takes a topic string and produces four distinct outputs **in parallel**:

| Output          | Description                                      | Format         |
| --------------- | ------------------------------------------------ | -------------- |
| **Explanation** | Detailed, structured breakdown of the topic      | Markdown       |
| **Summary**     | Concise 2-3 sentence overview                    | Plain text     |
| **Keywords**    | 5-15 important terms and key-phrases             | JSON array     |
| **Category**    | Broad academic / professional classification     | Single label   |

## Architecture

```
POST /research { "topic": "..." }
         │
         ▼
   ┌─────────────────────────┐
   │   RunnableParallel      │    ← LangChain parallel execution
   │  ┌───────┬──────────┐   │
   │  │Explain│ Summary  │   │
   │  │Chain  │ Chain    │   │
   │  ├───────┼──────────┤   │
   │  │Keyword│ Category │   │
   │  │Chain  │ Chain    │   │
   │  └───────┴──────────┘   │
   └─────────────────────────┘
         │
         ▼
   ResearchResponse (JSON)
```

Each chain is a `PromptTemplate → LLM → StrOutputParser` pipeline. All four chains run concurrently through `RunnableParallel.ainvoke()`.

## Quick Start

### 1. Clone & install

```bash
git clone <repo-url>
cd Research-Assistant
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your Google API key
```

### 3. Run

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Test

```bash
curl -X POST http://localhost:8000/research \
  -H "Content-Type: application/json" \
  -d '{"topic": "Quantum Computing"}'
```

## API Endpoints

| Method | Path        | Description                    |
| ------ | ----------- | ------------------------------ |
| GET    | `/health`   | Liveness probe                 |
| POST   | `/research` | Analyse a topic (see below)    |
| GET    | `/docs`     | Interactive Swagger UI         |
| GET    | `/redoc`    | Alternative API documentation  |

### `POST /research`

**Request body:**

```json
{
  "topic": "Quantum Computing"
}
```

**Response:**

```json
{
  "topic": "Quantum Computing",
  "explanation": "## Quantum Computing\n\nQuantum computing leverages ...",
  "summary": "Quantum computing uses quantum-mechanical phenomena ...",
  "keywords": ["qubit", "superposition", "entanglement", "quantum gate", ...],
  "category": "Computer Science"
}
```

## Project Structure

```
Research-Assistant/
├── app/
│   ├── __init__.py     # Package marker
│   ├── config.py       # Environment variable loading
│   ├── models.py       # Pydantic request/response schemas
│   ├── prompts.py      # ChatPromptTemplates for each chain
│   ├── chains.py       # LangChain chains + RunnableParallel pipeline
│   └── main.py         # FastAPI application & endpoints
├── .env.example        # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

## Configuration

| Variable          | Default              | Description                         |
| ----------------- | -------------------- | ----------------------------------- |
| `GOOGLE_API_KEY`  | —                    | Google AI API key (required)        |
| `LLM_MODEL`       | `gemini-2.0-flash`   | Gemini model name                   |
| `LLM_TEMPERATURE` | `0.3`                | LLM sampling temperature            |