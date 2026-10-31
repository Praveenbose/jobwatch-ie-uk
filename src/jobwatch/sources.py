"""Job sources. Each source = fetch (network) + parse (pure function, easy to test).

Only public, documented JSON endpoints are used. Do NOT scrape LinkedIn: its terms forbid it.
"""
import json
import time
import urllib.request
from typing import Any, Dict, List

from .models import Job

USER_AGENT = "jobwatch/0.1 (personal job alert project; contact: praveenchandrabose2001@gmail.com)"


def fetch_json(url: str, timeout: int = 20, retries: int = 2) -> Any:
    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # network errors, bad JSON, HTTP errors
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch {url}: {last_error}")


def parse_greenhouse(data: Dict[str, Any], company: str) -> List[Job]:
    return [
        Job("greenhouse", str(j["id"]), company, j.get("title", ""),
            (j.get("location") or {}).get("name", ""), j.get("absolute_url", ""),
            j.get("content", "") or "")
        for j in data.get("jobs", [])
    ]


def parse_lever(data: List[Dict[str, Any]], company: str) -> List[Job]:
    return [
        Job("lever", str(j["id"]), company, j.get("text", ""),
            (j.get("categories") or {}).get("location", "") or "", j.get("hostedUrl", ""),
            j.get("descriptionPlain", "") or "")
        for j in data
    ]


def _dig(obj: Any, path: str) -> Any:
    for part in path.split("."):
        if obj is None:
            return None
        obj = obj[int(part)] if isinstance(obj, list) else obj.get(part)
    return obj


def parse_generic(data: Any, cfg: Dict[str, Any]) -> List[Job]:
    """For any company API you discover in your browser's Network tab.

    cfg: {"company": "...", "list_path": "data.jobs", "fields": {"id": "jobId", "title": "title",
          "location": "location", "url": "applyUrl", "description": "summary"}}
    """
    items = _dig(data, cfg["list_path"]) if cfg.get("list_path") else data
    f = cfg["fields"]
    return [
        Job("generic", str(_dig(i, f["id"])), cfg["company"], str(_dig(i, f["title"]) or ""),
            str(_dig(i, f["location"]) or "") if f.get("location") else "",
            str(_dig(i, f["url"]) or ""),
            str(_dig(i, f["description"]) or "") if f.get("description") else "")
        for i in items or []
    ]


def fetch_source(cfg: Dict[str, Any]) -> List[Job]:
    kind = cfg["type"]
    if kind == "greenhouse":
        url = f"https://boards-api.greenhouse.io/v1/boards/{cfg['token']}/jobs?content=true"
        return parse_greenhouse(fetch_json(url), cfg["company"])
    if kind == "lever":
        url = f"https://api.lever.co/v0/postings/{cfg['slug']}?mode=json"
        return parse_lever(fetch_json(url), cfg["company"])
    if kind == "generic":
        return parse_generic(fetch_json(cfg["url"]), cfg)
    raise ValueError(f"Unknown source type: {kind}")
