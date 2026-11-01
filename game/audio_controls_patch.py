#!/usr/bin/env python3
"""Patch the existing v0.2 single-screen Phaser prototype in place.

No sprite/layout assets are recreated. Used by the Android build after
reassembling websrc/part_*.txt. Also works on the original browser HTML.
"""
from pathlib import Path
import re
import sys

AUDIO = r'''
// Tiny Web Audio effects: no remote audio assets; unlocked by the first touch.
const SFX=(()=>{
  const Ctx=window.AudioContext||window.webkitAudioContext;
  let context=null,mix=null,ambience=null;
  let enabled=true;
  let prevStep=0,prevFocus=0;
  try{enabled=localStorage.getItem('kiira_sound')!=='off'}catch(_e){}
  function setup(){
    if(!enabled||!Ctx)return;
    try{
      if(!context){
        context=new Ctx();mix=context.createGain();mix.gain.value=.17;mix.connect(context.destination);
        const hum=context.createOscillator(),g=context.createGain();
        hum.type='sine';hum.frequency.value=58;g.gain.value=.018;
        hum.connect(g);g.connect(mix);hum.start();ambience=g;
      }
      if(context.state==='suspended')context.resume().catch(()=>{});
      if(ambience)ambience.gain.setTargetAtTime(enabled?.018:0,context.currentTime,.08);
    }catch(_e){}
  }
  function pulse(f,to,d,v,type='sine',offset=0){
    if(!context||context.state!=='running'||!enabled)return;
    const t=context.currentTime+offset;
    const o=context.createOscillator(),g=context.createGain();
    o.type=type;
    o.frequency.setValueAtTime(Math.max(20,f),t);
    o.frequency.exponentialRampToValueAtTime(Math.max(20,to),t+d);
    g.gain.setValueAtTime(.0001,t);
    g.gain.exponentialRampToValueAtTime(Math.max(.0002,v),t+.008);
    g.gain.exponentialRampToValueAtTime(.0001,t+d);
    o.connect(g);g.connect(mix);o.start(t);o.stop(t+d+.015);
  }
  function play(event){
    if(!enabled||!context||context.state!=='running')return;
    const now=performance.now();
    switch(event){
      case 'jump':pulse(230,600,.16,.26,'triangle');break;
      case 'land':pulse(150,65,.13,.21,'triangle');pulse(480,160,.065,.06,'square');break;
      case 'step':if(now-prevStep>260){prevStep=now;pulse(105,62,.066,.056,'triangle')}break;
      case 'spark':pulse(690,1040,.13,.22,'sine');pulse(880,1320,.17,.16,'sine',.08);break;
      case 'focus':if(now-prevFocus>350){prevFocus=now;pulse(410,500,.07,.075,'sine')}break;
      case 'charged':pulse(250,700,.24,.19,'triangle');pulse(650,1020,.22,.13,'sine',.11);break;
      case 'expire':pulse(320,125,.17,.12,'triangle');break;
      case 'crumble':pulse(125,43,.24,.21,'sawtooth');break;
      case 'respawn':pulse(320,85,.28,.17,'sine');break;
    }
  }
  function toggle(){
    enabled=!enabled;
    try{localStorage.setItem('kiira_sound',enabled?'on':'off')}catch(_e){}
    if(enabled)setup();
    if(context&&ambience)ambience.gain.setTargetAtTime(enabled?.018:0,context.currentTime,.08);
    const b=document.getElementById('soundToggle');
    if(b)b.textContent=enabled?'ЗВУК: ВКЛ':'ЗВУК: ВЫКЛ';
  }
  document.addEventListener('pointerdown',setup,{capture:true});
  document.addEventListener('keydown',setup,{capture:true});
  document.getElementById('soundToggle').addEventListener('click',toggle);
  document.getElementById('soundToggle').textContent=enabled?'ЗВУК: ВКЛ':'ЗВУК: ВЫКЛ';
  return {play,setup,toggle};
})();
'''

RING_CSS='''#scanRing{position:absolute;right:1.4%;bottom:2%;width:min(23vw,146px);height:min(23vw,146px);max-height:33vh;max-width:33vh;aspect-ratio:1;border:2px solid #ff91d0b5;border-radius:50%;background:#34113b75;box-shadow:0 0 17px #dc29a44b inset,0 0 17px #ff32ba4e;pointer-events:auto;touch-action:none;overflow:visible}
#scanRing:before{content:'СЕНСОР';position:absolute;top:-22px;left:50%;transform:translateX(-50%);color:#ffd2f3;font:11px Arial;white-space:nowrap;pointer-events:none}
#scanRing:after{content:'';position:absolute;left:calc(50% + var(--ax, 34px));top:calc(50% + var(--ay, -3px));width:11px;height:11px;border-radius:50%;transform:translate(-50%,-50%);background:#fbadf0;box-shadow:0 0 12px 2px #ff4ad3;pointer-events:none}
#jump{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:46%;height:46%;border-radius:50%;border:2px solid #ffb9e7;background:#752d75e8;color:#fff;font:bold clamp(10px,1.6vw,14px) Arial;box-shadow:0 0 16px #f13ca77a;pointer-events:auto;touch-action:none}
'''

RING_JS='''// Movement and aiming are separate to avoid double-use of the left thumb.
stick('move',(x,y,strength)=>{
 control.move=Math.abs(x)>.13?x:0;
},()=>control.move=0);
const scanRing=document.getElementById('scanRing');
let scanPointer=null;
function aimFromRing(e){
 const b=scanRing.getBoundingClientRect();
 const dx=e.clientX-b.left-b.width/2,dy=e.clientY-b.top-b.height/2;
 if(Math.hypot(dx,dy)<12)return;
 const angle=Math.atan2(dy,dx);
 control.angle=angle;
 const r=Math.min(b.width,b.height)*.39;
 scanRing.style.setProperty('--ax',(Math.cos(angle)*r)+'px');
 scanRing.style.setProperty('--ay',(Math.sin(angle)*r)+'px');
}
scanRing.addEventListener('pointerdown',e=>{
 if(e.target.id==='jump')return;
 e.preventDefault();scanPointer=e.pointerId;
 scanRing.setPointerCapture(e.pointerId);aimFromRing(e);
});
scanRing.addEventListener('pointermove',e=>{
 if(e.pointerId===scanPointer){e.preventDefault();aimFromRing(e)}
});
function endAim(e){if(e.pointerId===scanPointer)scanPointer=null}
scanRing.addEventListener('pointerup',endAim);
scanRing.addEventListener('pointercancel',endAim);
'''

def one(src, old, new, label):
    count = src.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one anchor, found {count}')
    return src.replace(old, new, 1)


def patch(html):
    if 'const SFX=(()=>' in html:
        raise RuntimeError('Sound patch already applied; refusing duplicate')
    html, n = re.subn(r'#jump\{[^}]*\}', RING_CSS.strip(), html, count=1)
    if n!=1:raise RuntimeError('Jump button CSS not found')
    html = one(html,'#jump{bottom:11%}', '#scanRing{bottom:7%}', 'portrait CSS')
    html = one(html,'<div id="move" class="pad" data-label="СКАНЕР / ХОД"></div><button id="jump">ПРЫЖОК</button>',
               '<div id="move" class="pad" data-label="ХОД"></div><div id="scanRing"><button id="jump" type="button">ПРЫЖОК</button></div>', 'controls markup')
    html = one(html,'<button id="reset">', '<button id="soundToggle" type="button">ЗВУК: ВКЛ</button> <button id="reset">', 'settings markup')
    html = one(html,'const control={move:0,angle:-0.10,jumpQueued:false};',AUDIO+'\nconst control={move:0,angle:-0.10,jumpQueued:false};','sound init')
    start = html.index("stick('move',(x,y,strength)=>{")
    end = html.index('// На Android долгие касания',start)
    html=html[:start]+RING_JS+html[end:]
    html = one(html, "document.getElementById('jump').addEventListener('pointerdown',e=>{e.preventDefault();control.jumpQueued=true});",
               "document.getElementById('jump').addEventListener('pointerdown',e=>{e.preventDefault();e.stopPropagation();control.jumpQueued=true});", 'jump bubble')
    html = one(html,"if(this.stateTime>=85){body.setVelocityY(-params.jump);this.setState('rise');}",
               "if(this.stateTime>=85){body.setVelocityY(-params.jump);SFX.play('jump');this.setState('rise');}",'jump impulse')
    html = one(html,"else if(!this.previousGround){this.setState('land');this.fixedJumpPose(1)}",
               "else if(!this.previousGround){SFX.play('land');this.setState('land');this.fixedJumpPose(1)}",'landing')
    html = one(html,"else if(this.state==='idle'||this.state==='run'||this.state==='fall'||this.state==='rise')this.setState(Math.abs(axis)>.12?'run':'idle');",
               "else if(this.state==='idle'||this.state==='run'||this.state==='fall'||this.state==='rise')this.setState(Math.abs(axis)>.12?'run':'idle');", 'idle unchanged')
    html = one(html,"control.jumpQueued=false;\n if(this.state==='push'||this.state==='land')grounded=true;",
               "control.jumpQueued=false;\n if(grounded&&this.state==='run'&&Math.abs(axis)>.15)SFX.play('step');\n if(this.state==='push'||this.state==='land')grounded=true;",'steps')
    html = one(html,"if(this.actor.y>575)this.respawnToStart();",
               "if(this.actor.y>575){SFX.play('respawn');this.respawnToStart();}",'respawn')
    html = one(html,"if(lit){p.progress=Math.min(1,p.progress+dt*1.7);this.aimed=p;if(p.progress>=1){p.active=true;if(p.type==='timed')p.remaining=3.3}}",
               "if(lit){if(!p.active&&p.progress<.01)SFX.play('focus');p.progress=Math.min(1,p.progress+dt*1.7);this.aimed=p;if(p.progress>=1){if(!p.active)SFX.play('charged');p.active=true;if(p.type==='timed')p.remaining=3.3}}",'bridge charge')
    html = one(html,"if(p.remaining<=0){p.active=false;p.progress=0}",
               "if(p.remaining<=0){p.active=false;p.progress=0;SFX.play('expire')}",'bridge expiration')
    html = one(html,"if(p.breakTime>1.0){p.active=false;p.remaining=1.8}",
               "if(p.breakTime>1.0){p.active=false;p.remaining=1.8;SFX.play('crumble')}",'bridge collapse')
    html = one(html,"if(Math.hypot(ox-c.x,footY-25-cy)<26){c.got=true;this.items++;continue}",
               "if(Math.hypot(ox-c.x,footY-25-cy)<26){c.got=true;this.items++;SFX.play('spark');continue}",'spark')
    html = html.replace('СКАНЕР / ХОД','ХОД').replace('Стик: слегка — сканер, сильнее — ход · кнопка — прыжок','Левый стик — ход · правое кольцо — сенсор · центр — прыжок').replace('Наведи сенсор на пунктирные мосты','Наведи правым кольцом на пунктирные мосты')
    html = html.replace('платформера v0.2','платформера v0.3')
    return html

