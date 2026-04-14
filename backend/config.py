import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# Model assignments — swap these if your class uses different model strings
INTAKE_MODEL = "gpt-5-mini"       # lightweight, great for conversation
ROUTE_MODEL = "gpt-5"             # stronger reasoning for route logic
EXPERIENCE_MODEL = "gpt-5"        # stronger for curating recommendations
ORCHESTRATOR_MODEL = "gpt-5-mini" # just coordinates, no heavy lifting

# Update these strings to "gpt-5" / "gpt-5-mini" once available in your API tier
