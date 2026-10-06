#!/usr/bin/env python3
"""Fetch public schema.org Event records from public Terceira/Azores calendars."""
import json, re, os
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

SOURCES = [
    ("https://eventosterceira.pt/pt/", "Eventos Terceira"),
    ("https://eventosterceira.pt/pt/special/", "Eventos Terceira"),
    ("https://angradoheroismo.pt/eventos/", "Agenda de Angra"),
    ("https://whatson.azores.gov.pt/agenda/", "Azores What's On"),
    ("https://culturacores.azores.gov.pt/agenda/", "CulturAçores"),
    ("https://byacores.com/terceira/", "byAçores"),
]
HEADERS = {"User-Agent": "BoutiqueHotelTeatroEventsBot/1.0 (public events calendar)"}
TODAY = datetime.now(timezone.utc).date()
TERCEIRA_TERMS = ("terceira", "angra do heroísmo", "angra do heroismo", "praia da vitória", "praia da vitoria", "são mateus", "porto judeu", "biscoitos")

def txt(value):
    if isinstance(value, dict): return str(value.get("name") or value.get("addressLocality") or "")
    if isinstance(value, list): return ", ".join(filter(None, (txt(x) for x in value)))
    return str(value or "")

def walk_events(obj):
    if isinstance(obj, dict):
        types = obj.get("@type", [])
        types = types if isinstance(types, list) else [types]
        if any(str(t).lower().endswith("event") for t in types): yield obj
        for value in obj.values(): yield from walk_events(value)
    elif isinstance(obj, list):
        for value in obj: yield from walk_events(value)

def parse_page(url, label, session):
    response = session.get(url, timeout=25, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    events = []
    for tag in soup.select('script[type="application/ld+json"]'):
        try: data = json.loads(tag.string or tag.get_text())
        except Exception: continue
        for event in walk_events(data):
            name = txt(event.get("name")).strip()
            if not name: continue
            location = event.get("location", {})
            venue = txt(location.get("name")) if isinstance(location, dict) else txt(location)
            address = location.get("address", {}) if isinstance(location, dict) else {}
            if isinstance(address, dict):
                area = ", ".join(filter(None, [txt(address.get("addressLocality")), txt(address.get("addressRegion"))]))
            else: area = txt(address)
            haystack = " ".join([name, venue, area, txt(event.get("description"))]).lower()
            if not any(term in haystack for term in TERCEIRA_TERMS): continue
            start, end = str(event.get("startDate") or ""), str(event.get("endDate") or "")
            try:
                end_day = datetime.fromisoformat((end or start).replace("Z", "+00:00")).date()
                if end_day < TODAY: continue
            except Exception: pass
            link = event.get("url") or url
            if isinstance(link, dict): link = link.get("@id") or link.get("url") or url
            image = event.get("image")
            if isinstance(image, list): image = image[0] if image else ""
            if isinstance(image, dict): image = image.get("url") or image.get("@id") or ""
            events.append({
                "id": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:80],
                "name": name, "category": "Events", "period": "dated" if start else "recurring",
                "date": start[:10] if start else "Date to be confirmed", "area": area or "Terceira Island",
                "venue": venue or area or "Terceira Island",
                "description": BeautifulSoup(txt(event.get("description")), "html.parser").get_text(" ", strip=True)[:900],
                "source": urljoin(url, str(link)), "sourceLabel": label,
                "map": venue or area or "Terceira Island, Azores", "image": str(image or "")
            })
    return events, soup

def main():
    session = requests.Session(); events = []; checked = []; detail_urls = []
    for url, label in SOURCES:
        try:
            items, soup = parse_page(url, label, session); events.extend(items)
            checked.append({"url": url, "ok": True, "structuredEvents": len(items)})
            host = urlparse(url).netloc
            for a in soup.select("a[href]"):
                href = urljoin(url, a.get("href", "")); title = (a.get_text(" ", strip=True) + " " + href).lower()
                if urlparse(href).netloc == host and any(x in title for x in ("evento", "event", "agenda", "festival", "concerto", "exposi")):
                    if href not in [u for u, _ in detail_urls] and href != url and not href.endswith((".jpg", ".png", ".pdf")):
                        detail_urls.append((href, label))
        except Exception as exc:
            checked.append({"url": url, "ok": False, "structuredEvents": 0, "error": str(exc)[:180]})
    for url, label in detail_urls[:24]:
        try:
            items, _ = parse_page(url, label, session); events.extend(items)
        except Exception: pass
    unique = {}
    for event in events: unique[(event["name"].casefold(), event["date"], event["source"])] = event
    result = {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "timezone": "UTC", "scope": "Terceira, Azores", "sourcesChecked": checked, "events": sorted(unique.values(), key=lambda e: (e.get("date", ""), e.get("name", "")))}
    os.makedirs("data", exist_ok=True)
    with open("data/events-feed.json", "w", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Checked {len(checked)} sources; imported {len(result['events'])} structured events.")
    if not any(s["ok"] for s in checked): raise SystemExit("All event sources failed; see workflow logs.")

if __name__ == "__main__": main()
