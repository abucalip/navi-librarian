// Sample data and drawing code for mockups.html. Station names, songs and times are invented samples.
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const ST=[
 {n:'FIP',t:'Eclectic',fav:1,sub:'Talk Talk — Life\'s What You Make It',cls:'live-t'},
 {n:'Radio Paradise',t:'Eclectic',fav:1,sub:'Played today, 18:40'},
 {n:'KEXP',t:'Indie',fav:1,sub:'Played yesterday'},
 {n:'BBC Radio 6 Music',t:'Indie · Talk',fav:1,sub:'Not relayed · no song titles'},
 {n:'SomaFM Groove Salad',t:'Electronic',fav:1,sub:'Played 3 days ago'},
 {n:'Radio Swiss Jazz',t:'Jazz',fav:1,sub:'Sends no song titles'},
 {n:'NTS 1',t:'Electronic · Talk',sub:'Played last week'},
 {n:'Worldwide FM',t:'Jazz · Eclectic',sub:'Station unreachable',cls:'dg-t'}];
const HEARD=[
 {t:'Life\'s What You Make It',a:'Talk Talk',s:'FIP',at:'now',st:'wait'},
 {t:'Águas de Março',a:'Elis Regina & Tom Jobim',s:'FIP',at:'21:14',st:'get'},
 {t:'Pyramid Song',a:'Radiohead',s:'FIP',at:'21:09',st:'owned'},
 {t:'Les Fleurs',a:'Minnie Riperton',s:'FIP',at:'21:05',st:'done'},
 {t:'Marquee Moon',a:'Television',s:'KEXP',at:'18:40',st:'busy'},
 {t:'Spanish Key',a:'Miles Davis',s:'Radio Paradise',at:'Yesterday',st:'get'}];
const BTN={wait:'<span class="btn wait"><i class="ring"></i>Listening · 18 s</span>',get:'<span class="btn get">Download</span>',busy:'<span class="btn busy">Downloading…</span>',done:'<span class="btn done">✓ Downloaded</span>',owned:'<span class="btn owned">In library</span>'};
function logo(n,px,fs){let h=0;for(const c of n)h=(h*31+c.charCodeAt(0))%360;const i=n.split(/\s+/).slice(0,2).map(w=>w[0]).join('').toUpperCase();
 return `<div class="lg" style="background:hsl(${h} 48% 40%);${px?`width:${px}px;height:${px}px;`:''}font-size:${fs||Math.round(px*.4)}px">${i}</div>`}
