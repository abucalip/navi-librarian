/* Draws the chosen Home ("Marquee") in each of its states. Needs covers.js first. Sample data only. */
const fail='<div class="busy" style="background:rgba(0,0,0,.6);color:#fff;font-size:22px">!</div>';
const T={ // one tile per kind the "New on the shelf" row can hold
 look:()=>ti(13,'Looking for a source',busy(25),'wn'), down:()=>ti(3,'Downloading',busy(50),'wn'), imp:()=>ti(24,'Importing',busy(75),'wn'),
 fail:()=>ti(15,'Failed · no source found',fail,'dg'), arr1:()=>ti(11,'Arrived today',play), arr2:()=>ti(34,'Arrived yesterday',play),
 radio:()=>ti(8,'Heard on FIP · Get','<span class="tag">Radio</span>'), add1:()=>ti(27,'Added 9 November','','dim'), add2:()=>ti(20,'Added 7 November','','dim'),
 add3:()=>ti(32,'Added 2 November','','dim'), add4:()=>ti(4,'Added 30 October','','dim'), add5:()=>ti(29,'Added 28 October','','dim'), add6:()=>ti(10,'Added 21 October','','dim')};
const WAIT=[[6,'Since March 2023'],[17,'Since June 2023'],[22,'Since June 2023'],[26,'Since January 2024'],[12,'Since February 2024'],[31,'Since May 2024']];
const hero=`<div class="heroA onart"><div class="blur" data-c="0"></div>${cv(0)}
 <div class="mx"><span class="eye">Today's pick · 1 of 7</span><h4>${AL[0][0]}</h4><span class="by">${AL[0][1]} · ${AL[0][2]} · Jazz · not in your library</span>
 <p class="why">You have played three of her later records this month and none from before 1980. This is the one the others grew out of.</p>
 <span class="trk">↓ Mirage Line · suggested track</span>
 <div class="acts"><span class="btn pri">Get album <span class="kbd">→</span></span><span class="btn sec">Save <span class="kbd">↓</span></span><span class="btn sec">Not for me <span class="kbd">←</span></span></div></div>
 <div class="nextA"><span class="eye">Next picks</span><div>${[7,13,2].map(i=>cv(i)).join('')}</div><div>${[21,16,30].map(i=>cv(i)).join('')}</div></div></div>`;
const EMPTY={
 none:`<div class="heroE"><span class="eye">Today's pick</span><h4>No picks right now.</h4><p>Nothing is missing from your recommendations right now.</p><div class="acts"><span class="btn sec">Browse New releases</span></div></div>`,
 history:`<div class="heroE"><span class="eye">Today's pick</span><h4>No picks yet.</h4><p>Picks come from your listening history. Connect Last.fm or ListenBrainz in Services and the first list is built within a few minutes. Nothing is suggested from guesses.</p><div class="acts"><span class="btn sec">Open Services</span><span class="btn sec">Browse New releases</span></div></div>`,
 down:`<div class="heroE"><span class="eye">Today's pick</span><h4>Picks are unavailable.</h4><p>Picks come from Librarian, which is not answering.</p></div>`};
const NOTICE={
 down:`<div class="notice"><b>Can't reach Librarian.</b><span>Your library still plays from Navidrome. Picks, arrivals, taste and insights return when the server answers.</span><span class="btn sec" style="flex:none">Try again</span></div>`,
 failed:`<div class="notice"><b>Harbour Lights did not arrive.</b><span>No source had the whole album.</span><span class="btn sec" style="flex:none">Open Downloads</span></div>`,
 handoff:`<div class="notice info"><b>Playing on your phone:</b><span>Tidewater by Malik Serrano, at 1:52 of 4:47</span><span class="btn sec" style="flex:none">Continue on this Mac</span></div>`};
const fig=(n,l)=>`<span><b>${n}</b> ${l}</span>`;
function renderA(id,o={}){
 const shelf=o.shelf===undefined?['down','arr1','arr2','radio','add1','add2']:o.shelf, wait=o.wait===undefined?WAIT:o.wait;
 const figs=o.figs||[fig('1,248','albums'),fig('14','added in 30 days'),fig('186','listens in 7 days'),fig('312','never played')];
 const taste=o.taste===undefined?'“You are drifting from 2010s electronic toward 1970s jazz and folk.”':o.taste;
 const body=o.loading?`<div class="sk" style="height:292px;border-radius:18px"></div>
  ${[0,1].map(()=>`<div><div class="sk" style="width:170px;height:20px;margin-bottom:12px"></div><div class="g6">${'<div class="sk sq"></div>'.repeat(6)}</div></div>`).join('')}`
 :`${o.notice?NOTICE[o.notice]:''}${o.pick?EMPTY[o.pick]:hero}
<div><div class="hd"><b>New on the shelf</b><span>${o.shelfSub||'arriving, just arrived and heard on the radio'}</span><a>All downloads</a></div>
 ${shelf.length?`<div class="g6">${shelf.map(k=>T[k]()).join('')}</div>`:'<p class="sent">Nothing here yet. Albums you Get appear here while they download, and new albums stay for a while after they arrive.</p>'}</div>
<div><div class="hd"><b>Waiting longest</b><span>albums you own and have never played</span>${wait.length?'<a>Play something unplayed</a>':''}</div>
 ${wait.length?`<div class="g6">${wait.map(w=>ti(w[0],w[1],'','dim')).join('')}</div>`:`<p class="sent">${o.waitSent||'Nothing is waiting. Every album you own has been played.'}</p>`}</div>
<div class="lineA">${taste?`<p>${taste}</p>`:''}${figs.join('')}${taste?'':'<span style="flex:1"></span>'}</div>`;
 const el=document.getElementById(id);el.innerHTML=shell(body,9);if(o.narrow)el.classList.add('nar');paint(el)}

renderA('A');
renderA('A-notice',{notice:'failed',shelf:['fail','down','arr1','radio','add1','add2']});
renderA('A-nopick',{pick:'none'});
renderA('A-firstrun',{pick:'history',shelf:[],wait:[],waitSent:'Albums you own and have not played yet appear here.',taste:'',figs:[fig('0','albums')]});
renderA('A-down',{notice:'down',pick:'down',shelf:['add1','add2','add3','add4','add5','add6'],shelfSub:'recently added',taste:'',figs:[fig('1,248','albums'),fig('14','added in 30 days'),fig('312','never played')]});
renderA('A-loading',{loading:true});
renderA('A-narrow',{narrow:true});
document.getElementById('tiles').innerHTML=['look','down','imp','fail','arr1','radio','add1'].map(k=>T[k]()).join('');paint();
document.getElementById('mode').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
 document.querySelectorAll('#mode button').forEach(x=>x.setAttribute('aria-pressed',x===b));
 document.querySelectorAll('.app').forEach(a=>a.dataset.mode=b.dataset.v)});
