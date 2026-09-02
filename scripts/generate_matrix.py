#!/usr/bin/env python3
"""
generate_matrix.py — Generates an animated Matrix Binary Rain SVG banner (1s and 0s)
matching the cyberpunk matrix digital rain aesthetic for GitHub profile README.
Pure SMIL animation — runs on GitHub CDN without JavaScript.
"""
import random, os

def build_matrix_svg(width=620, height=130):
    random.seed(1337)  # Deterministic cyberpunk seed
    cols = 52
    col_width = width / cols
    
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none">')
    
    # Defs
    svg.append(f'''<defs>
  <linearGradient id="m-bg" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" stop-color="#010803" />
    <stop offset="50%" stop-color="#021206" />
    <stop offset="100%" stop-color="#010803" />
  </linearGradient>
  <linearGradient id="m-fade" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" stop-color="#010803" stop-opacity="0.85" />
    <stop offset="18%" stop-color="#010803" stop-opacity="0" />
    <stop offset="82%" stop-color="#010803" stop-opacity="0" />
    <stop offset="100%" stop-color="#010803" stop-opacity="0.85" />
  </linearGradient>
  <filter id="m-glow" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="1.6" result="blur" />
    <feMerge>
      <feMergeNode in="blur" />
      <feMergeNode in="SourceGraphic" />
    </feMerge>
  </filter>
  <clipPath id="m-clip">
    <rect width="{width}" height="{height}" rx="8" />
  </clipPath>
</defs>''')

    # Card background
    svg.append(f'<rect width="{width}" height="{height}" rx="8" fill="url(#m-bg)" stroke="#00ff66" stroke-opacity="0.3" stroke-width="1" />')
    
    # Clipped Matrix Rain streams
    svg.append('<g clip-path="url(#m-clip)">')
    
    font_size = 10.5
    line_spacing = 12
    
    for c in range(cols):
        x = c * col_width + (col_width / 2)
        stream_len = random.randint(12, 24)
        dur = random.uniform(2.2, 4.8)
        delay = random.uniform(0.0, 3.8)
        stream_height = stream_len * line_spacing
        
        y_start = -stream_height
        y_end = height + 30
        
        chars = [random.choice(["1", "0"]) for _ in range(stream_len)]
        
        svg.append(f'<g font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="{font_size}" text-anchor="middle">')
        svg.append(f'  <animateTransform attributeName="transform" type="translate" from="0,{y_start:.1f}" to="0,{y_end:.1f}" dur="{dur:.2f}s" begin="{delay:.2f}s" repeatCount="indefinite" />')
        
        for idx, ch in enumerate(chars):
            y_pos = idx * line_spacing
            
            # Head of stream (bright neon white/green)
            if idx == stream_len - 1:
                color = "#ffffff"
                opacity = 0.98
                glow = ' filter="url(#m-glow)" font-weight="700"'
            elif idx == stream_len - 2:
                color = "#bbf7d0"
                opacity = 0.92
                glow = ' filter="url(#m-glow)" font-weight="700"'
            elif idx >= stream_len - 5:
                color = "#00ff66"
                opacity = 0.80
                glow = ''
            elif idx >= stream_len - 10:
                color = "#00cc55"
                opacity = 0.55
                glow = ''
            elif idx >= stream_len - 16:
                color = "#008833"
                opacity = 0.35
                glow = ''
            else:
                color = "#004d1f"
                opacity = max(0.12, (idx / stream_len) * 0.25)
                glow = ''
                
            svg.append(f'  <text x="{x:.1f}" y="{y_pos:.1f}" fill="{color}" fill-opacity="{opacity:.2f}"{glow}>{ch}</text>')
            
        svg.append('</g>')

    # Fade overlay at top and bottom edges
    svg.append(f'<rect width="{width}" height="{height}" fill="url(#m-fade)" pointer-events="none" />')

    # Centered floating HUD pill for readability & cyberpunk aesthetics
    badge_w = 460
    badge_h = 36
    bx = (width - badge_w) / 2
    by = (height - badge_h) / 2
    
    svg.append(f'''
    <!-- Cyberpunk System HUD -->
    <rect x="{bx}" y="{by}" width="{badge_w}" height="{badge_h}" rx="6" fill="#020904" fill-opacity="0.88" stroke="#00ff66" stroke-opacity="0.55" stroke-width="1" />
    <circle cx="{bx + 16}" cy="{by + badge_h/2}" r="4" fill="#00ff66" filter="url(#m-glow)">
      <animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite" />
    </circle>
    <text x="{bx + 28}" y="{by + 22}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11" font-weight="700" fill="#00ff66" letter-spacing="1.2">SYSTEM // MATRIX BINARY STREAM [ONLINE]</text>
    <text x="{bx + badge_w - 14}" y="{by + 22}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="9.5" font-weight="600" fill="#86efac" text-anchor="end">01000001 01001011</text>
    ''')

    svg.append('</g>')
    svg.append('</svg>')
    return '\n'.join(svg)

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(repo_root, "matrix_banner.svg")
    svg_content = build_matrix_svg()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated {out_path} ({len(svg_content):,} bytes)")

if __name__ == "__main__":
    main()
