#!/usr/bin/env node
// Повторяемая проба переноса 9+9 деталей стражника на утверждённые
// костные оси манекена. Не изменяет мастера, риг, IK или исходные атласы.
const fs=require('fs');
const path=require('path');
const os=require('os');
const {createCanvas,loadImage}=require('@napi-rs/canvas');
const root=__dirname;
const outDir=process.argv[2]||root;
const parts=['torso','rightUpperArm','rightForearm','leftUpperArm','leftForearm',
 'rightThigh','rightShin','leftThigh','leftShin'];
const cells={
 front:{torso:[0,0],rightUpperArm:[0,2],rightForearm:[0,1],leftUpperArm:[1,2],
  leftForearm:[1,0],rightThigh:[1,1],rightShin:[2,0],leftThigh:[2,2],leftShin:[2,1]},
 rear:{torso:[0,1],rightUpperArm:[0,2],rightForearm:[1,2],leftUpperArm:[0,0],
  leftForearm:[1,0],rightThigh:[1,1],rightShin:[2,2],leftThigh:[2,0],leftShin:[2,1]}
};
const mannequinMap={
 front:{torso:0,rightUpperArm:2,rightForearm:1,leftUpperArm:5,leftForearm:3,
  rightThigh:4,rightShin:6,leftThigh:8,leftShin:7},
 rear:{torso:0,rightUpperArm:2,rightForearm:5,leftUpperArm:1,leftForearm:4,
  rightThigh:3,rightShin:8,leftThigh:6,leftShin:7}
};
const mannequinAnchors={
 front:[
  [[.37,.18],[.404,.915]],[[.782,.094],[.43,.66]],[[.722,.194],[.226,.877]],
  [[.709,.09],[.37,.63]],[[.669,.109],[.283,.901]],[[.277,.207],[.772,.879]],
  [[.661,.086],[.646,.685]],[[.507,.082],[.620,.688]],[[.367,.111],[.693,.9]]
 ],
 rear:[
  [[.60,.145],[.47,.906]],[[.712,.186],[.211,.893]],[[.298,.182],[.699,.885]],
  [[.584,.133],[.380,.920]],[[.792,.082],[.340,.605]],[[.158,.089],[.610,.622]],
  [[.587,.127],[.295,.916]],[[.528,.072],[.242,.825]],[[.383,.068],[.309,.839]]
 ]
};
const guardAnchors={
 front:{
  torso:[[.48,.20],[.49,.92]],rightUpperArm:[[.55,.16],[.245,.864]],
  rightForearm:[[.745,.121],[.36,.61]],leftUpperArm:[[.50,.16],[.635,.898]],
  leftForearm:[[.411,.101],[.56,.62]],rightThigh:[[.51,.09],[.384,.940]],
  rightShin:[[.634,.10],[.57,.73]],leftThigh:[[.51,.09],[.603,.939]],
  leftShin:[[.595,.10],[.53,.74]]
 },
 rear:{
  torso:[[.49,.22],[.51,.94]],rightUpperArm:[[.43,.13],[.726,.903]],
  rightForearm:[[.250,.113],[.50,.59]],leftUpperArm:[[.58,.16],[.260,.879]],
  leftForearm:[[.712,.124],[.40,.60]],rightThigh:[[.53,.09],[.380,.941]],
  rightShin:[[.399,.10],[.50,.73]],leftThigh:[[.53,.09],[.334,.938]],
  leftShin:[[.460,.10],[.48,.74]]
 }
};
const shoulderMarks={front:{right:[.12,.40],left:[.86,.43]},
 rear:{right:[.91,.48],left:[.10,.46]}};
const garmentAllowance={torso:1.09,rightUpperArm:1.15,leftUpperArm:1.15,
 rightForearm:1.10,leftForearm:1.10,rightThigh:1.12,leftThigh:1.12,
 rightShin:1.15,leftShin:1.15};
