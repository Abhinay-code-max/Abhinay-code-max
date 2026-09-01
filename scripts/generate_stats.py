#!/usr/bin/env python3
"""Draw the profile README's stat graphics from the GitHub & LeetCode APIs.

No third-party services and no dependencies — standard library only.

Outputs:
  stats.svg       hero total + weekly sparkline
  streak.svg      current and longest streak
  langs.svg       top languages, by bytes and by repo count
  year.svg        the year as a character map, in the portrait's own ramp
  terminal.svg    self-typing terminal HUD
  leetcode.svg    native LeetCode progress & stats card
  activity.svg    live recent GitHub activity feed
  hd-*.svg        custom monochrome section headings
"""
import base64
import functools
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

API_GITHUB = "https://api.github.com/graphql"
API_LEETCODE = "https://leetcode.com/graphql"

QUERY_GITHUB = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date weekday } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 privacy: PUBLIC) {
      nodes {
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""

QUERY_LEETCODE = """
query userProblemsSolved($username: String!) {
  allQuestionsCount { difficulty count }
  matchedUser(username: $username) {
    submitStatsGlobal {
      acSubmissionNum { difficulty count }
    }
    profile { ranking reputation }
  }
}
"""

LIGHT = dict(data="#6e7681", emph="#24292f", dim="#8c959f",
             rule="#d8dee4", surface="#ffffff", green="#1a7f37",
             accent="#0969da", bg="#f6f8fa", border="#d0d7de")
DARK = dict(data="#c9d1d9", emph="#f0f6fc", dim="#8b949e",
            rule="#30363d", surface="#0d1117", green="#3fb950",
            accent="#58a6ff", bg="#161b22", border="#30363d")

MONO = ("JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,"
        "&apos;Liberation Mono&apos;,monospace")
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
WIDTH = 620
LEFT = 34
REVEAL = 1.30
RAMP = [" ", ":", "+", "#", "@"]
MON = ["jan", "feb", "mar", "apr", "may", "jun",
       "jul", "aug", "sep", "oct", "nov", "dec"]

@functools.lru_cache(maxsize=None)
def face(filename, weight):
    fpath = os.path.join(FONT_DIR, filename)
    if not os.path.exists(fpath):
        return ""
    with open(fpath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return (f"@font-face{{font-family:JBMono;font-style:normal;"
            f"font-weight:{weight};font-display:block;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")

def font_text():
    return face("jbmono-400.woff2", 400) + face("jbmono-600.woff2", 600)

def font_head():
    return face("jbmono-head.woff2", 600) or font_text()

def style(extra="", font=None):
    def block(t):
        return (f".d-f{{fill:{t['data']}}}.d-s{{stroke:{t['data']}}}"
                f".e-f{{fill:{t['emph']}}}.m-f{{fill:{t['dim']}}}"
                f".u-s{{stroke:{t['rule']}}}.r{{stroke:{t['surface']}}}"
                f".g-f{{fill:{t['green']}}}.g-s{{stroke:{t['green']}}}"
                f".a-f{{fill:{t['accent']}}}.a-s{{stroke:{t['accent']}}}"
                f".card-bg{{fill:{t['bg']}}}.card-border{{stroke:{t['border']}}}")
    return (f"<style>{font or font_text()}"
            f"{block(LIGHT)}.w{{fill:{LIGHT['data']};opacity:.13}}{extra}"
            f"@media(prefers-color-scheme:dark){{{block(DARK)}"
            f".w{{fill:{DARK['data']};opacity:.16}}}}</style>")

def head(w, h, font=None, extra=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" fill="none" font-family="{MONO}">'
            + style(font=font, extra=extra))

def fade(delay, dur=0.45):
    return (f'<animate attributeName="opacity" from="0" to="1" '
            f'begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/>')

def wipe(cid, x, y, w, h, delay, dur=REVEAL):
    clip = (f'<clipPath id="{cid}"><rect x="{x}" y="{y}" height="{h}" width="0">'
            f'<animate attributeName="width" from="0" to="{w}" '
            f'begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/></rect></clipPath>')
    cursor = (f'<rect y="{y}" width="2" height="{h}" class="d-f" opacity="0">'
              f'<animate attributeName="x" from="{x}" to="{x + w}" '
              f'begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/>'
              f'<set attributeName="opacity" to="0.55" begin="{delay:.2f}s"/>'
              f'<set attributeName="opacity" to="0" '
              f'begin="{delay + dur:.2f}s"/></rect>')
    return clip, cursor

def label(x, y, text, size=11, cls="m-f", anchor="start", extra=""):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    safe_text = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if "&amp;" not in str(text) else str(text)
    return (f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}"{a}'
            f'{extra}>{safe_text}</text>')

def hbar(x, y, w, h, cls="d-f", r=3.0):
    if w <= 0.6:
        return ""
    r = min(r, h / 2.0, w)
    return (f'<path d="M{x:.1f} {y:.1f}H{x + w - r:.1f}'
            f'Q{x + w:.1f} {y:.1f} {x + w:.1f} {y + r:.1f}'
            f'V{y + h - r:.1f}Q{x + w:.1f} {y + h:.1f} {x + w - r:.1f} {y + h:.1f}'
            f'H{x:.1f}Z" class="{cls}"/>')

# ----------------- GITHUB STATS -----------------

def window():
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=364)
    return (f"{start.isoformat()}T00:00:00Z", f"{today.isoformat()}T23:59:59Z")

def fetch_github(login, token):
    since, until = window()
    body = json.dumps({"query": QUERY_GITHUB,
                       "variables": {"login": login,
                                     "from": since, "to": until}}).encode()
    req = urllib.request.Request(
        API_GITHUB, data=body,
        headers={"Authorization": f"bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": f"{login}-profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise SystemExit(f"GraphQL errors: {payload['errors']}")
    user = (payload.get("data") or {}).get("user")
    if not user:
        raise SystemExit(f"no such user: {login}")
    return user

def pretty(iso):
    d = date.fromisoformat(iso)
    return f"{MON[d.month - 1]} {d.day}"

def streaks(days):
    best = dict(length=0, start=None, end=None)
    run, run_start = 0, None
    for d in days:
        if d["contributionCount"] > 0:
            run += 1
            run_start = run_start or d["date"]
            if run > best["length"]:
                best = dict(length=run, start=run_start, end=d["date"])
        else:
            run, run_start = 0, None

    cur = dict(length=0, start=None, end=None)
    tail = days[:-1] if days and days[-1]["contributionCount"] == 0 else days
    for d in reversed(tail):
        if d["contributionCount"] == 0:
            break
        cur["length"] += 1
        cur["start"] = d["date"]
        cur["end"] = cur["end"] or d["date"]
    return cur, best

def languages(repos):
    by_size, by_repo = {}, {}
    for node in repos:
        edges = (node.get("languages") or {}).get("edges") or []
        for e in edges:
            name = e["node"]["name"]
            by_size[name] = by_size.get(name, 0) + e["size"]
        if edges:
            top = edges[0]["node"]["name"]
            by_repo[top] = by_repo.get(top, 0) + 1

    def rank(d):
        return sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:5]

    return rank(by_size), rank(by_repo)

def summarise_github(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = [w["contributionDays"] for w in cal["weeks"]]
    days = [d for w in weeks for d in w]
    weekly = [sum(d["contributionCount"] for d in w) for w in weeks]
    cur, best = streaks(days)
    by_size, by_repo = languages(user["repositories"]["nodes"])
    return dict(
        total=cal["totalContributions"],
        active=sum(1 for d in days if d["contributionCount"] > 0),
        best_week=max(weekly) if weekly else 0,
        weekly=weekly, weeks=weeks,
        current=cur, longest=best,
        by_size=by_size, by_repo=by_repo)

def draw_stats(s):
    H = 148
    weekly = s["weekly"] or [0]
    peak = max(weekly) or 1
    p = [head(WIDTH, H)]
    p.append(f'<g opacity="0">{fade(0.10)}'
             + label(0, 50, s["total"], 52, "e-f", extra=' font-weight="600"')
             + label(0, 72, "contributions in the last year", 12) + '</g>')
    for i, (val, lab) in enumerate([(s["active"], "active days"),
                                    (s["best_week"], "best week")]):
        p.append(f'<g opacity="0">{fade(0.30 + i * 0.12)}'
                 + label(WIDTH, 30 + i * 40, val, 19, "e-f", "end",
                         ' font-weight="600"')
                 + label(WIDTH, 47 + i * 40, lab, 11, "m-f", "end") + '</g>')

    base, top = H - 10, H - 58
    span = base - top
    step = WIDTH / max(len(weekly) - 1, 1)
    pts = [(i * step, base - (v / peak) * span) for i, v in enumerate(weekly)]
    clip, cursor = wipe("rs", 0, top - 6, WIDTH, span + 8, 0.50)
    p.append(clip)
    p.append('<g clip-path="url(#rs)">')
    p.append(f'<path d="M{pts[0][0]:.1f} {base:.1f}'
             + "".join(f'L{x:.1f} {y:.1f}' for x, y in pts)
             + f'L{pts[-1][0]:.1f} {base:.1f}Z" class="w"/>')
    p.append(f'<path d="M{pts[0][0]:.1f} {pts[0][1]:.1f}'
             + "".join(f'L{x:.1f} {y:.1f}' for x, y in pts[1:])
             + f'" class="d-s" stroke-width="2" stroke-linejoin="round" '
             f'stroke-linecap="round"/>')
    p.append("</g>")
    p.append(cursor)
    ex, ey = pts[-1]
    p.append(f'<circle cx="{ex - 2:.1f}" cy="{ey:.1f}" r="4.5" class="e-f r" '
             f'stroke-width="2" opacity="0">{fade(0.50 + REVEAL, 0.35)}</circle>')
    p.append("</svg>")
    return "".join(p)

def draw_streak(s):
    H = 96
    cells = []
    for k, lab in (("current", "current streak"), ("longest", "longest streak")):
        r = s[k]
        span = (f"{pretty(r['start'])} &#8211; {pretty(r['end'])}"
                if r["length"] else "&#8212;")
        cells.append((r["length"], lab, span))

    p = [head(WIDTH, H)]
    mid = WIDTH / 2
    p.append(f'<line x1="{mid:.0f}" y1="16" x2="{mid:.0f}" y2="80" '
             f'class="u-s" stroke-width="1" opacity="0">{fade(0.20)}</line>')
    for i, (val, lab, span) in enumerate(cells):
        x = LEFT if i == 0 else mid + LEFT
        p.append(f'<g opacity="0">{fade(0.12 + i * 0.14)}'
                 + label(x, 44, f"{val}", 34, "e-f", extra=' font-weight="600"')
                 + label(x, 64, lab, 11)
                 + label(x, 80, span, 10) + '</g>')
    p.append("</svg>")
    return "".join(p)

def draw_langs(s):
    rows = max(len(s["by_size"]), len(s["by_repo"]), 1)
    H = 26 + rows * 22 + 6
    colw = (WIDTH - LEFT - 30) / 2
    name_w, bar_max = 82, colw - 82 - 44

    p = [head(WIDTH, H)]
    groups = [(LEFT, "by bytes", s["by_size"], True),
              (LEFT + colw + 30, "by repos", s["by_repo"], False)]
    for gi, (gx, title, data, as_pct) in enumerate(groups):
        p.append(f'<g opacity="0">{fade(0.10 + gi * 0.10)}'
                 + label(gx, 12, title.upper(), 9, "m-f",
                         extra=' letter-spacing="1.3"') + '</g>')
        if not data:
            continue
        top = max(v for _, v in data) or 1
        total = sum(v for _, v in data) or 1
        cid = f"rl{gi}"
        clip, cursor = wipe(cid, gx + name_w, 20, bar_max, rows * 22,
                            0.34 + gi * 0.12, 0.95)
        p.append(clip)
        for ri, (name, val) in enumerate(data):
            y = 26 + ri * 22
            shown = (f"{val / total * 100:.0f}%" if as_pct else f"{val}")
            p.append(f'<g opacity="0">{fade(0.24 + gi * 0.10 + ri * 0.05)}'
                     + label(gx, y + 8, name.lower()[:11], 11, "e-f")
                     + label(gx + colw - 6, y + 8, shown, 11, "m-f", "end")
                     + '</g>')
            p.append(f'<g clip-path="url(#{cid})">'
                     + hbar(gx + name_w, y, bar_max * val / top, 7)
                     + '</g>')
        p.append(cursor)
    p.append("</svg>")
    return "".join(p)

def draw_heading(word):
    FS = 16
    H = 26
    text_end = len(word) * FS * 0.6 + 18
    p = [head(WIDTH, H, font=font_head())]
    p.append(label(0, 18, word, FS, "e-f", extra=' font-weight="600"'))
    p.append(f'<line x1="{text_end:.0f}" y1="12.5" x2="{WIDTH}" y2="12.5" '
             f'class="u-s" stroke-width="1"/>')
    p.append("</svg>")
    return "".join(p)

def draw_year(s):
    FS, LH, COLW = 9.2, 11.0, 2
    CW = FS * 0.6
    pad_l, pad_t = LEFT, 44
    weeks = s["weeks"]
    H = int(pad_t + 7 * LH + 26)

    def level(v):
        for i, cut in enumerate((0, 2, 5, 9)):
            if v <= cut:
                return i
        return 4

    p = [head(WIDTH, H)]
    p.append(f'<g opacity="0">{fade(0.10)}'
             + label(pad_l, 16, "THE YEAR", 9, "m-f",
                     extra=' letter-spacing="1.3"')
             + label(pad_l, 32, f"{s['active']} of "
                     f"{sum(len(w) for w in weeks)} days had a contribution", 11)
             + '</g>')

    lx = WIDTH - 6
    p.append(f'<g opacity="0">{fade(1.30)}'
             + label(lx - 78, 32, "less", 9, "m-f", "end")
             + f'<text xml:space="preserve" x="{lx - 72}" y="32" class="d-f" '
             f'font-size="{FS}">{" ".join(RAMP[1:])}</text>'
             + label(lx, 32, "more", 9, "m-f", "end") + '</g>')

    for r in range(7):
        chars = []
        for w in weeks:
            day = next((d for d in w if d.get("weekday") == r), None)
            v = day["contributionCount"] if day else 0
            chars.append(RAMP[level(v)] * COLW)
        line = "".join(chars).rstrip()
        if not line:
            continue
        y = pad_t + r * LH
        w_px = max(len(line), 1) * CW
        cid = f"ry{r}"
        delay = 0.30 + r * 0.07
        p.append(f'<clipPath id="{cid}"><rect x="{pad_l}" y="{y}" '
                 f'height="{LH}" width="0"><animate attributeName="width" '
                 f'from="0" to="{w_px:.1f}" begin="{delay:.2f}s" dur="0.40s" '
                 f'fill="freeze"/></rect></clipPath>')
        safe = line.replace("&", "&amp;").replace("<", "&lt;")
        p.append(f'<g clip-path="url(#{cid})"><text xml:space="preserve" '
                 f'x="{pad_l}" y="{y + FS - 0.6:.1f}" class="d-f" '
                 f'font-size="{FS}">{safe}</text></g>')

    for r, lab in ((1, "mon"), (3, "wed"), (5, "fri")):
        p.append(label(pad_l - 7, pad_t + r * LH + FS - 0.6, lab, 9, "m-f",
                       "end"))

    last_m, last_x = None, -999.0
    base_y = pad_t + 7 * LH + 13
    for i, w in enumerate(weeks):
        m = int(w[0]["date"][5:7])
        x = pad_l + i * COLW * CW
        if m != last_m and i < len(weeks) - 1 and x - last_x >= 34:
            p.append(label(x, base_y, MON[m - 1], 9, "m-f"))
            last_x = x
        last_m = m

    p.append("</svg>")
    return "".join(p)

# ----------------- LEETCODE STATS -----------------

def fetch_leetcode(username):
    try:
        body = json.dumps({"query": QUERY_LEETCODE, "variables": {"username": username}}).encode()
        req = urllib.request.Request(
            API_LEETCODE, data=body,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            payload = json.load(r)
        data = payload.get("data", {})
        matched = data.get("matchedUser")
        if not matched:
            return None
        all_q = {q["difficulty"]: q["count"] for q in data.get("allQuestionsCount", [])}
        ac = {q["difficulty"]: q["count"] for q in matched.get("submitStatsGlobal", {}).get("acSubmissionNum", [])}
        ranking = matched.get("profile", {}).get("ranking", 0)
        return {
            "ranking": ranking,
            "total_solved": ac.get("All", 0),
            "total_questions": all_q.get("All", 4000),
            "easy_solved": ac.get("Easy", 0),
            "easy_total": all_q.get("Easy", 960),
            "med_solved": ac.get("Medium", 0),
            "med_total": all_q.get("Medium", 2100),
            "hard_solved": ac.get("Hard", 0),
            "hard_total": all_q.get("Hard", 970),
        }
    except Exception as e:
        print(f"LeetCode fetch notice: {e}")
        return None

def draw_leetcode(lc):
    H = 136
    p = [head(WIDTH, H)]
    
    if not lc:
        p.append(f'<g opacity="0">{fade(0.10)}'
                 + label(LEFT, 40, "LEETCODE // PROFILE", 13, "e-f", extra=' font-weight="600"')
                 + label(LEFT, 64, "Problems solved & ranking tracking active", 11, "m-f")
                 + '</g>')
        p.append("</svg>")
        return "".join(p)
    
    # Left Hero: Solved count & Rank
    rank_str = f"global rank #{lc['ranking']:,}" if lc['ranking'] and lc['ranking'] < 5000000 else "leetcode active"
    p.append(f'<g opacity="0">{fade(0.10)}'
             + label(LEFT, 46, f"{lc['total_solved']}", 42, "e-f", extra=' font-weight="600"')
             + label(LEFT, 66, f"solved of {lc['total_questions']}", 11, "m-f")
             + label(LEFT, 86, rank_str, 10, "a-f")
             + '</g>')

    mid_x = 180
    p.append(f'<line x1="{mid_x}" y1="18" x2="{mid_x}" y2="{H-18}" class="u-s" stroke-width="1" opacity="0">{fade(0.20)}</line>')

    diffs = [
        ("Easy", lc["easy_solved"], lc["easy_total"], "#00b8a3"),
        ("Medium", lc["med_solved"], lc["med_total"], "#ffc01e"),
        ("Hard", lc["hard_solved"], lc["hard_total"], "#ef4743"),
    ]
    bar_start_x = mid_x + 80
    bar_max_w = WIDTH - bar_start_x - 70
    
    for i, (name, solved, total, color) in enumerate(diffs):
        y = 30 + i * 32
        pct = (solved / total) if total else 0
        w_val = max(bar_max_w * pct, 2)
        
        p.append(f'<g opacity="0">{fade(0.20 + i * 0.12)}'
                 + label(mid_x + 20, y + 9, name, 11, "e-f")
                 + label(WIDTH - 10, y + 9, f"{solved}/{total}", 11, "m-f", "end")
                 + '</g>')
        
        p.append(f'<rect x="{bar_start_x}" y="{y}" width="{bar_max_w}" height="8" rx="4" class="w"/>')
        
        cid = f"lcbar{i}"
        clip, cursor = wipe(cid, bar_start_x, y, bar_max_w, 8, 0.40 + i * 0.15, 0.8)
        p.append(clip)
        p.append(f'<g clip-path="url(#{cid})">'
                 + f'<rect x="{bar_start_x}" y="{y}" width="{w_val:.1f}" height="8" rx="4" fill="{color}"/>'
                 + '</g>')
        p.append(cursor)

    p.append("</svg>")
    return "".join(p)

# ----------------- RECENT ACTIVITY -----------------

def fetch_recent_activity(login):
    url = f"https://api.github.com/users/{login}/events/public"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            events = json.loads(resp.read().decode("utf-8"))
            for ev in events:
                if ev.get("type") == "PushEvent":
                    repo_name = ev.get("repo", {}).get("name", "")
                    created_at = ev.get("created_at", "")
                    commits = ev.get("payload", {}).get("commits", [])
                    msg = commits[0].get("message", "").split("\n")[0] if commits else "Pushed code"
                    return {"repo": repo_name, "msg": msg, "date": created_at}
    except Exception as e:
        print(f"Events fetch notice: {e}")
    return None

def time_ago(iso_str):
    if not iso_str:
        return "recently"
    try:
        ev_dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - ev_dt
        secs = diff.total_seconds()
        if secs < 3600:
            return f"{int(secs//60)}m ago"
        elif secs < 86400:
            return f"{int(secs//3600)}h ago"
        else:
            return f"{int(secs//86400)}d ago"
    except:
        return "recently"

def draw_activity(act):
    H = 64
    p = [head(WIDTH, H)]
    
    p.append(f'<rect x="0" y="0" width="{WIDTH}" height="{H}" rx="8" class="card-bg card-border" stroke-width="1"/>')
    
    p.append(f'<circle cx="24" cy="{H//2}" r="5" class="g-f">'
             f'<animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/>'
             f'</circle>')
    
    if act:
        repo = act["repo"].replace("Abhinay-code-max/", "")
        msg = (act["msg"][:42] + "...") if len(act["msg"]) > 42 else act["msg"]
        t = time_ago(act["date"])
        p.append(f'<g opacity="0">{fade(0.10)}'
                 + label(42, 28, f"Latest push to {repo}", 12, "e-f", extra=' font-weight="600"')
                 + label(42, 48, f'"{msg}"', 11, "m-f")
                 + label(WIDTH - 18, 38, t, 11, "a-f", "end")
                 + '</g>')
    else:
        p.append(f'<g opacity="0">{fade(0.10)}'
                 + label(42, 38, "Active development across repositories", 11, "e-f")
                 + '</g>')

    p.append("</svg>")
    return "".join(p)

# ----------------- SELF-TYPING TERMINAL -----------------

def draw_terminal():
    W, H = WIDTH, 178
    p = [head(W, H)]
    
    p.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="8" class="card-bg card-border" stroke-width="1"/>')
    
    p.append(f'<path d="M 0 8 Q 0 0 8 0 L {W-8} 0 Q {W} 0 {W} 8 L {W} 28 L 0 28 Z" class="card-bg"/>')
    p.append(f'<line x1="0" y1="28" x2="{W}" y2="28" class="card-border" stroke-width="1"/>')
    
    p.append('<circle cx="16" cy="14" r="5" fill="#ff5f56"/>')
    p.append('<circle cx="32" cy="14" r="5" fill="#ffbd2e"/>')
    p.append('<circle cx="48" cy="14" r="5" fill="#27c93f"/>')
    p.append(label(W//2, 18, "abhinay@core-system: ~ (zsh)", 11, "m-f", "middle"))

    lines = [
        ("$ whoami", "> Abhinay Kandrika [AI &amp; Full-Stack Engineer]", 0.30, 0.60),
        ("$ current_focus", "> Autonomous AI Agents | Scalable Backends | Distributed Web", 1.10, 0.75),
        ("$ status --live", "> [ACTIVE] Shipping fast &amp; building intelligent systems", 2.05, 0.65),
    ]

    for i, (cmd, output, d_cmd, d_out) in enumerate(lines):
        y_cmd = 52 + i * 40
        y_out = 68 + i * 40
        
        cid = f"tcmd{i}"
        w_cmd = len(cmd) * 7.2 + 10
        clip, cursor = wipe(cid, 18, y_cmd - 11, w_cmd, 15, d_cmd, 0.50)
        p.append(clip)
        p.append(f'<g clip-path="url(#{cid})">'
                 + label(18, y_cmd, cmd, 12, "a-f", extra=' font-weight="600"')
                 + '</g>')
        p.append(cursor)
        
        p.append(f'<g opacity="0">{fade(d_cmd + 0.55, 0.40)}'
                 + label(32, y_out, f"↳ {output}", 11, "e-f")
                 + '</g>')

    p.append("</svg>")
    return "".join(p)

# ----------------- MAIN WRITER -----------------

def write(path, svg):
    old = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = f.read()
    if old == svg:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return True

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is not set")
    login = os.environ.get("GH_LOGIN", "Abhinay-code-max")
    lc_user = os.environ.get("LEETCODE_USER", "Abhinay-code-max")
    out_dir = os.environ.get("OUT_DIR", ".")

    user = fetch_github(login, token)
    s = summarise_github(user)
    lc = fetch_leetcode(lc_user)
    act = fetch_recent_activity(login)

    files = {
        "stats.svg": draw_stats(s),
        "streak.svg": draw_streak(s),
        "langs.svg": draw_langs(s),
        "year.svg": draw_year(s),
        "terminal.svg": draw_terminal(),
        "leetcode.svg": draw_leetcode(lc),
        "activity.svg": draw_activity(act),
    }
    
    for word in ("about", "terminal", "stack", "projects", "stats", "leetcode", "activity", "about this page"):
        files[f"hd-{word.replace(' ', '-')}.svg"] = draw_heading(word)

    changed = [n for n, svg in files.items() if write(os.path.join(out_dir, n), svg)]
    print(f"Generated SVGs: {', '.join(sorted(files.keys()))}")
    print(f"Updated: {', '.join(sorted(changed)) if changed else 'no changes'}")

if __name__ == "__main__":
    main()