const hrow=(h,short)=>`<div class="row"><div class="mx"><b>${h.t}</b><span>${h.a}${short?'':' · '+h.s} · ${h.at}</span></div>${BTN[h.st]}</div>`;
const srow=(s,i)=>`<div class="row${i===0?' sel':''}">${logo(s.n,34)}<div class="mx"><b>${s.n}</b><span class="${s.cls||''}">${i===0?'● ':''}${s.sub}</span></div><span class="chip">${s.t}</span><span style="color:${s.fav?'var(--a)':'var(--t3)'};font-size:15px">${s.fav?'★':'☆'}</span></div>`;
const chips='<div class="chips"><span class="chip on">All</span><span class="chip">Eclectic</span><span class="chip">Indie</span><span class="chip">Jazz</span><span class="chip">Electronic</span><span class="chip">Talk</span></div>';
const onair=(big)=>`<div class="hero"><div class="cv" style="width:${big?96:120}px;height:${big?96:120}px"></div><div style="flex:1;min-width:0"><span class="livep">LIVE</span> <span style="opacity:.85;font-size:12px">FIP · since 20:58</span><div style="font:700 ${big?22:19}px var(--dp);margin-top:6px">Life's What You Make It</div><div style="opacity:.85">Talk Talk</div><div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">${BTN.wait.replace('btn wait','btn wait" style="background:rgba(255,255,255,.2);color:#fff')}<span class="btn" style="background:rgba(255,255,255,.2);color:#fff">♡ Love</span><span class="btn" style="background:rgba(255,255,255,.2);color:#fff">☾ Sleep</span></div></div></div>`;
const A={
 A1:()=>`<div class="col" style="flex:1">${chips}<div class="eye">Favourites</div><div class="grid">${ST.slice(0,4).map((s,i)=>`<div class="tile${i===0?' live':''}">${logo(s.n,0,34)}<i class="st" style="font-style:normal">★</i><b>${s.n}</b><span class="${s.cls||''}">${i===0?'● ':''}${s.sub}</span></div>`).join('')}</div>
   <div class="eye" style="margin-top:6px">All stations</div><div class="grid">${ST.slice(4).map(s=>`<div class="tile">${logo(s.n,0,34)}${s.fav?'<i class="st" style="font-style:normal">★</i>':''}<b>${s.n}</b><span class="${s.cls||''}">${s.sub}</span></div>`).join('')}</div></div>
  <div class="col panel" style="width:290px;flex:none"><div class="eye">Heard</div>${HEARD.slice(0,5).map(h=>hrow(h)).join('')}</div>`,
 A2:()=>`<div class="col" style="flex:1">${chips}<div>${ST.map(srow).join('')}</div></div>
  <div class="col" style="width:330px;flex:none">${onair()}<div class="panel"><div class="eye">Heard on FIP tonight</div>${HEARD.slice(1,4).map(h=>hrow(h,1)).join('')}<span style="color:var(--a);font-weight:600">All heard songs ›</span></div></div>`,
 A3:()=>`<div class="col" style="flex:1"><div class="pre">${ST.slice(0,6).map((s,i)=>`<div class="${i===0?'on':''}">${logo(s.n,30)}<b>${s.n}</b><kbd>⌘${i+1}</kbd></div>`).join('')}</div>
   ${onair(1)}<div style="display:flex;gap:20px;min-height:0"><div class="col" style="flex:1"><div class="eye">Stations</div><div>${ST.slice(0,4).map((s,i)=>srow(s,i)).join('')}</div></div>
   <div class="col" style="flex:1"><div class="eye">Heard</div><div>${HEARD.slice(1,5).map(h=>hrow(h)).join('')}</div></div></div></div>`};
const CAP={
 A1:'<b>A1 Station wall.</b> Logos carry the page, like the Albums grid. The playing station has an accent ring and its live song under the name. Heard sits in a fixed column on the right, so Download is always one click away. Best with many stations and good logos; weakest for reading states, because each tile has one short line.',
 A2:'<b>A2 Tuner.</b> A dense list on the left (logo, name, state in words, tag, star) and a fixed On Air panel on the right with the live song, Download, Love and Sleep, then what was heard on this station. Closest to a Mac list-and-detail window; every state has room for its sentence. Logos are small.',
 A3:'<b>A3 Presets and On Air.</b> Favourites are six preset buttons with ⌘1 to ⌘6 on top, a wide On Air band under them, then stations and Heard side by side. Made for a few stations used every day and for the keyboard. With many stations the list below gets short and needs scrolling.',
 B1:'<b>B1 Plain live.</b> Logo or cover, live title, "FIP · LIVE", stop, previous and next station, Download, and a hairline in place of the seek bar. Nothing moves. Smallest build.',
 B2:'<b>B2 Level meter.</b> The sound graph\'s place is taken by live level bars from the stream. It looks alive, but it is the only option that needs an audio tap on the live player, which is extra work and the part most likely to cost time. It stays still under Reduce Motion.',
 B3:'<b>B3 Session tape.</b> The bottom edge is a tape of the songs heard since tuning in: one segment per song, the current one in white, downloaded ones in green with a tick. Hover shows the title; click offers Download for that earlier song. It reuses <code>/now</code> and the Heard list, so it needs no new data. My pick.',
 C1:'<b>C1 Song first.</b> Built like the song Now Playing: the cover when the song is in your library (the server sends it), otherwise the station logo; title and artist large; the right column, where lyrics normally are, lists what this station played tonight with a button each.',
 C2:'<b>C2 Station first.</b> The station is the subject: large logo, name, tags and homepage link, with the live song as a card under it and the sleep timer choices visible. Calmer, and honest for stations without titles, but the song gets less room and Heard moves to the Radio page.'};
