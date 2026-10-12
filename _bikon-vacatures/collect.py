"""Fase 1: Belgische vacatures verzamelen via JobSpy en de Adzuna API.

Gebruik:
    python collect.py                                   # alle bronnen en zoektermen
    python collect.py --sources indeed adzuna --terms RAG chatbot   # kleine proefrun
    python collect.py --only-process                    # niets ophalen, data/raw/ opnieuw verwerken

Wat al in data/raw/ staat wordt niet opnieuw opgehaald (gebruik --refresh om dat wel te doen),
zodat een onderbroken run verder kan zonder de sites opnieuw te belasten.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import random
import re
import statistics
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv

import common

SOURCES = ["indeed", "linkedin", "glassdoor", "adzuna", "google"]
DEFAULT_SOURCES = ["indeed", "linkedin", "glassdoor", "adzuna"]
JOBSPY_SOURCES = {"indeed", "linkedin", "glassdoor", "google"}
JOBSPY_LOGGERS = {"indeed": "Indeed", "linkedin": "LinkedIn", "glassdoor": "Glassdoor", "google": "Google"}
LOCATION = "Belgium"
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/be/search/1"

DELAY_SECONDS = (3.0, 6.0)  # willekeurige pauze voor elk request naar dezelfde bron
BLOCK_STATUSES = {401, 403, 429, 999}  # 999 is LinkedIn's antwoord aan bots
MAX_CONNECTION_ERRORS = 3
MAX_AUTHWALL_REDIRECTS = 3

# Kolommen die nooit opgeslagen worden: e-mailadressen en logo's.
DROP_COLUMNS = {"emails", "company_logo"}
TEXT_COLUMNS = ("description", "company_description")


def log(source: str, message: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] [{source}] {message}", flush=True)


class SourceStopped(Exception):
    """De bron blokkeert, rate-limit of is onbereikbaar: er gaat niets meer naartoe."""


class Politeness:
    """Pauze tussen requests per bron, en stoppen bij blokkering. Eén thread per bron."""

    def __init__(self) -> None:
        self.last_request: dict[str, float] = {}
        self.stopped: dict[str, str] = {}
        self.requests: Counter = Counter()
        self.connection_errors: Counter = Counter()
        self.authwall: Counter = Counter()
        self.errors: Counter = Counter()
        self.last_error: dict[str, str] = {}
        self.messages: dict[str, list[str]] = {}
        self.lock = threading.Lock()

    def before(self, source: str) -> None:
        if source in self.stopped:
            raise SourceStopped(f"{source}: bron gestopt ({self.stopped[source]})")
        last = self.last_request.get(source)
        if last is not None:
            wait = random.uniform(*DELAY_SECONDS) - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self.requests[source] += 1

    def after(self, source: str, status: int | None = None, error: Exception | None = None) -> None:
        self.last_request[source] = time.monotonic()  # de pauze telt vanaf het einde van een request
        if error is not None:
            self.connection_errors[source] += 1
            if self.connection_errors[source] >= MAX_CONNECTION_ERRORS:
                self.stop(source, f"onbereikbaar na {MAX_CONNECTION_ERRORS} verbindingsfouten: {type(error).__name__}")
            return
        self.connection_errors[source] = 0
        if status in BLOCK_STATUSES:
            self.stop(source, f"HTTP {status}")

    def stop(self, source: str, reason: str) -> None:
        with self.lock:
            if source not in self.stopped:
                self.stopped[source] = reason
                log(source, f"GESTOPT: {reason}. Deze bron wordt overgeslagen.")

    def note(self, source: str, message: str) -> None:
        with self.lock:
            notes = self.messages.setdefault(source, [])
            if message not in notes and len(notes) < 50:
                notes.append(message)


def source_for(url: str) -> str:
    host = urlsplit(url).hostname or ""
    return next((name for name in SOURCES if name in host), host)


class JobSpyLogWatcher(logging.Handler):
    """Leest JobSpy's eigen foutmeldingen mee en stopt een bron die zegt geblokkeerd te zijn."""

    def __init__(self, source: str, polite: Politeness) -> None:
        super().__init__(level=logging.WARNING)
        self.source = source
        self.polite = polite

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        self.polite.note(self.source, message)
        if record.levelno >= logging.ERROR:
            self.polite.errors[self.source] += 1
            self.polite.last_error[self.source] = message
        lowered = message.lower()
        if "blocked" in lowered:
            self.polite.stop(self.source, f"JobSpy meldt: {message}")
        elif "authwall" in lowered or "/login" in lowered:
            self.polite.authwall[self.source] += 1
            if self.polite.authwall[self.source] >= MAX_AUTHWALL_REDIRECTS:
                self.polite.stop(self.source, "doorgestuurd naar de inlogpagina")


