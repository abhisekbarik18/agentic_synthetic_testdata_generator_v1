# Agentic LLM-Powered Test Data Simulator

A production-ready synthetic test data simulator that translates natural-language prompts into realistic, validated, relational datasets using a multi-agent LangGraph workflow.

---

## Key Features

- **Multi-Agent LangGraph Pipeline**:
  1. **Scenario Exploration Agent**: Builds a domain-specific scenario brief with explicit assumptions, workflows, realism rules, and financial reconciliation guidance. It does not claim live external research.
  2. **Requirement Analysis Agent**: Extracts entities, fields, data types, constraints, nullability, uniqueness, foreign-key relationships, and business rules.
  3. **Planning Agent**: Determines topological generation order and batching strategies.
  4. **Data Generation Agent**: Generates realistic synthetic records, boundary values, negative cases, nulls, and outliers.
  5. **Validation Agent**: Performs schema validation, constraint enforcement, referential integrity verification, financial statement reconciliations, and LLM-based business rule auditing with automatic self-repair retry loops.
  6. **Export Agent**: Exports datasets into CSV, JSON, XLSX, XML, SQL INSERT statements, Parquet, PDF, HTML, Markdown, and DOCX. Financial statement PDFs use the generated statement sections, periods, line items, amounts, and currencies.
  7. **Orchestrator**: Manages state, conditional edges, retry counts, checkpointing, and real-time WebSocket progress broadcasts.