const TX=`<span>⏮</span><span class="pp">■</span><span>⏭</span>`;
function bar(el,o={}){const st=o.st||'wait';
 el.innerHTML=`<div class="meter">${'<i></i>'.repeat(64)}</div>${o.cover===0?logo('FIP',50):'<div class="cv" style="width:50px;height:50px"></div>'}
 <div class="mx"><b>${o.title||"Life's What You Make It"}</b><span>${o.sub||'Talk Talk'}</span></div><span class="livep">LIVE</span><span style="font-size:12px;opacity:.8">FIP · 19:12</span>
 <div class="tx">${TX}</div>${o.btn!==undefined?o.btn:BTN[st]}<span class="ic">★</span><span class="ic">☾</span>
 <div class="hair"></div><div class="tape"><i class="got" style="flex:4" title="Les Fleurs · Downloaded">✓</i><i style="flex:5" title="Pyramid Song · In library"></i><i style="flex:3" title="Águas de Março · Download"></i><i style="flex:1" title="Station talk, no title"></i><i class="cur" style="flex:2" title="Life's What You Make It">now</i></div>`}
function np(v){$('#np').innerHTML=v==='C1'?
 `<div class="l"><div class="cv" style="width:230px;height:230px;border-radius:12px"></div><div><span class="livep">LIVE</span> <span style="opacity:.85;font-size:12px">FIP · 19:12</span></div><h4>Life's What You Make It</h4><div style="opacity:.85;font-size:15px;margin-top:-8px">Talk Talk</div>
  <div class="acts">${BTN.wait}<span class="btn pl">♡ Love</span><span class="btn pl">★ Favourite</span><span class="btn pl">☾ Sleep</span></div></div>
  <div class="r"><div class="eye">Heard on FIP tonight</div>${HEARD.slice(1,4).map(h=>hrow(h,1)).join('')}<div class="row"><div class="mx"><b>Blue in Green</b><span>Miles Davis · 20:59</span></div>${BTN.owned}</div><span style="opacity:.75;font-size:12px;margin-top:6px">Download appears once a song has been heard for about 30 seconds.</span></div>`:
 `<div class="l" style="width:260px;align-items:flex-start">${logo('FIP',230,92)}</div>
  <div class="r" style="gap:12px"><div><span class="livep">LIVE</span> <span style="opacity:.85;font-size:12px">playing for 19:12</span></div><h4 style="font-size:44px">FIP</h4><div style="opacity:.85;margin-top:-8px">Eclectic · France · fip.fr ↗</div>
  <div style="background:rgba(255,255,255,.14);border-radius:14px;padding:14px;display:flex;gap:14px;align-items:center;max-width:470px"><div class="cv" style="width:64px;height:64px"></div><div style="flex:1;min-width:0"><b style="font-size:16px">Life's What You Make It</b><div style="opacity:.8">Talk Talk</div></div>${BTN.wait}</div>
  <div class="acts"><span class="btn pl">♡ Love</span><span class="btn pl">★ Favourite</span><span class="eye" style="margin-left:8px">Sleep</span>${[15,30,45,60,90].map(m=>`<span class="btn pl">${m}</span>`).join('')}</div></div>`;
 $('#capC').innerHTML=CAP[v]}
