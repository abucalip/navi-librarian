/* Draws every state of the macOS Paths sheet and Booklet sheet from sample data. ?only=<state id> draws one state
   (used by _src/build.py for the PNGs). The data shapes follow the app's model: a stop is a PathStep, a group is a
   PathTrailGroup (spec section 4), an edition is a BookletView. Sample data only. */
(function () {
  "use strict";
  var esc = function (s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); };
  var G = {
    ram: "linear-gradient(140deg,#c0392b,#5b1010)", gold: "linear-gradient(150deg,#d9a441,#7a4b12)",
    blue: "linear-gradient(150deg,#3f7cac,#132b45)", violet: "linear-gradient(150deg,#8e44ad,#2c0f3d)",
    teal: "linear-gradient(150deg,#16a085,#06362c)", orange: "linear-gradient(150deg,#e67e22,#6e2c00)",
    slate: "linear-gradient(150deg,#2c3e50,#0b1218)", red: "linear-gradient(150deg,#c0392b,#3d0a0a)",
    grey: "linear-gradient(150deg,#7f8c8d,#2b3233)", olive: "linear-gradient(150deg,#7d8a2e,#262b0b)",
    rose: "linear-gradient(150deg,#c76d8a,#45131f)", sky: "linear-gradient(150deg,#5fa8d3,#173247)"
  };

  // ---------- Paths sample answers ----------
  function stop(t, a, g, owned, story, extra) { return { t: t, a: a, g: g, owned: owned, story: story, extra: extra }; }
  var crewStory = function (via, title, tracks) {
    return "<b>" + via + "</b> has a production credit on " + (tracks || "<i>’Round About Midnight</i>") + " and on <i>" + title + "</i>.";
  };
  var CREW = [
    { name: "George Avakian", kind: "producer credit", role: "On the album itself", count: 4, capped: 4, stops: [
      stop("Ellington at Newport", "Duke Ellington", G.gold, false, crewStory("George Avakian", "Ellington at Newport")),
      stop("Concert by the Sea", "Erroll Garner", G.blue, false, crewStory("George Avakian", "Concert by the Sea")),
      stop("Louis Armstrong Plays W.C. Handy", "Louis Armstrong", G.violet, false, crewStory("George Avakian", "Louis Armstrong Plays W.C. Handy")),
      stop("Jazz Goes to College", "The Dave Brubeck Quartet", G.teal, true, crewStory("George Avakian", "Jazz Goes to College"))] },
    { name: "Fred Plaut", kind: "engineer credit", role: "On <i>’Round Midnight</i>, <i>Ah-Leu-Cha</i> and 2 more", count: 4, stops: [
      stop("Time Out", "The Dave Brubeck Quartet", G.orange, false, crewStory("Fred Plaut", "Time Out", "<i>’Round Midnight</i>, <i>Ah-Leu-Cha</i>, <i>All of You</i> and <i>Bye Bye Blackbird</i> from <i>’Round About Midnight</i>")),
      stop("Kind of Blue", "Miles Davis", G.slate, true, crewStory("Fred Plaut", "Kind of Blue", "<i>’Round Midnight</i> and <i>Ah-Leu-Cha</i> from <i>’Round About Midnight</i>")),
      stop("Mingus Ah Um", "Charles Mingus", G.red, false, crewStory("Fred Plaut", "Mingus Ah Um", "<i>All of You</i> from <i>’Round About Midnight</i>")),
      stop("Sketches of Spain", "Miles Davis", G.grey, true, crewStory("Fred Plaut", "Sketches of Spain"))] }
  ];
  var ROOM = [
    { name: "Columbia 30th Street Studio", kind: "recorded at", role: "On <i>’Round Midnight</i>, <i>All of You</i> and 2 more", count: 3, stops: [
      stop("Kind of Blue", "Miles Davis", G.slate, true, "<b>Columbia 30th Street Studio</b> is where <i>’Round Midnight</i> and <i>All of You</i> were made (recorded, mixed or engineered) and where <i>Kind of Blue</i> was made."),
      stop("Time Out", "The Dave Brubeck Quartet", G.orange, false, "<b>Columbia 30th Street Studio</b> is where <i>’Round Midnight</i> was made (recorded, mixed or engineered) and where <i>Time Out</i> was made."),
      stop("Mingus Ah Um", "Charles Mingus", G.red, false, "<b>Columbia 30th Street Studio</b> is where <i>All of You</i> was made (recorded, mixed or engineered) and where <i>Mingus Ah Um</i> was made.")] },
    { name: "Columbia Studio D", kind: "recorded at", role: "On <i>Ah-Leu-Cha</i>", count: 1, stops: [
      stop("Miles Ahead", "Miles Davis", G.sky, false, "<b>Columbia Studio D</b> is where <i>Ah-Leu-Cha</i> was made (recorded, mixed or engineered) and where <i>Miles Ahead</i> was made.")] }
  ];
  var GAPS = [
    { name: "Teo Macero", kind: "production credit", role: "On the album itself", count: 2, stops: [
      stop("Sketches of Spain", "Miles Davis", G.grey, true, crewStory("Teo Macero", "Sketches of Spain"), "Not played"),
      stop("Someday My Prince Will Come", "Miles Davis", G.rose, true, crewStory("Teo Macero", "Someday My Prince Will Come"), "Played once")] },
    { name: "Fred Plaut", kind: "engineer credit", role: "On <i>’Round Midnight</i>", count: 1, stops: [
      stop("Jazz Goes to College", "The Dave Brubeck Quartet", G.teal, true, crewStory("Fred Plaut", "Jazz Goes to College"), "Not played")] }
  ];
  var SONIC = [{ flat: true, stops: [
    stop("Kind of Blue", "Miles Davis", G.slate, true, "Sounds like <i>’Round About Midnight</i> on 5 of its 8 tracks.", "5 of 8 tracks · 1959"),
    stop("Workin’", "The Miles Davis Quintet", G.olive, true, "Sounds like <i>’Round About Midnight</i> on 4 of its 8 tracks.", "4 of 8 tracks · 1960"),
    stop("Blue Train", "John Coltrane", G.blue, true, "Sounds like <i>’Round About Midnight</i> on 3 of its 8 tracks.", "3 of 8 tracks · 1958"),
    stop("Soultrane", "John Coltrane", G.teal, true, "Sounds like <i>’Round About Midnight</i> on 2 of its 8 tracks.", "2 of 8 tracks · 1958"),
    stop("Bags’ Groove", "Miles Davis", G.gold, true, "Sounds like <i>’Round About Midnight</i> on 2 of its 8 tracks.", "2 of 8 tracks · 1957")] }];
  var MUSICIAN = [
    { name: "John Coltrane", kind: "musician", role: "Played with Miles Davis", count: 3, stops: [
      stop("Giant Steps", "Giant Steps · John Coltrane", G.orange, false, "<b>John Coltrane</b> played with <b>Miles Davis</b> and plays on <i>Giant Steps</i>."),
      stop("Blue Train", "Blue Train · John Coltrane", G.blue, true, "<b>John Coltrane</b> played with <b>Miles Davis</b> and plays on <i>Blue Train</i>."),
      stop("Naima", "Giant Steps · John Coltrane", G.orange, false, "<b>John Coltrane</b> played with <b>Miles Davis</b> and plays on <i>Naima</i>.")] },
    { name: "Red Garland", kind: "musician", role: "Played with Miles Davis", count: 2, stops: [
      stop("C Jam Blues", "Groovy · Red Garland Trio", G.violet, false, "<b>Red Garland</b> played with <b>Miles Davis</b> and plays on <i>C Jam Blues</i>."),
      stop("Billy Boy", "Milestones · Miles Davis", G.grey, true, "<b>Red Garland</b> played with <b>Miles Davis</b> and plays on <i>Billy Boy</i>.")] }
  ];
  var SIDEMAN = [
    { name: "Somethin’ Else", kind: "a record they led", role: "Miles Davis played on it", count: 1, round: true, stops: [
      stop("Cannonball Adderley", "", G.gold, false, "<b>Miles Davis</b> played on <i>Somethin’ Else</i>, a record <b>Cannonball Adderley</b> led.")] },
    { name: "Bags’ Groove", kind: "a record they led", role: "Miles Davis played on it", count: 2, round: true, stops: [
      stop("Thelonious Monk", "", G.slate, true, "<b>Miles Davis</b> played on <i>Bags’ Groove</i> with <b>Thelonious Monk</b>."),
      stop("Milt Jackson", "", G.teal, false, "<b>Miles Davis</b> played on <i>Bags’ Groove</i> with <b>Milt Jackson</b>.")] }
  ];

  var ALBUM_TABS = ["Crew", "Guests", "Covers", "Scene", "Room", "Gaps", "Sonic"];
  var ARTIST_TABS = ["Follow the Musician", "Sideman", "Label", "Composition", "Scene"];
  var SUMMARY = {
    Crew: "Albums that share a producer, engineer or mixer credit with ’Round About Midnight, those not in your library first.",
    Room: "Albums with a track made in the same studio or at the same event as a track on ’Round About Midnight, those not in your library first.",
    Gaps: "Albums in your library that share a credit with ’Round About Midnight and that you have played little or never.",
    Sonic: "Albums in your library that sound like ’Round About Midnight, found from 8 of its tracks.",
    "Follow the Musician": "Songs, not in your library, by musicians who also played with Miles Davis.",
    Sideman: "Artists whose records Miles Davis played on as a sideman."
  };

  function cover(s, round, badge) {
    var initials = round ? esc(s.t.split(" ").map(function (w) { return w[0]; }).join("").slice(0, 2)) : "<span>" + esc(s.t) + "</span>";
    return '<div class="cov art' + (round ? " round" : "") + '" style="background:' + s.g + '">' +
      (badge ? '<span class="badge-corner">Get</span>' : "") + initials + "</div>";
  }
  function ownBadge(owned) {
    return owned ? '<span class="own in">✓ In library</span>' : '<span class="own out">○ Not in library</span>';
  }
  function stopCard(s, i, sel, round, sheetSubject) {
    var badge = !s.owned && sheetSubject !== "artist-people";
    return '<button class="stop' + (sel ? " sel" : "") + '" data-i="' + i + '">' + cover(s, round, badge && !round) +
      '<div class="t">' + esc(s.t) + "</div>" + (s.a ? '<div class="a">' + esc(s.a) + "</div>" : "") +
      (s.extra ? '<div class="x">' + esc(s.extra) + "</div>" : "") + ownBadge(s.owned) + "</button>";
  }

  function pathsWindow(o) {
    var tabs = o.subject === "album" ? ALBUM_TABS : ARTIST_TABS;
    var counts = o.counts || {};
    var tabHtml = tabs.map(function (t) {
      return '<button role="tab" aria-selected="' + (t === o.tab) + '">' + esc(t) + (counts[t] != null ? ' <span class="n">' + counts[t] + "</span>" : "") + "</button>";
    }).join("");
    var head = '<div class="p-head"><div class="p-start">' +
      (o.subject === "album" ? '<div class="cov art" style="background:' + G.ram + '"><span>RAM</span></div>' : '<div class="cov art round" style="background:' + G.slate + ';width:56px;height:56px;font-size:20px">MD</div>') +
      '<div><span class="t-eyebrow eb">Paths from</span><span class="t-title2 ttl">' + esc(o.subject === "album" ? "’Round About Midnight" : "Miles Davis") + '</span><span class="sub">' +
      esc(o.subject === "album" ? "Miles Davis · 1957" : "Artist") + '</span></div></div><div></div><button class="p-close" aria-label="Close">✕</button></div>';
    var nav = '<nav class="p-tabs" role="tablist" aria-label="Paths">' + tabHtml + "</nav>";
    var summary = '<div class="p-summary"><span>' + esc(SUMMARY[o.tab] || "") + "</span>" +
      (o.filter !== false ? '<div class="filter" role="group" aria-label="Show">' + ["All", "Not in library", "In library"].map(function (f) {
        return '<button class="' + ((o.filterOn || "All") === f ? "on" : "") + '">' + f + "</button>";
      }).join("") + "</div>" : "") + "</div>";
    if (o.phase) {
      return '<div class="win paths short ' + (o.night ? "pb-night" : "pb-mode") + '">' + head + nav + '<div class="p-body">' + summary + o.phase + "</div></div>";
    }
    var all = [];
    var groupsHtml = o.groups.map(function (g) {
      var shown = g.stops.filter(function (s) { return o.filterOn === "Not in library" ? !s.owned : o.filterOn === "In library" ? s.owned : true; });
      if (!shown.length) return "";
      var cards = shown.map(function (s) { all.push(s); return stopCard(s, all.length - 1, all.length - 1 === (o.sel || 0), g.round || o.round, o.subjectKind); }).join("");
      if (g.flat) return '<div class="stops">' + cards + "</div>";
      var count = o.filterOn && o.filterOn !== "All" ? shown.length + " of " + g.count + " " + (g.count === 1 ? o.unit1 || "album" : o.unit || "albums") : g.count + " " + (g.count === 1 ? o.unit1 || "album" : o.unit || "albums");
      return '<div class="link"><div class="dot"></div><div class="link-head"><span class="pill"><b>' + esc(g.name) + "</b> · " + esc(g.kind) +
        '</span><span class="role">' + g.role + '</span><span class="count">' + count + '</span></div><div class="stops">' + cards + "</div>" +
        (g.capped ? '<p class="capnote">' + g.capped + " more albums with " + esc(g.name) + " are not shown.</p>" : "") + "</div>";
    }).join("");
    var flat = o.groups.length === 1 && o.groups[0].flat;
    var notes = o.notes ? '<div class="p-notes">' + o.notes.map(function (n) { return "<p>" + esc(n) + "</p>"; }).join("") + "</div>" : "";
    var s = all[o.sel || 0];
    // One primary per view: the stop's own target (Return). Album stops: Open Album; artist stops: Open Artist.
    var people = o.subjectKind === "artist-people";
    var acts = '<div class="acts">' + (people ? "" : '<button class="btn">Open Artist</button>') +
      (!s.owned && !people ? '<button class="btn">↓ Get</button>' : "") +
      (s.owned && !people ? '<button class="btn">▶ Play Album</button>' : "") +
      '<button class="btn pri">' + (people ? "Open Artist" : "Open Album") + "</button></div>";
    var ttlOwn = s.owned ? "In your library" : "Not in your library";
    var extraSlot = o.tab === "Room" ? '<div class="extra-slot session"><figure><div class="ph"></div><figcaption>’Round About Midnight</figcaption></figure><figure><div class="ph"></div><figcaption>' + esc(s.t) + "</figcaption></figure></div>" :
      (o.tab === "Gaps" ? '<div class="play-card"><small>Your listening</small><b>' + esc(s.extra) + "</b></div>" : "");
    var detail = '<div class="p-detail" aria-live="polite">' + cover(s, o.round || (o.groups[0] && o.groups[0].round), false) +
      '<div><div class="ttl">' + esc(s.t) + (s.a ? " · " + esc(s.a.split(" · ").pop()) : "") + " · " + ttlOwn + '</div><div class="story">' + s.story +
      '</div><div class="ev">' + esc(o.evidence || "producer · MusicBrainz") + ' &nbsp;·&nbsp; <kbd>←</kbd> <kbd>→</kbd> move &nbsp;<kbd>↩</kbd> open</div>' + extraSlot + "</div>" + acts + "</div>";
    return '<div class="win paths' + (o.min ? " min" : "") + " " + (o.night ? "pb-night" : "pb-mode") + '">' + head + nav + '<div class="p-body">' + summary +
      '<div class="trail' + (flat ? " flat" : "") + '">' + groupsHtml + notes + "</div></div>" + detail + "</div>";
  }

  var PHASE = {
    loading: '<div class="p-phase"><div class="spin" aria-hidden="true"></div><div>Finding the paths…</div></div>',
    failed: '<div class="p-phase"><div class="fail"><span aria-hidden="true">⚠︎</span>This album isn’t in the server’s knowledge store yet.</div>' +
      '<div class="row"><button class="btn">Try Again</button><button class="btn">Request update</button></div><small>The server is updating its store…</small></div>',
    empty: '<div class="p-phase"><div>No Guest List path from ’Round About Midnight yet. A path appears only when every step has evidence.</div></div>'
  };

  // ---------- Booklet ----------
  var EDITIONS = [
    { name: "2001 US CD", detail: "16 pages · 1400 px", tag: "Your edition", owned: true },
    { name: "1957 US LP", detail: "2 pages · 3000 px" },
    { name: "2005 JP CD", detail: "24 pages · 600 px", tag: "Japanese" }
  ];
  var SPREADS = [["cv"], ["paper", "paper"], ["paper", "ph"], ["ph", "paper"], ["paper", "paper"], ["paper", "ph"], ["paper", "paper"], ["paper", "paper"], ["cv"]];
  var LABELS = ["1", "2–3", "4–5", "6–7", "8–9", "10–11", "12–13", "14–15", "16"];
  var LINES = function (ws) { return '<div class="lines">' + ws.map(function (w) { return '<i style="width:' + w + '%"></i>'; }).join("") + "</div>"; };
  var PAGE4 = '<div class="pg l"><span class="cap">Personnel</span><h5>’Round About Midnight</h5><div class="credits">' +
    [["Trumpet", "Miles Davis"], ["Tenor sax", "John Coltrane"], ["Piano", "Red Garland"], ["Bass", "Paul Chambers"], ["Drums", "Philly Joe Jones"], ["Producer", "George Avakian"]]
      .map(function (c) { return "<span>" + c[0] + "</span><span>" + c[1] + "</span>"; }).join("") + "</div>" + LINES([92, 88, 95, 70, 90, 84, 60]) + '<span class="folio">4</span></div>';
  var PAGE5 = '<div class="pg r"><div class="photo"></div>' + LINES([96, 91, 94, 88, 93, 52]) + '<span class="folio">5</span></div>';

  function bookletWindow(o) {
    var side = !o.noSidebar && !o.min;
    var title = '<div class="b-title"><b>’Round About Midnight</b><span>' + esc(o.titleDetail) + "</span></div>";
    var editionMenu = !side && (o.editions || 3) > 1 ? '<button class="ib" style="width:auto;padding:0 8px;margin-right:8px">2001 US CD ▾</button>' : "";
    var tools = '<div class="b-tools">' + editionMenu + (o.pdf ? "" : '<div class="seg" role="group" aria-label="Layout"><button class="' + (o.page ? "on" : "") + '">Page</button><button class="' + (o.page ? "" : "on") + '">Spread</button></div>') +
      '<button class="ib" aria-label="Zoom out">−</button><span class="zoomval">' + (o.zoom || "Fit") + '</span><button class="ib" aria-label="Zoom in">+</button><button class="ib" aria-label="Actual size" title="Actual size (loads the full-resolution file)">1:1</button><button class="ib done">Done</button></div>';
    // Drawn with D1 (a): a sheet, so no window controls; Done (Escape) closes.
    var bar = '<div class="b-bar"><div></div>' + title + tools + "</div>";
    var eds = (o.pdf ? [{ name: "1999 EU CD", detail: "PDF · 12 pages" }] : EDITIONS.slice(0, o.editions || 3));
    var sidebar = side ? '<aside class="b-side"><div><h4>Editions · ' + eds.length + (eds.length === 1 ? " booklet" : " booklets") + '</h4><div class="eds">' + eds.map(function (e, i) {
      return '<button class="ed' + (i === 0 ? " on" : "") + '"><span class="mini' + (o.pdf ? "" : " paper") + '">' + (o.pdf ? "▤" : "") + "</span><span><b>" + esc(e.name) + "</b><small>" + esc(e.detail) + "</small>" +
        (e.tag ? '<span class="tag' + (e.owned ? " owned" : "") + '">' + esc(e.tag) + "</span>" : "") + "</span></button>";
    }).join("") + "</div></div>" + (o.extras !== false && !o.pdf ? '<div><h4>Extras</h4><div class="extras">' +
      [["Obi", "linear-gradient(90deg,#efe9dc 0 70%,#b0262c 70%)"], ["Sticker", "radial-gradient(circle,#e8c547 0 45%,#1b1b1d 46%)"], ["Poster", "linear-gradient(160deg,#3d5a80,#0b1320)"]]
        .map(function (x) { return '<button class="extra' + (o.extra === x[0] ? " on" : "") + '"><span class="x" style="background:' + x[1] + '"></span>' + x[0] + "</button>"; }).join("") + "</div></div>" : "") + "</aside>" : "";
    var stage;
    if (o.pdf) {
      stage = '<div class="pdfview"><div class="pg r"><span class="cap">Liner notes</span><h5>’Round About Midnight</h5>' + LINES([95, 90, 93, 88, 96, 91, 70, 94, 89, 92, 60]) + '<span class="folio">3</span></div></div>';
    } else if (o.loading) {
      stage = '<div class="spread-stage"><button class="arrow" aria-label="Previous spread">‹</button><div class="b-phase" style="height:470px"><div class="spin" aria-hidden="true"></div><div>Loading pages 4–5…</div></div><button class="arrow" aria-label="Next spread">›</button></div>';
    } else {
      var pages = o.extra ? '<div class="spread sq"><div class="pg obi"></div></div>' : o.page ? '<div class="spread one">' + PAGE4.replace("pg l", "pg") + "</div>" : '<div class="spread">' + PAGE4 + PAGE5 + "</div>";
      stage = '<div class="spread-stage"><button class="arrow" aria-label="Previous">‹</button>' + pages + '<button class="arrow" aria-label="Next"' + (o.extra === "Poster" ? " disabled" : "") + ">›</button></div>";
    }
    var caption = o.pdf ? "" : '<div class="caption"><b>' + esc(o.capTitle || "Pages 4–5 · Booklet, 2001 US CD") + "</b>" + (o.capQuote ? "<q>" + esc(o.capQuote) + "</q>" : "") +
      "<span>" + esc(o.capLine || "1400 × 1400 px each · ← → turn · pinch to zoom · double-click to fit") + "</span></div>";
    var strip = "";
    if (!o.pdf) {
      var items = o.page ? ["cv", "paper", "paper", "paper", "ph"].map(function (k, i) { return { k: [k], l: String(i + 1) }; }) : SPREADS.map(function (k, i) { return { k: k, l: LABELS[i] }; });
      var on = o.page ? 3 : o.extra ? -1 : 2;
      strip = '<nav class="strip" aria-label="Spreads">' + items.map(function (it, i) {
        return '<button class="thumbspread' + (i === on ? " on" : "") + '"><span class="tp">' + it.k.map(function (k) { return '<i class="' + (k === "ph" ? "paper ph" : k) + '"></i>'; }).join("") + "</span>" + it.l + "</button>";
      }).join("") + (o.page ? '<span class="thumbspread">…</span>' : "") +
        (o.extras !== false ? '<span class="sep"></span>' + [["ob", "Obi"], ["st", "Sticker"], ["po", "Poster"]].map(function (x) {
          return '<button class="thumbspread' + (o.extra === x[1] ? " on" : "") + '"><span class="tp"><i class="' + x[0] + '"></i></span>' + x[1] + "</button>";
        }).join("") : "") + "</nav>";
    }
    var cls = "win booklet" + (o.min ? " min" : "") + (!side && !o.min ? " nosidebar" : "");
    return '<div class="' + cls + '">' + bar + sidebar + '<div class="b-main">' + stage + caption + strip + "</div></div>";
  }

  // ---------- the states ----------
  var crewCounts = { Crew: 8 };
  var STATES = [
    ["paths-crew", "Paths 1 · Album sheet · Crew · Day · 1040 × 680", "The trail: one group per person, studio or work",
      "Groups in the order of their first stop in the server's answer; stops in server order inside a group. The first stop is selected when the tab loads, so the bar is never empty. Tab counts appear only for tabs already loaded.",
      function () { return pathsWindow({ subject: "album", tab: "Crew", groups: CREW, counts: crewCounts }); }],
    ["paths-crew-night", "Paths 2 · Crew · Night", "The same sheet in Night",
      "Every colour is a CU role, so Night needs no separate design. The selected card's artist line is CU.text here (CU.textSecondary would fall under 4.5:1 on the Night tint for some hues).",
      function () { return pathsWindow({ subject: "album", tab: "Crew", groups: CREW, counts: crewCounts, night: true, sel: 1 }); }],
    ["paths-filter", "Paths 3 · Filter: Not in library", "The client-side filter",
      "Hides cards, never asks the server. A group with no card left is hidden; the count says 'n of N'. The capped note stays. When the selected stop is hidden, the first visible stop is selected.",
      function () { return pathsWindow({ subject: "album", tab: "Crew", groups: CREW, counts: crewCounts, filterOn: "Not in library" }); }],
    ["paths-room", "Paths 4 · Room", "Same Room: session photos in the bar",
      "SameRoomPhotos moves from the inspector into the detail bar, under the evidence line, 96 × 64 each. Drawn only when at least one album has a photo (unchanged rule).",
      function () { return pathsWindow({ subject: "album", tab: "Room", groups: ROOM, counts: { Crew: 8, Room: 4 }, evidence: "recorded at · MusicBrainz" }); }],
    ["paths-gaps", "Paths 5 · Gaps", "Listen-through Gaps: owned only, with the play label",
      "Every stop is owned, so no Get marker and Play Album is the primary action. The play label is the card's extra line and the 'Your listening' card in the bar. History notes go under the trail.",
      function () { return pathsWindow({ subject: "album", tab: "Gaps", groups: GAPS, counts: { Crew: 8, Gaps: 3 }, filter: false,
        notes: ["2 albums reached by these credits left out because you have played them more than 1 time."] }); }],
    ["paths-sonic", "Paths 6 · Sonic", "Neighbours by Ear: no groups",
      "Sonic stops have no link, so the trail is flat: no rail, no pills. The extra line is the match count and the year. Skipped and truncation notes go under the cards.",
      function () { return pathsWindow({ subject: "album", tab: "Sonic", groups: SONIC, counts: { Crew: 8, Sonic: 5 }, filter: false, evidence: "sound analysis",
        notes: ["1 track has no sound analysis and was skipped."] }); }],
    ["paths-loading", "Paths 7 · Loading", "Loading",
      "Today's spinner and words. No skeleton shimmer (no continuous motion). The tabs and the summary are drawn at once.",
      function () { return pathsWindow({ subject: "album", tab: "Crew", phase: PHASE.loading, filter: false }); }],
    ["paths-failed", "Paths 8 · Failed", "Failed, with Request update",
      "Danger colour with its icon and sentence, never the accent. Request update only when the failure was 404 (not in the knowledge store); its progress note is under the buttons.",
      function () { return pathsWindow({ subject: "album", tab: "Crew", phase: PHASE.failed, filter: false }); }],
    ["paths-empty", "Paths 9 · Empty", "Empty",
      "The tab's own empty sentence, or the server's (Gaps says why nothing is listed). No detail bar.",
      function () { return pathsWindow({ subject: "album", tab: "Guests", phase: PHASE.empty, filter: false, counts: { Crew: 8, Guests: 0 } }); }],
    ["paths-artist-musician", "Paths 10 · Artist sheet · Follow the Musician", "Artist sheet: songs grouped by musician",
      "Same layout. A stop is a song: the cover is its album's, the second line is album · album artist. Primary action opens the album (or plays it when owned).",
      function () { return pathsWindow({ subject: "artist", subjectKind: "songs", tab: "Follow the Musician", groups: MUSICIAN, counts: { "Follow the Musician": 5 }, unit: "songs", unit1: "song", evidence: "performer · MusicBrainz" }); }],
    ["paths-artist-sideman", "Paths 11 · Artist sheet · Sideman", "Artist sheet: artists, round photos",
      "Sideman and Scene stops are artists: ArtistPhoto, round, the width of the card. No Get marker (an artist is not acquired here). The one action is Open Artist.",
      function () { return pathsWindow({ subject: "artist", subjectKind: "artist-people", tab: "Sideman", groups: SIDEMAN, counts: { "Follow the Musician": 5, Sideman: 3 }, round: true, unit: "artists", unit1: "artist", filter: true, evidence: "instrument · MusicBrainz" }); }],
    ["paths-min", "Paths 12 · Smallest size · 820 × 520", "Smallest size",
      "The sheet can be resized down to today's 820 × 520. The grid reflows (four columns here), the role line truncates, the bar keeps its buttons.",
      function () { return pathsWindow({ subject: "album", tab: "Crew", groups: CREW, counts: crewCounts, min: true }); }],
    ["booklet-spread", "Booklet 1 · Spread · 1120 × 740", "Facing spreads, named editions",
      "Spreads from BookletView.spreads: the cover alone, then pairs. The sidebar lists every booklet by edition; extras sit apart. The filmstrip shows every spread and the extras after a separator.",
      function () { return bookletWindow({ titleDetail: "Booklet · 2001 US CD · Pages 4–5 of 16", capQuote: "Inner spread with personnel and session photo" }); }],
    ["booklet-page", "Booklet 2 · Page", "Page mode",
      "One page at a time, as today. The filmstrip shows single pages. The choice is remembered for the session (not saved).",
      function () { return bookletWindow({ page: true, titleDetail: "Booklet · 2001 US CD · Page 4 of 16", capTitle: "Page 4 · Booklet, 2001 US CD", capLine: "1400 × 1400 px · ← → turn · pinch to zoom · double-click to fit" }); }],
    ["booklet-extra", "Booklet 3 · An extra", "An extra, alone",
      "Obi, Sticker and Poster are shown alone, at their own shape. Picked from the sidebar or the filmstrip; the arrows still walk on from the last spread into the extras.",
      function () { return bookletWindow({ extra: "Obi", titleDetail: "Booklet · 2001 US CD · Obi", capTitle: "Obi · 2001 US CD", capLine: "600 × 1600 px · ← → turn" }); }],
    ["booklet-single", "Booklet 4 · One booklet, no extras", "Sidebar collapsed",
      "With one booklet and no extras the sidebar is not drawn; the spread takes the width.",
      function () { return bookletWindow({ editions: 1, extras: false, noSidebar: true, titleDetail: "Booklet · 2001 US CD · Pages 4–5 of 16" }); }],
    ["booklet-pdf", "Booklet 5 · PDF booklet", "PDF booklet",
      "PDFKit, one page wide, continuous. No Page/Spread switch and no filmstrip. Zoom buttons set the PDFView scale; Fit is autoScales. Links in the PDF stay dead.",
      function () { return bookletWindow({ pdf: true, extras: false, titleDetail: "Booklet · 1999 EU CD · PDF, 12 pages", zoom: "Fit" }); }],
    ["booklet-loading", "Booklet 6 · Pages loading", "A spread still loading",
      "The spread's place keeps its size with a spinner, so nothing jumps. A page that fails says 'This page could not be loaded.' in the same place.",
      function () { return bookletWindow({ loading: true, titleDetail: "Booklet · 2001 US CD · Pages 4–5 of 16", capLine: "← → turn" }); }],
    ["booklet-min", "Booklet 7 · Narrow · 760 × 600", "Under 900 wide",
      "The sidebar gives way to an edition pop-up button in the bar (extras stay in the filmstrip).",
      function () { return bookletWindow({ min: true, titleDetail: "Pages 4–5 of 16" }); }]
  ];

  var params = new URLSearchParams(location.search);
  var only = params.get("only");
  var root = document.getElementById("root");
  if (only) document.body.classList.add("only");
  STATES.forEach(function (s) {
    if (only && s[0] !== only) return;
    var el = document.createElement("section");
    el.className = "state"; el.id = s[0];
    el.innerHTML = '<div class="eyebrow">' + s[1] + "</div><h2>" + s[2] + '</h2><p class="note">' + s[3] + '</p><div class="stage">' + s[4]() + "</div>";
    root.appendChild(el);
  });

  // Day / Night for the Paths drawings that follow the mode.
  document.querySelectorAll(".switch button").forEach(function (b) {
    b.addEventListener("click", function () {
      document.querySelectorAll(".switch button").forEach(function (x) { x.classList.toggle("on", x === b); });
      document.querySelectorAll(".paths.pb-mode").forEach(function (w) { w.classList.toggle("pb-night", b.dataset.mode === "night"); });
    });
  });
  // Selection inside each window (the detail bar is drawn for the first selection only; this shows the state change).
  document.querySelectorAll(".paths").forEach(function (w) {
    var cards = w.querySelectorAll(".stop");
    cards.forEach(function (c) { c.addEventListener("click", function () { cards.forEach(function (x) { x.classList.toggle("sel", x === c); }); }); });
  });
  [".ed", ".thumbspread", ".seg button"].forEach(function (sel) {
    document.querySelectorAll(".booklet").forEach(function (w) {
      var els = w.querySelectorAll(sel);
      els.forEach(function (e) { e.addEventListener("click", function () { els.forEach(function (x) { x.classList.toggle("on", x === e); }); }); });
    });
  });
})();
