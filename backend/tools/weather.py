"""
Weather Tool — code-as-tool
-----------------------------
Fetches a weather forecast for a given city using the OpenWeatherMap API.
Used by the Experience Agent to warn about weather along the route.
"""

import httpx
from config import OPENWEATHER_API_KEY


async def get_weather_forecast(city: str) -> dict:
    """
    Get a 5-day weather forecast for a city.

    Args:
        city: City name (e.g. "Denver, CO" or "Moab, Utah").

    Returns:
        A dict with a summary of upcoming weather conditions.
    """
    if not OPENWEATHER_API_KEY:
        return {"error": "OpenWeather API key not configured. Skipping weather check."}

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "imperial",
        "cnt": 8,  # ~2 days of 3-hour intervals
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            forecasts = []
            for item in data.get("list", []):
                forecasts.append({
                    "time": item["dt_txt"],
                    "temp_f": item["main"]["temp"],
                    "description": item["weather"][0]["description"],
                    "wind_mph": round(item["wind"]["speed"], 1),
                })

            return {
                "city": city,
                "forecasts": forecasts[:4],  # return first 4 time slots
                "summary": f"Weather for {city}: {forecasts[0]['description']}, "
                           f"{forecasts[0]['temp_f']:.0f}°F" if forecasts else "No data",
            }
        except Exception as e:
            return {"city": city, "error": str(e), "summary": "Weather data unavailable."}
