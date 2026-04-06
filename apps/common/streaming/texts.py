from __future__ import annotations


STREAM_TEXTS: dict[str, dict[str, str]] = {
    "rewrite_query": {
        "start": "Rewriting your query for clarity",
        "end": "Finished rewriting your query for clarity",
    },
    "classify_intent": {
        "start": "Clarifying what you’re aiming to explore",
        "end": "Finished clarifying what you’re aiming to explore",
    },
    "plan": {
        "start": "Shaping the optimal plan for your question",
        "end": "Finished shaping the optimal plan for your question",
    },
    "search": {
        "start": "Gathering the key data points",
        "end": "Finished gathering the key data points",
    },
    "generate_chart": {
        "start": "Building charts from the results",
        "end": "Finished building charts from the results",
    },
    "analysis": {
        "start": "Reviewing the data to uncover insights",
        "end": "Finished reviewing the data to uncover insights",
    },
    "search_web": {
        "start": "Checking recent news and market events",
        "end": "Finished checking recent news and market events",
    },
    "search_rdb": {
        "start": "Retrieving structured market data",
        "end": "Finished retrieving structured market data",
    },
    "search_vdb": {
        "start": "Looking through related reports and documents",
        "end": "Finished looking through related reports and documents",
    },
}
