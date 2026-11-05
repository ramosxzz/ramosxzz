"""Build neofetch-style profile cards (dark_mode.svg / light_mode.svg).

Stdlib only. Needs GITHUB_TOKEN (or ACCESS_TOKEN for private repo stats).
"""
import datetime as dt
import json
import os
import time
import urllib.request
from html import escape
from pathlib import Path

USER = "ramosxzz"
ROOT = Path(__file__).parent
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
HEADERS = {"Authorization": f"bearer {TOKEN}", "User-Agent": USER}

WIDTH = 58  # chars per info line
ASCII_FONT, ASCII_LH = 8, 8  # small font so the avatar has more detail

INFO = [
    ("title", "matheus@ramos"),
    ("kv", "OS", "Windows 10"),
    ("kv", "Uptime", "{uptime}"),
    ("kv", "Host", "Solaire W+"),
    ("kv", "Kernel", "Full Stack Developer"),
    ("kv", "IDE", "VSCode"),
    ("blank",),
    ("kv", "Languages.Programming", "TypeScript, JavaScript, Python"),
    ("kv", "Languages.Computer", "HTML, CSS, JSON, SQL, Shell"),
    ("kv", "Languages.Real", "Portuguese, English"),
    ("blank",),
    ("kv", "Hobbies.Software", "Linux Ricing, Hyprland"),
    ("kv", "Hobbies.Hardware", "Custom Setups"),
    ("blank",),
    ("section", "Contact"),
    ("kv", "Email.Work", "admin@solairew.com.br"),
    ("kv", "Website", "ramosx.tech"),
    ("kv", "GitHub", USER),
    ("blank",),
    ("section", "GitHub Stats"),
    ("stats1",),
    ("stats2",),
    ("loc",),
]

THEMES = {
    "dark": dict(bg="#161b22", text="#c9d1d9", key="#ffa657", value="#a5d6ff",
                 cc="#616e7f", add="#3fb950", dele="#f85149"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", value="#0a3069",
                  cc="#c2cfde", add="#1a7f37", dele="#cf222e"),
}


# ---------- GitHub API ----------