def upgrade_v04(html):
    html=one(html,
        'right:1.4%;bottom:2%;width:min(23vw,146px);height:min(23vw,146px);max-height:33vh;max-width:33vh;aspect-ratio:1;border:2px solid #ff91d0b5;',
        'right:max(10px,env(safe-area-inset-right));bottom:max(8px,env(safe-area-inset-bottom));width:min(34vw,228px,54vh);height:min(34vw,228px,54vh);aspect-ratio:1;border:5px solid #ff91d0c9;',
        'aim control size')
    html=one(html,
        'width:46%;height:46%;border-radius:50%;border:2px solid #ffb9e7;',
        'width:42%;height:42%;min-width:72px;min-height:72px;border-radius:50%;border:2px solid #ffb9e7;',
        'jump button within ring')
    html=one(html,
        'width:11px;height:11px;border-radius:50%;transform:translate(-50%,-50%);background:#fbadf0;',
        'width:17px;height:17px;border-radius:50%;transform:translate(-50%,-50%);background:#fbadf0;',
        'aim marker')
    html=one(html,
        "const r=Math.min(b.width,b.height)*.39;",
        "const r=Math.min(b.width,b.height)*.38;",
        'aim indicator radius')
    html=one(html,
        '<button id="soundToggle" type="button">ЗВУК: ВКЛ</button>',
        '<div id="perfInfo" style="font:11px Arial;color:#bce9fd;margin:6px 0">FPS: — · макс. кадр: —</div><button id="soundToggle" type="button">ЗВУК: ВКЛ</button>',
        'physics diagnostics')
    html=one(html,
        'this.blocksGraphics.clear();this.aimed=null;',
        "// Animate decorative geometry at ~30 Hz; physics and beam still run at the native rate.\n this._decorMs=(this._decorMs??32)+ms;const drawDecor=this._decorMs>=32;\n if(drawDecor){this._decorMs%=32;this.blocksGraphics.clear();}\n this.aimed=null;",
        'decoration cadence')
    html=one(html,
        '  // Процедурная мягкая неоновая рамка поверх опор, без перерисовки фонового изображения.\n  this.blocksGraphics.fillStyle',
        '  if(drawDecor){\n  // Процедурная мягкая неоновая рамка поверх опор, без перерисовки фонового изображения.\n  this.blocksGraphics.fillStyle',
        'guard graphics draw')
    html=one(html,
        '  this.blocksGraphics.lineStyle(1,0xffffff,.4*alpha).lineBetween(p.a+4,p.y+2,p.b-4,p.y+2);',
        '  this.blocksGraphics.lineStyle(1,0xffffff,.4*alpha).lineBetween(p.a+4,p.y+2,p.b-4,p.y+2);\n  }',
        'close graphics guard')
    html=one(html,
        'this.orbs.clear();for(let c of this.collectibles)',
        'if(drawDecor)this.orbs.clear();for(let c of this.collectibles)',
        'orbs cadence')
    html=one(html,
        ' this.orbs.lineStyle(2,0xa5f8ff,.9);',
        ' if(drawDecor){this.orbs.lineStyle(2,0xa5f8ff,.9);',
        'guard orb draw')
    html=one(html,
        'this.orbs.fillTriangle(c.x,cy+9,c.x-6,cy,c.x+6,cy);',
        'this.orbs.fillTriangle(c.x,cy+9,c.x-6,cy,c.x+6,cy);}',
        'close orb guard')
    html=one(html,
        "this.label.setText('Искры: '+this.items+'/'+this.collectibles.length+'   ·   '+(this.aimed?'ЗАРЯДКА '+Math.round(this.aimed.progress*100)+'%':'Наведи правым кольцом на пунктирные мосты'));",
        "// Text rasterization is not needed every animation frame.\n this._hudMs=(this._hudMs??120)+ms;if(this._hudMs>=120){this._hudMs%=120;\n const label='Искры: '+this.items+'/'+this.collectibles.length+'   ·   '+(this.aimed?'ЗАРЯДКА '+Math.round(this.aimed.progress*100)+'%':'Наведи правым кольцом на пунктирные мосты');\n if(this._lastLabel!==label){this.label.setText(label);this._lastLabel=label;}}\n // Expose frame pacing on the phone, but update the DOM once per second only.\n const pf=this._perf||(this._perf={elapsed:0,count:0,worst:0});pf.elapsed+=ms;pf.count++;pf.worst=Math.max(pf.worst,ms);\n if(pf.elapsed>=1000){const readout=document.getElementById('perfInfo');readout.textContent='FPS: '+Math.round(1000*pf.count/pf.elapsed)+' · макс. кадр: '+Math.round(pf.worst)+' мс';pf.elapsed=0;pf.count=0;pf.worst=0;}",
        'hud and perf instrumentation')
    html=one(html,'платформера v0.3','платформера v0.4','title version')
    return html


def upgrade_v05(s):
    # Both dimensions must share the same constraint; CSS max-height had squeezed a joystick into an ellipse.
    s=one(s,
        'width:min(26vw,125px);height:min(26vw,125px);max-height:26vh;aspect-ratio:1;',
        'width:min(26vw,125px,26vh);height:min(26vw,125px,26vh);aspect-ratio:1;',
        'circular movement pad')
    # Keep wide touch zone, restore a restrained visual ring with a pseudosurface.
    s=one(s,
        'aspect-ratio:1;border:5px solid #ff91d0c9;border-radius:50%;background:#34113b75;box-shadow:0 0 17px #dc29a44b inset,0 0 17px #ff32ba4e;pointer-events:auto;touch-action:none;overflow:visible}',
        'aspect-ratio:1;border:0;border-radius:50%;background:transparent;box-shadow:none;pointer-events:auto;touch-action:none;overflow:visible}',
        'invisible large aiming capture zone')
    s=one(s,
        "#scanRing:before{content:'СЕНСОР';position:absolute;top:-22px;left:50%;transform:translateX(-50%);color:#ffd2f3;font:11px Arial;white-space:nowrap;pointer-events:none}",
        "#scanRing:before{content:'';position:absolute;inset:16%;border:2px solid #ff91d0b8;border-radius:50%;background:#34113b3d;box-shadow:0 0 10px #dc29a422 inset,0 0 8px #ff32ba35;pointer-events:none}\n#scanRing .ring-label{position:absolute;top:6%;left:50%;transform:translateX(-50%);color:#ffd2f3;font:11px Arial;white-space:nowrap;pointer-events:none}",
        'small display ring')
    s=one(s,
        'width:42%;height:42%;min-width:72px;min-height:72px;border-radius:50%;',
        'width:36%;height:36%;min-width:65px;min-height:65px;max-width:82px;max-height:82px;border-radius:50%;',
        'jump button fits compact display ring')
    s=one(s,
        '<div id="scanRing"><button id="jump" type="button">ПРЫЖОК</button></div>',
        '<div id="scanRing"><span class="ring-label">СЕНСОР</span><button id="jump" type="button">ПРЫЖОК</button></div>',
        'ring label markup')
    s=one(s,
        '<button id="menu">ФИЗИКА ⚙</button>',
        '<div id="fpsHud" aria-live="off">FPS: — · кадр: —</div><button id="menu">ФИЗИКА ⚙</button>',
        'fps HUD markup')
    s=one(s,
        '#menu{position:absolute;',
        '#fpsHud{position:absolute;top:max(9px,env(safe-area-inset-top));left:max(10px,env(safe-area-inset-left));z-index:6;padding:4px 7px;border:1px solid #3d8ba557;border-radius:6px;background:#0715239e;color:#c8edff;font:12px/1.3 Arial;pointer-events:none;white-space:nowrap}#menu{position:absolute;',
        'fps HUD style')
    s=one(s,
        'control.move=Math.abs(x)>.13?x:0;',
        'control.move=Math.abs(x)>=.28?Math.sign(x):0;',
        'consistent side-scrolling move speed')
    s=one(s,
        "el.addEventListener('pointerdown',e=>{e.preventDefault();pid=e.pointerId;el.setPointerCapture(pid);read(e)});",
        "el.addEventListener('pointerdown',e=>{e.preventDefault();if(pid!==null)return;pid=e.pointerId;el.setPointerCapture(pid);read(e)});",
        'protect active pointer')
    s=one(s,
        'const r=Math.min(b.width,b.height)*.38;',
        'const r=Math.min(b.width,b.height)*.335;',
        'align marker with visible ring')
    s=one(s,
        "const pf=this._perf||(this._perf={elapsed:0,count:0,worst:0});pf.elapsed+=ms;pf.count++;pf.worst=Math.max(pf.worst,ms);\n if(pf.elapsed>=1000){const readout=document.getElementById('perfInfo');readout.textContent='FPS: '+Math.round(1000*pf.count/pf.elapsed)+' · макс. кадр: '+Math.round(pf.worst)+' мс';pf.elapsed=0;pf.count=0;pf.worst=0;}",
        "const pf=this._perf||(this._perf={elapsed:0,count:0,worst:0,last:0});\n const now=performance.now(),actual=pf.last?now-pf.last:0;pf.last=now;\n if(actual>0){pf.elapsed+=actual;pf.count++;pf.worst=Math.max(pf.worst,actual);}\n if(pf.elapsed>=1000){const line='FPS: '+Math.round(1000*pf.count/pf.elapsed)+' · кадр: '+Math.round(pf.worst)+' мс';\n const readout=document.getElementById('perfInfo'),hud=document.getElementById('fpsHud');readout.textContent=line;hud.textContent=line;pf.elapsed=0;pf.count=0;pf.worst=0;}",
        'real frame diagnostic on screen')
    s=one(s,'платформера v0.4','платформера v0.5','document version title')
    return s

