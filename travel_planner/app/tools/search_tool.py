import logging
import httpx
import re
from travel_planner.app.config import settings

logger = logging.getLogger(__name__)

def clean_snippet(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 120:
        text = text[:117] + "..."
    return text

def perform_web_search(destination: str, query_type: str = "general") -> str:
    query = f"top attractions, dining, tips, seasonal activities, safety for travel in {destination}"
    if query_type == "weather":
        query = f"weather and travel season considerations for {destination}"

    if settings.tavily_api_key:
        try:
            logger.info("Using Tavily for web search...")
            response = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "search_depth": "advanced"
                },
                timeout=10.0
            )
            if response.status_code == 200:
                results = response.json().get("results", [])
                items = []
                for r in results[:2]:
                    title = r.get("title", "").strip()
                    snippet = clean_snippet(r.get("content", ""))
                    items.append(f"- {title}: {snippet}")
                return "\n".join(items)
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")

    if settings.serper_api_key:
        try:
            logger.info("Using Serper for web search...")
            response = httpx.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json"
                },
                json={"q": query},
                timeout=10.0
            )
            if response.status_code == 200:
                results = response.json().get("organic", [])
                items = []
                for r in results[:2]:
                    title = r.get("title", "").strip()
                    snippet = clean_snippet(r.get("snippet", ""))
                    items.append(f"- {title}: {snippet}")
                return "\n".join(items)
        except Exception as e:
            logger.error(f"Serper search failed: {e}")

    if settings.exa_api_key:
        try:
            logger.info("Using Exa for web search...")
            response = httpx.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": settings.exa_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "query": query,
                    "numResults": 2,
                    "useAutoprompt": True
                },
                timeout=10.0
            )
            if response.status_code == 200:
                results = response.json().get("results", [])
                items = []
                for r in results[:2]:
                    title = r.get("title", "").strip()
                    snippet = clean_snippet(r.get("text", r.get("highlights", "")))
                    items.append(f"- {title}: {snippet}")
                return "\n".join(items)
        except Exception as e:
            logger.error(f"Exa search failed: {e}")

    logger.warning("No search API key provided or search APIs failed. Falling back to mock search data.")
    return get_mock_search_data(destination)

def get_mock_search_data(destination: str) -> str:
    dest = destination.lower().strip()
    if "paris" in dest:
        return (
            "- Eiffel Tower & Louvre: Book summit tickets in advance. Louvre is closed on Tuesdays.\n"
            "- Dining: Highly recommend bistros in Latin Quarter and Saint-Germain-des-Prés.\n"
            "- Marais & Montmartre: Features excellent fashion, historic streets, and views from Sacré-Cœur.\n"
            "- Safety & Tips: Caution against pickpocketing in crowded tourist zones. Learn basic greetings."
        )
    elif "tokyo" in dest:
        return (
            "- Tokyo Highlights: Shibuya Crossing, Senso-ji Temple in Asakusa, teamLab Planets, and Meiji Shrine.\n"
            "- Dining Guide: Tsukiji Market for sushi, Omoide Yokocho for yakitori, Kagurazaka for fine dining.\n"
            "- Public Transit: Highly punctual subways; purchase a Pasmo/Suica IC card for convenience.\n"
            "- Safety & Tips: Very safe. Carry cash, keep trash with you as public cans are rare."
        )
    else:
        return (
            f"- Attractions in {destination.title()}: Popular local landmarks and central parks. Tours are recommended.\n"
            f"- Dining & Food: Traditional street foods and highly-ranked family eateries.\n"
            f"- Navigation: Public buses or subways are the most budget-friendly.\n"
            f"- Safety & Tips: Keep items secure in markets. Learn basic local greetings."
        )
