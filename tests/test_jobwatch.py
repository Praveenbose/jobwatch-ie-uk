import sys, unittest, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from jobwatch.filters import classify_level, evaluate, in_target_location, visa_signal
from jobwatch.models import Job
from jobwatch.notifier import build_digest
from jobwatch import sources
from jobwatch.sources import parse_generic, parse_greenhouse, parse_lever
from jobwatch.storage import SeenStore


def job(title="Junior Cloud Engineer", loc="Dublin, Ireland", desc="Visa sponsorship available.", jid="1"):
    return Job("greenhouse", jid, "Acme", title, loc, "https://x/1", desc)


class ParseTests(unittest.TestCase):
    def test_greenhouse(self):
        data = {"jobs": [{"id": 7, "title": "Analyst", "location": {"name": "Cork"}, "absolute_url": "u", "content": "c"}]}
        j = parse_greenhouse(data, "Acme")[0]
        self.assertEqual((j.job_id, j.location, j.uid), ("7", "Cork", "greenhouse:acme:7"))

    def test_lever(self):
        data = [{"id": "abc", "text": "Dev", "categories": {"location": "London"}, "hostedUrl": "u", "descriptionPlain": "d"}]
        self.assertEqual(parse_lever(data, "Acme")[0].location, "London")

    def test_generic_nested_paths(self):
        data = {"data": {"jobs": [{"id": 1, "t": "QA", "loc": {"city": "Belfast"}, "link": "u"}]}}
        cfg = {"company": "Acme", "list_path": "data.jobs",
               "fields": {"id": "id", "title": "t", "location": "loc.city", "url": "link"}}
        self.assertEqual(parse_generic(data, cfg)[0].location, "Belfast")


class PagingTests(unittest.TestCase):
    def test_pagination_stops_on_empty_page(self):
        calls = []
        def fake(url, **kw):
            calls.append((url, kw.get("method"), kw.get("body")))
            page = kw["body"]["page"]
            return {"jobs": [{"id": page, "t": "Cloud Support", "l": "Cork", "u": "/j/%d" % page}]} if page <= 2 else {"jobs": []}
        original, sleeper = sources.fetch_json, sources.time.sleep
        sources.fetch_json, sources.time.sleep = fake, lambda s: None
        try:
            cfg = {"company": "Acme", "url": "https://x/api", "method": "POST", "body": {"country": "IE"},
                   "list_path": "jobs", "url_prefix": "https://x",
                   "fields": {"id": "id", "title": "t", "location": "l", "url": "u"},
                   "pagination": {"type": "page", "param": "page", "start": 1, "max_pages": 5}}
            jobs = sources.fetch_generic(cfg)
        finally:
            sources.fetch_json, sources.time.sleep = original, sleeper
        self.assertEqual([j.job_id for j in jobs], ["1", "2"])
        self.assertEqual(jobs[0].url, "https://x/j/1")
        self.assertEqual(calls[0][2], {"country": "IE", "page": 1})
        self.assertEqual(len(calls), 3)   # page 3 was empty, so it stopped


class FilterTests(unittest.TestCase):
    def test_location(self):
        self.assertTrue(in_target_location(job()))
        self.assertTrue(in_target_location(job(loc="UK - Remote")))
        self.assertFalse(in_target_location(job(loc="Bangalore, India")))
        self.assertFalse(in_target_location(job(loc="Dubai")))  # 'uk' must not match inside other words

    def test_levels(self):
        self.assertEqual(classify_level("Graduate Software Engineer"), "entry")
        self.assertEqual(classify_level("Senior DevOps Engineer"), "senior")
        self.assertEqual(classify_level("Cloud Engineer"), "mid")

    def test_visa_negative_wins(self):
        self.assertEqual(visa_signal(job(desc="Visa sponsorship available")), "likely")
        self.assertEqual(visa_signal(job(desc="Visa sponsorship available but unable to sponsor now")), "unlikely")
        self.assertEqual(visa_signal(job(desc="Great team")), "unknown")

    def test_evaluate(self):
        prefs = {"levels": ["entry"], "keywords": ["cloud"], "require_visa": True}
        ok, score, _ = evaluate(job(), prefs)
        self.assertTrue(ok)
        self.assertGreater(score, 3)
        self.assertFalse(evaluate(job(title="Senior Cloud Engineer"), prefs)[0])
        self.assertFalse(evaluate(job(desc="No details"), prefs)[0])       # visa required
        self.assertFalse(evaluate(job(title="Junior Chef"), prefs)[0])     # keyword missing


class StorageAndEmailTests(unittest.TestCase):
    def test_only_new_jobs(self):
        store = SeenStore(":memory:")
        a, b = job(jid="1"), job(jid="2")
        self.assertEqual(len(store.new_only([a, b])), 2)
        store.mark_seen([a])
        self.assertEqual([j.job_id for j in store.new_only([a, b])], ["2"])

    def test_digest(self):
        subject, text, html = build_digest([(job(), 6, ["entry level"])])
        self.assertIn("1 new job", subject)
        self.assertIn("Junior Cloud Engineer", text)
        self.assertIn("<a href=", html)


if __name__ == "__main__":
    unittest.main()