def upgrade_v06(s):
    # One right joystick: press its central jump zone, drag anywhere to aim.
    s=one(s,
      '#jump:active{background:#d839ab}',
      '#scanRing.jump-held #jump{background:#d839ab}',
      'visual jump press state')
    s=one(s,
      'pointer-events:auto;touch-action:none}#scanRing.jump-held #jump',
      'pointer-events:none;touch-action:none;display:grid;place-items:center}#scanRing.jump-held #jump',
      'non-intercepting jump zone')
    s=one(s,
      '<span class="ring-label">СЕНСОР</span><button id="jump" type="button">ПРЫЖОК</button>',
      '<span class="ring-label">СЕНСОР</span><div id="jump" aria-hidden="true">ПРЫЖОК</div>',
      'jump decorative div')
    s=one(s,
      '''scanRing.addEventListener('pointerdown',e=>{
 if(e.target.id==='jump')return;
 e.preventDefault();scanPointer=e.pointerId;
 scanRing.setPointerCapture(e.pointerId);aimFromRing(e);
});''',
      '''scanRing.addEventListener('pointerdown',e=>{
 if(scanPointer!==null)return;
 e.preventDefault();
 scanPointer=e.pointerId;
 const box=document.getElementById('jump').getBoundingClientRect();
 const dx=e.clientX-(box.left+box.width/2),dy=e.clientY-(box.top+box.height/2);
 const startInJump=Math.hypot(dx,dy)<=Math.min(box.width,box.height)/2;
 if(startInJump){
  control.jumpQueued=true; // exactly one jump request on the initial central touch
  scanRing.classList.add('jump-held');
 }else{
  aimFromRing(e); // outside center only aims
 }
 scanRing.setPointerCapture(e.pointerId);
});''',
      'zone-aware pointerdown')
    s=one(s,
      'function endAim(e){if(e.pointerId===scanPointer)scanPointer=null}',
      "function endAim(e){if(e.pointerId===scanPointer){scanPointer=null;scanRing.classList.remove('jump-held')}}",
      'release jump-held state')
    s=one(s,
      "document.getElementById('jump').addEventListener('pointerdown',e=>{e.preventDefault();e.stopPropagation();control.jumpQueued=true});",
      '// All right-side touches use the same scanRing listener; the jump icon does not steal drag events.',
      'remove separate jump handler')
    s=one(s,
      'Левый стик — ход · правое кольцо — сенсор · центр — прыжок',
      'Левый — ход · правый — свет · центр правого — прыжок + свет',
      'control legend')
    s=s.replace('платформера v0.5','платформера v0.6')
    return s

def upgrade_v07(s):
    old = """let grounded=body.blocked.down||body.touching.down;
if(this.state==='push') {body.setVelocityY(0);this.stateTime+=ms;this.fixedJumpPose(1);if(this.stateTime>=85){body.setVelocityY(-params.jump);SFX.play('jump');this.setState('rise');}}
else if(this.state==='land'){this.stateTime+=ms;this.fixedJumpPose(this.stateTime<95?1:0);if(this.stateTime>=200)this.setState(Math.abs(axis)>.1?'run':'idle')}
else {
 if(control.jumpQueued&&grounded){this.setState('push');this.fixedJumpPose(1)}
 else if(!grounded){"""
    new = """let grounded=body.blocked.down||body.touching.down;
// Store one tap for a short period so a tap during landing or just before contact is not lost.
if(control.jumpQueued){this.jumpBufferMs=160;control.jumpQueued=false;}
else this.jumpBufferMs=Math.max(0,(this.jumpBufferMs||0)-ms);
if(this.state==='push') {body.setVelocityY(0);this.stateTime+=ms;this.fixedJumpPose(1);if(this.stateTime>=45){body.setVelocityY(-params.jump);this.jumpBufferMs=0;SFX.play('jump');this.setState('rise');}}
// The landing animation is visual only: the next jump can interrupt it immediately.
else if(grounded&&this.jumpBufferMs>0){this.jumpBufferMs=0;this.setState('push');this.fixedJumpPose(1);}
else if(this.state==='land'){this.stateTime+=ms;this.fixedJumpPose(this.stateTime<95?1:0);if(this.stateTime>=200)this.setState(Math.abs(axis)>.1?'run':'idle')}
else {
 if(!grounded){"""
    assert s.count(old)==1, f'animation anchor found {s.count(old)} times'
    s=s.replace(old,new)
    # Reset a buffered tap when the player is explicitly reset, not on the next update tick.
    old_reset="this.state='idle';this.stateTime=0;this.previousGround=false;};resetFn=this.respawnToStart;"
    new_reset="this.state='idle';this.stateTime=0;this.previousGround=false;this.jumpBufferMs=0;control.jumpQueued=false;};resetFn=this.respawnToStart;"
    assert s.count(old_reset)==1, f'respawn anchor found {s.count(old_reset)} times'
    s=s.replace(old_reset,new_reset)
    assert s.count("control.jumpQueued=false;")==3  # queued consumption, original unconditional, reset
    # Original unconditional clearing is redundant but harmless; now remove it to keep one source of truth.
    s=s.replace("\n control.jumpQueued=false;\n if(grounded&&this.state==='run'", "\n if(grounded&&this.state==='run'",1)
    assert "if(grounded&&this.jumpBufferMs>0)" in s
    s=s.replace('платформера v0.6','платформера v0.7')
    return s


def upgrade_v08(s):
    # Pure layout adjustment. Preserve pointer geometry and all jump/beam logic.
    s=one(s,
      'width:min(26vw,125px,26vh);height:min(26vw,125px,26vh);aspect-ratio:1;',
      'width:min(31vw,150px,32vh);height:min(31vw,150px,32vh);aspect-ratio:1;',
      'left movement pad: enlarge without ellipse')
    s=one(s,'#move{left:2.4%;bottom:5%}', '#move{left:5.2%;bottom:5%}', 'shift left movement pad right')
    # Sprites were 512 px/frame, but on screen they are around 67 logical pixels.
    # Keep the existing sprite position/physical collider exactly unchanged.
    for key in ('idle','run','jump'):
        s=one(s,
          f"this.load.spritesheet('kiira_{key}',ASSETS.{key},{{frameWidth:512,frameHeight:512}})",
          f"this.load.spritesheet('kiira_{key}',ASSETS.{key},{{frameWidth:256,frameHeight:256}})",
          f'{key} frame cell')
    s=one(s,'.setOrigin(.5,1).setScale(.131).setDepth(40)',
      '.setOrigin(.5,1).setScale(.262).setDepth(40)','preserve sprite display size')
    # Drawing the same triangles/lines every frame at rest sends redundant graphics to WebGL.
    s=one(s,
      'this.lightGraphics.clear();this.lightGraphics.fillStyle(0x45caff,.09);',
      'if(this._beamX!==ox||this._beamY!==oy||this._beamAng!==ang){\n this._beamX=ox;this._beamY=oy;this._beamAng=ang;\n this.lightGraphics.clear();this.lightGraphics.fillStyle(0x45caff,.09);',
      'cache static flashlight start')
    s=one(s,
      'this.sensorGraphics.fillStyle(0x89ecff,1).fillCircle(sx+2*Math.cos(ang),sy+2*Math.sin(ang),3);',
      'this.sensorGraphics.fillStyle(0x89ecff,1).fillCircle(sx+2*Math.cos(ang),sy+2*Math.sin(ang),3);\n }',
      'cache static flashlight end')
    # Measure engine/preload/scene startup phases as one-time diagnostics.
    s=one(s,'function initGame(){',
      'const bootTelemetry={start:performance.now(),load:0,ready:0,first:0};\nfunction initGame(){',
      'boot marker')
    s=one(s,"preload(){this.load.image('screen',ASSETS.bg);",
      "preload(){this.load.once('complete',()=>{bootTelemetry.load=performance.now();});this.load.image('screen',ASSETS.bg);",
      'loader marker')
    s=one(s,'resetFn=this.respawnToStart;',
      'resetFn=this.respawnToStart;bootTelemetry.ready=performance.now();',
      'creation marker')
    s=one(s,"<div id=\"perfInfo\" style=\"font:11px Arial;color:#bce9fd;margin:6px 0\">",
      "<div id=\"startupInfo\" style=\"font:11px Arial;color:#bce9fd;margin:6px 0\">Загрузка: замер...</div><div id=\"perfInfo\" style=\"font:11px Arial;color:#bce9fd;margin:6px 0\">",
      'startup diagnostics label')
    s=one(s,
      'const now=performance.now(),actual=pf.last?now-pf.last:0;pf.last=now;',
      "const now=performance.now(),actual=pf.last?now-pf.last:0;pf.last=now;\n if(!bootTelemetry.first){bootTelemetry.first=now;const el=document.getElementById('startupInfo');if(el)el.textContent='Загрузка: '+((bootTelemetry.first-bootTelemetry.start)/1000).toFixed(1)+' с · ресурсы: '+((bootTelemetry.load-bootTelemetry.start)/1000).toFixed(1)+' с · сцена: '+((bootTelemetry.ready-bootTelemetry.load)/1000).toFixed(1)+' с';}",
      'startup diagnostics on first frame')
    s=s.replace('платформера v0.7','платформера v0.8')
    return s


