# RoadWise — AI Road Trip Planner
> Agent Engineering (CS 301R) Final Project

A multi-agent AI app that helps users plan road trips through a conversational chatbot interface.

---

## Class Concepts Demonstrated

| Concept | Where |
|---|---|
| **Prompt Engineering** | `intake_agent.py` — enforces one-question-at-a-time format + JSON completion signal; `experience_agent.py` — strict output schema and persona |
| **Multiple Agents** | `orchestrator.py` — coordinates Route Agent and Experience Agent as sub-agents |
| **Tool Calling (MCP)** | `route_agent.py` + `experience_agent.py` — use Google Maps MCP for real distances, places, directions |
| **Tool Calling (code-as-tool)** | `gas_calculator.py` — deterministic Python function called by the Route Agent |
| **Hallucination Control** | Agents are grounded to tool outputs only — they cannot invent place names or distances |
| **Jailbreak Protection** | Intake Agent system prompt explicitly rejects off-topic requests |

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys in `.envrc` (see below)

### Environment Variables
```bash
export OPENAI_API_KEY="..."
export GOOGLE_API_KEY="..."          # Google Maps Platform key
export OPENWEATHER_API_KEY="..."     # Optional — for weather forecasts
```
Run `direnv allow` if using direnv, or `source .envrc` manually.

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

---

## Architecture

```
User (React UI)
    ↓ POST /api/chat
FastAPI (main.py)
    ↓ multi-turn conversation
Intake Agent (gpt-4.1-mini)
    ↓ TripBrief JSON
Orchestrator
    ├── Route Agent (gpt-4.1)
    │     ├── Google Maps MCP  ← real route data
    │     └── calculate_gas_stops()  ← code-as-tool
    └── Experience Agent (gpt-4.1)
          ├── Google Maps MCP  ← real places
          └── get_weather_forecast()  ← code-as-tool
    ↓ TripPlan JSON
React (TripPlanCard.jsx)
```

---

## Project Structure

```
301R-project/
├── .envrc
├── backend/
│   ├── main.py                  # FastAPI app
│   ├── config.py                # API keys + model constants
│   ├── requirements.txt
│   ├── agents/
│   │   ├── intake_agent.py      # Conversational intake
│   │   ├── route_agent.py       # Route + gas logistics
│   │   ├── experience_agent.py  # Hotels, food, activities
│   │   └── orchestrator.py      # Pipeline coordinator
│   ├── tools/
│   │   ├── gas_calculator.py    # Code-as-tool: fuel math
│   │   └── weather.py           # Code-as-tool: weather API
│   ├── mcp/
│   │   └── google_maps.py       # Google Maps MCP client
│   └── schemas/
│       └── trip.py              # Pydantic data models
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── index.css
        ├── api/
        │   └── chat.js          # fetch wrapper
        └── components/
            ├── ChatWindow.jsx   # Main chat UI
            ├── MessageBubble.jsx
            └── TripPlanCard.jsx # Renders the trip plan
```
