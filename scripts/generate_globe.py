#!/usr/bin/env python3
"""
generate_globe.py — Rotating 3D contribution globe for GitHub profile README.

Technique: flat-map-scrolling inside a circular clip creates a convincing
rotating-sphere illusion using only SMIL — no JavaScript, no external deps.
Works inside GitHub README <img> tags (SMIL is preserved by GitHub's CDN).

Output: globe.svg in the repository root.
Workflow: .github/workflows/3d-globe.yml  (runs daily, commits globe.svg)
"""
import json, os, urllib.request
from datetime import datetime, timezone, timedelta

# ── Configuration ─────────────────────────────────────────────────────────────
HYD_LAT, HYD_LON = 17.3850, 78.4867          # Hyderabad, Telangana, India
W,  H   = 300, 308                            # SVG canvas px
CX, CY  = 150, 146                            # Globe centre px
R       = 122                                 # Globe radius px
MAP_W   = R * 2                               # One map-copy width (equirectangular)
MAP_H   = R * 2                               # One map-copy height
ROT     = "22s"                               # Seconds per full 360° rotation

# ── Simplified continent outline dots (lat, lon) ──────────────────────────────
# ~130 carefully-chosen coastline points — recognisable from the India-facing side
LAND = [
    # Africa
    (37,-5),(34,9),(30,32),(22,37),(15,42),(5,41),(-5,40),(-14,38),
    (-20,35),(-30,30),(-35,20),(-33,17),(-25,15),(-18,12),(-5,10),
    (5,3),(12,-15),(18,-16),(25,-15),(32,-10),(35,-5),
    # Arabian / Middle East
    (37,36),(40,27),(24,50),(22,60),(23,57),(12,43),(14,50),(22,59),(24,67),
    # Indian Subcontinent
    (25,68),(22,70),(20,73),(15,73),(8,77),(8,80),(12,80),(20,87),
    (23,90),(22,92),(20,93),
    # India context extras
    (28,73),(26,80),(24,86),(22,88),(24,89),
    # SE Asia / East Asia
    (5,100),(10,99),(16,102),(20,106),(22,114),(25,120),
    (30,122),(35,130),(40,124),(42,130),(48,140),
    # North / Central Asia
    (55,140),(60,150),(60,163),(65,180),(70,178),(72,145),
    (73,120),(75,95),(77,75),(73,55),(65,30),
    (70,55),(70,75),(70,95),(70,115),(68,140),
    # Europe
    (70,25),(65,15),(60,5),(55,8),(51,2),(47,-2),(43,-9),
    (36,-5),(38,15),(43,15),(45,13),(47,24),(55,21),(60,24),(65,25),
    # North America
    (71,-156),(60,-165),(55,-130),(50,-128),(48,-124),(40,-124),
    (35,-120),(28,-110),(22,-97),(18,-88),(25,-80),(30,-81),
    (35,-75),(42,-70),(50,-55),(55,-59),(60,-65),(65,-80),
    (70,-95),(72,-120),(70,-135),(65,-170),
    # South America
    (12,-72),(8,-62),(5,-52),(0,-50),(-5,-35),(-12,-37),
    (-20,-40),(-30,-50),(-38,-57),(-45,-65),(-55,-68),
    (-50,-73),(-42,-72),(-30,-70),(-18,-70),(-5,-80),(0,-78),
    # Australia
    (-15,130),(-18,140),(-25,153),(-32,153),(-38,147),
    (-40,144),(-35,138),(-32,115),(-22,113),(-12,135),
    # Antarctica (sparse)
    (-70,0),(-73,30),(-75,60),(-73,90),(-75,120),
    (-73,150),(-70,170),(-65,100),(-67,40),(-65,-20),
]

# ── GitHub GraphQL ────────────────────────────────────────────────────────────
GRAPHQL = "https://api.github.com/graphql"
QUERY   = """
query($login:String!,$from:DateTime!,$to:DateTime!){
  user(login:$login){
    contributionsCollection(from:$from,to:$to){
      contributionCalendar{
        totalContributions
        weeks{contributionDays{contributionCount date}}
      }
    }
  }
}
"""