def optimize_assets(html):
    """Offline build-time compression; keeps source parts and runtime Phaser APIs intact."""
    import base64
    import io
    from PIL import Image
    sizes={'bg':(960,540),'idle':(768,256),'run':(1024,512),'jump':(1024,256)}
    counts={key:0 for key in sizes}
    before=after=0
    def replace(match):
        nonlocal before,after
        key=match.group(1)
        if key not in sizes: return match.group(0)
        counts[key]+=1
        raw=base64.b64decode(match.group(2),validate=True)
        with Image.open(io.BytesIO(raw)) as im:
            target=sizes[key]
            if key!='bg' and (im.width//target[0],im.height//target[1])!=(2,2):
                raise RuntimeError(f'unexpected {key} frame sheet: {im.size}')
            if key=='bg' and im.size!=(1672,941):
                raise RuntimeError(f'unexpected background: {im.size}')
            out=im.resize(target, Image.Resampling.LANCZOS)
            output=io.BytesIO()
            out.save(output,format='PNG',optimize=True)
            blob=output.getvalue()
        before+=len(raw);after+=len(blob)
        return '"'+key+'":"data:image/png;base64,'+base64.b64encode(blob).decode('ascii')+'"'
    html=re.sub(r'"(bg|idle|run|jump)":"data:image/png;base64,([A-Za-z0-9+/=]+)"',replace,html)
    if any(c!=1 for c in counts.values()):
        raise RuntimeError(f'Expected exactly four textures: {counts}')
    print(f'Textures: {before:,} -> {after:,} bytes; GPU memory 21 -> 5.75 MiB')
    return html

def upgrade_v09(s):
    helper='''// Beam overlap accounts for a bridge's entire width, not just its midpoint.
// Shared by visibility, charging and the sparkle highlights.
function beamCoverage(ox,oy,angle,range,spread,a,b,y){
 const forwardX=Math.cos(angle),forwardY=Math.sin(angle),limit=Math.cos(spread),max2=range*range;
 let hits=0;const samples=11;
 for(let i=0;i<samples;i++){
  const x=a+(b-a)*i/(samples-1),vx=x-ox,vy=y-oy,d2=vx*vx+vy*vy;
  if(d2>1&&d2<=max2&&(vx*forwardX+vy*forwardY)>=Math.sqrt(d2)*limit)hits++;
 }
 return hits/samples;
}'''
    s=one(s,'class Demo extends Phaser.Scene{',helper+'\nclass Demo extends Phaser.Scene{','beam helper')
    s=one(s,
       "this.add.rectangle(W/2,H/2,W,H,0x020713,0.51).setDepth(4);",
       """this.add.rectangle(W/2,H/2,W,H,0x020713,0.51).setDepth(4);
// Two cut-outs of the SAME approved background texture: only pixels hit by
// the movable light return to their original brightness (no flat painted beam).
this.revealMaskGraphics=this.make.graphics({x:0,y:0,add:false});
this.focusMaskGraphics=this.make.graphics({x:0,y:0,add:false});
this.revealBackground=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(5).setAlpha(.69);
this.revealFocus=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(6).setAlpha(.27);
this.revealBackground.setMask(this.revealMaskGraphics.createGeometryMask());
this.revealFocus.setMask(this.focusMaskGraphics.createGeometryMask());""",
       'actual reveal layers')
    s=one(s,
       'progress:0,remaining:0,breakTime:0,obj:g',
       'progress:0,remaining:0,breakTime:0,revealed:false,beamCoverage:0,obj:g',
       'bridge reveal state')
    s=one(s,
       "this._beamX=ox;this._beamY=oy;this._beamAng=ang;\n this.lightGraphics.clear();",
       """this._beamX=ox;this._beamY=oy;this._beamAng=ang;
 this.revealMaskGraphics.clear();this.revealMaskGraphics.fillStyle(0xffffff,1);
 this.revealMaskGraphics.fillTriangle(ox,oy,ox+280*Math.cos(ang-rad),oy+280*Math.sin(ang-rad),ox+280*Math.cos(ang+rad),oy+280*Math.sin(ang+rad));
 this.focusMaskGraphics.clear();this.focusMaskGraphics.fillStyle(0xffffff,1);
 this.focusMaskGraphics.fillTriangle(ox,oy,ox+260*Math.cos(ang-.12),oy+260*Math.sin(ang-.12),ox+260*Math.cos(ang+.12),oy+260*Math.sin(ang+.12));
 this.lightGraphics.clear();""",
       'light masks update with sensor')
    s=one(s,
       "this.lightGraphics.clear();this.lightGraphics.fillStyle(0x45caff,.09);",
       "this.lightGraphics.clear();this.lightGraphics.fillStyle(0x45caff,.028);",
       'beam visual lightening')
    s=one(s,
       "this.lightGraphics.fillStyle(0x9cefff,.12);",
       "this.lightGraphics.fillStyle(0x9cefff,.043);",
       'beam core visual lightening')
    s=one(s,
       "let px=(p.a+p.b)/2,py=p.y+3,vx=px-ox,vy=py-oy,dist=Math.hypot(vx,vy),dot=(vx*dirx+vy*diry)/(dist||1),lit=dist<295&&dot>Math.cos(rad);",
       """const coverage=beamCoverage(ox,oy,ang,295,rad,p.a,p.b,p.y+3);
  const lit=coverage>0;
  p.beamCoverage=coverage;
  p.revealed=lit||p.active;""",
       'bridge full-width illumination')
    s=one(s,
       'p.progress=Math.min(1,p.progress+dt*1.7);',
       'p.progress=Math.min(1,p.progress+dt*(.95+.75*Math.min(1,coverage*3)));',
       'beam strength charge')
    s=one(s,
       "if(drawDecor){\n  // Процедурная мягкая неоновая рамка поверх опор, без перерисовки фонового изображения.",
       """if(drawDecor){
  // A hidden bridge has a near-black cover over its baked backdrop; a real hit
  // removes that cover and lights its outline while charging. Active bridges stay visible.
  if((p.type==='charge'||p.type==='timed')&&!p.active){
    this.blocksGraphics.fillStyle(0x020a17,lit?.16:.83).fillRect(p.a,p.y-4,p.b-p.a,29);
  }
  if(lit&&!p.active&&(p.type==='charge'||p.type==='timed')){
    this.blocksGraphics.fillStyle(color,.11+.09*Math.min(1,coverage*3)).fillRect(p.a,p.y,p.b-p.a,24);
    this.blocksGraphics.fillStyle(color,.75).fillRect(p.a+4,p.y-7,Math.max(1,(p.b-p.a-8)*p.progress),3);
  }
  // Процедурная мягкая неоновая рамка поверх опор, без перерисовки фонового изображения.""",
       'bridge concealment and fill status')
    s=one(s,
       "let alpha=p.active?1:(p.progress>.02?p.progress*.9:.11),color=p.type==='timed'?0xff5cc8:p.type==='crumble'?0xff4665:0x55deff;",
       "let alpha=p.active?1:(lit?.67:(p.progress>.02?.18:.07)),color=p.type==='timed'?0xff5cc8:p.type==='crumble'?0xff4665:0x55deff;",
       'glow based on beam contact')
    s=one(s,
       "if(drawDecor){this.orbs.lineStyle(2,0xa5f8ff,.9);this.orbs.fillStyle(0x75ebff,.3);",
       "if(drawDecor){const sparkLit=beamCoverage(ox,oy,ang,295,rad,c.x-6,c.x+6,cy)>0;const shine=sparkLit?1:.38;this.orbs.lineStyle(2,0xa5f8ff,.9*shine);this.orbs.fillStyle(0x75ebff,.3*shine);",
       'orbs brighten in sensor')
    s=one(s,
       "'Наведи правым кольцом на пунктирные мосты'",
       "'Освети мост · удерживай луч до зарядки'",
       'help text')
    s=one(s, 'платформера v0.8', 'платформера v0.9', 'version label')
    return s


# Shared sensor raycasts, light falloff, platform state rails, and collectible beacons.
LOGIC = r'''// Pure 2D beam geometry and shared platform meter logic.
function rayHitRect(ox,oy,dx,dy,r,maxDist){
 let near=0,far=maxDist;
 for(const [pos,dir,min,max] of [[ox,dx,r.a,r.b],[oy,dy,r.top,r.bottom]]){
  if(Math.abs(dir)<1e-7){if(pos<min||pos>max)return null;continue;}
  let a=(min-pos)/dir,b=(max-pos)/dir;
  if(a>b){const tmp=a;a=b;b=tmp}
  near=Math.max(near,a);far=Math.min(far,b);
  if(near>far)return null;
 }
 const hit=near>1.5?near:far>1.5?far:null;
 return hit!==null&&hit<maxDist?hit:null;
}
function visibleRayLength(ox,oy,dx,dy,range,occluders,exclude){
 let length=range;
 for(const box of occluders){
  if(box.owner===exclude)continue;
  const hit=rayHitRect(ox,oy,dx,dy,box,length);
  if(hit!==null&&hit<length)length=hit;
 }
 return length;
}
function beamCoverage(ox,oy,ang,range,spread,a,b,y,occluders=[],exclude=null){
 const fx=Math.cos(ang),fy=Math.sin(ang),limit=Math.cos(spread),max2=range*range;
 let hits=0;const samples=11;
 for(let i=0;i<samples;i++){
  const x=a+(b-a)*i/(samples-1),vx=x-ox,vy=y-oy,d2=vx*vx+vy*vy;
  if(d2<=1||d2>max2)continue;
  const dist=Math.sqrt(d2),dx=vx/dist,dy=vy/dist;
  if(dx*fx+dy*fy<limit)continue;
  if(visibleRayLength(ox,oy,dx,dy,dist,occluders,exclude)>=dist-2)hits++;
 }
 return hits/samples;
}
function platformMeter(p){
 const safe=(n)=>Math.min(1,Math.max(0,n||0));
 if(p.type==='solid')return 1;
 if(p.type==='charge')return p.active?1:safe(p.progress);
 if(p.type==='timed')return p.active?(p.beamCoverage>0?1:safe(p.remaining/3.3)):safe(p.progress);
 if(p.type==='crumble')return p.active?safe(1-(p.breakTime||0)):safe(1-(p.remaining||0)/1.8);
 return 0;
}
function beamPolygon(ox,oy,angle,spread,range,occluders,rays=32){
 const out=[];
 for(let i=0;i<=rays;i++){
  const a=angle-spread+2*spread*i/rays,dx=Math.cos(a),dy=Math.sin(a);
  const reach=visibleRayLength(ox,oy,dx,dy,range,occluders,null);
  out.push({x:ox+reach*dx,y:oy+reach*dy});
 }
 return out;
}
'''

def upgrade_v10(html):
 # Pure geometry and platform state: one source used by local tests and Phaser.
 start=html.index('function beamCoverage(')
 end=html.index('class Demo extends Phaser.Scene',start)
 html=html[:start]+LOGIC+'\n// Small geometry-mask helper: each triangle ends at the nearest light-blocking surface.\nfunction fillBeamMask(graphics,ox,oy,points){\n graphics.clear();graphics.fillStyle(0xffffff,1);\n for(let i=1;i<points.length;i++)graphics.fillTriangle(ox,oy,points[i-1].x,points[i-1].y,points[i].x,points[i].y);\n}\n'+html[end:]
 html=one(html,
  "this.focusMaskGraphics=this.make.graphics({x:0,y:0,add:false});\nthis.revealBackground=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(5).setAlpha(.69);",
  "this.focusMaskGraphics=this.make.graphics({x:0,y:0,add:false});\nthis.midMaskGraphics=this.make.graphics({x:0,y:0,add:false});\nthis.revealBackground=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(5).setAlpha(.30);\nthis.revealMid=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(5.5).setAlpha(.39);\nthis.revealMid.setMask(this.midMaskGraphics.createGeometryMask());",
  'mask falloff layers')
 html=one(html,
  "this.revealFocus=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(6).setAlpha(.27);",
  "this.revealFocus=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(6).setAlpha(.28);",
  'focus strength')
 html=one(html,
  'this.camAngle=control.angle;',
  '''// Shortest-angle interpolation makes the scanner feel mounted on a moving head.
const difference=Math.atan2(Math.sin(control.angle-this.camAngle),Math.cos(control.angle-this.camAngle));
this.camAngle=Math.abs(difference)<.0006?control.angle:this.camAngle+difference*(1-Math.exp(-dt*13));''',
  'scanner angular inertia')

 start=html.index(' if(this._beamX!==ox||this._beamY!==oy||this._beamAng!==ang){')
 end=html.index(' // Animate decorative geometry',start)
 light=''' // Active platform slabs are actual 2D light blockers. Hidden bridges do not cast shadows.
 const occluders=[];
 for(const p of this.blocks)if(p.active)occluders.push({a:p.a,b:p.b,top:p.y+2,bottom:p.y+22,owner:p});
 const occStamp=this.blocks.map(p=>p.active?'1':'0').join('');
 this._lightMs=(this._lightMs??32)+ms;
 if(this._lightMs>=32&&(this._beamX!==ox||this._beamY!==oy||this._beamAng!==ang||this._occStamp!==occStamp)){
  this._lightMs%=32;this._beamX=ox;this._beamY=oy;this._beamAng=ang;this._occStamp=occStamp;
  // Three illumination bands add distance falloff without a costly shader.
  const outer=beamPolygon(ox,oy,ang,rad,295,occluders,40);
  const mid=beamPolygon(ox,oy,ang,rad,185,occluders,40);
  const core=beamPolygon(ox,oy,ang,.125,252,occluders,18);
  fillBeamMask(this.revealMaskGraphics,ox,oy,outer);
  fillBeamMask(this.midMaskGraphics,ox,oy,mid);
  fillBeamMask(this.focusMaskGraphics,ox,oy,core);
  this.lightGraphics.clear();
  this.lightGraphics.fillStyle(0x62d9ff,.028);
  for(let i=1;i<outer.length;i++)this.lightGraphics.fillTriangle(ox,oy,outer[i-1].x,outer[i-1].y,outer[i].x,outer[i].y);
  this.lightGraphics.lineStyle(1,0x8ceeff,.22);
  this.lightGraphics.lineBetween(ox,oy,outer[0].x,outer[0].y);
  this.lightGraphics.lineBetween(ox,oy,outer[outer.length-1].x,outer[outer.length-1].y);
  this.sensorGraphics.clear();this.sensorGraphics.lineStyle(3,0x212a44,.95);
  this.sensorGraphics.lineBetween(ox,footY-42,ox,footY-58);
  const sx=ox,sy=footY-59;
  this.sensorGraphics.fillStyle(0x13243d,1).fillCircle(sx,sy,5);
  this.sensorGraphics.fillStyle(0x89ecff,1).fillCircle(sx+2*Math.cos(ang),sy+2*Math.sin(ang),3);
 }
'''
 html=html[:start]+light+html[end:]
 start=html.index(' this.aimed=null;\n for(const p of this.blocks)')
 end=html.index(' // Декоративные собираемые искры',start)
 platforms=''' this.aimed=null;
 for(const p of this.blocks){
  const coverage=beamCoverage(ox,oy,ang,295,rad,p.a,p.b,p.y+3,occluders,p);
  const lit=coverage>0;
  p.beamCoverage=coverage;p.revealed=lit||p.active;
  if(p.type==='charge'||p.type==='timed'){
   if(lit){
    if(!p.active&&p.progress<.01)SFX.play('focus');
    p.progress=Math.min(1,p.progress+dt*(.95+.75*Math.min(1,coverage*3)));
    this.aimed=p;
    if(p.progress>=1){if(!p.active)SFX.play('charged');p.active=true;if(p.type==='timed')p.remaining=3.3;}
   }else if(!p.active)p.progress=Math.max(0,p.progress-dt*.22);
   if(p.type==='timed'&&p.active&&!lit){p.remaining-=dt;if(p.remaining<=0){p.active=false;p.remaining=0;p.progress=0;SFX.play('expire');}}
  }
  if(p.type==='crumble'&&grounded&&footY>=p.y-3&&footY<=p.y+11&&ox>=p.a&&ox<=p.b){
   p.breakTime+=dt;if(p.breakTime>1){p.active=false;p.remaining=1.8;SFX.play('crumble');}
  }
  if(p.type==='crumble'&&!p.active){p.remaining-=dt;if(p.remaining<=0){p.active=true;p.breakTime=0;}}
  p.obj.body.enable=p.active;
  if(!drawDecor)continue;
  const color=p.type==='timed'?0xff63bd:p.type==='crumble'?0xffa15e:p.type==='solid'?0x87c6d9:0x51dfff;
  const alpha=p.type==='solid'?.52:p.active?1:lit?.82:.19;
  if(!p.active&&(p.type==='charge'||p.type==='timed')){
   this.blocksGraphics.fillStyle(0x030b17,lit?.25:.85).fillRect(p.a,p.y-3,p.b-p.a,28);
  }
  // Every platform has the same internal status rail. Only its fill logic changes.
  this.blocksGraphics.fillStyle(color,.12*alpha).fillRect(p.a,p.y+1,p.b-p.a,23);
  this.blocksGraphics.lineStyle(2,color,.70*alpha).strokeRect(p.a+2,p.y+2,p.b-p.a-4,20);
  const railX=p.a+8,railY=p.y+12,railW=Math.max(4,p.b-p.a-16),railH=6;
  this.blocksGraphics.fillStyle(0x020b18,.85).fillRoundedRect(railX,railY,railW,railH,3);
  this.blocksGraphics.lineStyle(1,color,.46*alpha).strokeRoundedRect(railX,railY,railW,railH,3);
  const amount=platformMeter(p),fillW=Math.max(0,(railW-2)*amount);
  if(fillW>.3){
   const pulse=p.type==='solid'?.6:.77+.23*Math.sin(time*.008);
   this.blocksGraphics.fillStyle(color,alpha*pulse).fillRect(railX+1,railY+1,fillW,railH-2);
   if(amount<.18||p.type==='crumble'&&p.breakTime>.65){
    this.blocksGraphics.lineStyle(2,0xffffff,.44+.3*Math.sin(time*.035)).strokeRect(p.a+2,p.y+2,p.b-p.a-4,20);
   }
  }
 }
'''
 html=html[:start]+platforms+html[end:]
 start=html.index(' // Декоративные собираемые искры')
 end=html.index(' // Text rasterization',start)
 sparks=''' // Bright pulsing collectible cells stay legible even outside the searchlight.
 if(drawDecor)this.orbs.clear();
 for(const c of this.collectibles){
  if(c.got)continue;
  const cy=c.y+Math.sin(time*.003+c.index)*4;
  if(Math.hypot(ox-c.x,footY-25-cy)<26){c.got=true;this.items++;SFX.play('spark');continue;}
  if(!drawDecor)continue;
  const sparkLit=beamCoverage(ox,oy,ang,295,rad,c.x-5,c.x+5,cy,occluders)>0;
  const pulse=.86+.14*Math.sin(time*.005+c.index*1.7),shine=(sparkLit?1.22:1)*pulse;
  this.orbs.fillStyle(0x51e9ff,.10*shine).fillCircle(c.x,cy,20);
  this.orbs.fillStyle(0x62dfff,.20*shine).fillCircle(c.x,cy,14);
  this.orbs.fillStyle(0xcaffff,.65*shine).fillCircle(c.x,cy,7);
  this.orbs.fillStyle(0xffffff,.95).fillCircle(c.x,cy,3);
  this.orbs.lineStyle(2,0x99faff,.9*shine);
  this.orbs.lineBetween(c.x-13,cy,c.x+13,cy);
  this.orbs.lineBetween(c.x,cy-13,c.x,cy+13);
 }
'''
 html=html[:start]+sparks+html[end:]
 html=one(html,'платформера v0.9','платформера v0.10','document version')
 return html


def upgrade_v11(html):
    html=one(html,'const params={speed:205,jump:420,gravity:900};',
                 'const params={speed:205,jump:460,gravity:640};','physics defaults')
    html=one(html,'id="jumpV">420</span>','id="jumpV">460</span>','jump value label')
    html=one(html,'id="power" type="range" min="260" max="590" value="420"',
                 'id="power" type="range" min="260" max="590" value="460"','jump slider value')
    html=one(html,'id="gravV">900</span>','id="gravV">640</span>','gravity value label')
    html=one(html,'id="grav" type="range" min="500" max="1450" value="900"',
                 'id="grav" type="range" min="500" max="1450" value="640"','gravity slider value')
    # Dark areas should be genuinely dark; approved background remains unchanged.
    html=one(html,'this.add.rectangle(W/2,H/2,W,H,0x020713,0.51)',
                 'this.add.rectangle(W/2,H/2,W,H,0x020713,0.74)','ambient darkness')
    # With more ambient darkness, revealed background can be substantially brighter.
    html=one(html,"this.revealBackground=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(5).setAlpha(.30);",
                 "this.revealBackground=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(5).setAlpha(.43);",'outer light band')
    html=one(html,"this.revealMid=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(5.5).setAlpha(.39);",
                 "this.revealMid=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(5.5).setAlpha(.52);",'middle light band')
    html=one(html,"this.revealFocus=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(6).setAlpha(.28);",
                 "this.revealFocus=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(6).setAlpha(.38);",'focused light band')
    html=one(html,
      'this.lightGraphics=this.add.graphics().setDepth(10);this.blocksGraphics=this.add.graphics().setDepth(13);this.sensorGraphics=this.add.graphics().setDepth(45);',
      '''this.lightGraphics=this.add.graphics().setDepth(10);
// Lightweight additive passes at 30 Hz: no blur filters or dynamic shadow textures.
this.platformGlow=this.add.graphics().setDepth(12.5).setBlendMode(Phaser.BlendModes.ADD);
this.blocksGraphics=this.add.graphics().setDepth(13);
this.sensorGraphics=this.add.graphics().setDepth(45);''','platform glow layer')
    html=one(html,'this.orbs=this.add.graphics().setDepth(18);',
      'this.orbGlow=this.add.graphics().setDepth(17.5).setBlendMode(Phaser.BlendModes.ADD);\nthis.orbs=this.add.graphics().setDepth(18);',
      'collectible glow layer')
    html=one(html,'function fillBeamMask(graphics,ox,oy,points){',
      '''// A charge bridge persists after light leaves it; timed bridges keep their original timing.
function platformChargeRate(type,coverage){
 const base=.95+.75*Math.min(1,coverage*3);
 return type==='charge'?base*.78:base;
}
function fillBeamMask(graphics,ox,oy,points){''','charge-rate function')
    html=one(html,'p.progress=Math.min(1,p.progress+dt*(.95+.75*Math.min(1,coverage*3)));',
      'p.progress=Math.min(1,p.progress+dt*platformChargeRate(p.type,coverage));',
      'charge rate usage')
    html=one(html,'this.lightGraphics.fillStyle(0x62d9ff,.028);',
      'this.lightGraphics.fillStyle(0x62d9ff,.055);','visible pale-cyan beam')
    html=one(html,'this.sensorGraphics.fillStyle(0x89ecff,1).fillCircle(sx+2*Math.cos(ang),sy+2*Math.sin(ang),3);',
      '''this.sensorGraphics.fillStyle(0x53dfff,.12).fillCircle(sx,sy,16);
  this.sensorGraphics.fillStyle(0x7eeeff,.24).fillCircle(sx,sy,9);
  this.sensorGraphics.fillStyle(0x89ecff,1).fillCircle(sx+2*Math.cos(ang),sy+2*Math.sin(ang),3);''',
      'sensor emitter glow')
    html=one(html,'if(drawDecor){this._decorMs%=32;this.blocksGraphics.clear();}',
      'if(drawDecor){this._decorMs%=32;this.blocksGraphics.clear();this.platformGlow.clear();}',
      'platform glow clear')
    html=one(html,
      "const alpha=p.type==='solid'?.52:p.active?1:lit?.82:.19;",
      '''const alpha=p.type==='solid'?.58:p.active?1:lit?.90:.12;
  // Warm/cold emissive halos reveal active edges without illuminating hidden bridges.
  const energy=p.active?(p.type==='solid'?.27:.86):lit?Math.max(.20,p.progress*.66):p.progress*.14;
  if(energy>.09){
   const e=energy*(.90+.10*Math.sin(time*.006+p.a*.07));
   const w=p.b-p.a;
   this.platformGlow.fillStyle(color,.036*e).fillRoundedRect(p.a-10,p.y-11,w+20,43,11);
   this.platformGlow.fillStyle(color,.070*e).fillRoundedRect(p.a-5,p.y-6,w+10,32,7);
   this.platformGlow.lineStyle(5,color,.22*e).lineBetween(p.a+3,p.y+3,p.b-3,p.y+3);
   this.platformGlow.lineStyle(2,0xffffff,.29*e).lineBetween(p.a+4,p.y+3,p.b-4,p.y+3);
  }''',
      'platform energy glow')
    html=one(html,'this.blocksGraphics.fillStyle(color,.12*alpha).fillRect(p.a,p.y+1,p.b-p.a,23);',
      'this.blocksGraphics.fillStyle(color,.17*alpha).fillRect(p.a,p.y+1,p.b-p.a,23);',
      'platform emissive interior')
    html=one(html,'if(drawDecor)this.orbs.clear();',
      'if(drawDecor){this.orbs.clear();this.orbGlow.clear();}',
      'spark glow clear')
    html=one(html,'const pulse=.86+.14*Math.sin(time*.005+c.index*1.7),shine=(sparkLit?1.22:1)*pulse;',
      '''const pulse=.84+.16*Math.sin(time*.005+c.index*1.7),shine=(sparkLit?1.30:1.08)*pulse;
  // Layered alpha circles approximate a blooming self-lit collectible.
  this.orbGlow.fillStyle(0x2dbbff,.045*shine).fillCircle(c.x,cy,32);
  this.orbGlow.fillStyle(0x43dfff,.105*shine).fillCircle(c.x,cy,23);
  this.orbGlow.fillStyle(0x9dfaff,.21*shine).fillCircle(c.x,cy,13);''',
      'spark bloom')
    html=one(html,'this.orbs.fillStyle(0xcaffff,.65*shine).fillCircle(c.x,cy,7);',
      'this.orbs.fillStyle(0xcaffff,.78*shine).fillCircle(c.x,cy,7);',
      'spark luminous core')
    html=one(html,'платформера v0.10','платформера v0.11','document version')
    return html


HELPERS=r'''// Scene depth: static lamp falloff and pseudo-3D prism surfaces.
const SCENE_LAMPS=[
 {x:98,y:184,tint:0x27bbfa,radius:135,power:.85},
 {x:570,y:202,tint:0x32cbef,radius:152,power:.80},
 {x:872,y:215,tint:0xf551b8,radius:120,power:.72},
 {x:350,y:392,tint:0x36dfff,radius:112,power:.68},
 {x:776,y:380,tint:0x2bb6ff,radius:115,power:.67}
];
function staticLightStrength(x,y,lamps=SCENE_LAMPS){
 let power=0;
 for(const lamp of lamps){
  const d=Math.hypot(x-lamp.x,y-lamp.y)/lamp.radius;
  if(d<1)power=Math.max(power,lamp.power*(1-d)*(1-d));
 }
 return Math.min(1,power);
}
function platformPrismPoints(a,b,y){
 const edge=Math.min(8,(b-a)*.07),depth=24;
 return {
  top:[{x:a,y:y},{x:b,y:y},{x:b-edge,y:y+8},{x:a+edge,y:y+8}],
  front:[{x:a+edge,y:y+8},{x:b-edge,y:y+8},{x:b-edge,y:y+depth},{x:a+edge,y:y+depth}],
  left:[{x:a,y:y},{x:a+edge,y:y+8},{x:a+edge,y:y+depth},{x:a,y:y+depth-8}],
  right:[{x:b,y:y},{x:b-edge,y:y+8},{x:b-edge,y:y+depth},{x:b,y:y+depth-8}]
 };
}
// Build one small radial sprite, reused by all stationary lights.
function makeVisualTexture(scene,key,width,height,kind){
 if(scene.textures.exists(key))return;
 const cv=document.createElement('canvas');cv.width=width;cv.height=height;
 const cx=cv.getContext('2d');
 if(kind==='vignette'){
  const g=cx.createRadialGradient(width*.5,height*.45,width*.19,width*.5,height*.48,width*.73);
  g.addColorStop(0,'rgba(0,1,6,0)');g.addColorStop(.55,'rgba(0,2,9,.10)');
  g.addColorStop(.81,'rgba(0,2,10,.44)');g.addColorStop(1,'rgba(0,1,6,.83)');
  cx.fillStyle=g;cx.fillRect(0,0,width,height);
 }else{
  const g=cx.createRadialGradient(width/2,height/2,0,width/2,height/2,width/2);
  g.addColorStop(0,'rgba(255,255,255,.72)');g.addColorStop(.14,'rgba(255,255,255,.38)');
  g.addColorStop(.44,'rgba(255,255,255,.12)');g.addColorStop(1,'rgba(255,255,255,0)');
  cx.fillStyle=g;cx.fillRect(0,0,width,height);
 }
 scene.textures.addCanvas(key,cv);
}
'''

CREATION=r'''// Three planes: the approved painting remains the far field, architecture is the
// mid-distance, while near silhouettes partially occlude the game plane.
this.midArchitecture=this.add.graphics().setDepth(8);
this.midArchitecture.lineStyle(9,0x041020,.68);
this.midArchitecture.lineBetween(0,337,410,337);
this.midArchitecture.lineBetween(480,335,960,335);
this.midArchitecture.lineStyle(3,0x2a6b89,.28);
this.midArchitecture.lineBetween(20,329,388,329);
this.midArchitecture.lineBetween(496,328,953,328);
for(const bx of [72,193,503,688,887]){
 this.midArchitecture.lineStyle(6,0x071625,.8).lineBetween(bx,304,bx+16,335);
 this.midArchitecture.lineStyle(2,0x32768a,.20).lineBetween(bx+2,304,bx+17,335);
}
this.midArchitecture.fillStyle(0x071425,.42).fillRect(259,346,290,10);
this.midArchitecture.lineStyle(2,0x3086a1,.2).lineBetween(265,346,540,346);
this.foregroundSilhouette=this.add.graphics().setDepth(53);
this.foregroundSilhouette.fillStyle(0x01050d,.92);
this.foregroundSilhouette.fillRoundedRect(-40,-17,300,40,12);
this.foregroundSilhouette.fillRoundedRect(746,-22,260,44,12);
this.foregroundSilhouette.lineStyle(17,0x020712,.88);
this.foregroundSilhouette.beginPath();this.foregroundSilhouette.moveTo(120,-9);this.foregroundSilhouette.lineTo(142,56);this.foregroundSilhouette.lineTo(203,89);this.foregroundSilhouette.strokePath();
this.foregroundSilhouette.lineStyle(7,0x172f3a,.42).lineBetween(114,0,146,52);
this.foregroundSilhouette.fillStyle(0x020710,.97);
this.foregroundSilhouette.fillRect(-17,522,280,30);
this.foregroundSilhouette.fillRoundedRect(766,515,280,45,15);
this.foregroundSilhouette.lineStyle(21,0x020813,.92).lineBetween(-7,507,135,505);
this.foregroundSilhouette.lineStyle(12,0x020813,.95).lineBetween(864,496,978,489);
// Pre-rendered gradient lights: no blur filters or per-frame canvas work.
makeVisualTexture(this,'scene_v12_lamp',128,128,'glow');
makeVisualTexture(this,'scene_v12_vignette',512,288,'vignette');
this.staticLights=SCENE_LAMPS;
this.staticLampGlow=[];
for(const [i,lamp] of this.staticLights.entries()){
 const glow=this.add.image(lamp.x,lamp.y,'scene_v12_lamp')
  .setDisplaySize(lamp.radius*2,lamp.radius*2).setTint(lamp.tint)
  .setAlpha(lamp.power*.38).setBlendMode(Phaser.BlendModes.ADD).setDepth(7.2);
 const core=this.add.image(lamp.x,lamp.y,'scene_v12_lamp')
  .setDisplaySize(36,36).setTint(lamp.tint).setAlpha(.55)
  .setBlendMode(Phaser.BlendModes.ADD).setDepth(11.2);
 this.staticLampGlow.push({glow,core,index:i,power:lamp.power});
}
// Dark silhouettes behind platforms create a visible stationary shadow layer.
this.staticShadowLayer=this.add.graphics().setDepth(11.1);
this.staticShadowLayer.fillStyle(0x010610,.39);
for(const p of this.blocks){
 const lamp=this.staticLights.reduce((a,b)=>Math.hypot((p.a+p.b)/2-b.x,p.y-b.y)<Math.hypot((p.a+p.b)/2-a.x,p.y-a.y)?b:a);
 if(!p.active||Math.hypot((p.a+p.b)/2-lamp.x,p.y-lamp.y)>lamp.radius)continue;
 const dx=((p.a+p.b)/2-lamp.x)*.22;
 this.staticShadowLayer.fillPoints([
  {x:p.a+3,y:p.y+22},{x:p.b-3,y:p.y+22},
  {x:p.b-3+dx,y:p.y+40},{x:p.a+3+dx,y:p.y+40}
 ],true);
}
this.sceneVignette=this.add.image(W/2,H/2,'scene_v12_vignette').setDisplaySize(W,H).setDepth(60);
'''

UPDATE_METHOD=r'''updateVisualDepth(time,playerX){
 // Motion is subtle because this demo has a single fixed camera.
 const drift=(playerX-W*.5)/W;
 const far=drift*5+Math.sin(time*.00016)*1.5;
 this.farImage.x=W*.5-far;
 this.revealBackground.x=W*.5-far;
 this.revealMid.x=W*.5-far;
 this.revealFocus.x=W*.5-far;
 this.midArchitecture.x=-drift*11;
 this.foregroundSilhouette.x=-drift*23;
 for(const light of this.staticLampGlow){
  const flicker=.96+.04*Math.sin(time*.0023+light.index*2.5);
  light.glow.setAlpha(light.power*.38*flicker);
  light.core.setAlpha(.55*flicker);
 }
}
'''

def once(s,old,new,label):
 n=s.count(old)
 if n!=1: raise AssertionError(f'{label}: expected one target, got {n}')
 return s.replace(old,new,1)

def upgrade_v12(html):
 html=once(html,'class Demo extends Phaser.Scene{',HELPERS+'\nclass Demo extends Phaser.Scene{','helpers')
 html=once(html,"create(){document.getElementById('status').style.display='none';this.add.image(W/2,H/2,'screen').setDisplaySize(W,H).setDepth(0);",
 "create(){document.getElementById('status').style.display='none';this.farImage=this.add.image(W/2,H/2,'screen').setDisplaySize(W+20,H+10).setDepth(0);",
 'far background scene')
 for x in ['revealBackground','revealMid','revealFocus']:
  html=once(html,f"this.{x}=this.add.image(W/2,H/2,'screen').setDisplaySize(W,H)",f"this.{x}=this.add.image(W/2,H/2,'screen').setDisplaySize(W+20,H+10)",f'{x} resize')
 html=once(html,'this.orbs=this.add.graphics().setDepth(18);', 'this.orbs=this.add.graphics().setDepth(18);\n'+CREATION,'create visual planes')
 html=once(html,'setState(state){if(this.state===state)return;',UPDATE_METHOD+'setState(state){if(this.state===state)return;','visual update method')
 html=once(html,'const footY=this.actor.y+20;this.visual.setPosition(this.actor.x,footY+1);',
 'const footY=this.actor.y+20;this.visual.setPosition(this.actor.x,footY+1);\n this.updateVisualDepth(time,this.actor.x);','parallax update')
 html=once(html,'  // Every platform has the same internal status rail. Only its fill logic changes.\n  this.blocksGraphics.fillStyle(color,.17*alpha).fillRect(p.a,p.y+1,p.b-p.a,23);\n  this.blocksGraphics.lineStyle(2,color,.70*alpha).strokeRect(p.a+2,p.y+2,p.b-p.a-4,20);',
 '''  // Pseudo-3D surface: top, front, two dark end caps, and retained status rail.
  const prism=platformPrismPoints(p.a,p.b,p.y);
  const staticStrength=staticLightStrength((p.a+p.b)*.5,p.y);
  const topLight=Math.min(1,alpha*(.58+.50*staticStrength));
  this.blocksGraphics.fillStyle(0x020a15,.92).fillPoints(prism.left,true);
  this.blocksGraphics.fillStyle(0x061a2a,.91).fillPoints(prism.right,true);
  this.blocksGraphics.fillStyle(0x071522,.93).fillPoints(prism.front,true);
  this.blocksGraphics.fillStyle(color,.12*topLight).fillPoints(prism.top,true);
  this.blocksGraphics.lineStyle(2,color,.48*alpha+.16*staticStrength).strokePoints(prism.top,true);
  this.blocksGraphics.lineStyle(1,0xb3edff,.11+.36*staticStrength*alpha)
    .lineBetween(p.a+3,p.y+1,p.b-3,p.y+1);''',
 'replace flat rectangles')
 html=once(html,'платформера v0.11','платформера v0.12','document label')
 return html



# v0.13 performance repair: static 3D platform geometry is cached between state changes.
def upgrade_v13(html):
 html=once(html,
  "this.platformGlow=this.add.graphics().setDepth(12.5).setBlendMode(Phaser.BlendModes.ADD);\nthis.blocksGraphics=this.add.graphics().setDepth(13);",
  "this.platformGlow=this.add.graphics().setDepth(12.5).setBlendMode(Phaser.BlendModes.ADD);\nthis.platformFaces=this.add.graphics().setDepth(12.85);\nthis._platformFacesStamp='';\nthis.blocksGraphics=this.add.graphics().setDepth(13);",
  'cached platform graphics')
 html=once(html,'function platformPrismPoints(a,b,y){',
  '''// The platform mesh changes only when a bridge switches active state, not at 30Hz.
function drawPlatformFaces(graphics,blocks){
 graphics.clear();
 for(const p of blocks){
  if(!p.active)continue;
  const color=p.type==='timed'?0xff63bd:p.type==='crumble'?0xffa15e:p.type==='solid'?0x87c6d9:0x51dfff;
  const alpha=p.type==='solid'?.58:1;
  const prism=platformPrismPoints(p.a,p.b,p.y);
  const staticStrength=staticLightStrength((p.a+p.b)*.5,p.y);
  const topLight=Math.min(1,alpha*(.58+.50*staticStrength));
  graphics.fillStyle(0x020a15,.92).fillPoints(prism.left,true);
  graphics.fillStyle(0x061a2a,.91).fillPoints(prism.right,true);
  graphics.fillStyle(0x071522,.93).fillPoints(prism.front,true);
  graphics.fillStyle(color,.12*topLight).fillPoints(prism.top,true);
  graphics.lineStyle(2,color,.48*alpha+.16*staticStrength).strokePoints(prism.top,true);
  graphics.lineStyle(1,0xb3edff,.11+.36*staticStrength*alpha)
   .lineBetween(p.a+3,p.y+1,p.b-3,p.y+1);
 }
}
function platformPrismPoints(a,b,y){''',
  'cached platform mesh builder')
 html=once(html,
   '''  // Pseudo-3D surface: top, front, two dark end caps, and retained status rail.
  const prism=platformPrismPoints(p.a,p.b,p.y);
  const staticStrength=staticLightStrength((p.a+p.b)*.5,p.y);
  const topLight=Math.min(1,alpha*(.58+.50*staticStrength));
  this.blocksGraphics.fillStyle(0x020a15,.92).fillPoints(prism.left,true);
  this.blocksGraphics.fillStyle(0x061a2a,.91).fillPoints(prism.right,true);
  this.blocksGraphics.fillStyle(0x071522,.93).fillPoints(prism.front,true);
  this.blocksGraphics.fillStyle(color,.12*topLight).fillPoints(prism.top,true);
  this.blocksGraphics.lineStyle(2,color,.48*alpha+.16*staticStrength).strokePoints(prism.top,true);
  this.blocksGraphics.lineStyle(1,0xb3edff,.11+.36*staticStrength*alpha)
    .lineBetween(p.a+3,p.y+1,p.b-3,p.y+1);''',
   '''  // Pseudo-3D faces are in a cached graphics layer at depth 12.85.
  // Status rails and highlights continue to update independently at 30Hz.''',
   'remove repeated platform polygon uploads')
 html=once(html,
  ' this.aimed=null;\n for(const p of this.blocks){',
  ''' this.aimed=null;
 // Redraw 3D platform faces only on actual bridge state changes.
 const facesStamp=this.blocks.map(p=>p.active?'1':'0').join('');
 if(facesStamp!==this._platformFacesStamp){
  this._platformFacesStamp=facesStamp;
  drawPlatformFaces(this.platformFaces,this.blocks);
 }
 for(const p of this.blocks){''',
  'state-diff platform mesh redraw')
 html=once(html,'платформера v0.12','платформера v0.13','document label')
 return html



# v0.14 diagnostic: isolate additional graphics into touch-switchable groups.
# This intentionally does NOT guess which layer is slow. On Android, compare
# observed FPS in A (baseline), B (depth), C (lamps), D (vignette), E (all).
def upgrade_v14(html):
 html=once(html,
  "this.sceneVignette=this.add.image(W/2,H/2,'scene_v12_vignette').setDisplaySize(W,H).setDepth(60);",
  """this.sceneVignette=this.add.image(W/2,H/2,'scene_v12_vignette').setDisplaySize(W,H).setDepth(60);
 // Developer diagnostic: switch individual v0.12 layers without restarting.
 this._perfMode=0;
 this._perfDepth=false;
 this._perfLabels=['A БАЗА','Б ГЛУБИНА','В ЛАМПЫ','Г ВИНЬЕТКА','Д ВСЁ'];
 this._perfButton=this.add.text(W/2,9,'',{fontFamily:'Arial',fontSize:'18px',color:'#d0f5ff',
   backgroundColor:'#06162b',padding:{x:13,y:7},align:'center'})
   .setOrigin(.5,0).setDepth(125).setInteractive({useHandCursor:true});
 this._applyPerfMode=()=>{
  const m=this._perfMode,depth=(m===1||m===4),lamps=(m===2||m===4),vignette=(m===3||m===4);
  this._perfDepth=depth;
  this.midArchitecture.setVisible(depth);
  this.foregroundSilhouette.setVisible(depth);
  this.platformFaces.setVisible(depth);
  this.staticShadowLayer.setVisible(lamps);
  for(const l of this.staticLampGlow){l.glow.setVisible(lamps);l.core.setVisible(lamps);}
  this.sceneVignette.setVisible(vignette);
  if(!depth){
   this.farImage.x=W/2;
   this.revealBackground.x=W/2;this.revealMid.x=W/2;this.revealFocus.x=W/2;
   this.midArchitecture.x=0;this.foregroundSilhouette.x=0;
  }
  this._perfButton.setText('ГРАФИКА: '+this._perfLabels[m]+' ⟲');
 };
 this._perfButton.on('pointerdown',()=>{
  this._perfMode=(this._perfMode+1)%this._perfLabels.length;
  this._applyPerfMode();
 });
 this._applyPerfMode();""",
 'diagnostic graphics switching')
 html=once(html,
  '''updateVisualDepth(time,playerX){
 // Motion is subtle because this demo has a single fixed camera.''',
  '''updateVisualDepth(time,playerX){
 // Freeze v0.12 visual animation when only the older baseline or isolated lamp
 // and vignette layers are enabled. This separates render cost from CPU cost.
 if(!this._perfDepth)return;
 // Motion is subtle because this demo has a single fixed camera.''',
  'disable depth work in other modes')
 html=once(html,'платформера v0.13','платформера v0.14','document version')
 return html



# v0.15: collapse 3 full-screen geometry masks/background passes into one
# low-resolution light/shadow texture. Preserve the 3 falloff bands, occlusion,
# lamps, perspective planes, illuminated collectibles, 3D platforms and physics.
import re

V15_LIGHT=r'''
// Full-scene shadow map. One texture in place of three masked copies of the background.
function initCompositeLighting(scene){
 const canvas=document.createElement('canvas');canvas.width=480;canvas.height=270;
 const ctx=canvas.getContext('2d',{alpha:true});
 const texture=scene.textures.addCanvas('scene_v15_darkness',canvas);
 const image=scene.add.image(W/2,H/2,'scene_v15_darkness').setDisplaySize(W,H).setDepth(4);
 return {ctx,texture,image};
}
function paintCompositeLighting(light,ox,oy,outer,mid,core){
 const ctx=light.ctx;
 ctx.setTransform(.5,0,0,.5,0,0);
 ctx.globalCompositeOperation='source-over';
 ctx.clearRect(0,0,W,H);
 ctx.fillStyle='rgba(2,7,19,.74)';ctx.fillRect(0,0,W,H);
 ctx.globalCompositeOperation='destination-out';
 function reveal(points,amount){
  if(!points||points.length<2)return;
  ctx.fillStyle='rgba(0,0,0,'+amount+')';
  ctx.beginPath();ctx.moveTo(ox,oy);
  for(let i=0;i<points.length;i++)ctx.lineTo(points[i].x,points[i].y);
  ctx.closePath();ctx.fill();
 }
 // The three original distance/angle occlusion polygons are retained.
 reveal(outer,.44);reveal(mid,.53);reveal(core,.43);
 ctx.globalCompositeOperation='source-over';
 light.texture.refresh();
}
'''

V15_RAY=r'''function rayHitRect(ox,oy,dx,dy,r,maxDist){
 let near=0,far=maxDist;
 if(Math.abs(dx)<1e-7){
  if(ox<r.a||ox>r.b)return null;
 }else{
  let a=(r.a-ox)/dx,b=(r.b-ox)/dx;
  if(a>b){const swap=a;a=b;b=swap;}
  if(a>near)near=a;if(b<far)far=b;
  if(near>far)return null;
 }
 if(Math.abs(dy)<1e-7){
  if(oy<r.top||oy>r.bottom)return null;
 }else{
  let a=(r.top-oy)/dy,b=(r.bottom-oy)/dy;
  if(a>b){const swap=a;a=b;b=swap;}
  if(a>near)near=a;if(b<far)far=b;
  if(near>far)return null;
 }
 const hit=near>1.5?near:far>1.5?far:null;
 return hit!==null&&hit<maxDist?hit:null;
}
'''

def v15_replace(s,old,new,label):
 if s.count(old)!=1:raise AssertionError(label+': '+str(s.count(old)))
 return s.replace(old,new,1)

def v15_regex(s,pattern,new,label):
 s,n=re.subn(pattern,lambda m:new,s,count=1,flags=re.S)
 if n!=1:raise AssertionError(label+': '+str(n))
 return s

def upgrade_v15(html):
 html=v15_regex(html,r'function rayHitRect\(ox,oy,dx,dy,r,maxDist\)\{.*?(?=function visibleRayLength\()',V15_RAY,'ray GC elimination')
 html=v15_replace(html,'class Demo extends Phaser.Scene{',V15_LIGHT+'\nclass Demo extends Phaser.Scene{','single dynamic shadow layer')
 html=v15_replace(html,'this.add.rectangle(W/2,H/2,W,H,0x020713,0.74).setDepth(4);',
                  '// Darkness is composited into the single light/shadow texture.','remove old darkness')
 html=v15_regex(html,r'this\.revealMaskGraphics=this\.make\.graphics\(\{x:0,y:0,add:false\}\);.*?this\.revealFocus\.setMask\(this\.focusMaskGraphics\.createGeometryMask\(\)\);',
                'this.compositeLight=initCompositeLighting(this);','remove three masked background images')
 html=v15_replace(html,
  'fillBeamMask(this.revealMaskGraphics,ox,oy,outer);\n  fillBeamMask(this.midMaskGraphics,ox,oy,mid);\n  fillBeamMask(this.focusMaskGraphics,ox,oy,core);',
  'paintCompositeLighting(this.compositeLight,ox,oy,outer,mid,core);',
  'single lightmap refresh')
 html=v15_replace(html,'this._lightMs>=32&&','this._lightMs>=48&&','beam update interval')
 html=v15_replace(html,'this._lightMs%=32;','this._lightMs%=48;','beam update timer')
 html=v15_replace(html,'beamPolygon(ox,oy,ang,rad,295,occluders,40)','beamPolygon(ox,oy,ang,rad,295,occluders,28)','outer ray count')
 html=v15_replace(html,'beamPolygon(ox,oy,ang,rad,185,occluders,40)','beamPolygon(ox,oy,ang,rad,185,occluders,28)','mid ray count')
 html=v15_replace(html,'beamPolygon(ox,oy,ang,.125,252,occluders,18)','beamPolygon(ox,oy,ang,.125,252,occluders,16)','focus ray count')
 # Remove the v0.14 testing button. Full visual quality becomes the default.
 html=v15_regex(html,
  r'\s*// Developer diagnostic: switch individual v0\.12 layers without restarting\..*?this\._perfButton\.on\(.+?\}\);\s*this\._applyPerfMode\(\);',
  '','remove temporary graphics test UI')
 html=v15_regex(html,
  r'\s*// Freeze v0\.12 visual animation when only the older baseline or isolated lamp\n // and vignette layers are enabled\. This separates render cost from CPU cost\.\n if\(!this\._perfDepth\)return;',
  '','restore full depth animation')
 for x in ('revealBackground','revealMid','revealFocus'):
  html=v15_regex(html,r'\s*this\.'+x+r'\.x=W\*\.5-far;', '', 'unused '+x+' parallax')
 for x in ('revealMaskGraphics','focusMaskGraphics','midMaskGraphics','revealBackground','revealMid','revealFocus'):
  if x in html:raise AssertionError('stale mask reference: '+x)
 html=v15_replace(html,'платформера v0.14','платформера v0.15','version label')
 return html


if __name__ == '__main__':
    src = Path(sys.argv[1]); dst=Path(sys.argv[2]) if len(sys.argv)>2 else src
    output=patch(src.read_text('utf-8'))
    for upgrade in (upgrade_v04,upgrade_v05,upgrade_v06,upgrade_v07,upgrade_v08,upgrade_v09,upgrade_v10,upgrade_v11,upgrade_v12,upgrade_v13,upgrade_v14,upgrade_v15):
        output=upgrade(output)
    output=optimize_assets(output)
    dst.write_text(output,'utf-8')
    print(f'Patched {dst} ({len(output)} chars)')