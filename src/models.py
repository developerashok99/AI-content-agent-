from dataclasses import dataclass, field


@dataclass
class Article:
    title: str
    url: str
    summary: str
    source: str
    published_at: str  # ISO 8601 string
    body: str = field(default="")
