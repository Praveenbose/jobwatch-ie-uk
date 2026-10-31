import argparse
import json
import logging
import os
from typing import Dict, List

from .filters import evaluate
from .models import Job
from .notifier import build_digest, send_email
from .sources import fetch_source
from .storage import SeenStore

log = logging.getLogger("jobwatch")
DEFAULT_PREFS = {"levels": ["entry", "mid"], "keywords": [], "exclude": [], "require_visa": False}


def load_config(path: str) -> Dict:
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    # Keep subscriber emails OUT of a public repo: pass them as a secret instead.
    extra = [e.strip() for e in os.environ.get("JOBWATCH_SUBSCRIBERS", "").split(",") if e.strip()]
    cfg.setdefault("subscribers", [])
    cfg["subscribers"] += [{"email": e, **cfg.get("default_prefs", DEFAULT_PREFS)} for e in extra]
    return cfg


def collect(cfg: Dict) -> List[Job]:
    jobs: List[Job] = []
    for src in cfg["sources"]:
        try:
            found = fetch_source(src)
            log.info("%s: %d jobs", src.get("company"), len(found))
            jobs += found
        except Exception as exc:       # one broken source must not stop the others
            log.warning("source failed (%s): %s", src.get("company"), exc)
    return jobs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="jobwatch")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--db", default="data/seen.db")
    ap.add_argument("--dry-run", action="store_true", help="print instead of emailing")
    ap.add_argument("--baseline", action="store_true", help="mark all current jobs as seen, send nothing")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    cfg = load_config(args.config)
    store = SeenStore(args.db)
    fresh = store.new_only(collect(cfg))
    log.info("%d new jobs since last run", len(fresh))
    if args.baseline:
        store.mark_seen(fresh)
        log.info("baseline stored; no emails sent")
        return 0

    sent_all = True
    for sub in cfg["subscribers"]:
        prefs = {**DEFAULT_PREFS, **{k: v for k, v in sub.items() if k != "email"}}
        matches = []
        for job in fresh:
            ok, score, reasons = evaluate(job, prefs)
            if ok:
                matches.append((job, score, reasons))
        if not matches:
            continue
        subject, text, html_body = build_digest(matches)
        if args.dry_run:
            print(f"\n=== {sub['email']} :: {subject} ===\n{text}")
            continue
        try:
            send_email(sub["email"], subject, text, html_body)
        except Exception as exc:
            sent_all = False
            log.error("email to %s failed: %s", sub["email"], exc)
    if not args.dry_run and sent_all:
        store.mark_seen(fresh)           # only forget jobs once every email went out
    return 0 if sent_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
