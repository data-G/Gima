from __future__ import annotations

import csv
import json
import math
import re
import shutil
import subprocess
import textwrap
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .services import WebImporter


@dataclass
class ArtifactAnswer:
    reply: str
    files: list[dict[str, Any]]
    sources: list[str]
    used_internet: bool = False


FASTEST_CARS_ROWS = [
    {
        "rank": 1,
        "car": "Koenigsegg Jesko Absolut",
        "claimed_or_recorded_top_speed_mph": "330 claimed",
        "top_speed_kmh": "531 claimed",
        "status": "manufacturer claim, not independently production-record verified",
        "note": "Often cited as one of the fastest claimed production-capable cars.",
    },
    {
        "rank": 2,
        "car": "Bugatti Chiron Super Sport 300+",
        "claimed_or_recorded_top_speed_mph": "304.773 recorded",
        "top_speed_kmh": "490.484 recorded",
        "status": "prototype/pre-production speed run",
        "note": "First road-car-related run reported above 300 mph.",
    },
    {
        "rank": 3,
        "car": "SSC Tuatara",
        "claimed_or_recorded_top_speed_mph": "295 recorded",
        "top_speed_kmh": "475 recorded",
        "status": "two-way production-car record claim",
        "note": "Later verified attempts are lower than the disputed 2020 claim.",
    },
    {
        "rank": 4,
        "car": "Hennessey Venom F5",
        "claimed_or_recorded_top_speed_mph": "300+ claimed",
        "top_speed_kmh": "483+ claimed",
        "status": "manufacturer target/claim",
        "note": "Built around a 300 mph goal; independent final record varies by source/date.",
    },
    {
        "rank": 5,
        "car": "Koenigsegg Agera RS",
        "claimed_or_recorded_top_speed_mph": "277.87 recorded",
        "top_speed_kmh": "447.19 recorded",
        "status": "verified production-car record run",
        "note": "Widely accepted GPS-measured two-way average from Nevada.",
    },
]

FASTEST_CARS_SOURCES = [
    "https://en.wikipedia.org/wiki/Production_car_speed_record",
    "https://www.koenigsegg.com/model/jesko-absolut",
    "https://www.bugatti.com/the-bugatti-models/chiron-facets-of-performance/super-sport-300/",
]

CATERING_BUDGET_SOURCES = [
    "https://www.cbsl.gov.lk/sites/default/files/cbslweb_documents/statistics/pricerpt/price_report_20260618_e.pdf",
    "https://www.statistics.gov.lk/Resource/en/InflationAndPrices/retail/DCSB-WRP-2026-05-W4.pdf",
    "https://onlinekade.lk/product/prima-sunrise-top-sandwich-bread-350g/",
    "https://www.paperbags.lk/product-page/ziplock-kraft-100g-20x12cm",
]