const STATES=[
 ['Waiting 30 s',{},'<b>ok, no play id yet.</b> Title shown; the button counts the listening time and cannot be pressed.'],
 ['Download',{st:'get'},'<b>ok with a play id.</b> Download is enabled.'],
 ['Downloading',{st:'busy'},'After a click. The server\'s own sentence is shown if it refuses ("No exact match on MusicBrainz").'],
 ['Downloaded',{st:'done'},'The song was requested and has arrived.'],
 ['In library',{st:'owned'},'The server says the song is already owned; the cover is the library cover.'],
 ['No titles',{cover:0,title:'FIP',sub:'This station sends no song titles',btn:''},'<b>no_metadata.</b> The station plays; no button at all.'],
 ['Unmatched title',{cover:0,title:'FIP — Journal de 21h',sub:'This title could not be matched to an artist and song',btn:''},'<b>unparsed.</b> Raw title shown; no button.'],
 ['Not relayed',{cover:0,title:'BBC Radio 6 Music',sub:'Played from its own address · no song titles',btn:''},'<b>not_proxied.</b> Plays from the original address when the Mac can reach it.'],
 ['Try again',{btn:'<span class="btn get">Try again</span>',sub:'Talk Talk · No exact match on MusicBrainz'},'The server refused the request. Its own sentence is shown beside the artist, and the button offers another try.'],
 ['Reconnecting',{cover:0,title:'FIP',sub:'Connection lost · trying again in 5 s (attempt 2 of 5)',btn:'<span class="btn pl" style="background:rgba(255,255,255,.2);color:#fff">Stop</span>'},'Retries after 2, 5, 10, 20 and 30 s. None after you press stop.'],
 ['Unreachable',{cover:0,title:'FIP',sub:'Station unreachable',btn:'<span class="btn get">Retry</span>'},'<b>unavailable</b>, or five failed attempts. Never silence without text.']];
const EX=[
 ['E1','Number shortcuts','⌘1 to ⌘9 tune to the first nine favourites, from any screen.'],
 ['E2','"Tune to…" in ⌘K','Stations appear in the command palette with their logos; also "Stop radio" and "Download this song".'],
 ['E3','Love on Last.fm','A heart on the live song and on Heard rows (existing endpoint). Hidden when Last.fm is not set up.'],
 ['E4','Drop an image to set a logo','Drag a picture onto a station to upload it as the logo; right-click has Change and Reset.'],
 ['E5','Edit tags on the Mac','Right-click a station, Edit Tags (up to 10). Filter chips come from the tags.'],
 ['E6','Download all heard','One button on the Heard list that requests every song still on "Download", one after the other.'],
 ['E7','Radio card on Home','A small "On air" card on Home when a station plays, and a last-station "Resume" when none does.'],
 ['E8','Notify on In library','A quiet notification when a radio download arrives (the existing Get-finished notice, with the station named).'],
 ['E9','Resume last station at launch','Off by default; a switch in Settings, Playback.']];
const CHOSEN=['A2','B2','C1','D2','E1','E5','E7'];
const pick={A:'A2',B:'B2',C:'C1',D:'D2'},ex=new Set(['E1','E5','E7']);
function draw(){
 $('#bdA').innerHTML=A[pick.A]();$('#capA').innerHTML=CAP[pick.A];
 for(const id of['#pbA','#pbB']){bar($(id));$(id).dataset.b=pick.B}$('#capB').innerHTML=CAP[pick.B];
 np(pick.C);$('#desk').dataset.d=pick.D;
 $$('.pills[data-g]').forEach(g=>g.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.v===pick[g.dataset.g]))));
 $('#picks').textContent=`${pick.A} · ${pick.B} · ${pick.C} · ${pick.D} · ${[...ex].sort().join(' ')||'no extras'}`}
