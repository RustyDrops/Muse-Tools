#!/usr/bin/env python3
"""Build a hand-drawn story animation scene (single HTML file) from Gemini-drafted SVG art.

The art file must contain two groups: id="bearBed" (hero character) and id="owlTree"
(second character / set piece), plus optional id="bearEyesOpen" / id="bearEyesClosed"
groups inside the hero group for the sleepy eye swap. See PROMPTS.md for the prompt
that produces art in this shape.

Usage:
  build_scene.py --art gemini-art.svg --out scene.html [--frame slight|none]
                 [--cap1 "..."] [--cap2 "..."] [--cap3 "..."]
                 [--bub1 "line1|line2"] [--bub2 "line1|line2"]

Sizes: the scene is authored at 540x960 (9:16). render_frames.py --scale 2 renders
the production 1080x1920 version from the same file; SVG scales cleanly.
Frame: "paper" (default, Rusty's pick 2026-11-26) is a cream book-page matte.
"slight" is a thin wobbly inner line; Rusty ruled it does not go with the video.
Keep all art inside x 30..510, y 30..930 (the art prompt enforces it).
"""
import argparse, os, sys

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<style>
  html,body{margin:0;padding:0;background:#141c36;overflow:hidden}
  #stage{width:540px;height:960px;position:relative}
  svg{display:block}
  .cap{font-family:"Segoe Print","Comic Sans MS",cursive;font-weight:700;fill:#f3e9cf;text-anchor:middle}
  .bub{font-family:"Segoe Print","Comic Sans MS",cursive;font-weight:700;fill:#2b2118;text-anchor:middle}
</style></head>
<body><div id="stage">
<svg id="s" width="540" height="960" viewBox="0 0 540 960" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#141c36"/><stop offset="0.55" stop-color="#1e2b4c"/><stop offset="1" stop-color="#2a3a63"/>
    </linearGradient>
    <radialGradient id="halo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#fff5c8" stop-opacity="0.35"/><stop offset="1" stop-color="#fff5c8" stop-opacity="0"/>
    </radialGradient>
    <filter id="rough" x="-5%" y="-5%" width="110%" height="110%">
      <feTurbulence id="turb" type="fractalNoise" baseFrequency="0.015" numOctaves="2" seed="1" result="n"/>
      <feDisplacementMap in="SourceGraphic" in2="n" scale="3"/>
    </filter>
    <filter id="grainF"><feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="2" seed="7" result="n"/><feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0.6 0.6 0.6 0 0"/></filter>
  </defs>
  <rect x="0" y="0" width="540" height="960" fill="url(#sky)"/>
  <g filter="url(#rough)" id="world">
    <circle id="moonHalo" cx="445" cy="130" r="105" fill="url(#halo)"/>
    <path id="moon" d="M462 52 C424 66 402 102 410 142 C418 180 450 204 488 200 C458 184 442 158 444 126 C446 96 458 70 478 56 C473 50 468 49 462 52 Z" fill="#fff2b2" stroke="#e8d588" stroke-width="3" stroke-linejoin="round"/>
    <g id="stars"></g>
    <path id="ground" d="M0 560 C120 522 250 592 380 552 C450 532 505 544 540 556 V960 H0 Z" fill="#2a4433"/>
    <path d="M0 560 C120 522 250 592 380 552 C450 532 505 544 540 556" fill="none" stroke="#3f634b" stroke-width="5"/>
    <g id="artTree">__ART_TREE__</g>
    <g id="artBear">__ART_BEAR__</g>
    <g id="bub1" opacity="0">
      <path d="M276 470 C270 428 322 402 382 408 C438 413 466 442 460 478 C454 516 398 534 338 528 C288 523 280 502 276 470 Z M306 522 L292 560 L330 528" fill="#f7f0dd" stroke="#2b2118" stroke-width="3" stroke-linejoin="round"/>
      <text class="bub" x="368" y="462" font-size="29">__BUB1A__</text>
      <text class="bub" x="368" y="496" font-size="29">__BUB1B__</text>
    </g>
    <g id="bub2" opacity="0">
      <path d="M60 268 C54 226 106 200 166 206 C222 211 250 240 244 276 C238 314 182 332 122 326 C72 321 64 300 60 268 Z M196 322 L214 360 L228 318" fill="#f7f0dd" stroke="#2b2118" stroke-width="3" stroke-linejoin="round"/>
      <text class="bub" x="152" y="260" font-size="26">__BUB2A__</text>
      <text class="bub" x="152" y="294" font-size="26">__BUB2B__</text>
    </g>
  </g>
  <rect id="grain" x="0" y="0" width="540" height="960" filter="url(#grainF)" opacity="0.10"/>
  __FRAME__
  <text id="cap1" class="cap" x="270" y="886" font-size="29">__CAP1__</text>
  <text id="cap2" class="cap" x="270" y="886" font-size="25" opacity="0">__CAP2__</text>
  <text id="cap3" class="cap" x="270" y="886" font-size="27" opacity="0">__CAP3__</text>
</svg>
</div>
<script>
(function(){
  var seed=42; function rnd(){seed=(seed*1103515245+12345)%2147483648;return seed/2147483648;}
  var g=document.getElementById('stars'), NS='http://www.w3.org/2000/svg';
  var starData=[];
  for(var i=0;i<34;i++){
    var x=26+rnd()*480, y=36+rnd()*430, tier=rnd();
    var p=document.createElementNS(NS,'path');
    if(tier<0.14){ var r=11+rnd()*5; p.setAttribute('d','M'+x+' '+(y-r)+' L'+(x+r*0.25)+' '+(y-r*0.25)+' L'+(x+r)+' '+y+' L'+(x+r*0.25)+' '+(y+r*0.25)+' L'+x+' '+(y+r)+' L'+(x-r*0.25)+' '+(y+r*0.25)+' L'+(x-r)+' '+y+' L'+(x-r*0.25)+' '+(y-r*0.25)+' Z'); p.setAttribute('fill','#ffe79a'); }
    else if(tier<0.5){ var r2=6+rnd()*4; p.setAttribute('d','M'+x+' '+(y-r2)+' L'+(x+r2*0.3)+' '+(y-r2*0.3)+' L'+(x+r2)+' '+y+' L'+(x+r2*0.3)+' '+(y+r2*0.3)+' L'+x+' '+(y+r2)+' L'+(x-r2*0.3)+' '+(y+r2*0.3)+' L'+(x-r2)+' '+y+' L'+(x-r2*0.3)+' '+(y-r2*0.3)+' Z'); p.setAttribute('fill','#fff5c8'); }
    else { p.setAttribute('d','M'+x+' '+y+' h3 v3 h-3 Z'); p.setAttribute('fill','#7a8cae'); }
    p.setAttribute('opacity','0'); g.appendChild(p); starData.push(p);
  }
  function clamp(v){return v<0?0:v>1?1:v;}
  function ease(v){return 1-Math.pow(1-v,2);}
  window.renderAt=function(t){
    var boil=Math.floor(t*8);
    document.getElementById('turb').setAttribute('seed', String(1+(boil%3)));
    document.getElementById('world').setAttribute('transform','rotate('+(boil%2?0.15:-0.15)+' 270 480)');
    document.getElementById('moon').setAttribute('opacity', String(ease(clamp((t-0.2)/1.2))));
    document.getElementById('moonHalo').setAttribute('opacity', String(ease(clamp((t-0.4)/1.4))*(0.85+0.15*Math.sin(t*1.3))));
    starData.forEach(function(p,i){
      var on=clamp((t-(0.5+i*0.07))/0.3);
      var tw=0.7+0.3*Math.sin(t*2.2+i*1.9);
      var dim=t>13?clamp(1-(t-13-i*0.03)/0.6):1;
      p.setAttribute('opacity', String(on*tw*Math.max(0.2,dim)));
    });
    var tree=document.getElementById('artTree'); if(tree) tree.setAttribute('opacity', String(ease(clamp((t-2.6)/1.6))));
    var owl=document.getElementById('ot-owl'); if(owl){ owl.setAttribute('opacity', String(ease(clamp((t-8.8)/1.2)))); }
    var bear=document.getElementById('artBear'); if(bear) bear.setAttribute('opacity', String(ease(clamp((t-4.6)/1.4))));
    var eo=document.getElementById('bearEyesOpen'), ec=document.getElementById('bearEyesClosed');
    if(eo) eo.setAttribute('opacity', (t<5.6||t>13.2)?'0':'1');
    if(ec) ec.setAttribute('opacity', t>13.2?'1':'0');
    function bub(id,s,e){var o=clamp((t-s)/0.35)*(t>e?clamp(1-(t-e)/0.35):1);document.getElementById(id).setAttribute('opacity',String(o));}
    bub('bub1',6.8,8.8); bub('bub2',10.6,12.8);
    document.getElementById('cap1').setAttribute('opacity', t<5?'1':'0');
    document.getElementById('cap2').setAttribute('opacity', (t>=5&&t<10.4)?'1':'0');
    document.getElementById('cap3').setAttribute('opacity', t>=10.4?'1':'0');
  };
  window.renderAt(0);
  window.__ready=true;
})();
</script>
</body></html>
"""

FRAME_SLIGHT = """<rect x="6" y="6" width="528" height="948" fill="none" stroke="#0d1322" stroke-width="5" opacity="0.6"/>
  <path d="M16 17 C170 11 350 22 524 15 C529 300 519 640 525 943 C350 950 170 938 17 945 C12 650 22 320 16 17 Z" fill="none" stroke="#f3e9cf" stroke-width="2.5" opacity="0.45"/>"""

FRAME_PAPER = """<rect x="0" y="0" width="540" height="960" fill="none" stroke="#f3e9cf" stroke-width="46"/>
  <rect x="24" y="24" width="492" height="912" fill="none" stroke="#2b2118" stroke-width="2" opacity="0.35"/>"""

FRAMES = {"slight": FRAME_SLIGHT, "paper": FRAME_PAPER, "none": ""}


def split_art(art):
    bear_start = art.index('<g id="bearBed">')
    tree_start = art.index('<g id="owlTree">')
    return art[bear_start:tree_start].rstrip(), art[tree_start:]


def two_lines(s):
    parts = s.split("|")
    return parts[0], (parts[1] if len(parts) > 1 else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frame", choices=["paper", "slight", "none"], default="paper")
    ap.add_argument("--cap1", default="Bramble could not sleep.")
    ap.add_argument("--cap2", default="He counted stars. They winked back.")
    ap.add_argument("--cap3", default="Just listen. The night is singing.")
    ap.add_argument("--bub1", default="I can&#8217;t|sleep!")
    ap.add_argument("--bub2", default="Sleep is|just shy.")
    a = ap.parse_args()
    art = open(a.art).read()
    bear, tree = split_art(art)
    b1a, b1b = two_lines(a.bub1)
    b2a, b2b = two_lines(a.bub2)
    html = (TEMPLATE.replace("__ART_BEAR__", bear).replace("__ART_TREE__", tree)
            .replace("__FRAME__", FRAMES[a.frame])
            .replace("__CAP1__", a.cap1).replace("__CAP2__", a.cap2).replace("__CAP3__", a.cap3)
            .replace("__BUB1A__", b1a).replace("__BUB1B__", b1b)
            .replace("__BUB2A__", b2a).replace("__BUB2B__", b2b))
    open(a.out, "w").write(html)
    print("wrote", a.out, len(html), "bytes, frame:", a.frame)


if __name__ == "__main__":
    main()
