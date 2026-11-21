"""robots.txt parsing and matching, following Google's documented rules (RFC 9309):

- a crawler obeys the group whose user-agent equals its product token (case-insensitive); groups
  naming the same agent are merged; with no such group it obeys `*`
- within the group, the longest matching path pattern wins; on a tie, Allow wins
- `*` matches any run of characters and a trailing `$` anchors the end
- an empty Disallow means nothing is disallowed
"""

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass
class Rule:
    allow: bool
    pattern: str
    line: int

    def matches(self, path: str) -> bool:
        return _compile(self.pattern).match(path) is not None


@dataclass
class Group:
    agents: list[str] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)


@dataclass
class Robots:
    groups: list[Group] = field(default_factory=list)
    sitemaps: list[str] = field(default_factory=list)
    invalid_lines: list[int] = field(default_factory=list)


@dataclass
class Verdict:
    rule: str  # robots_rule enum: allow | disallow | no_rule
    group: str | None  # agent of the group that applied ("*" for the wildcard), None if none
    matched: str | None  # the deciding line, e.g. "Disallow: /"


_cache: dict[str, re.Pattern[str]] = {}


def _compile(pattern: str) -> re.Pattern[str]:
    if pattern not in _cache:
        anchored = pattern.endswith("$")
        body = pattern[:-1] if anchored else pattern
        regex = "".join(".*" if ch == "*" else re.escape(ch) for ch in body)
        _cache[pattern] = re.compile(regex + ("$" if anchored else ""), re.S)
    return _cache[pattern]


def parse(text: str) -> Robots:
    robots = Robots()
    current: Group | None = None
    last_was_agent = False
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            robots.invalid_lines.append(n)
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if current is None or not last_was_agent:
                current = Group()
                robots.groups.append(current)
            current.agents.append(value)
            last_was_agent = True
            continue
        last_was_agent = False
        if key in ("allow", "disallow"):
            if current is None:
                robots.invalid_lines.append(n)
            elif value:
                current.rules.append(Rule(allow=key == "allow", pattern=value, line=n))
        elif key == "sitemap":
            robots.sitemaps.append(value)
        elif key not in ("crawl-delay", "host", "clean-param", "request-rate", "visit-time"):
            robots.invalid_lines.append(n)
    return robots


def _rules_for(robots: Robots, agent: str) -> list[Rule] | None:
    found = [g for g in robots.groups if any(a.lower() == agent.lower() for a in g.agents)]
    if not found:
        return None
    return [r for g in found for r in g.rules]


def check(robots: Robots, token: str, url: str) -> Verdict:
    parts = urlsplit(url)
    path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    specific = _rules_for(robots, token)
    group = token if specific is not None else ("*" if _rules_for(robots, "*") is not None else None)
    rules = specific if specific is not None else (_rules_for(robots, "*") or [])
    best: Rule | None = None
    for rule in rules:
        if rule.matches(path):
            if best is None or len(rule.pattern) > len(best.pattern) or (
                len(rule.pattern) == len(best.pattern) and rule.allow and not best.allow
            ):
                best = rule
    matched = f"{'Allow' if best.allow else 'Disallow'}: {best.pattern}" if best else None
    if best is not None and not best.allow:
        return Verdict("disallow", group, matched)
    if specific is not None:
        return Verdict("allow", group, matched)
    # Nothing blocks it and no group names it: the '*' Allow line isn't a decision about this crawler.
    return Verdict("no_rule", group, None)
