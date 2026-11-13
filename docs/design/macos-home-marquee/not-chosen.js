/* Mockups B (Cover Wall) and C (Covers as Charts). Offered on 2026-11-13, not chosen, not built. Kept for the record. */
/* B */
const t=(i,area,x='')=>`<div class="cv" data-c="${i}" style="grid-area:${area}">${x}</div>`;
const cap=(i,s)=>`<div class="cap"><b>${AL[i][0]}</b><span>${s}</span></div>`;
document.getElementById('B').innerHTML=shell(`
<div class="chips"><span class="chip on">Everything</span><span class="chip">Picks</span><span class="chip">Arrivals</span><span class="chip">Unplayed</span><span class="chip">Recently added</span></div>
<div class="wall">
 <div class="pickB" data-c="2" style="grid-area:1/1/4/4"><span class="tag ac">Today's pick · 1 of 7</span><h4>${AL[2][0]}</h4><span>${AL[2][1]} · ${AL[2][2]}</span>
  <p>The record his whole circle points back to, and the only one of his you do not own.</p>
  <div class="acts"><span class="btn pri" style="background:#fff;color:#b3123c">Get <span class="kbd">→</span></span><span class="btn sec" style="background:rgba(255,255,255,.2);color:#fff">Save</span><span class="btn sec" style="background:rgba(255,255,255,.2);color:#fff">Not for me</span></div></div>
 ${t(11,'1/4/3/6','<span class="tag">Arrived today</span>'+play+cap(11,AL[11][1]))}
 ${t(27,'1/6/2/7')}${t(20,'1/7/2/8')}${t(15,'1/8/2/9')}
 <div class="txt" style="grid-area:2/6/3/8"><p>“You are drifting from 2010s electronic toward 1970s jazz and folk.”</p><span>Your taste</span></div>
 ${t(24,'2/8/3/9')}
 ${t(3,'3/4/4/5',busy(62))}${t(8,'3/5/4/6','<span class="tag">Heard on FIP</span>')}${t(33,'3/6/4/7')}
 ${t(6,'3/7/5/9','<span class="tag">Never played</span>'+play+cap(6,'On your shelf since March 2023'))}
 <div class="txt" style="grid-area:4/1/5/3"><span class="big">1,248</span><span>albums · 14 added this month</span></div>
 ${t(34,'4/3/5/4','<span class="tag">New</span>')}${t(29,'4/4/5/5')}
 ${t(18,'4/5/6/7','<span class="tag">Deep cuts lens</span>'+cap(18,'Three songs here you have never reached'))}
 ${t(4,'5/1/6/2')}${t(25,'5/2/6/3')}${t(10,'5/3/6/4')}${t(35,'5/4/6/5')}
 <div class="txt" style="grid-area:5/7/6/9"><span class="big">186</span><span>listens this week · 23 more than last week</span></div>
</div>`,14);

/* C */
const DEC=[["1960s",7,4,[6,17,22,26]],["1970s",18,31,[0,8,12,19,31]],["1980s",13,9,[4,14,23,28,35]],["1990s",21,17,[2,10,16,25,33]],["2000s",16,12,[5,9,18,29,30]],["2010s",17,19,[7,13,15,20,24,32]],["2020s",8,8,[3,11,21,27,34]]];
const BIN=[["This month",96,[1,13,9],1],["1–6 months",284,[24,5,16,30,2],.75],["6–12 months",211,[28,19,33,10],.5],["1–2 years",187,[4,25,35],.3],["2+ years",158,[14,23],.15],["Never",312,[6,17,22,26,12,31],0]];
document.getElementById('C').innerHTML=shell(`
<div class="rowC">
 <div><div class="hd"><b>Today's pick</b><span>1 of 7</span></div><div class="deck"><div class="stack">${cv(13)}${cv(7)}${cv(19)}</div>
  <div class="mx"><h4>${AL[19][0]}</h4><span>${AL[19][1]} · ${AL[19][2]}</span><p>Closest in sound to the album you have played most this month, from a decade you rarely reach.</p><span style="font-size:12px">▶ Start with “Amber Road”</span>
  <div class="acts"><span class="btn pri">Get <span class="kbd">→</span></span><span class="btn sec">Save <span class="kbd">↓</span></span><span class="btn sec">Not for me <span class="kbd">←</span></span></div></div></div></div>
 <div><div class="hd"><b>On rotation</b><span>bigger means played more</span><a>History</a></div>
  <div class="rot">${cv(9,'','width:148px;height:148px')}<div><div class="r1">${cv(1)}${cv(24)}${cv(16)}</div><div class="r2">${cv(5)}${cv(30)}${cv(13)}${cv(2)}</div></div></div>
  <p class="note"><b>186 listens</b> in the last 7 days, 23 more than the week before.</p></div>
</div>
<div>
  <div><div class="hd"><b>Your shelf by decade</b><span>width is the share of albums · the line is the share of listens</span></div>
  <div class="ribbon">${DEC.map(d=>`<div class="dec${d[0]=='1970s'?' sel':''}" style="flex:${d[1]} 1 0"><div class="strip">${Array.from({length:12},(_,j)=>`<i data-c="${d[3][(j*3+(j>>1))%d[3].length]}"></i>`).join('')}</div><div class="ls"><i style="width:${Math.min(100,d[2]/31*100)}%"></i></div><b>${d[0]}</b><span>${d[1]}% owned</span><span>${d[2]}% played</span></div>`).join('')}</div></div>
 </div>
<div class="lastC"><div style="min-width:0"><div class="hd"><b>Shelf life</b><span>time since each album was last played · taller piles hold more albums</span><a>Play something unplayed</a></div>
 <div class="dust">${BIN.map((b,k)=>`<div><div class="pile">${b[2].map((i,j)=>cv(i,'',`left:${j*6}px;bottom:${j*7}px;z-index:${9-j};filter:saturate(${b[3]}) ${b[3]?'':'opacity(.75)'}`)).reverse().join('')}</div><div class="lb${k==5?' nv':''}"><b>${b[0]}</b><span>${b[1]} albums</span></div></div>`).join('')}</div></div>
 <div><div class="hd"><b>On its way</b><a>All downloads</a></div><div class="way">${ti(3,'Downloading',busy(62),'wn')}${ti(11,'Arrived',play)}${ti(34,'Arrived',play)}${ti(8,'Heard on FIP','','dim')}</div></div></div>`,1);

paint();
