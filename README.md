# jobwatch: new-job email alerts for Ireland and UK

A small Python tool that checks company career portals and emails you only the **new** jobs that match your rules: location (Ireland/UK), level (entry or experienced), keywords, and visa-sponsorship signals. It runs free on a schedule with GitHub Actions.

**Python standard library only** (no dependencies), so it is easy to read, test and explain.

## How it works

```
sources.py   ->  filters.py   ->  storage.py   ->  notifier.py
fetch + parse    location /       SQLite memory     HTML + text
public JSON      level / visa /   of seen jobs      email via SMTP
APIs             keyword score    (alert once)
```

| Module | What it does | Skill it shows |
|---|---|---|
| `sources.py` | Fetches jobs from Greenhouse and Lever public APIs, plus a configurable generic JSON adapter | REST APIs, JSON parsing, retries, error handling |
| `filters.py` | Regex location match, title-based level classifier, visa phrase detection (negatives win), keyword scoring | Rule-based logic, regex, edge cases |
| `storage.py` | SQLite table of seen job ids so each job is announced once | SQL, idempotency |
| `notifier.py` | Builds an HTML and plain-text digest, sends via SMTP using env-var secrets | Email automation, secrets handling |
| `cli.py` | Orchestrates, supports `--dry-run` and `--baseline`, isolates failing sources | CLI design, reliability |
| `.github/workflows/jobwatch.yml` | Runs every 6 hours, caches the SQLite file between runs | CI/CD, scheduled automation, secrets |

## Run it locally

```bash
cp config.example.json config.json      # edit sources and preferences
export PYTHONPATH=src
python -m jobwatch --config config.json --baseline   # first run: remember today's jobs, send nothing
python -m jobwatch --config config.json --dry-run    # prints what WOULD be emailed
python -m unittest discover -s tests -v              # run the tests
```

To send real email, set these environment variables (use an **app password**, never your normal password):

```bash
export SMTP_HOST=smtp.gmail.com SMTP_USER=you@gmail.com SMTP_PASSWORD=your-app-password
```

## Add companies

* **Greenhouse:** if a company's board is `boards.greenhouse.io/<token>`, add `{"type":"greenhouse","company":"Name","token":"<token>"}`.
* **Lever:** if it is `jobs.lever.co/<slug>`, add `{"type":"lever","company":"Name","slug":"<slug>"}`.
* **Any other portal (e.g. Accenture):** open the careers site, press F12, go to the **Network** tab, search jobs, and look for a JSON (XHR/Fetch) request. Use the `generic` source with that URL and map its field names. **Check the site's terms and robots.txt first, keep the request rate low, and never scrape LinkedIn.**

## Subscribers

Put people in `subscribers` with their own `levels`, `keywords` and `require_visa`. For a public repo, **do not commit email addresses**. Add a repository secret `JOBWATCH_SUBSCRIBERS` (comma-separated) instead.

## Deploy on GitHub Actions

1. Push this folder to a public repo.
2. Repo **Settings → Secrets and variables → Actions**: add `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `JOBWATCH_SUBSCRIBERS`.
3. Run the workflow once with `--baseline` (edit the command) so you are not flooded, then switch back.

## Honest limitations

* Visa detection is keyword-based: "likely" is a hint, not a guarantee. Always read the posting.
* Level detection uses the job title only.
* GitHub's cache can be evicted after 7 days of inactivity, which can cause one repeated digest.
* The generic adapter needs a real endpoint, which has to be checked from your own machine.

## Ideas to extend

Add UK Skilled Worker and Irish Critical Skills Employment Permit salary checks, a Telegram bot, per-source rate limits, a small Flask dashboard, or Docker.