class ChatArtifactEngine:
    def __init__(self, output_root: Path, allowed_domains: list[str] | tuple[str, ...]):
        self.output_root = output_root
        self.importer = WebImporter(allowed_domains)

    def answer(self, message: str) -> ArtifactAnswer | None:
        normalized = " ".join(message.casefold().split())
        wants_file = any(word in normalized for word in {"file", "download", "csv", "pdf", "table", "report"})
        if _is_seeni_sambol_budget_request(normalized):
            return self._seeni_sambol_budget(message)
        if _is_generic_catering_budget_request(normalized):
            return self._catering_budget(message, normalized)
        if "fastest car" in normalized or "fastest cars" in normalized:
            return self._fastest_cars(message)
        if _is_sports_schedule_request(normalized):
            sport = _mentioned_sport(normalized)
            if not sport:
                return ArtifactAnswer(
                    reply=(
                        "I can build the real Japan match schedule in Japan Standard Time, but I need the sport or "
                        "competition first. For example: `Japan men's football World Cup matches`, `Japan baseball "
                        "matches`, or `Japan rugby fixtures`. I did not create placeholder files because that would "
                        "invent the dataset."
                    ),
                    files=[],
                    sources=[],
                )
            query = (
                f"Japan {sport} national team official upcoming fixtures schedule opponents dates times "
                "Japan Standard Time JST UTC+9"
            )
            return self._web_answer(query, wants_file=True)
        if _is_weather_request(normalized):
            location = _extract_weather_location(message)
            return self._weather_answer(location or "Osaka")
        direct_url = _extract_public_url(message)
        if direct_url and _is_web_research_request(normalized):
            return self._url_answer(direct_url)
        if _is_web_research_request(normalized):
            query = _clean_web_query(message)
            return self._web_answer(query or message, wants_file=wants_file)
        if wants_file and _requires_current_research(normalized):
            return self._web_answer(_clean_web_query(message) or message, wants_file=True)
        if wants_file and any(word in normalized for word in {"table", "report", "pdf", "csv"}):
            return self._generic_report(message)
        return None

    def _catering_budget(self, message: str, normalized: str) -> ArtifactAnswer:
        quantity = _largest_request_count(message) or 100
        if "chicken" not in normalized:
            return ArtifactAnswer(
                reply=(
                    "I recognized a catering-cost request, but I do not yet have a verified recipe template for that "
                    "sandwich type. Chicken and seeni sambol templates are currently supported."
                ),
                files=[],
                sources=[],
            )
        project = self._project_dir(f"chicken_sandwich_{quantity}")
        model = _chicken_sandwich_model(quantity)
        model_path = project / "costing_model.json"
        model_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
        try:
            files = _build_catering_files(model_path, model["stem"])
        except Exception as error:
            return ArtifactAnswer(
                reply=f"I calculated the chicken-sandwich budget, but file generation failed: {error}",
                files=[],
                sources=[source["url"] for source in model["sources"] if source["url"].startswith("http")],
            )
        total = sum(item["procure_qty"] * item["unit_price"] for item in model["items"])
        total *= 1 + model["contingency"]
        reply = (
            f"Created a researched planning budget for **{quantity:,} individually packed chicken sandwiches**.\n\n"
            f"- Estimated total: **Rs {total:,.0f}**\n"
            f"- Estimated cost per sandwich: **Rs {total / quantity:,.2f}**\n"
            f"- Contingency: {model['contingency']:.1%}\n\n"
            "The workbook separates researched prices from supplier-quote estimates. Confirm chicken preparation yield, "
            "bread slice count, mayonnaise usage, cold-chain handling and bulk quotations before ordering.\n\n"
            "Files ready:\n" + "\n".join(f"- {path.name}: {path}" for path in files)
        )
        return ArtifactAnswer(
            reply=reply,
            files=[_file_info(path) for path in files],
            sources=[source["url"] for source in model["sources"] if source["url"].startswith("http")],
        )

    def _seeni_sambol_budget(self, message: str) -> ArtifactAnswer:
        project = self.output_root / "catering_budget" / "seeni_sambol_budget_7000"
        paths = [
            project / "seeni_sambol_sandwich_budget_7000.xlsx",
            project / "seeni_sambol_sandwich_budget_7000.jpg",
            project / "seeni_sambol_sandwich_budget_7000.pdf",
        ]
        available = [path for path in paths if path.exists()]
        requested = _largest_request_count(message)
        quantity_note = ""
        if requested and requested != 7000:
            quantity_note = (
                f"\n\nI recognized {requested:,} sandwiches. The verified workbook opens with 7,000; "
                "change the blue `Sandwiches required` cell on the Assumptions sheet and every formula will update."
            )
        if len(available) != len(paths):
            return ArtifactAnswer(
                reply=(
                    "I recognized this as a seeni sambol sandwich catering budget, but the verified download bundle "
                    "is not installed in Gima hands/out yet."
                ),
                files=[],
                sources=CATERING_BUDGET_SOURCES,
            )
        reply = (
            "I treated your request as **7,000 individually packed seeni sambol sandwiches**.\n\n"
            "| Scenario | Total budget | Cost per sandwich |\n"
            "| --- | ---: | ---: |\n"
            "| Economy | Rs 650,271 | Rs 92.90 |\n"
            "| Base | **Rs 721,382** | **Rs 103.05** |\n"
            "| Premium | Rs 1,059,910 | Rs 151.42 |\n\n"
            "The base case includes 735 bread loaves, recipe quantities, 5% production waste, 3% spare packaging, "
            "labour, transport, utilities, sanitation and 7.5% contingency. Blue cells in Excel are editable. "
            "Confirm loaf slice yield and obtain bulk bread, onion and packaging quotations before ordering."
            f"{quantity_note}\n\n"
            "Files ready:\n"
            + "\n".join(f"- {path.name}: {path}" for path in paths)
        )
        return ArtifactAnswer(
            reply=reply,
            files=[_file_info(path) for path in paths],
            sources=CATERING_BUDGET_SOURCES,
        )

    def _fastest_cars(self, message: str) -> ArtifactAnswer:
        project = self._project_dir("fastest_cars")
        csv_path = project / "fastest_cars.csv"
        md_path = project / "fastest_cars_report.md"
        pdf_path = project / "fastest_cars_report.pdf"
        json_path = project / "manifest.json"
        _write_csv(csv_path, FASTEST_CARS_ROWS)
        markdown = _markdown_table(FASTEST_CARS_ROWS)
        caveat = (
            "Fastest-car rankings depend on whether you count verified production records, prototypes, "
            "or manufacturer claims. I separated status so the answer is honest."
        )
        md_text = (
            "# Fastest Cars Table\n\n"
            f"{caveat}\n\n"
            f"{markdown}\n\n"
            "## Sources To Review\n"
            + "\n".join(f"- {source}" for source in FASTEST_CARS_SOURCES)
            + "\n"
        )
        md_path.write_text(md_text, encoding="utf-8")
        _write_simple_pdf(
            pdf_path,
            "Fastest Cars Table",
            [caveat, "", *[f"{row['rank']}. {row['car']} - {row['claimed_or_recorded_top_speed_mph']} mph - {row['status']}" for row in FASTEST_CARS_ROWS]],
        )
        _write_manifest(json_path, "fastest_cars_table", message, [csv_path, md_path, pdf_path], FASTEST_CARS_SOURCES)
        reply = (
            f"{caveat}\n\n{markdown}\n\n"
            "Files generated:\n"
            f"- CSV: {csv_path}\n"
            f"- PDF: {pdf_path}\n"
            f"- Report: {md_path}\n\n"
            "Sources to review:\n"
            + "\n".join(f"- {source}" for source in FASTEST_CARS_SOURCES)
        )
        return ArtifactAnswer(
            reply=reply,
            files=[_file_info(csv_path), _file_info(pdf_path), _file_info(md_path), _file_info(json_path)],
            sources=FASTEST_CARS_SOURCES,
        )

    def _web_answer(self, query: str, wants_file: bool = False) -> ArtifactAnswer:
        project = self._project_dir("internet_answer")
        sources = self.importer.search(query, limit=4)
        rows: list[dict[str, str]] = []
        notes: list[str] = []
        for url in sources[:4]:
            try:
                text = self.importer.fetch(url)
            except Exception as error:
                rows.append({"source": url, "status": "error", "summary": str(error)})
                continue
            summary = _summarize_text(text, query)
            rows.append({"source": url, "status": "fetched", "summary": summary})
            notes.append(f"Source: {url}\n{summary}")
        if not rows:
            return ArtifactAnswer(
                reply="I tried to search the internet, but no public sources could be fetched. Try a more specific query.",
                files=[],
                sources=[],
                used_internet=True,
            )
        csv_path = project / "internet_sources.csv"
        md_path = project / "internet_answer.md"
        _write_csv(csv_path, rows)
        md_text = "# Internet Answer Notes\n\n" + "\n\n".join(notes or [json.dumps(rows, indent=2)])
        md_path.write_text(md_text, encoding="utf-8")
        files = [_file_info(csv_path), _file_info(md_path)]
        if wants_file or "pdf" in query.casefold():
            pdf_path = project / "internet_answer.pdf"
            _write_simple_pdf(pdf_path, "Internet Answer Notes", md_text.splitlines())
            files.append(_file_info(pdf_path))
        reply = (
            f"I searched public web sources for: {query}\n\n"
            + "\n\n".join(notes[:4])
            + "\n\nGenerated files:\n"
            + "\n".join(f"- {file['path']}" for file in files)
        )
        return ArtifactAnswer(reply=reply, files=files, sources=sources, used_internet=True)

    def _weather_answer(self, location: str) -> ArtifactAnswer:
        project = self._project_dir("weather")
        try:
            geo_source = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode(
                {"name": location, "count": 1, "language": "en", "format": "json"}
            )
            with urllib.request.urlopen(
                urllib.request.Request(geo_source, headers={"User-Agent": "Gima local weather/0.1"}),
                timeout=10,
            ) as response:
                geo_body = json.loads(response.read().decode("utf-8"))
            place = (geo_body.get("results") or [])[0]
            source = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
                {
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                    "timezone": "auto",
                }
            )
            with urllib.request.urlopen(
                urllib.request.Request(source, headers={"User-Agent": "Gima local weather/0.1"}),
                timeout=10,
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            query = f"current weather {location}"
            fallback = self._web_answer(query, wants_file=False)
            if fallback.sources:
                return fallback
            return ArtifactAnswer(
                reply=f"I tried to fetch current weather for {location}, but the weather source did not answer: {error}",
                files=[],
                sources=[],
                used_internet=True,
            )
        current = body.get("current") or {}
        area = place.get("name", location)
        country = place.get("country", "")
        desc = _weather_code_description(current.get("weather_code"))
        temp_c = str(current.get("temperature_2m", ""))
        feels_c = str(current.get("apparent_temperature", ""))
        humidity = str(current.get("relative_humidity_2m", ""))
        wind_kmph = str(current.get("wind_speed_10m", ""))
        precipitation = str(current.get("precipitation", ""))
        observation = str(current.get("time", ""))
        rows = [
            {
                "location": f"{area}, {country}".strip(", "),
                "observed_local_time": observation,
                "condition": desc,
                "temperature_c": temp_c,
                "feels_like_c": feels_c,
                "humidity_percent": humidity,
                "wind_kmph": wind_kmph,
                "precipitation_mm": precipitation,
                "source": source,
            }
        ]
        csv_path = project / "current_weather.csv"
        md_path = project / "current_weather.md"
        _write_csv(csv_path, rows)
        line = (
            f"Current weather for **{area}{', ' + country if country else ''}**"
            f"{f' at {observation}' if observation else ''}: **{desc}**, "
            f"**{temp_c}°C**"
            f"{f' feels like {feels_c}°C' if feels_c else ''}, "
            f"humidity {humidity}%, wind {wind_kmph} km/h, precipitation {precipitation} mm."
        )
        md_text = f"# Current Weather\n\n{line}\n\nSource: {source}\n"
        md_path.write_text(md_text, encoding="utf-8")
        files = [_file_info(csv_path), _file_info(md_path)]
        reply = (
            f"{line}\n\n"
            "Files generated:\n"
            + "\n".join(f"- {file['path']}" for file in files)
            + "\n\nSource:\n"
            f"- {source}"
        )
        return ArtifactAnswer(reply=reply, files=files, sources=[source], used_internet=True)

    def _url_answer(self, url: str) -> ArtifactAnswer:
        project = self._project_dir("web_page")
        try:
            text = self.importer.fetch(url)
        except Exception as error:
            return ArtifactAnswer(
                reply=f"I tried to browse {url}, but it could not be fetched: {error}",
                files=[],
                sources=[url],
                used_internet=True,
            )
        summary = _summarize_text(text, url, max_sentences=6)
        csv_path = project / "web_page_source.csv"
        md_path = project / "web_page_summary.md"
        rows = [{"source": url, "status": "fetched", "summary": summary}]
        _write_csv(csv_path, rows)
        md_text = f"# Web Page Summary\n\nSource: {url}\n\n{summary}\n"
        md_path.write_text(md_text, encoding="utf-8")
        files = [_file_info(csv_path), _file_info(md_path)]
        reply = (
            f"I browsed this public page:\n{url}\n\n"
            f"{summary}\n\n"
            "Generated files:\n"
            + "\n".join(f"- {file['path']}" for file in files)
        )
        return ArtifactAnswer(reply=reply, files=files, sources=[url], used_internet=True)

    def _generic_report(self, message: str) -> ArtifactAnswer:
        return ArtifactAnswer(
            reply=(
                "I can create a useful table or report, but this request does not identify a trustworthy dataset yet. "
                "Tell me the subject, date range, desired columns, and data source, or say `search the internet`. "
                "I did not create placeholder files because a table containing only your prompt is not a real answer."
            ),
            files=[],
            sources=[],
        )

    def _project_dir(self, stem: str) -> Path:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = self.output_root / "chat_artifacts" / f"{stamp}_{stem}_{uuid.uuid4().hex[:6]}"
        path.mkdir(parents=True, exist_ok=True)
        return path


def _clean_web_query(message: str) -> str:
    cleaned = re.sub(
        r"\b(search|look up|lookup|browse|use|from|learn from|find|check|verify|the|internet|web|online|please|gima|for me|and make|make|create|generate)\b",
        " ",
        message,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :.-")
    return cleaned


def _extract_public_url(message: str) -> str:
    match = re.search(r"https?://[^\s<>()]+", message)
    if not match:
        return ""
    return match.group(0).rstrip(".,;")


def _is_weather_request(normalized: str) -> bool:
    return "weather" in normalized and any(term in normalized for term in {"current", "today", "now", "forecast", "temperature"})


def _extract_weather_location(message: str) -> str:
    patterns = [
        r"\bweather\s+(?:in|for|at)\s+(.+)$",
        r"\b(?:in|for|at)\s+(.+?)\s+weather\b",
    ]
    cleaned = re.sub(r"\b(search|browse|look up|check|find|current|today|now|please|gima|the|web|internet|online)\b", " ", message, flags=re.IGNORECASE)
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            cleaned = match.group(1)
            break
    cleaned = re.sub(r"[?.!,;]+$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .:-")
    return cleaned


def _weather_code_description(code: Any) -> str:
    try:
        value = int(code)
    except (TypeError, ValueError):
        return "weather data"
    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
    }
    return descriptions.get(value, f"Weather code {value}")


def _is_web_research_request(normalized: str) -> bool:
    explicit_phrases = {
        "search internet",
        "search the internet",
        "search web",
        "search the web",
        "from internet",
        "from the internet",
        "use internet",
        "use the internet",
        "browse",
        "browse internet",
        "browse the internet",
        "look up",
        "lookup",
        "find online",
        "check online",
        "verify online",
    }
    if any(phrase in normalized for phrase in explicit_phrases):
        return True
    return _requires_current_research(normalized) and any(
        term in normalized
        for term in {
            "what is",
            "who is",
            "when is",
            "where is",
            "which",
            "list",
            "table",
            "compare",
            "price",
            "news",
            "latest",
            "current",
            "today",
            "this week",
            "this month",
            "2026",
        }
    )


def _is_sports_schedule_request(normalized: str) -> bool:
    team_terms = ("japan", "national team", "country", "countries", "vs", "versus")
    schedule_terms = ("match", "matches", "fixture", "fixtures", "schedule", "game", "games", "kickoff")
    return any(term in normalized for term in team_terms) and any(term in normalized for term in schedule_terms)


def _mentioned_sport(normalized: str) -> str:
    aliases = {
        "soccer": "football",
        "football": "football",
        "baseball": "baseball",
        "rugby": "rugby",
        "basketball": "basketball",
        "volleyball": "volleyball",
        "cricket": "cricket",
        "hockey": "hockey",
        "tennis": "tennis",
        "futsal": "futsal",
    }
    for term, canonical in aliases.items():
        if re.search(rf"\b{re.escape(term)}\b", normalized):
            return canonical
    return ""


def _requires_current_research(normalized: str) -> bool:
    current_terms = (
        "current",
        "latest",
        "today",
        "upcoming",
        "schedule",
        "fixture",
        "match",
        "ranking",
        "price",
        "weather",
        "news",
        "2026",
    )
    return any(term in normalized for term in current_terms)


def _is_seeni_sambol_budget_request(normalized: str) -> bool:
    food_terms = ("seeni", "sini", "sambol", "sambal", "symbol")
    sandwich_terms = ("sandwich", "sandwitched", "sandwitch", "sandwitches")
    budget_terms = ("budget", "cost", "price", "quotation", "quote", "how much")
    return (
        any(term in normalized for term in food_terms)
        and any(term in normalized for term in sandwich_terms)
        and any(term in normalized for term in budget_terms)
    )


def _is_generic_catering_budget_request(normalized: str) -> bool:
    sandwich = any(term in normalized for term in ("sandwich", "sandwitched", "sandwitch"))
    costing = any(term in normalized for term in ("budget", "cost", "costing", "quotation", "estimate"))
    artifact = any(term in normalized for term in ("excel", "xlsx", "jpg", "jpeg", "pdf", "table", "download"))
    return sandwich and costing and artifact


def _chicken_sandwich_model(quantity: int) -> dict[str, Any]:
    waste = 0.05
    packaging_spare = 0.03
    staff = max(6, math.ceil(quantity / 200) + 2)
    sources = [
        {"id": "S1", "item": "Sandwich bread 350g", "price": 230, "unit": "Rs/loaf", "url": "https://onlinekade.lk/product/prima-sunrise-top-sandwich-bread-350g/", "caveat": "Retail proxy; verify usable slices and request a bakery quote"},
        {"id": "S2", "item": "Fresh chicken", "price": 1387.06, "unit": "Rs/kg", "url": "https://www.statistics.gov.lk/Resource/en/InflationAndPrices/retail/DCSB-WRP-2026-05-W4.pdf", "caveat": "Official Colombo weekly average, 4th week May 2026"},
        {"id": "S3", "item": "Mayonnaise 1L", "price": 1290, "unit": "Rs/kg", "url": "https://supersavings.lk/shop-products/mamas-mayonnaise-1l/", "caveat": "Retail quote; obtain catering-pack quotation"},
        {"id": "S4", "item": "Imported big onion", "price": 165, "unit": "Rs/kg", "url": "https://www.cbsl.gov.lk/sites/default/files/cbslweb_documents/statistics/pricerpt/price_report_20260618_e.pdf", "caveat": "Dambulla wholesale proxy, 18 June 2026"},
        {"id": "S5", "item": "Meadowlea fat spread 1kg", "price": 1700, "unit": "Rs/kg", "url": "https://spar2u.lk/products/meadowlea-fat-spread-1kg", "caveat": "Retail quote"},
        {"id": "S6", "item": "Kraft food bag", "price": 12, "unit": "Rs/unit", "url": "https://www.paperbags.lk/product-page/ziplock-kraft-100g-20x12cm", "caveat": "Confirm food-contact suitability and fit"},
        {"id": "E1", "item": "Lettuce", "price": 600, "unit": "Rs/kg", "url": "Supplier quote required", "caveat": "Planning estimate"},
        {"id": "E2", "item": "Pepper", "price": 4000, "unit": "Rs/kg", "url": "Supplier quote required", "caveat": "Planning estimate"},
        {"id": "E3", "item": "Salt", "price": 161.6, "unit": "Rs/kg", "url": "https://www.statistics.gov.lk/Resource/en/InflationAndPrices/retail/DCSB-WRP-2026-05-W4.pdf", "caveat": "Official weekly retail average"},
        {"id": "E4", "item": "Napkin and label", "price": 3, "unit": "Rs/pack", "url": "Supplier quote required", "caveat": "Planning estimate"},
    ]
    source_map = {source["id"]: source for source in sources}
    specs = [
        ("Bread", "Sandwich bread", quantity * 2 / 20, waste, "loaf", 230, "S1"),
        ("Filling", "Fresh chicken", quantity * 0.060, waste, "kg", 1387.06, "S2"),
        ("Filling", "Mayonnaise", quantity * 0.015, waste, "kg", 1290, "S3"),
        ("Filling", "Lettuce", quantity * 0.015, waste, "kg", 600, "E1"),
        ("Filling", "Imported big onion", quantity * 0.005, waste, "kg", 165, "S4"),
        ("Filling", "Fat spread", quantity * 0.004, waste, "kg", 1700, "S5"),
        ("Seasoning", "Pepper", quantity * 0.0005, waste, "kg", 4000, "E2"),
        ("Seasoning", "Salt", quantity * 0.0005, waste, "kg", 161.6, "E3"),
        ("Packaging", "Kraft food bag", quantity, packaging_spare, "unit", 12, "S6"),
        ("Packaging", "Napkin and label", quantity, packaging_spare, "pack", 3, "E4"),
        ("Labour", "Production crew", staff * 8, 0, "hour", 500, "Estimate"),
        ("Operations", "Gas / electricity", 1, 0, "fixed", max(10000, quantity * 5), "Estimate"),
        ("Operations", "Cold-chain transport", 1, 0, "fixed", max(20000, quantity * 10), "Estimate"),
        ("Operations", "Sanitation / PPE", 1, 0, "fixed", max(8000, quantity * 4), "Estimate"),
    ]
    items = []
    for category, item, base_qty, allowance, unit, price, source_id in specs:
        procure_qty = math.ceil(base_qty * (1 + allowance)) if unit != "fixed" else 1
        source = source_map.get(source_id)
        items.append(
            {
                "category": category,
                "item": item,
                "base_qty": round(base_qty, 3),
                "waste": allowance,
                "procure_qty": procure_qty,
                "unit": unit,
                "unit_price": price,
                "source": source_id,
                "status": source["caveat"] if source else "Planning estimate",
            }
        )
    return {
        "name": "Chicken Sandwich Costing",
        "stem": f"chicken_sandwich_budget_{quantity}",
        "quantity": quantity,
        "as_of": "19 June 2026",
        "contingency": 0.075,
        "items": items,
        "sources": sources,
        "assumptions": [
            {"name": "Sandwiches required", "value": quantity, "unit": "sandwiches", "note": "Parsed from the request"},
            {"name": "Slices per sandwich", "value": 2, "unit": "slices", "note": "Closed sandwich"},
            {"name": "Usable slices per loaf", "value": 20, "unit": "slices", "note": "Count a sample loaf before ordering"},
            {"name": "Raw chicken per sandwich", "value": 60, "unit": "g", "note": "Confirm cooked yield and portion size"},
            {"name": "Mayonnaise per sandwich", "value": 15, "unit": "g", "note": "Adjust after a test batch"},
            {"name": "Food and bread waste", "value": 5, "unit": "%", "note": "Production allowance"},
            {"name": "Packaging spare", "value": 3, "unit": "%", "note": "Damage allowance"},
            {"name": "Production staff", "value": staff, "unit": "people", "note": "Eight-hour shift at Rs 500/hour"},
        ],
        "warnings": [
            "Chicken requires validated cooking, rapid cooling and cold-chain controls.",
            "Confirm cooked chicken yield and portion size with a test batch.",
            "Count usable slices in the selected bread loaf before ordering.",
            "Replace lettuce, pepper, labour and logistics estimates with supplier quotes.",
            "Declare egg/gluten allergens from mayonnaise and bread.",
        ],
    }


def _build_catering_files(model_path: Path, stem: str) -> list[Path]:
    workspace = Path(__file__).resolve().parent.parent
    script = workspace / "scripts" / "build_catering_workbook.mjs"
    bundled_node = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin" / "node"
    node = str(bundled_node if bundled_node.exists() else shutil.which("node") or "")
    if not node:
        raise RuntimeError("Node.js runtime is unavailable")
    result = subprocess.run(
        [node, str(script), str(model_path)],
        cwd=str(script.parent),
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown workbook error"
        raise RuntimeError(detail[-800:])
    paths = [model_path.parent / f"{stem}.{suffix}" for suffix in ("xlsx", "jpg", "pdf")]
    if not all(path.exists() and path.stat().st_size > 0 for path in paths):
        raise RuntimeError("the artifact builder did not create every requested format")
    return paths


def _largest_request_count(message: str) -> int | None:
    values = []
    for raw in re.findall(r"(?<![\w.])\d[\d,]*(?![\w.])", message):
        try:
            values.append(int(raw.replace(",", "")))
        except ValueError:
            continue
    return max(values) if values else None


def _summarize_text(text: str, query: str, max_sentences: int = 4) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "No readable text extracted."
    terms = [term for term in re.findall(r"[a-zA-Z0-9]{4,}", query.casefold()) if term not in {"internet", "search"}]
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    scored: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(sentences[:180]):
        lowered = sentence.casefold()
        score = sum(1 for term in terms if term in lowered)
        if 60 <= len(sentence) <= 320:
            scored.append((score, -index, sentence))
    best = [item[2] for item in sorted(scored, reverse=True)[:max_sentences]]
    if not best:
        best = textwrap.wrap(cleaned, 260)[:max_sentences]
    return " ".join(best)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    fields = list(rows[0].keys())
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        values = [str(row.get(field, "")).replace("|", "\\|").replace("\n", " ") for field in fields]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _write_manifest(path: Path, kind: str, prompt: str, files: list[Path], sources: list[str]) -> None:
    path.write_text(
        json.dumps(
            {
                "kind": kind,
                "prompt": prompt,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "files": [str(file) for file in files],
                "sources": sources,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _file_info(path: Path) -> dict[str, Any]:
    return {
        "name": path.name,
        "path": str(path),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }


def _write_simple_pdf(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content_lines = [title, "", *lines]
    stream_parts = ["BT", "/F1 12 Tf", "50 792 Td", "14 TL"]
    first = True
    for raw_line in content_lines:
        for wrapped in textwrap.wrap(str(raw_line), width=88) or [""]:
            escaped = wrapped.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if first:
                stream_parts.append(f"({escaped}) Tj")
                first = False
            else:
                stream_parts.append(f"T* ({escaped}) Tj")
    stream_parts.append("ET")
    stream = "\n".join(stream_parts).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_at = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(bytes(output))