def fetch(token, login):
    today = datetime.now(timezone.utc).date()
    since = today - timedelta(days=364)
    body  = json.dumps({
        "query": QUERY,
        "variables": {
            "login": login,
            "from": f"{since.isoformat()}T00:00:00Z",
            "to":   f"{today.isoformat()}T23:59:59Z",
        }
    }).encode()
    req = urllib.request.Request(GRAPHQL, data=body, headers={
        "Authorization": f"bearer {token}",
        "Content-Type":  "application/json",
        "User-Agent":    f"{login}-globe",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], cal["weeks"]

def streak(weeks):
    days = [d for w in weeks for d in w["contributionDays"]]
    s = 0
    for d in reversed(days):
        if d["contributionCount"] > 0:
            s += 1
        elif s:
            break
    return s

# ── Coordinate helpers ────────────────────────────────────────────────────────
def ll(lat, lon):
    """Equirectangular: (lat, lon) -> (x, y) on one map copy."""
    x = (lon + 180) / 360 * MAP_W
    y = (90  - lat)  / 180 * MAP_H
    return x, y

# ── SVG generator ─────────────────────────────────────────────────────────────
def build_svg(total, cur_streak):
    # Pulse intensity scales with contribution volume
    if total >= 500:   pdur, pr = "1.2s", 9
    elif total >= 200: pdur, pr = "1.8s", 8
    elif total >= 50:  pdur, pr = "2.5s", 7
    else:              pdur, pr = "3.0s", 6
    pb = f"{float(pdur[:-1]) / 2:.2f}s"    # second-ring phase offset

    hx, hy = ll(HYD_LAT, HYD_LON)          # Hyderabad on the map

    # Scroll group offset: start with Hyderabad centred on globe
    sx   = CX - hx                          # translate-x at t=0
    sx2  = sx  - MAP_W                      # translate-x after one full revolution
    my   = CY  - MAP_H / 2                  # vertical centre-align

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" '
         f'width="{W}" height="{H}" viewBox="0 0 {W} {H}">']

    # ─ Defs ───────────────────────────────────────────────────────────────────
    p.append(f'''<defs>
  <radialGradient id="sph" cx="36%" cy="30%" r="68%">
    <stop offset="0%"   stop-color="#1e3a6e"/>
    <stop offset="45%"  stop-color="#0d1f40"/>
    <stop offset="100%" stop-color="#040810"/>
  </radialGradient>
  <radialGradient id="shn" cx="33%" cy="26%" r="42%">
    <stop offset="0%"   stop-color="#ffffff" stop-opacity="0.14"/>
    <stop offset="100%" stop-color="transparent"/>
  </radialGradient>
  <clipPath id="gc"><circle cx="{CX}" cy="{CY}" r="{R}"/></clipPath>
  <filter id="hg" x="-200%" y="-200%" width="500%" height="500%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>''')

    # ─ Sphere base ────────────────────────────────────────────────────────────
    p.append(f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="url(#sph)"/>')

    # ─ Scrolling map (clipped to sphere) ─────────────────────────────────────
    p.append(f'<g clip-path="url(#gc)">')
    p.append(f'<g transform="translate({sx:.2f},{my:.2f})">'
             f'<animateTransform attributeName="transform" type="translate" '
             f'from="{sx:.2f},{my:.2f}" to="{sx2:.2f},{my:.2f}" '
             f'dur="{ROT}" repeatCount="indefinite" calcMode="linear"/>')

    for cp in range(2):
        ox = cp * MAP_W

        # Latitude lines
        for lat in range(-80, 91, 15):
            eq = (lat == 0)
            y  = (90 - lat) / 180 * MAP_H
            sc = "#58a6ff" if eq else "#1f6feb"
            sw = "1"       if eq else "0.4"
            so = "0.65"    if eq else "0.28"
            p.append(f'<line x1="{ox:.1f}" y1="{y:.1f}" '
                     f'x2="{ox+MAP_W:.1f}" y2="{y:.1f}" '
                     f'stroke="{sc}" stroke-width="{sw}" stroke-opacity="{so}"/>')

        # Longitude lines
        for lon in range(-180, 181, 15):
            pm = (lon == 0)
            x  = (lon + 180) / 360 * MAP_W + ox
            sc = "#58a6ff" if pm else "#1f6feb"
            sw = "1"       if pm else "0.4"
            so = "0.65"    if pm else "0.28"
            p.append(f'<line x1="{x:.1f}" y1="0" '
                     f'x2="{x:.1f}" y2="{MAP_H:.1f}" '
                     f'stroke="{sc}" stroke-width="{sw}" stroke-opacity="{so}"/>')

        # Continent dots
        for lat, lon in LAND:
            dx, dy = ll(lat, lon)
            p.append(f'<circle cx="{dx+ox:.1f}" cy="{dy:.1f}" '
                     f'r="1.6" fill="#2d7ec4" fill-opacity="0.72"/>')

        # ─ Hyderabad marker ───────────────────────────────────────────────────
        mx_, my_ = hx + ox, hy

        # Pulse ring A (immediate)
        p.append(f'<circle cx="{mx_:.1f}" cy="{my_:.1f}" r="3.8" '
                 f'fill="none" stroke="#ff6b35" stroke-width="1.8">'
                 f'<animate attributeName="r" from="3.8" to="{pr}" '
                 f'dur="{pdur}" repeatCount="indefinite"/>'
                 f'<animate attributeName="stroke-opacity" from="0.9" to="0" '
                 f'dur="{pdur}" repeatCount="indefinite"/></circle>')

        # Pulse ring B (half-phase offset)
        p.append(f'<circle cx="{mx_:.1f}" cy="{my_:.1f}" r="3.8" '
                 f'fill="none" stroke="#ff9944" stroke-width="1">'
                 f'<animate attributeName="r" from="3.8" to="{pr}" '
                 f'dur="{pdur}" begin="{pb}" repeatCount="indefinite"/>'
                 f'<animate attributeName="stroke-opacity" from="0.6" to="0" '
                 f'dur="{pdur}" begin="{pb}" repeatCount="indefinite"/></circle>')

        # Solid pin dot
        p.append(f'<circle cx="{mx_:.1f}" cy="{my_:.1f}" '
                 f'r="3.8" fill="#ff6b35" filter="url(#hg)"/>')

        # "HYD" label
        p.append(f'<text x="{mx_+5.5:.1f}" y="{my_-4:.1f}" '
                 f'font-family="monospace" font-size="7.5" '
                 f'font-weight="700" fill="#ffaa77">HYD</text>')

    p.append('</g></g>')  # close scroll group + clip group

    # ─ Atmosphere ─────────────────────────────────────────────────────────────
    p.append(f'<circle cx="{CX}" cy="{CY}" r="{R+10}" fill="none" '
             f'stroke="#1f6feb" stroke-width="10" stroke-opacity="0.12"/>')
    p.append(f'<circle cx="{CX}" cy="{CY}" r="{R+2}" fill="none" '
             f'stroke="#58a6ff" stroke-width="1.5" stroke-opacity="0.35"/>')
    p.append(f'<circle cx="{CX}" cy="{CY}" r="{R+0.5}" fill="none" '
             f'stroke="#ffffff" stroke-width="0.5" stroke-opacity="0.12"/>')

    # ─ Specular highlight ──────────────────────────────────────────────────────
    p.append(f'<circle cx="{CX}" cy="{CY}" r="{R}" fill="url(#shn)"/>')

    # ─ Stats overlay ──────────────────────────────────────────────────────────
    ty = CY + R + 16
    p.append(f'<text x="{CX}" y="{ty}" font-family="monospace" font-size="11.5" '
             f'font-weight="600" fill="#58a6ff" text-anchor="middle">'
             f'{total:,} contributions</text>')
    p.append(f'<text x="{CX}" y="{ty+15}" font-family="monospace" font-size="9" '
             f'fill="#8b949e" text-anchor="middle">'
             f'streak {cur_streak}  ·  Hyderabad, IN</text>')

    p.append('</svg>')
    return '\n'.join(p)

# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    token = os.environ.get("GITHUB_TOKEN")
    login = os.environ.get("GH_LOGIN", "Abhinay-code-max")

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path  = os.path.join(repo_root, "globe.svg")

    if token:
        print(f"Fetching contributions for {login}...")
        total, weeks = fetch(token, login)
        cur = streak(weeks)
        print(f"  total={total}, streak={cur}")
    else:
        print("No GITHUB_TOKEN — placeholder globe (total=0, streak=0)")
        total, cur = 0, 0

    svg = build_svg(total, cur)

    old = ""
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            old = f.read()
    if svg == old:
        print("globe.svg unchanged — skipping write")
        return
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {out_path}  ({len(svg):,} bytes)")

if __name__ == "__main__":
    main()