def install_jobspy_politeness(polite: Politeness) -> None:
    """Elk request van JobSpy loopt via Politeness: pauze vooraf, statuscode achteraf."""
    from jobspy import util as jobspy_util

    original = jobspy_util.RotatingProxySession.request

    def request(self, method, url, **kwargs):
        source = source_for(url)
        polite.before(source)
        try:
            response = original(self, method, url, **kwargs)
        except Exception as e:
            polite.after(source, error=e)
            raise
        polite.after(source, status=response.status_code)
        return response

    jobspy_util.RotatingProxySession.request = request
    for source, name in JOBSPY_LOGGERS.items():
        logging.getLogger(f"JobSpy:{name}").addHandler(JobSpyLogWatcher(source, polite))


def query_for(term: str) -> str:
    """Exacte woordgroep: anders vindt 'AI Act' elke vacature met 'AI' en 'act'."""
    return f'"{term}"' if (" " in term or "-" in term) else term


def scrape_jobspy(source: str, term: str, args) -> list[dict]:
    from jobspy import scrape_jobs

    kwargs = dict(
        site_name=[source],
        search_term=term if args.loose else query_for(term),
        results_wanted=args.max,
        hours_old=args.days * 24,
        country_indeed=LOCATION,
        description_format="markdown",
        verbose=1,
    )
    if source == "linkedin":
        kwargs |= dict(location=LOCATION, distance=None, fetch_description=not args.no_linkedin_details)
    elif source == "glassdoor":
        kwargs |= dict(location=LOCATION, distance=None, fetch_description=True)
    elif source == "google":
        kwargs |= dict(google_search_term=f"{term} jobs in {LOCATION} since last month")
    df = scrape_jobs(**kwargs)
    if df.empty:
        return []
    rows = []
    for row in df.to_dict("records"):
        clean = {}
        for key, value in row.items():
            if key in DROP_COLUMNS:
                continue
            if isinstance(value, float) and value != value:  # NaN
                value = None
            elif isinstance(value, (date, datetime)):
                value = value.isoformat()
            clean[key] = value
        rows.append(clean)
    return rows


def scrape_adzuna(term: str, args, polite: Politeness, session: requests.Session) -> list[dict]:
    app_id, app_key = os.environ["ADZUNA_APP_ID"], os.environ["ADZUNA_APP_KEY"]
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": args.max,
        "max_days_old": args.days,
        "sort_by": "date",
        "content-type": "application/json",
    }
    multiword = " " in term or "-" in term
    params["what_phrase" if multiword and not args.loose else "what"] = term
    polite.before("adzuna")
    try:
        response = session.get(ADZUNA_URL, params=params, timeout=30)
    except requests.RequestException as e:
        polite.after("adzuna", error=e)
        raise RuntimeError(f"verbindingsfout ({type(e).__name__})") from None
    polite.after("adzuna", status=response.status_code)
    if response.status_code != 200:
        # De URL bevat de sleutels, dus enkel de status tonen.
        raise RuntimeError(f"HTTP {response.status_code}")
    return response.json().get("results") or []


def scrub_rows(rows: list[dict], text_fields) -> tuple[list[dict], Counter]:
    totals: Counter = Counter()
    for row in rows:
        for field in text_fields:
            if isinstance(row.get(field), str):
                row[field], counts = common.scrub_pii(row[field])
                totals.update({k: v for k, v in counts.items() if v})
    return rows, totals


