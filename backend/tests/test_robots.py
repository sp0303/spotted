from spotted import robots

TXT = """
# comment
User-agent: *
Disallow: /admin/
Allow: /admin/public$

User-agent: GPTBot
User-agent: ClaudeBot
Disallow: /

User-agent: Googlebot
Disallow: /private
Allow: /private/ok*

User-agent: googlebot
Disallow: /tmp

Sitemap: https://shop.example/sitemap.xml
bogus line
Crawl-delay: 5
"""


def test_parse_groups_and_sitemaps():
    r = robots.parse(TXT)
    assert [g.agents for g in r.groups] == [["*"], ["GPTBot", "ClaudeBot"], ["Googlebot"], ["googlebot"]]
    assert r.sitemaps == ["https://shop.example/sitemap.xml"]
    assert r.invalid_lines == [19]  # line numbers count the leading blank line


def test_specific_group_wins_and_groups_merge():
    r = robots.parse(TXT)
    assert robots.check(r, "GPTBot", "https://shop.example/").rule == "disallow"
    assert robots.check(r, "ClaudeBot", "https://shop.example/x").matched == "Disallow: /"
    g = robots.check(r, "Googlebot", "https://shop.example/admin/")
    assert g.rule == "allow" and g.group == "Googlebot"  # Googlebot ignores the * group
    assert robots.check(r, "Googlebot", "https://shop.example/tmp/a").rule == "disallow"  # merged group
    assert robots.check(r, "Googlebot", "https://shop.example/private/ok-page").rule == "allow"  # longer Allow
    assert robots.check(r, "Googlebot", "https://shop.example/private/no").rule == "disallow"


def test_wildcard_group_and_no_rule():
    r = robots.parse(TXT)
    assert robots.check(r, "Bingbot", "https://shop.example/").rule == "no_rule"
    v = robots.check(r, "Bingbot", "https://shop.example/admin/x")
    assert v.rule == "disallow" and v.group == "*"
    assert robots.check(r, "Bingbot", "https://shop.example/admin/public").rule == "no_rule"
    assert robots.check(r, "Bingbot", "https://shop.example/admin/public2").rule == "disallow"  # $ anchors


def test_empty_disallow_and_no_groups():
    r = robots.parse("User-agent: *\nDisallow:\n")
    assert robots.check(r, "GPTBot", "https://a.example/").rule == "no_rule"
    assert robots.check(robots.parse(""), "GPTBot", "https://a.example/").rule == "no_rule"
