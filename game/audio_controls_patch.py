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

if __name__ == '__main__':
    src = Path(sys.argv[1]); dst=Path(sys.argv[2]) if len(sys.argv)>2 else src
    output=patch(src.read_text('utf-8'))
    dst.write_text(output,'utf-8')
    print(f'Patched {dst} ({len(output)} chars)')