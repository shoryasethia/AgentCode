# search/external_search.py

import os
import json
from typing import List
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from bs4 import BeautifulSoup
import requests

@tool
def external_search(query: str, max_results: int = 5) -> str:
    """
    Search external sources using the Tavily Search API.

    Args:
        query: The search query.
        max_results: The maximum number of results to return.

    Returns:
        A JSON string with the search results.
    """
    if not os.getenv("TAVILY_API_KEY"):
        return json.dumps({"error": "Tavily API key not set in environment variables."})

    try:
        search_tool = TavilySearch(max_results=max_results)
        results = search_tool.invoke(query)
        return json.dumps(results, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Tavily search failed with error: {str(e)}",
            "query": query,
            "results": []
        })

@tool
def scrape_content(urls: List[str]) -> str:
    """
    Scrape text content from a list of URLs.

    Args:
        urls: List of URLs to scrape.

    Returns:
        JSON string with scraped content from each URL.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    scraped_results = []
    for url in urls:
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                for script_or_style in soup(["script", "style"]):
                    script_or_style.decompose()
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = ' '.join(chunk for chunk in chunks if chunk)
                scraped_results.append({
                    'url': url,
                    'content': clean_text[:5000]
                })
        except Exception as e:
            scraped_results.append({'url': url, 'error': f"Error scraping: {str(e)}"})
    
    return json.dumps(scraped_results, indent=2)