def request(url, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, json.loads(r.read() or "null")


def graphql(query, **variables):
    _, res = request("https://api.github.com/graphql", {"query": query, "variables": variables})
    if res.get("errors"):
        raise RuntimeError(res["errors"])
    return res["data"]


def fetch_stats():
    d = graphql("""
    query($login: String!) {
      user(login: $login) {
        id createdAt
        followers { totalCount }
        owned: repositories(ownerAffiliations: OWNER, first: 100) {
          totalCount
          nodes { name isFork stargazerCount }
        }
        all: repositories(ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]) { totalCount }
      }
    }""", login=USER)["user"]

    created = dt.datetime.fromisoformat(d["createdAt"].replace("Z", "+00:00"))
    commits = 0
    year_start = created
    now = dt.datetime.now(dt.timezone.utc)
    while year_start < now:
        year_end = min(year_start + dt.timedelta(days=365), now)
        commits += graphql("""
        query($login: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $login) { contributionsCollection(from: $from, to: $to) {
            totalCommitContributions restrictedContributionsCount } }
        }""", login=USER, **{"from": year_start.isoformat(), "to": year_end.isoformat()}
        )["user"]["contributionsCollection"]["totalCommitContributions"]
        year_start = year_end

    owned = d["owned"]["nodes"]
    add, dele = lines_of_code([r["name"] for r in owned if not r["isFork"]])
    return dict(
        created=created,
        repos=d["owned"]["totalCount"],
        contributed=d["all"]["totalCount"],
        stars=sum(r["stargazerCount"] for r in owned),
        followers=d["followers"]["totalCount"],
        commits=commits,
        add=add,
        dele=dele,
    )


def lines_of_code(repos):
    add = dele = 0
    for name in repos:
        url = f"https://api.github.com/repos/{USER}/{name}/stats/contributors"
        for _ in range(6):  # GitHub returns 202 while it computes stats
            status, data = request(url)
            if status == 200:
                break
            time.sleep(3)
        else:
            continue
        for c in data or []:
            if c.get("author") and c["author"]["login"].lower() == USER.lower():
                add += sum(w["a"] for w in c["weeks"])
                dele += sum(w["d"] for w in c["weeks"])
    return add, dele


def uptime(created):
    today = dt.date.today()
    start = created.date()
    months = (today.year - start.year) * 12 + today.month - start.month
    if today.day < start.day:
        months -= 1
    anchor_m = start.month + months
    anchor = start.replace(year=start.year + (anchor_m - 1) // 12, month=(anchor_m - 1) % 12 + 1)
    days = (today - anchor).days
    y, m = divmod(months, 12)
    plural = lambda n, w: f"{n} {w}{'s' if n != 1 else ''}"
    return f"{plural(y, 'year')}, {plural(m, 'month')}, {plural(days, 'day')}"


# ---------- SVG ----------

def span(cls, text):
    return f'<tspan class="{cls}">{escape(text)}</tspan>'


def kv(key, value, width=WIDTH):
    """'. Key: ....... value' padded to width."""
    dots = width - len(key) - len(value) - 5
    return ". " + span("key", key) + ":" + span("cc", " " + "." * max(dots, 1) + " ") + span("value", value)


def build_lines(s):
    n = lambda v: f"{v:,}"
    out = []
    for item in INFO:
        kind = item[0]
        if kind == "title":
            out.append(span("title", item[1]) + " " + span("cc", "—" * (WIDTH - len(item[1]) - 4) + "-—-"))
        elif kind == "kv":
            out.append(kv(item[1], item[2].format(uptime=uptime(s["created"]))))
        elif kind == "blank":
            out.append(span("cc", ". "))
        elif kind == "section":
            pad = WIDTH - len(item[1]) - 6
            out.append("- " + escape(item[1]) + " " + span("cc", "—" * pad + "-—-"))
        elif kind == "stats1":
            left = f"{n(s['repos'])} {{Contributed: {n(s['contributed'])}}}"
            out.append(kv("Repos", left, 34) + " | " + kv("Stars", n(s["stars"]), 21)[2:])
        elif kind == "stats2":
            out.append(kv("Commits", n(s["commits"]), 34) + " | " + kv("Followers", n(s["followers"]), 21)[2:])
        elif kind == "loc":
            total = n(s["add"] - s["dele"])
            tail = f"{n(s['add'])}++, {n(s['dele'])}--"
            dots = WIDTH - len("Lines of Code on GitHub") - len(total) - len(tail) - 11
            out.append(". " + span("key", "Lines of Code on GitHub") + ":"
                       + span("cc", " " + "." * max(dots, 1) + " ") + span("value", total)
                       + " ( " + span("add", f"{n(s['add'])}++") + ", "
                       + span("del", f"{n(s['dele'])}--") + " )")
    return out


def render(theme, ascii_lines, info_lines):
    c = THEMES[theme]
    lh, top = 20, 30
    height = max(top + len(info_lines) * lh + 10, len(ascii_lines) * ASCII_LH + 30)
    ascii_top = (height - len(ascii_lines) * ASCII_LH) // 2 + ASCII_LH - 2
    ascii_text = "\n".join(
        f'<tspan x="20" y="{ascii_top + i * ASCII_LH}">{escape(l)}</tspan>' for i, l in enumerate(ascii_lines))
    info_text = "\n".join(
        f'<tspan x="400" y="{top + i * lh}">{l}</tspan>' for i, l in enumerate(info_lines))
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="Consolas,'Courier New',monospace" width="985px" height="{height}px" font-size="16px">
<style>
text, tspan {{ white-space: pre; }}
.title {{ fill: {c["text"]}; font-weight: bold; }}
.key {{ fill: {c["key"]}; }}
.value {{ fill: {c["value"]}; }}
.cc {{ fill: {c["cc"]}; }}
.add {{ fill: {c["add"]}; }}
.del {{ fill: {c["dele"]}; }}
</style>
<rect width="985px" height="{height}px" fill="{c["bg"]}" rx="15"/>
<text xml:space="preserve" fill="{c["text"]}" font-size="{ASCII_FONT}px">
{ascii_text}
</text>
<text xml:space="preserve" fill="{c["text"]}">
{info_text}
</text>
</svg>
'''


def main():
    stats = fetch_stats()
    print(json.dumps({k: str(v) for k, v in stats.items()}, indent=2))
    ascii_lines = (ROOT / "ascii.txt").read_text().rstrip("\n").split("\n")
    info = build_lines(stats)
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(render(theme, ascii_lines, info))


if __name__ == "__main__":
    main()
