#!/usr/bin/env python3
"""Generate the AI chain rotation dashboard (index.html) from ai.perf.json.

Usage:
  python3 gen_dashboard.py --out <widget workspace>/index.html [--standalone-out <path>]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 产业链轮动看板</title>
<style>
:root{--daimon-widget-host-safe-inline-end:190px;--daimon-widget-host-safe-block-start:44px}
.kimi-host-safe-context{container-type:inline-size}
.kimi-host-safe-header{box-sizing:border-box;min-block-size:var(--daimon-widget-host-safe-block-start,44px);padding-inline-end:var(--daimon-widget-host-safe-inline-end,190px)}
@container (max-width:419px){.kimi-host-safe-header{min-block-size:0;padding-block-start:var(--daimon-widget-host-safe-block-start,44px);padding-inline-end:0}}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent}
body{font-family:var(--kimi-font-sans,-apple-system,"PingFang SC","Microsoft YaHei",sans-serif);color:var(--kimi-color-text-primary);letter-spacing:0}
.wrap{max-width:1080px;margin:0 auto;padding:14px 18px 20px}
.up{color:var(--kimi-color-danger)}
.dn{color:var(--kimi-color-positive)}
h1{font-size:19px;font-weight:650;line-height:1.3}
.sub{color:var(--kimi-color-text-secondary);font-size:12px;margin-top:4px}
.stats{display:flex;gap:16px;flex-wrap:wrap;margin-top:10px}
.stat output{display:block;font-size:20px;font-weight:650;line-height:1.15;font-variant-numeric:tabular-nums}
.stat span{font-size:11px;color:var(--kimi-color-text-tertiary)}
section{margin-top:20px}
.sec-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.sec-head h2{font-size:15px;font-weight:650}
.sec-head .hint{font-size:11px;color:var(--kimi-color-text-tertiary)}
.sec-head::after{content:"";flex:1;height:1px;background:var(--kimi-color-border);align-self:center}
.legend{display:flex;gap:12px;align-items:center;font-size:11px;color:var(--kimi-color-text-tertiary);margin-top:6px;flex-wrap:wrap}
.chipbar{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.chipbtn{font-family:inherit;font-size:12px;padding:6px 10px;border-radius:7px;cursor:pointer;border:1px solid var(--kimi-color-border);background:var(--kimi-color-surface);color:var(--kimi-color-text-primary)}
.chipbtn:hover{border-color:var(--kimi-color-accent)}
.chipbtn:focus-visible{outline:2px solid var(--kimi-color-accent);outline-offset:1px}
.chipbtn.on{background:var(--kimi-color-accent);color:var(--kimi-color-on-accent);border-color:var(--kimi-color-accent)}

/* heatmap */
.hm{width:100%;border-collapse:collapse;margin-top:10px;font-variant-numeric:tabular-nums}
.hm th,.hm td{padding:6px 8px;font-size:12px;text-align:right;border-bottom:1px solid var(--kimi-color-border)}
.hm th{font-weight:600;color:var(--kimi-color-text-secondary);text-align:right;white-space:nowrap}
.hm td.seg,.hm th.seg{text-align:left;white-space:nowrap;cursor:pointer}
.hm tr.sel td.seg{color:var(--kimi-color-accent);font-weight:650}
.hm td.c{border-radius:4px;text-align:right;cursor:pointer;min-width:56px}
.hm td.na{color:var(--kimi-color-text-quaternary)}
.hmwrap{overflow-x:auto}

/* quadrant */
.quad{width:100%;margin-top:6px}
.quad .lbl{font-size:11px;fill:var(--kimi-color-text-tertiary)}
.quad .seg-lbl{font-size:10.5px;fill:var(--kimi-color-text-primary)}
.quad .axis{stroke:var(--kimi-color-border);stroke-width:1}
.quad .mid{stroke:var(--kimi-color-text-quaternary);stroke-width:1;stroke-dasharray:4 3}
.quad circle{fill:var(--kimi-color-accent);fill-opacity:.45;stroke:var(--kimi-color-accent);stroke-width:1.2;cursor:pointer}
.quad circle.sel{fill-opacity:.95}
.quad .tag{font-size:10.5px;font-weight:650}

/* money flow */
.mflow{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.mcard{border:1px solid var(--kimi-color-border);border-radius:10px;background:var(--kimi-color-surface-raised);padding:10px 12px;min-width:0}
.mcard h3{font-size:13px;font-weight:650;margin-bottom:8px}
.mrow{display:flex;align-items:center;gap:8px;font-size:12px;padding:4px 0;min-width:0}
.mrow .nm{flex:0 0 108px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--kimi-color-text-secondary)}
.mrow .bar{flex:1;height:8px;border-radius:4px;background:var(--kimi-color-surface-muted);position:relative;min-width:0}
.mrow .bar i{position:absolute;top:0;bottom:0;border-radius:4px}
.mrow .val{flex:0 0 64px;text-align:right;font-variant-numeric:tabular-nums}
.cand{margin-top:10px;border:1px dashed var(--kimi-color-accent);border-radius:10px;padding:10px 12px}
.cand h3{font-size:13px;font-weight:650;color:var(--kimi-color-accent)}
.cand p{font-size:12px;color:var(--kimi-color-text-secondary);margin-top:6px;line-height:1.7}
.cand .flag{font-size:10px;border:1px solid var(--kimi-color-accent);color:var(--kimi-color-accent);border-radius:99px;padding:0 6px;margin-left:4px}

/* nav */
.navwrap{margin-top:6px}
.nav svg{width:100%;height:auto}
.nav .ln{fill:none;stroke-width:1.6}
.nav .lbl{font-size:11px;fill:var(--kimi-color-text-primary)}
.nav .axis{stroke:var(--kimi-color-border)}
.nav .grid{stroke:var(--kimi-color-border);stroke-dasharray:2 4;opacity:.6}
.nav .ylb{font-size:10px;fill:var(--kimi-color-text-tertiary)}

/* drill */
.drill{margin-top:10px}
.drow{display:flex;align-items:center;gap:8px;font-size:12px;padding:3px 0;min-width:0}
.drow .nm{flex:0 0 130px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.drow .cd{flex:0 0 76px;font-family:var(--kimi-font-mono,ui-monospace,monospace);font-size:11px;color:var(--kimi-color-text-tertiary)}
.drow .bar{flex:1;height:12px;position:relative;min-width:0}
.drow .bar i{position:absolute;top:1px;bottom:1px;border-radius:3px;min-width:1px}
.drow .zero{position:absolute;top:-1px;bottom:-1px;width:1px;background:var(--kimi-color-text-quaternary)}
.drow .val{flex:0 0 70px;text-align:right;font-variant-numeric:tabular-nums}
footer{margin-top:22px;padding-top:10px;border-top:1px solid var(--kimi-color-border);font-size:11px;color:var(--kimi-color-text-tertiary);line-height:1.7}
@media (max-width:759px){.mflow{grid-template-columns:1fr}.drow .cd{display:none}.drow .nm{flex-basis:96px}}
@media (max-width:519px){.wrap{padding:10px 12px 16px}h1{font-size:16px}.hm th,.hm td{padding:5px 5px;font-size:11px}.mrow .nm{flex-basis:88px}}
</style>
</head>
<body>
<main class="wrap kimi-host-safe-context">
  <header class="kimi-host-safe-header">
    <h1>AI 产业链资金轮动看板</h1>
    <p class="sub" id="metaLine"></p>
    <div class="stats" role="group" aria-label="看板概览">
      <div class="stat"><output id="stCov">—</output><span>覆盖公司</span></div>
      <div class="stat"><output id="stSeg">19</output><span>环节</span></div>
      <div class="stat"><output id="stTop">—</output><span>年初以来最强环节</span></div>
      <div class="stat"><output id="stHot">—</output><span>近1月最强环节</span></div>
    </div>
  </header>

  <section aria-label="月度收益热力图">
    <div class="sec-head"><h2>① 月度收益热力图</h2><span class="hint">环节等权月收益，红涨绿跌；点击行下钻公司</span></div>
    <div class="legend"><span>色阶：</span><span id="hmScale"></span><span>（±15% 饱和）</span></div>
    <div class="hmwrap"><table class="hm" id="hm"></table></div>
  </section>

  <section aria-label="轮动四象限">
    <div class="sec-head"><h2>② 轮动四象限</h2><span class="hint">X=年初以来涨幅，Y=近1月涨幅，气泡=成交额占比</span></div>
    <div class="legend">
      <span class="up">右上 持续强势</span><span class="dn">右下 高位退潮</span>
      <span style="color:var(--kimi-color-accent)">左上 逆势转强</span><span>左下 持续弱势</span>
    </div>
    <svg class="quad" id="quad" viewBox="0 0 760 460" role="img" aria-label="环节轮动四象限散点图"></svg>
  </section>

  <section aria-label="资金方向">
    <div class="sec-head"><h2>③ 资金方向</h2><span class="hint">成交额占比 = 环节成交额 / 全链（近1周 vs 4周前）</span></div>
    <div class="mflow">
      <div class="mcard"><h3>占比上升（资金流入）</h3><div id="flowUp"></div></div>
      <div class="mcard"><h3>占比下降（资金流出）</h3><div id="flowDn"></div></div>
    </div>
    <div class="cand" id="cand"></div>
  </section>

  <section aria-label="环节净值曲线" class="nav">
    <div class="sec-head"><h2>④ 环节净值曲线</h2><span class="hint">2025-12-31 = 100，等权</span></div>
    <div class="chipbar" id="navBtns"></div>
    <div class="navwrap"><svg id="navSvg" viewBox="0 0 760 360" role="img" aria-label="环节净值曲线"></svg></div>
  </section>

  <section aria-label="公司下钻" class="drill">
    <div class="sec-head"><h2>⑤ 公司下钻</h2><span class="hint">选择环节与区间，查看公司涨幅排序</span></div>
    <div class="chipbar" id="anchorBtns"></div>
    <div id="drillTitle" class="sub" style="margin-top:8px"></div>
    <div id="drill"></div>
  </section>

  <footer id="foot"></footer>
</main>

<script id="perfData" type="application/json">__DATA__</script>
<script>
(function(){
var D=JSON.parse(document.getElementById('perfData').textContent);
var M=D.meta, SEG=D.segments, COS=D.companies;
var pct=function(v,d){if(v==null)return"—";var x=(v*100).toFixed(d==null?1:d);return(v>0?"+":"")+x+"%"};
function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e}
function tok(name){return getComputedStyle(document.body).getPropertyValue(name).trim()}
var C_UP,C_DN,C_AC,C_TX,C_TX2,C_BD;
function readToks(){C_UP=tok('--kimi-color-danger');C_DN=tok('--kimi-color-positive');C_AC=tok('--kimi-color-accent');C_TX=tok('--kimi-color-text-primary');C_TX2=tok('--kimi-color-text-tertiary');C_BD=tok('--kimi-color-border')}
readToks();

/* header */
document.getElementById('metaLine').textContent=
  "数据截至 "+M.px_end+" 收盘 ｜ 前复权日线（iFinD）｜ 锚点：年初以来("+M.anchors.ytd+") / 4月以来("+M.anchors.apr+") / 近1月 / 近3月";
document.getElementById('stCov').textContent=M.covered;
var byYtd=SEG.slice().sort(function(a,b){return b.ret.ytd_mean-a.ret.ytd_mean});
var byM1=SEG.slice().sort(function(a,b){return b.ret.m1_mean-a.ret.m1_mean});
document.getElementById('stTop').textContent=byYtd[0].short;
document.getElementById('stHot').textContent=byM1[0].short;

/* ① heatmap */
var months=M.months;
var hm=document.getElementById('hm');
var tr=el('tr');tr.appendChild(el('th','seg','环节'));
months.forEach(function(m){tr.appendChild(el('th',null,m.slice(2).replace('-','/')))});
tr.appendChild(el('th',null,'年初以来'));
hm.appendChild(tr);
function hmCell(v){
  var td=el('td','c');
  if(v==null){td.className='c na';td.textContent='—';return td}
  var k=Math.min(Math.abs(v)/0.15,1);
  var col=v>0?C_UP:C_DN;
  td.style.background='color-mix(in srgb,'+col+' '+(k*72+4)+'%,transparent)';
  td.textContent=(v*100).toFixed(1);
  td.title=(v*100).toFixed(2)+'%';
  return td;
}
var selSegId=null;
SEG.forEach(function(s){
  var r=el('tr');r.dataset.seg=s.id;
  var nm=el('td','seg',s.short);nm.title=s.name;
  nm.addEventListener('click',function(){selSegId=s.id;drawDrill();markHmSel()});
  r.appendChild(nm);
  months.forEach(function(m){var c=hmCell(s.monthly[m]);c.addEventListener('click',function(){selSegId=s.id;drawDrill();markHmSel()});r.appendChild(c)});
  var ytd=el('td',null,pct(s.ret.ytd_mean));ytd.style.fontWeight='600';
  ytd.className=s.ret.ytd_mean>0?'up':'dn';
  r.appendChild(ytd);
  hm.appendChild(r);
});
function markHmSel(){
  hm.querySelectorAll('tr').forEach(function(r){r.classList.toggle('sel',r.dataset.seg===selSegId)});
}
document.getElementById('hmScale').innerHTML=
  '<span style="display:inline-block;width:70px;height:8px;border-radius:4px;background:linear-gradient(90deg,'+C_DN+',transparent 50%,'+C_UP+')"></span>';

/* ② quadrant */
var qs=document.getElementById('quad'),W=760,H=460,PL=56,PR=16,PT=16,PB=40;
var xs=SEG.map(function(s){return s.ret.ytd_mean}),ys=SEG.map(function(s){return s.ret.m1_mean});
var x0=Math.min.apply(null,xs),x1=Math.max.apply(null,xs),y0=Math.min.apply(null,ys),y1=Math.max.apply(null,ys);
var mx=(x0+x1)/2; x0-=Math.abs(mx)*0.15+0.02;x1+=Math.abs(mx)*0.15+0.02;
var my=(y0+y1)/2; y0-=Math.abs(my)*0.2+0.02;y1+=Math.abs(my)*0.2+0.02;
function X(v){return PL+(v-x0)/(x1-x0)*(W-PL-PR)}
function Y(v){return H-PB-(v-y0)/(y1-y0)*(H-PT-PB)}
var sh=SEG.map(function(s){return s.share_now||0}),shMax=Math.max.apply(null,sh);
function R(s){return 6+18*Math.sqrt((s.share_now||0)/shMax)}
function line(x1_,y1_,x2_,y2_,cls){var l=document.createElementNS('http://www.w3.org/2000/svg','line');l.setAttribute('x1',x1_);l.setAttribute('y1',y1_);l.setAttribute('x2',x2_);l.setAttribute('y2',y2_);l.setAttribute('class',cls);qs.appendChild(l)}
function text(x,y,str,cls,anchor){var t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',x);t.setAttribute('y',y);t.setAttribute('class',cls);if(anchor)t.setAttribute('text-anchor',anchor);t.textContent=str;qs.appendChild(t);return t}
line(PL,PT,PL,H-PB,'axis');line(PL,H-PB,W-PR,H-PB,'axis');
line(X(0),PT,X(0),H-PB,'mid');line(PL,Y(0),W-PR,Y(0),'mid');
text(PL-8,Y(0)+3,'0','ylb','end');text(X(0),H-PB+16,'0','ylb','middle');
text(W-PR-2,H-PB+16,'年初以来 →','lbl','end');text(PL+4,PT+4,'↑ 近1月','lbl');
text(W-PR-4,PT+14,'年初以来中位数 '+pct(M.chain_median.ytd),'lbl','end');
var medX=M.chain_median.ytd,medY=M.chain_median.m1;
if(medX!=null)line(X(medX),PT,X(medX),H-PB,'mid');
if(medY!=null)line(PL,Y(medY),W-PR,Y(medY),'mid');
var qSel=null;
SEG.forEach(function(s){
  var cx=X(s.ret.ytd_mean),cy=Y(s.ret.m1_mean),r=R(s);
  var c=document.createElementNS('http://www.w3.org/2000/svg','circle');
  c.setAttribute('cx',cx);c.setAttribute('cy',cy);c.setAttribute('r',r);
  c.dataset.seg=s.id;
  var tip=document.createElementNS('http://www.w3.org/2000/svg','title');
  tip.textContent=s.short+'：年初以来'+pct(s.ret.ytd_mean)+'，近1月'+pct(s.ret.m1_mean)+'，成交额占比'+pct(s.share_now,2);
  c.appendChild(tip);
  c.addEventListener('click',function(){
    selSegId=s.id;drawDrill();markHmSel();
    if(qSel)qSel.classList.remove('sel');qSel=c;c.classList.add('sel');
  });
  qs.appendChild(c);
  var anchor=cx>X(medX==null?0:medX)?'end':'start';
  var lx=cx+(anchor==='end'?-r-4:r+4);
  var t=text(lx,cy+3.5,s.short,'seg-lbl',anchor);
});
/* quadrant tags */
text(X(medX)+(W-PR-X(medX))/2,Y(medY)-6,'持续强势','tag','middle').style.fill=C_UP;
text(X(medX)+(W-PR-X(medX))/2,Y(medY)+16,'高位退潮','tag','middle').style.fill=C_DN;
text(PL+6,Y(medY)-6,'逆势转强','tag','start').style.fill=C_AC;
text(PL+6,Y(medY)+16,'持续弱势','tag','start').style.fill=C_TX2;

/* ③ money flow */
function flowRows(id,list,color){
  var box=document.getElementById(id);
  if(!list.length){box.appendChild(el('p','sub','无'));return}
  var mx=Math.max.apply(null,list.map(function(s){return Math.abs(s.share_delta)}));
  list.forEach(function(s){
    var row=el('div','mrow');
    row.appendChild(el('span','nm',s.short));
    var bar=el('span','bar'),i=el('i');
    i.style.width=(Math.abs(s.share_delta)/mx*100)+'%';
    i.style.background=color;i.style.left='0';
    bar.appendChild(i);row.appendChild(bar);
    var v=el('span','val',(s.share_delta>0?'+':'')+(s.share_delta*100).toFixed(2)+'pp');
    v.className='val '+(s.share_delta>0?'up':'dn');
    row.appendChild(v);
    box.appendChild(row);
  });
}
var up5=SEG.filter(function(s){return s.share_delta>0}).sort(function(a,b){return b.share_delta-a.share_delta}).slice(0,5);
var dn5=SEG.filter(function(s){return s.share_delta<0}).sort(function(a,b){return a.share_delta-b.share_delta}).slice(0,5);
flowRows('flowUp',up5,C_UP);flowRows('flowDn',dn5,C_DN);
/* candidates */
var cand=SEG.filter(function(s){return s.flags.indexOf('转强')>=0});
var candBox=document.getElementById('cand');
candBox.appendChild(el('h3',null,'补涨/转强候选（年初以来跑输全链中位数，近1月跑赢）'));
var cp=el('p');
cand.forEach(function(s,i){
  var b=el('span',null,s.short);
  b.style.fontWeight='600';b.style.cursor='pointer';
  b.addEventListener('click',function(){selSegId=s.id;drawDrill();markHmSel()});
  cp.appendChild(b);
  var fl=el('span','flag','年初以来'+pct(s.ret.ytd_mean)+' → 近1月'+pct(s.ret.m1_mean)+(s.flags.indexOf('放量')>=0?' · 放量':''));
  cp.appendChild(fl);
  if(i<cand.length-1)cp.appendChild(document.createTextNode('　'));
});
candBox.appendChild(cp);

/* ④ NAV */
var navSvg=document.getElementById('navSvg');
var navMode='top';
var navBtnBox=document.getElementById('navBtns');
[['top','最强 5 环节'],['bottom','最弱 5 环节'],['all','全部 19 环节']].forEach(function(m){
  var b=el('button','chipbtn'+(m[0]===navMode?' on':''),m[1]);b.type='button';
  b.addEventListener('click',function(){navMode=m[0];navBtnBox.querySelectorAll('button').forEach(function(x){x.classList.remove('on')});b.classList.add('on');drawNav()});
  navBtnBox.appendChild(b);
});
function drawNav(){
  navSvg.textContent='';
  var list=SEG.slice();
  if(navMode==='top')list=byYtd.slice(0,5);
  else if(navMode==='bottom')list=byYtd.slice(-5).reverse();
  var NW=760,NH=360,NPL=44,NPR=150,NPT=14,NPB=26;
  var allV=[];list.forEach(function(s){s.nav.forEach(function(p){allV.push(p.v)})});
  if(!allV.length)return;
  var v0=Math.min.apply(null,allV),v1=Math.max.apply(null,allV),pad=(v1-v0)*0.08+1;v0-=pad;v1+=pad;
  var dates=list[0].nav.map(function(p){return p.d});
  function NX(i){return NPL+i/(dates.length-1)*(NW-NPL-NPR)}
  function NY(v){return NH-NPB-(v-v0)/(v1-v0)*(NH-NPT-NPB)}
  for(var g=0;g<=4;g++){var vv=v0+(v1-v0)*g/4,y=NY(vv);
    var gl=document.createElementNS('http://www.w3.org/2000/svg','line');
    gl.setAttribute('x1',NPL);gl.setAttribute('y1',y);gl.setAttribute('x2',NW-NPR);gl.setAttribute('y2',y);gl.setAttribute('class','grid');navSvg.appendChild(gl);
    var gt=document.createElementNS('http://www.w3.org/2000/svg','text');
    gt.setAttribute('x',NPL-6);gt.setAttribute('y',y+3);gt.setAttribute('class','ylb');gt.setAttribute('text-anchor','end');gt.textContent=vv.toFixed(0);navSvg.appendChild(gt);}
  if(dates.length){
    var t0=document.createElementNS('http://www.w3.org/2000/svg','text');
    t0.setAttribute('x',NPL);t0.setAttribute('y',NH-8);t0.setAttribute('class','ylb');t0.textContent=dates[0];navSvg.appendChild(t0);
    var t1=t0.cloneNode();t1.setAttribute('x',NW-NPR);t1.setAttribute('text-anchor','end');t1.textContent=dates[dates.length-1];navSvg.appendChild(t1);
  }
  var palette=navMode==='bottom'?[C_DN,C_DN,C_DN,C_DN,C_DN]:(navMode==='top'?[C_UP,C_UP,C_UP,C_UP,C_UP]:null);
  list.forEach(function(s,idx){
    var col=palette?palette[idx]:C_AC;
    if(navMode==='top'&&palette)col='color-mix(in srgb,'+C_UP+' '+(100-idx*14)+'%,'+C_TX2+')';
    if(navMode==='bottom'&&palette)col='color-mix(in srgb,'+C_DN+' '+(100-idx*14)+'%,'+C_TX2+')';
    var pts=s.nav.map(function(p,i){return NX(i).toFixed(1)+','+NY(p.v).toFixed(1)}).join(' ');
    var pl=document.createElementNS('http://www.w3.org/2000/svg','polyline');
    pl.setAttribute('points',pts);pl.setAttribute('class','ln');pl.setAttribute('stroke',col);
    if(navMode==='all')pl.setAttribute('opacity','0.75');
    navSvg.appendChild(pl);
    var last=s.nav[s.nav.length-1];
    var lt=document.createElementNS('http://www.w3.org/2000/svg','text');
    lt.setAttribute('x',NW-NPR+8);lt.setAttribute('y',NY(last.v)+3.5);lt.setAttribute('class','lbl');
    lt.textContent=s.short+' '+last.v.toFixed(0);
    navSvg.appendChild(lt);
    /* de-collide: nudge overlapping end labels */
    var prev=navSvg.querySelectorAll('text.lbl');
    for(var k=0;k<prev.length-1;k++){
      var py=parseFloat(prev[k].getAttribute('y')),cy=parseFloat(lt.getAttribute('y'));
      if(Math.abs(py-cy)<11)lt.setAttribute('y',py+11);
    }
  });
}
drawNav();

/* ⑤ drill */
var anchors=[['ytd','年初以来'],['apr','4月以来'],['m1','近1月'],['m3','近3月']];
var curAnchor='apr';
var abBox=document.getElementById('anchorBtns');
anchors.forEach(function(a){
  var b=el('button','chipbtn'+(a[0]===curAnchor?' on':''),a[1]);b.type='button';
  b.addEventListener('click',function(){curAnchor=a[0];abBox.querySelectorAll('button').forEach(function(x){x.classList.remove('on')});b.classList.add('on');drawDrill()});
  abBox.appendChild(b);
});
var coById={};COS.forEach(function(c){coById[c.c]=c});
function drawDrill(){
  var box=document.getElementById('drill');box.textContent='';
  var seg=SEG.filter(function(s){return s.id===selSegId})[0];
  if(!seg){box.appendChild(el('p','sub','← 点击上方热力图行、四象限气泡或候选环节，查看公司明细'));document.getElementById('drillTitle').textContent='';return}
  var aLabel=anchors.filter(function(a){return a[0]===curAnchor})[0][1];
  document.getElementById('drillTitle').textContent=seg.name+'（'+seg.n_co+' 家）· '+aLabel+' · 环节等权 '+pct(seg.ret[curAnchor+'_mean'])+' / 中位 '+pct(seg.ret[curAnchor+'_med']);
  var list=COS.filter(function(c){return c.seg===seg.id&&c.rets[curAnchor]!=null})
    .sort(function(a,b){return b.rets[curAnchor]-a.rets[curAnchor]});
  var mx=Math.max.apply(null,list.map(function(c){return Math.abs(c.rets[curAnchor])}));
  var zPos=62;
  list.forEach(function(c){
    var v=c.rets[curAnchor];
    var row=el('div','drow');
    var nm=el('span','nm',(c.leader?'★':'')+c.n);if(c.leader)nm.style.color=C_AC;
    row.appendChild(nm);
    row.appendChild(el('span','cd',c.c));
    var bar=el('span','bar');
    var w=Math.abs(v)/mx*38;
    var i=el('i');
    i.style.background=v>0?C_UP:C_DN;
    if(v>=0){i.style.left=zPos+'%';i.style.width=w+'%'}
    else{i.style.left=(zPos-w)+'%';i.style.width=w+'%'}
    bar.appendChild(i);
    var z=el('span','zero');z.style.left=zPos+'%';bar.appendChild(z);
    row.appendChild(bar);
    var vv=el('span','val',pct(v));vv.className='val '+(v>0?'up':'dn');
    row.appendChild(vv);
    box.appendChild(row);
  });
}
drawDrill();

document.getElementById('foot').innerHTML=
  '口径：前复权收盘价（iFinD ifind_get_price，2025-12-01 至 '+M.px_end+'）；环节收益=成分等权均值；成交额=收盘价×成交量近似；资金占比=环节成交额/全链合计；'+
  '并行科技（839493.BJ）北交所行情 iFinD/Wind 均未覆盖，未纳入统计（覆盖 '+M.covered+'/133 家）。<br>本看板为历史行情统计，不构成投资建议。';
})();
</script>
</body>
</html>
"""

