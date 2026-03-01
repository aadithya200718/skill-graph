# SkillGraph

AI-powered diagnostic learning platform that finds and fixes invisible prerequisite gaps using knowledge graph analysis.

## Architecture

- **Backend**: FastAPI + Python 3.11
- **Graph DB**: Neo4j Aura (free tier)
- **Agents**: 3 LangGraph agents communicating via A2A protocol
- **LLM**: Ollama + Llama 3.2 8B (primary), Gemini 3.1 Pro Preview (fallback)
- **Frontend**: React 18 + Vite + D3.js

## Quick Start

### Prerequisites

1. Python 3.11+
2. Node.js 18+
3. Neo4j Aura instance (free at neo4j.com/cloud)
4. Gemini API key (free at aistudio.google.com/apikey)

### Backend

```bash
cd backend
cp .env.example .env
# Edit .env with your Neo4j and Gemini credentials
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Demo Mode

1. Click "Demo Mode" toggle in the header
2. Select "Priya Sharma" from the dropdown
3. Navigate to Knowledge Graph to see gap visualization
4. Take a quiz on Machine Learning
5. View root cause analysis and remediation plan

## API Endpoints

| Method | Endpoint                   | Description                  |
| ------ | -------------------------- | ---------------------------- |
| GET    | /api/v1/health             | Health check                 |
| GET    | /api/v1/quiz/{subject}     | Get diagnostic quiz          |
| POST   | /api/v1/quiz/submit        | Submit quiz answers          |
| GET    | /api/v1/graph/{student_id} | Get graph visualization data |
| POST   | /api/v1/remediate          | Generate remediation plan    |
| POST   | /api/v1/triage             | Generate exam triage plan    |
| GET    | /api/v1/agents/activity    | Get A2A agent activity log   |
| GET    | /api/v1/demo/profiles      | Get demo profiles            |
| POST   | /api/v1/demo/activate      | Activate a demo profile      |