def raw_path(source: str, term: str):
    return common.RAW_DIR / source / f"{common.slug(term)}.json"


def run_source(source: str, terms: list[str], args, polite: Politeness) -> dict:
    status = {}
    session = requests.Session() if source == "adzuna" else None
    for term in terms:
        path = raw_path(source, term)
        if path.exists() and not args.refresh:
            cached = json.loads(path.read_text(encoding="utf-8"))
            # LinkedIn zonder tekst (proefrun met --no-linkedin-details) opnieuw ophalen met tekst.
            missing_details = (
                source == "linkedin" and not args.no_linkedin_details and not cached.get("linkedin_details")
            )
            if cached.get("volledig") and not missing_details:
                status[term] = {"status": "al opgehaald", "aantal": len(cached["resultaten"])}
                continue
        if source in polite.stopped:
            status[term] = {"status": "overgeslagen", "aantal": 0}
            log(source, f"'{term}': overgeslagen (bron gestopt)")
            continue
        started = time.monotonic()
        error = None
        errors_before = polite.errors[source]
        try:
            if source == "adzuna":
                rows = scrape_adzuna(term, args, polite, session)
                rows, pii = scrub_rows(rows, ("description",))
            else:
                rows = scrape_jobspy(source, term, args)
                rows, pii = scrub_rows(rows, TEXT_COLUMNS)
        except SourceStopped:
            rows, pii = [], Counter()
        except Exception as e:
            rows, pii, error = [], Counter(), f"{type(e).__name__}: {e}"
        if error is None and polite.errors[source] > errors_before:
            # JobSpy vangt zijn eigen fouten op en logt ze enkel: dan is de zoekterm niet af.
            error = polite.last_error[source][:300]
        complete = error is None and source not in polite.stopped
        if rows or complete:
            common.write_json(
                path,
                {
                    "bron": source,
                    "zoekterm": term,
                    "query": term if args.loose or source == "adzuna" else query_for(term),
                    "opgehaald_op": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "max_dagen": args.days,
                    "linkedin_details": source == "linkedin" and not args.no_linkedin_details,
                    "volledig": complete,
                    "pii_verwijderd": dict(pii),
                    "resultaten": rows,
                },
            )
        label = "ok" if complete else ("fout" if error else "onvolledig (bron gestopt)")
        status[term] = {"status": label, "aantal": len(rows), "fout": error}
        log(source, f"'{term}': {len(rows)} vacatures, {label} ({time.monotonic() - started:.0f} s)")
    return status


# --- Verwerken: raw -> genormaliseerde records -> deduplicatie ---------------------


def strip_html(text: str | None) -> str | None:
    if not text:
        return text
    return " ".join(re.sub(r"<[^>]+>", " ", text).split())


def to_record(source: str, term: str, row: dict) -> dict:
    if source == "adzuna":
        location = row.get("location") or {}
        return {
            "bron": source,
            "zoekterm": term,
            "titel": strip_html(row.get("title")),
            "bedrijf": (row.get("company") or {}).get("display_name"),
            "plaats": location.get("display_name"),
            "datum": (row.get("created") or "")[:10] or None,
            "url": row.get("redirect_url"),
            "beschrijving": strip_html(row.get("description")),
            "sector_bron": (row.get("category") or {}).get("label"),
        }
    return {
        "bron": source,
        "zoekterm": term,
        "titel": row.get("title"),
        "bedrijf": row.get("company"),
        "plaats": row.get("location"),
        "datum": (row.get("date_posted") or "")[:10] or None,
        "url": row.get("job_url"),
        "beschrijving": row.get("description"),
        "sector_bron": row.get("company_industry"),
    }


