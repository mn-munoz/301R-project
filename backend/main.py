"""
RoadWise — FastAPI Backend
---------------------------
CLASS CONCEPTS DEMONSTRATED:
  ✅ Agents-as-tools  — route_agent and experience_agent are loaded from agents.yaml,
                        wrapped with as_tool(), and registered in the ToolBox so the
                        Orchestrator LLM can call them exactly like any other function tool.
  ✅ Tool Calling      — all Google Maps calls, gas math, and weather are plain Python
                        functions registered in the ToolBox with toolbox.tool().
  ✅ Multiple Agents   — four agents defined in agents.yaml: intake, route, experience,
                        orchestrator. Loaded and wired together at startup.
  ✅ Hallucination ctrl — grounding enforced in each agent's system prompt (in agents.yaml).

Agent loading follows the same pattern as the professor's guardrails.py:
  1. Read agents.yaml (multi-document YAML, one agent per --- section).
  2. Sub-agents (route_agent, experience_agent) are automatically wrapped as tools
     so the orchestrator LLM can call them by name.
  3. The two "main" agents (intake_agent, orchestrator) are invoked directly
     by the endpoint, one per phase of the conversation.

Endpoints:
  POST /api/chat            — main chat endpoint (intake phase + planning phase)
  GET  /api/health          — health check
  DELETE /api/session/{id}  — clear a session
"""

import json
import re
import yaml
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from config import OPENAI_API_KEY
from schemas.trip import ChatRequest, ChatResponse, TripBrief, VehicleInfo
from run_agent import run_agent, as_tool
from toolbox import ToolBox
from app_agents.orchestrator import build_trip_plan

# ── Tool imports ──────────────────────────────────────────────────────────────
from tools.gas_calculator import calculate_gas_stops
from tools.weather import get_weather_forecast
from tools.google_maps_tools import get_route, get_midpoint_cities, search_places


# ── OpenAI client ─────────────────────────────────────────────────────────────
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# ── Load agents from YAML ─────────────────────────────────────────────────────
# Same pattern as the professor's guardrails.py:
#   agents.yaml holds every agent's name, model, prompt, and tool list.
#   We parse the multi-document file and store agents as plain dicts.
#
_agents_path = Path(__file__).parent / "agents.yaml"
_all_agents: list[dict] = list(yaml.safe_load_all(_agents_path.read_text()))


# ── ToolBox — register code tools, then wrap sub-agents as tools ──────────────
#
# Step 1: Register all plain Python functions as callable tools.
#         ToolBox introspects type hints to auto-generate JSON schemas.
#
# Step 2: Wrap sub-agents as tools using as_tool().
#         as_tool() converts any agent dict into an async function(input: str) -> str
#         that runs that agent's full tool-calling loop internally.
#         The resulting function is registered in the ToolBox under the agent's name.
#
# Step 3: The orchestrator's YAML lists "route_agent" and "experience_agent" as tools.
#         When the orchestrator LLM calls one of them, the ToolBox dispatches to the
#         wrapped run_agent() — the orchestrator never knows it's talking to another LLM.
#
toolbox = ToolBox()

# Register code-as-tool functions
toolbox.tool(calculate_gas_stops)
toolbox.tool(get_weather_forecast)
toolbox.tool(get_route)
toolbox.tool(get_midpoint_cities)
toolbox.tool(search_places)

# Sub-agents: automatically wrap every agent that is NOT a direct "main" agent
# (mirrors the professor's pattern of wrapping everything except `main`)
_DIRECT_AGENTS = {"intake_agent", "orchestrator"}

for _agent in _all_agents:
    if _agent["name"] not in _DIRECT_AGENTS:
        toolbox.tool(as_tool(client, toolbox, _agent))

# Grab the two agents we invoke directly by phase
intake_agent_config    = next(a for a in _all_agents if a["name"] == "intake_agent")
orchestrator_config    = next(a for a in _all_agents if a["name"] == "orchestrator")