FALLBACK_TOKENS = """
<style>
:root{
--kimi-color-text-primary:#1f2329;--kimi-color-text-secondary:#51565e;--kimi-color-text-tertiary:#8a9099;--kimi-color-text-quaternary:#b6bcc4;
--kimi-color-surface:#ffffff;--kimi-color-surface-muted:#f5f6f7;--kimi-color-surface-raised:#ffffff;
--kimi-color-border:#e4e7eb;--kimi-color-accent:#2f6bff;--kimi-color-on-accent:#ffffff;
--kimi-color-positive:#1a9e54;--kimi-color-danger:#e0393e;--kimi-color-warning:#d97b06}
@media (prefers-color-scheme:dark){:root{
--kimi-color-text-primary:#eceef1;--kimi-color-text-secondary:#b3b8c0;--kimi-color-text-tertiary:#7d838d;--kimi-color-text-quaternary:#5c636d;
--kimi-color-surface:#17191d;--kimi-color-surface-muted:#1e2126;--kimi-color-surface-raised:#1e2126;
--kimi-color-border:#2c3138;--kimi-color-accent:#6b93ff;--kimi-color-on-accent:#0d1020;
--kimi-color-positive:#3fca7d;--kimi-color-danger:#ff6b6e;--kimi-color-warning:#f0a23c}}
body{background-color:var(--kimi-color-surface)}
</style>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--out", required=True)
    ap.add_argument("--standalone-out", default=None)
    args = ap.parse_args()
    root = Path(args.root)
    perf = json.loads((root / "data" / "ai.perf.json").read_text(encoding="utf-8"))
    html = TEMPLATE.replace("__DATA__", json.dumps(perf, ensure_ascii=False))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"dashboard -> {out} ({len(html)} bytes)")
    if args.standalone_out:
        sa = html.replace("</head>", FALLBACK_TOKENS + "\n</head>")
        Path(args.standalone_out).write_text(sa, encoding="utf-8")
        print(f"standalone -> {args.standalone_out}")


if __name__ == "__main__":
    main()