// Ограничители на основе уже просмотренного на телефоне костюма: пользователь
// подтвердил улучшенную толщину. Автоподгонка не вправе снова раздуть ладони.
const reviewedWidths={
 front:{rightForearm:.68,leftForearm:.78,rightShin:.67,leftShin:.75},
 rear:{rightForearm:.63,leftForearm:.65,rightShin:.65,leftShin:.77}
};
const clamp=(x,min,max)=>Math.min(max,Math.max(min,x));
function imgFromFile(p){return loadImage(p)}
async function imgFromScript(p){
 const txt=fs.readFileSync(p,'utf8'),match=txt.match(/base64,([^"\s]+)/);
 if(!match)throw Error('No embedded atlas: '+p);
 // PNG with custom ancillary chunks is reliably decoded via a file path.
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'diablo34-template-'));
 const decoded=path.join(dir,'mannequin.png');
 try{
  fs.writeFileSync(decoded,Buffer.from(match[1],'base64'));
  return await loadImage(decoded);
 }finally{
  fs.unlinkSync(decoded);fs.rmdirSync(dir);
 }
}
function imageData(img){
 const c=createCanvas(img.width,img.height),g=c.getContext('2d',{willReadFrequently:true});
 g.drawImage(img,0,0);return g.getImageData(0,0,c.width,c.height);
}
// Тот же 8-связный alpha-порог, что в browser lab; +3 px у компонента.
function connected(img){
 const scale=Math.min(1,700/Math.max(img.width,img.height));
 const w=Math.round(img.width*scale),h=Math.round(img.height*scale);
 const c=createCanvas(w,h),g=c.getContext('2d',{willReadFrequently:true});
 g.drawImage(img,0,0,w,h);
 const px=g.getImageData(0,0,w,h).data,seen=new Uint8Array(w*h);
 const stack=new Int32Array(w*h),boxes=[];
 for(let pos=0;pos<w*h;pos++){
  if(seen[pos])continue;seen[pos]=1;
  if(px[pos*4+3]<35)continue;
  let head=1,count=0,minX=w,minY=h,maxX=0,maxY=0;stack[0]=pos;
  while(head){
   const at=stack[--head],y=Math.floor(at/w),x=at-y*w;
   count++;minX=Math.min(minX,x);minY=Math.min(minY,y);
   maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);
   for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
    const nx=x+dx,ny=y+dy;if(nx<0||ny<0||nx>=w||ny>=h)continue;
    const n=ny*w+nx;if(seen[n])continue;seen[n]=1;
    if(px[n*4+3]>=35)stack[head++]=n;
   }
  }
  if(count>=Math.max(16,w*h*.00012)){
   const x=Math.max(0,Math.floor(minX/scale)-3),y=Math.max(0,Math.floor(minY/scale)-3);
   const right=Math.min(img.width,Math.ceil((maxX+1)/scale)+3);
   const bottom=Math.min(img.height,Math.ceil((maxY+1)/scale)+3);
   boxes.push({x,y,w:right-x,h:bottom-y,count});
  }
 }
 return boxes.sort((a,b)=>b.count-a.count).slice(0,9).sort((a,b)=>a.y-b.y||a.x-b.x);
}
function guardBox(boxes,view,part){
 const [row,col]=cells[view][part];
 const result=boxes.find(b=>Math.floor((b.y+b.h/2)/512)===row&&
  Math.floor((b.x+b.w/2)/(1024/3))===col);
 if(!result)throw Error('Missing '+view+' '+part);return result;
}
function frame(box,anchors){
 const a={x:box.w*anchors[0][0],y:box.h*anchors[0][1]};
 const b={x:box.w*anchors[1][0],y:box.h*anchors[1][1]};
 const d=Math.hypot(b.x-a.x,b.y-a.y),ux=(b.x-a.x)/d,uy=(b.y-a.y)/d;
 return {a,b,d,ux,uy,vx:-uy,vy:ux};
}
function percentile(sorted,p){return sorted[Math.min(sorted.length-1,Math.floor((sorted.length-1)*p))]}
function silhouette(imgData,box,f,part){
 const cross=[],tail=[],uEnd=[];const px=imgData.data,w=imgData.width;
 const shaftEnd=part.endsWith('Forearm')?.57:part.endsWith('Shin')?.72:.84;
 for(let y=0;y<box.h;y+=2)for(let x=0;x<box.w;x+=2){
  const i=((y+box.y)*w+x+box.x)*4;if(px[i+3]<140)continue;
  const dx=x-f.a.x,dy=y-f.a.y,u=dx*f.ux+dy*f.uy;
  const v=dx*f.vx+dy*f.vy;
  if(u>=f.d*.19&&u<=f.d*shaftEnd)cross.push(v);
  if(u>f.d)tail.push(u-f.d);
  uEnd.push(u);
 }
 if(cross.length<30||uEnd.length<40)throw Error('Missing opaque silhouette');
 cross.sort((a,b)=>a-b);tail.sort((a,b)=>a-b);
 return {width:percentile(cross,.98)-percentile(cross,.02),
  tail:tail.length>10?percentile(tail,.99):0};
}
function graphicsMatrix(src,dst,along,across,origin){
 return [dst.ux*along*src.ux+dst.vx*across*src.vx,
  dst.uy*along*src.ux+dst.vy*across*src.vx,
  dst.ux*along*src.uy+dst.vx*across*src.vy,
  dst.uy*along*src.uy+dst.vy*across*src.vy,
  origin.x,origin.y];
}
function clipAtDistal(g,src,tail){
 const e=src.b,L=2000,sign=tail?1:-1;
 g.beginPath();g.moveTo(e.x+src.vx*L,e.y+src.vy*L);
 g.lineTo(e.x-src.vx*L,e.y-src.vy*L);
 g.lineTo(e.x-src.vx*L+src.ux*L*sign,e.y-src.vy*L+src.uy*L*sign);
 g.lineTo(e.x+src.vx*L+src.ux*L*sign,e.y+src.vy*L+src.uy*L*sign);
 g.closePath();g.clip();
}
function alignPiece(img,box,src,ref,across,tailAlong,hasTail){
 const c=createCanvas(1100,1250),g=c.getContext('2d');
 const origin={x:550,y:350},along=ref.d/src.d;
 function render(appendage){
  const position=appendage?{x:origin.x+ref.ux*ref.d,y:origin.y+ref.uy*ref.d}:origin;
  const old=appendage?src.b:src.a;
  const matrix=graphicsMatrix(src,ref,appendage?tailAlong:along,across,position);
  g.save();g.transform(...matrix);g.translate(-old.x,-old.y);
  if(hasTail)clipAtDistal(g,src,appendage);
  g.drawImage(img,box.x,box.y,box.w,box.h,0,0,box.w,box.h);g.restore();
 }
 render(false);if(hasTail)render(true);
 const d=g.getImageData(0,0,c.width,c.height).data;
 let left=c.width,top=c.height,right=0,bottom=0;
 for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++){
  if(d[(y*c.width+x)*4+3]<35)continue;
  left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);
 }
 if(right<=left||bottom<=top)throw Error('Result sprite empty');
 const crop={x:Math.max(0,left-6),y:Math.max(0,top-6),
  w:Math.min(c.width,right+7)-Math.max(0,left-6),
  h:Math.min(c.height,bottom+7)-Math.max(0,top-6)};
 return {canvas:c,crop,anchor0:origin,
  anchor1:{x:origin.x+ref.ux*ref.d,y:origin.y+ref.uy*ref.d},
  transformMark(local){
   const dx=local.x-src.a.x,dy=local.y-src.a.y;
   const u=dx*src.ux+dy*src.uy,v=dx*src.vx+dy*src.vy;
   return {x:origin.x+ref.ux*u*along+ref.vx*v*across,
    y:origin.y+ref.uy*u*along+ref.vy*v*across};
  }};
}
async function assemble(view){
 const [src,ref]=await Promise.all([
  imgFromFile(path.join(root,view==='front'?'guard-sw-atlas.webp':'guard-ne-atlas.webp')),
  imgFromScript(path.join(root,view==='front'?'mannequin-sheet.js':'mannequin-back-sheet.js'))
 ]);
 const guardBoxes=connected(src),manBoxes=connected(ref);
 if(guardBoxes.length!==9||manBoxes.length!==9)throw Error('Expected 9+9 sprites '+view);
 const sd=imageData(src),rd=imageData(ref),out=createCanvas(1024,1536),g=out.getContext('2d');
 const marks={},metrics=[];let shoulders={};
 for(const part of parts){
  const sb=guardBox(guardBoxes,view,part),mb=manBoxes[mannequinMap[view][part]];
  const source=frame(sb,guardAnchors[view][part]);
  const target=frame(mb,mannequinAnchors[view][mannequinMap[view][part]]);
  const sw=silhouette(sd,sb,source,part),tw=silhouette(rd,mb,target,part);
  let across=clamp(tw.width/sw.width*garmentAllowance[part],.40,1.7);
  const hasTail=part.endsWith('Forearm')||part.endsWith('Shin');
  const boneRatio=target.d/source.d;
  if(hasTail)across=Math.min(across,reviewedWidths[view][part]*boneRatio*1.12);
  const tailAlong=hasTail?clamp(tw.tail/Math.max(1,sw.tail)*
   (part.endsWith('Shin')?1.12:1.02),boneRatio*.85,boneRatio*1.12):boneRatio;
  const prepared=alignPiece(src,sb,source,target,across,tailAlong,hasTail);
  const [row,col]=cells[view][part],cw=1024/3,ch=512;
  const {crop}=prepared;
  const scale=Math.min((cw-16)/crop.w,(ch-16)/crop.h,1);
  const dst={x:col*cw+(cw-crop.w*scale)/2,y:row*ch+(ch-crop.h*scale)/2,
   w:crop.w*scale,h:crop.h*scale};
  g.drawImage(prepared.canvas,crop.x,crop.y,crop.w,crop.h,dst.x,dst.y,dst.w,dst.h);
  function globalPoint(p){return {x:dst.x+(p.x-crop.x)*scale,y:dst.y+(p.y-crop.y)*scale}}
  marks[part]={anchors:[globalPoint(prepared.anchor0),globalPoint(prepared.anchor1)]};
  if(part==='torso')for(const side of ['right','left']){
   const m=shoulderMarks[view][side];
   shoulders[side]=globalPoint(prepared.transformMark({x:sb.w*m[0],y:sb.h*m[1]}));
  }
  metrics.push({part,refWidth:Math.round(tw.width),guardWidth:Math.round(sw.width),
   xScale:+across.toFixed(3),lengthScale:+(target.d/source.d).toFixed(3),
   tailScale:+tailAlong.toFixed(3),cellScale:+scale.toFixed(3)});
 }
 const outputName=view==='front'?'guard-sw-template.webp':'guard-ne-template.webp';
 const buf=out.toBuffer('image/webp',{quality:88});
 const outputImage=await loadImage(buf);
 const newBoxes=connected(outputImage);
 if(newBoxes.length!==9)throw Error('After normalization found '+newBoxes.length+' parts, expected 9');
 const anchors={},fittedShoulders={};
 for(const part of parts){
  const b=guardBox(newBoxes,view,part),points=marks[part].anchors;
  const normalized=points.map(p=>[+(p.x-b.x)/b.w,+(p.y-b.y)/b.h]);
  if(normalized.some(pt=>pt.some(x=>x<0||x>1||!Number.isFinite(x))))
   throw Error('Anchor outside silhouette '+view+' '+part+' '+JSON.stringify(normalized));
  anchors[part]=normalized.map(pt=>pt.map(x=>+x.toFixed(4)));
  if(part==='torso')for(const side of ['right','left']){
   const p=shoulders[side];fittedShoulders[side]=[
    +((p.x-b.x)/b.w).toFixed(4),+((p.y-b.y)/b.h).toFixed(4)];
  }
 }
 fs.mkdirSync(outDir,{recursive:true});
 fs.writeFileSync(path.join(outDir,outputName),buf);
 return {view,filename:outputName,size:buf.length,anchors,shoulders:fittedShoulders,metrics};
}
(async()=>{
 const [front,rear]=await Promise.all([assemble('front'),assemble('rear')]);
 const final={generatedAt:'2026-11-04',source:'mannequin atlas silhouette axes',front,rear};
 fs.writeFileSync(path.join(outDir,'guard-template-fit.json'),JSON.stringify(final,null,2)+'\n');
 console.log(JSON.stringify({front:front.metrics,rear:rear.metrics,
  files:[front.filename,rear.filename,'guard-template-fit.json']},null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