$$('.pills[data-g]').forEach(g=>g.querySelectorAll('button').forEach(b=>b.onclick=()=>{pick[g.dataset.g]=b.dataset.v;g.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));draw()}));
$$('#mode button').forEach(b=>b.onclick=()=>{$$('#mode button').forEach(x=>x.setAttribute('aria-pressed',x===b));$$('.app').forEach(a=>a.dataset.mode=b.dataset.v)});
STATES.forEach((s,i)=>{const b=document.createElement('button');b.textContent=s[0];b.setAttribute('aria-pressed',i===0);b.onclick=()=>{$$('#states button').forEach(x=>x.setAttribute('aria-pressed',x===b));bar($('#pbS'),s[1]);$('#capS').innerHTML=s[2]};$('#states').appendChild(b)});
bar($('#pbS'),{});$('#capS').innerHTML=STATES[0][2];
$('#ex').innerHTML=EX.map(e=>`<label><input type="checkbox" id="x${e[0]}" ${ex.has(e[0])?'checked':''}><div><b>${e[0]} · ${e[1]}${CHOSEN.includes(e[0])?' · chosen':''}</b><span>${e[2]}</span></div></label>`).join('');
EX.forEach(e=>$('#x'+e[0]).onchange=ev=>{ev.target.checked?ex.add(e[0]):ex.delete(e[0]);draw()});
$('#pop').innerHTML=`<div style="display:flex;gap:10px;align-items:center"><div class="cv" style="width:54px;height:54px"></div><div style="flex:1;min-width:0"><span class="livep" style="background:#d61f4a;color:#fff">LIVE</span> <span style="font-size:12px;color:#636368">FIP</span><b style="display:block">Life's What You Make It</b><span style="color:#636368">Talk Talk</span></div></div>
 <div style="display:flex;gap:8px"><span class="btn pl">■ Stop</span><span class="btn get">Download</span><span class="btn pl">☾ 45 min</span></div><hr>
 ${ST.slice(0,4).map((s,i)=>`<div class="row">${logo(s.n,26)}<div class="mx"><b>${s.n}</b></div><span>⌘${i+1}</span></div>`).join('')}<hr><div class="row"><div class="mx">Open Discair</div></div>`;
$('#hc1').innerHTML=`<div class="cv" style="width:56px;height:56px"></div><div class="mx"><i class="livea">LIVE</i><b>Life's What You Make It</b><span>Talk Talk · FIP</span></div><span class="btn pl">■ Stop</span><span class="btn pl">Open Radio</span>`;
$('#hc2').innerHTML=`${logo('FIP',56)}<div class="mx"><b>FIP</b><span>Last played today, 21:17</span></div><span class="btn get">▶ Resume</span>`;
$('#tags').innerHTML=`<b style="font-size:15px">Tags for FIP</b><div class="fld"><span class="tk">Eclectic ×</span><span class="tk">France ×</span><span style="color:var(--t3)">Add a tag</span></div><span style="color:var(--t2);font-size:12px">2 of 10 tags. Each up to 24 characters.</span><div style="display:flex;gap:8px;justify-content:flex-end"><span class="btn pl">Cancel</span><span class="btn get">Save</span></div>`;
$('#sleep').innerHTML=['Off','15 minutes','30 minutes','45 minutes','60 minutes','90 minutes'].map((m,i)=>`<div class="${i===3?'on':''}">${i===3?'✓':'&nbsp;&nbsp;'} ${m}</div>`).join('');
$('#stmenu').innerHTML=ST.slice(0,5).map((s,i)=>`<div>${s.n}<kbd>⌘${i+1}</kbd></div>`).join('')+'<hr><div>Stop Radio</div>';
$('#mini').innerHTML=`${logo('FIP',52)}<div class="mx"><span class="livep">LIVE</span><b>Life's What You Make It</b><span>Talk Talk · FIP</span></div><span style="font-size:18px">■</span>`;
$('#copy').onclick=()=>{const t=$('#picks').textContent;(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>{$('#copy').textContent='Copied';setTimeout(()=>$('#copy').textContent='Copy',1500)}).catch(()=>{const r=document.createRange();r.selectNodeContents($('#picks'));const s=getSelection();s.removeAllRanges();s.addRange(r)})};
$$('.pills[data-g] button').forEach(b=>{if(CHOSEN.includes(b.dataset.v))b.textContent+=' · chosen'});
draw();
const still=matchMedia('(prefers-reduced-motion:reduce)').matches;
function meter(){$$('.pb[data-b=B2] .meter i').forEach((i,k)=>i.style.height=(still?20+30*Math.abs(Math.sin(k*.6)):12+Math.random()*55)+'%')}
meter();if(!still)setInterval(meter,160);
