from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    source: str          # e.g. "greenhouse"
    job_id: str          # id from the source
    company: str
    title: str
    location: str
    url: str
    description: str = ""

    @property
    def uid(self) -> str:
        """Globally unique id used to remember what we have already seen."""
        return f"{self.source}:{self.company.lower()}:{self.job_id}"