def load_raw() -> tuple[list[dict], list[dict]]:
    """Alle raw-bestanden als records, plus een overzicht per bestand."""
    records, files = [], []
    for path in sorted(common.RAW_DIR.glob("*/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        source, term = data["bron"], data["zoekterm"]
        rows = data["resultaten"]
        texts = [strip_html(f"{r.get('title')} {r.get('description') or ''}") for r in rows]
        files.append(
            {
                "bron": source,
                "zoekterm": term,
                "aantal": len(rows),
                "volledig": data.get("volledig"),
                "met_term": sum(common.term_in_text(term, t) for t in texts),
                "met_beschrijving": sum(bool(r.get("description")) for r in rows),
                "tekstlengtes": [len(r.get("description") or "") for r in rows],
                "pii_verwijderd": data.get("pii_verwijderd", {}),
            }
        )
        records += [to_record(source, term, row) for row in rows]
    return records, files


def deduplicate(records: list[dict], days: int) -> tuple[list[dict], int]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    groups: dict[str, list[dict]] = {}
    too_old = 0
    for record in records:
        if not record["titel"]:
            continue
        if record["datum"] and record["datum"] < cutoff:
            too_old += 1
            continue
        key = common.dedup_key(record["bedrijf"], record["titel"], record["plaats"], record["url"] or "")
        groups.setdefault(key, []).append(record)

    term_order = {t: i for i, t in enumerate(common.ALL_TERMS)}
    jobs = []
    for key, group in groups.items():
        primary = max(group, key=lambda r: len(r["beschrijving"] or ""))
        terms = sorted({r["zoekterm"] for r in group}, key=lambda t: term_order.get(t, 99))
        dates = sorted(r["datum"] for r in group if r["datum"])
        flag, reason = common.recruiter_flag(primary["bedrijf"], primary["beschrijving"])
        jobs.append(
            {
                "job_id": common.job_id(key),
                "bedrijf": primary["bedrijf"],
                "titel": primary["titel"],
                "plaats": primary["plaats"],
                "datum": dates[0] if dates else None,
                "bron": "; ".join(sorted({r["bron"] for r in group})),
                "zoekterm": "; ".join(terms),
                "categorie": "; ".join(sorted({common.TERM_CATEGORY.get(t, "?") for t in terms})),
                "url": primary["url"],
                "alle_urls": list(dict.fromkeys(r["url"] for r in group if r["url"])),
                "sector_bron": primary["sector_bron"],
                "recruiter_vlag": flag,
                "recruiter_reden": reason,
                "beschrijving": primary["beschrijving"],
            }
        )
    jobs.sort(key=lambda j: (j["datum"] or "", j["bedrijf"] or ""), reverse=True)
    return jobs, too_old


# --- Overzicht ----------------------------------------------------------------------


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(str(c).replace("|", "/") for c in row) + " |" for row in rows]
    return "\n".join(lines)


def build_summary(files, records, jobs, too_old, run_status, stopped, request_counts, sources_used, seed) -> str:
    out = [f"# Fase 1: overzicht ({datetime.now():%Y-%m-%d %H:%M})", ""]

    out += ["## Status per bron", ""]
    rows = []
    for source in sources_used:
        source_files = [f for f in files if f["bron"] == source]
        lengths = [n for f in source_files for n in f["tekstlengtes"]]
        found = sum(f["aantal"] for f in source_files)
        with_text = sum(f["met_beschrijving"] for f in source_files)
        if not source_files and not run_status.get(source):
            state = "geen data"
        elif source in stopped:
            state = f"gestopt: {stopped[source]}"
        elif run_status.get(source, {}).get("_reden"):
            state = run_status[source]["_reden"]
        elif any(s.get("status") == "fout" for s in run_status.get(source, {}).values() if isinstance(s, dict)):
            state = "ok, met fouten (zie run_log.json)"
        elif any(not f["volledig"] for f in source_files):
            state = "onvolledig (zie data/raw/run_log.json)"
        else:
            state = "ok"
        rows.append(
            [
                source,
                state,
                f"{len({f['zoekterm'] for f in source_files})}/{len(common.ALL_TERMS)}",
                request_counts.get(source, "-"),
                found,
                f"{100 * with_text / found:.0f}%" if found else "-",
                int(statistics.median(lengths)) if lengths else "-",
            ]
        )
    out += [md_table(["bron", "status", "termen", "requests deze run", "vacatures", "met tekst", "mediaan tekstlengte"], rows), ""]

    out += ["## Per zoekterm", ""]
    by_term_source = {(f["zoekterm"], f["bron"]): f for f in files}
    unique_per_term = Counter(t for j in jobs for t in j["zoekterm"].split("; "))
    rows = []
    for term in common.ALL_TERMS:
        cells = [by_term_source.get((term, s), {}).get("aantal", "-") for s in sources_used]
        term_files = [f for f in files if f["zoekterm"] == term]
        total = sum(f["aantal"] for f in term_files)
        hits = sum(f["met_term"] for f in term_files)
        rows.append(
            [term, common.TERM_CATEGORY[term], *cells, total, unique_per_term.get(term, 0),
             f"{100 * hits / total:.0f}%" if total else "-"]
        )
    out += [
        md_table(["zoekterm", "categorie", *sources_used, "totaal", "uniek na dedup", "term in titel/tekst"], rows),
        "",
        "'term in titel/tekst' is een eerste ruisindicatie: het aandeel resultaten waarin de zoekterm "
        "letterlijk voorkomt. Laag bij LinkedIn zonder tekst en bij Adzuna (ingekorte tekst).",
        "",
    ]

    recruiters = sum(j["recruiter_vlag"] for j in jobs)
    multi = sum(";" in j["bron"] for j in jobs)
    pii = Counter()
    for f in files:
        pii.update(f["pii_verwijderd"])
    out += [
        "## Totalen",
        "",
        f"- Opgehaald (alle bronnen en zoektermen samen): {len(records)}",
        f"- Weggelaten omdat ouder dan de grens: {too_old}",
        f"- Uniek na deduplicatie (bedrijf + titel + plaats): {len(jobs)}",
        f"- Gevonden op meer dan één bron: {multi}",
        f"- Met recruiter-/interimvlag (gemarkeerd, niet verwijderd): {recruiters}",
        f"- Verwijderde persoonsgegevens: e-mail {pii['email']}, telefoon {pii['telefoon']}, "
        f"naam {pii['naam']}, profiel-URL {pii['profiel']}",
        "",
    ]

    sample = random.Random(seed).sample(jobs, min(10, len(jobs)))
    out += ["## Tien willekeurige voorbeelden", ""]
    out += [
        md_table(
            ["bedrijf", "titel", "bron", "recruitervlag"],
            [[j["bedrijf"], j["titel"], j["bron"], "ja" if j["recruiter_vlag"] else ""] for j in sample],
        ),
        "",
    ]
    return "\n".join(out)


def write_outputs(jobs: list[dict]) -> None:
    common.write_jsonl(common.JOBS_FILE, jobs)
    csv_path = common.DATA_DIR / "vacatures_fase1.csv"
    columns = [k for k in jobs[0] if k not in ("beschrijving", "alle_urls")] if jobs else []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(jobs)


def parse_args():
    parser = argparse.ArgumentParser(description="Fase 1: vacatures verzamelen")
    parser.add_argument("--sources", nargs="+", choices=SOURCES, default=DEFAULT_SOURCES,
                        help="bronnen (standaard: indeed linkedin glassdoor adzuna)")
    parser.add_argument("--terms", nargs="+", help="enkel deze zoektermen (standaard: alle)")
    parser.add_argument("--max", type=int, default=common.MAX_RESULTS,
                        help=f"resultaten per zoekterm per bron (max {common.MAX_RESULTS})")
    parser.add_argument("--days", type=int, default=common.MAX_DAYS,
                        help=f"enkel vacatures van de laatste N dagen (max {common.MAX_DAYS})")
    parser.add_argument("--no-linkedin-details", action="store_true",
                        help="LinkedIn-vacatureteksten niet ophalen (veel sneller, maar zonder tekst)")
    parser.add_argument("--loose", action="store_true",
                        help="zoektermen niet als exacte woordgroep zoeken")
    parser.add_argument("--refresh", action="store_true", help="ook al opgehaalde zoektermen opnieuw ophalen")
    parser.add_argument("--only-process", action="store_true", help="niets ophalen, enkel data/raw/ verwerken")
    parser.add_argument("--seed", type=int, default=None, help="seed voor de tien voorbeelden")
    args = parser.parse_args()
    args.max = max(1, min(args.max, common.MAX_RESULTS))
    args.days = max(1, min(args.days, common.MAX_DAYS))
    if args.terms:
        unknown = [t for t in args.terms if t not in common.ALL_TERMS]
        if unknown:
            parser.error(f"onbekende zoekterm(en): {unknown}. Kies uit: {common.ALL_TERMS}")
    return args


def main() -> None:
    args = parse_args()
    load_dotenv(common.ROOT / ".env")
    terms = args.terms or common.ALL_TERMS
    sources = list(args.sources)
    run_status: dict[str, dict] = {}
    stopped: dict[str, str] = {}
    request_counts: dict[str, int] = {}
    run_log_path = common.RAW_DIR / "run_log.json"
    previous = json.loads(run_log_path.read_text(encoding="utf-8")) if run_log_path.exists() else {}

    if not args.only_process:
        if "adzuna" in sources and not (os.getenv("ADZUNA_APP_ID") and os.getenv("ADZUNA_APP_KEY")):
            run_status["adzuna"] = {"_reden": "overgeslagen: ADZUNA_APP_ID/ADZUNA_APP_KEY ontbreken in .env"}
            log("adzuna", run_status["adzuna"]["_reden"])
            sources.remove("adzuna")
        polite = Politeness()
        install_jobspy_politeness(polite)
        print(
            f"{len(terms)} zoektermen x {len(sources)} bronnen, max {args.max} resultaten, "
            f"laatste {args.days} dagen, {DELAY_SECONDS[0]:.0f} tot {DELAY_SECONDS[1]:.0f} s pauze per request.",
            flush=True,
        )
        if "linkedin" in sources and not args.no_linkedin_details:
            print("LinkedIn haalt per vacature de tekst apart op: reken op 1 tot 2 uur voor alle termen.", flush=True)
        with ThreadPoolExecutor(max_workers=max(1, len(sources))) as pool:
            futures = {s: pool.submit(run_source, s, terms, args, polite) for s in sources}
            for source, future in futures.items():
                run_status[source] = future.result()
        # Bronnen die deze keer niet meededen, houden hun status uit de vorige run.
        stopped = {s: r for s, r in previous.get("gestopt", {}).items() if s not in args.sources}
        stopped |= polite.stopped
        earlier = {s: st for s, st in previous.get("per_bron", {}).items() if s not in run_status}
        run_status = earlier | run_status
        request_counts = dict(polite.requests)
        common.write_json(
            run_log_path,
            {
                "gedraaid_op": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "argumenten": {k: v for k, v in vars(args).items()},
                "gestopt": stopped,
                "requests": request_counts,
                "per_bron": run_status,
                "jobspy_meldingen": polite.messages,
            },
        )

    else:
        stopped, run_status = previous.get("gestopt", {}), previous.get("per_bron", {})

    records, files = load_raw()
    if not records:
        print("Geen vacatures in data/raw/. Niets te verwerken.")
        sys.exit(1)
    jobs, too_old = deduplicate(records, args.days)
    write_outputs(jobs)
    sources_used = [s for s in SOURCES if s in args.sources or any(f["bron"] == s for f in files)]
    summary = build_summary(
        files, records, jobs, too_old, run_status, stopped, request_counts, sources_used, args.seed
    )
    (common.DATA_DIR / "fase1_overzicht.md").write_text(summary, encoding="utf-8")
    print("\n" + summary)
    print(f"Opgeslagen: {common.JOBS_FILE.relative_to(common.ROOT)}, data/vacatures_fase1.csv, data/fase1_overzicht.md")


if __name__ == "__main__":
    main()