# ── In-memory session store ───────────────────────────────────────────────────
# { session_id: { "history": [...], "phase": "intake"|"done", "plan": TripPlan|None } }
sessions: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ RoadWise backend starting up")
    print(f"   Loaded {len(_all_agents)} agents from agents.yaml: "
          f"{[a['name'] for a in _all_agents]}")
    yield
    print("🛑 RoadWise backend shutting down")


app = FastAPI(
    title="RoadWise API",
    description="Road trip planning powered by multi-agent AI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "RoadWise"}


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    sessions.pop(session_id, None)
    return {"cleared": True}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id   = request.session_id
    user_message = request.message.strip()

    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Initialise session on first contact
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "phase": "intake",
            "plan": None,
        }

    session = sessions[session_id]

    # ── PHASE: intake ─────────────────────────────────────────────────────────
    if session["phase"] == "intake":
        # run_agent appends the user message and all response items to history
        # automatically — history is mutated in-place across turns.
        reply = await run_agent(
            client,
            toolbox,
            intake_agent_config,
            user_message=user_message,
            history=session["history"],
        )

        # run_agent returns None only if the `conclude` tool is called — which
        # we never register, so this is purely a safety guard.
        if reply is None:
            reply = "Sorry, something went wrong. Could you repeat that?"

        # Check whether the intake agent has emitted the completion JSON block
        trip_brief = _parse_trip_brief(reply)

        if trip_brief:
            display_reply = reply.split("TRIP_BRIEF_JSON:")[0].strip()
            session["phase"] = "planning"

            # ── PHASE: planning ───────────────────────────────────────────────
            # The orchestrator agent (loaded from agents.yaml) calls route_agent
            # and experience_agent as tools via the ToolBox — agents-as-tools pattern.
            try:
                orchestrator_output = await run_agent(
                    client,
                    toolbox,
                    orchestrator_config,
                    user_message=trip_brief.model_dump_json(indent=2),
                ) or ""

                plan = build_trip_plan(orchestrator_output, trip_brief)
                session["plan"]  = plan
                session["phase"] = "done"

                return ChatResponse(
                    session_id=session_id,
                    reply=display_reply,
                    trip_plan=plan,
                    phase="done",
                )

            except Exception as e:
                session["phase"] = "intake"
                return ChatResponse(
                    session_id=session_id,
                    reply=(
                        f"{display_reply}\n\n"
                        f"⚠️ I hit a snag while building your plan: {str(e)}. "
                        "Let's try again — could you re-confirm your trip details?"
                    ),
                    phase="intake",
                )

        # Still collecting info — return the agent's next question
        return ChatResponse(
            session_id=session_id,
            reply=reply,
            phase="intake",
        )

    # ── PHASE: done ───────────────────────────────────────────────────────────
    if session["phase"] == "done":
        return ChatResponse(
            session_id=session_id,
            reply=(
                "Your trip plan is ready above! 🗺️ "
                "If you'd like to plan a different trip, click **New Trip** to start over."
            ),
            trip_plan=session["plan"],
            phase="done",
        )

    raise HTTPException(status_code=500, detail="Unknown session state.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_trip_brief(text: str) -> TripBrief | None:
    """
    Scan the intake agent's response for the TRIP_BRIEF_JSON: marker.
    Returns a validated TripBrief if found, otherwise None.
    """
    if "TRIP_BRIEF_JSON:" not in text:
        return None
    try:
        json_part = text.split("TRIP_BRIEF_JSON:", 1)[1].strip()
        match = re.search(r"\{[\s\S]*\}", json_part)
        if not match:
            return None
        data = json.loads(match.group())
        vehicle_data = data.pop("vehicle", {})
        vehicle = VehicleInfo(**vehicle_data)
        return TripBrief(vehicle=vehicle, **data)
    except Exception:
        return None
