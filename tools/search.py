import os
from serpapi import GoogleSearch
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

def search_web(query: str, num_results: int = 5) -> list[dict]:
    """
    Search Google and return a list of results.
    Each result has: title, link, snippet
    """
    try:
        search = GoogleSearch({
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": num_results,
            "engine": "google"
        })
        results = search.get_dict()
        organic = results.get("organic_results", [])

        cleaned = []
        for r in organic:
            cleaned.append({
                "title": r.get("title", ""),
                "link": r.get("link", ""),
                "snippet": r.get("snippet", "")
            })

        return cleaned

    except Exception as e:
        print(f"Search error: {e}")
        return []


def format_search_results(results: list[dict]) -> str:
    """
    Converts search results into a clean readable string
    that we can pass to an agent as context.
    """
    if not results:
        return "No results found."

    formatted = ""
    for i, r in enumerate(results, 1):
        formatted += f"{i}. {r['title']}\n"
        formatted += f"   {r['snippet']}\n"
        formatted += f"   Source: {r['link']}\n\n"

    return formatted.strip()