- **Universal Multi-Provider LLM Support**:
  - **Groq** (`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `mixtral-8x7b-32768`)
  - **OpenRouter** (unified gateway to 200+ top frontier models)
  - **OpenAI** (`gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini`)
  - **Google Gemini** (`gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash`)
  - **Anthropic** (`claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022`)
  - **DeepSeek** (`deepseek-chat`, `deepseek-coder`)
  - **Mistral AI** (`mistral-large-latest`, `codestral-latest`)
  - **Ollama** (Local offline execution with `llama3.1`, `qwen2.5-coder`)
  - **Azure OpenAI** (Enterprise deployments)
  - **Local / Custom OpenAI-compatible endpoints** (LM Studio, vLLM, LocalAI)

- **Natural-Language Export & Refinement**:
  - Request exports through the UI in multiple formats simultaneously.
  - Follow-up prompts detect named output formats (for example, "convert this to Parquet and SQL"). Enable **Regenerate Records** to apply data or schema changes.
  - Export filenames include a UTC timestamp; the downloads panel labels the latest version for each entity and format.
  - Generate document exports and use the Financial Statements starter prompt for an SOI, balance sheet, cash flow statement, and statement of changes in equity.
  - Describe other statement or report types directly in the prompt; document exports are produced for each generated entity.

- **Modern Responsive Dashboard**:
  - Next.js 15, TypeScript, Tailwind CSS.
  - Light and dark themes with a settings control, saved across visits and system-theme support by default.
  - Live agent status cards with spinner/completion indicators.
  - Interactive multi-entity tabular preview with real-time text filtering.
  - Schema inspection viewer and detailed data-quality validation reports.
  - One-click downloads with file size and record metrics.

---

## Project Structure

```
agentic_tdm_v01/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application & lifespan
│   │   ├── config.py                # Pydantic Settings loaded from .env
│   │   ├── database.py              # SQLAlchemy engine (SQLite / PostgreSQL)
│   │   ├── models/
│   │   │   ├── db_models.py         # Persistent Job ORM model
│   │   │   └── schemas.py           # Pydantic API & agent schemas
│   │   ├── api/
│   │   │   ├── routes.py            # REST API endpoints
│   │   │   └── websocket.py         # Real-time WebSocket connection manager
│   │   ├── agents/
│   │   │   ├── state.py             # Shared TypedDict AgentState
│   │   │   ├── orchestrator.py      # LangGraph StateGraph & conditional retry router
│   │   │   ├── requirement_agent.py # Entity & constraint extractor
│   │   │   ├── planning_agent.py    # Topological dependency planner
│   │   │   ├── generation_agent.py  # Batch synthetic record generator
│   │   │   ├── validation_agent.py  # Schema & referential integrity auditor
│   │   │   └── export_agent.py      # Multi-format exporter
│   │   ├── llm/
│   │   │   └── provider.py          # Universal modular provider factory
│   │   ├── services/
│   │   │   ├── generation_service.py # Background thread job runner
│   │   │   └── export_service.py     # On-demand format converter
│   │   └── utils/
│   │       ├── logging_config.py    # Structured logging
│   │       └── security.py          # SQL injection & file-size guards
│   ├── sample_datasets/             # Sample datasets & fixtures
│   ├── tests/                       # Unit and integration test suite
│   ├── .env.example                 # Template for all LLM providers & settings
│   └── requirements.txt             # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── app/                     # Next.js App Router (page.tsx, layout.tsx)
│   │   ├── components/              # PromptEditor, AgentStatus, DataPreview, etc.
│   │   ├── hooks/                   # useWebSocket hook
│   │   ├── lib/                     # api.ts client
│   │   └── types/                   # TypeScript interfaces
│   ├── package.json
│   ├── tsconfig.json
│   └── tailwind.config.ts
└── README.md
```

---

## Quickstart Setup & 1-Click Scripts (Windows)

You can run the entire application with a single command or double-click using the provided automation scripts:

### Option A: 1-Click Launch (Recommended)

Double-click or run:
```cmd
start.bat
```
or in PowerShell:
```powershell
.\start.ps1
```

**What `start.ps1` / `start.bat` does automatically:**
1. Verifies Python 3.10+ and Node.js 18+ exist in PATH.
2. Checks for `backend\.env`; if missing, automatically copies `backend\.env.example` to `backend\.env`.
3. Creates the Python virtual environment (`backend\venv`) if not present.
4. Installs / updates all backend dependencies (`pip install -r requirements.txt`).
5. Installs frontend packages (`npm install`) if `node_modules` is missing.
6. Launches the FastAPI backend (`http://localhost:8000`) and Next.js frontend (`http://localhost:3000`) in separate dedicated terminal windows.
7. Automatically opens `http://localhost:3000` in your default browser.

---

### Option B: 1-Click Shutdown

Double-click or run:
```cmd
stop.bat
```
or in PowerShell:
```powershell
.\stop.ps1
```

**What `stop.ps1` / `stop.bat` does:**
- Detects and terminates processes listening on port 8000 (Backend) and port 3000 (Frontend).
- Closes the dedicated terminal windows cleanly.

---

### Option C: Manual Step-by-Step Launch

1. Navigate to the `backend` folder:
   ```powershell
   cd "d:\Projects\Private Equity TDM\agentic_tdm_v01\backend"
   ```

2. Copy the example configuration to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```

3. Open `.env` and set your preferred provider and API key. For example, for **Groq**:
   ```env
   LLM_PROVIDER=groq
   LLM_MODEL=llama-3.3-70b-versatile
   GROQ_API_KEY=your_actual_groq_api_key_here
   ```
   Or for **OpenRouter**:
   ```env
   LLM_PROVIDER=openrouter
   LLM_MODEL=meta-llama/llama-3.3-70b-instruct
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```
   Or for **OpenAI**:
   ```env
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4o-mini
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   Provider endpoints and the OpenRouter site URL can also be configured in `.env`. Set `CORS_ORIGINS` to a JSON array containing the frontend origin(s), for example `["http://localhost:3000"]`; wildcard origins are not enabled by default.

---

### Step 2: Install Backend Dependencies & Run

1. Create and activate a Python virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

3. Run the automated tests to verify the setup:
   ```powershell
   pytest
   ```

4. Start the FastAPI backend server:
   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   The backend API will be live at `http://localhost:8000` (Interactive Swagger docs at `http://localhost:8000/docs`).

---

### Step 3: Install Frontend Dependencies & Run

Open a **separate PowerShell terminal window**:

1. Navigate to the `frontend` folder:
   ```powershell
   cd "d:\Projects\Private Equity TDM\agentic_tdm_v01\frontend"
   ```

2. Install npm packages:
   ```powershell
   npm install
   ```

3. Start the Next.js development server:
   ```powershell
   npm run dev
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```

---

## API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check, active provider & model info |
| `POST` | `/api/generate` | Starts a new agentic generation job |
| `GET` | `/api/jobs` | Lists all jobs with pagination |
| `GET` | `/api/jobs/{id}` | Retrieves job status, agent progression, and results |
| `GET` | `/api/jobs/{id}/data` | Retrieves tabular preview of generated records |
| `POST` | `/api/jobs/{id}/export` | Re-exports dataset into additional requested formats |
| `GET` | `/api/jobs/{id}/export/{filename}` | Downloads a specific generated export file |
| `POST` | `/api/jobs/{id}/followup` | Applies natural-language follow-up modifications |
| `WS` | `/api/ws/{id}` | Real-time WebSocket streaming of agent execution steps |
