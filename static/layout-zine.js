/* Zine Spread layout behaviour (D-024, docs/BRUT_ROUND3_PLAN.md, phase P1). Loaded after static/app.js; it defines functions that app.js
   calls through zineHook() and a few listeners. Every function returns at once unless <html data-layout="zine"> is set, and every
   element it fills is hidden by default and shown only by static/layouts.css, so no other theme changes. Nothing here makes a request
   of its own except one read of the existing /api/library/artists list (how many records of the lead story's artist are owned);
   Get, Save and Not for me are always the app's real controls. */

const ZINE_NUMBERS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
let zineLeadIndex = 0;
let zineJobs = [];
const zineOwnedCounts = new Map();

function zineOn() {
  return document.documentElement.dataset.layout === 'zine';
}

function zineFrontActive() {
  return Boolean($('zineFront')) && zineOn() && !isMobileLayout();
}

function zineWord(n) {
  return n >= 0 && n < ZINE_NUMBERS.length ? ZINE_NUMBERS[n] : String(n);
}

function zineSentence(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/* ---------------------------------------------------------------- page mast (THE DISCAIR DAILY / THE INDEX / THE WIRE) */
function zineDateLabel() {
  return new Date().toLocaleDateString('en-GB', {weekday: 'short', day: 'numeric', month: 'short'}).replace(/,/g, '').toUpperCase();
}

function updateZineMast() {
  const mast = $('zineMast');
  if (!mast || !zineOn()) return;
  const volume = /(\d+)\.(\d+)/.exec((document.querySelector('.app-version') || {}).textContent || '');
  let title = 'The Discair Daily';
  let note = 'Vol. ' + (volume ? volume[2] : '1') + ' · ' + zineDateLabel();
  let off = false;
  if (activePage === 'library') {
    if (!$('libraryDetailView').hidden) off = true;
    else if (!$('libraryAlbumView').hidden) {
      const album = albumPage.album;
      const genre = $('albumGenre').textContent.trim();
      note = ['Review', genre, album && album.year ? album.year : $('albumYear').textContent.trim()].filter(Boolean).join(' · ');
    } else if (!$('libraryGenreView').hidden) {
      title = 'The Index';
      note = 'Genre';
    } else {
      title = 'The Index';
      const noun = libraryView.tab === 'albums' ? 'albums' : 'artists';
      note = (libraryView.total ? Number(libraryView.total).toLocaleString() + ' ' + noun + ' · ' : '') + '/ to filter';
    }
  } else if (activePage === 'acquisitions') {
    const counts = acquisitionCounts(zineJobs);
    title = 'The Wire';
    note = counts.active + ' open · ' + counts.imported + ' imported this week';
  } else if (activePage !== 'dashboard') {
    const button = document.querySelector('nav button[data-page="' + activePage + '"]');
    if (button) note = (button.title || button.textContent.trim());
  }
  mast.dataset.off = off ? 'true' : 'false';
  $('zineMastTitle').textContent = title;
  $('zineMastNote').textContent = note;
}

/* ---------------------------------------------------------------- ticker */
function updateZineTicker(jobs) {
  zineJobs = Array.isArray(jobs) ? jobs : zineJobs;
  updateZineMast();
  const holder = $('zineTickerItems');
  if (!holder || !zineOn()) return;
  const counts = acquisitionCounts(zineJobs);
  const ordered = orderAcquisitions(zineJobs);
  const imported = ordered.filter(job => String(job.status || '').toLowerCase() === 'imported')
    .sort((a, b) => (Number(b.updated_at) || 0) - (Number(a.updated_at) || 0))[0];
  const failed = ordered.find(job => acquisitionStatusInfo(job.status).tone === 'error');
  const items = [];
  if (counts.active) items.push('▶ ' + counts.active + ' downloading');
  if (imported) {
    const when = Number(imported.updated_at) ? new Date(imported.updated_at * 1000).toLocaleTimeString('en-GB', {hour: '2-digit', minute: '2-digit'}) : '';
    items.push('● ' + (imported.album || imported.artist || 'An album') + ' imported' + (when ? ' ' + when : ''));
  }
  if (counts.failed) items.push('○ ' + counts.failed + ' failed: ' + ((failed && (failed.album || failed.artist)) || 'a request') + ' (retry)');
  const fresh = (shelfItems.NewReleases || []).length;
  if (fresh) items.push('▶ ' + fresh + ' new releases this week');
  const text = items.join('  ') || '▶ No open requests';
  if (holder.textContent !== text) holder.textContent = text;
}

/* ---------------------------------------------------------------- dashboard front page */
function zineLabelActions(tile) {
  const group = tile.querySelector('.card-art > .action-group');
  if (group) tile.append(group);
  const dismiss = tile.querySelector('.dismiss-album');
  if (dismiss && !dismiss.querySelector('.dismiss-album-label')) addTextElement(dismiss, 'span', 'dismiss-album-label', 'Not for me');
}

// What the library holds by this artist: its albums with their years, read once per artist from the existing library album list (exact
// artist-name match). null when the index cannot answer yet.
async function zineShelfFacts(artist) {
  const key = foldKey(artist);
  if (zineOwnedCounts.has(key)) return zineOwnedCounts.get(key);
  let facts = null;
  try {
    const data = await requestJSON('/api/library/albums?' + new URLSearchParams({q: artist, limit: '60', sort: 'year', order: 'asc'}));
    if (data.index_state !== 'building' && data.index_state !== 'unavailable') {
      const albums = (data.items || []).filter(item => foldKey(item.artist) === key)
        .map(item => ({name: displayAlbumName(item.name), year: Number(item.year) || null}));
      facts = {count: albums.length, albums};
    }
  } catch (error) {
    facts = null;
  }
  zineOwnedCounts.set(key, facts);
  return facts;
}

// The first quality the owner asked for (Settings), read once.
let zineQualityPromise = null;
function zineTargetQuality() {
  if (!zineQualityPromise) {
    zineQualityPromise = requestJSON('/api/settings/slskd').then(data => {
      const first = Array.isArray(data.quality_priority) ? data.quality_priority[0] : null;
      const option = qualityOptions.find(([value]) => value === first);
      return option ? option[1] : null;
    }).catch(() => null);
  }
  return zineQualityPromise;
}

// The album's own description (Apple Music, else Wikipedia), read once per album through the same endpoint the album page uses.
const zineDescriptions = new Map();
function zineAlbumDescription(artist, album) {
  const key = foldKey(artist) + '::' + foldKey(album);
  if (!zineDescriptions.has(key)) {
    zineDescriptions.set(key, requestJSON('/api/album-description?' + new URLSearchParams({artist, album})).catch(() => null));
  }
  return zineDescriptions.get(key);
}

function zineList(names) {
  if (names.length < 2) return names.join('');
  return names.slice(0, -1).join(', ') + ' and ' + names[names.length - 1];
}

const ZINE_ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth'];

// Where the pick sits among the records the library already holds, in words.
function zinePosition(artist, year, facts) {
  if (!facts || !facts.count) return facts ? 'is your way into ' + artist : '';
  const owned = facts.albums;
  const dated = owned.filter(entry => entry.year);
  if (year && dated.length) {
    const before = [...dated].reverse().find(entry => entry.year < year);
    const after = dated.find(entry => entry.year > year);
    if (before && after) return facts.count === 2 ? 'sits between the two you have' : 'sits between ' + before.name + ' and ' + after.name;
    if (before) return 'comes after ' + before.name + ', the latest you have';
    if (after) return 'comes before ' + after.name + ', the earliest you have';
  }
  return 'joins the ' + zineWord(facts.count) + ' you have' + (facts.count <= 3 ? ': ' + zineList(owned.map(entry => entry.name)) : '');
}

// The reason, in words: the owner's own plays of records by the artist, Last.fm neighbours, else the server's reason.
function zineWhy(item, facts, rank) {
  const key = foldKey(item.artist || item.album_artist || '');
  const owned = new Set(((facts && facts.albums) || []).map(entry => foldKey(entry.name)));
  const played = [];
  for (const entry of shelfItems.Frequent || []) {
    if (foldKey(entry.artist) === key && owned.has(foldKey(displayAlbumName(entry.name))) && !played.includes(displayAlbumName(entry.name))) played.push(displayAlbumName(entry.name));
  }
  const generic = /Genre tags connect this artist to your established musical interests/i.test(item.reason || '');
  const lead = rank === 0 ? 'Ranked first today' : 'Ranked ' + (ZINE_ORDINALS[rank] || '#' + (rank + 1)) + ' today';
  const parts = [];
  if (played.length) parts.push('from your plays of ' + zineList(played.slice(0, 2)));
  if (item.anchor_artist) parts.push((played.length ? 'and ' : '') + 'from Last.fm neighbours of ' + item.anchor_artist);
  if (parts.length) return lead + ' ' + parts.join(' ') + '.';
  if (item.reason && !generic) return lead + ': ' + item.reason.replace(/\.$/, '') + '.';
  return lead + ' among your recommendations.';
}

// A description is shortened at a sentence end so it fills the two columns without running on.
function zineExcerpt(paragraphs, limit) {
  const text = paragraphs.join(' ').replace(/\s+/g, ' ').trim();
  if (text.length <= limit) return text;
  const cut = text.slice(0, limit);
  const end = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf('! '), cut.lastIndexOf('? '));
  return (end > limit * 0.5 ? cut.slice(0, end + 1) : cut.replace(/\s+\S*$/, '') + '…');
}

function zineApplyLead(tile, item, rank) {
  const artist = item.artist || item.album_artist || 'this artist';
  const album = item.album || item.title || item.name || '';
  const headline = tile.querySelector('.zine-headline');
  const kicker = tile.querySelector('.zine-kicker');
  const blurb = tile.querySelector('.zine-blurb');
  const link = blurb.querySelector('a, button');
  Promise.all([zineShelfFacts(artist), zineTargetQuality(), zineAlbumDescription(artist, album)]).then(([facts, quality, description]) => {
    if (!tile.isConnected) return;
    const count = facts ? facts.count : null;
    if (count > 0) {
      headline.textContent = zineSentence('you own ' + zineWord(count) + ' ' + artist + (count === 1 ? ' record' : ' records') + '. Not this one.');
      kicker.textContent = 'Lead story · missing from your shelf';
    } else if (count === 0) {
      headline.textContent = 'Nothing by ' + artist + ' on your shelf. Start here.';
      kicker.textContent = 'Lead story · new to your shelf';
    } else {
      headline.textContent = artist + ', picked for you today.';
    }
    const year = firstReleaseYear(item.year, item.release_year, item.first_release_year);
    const position = zinePosition(artist, year ? Number(year) : null, facts);
    blurb.replaceChildren();
    if (link) blurb.append(link);
    blurb.append((year ? ' (' + year + ')' : '') + (position ? ' ' + position + '. ' : ' ') + zineWhy(item, facts, rank) + (quality ? ' Target quality: ' + quality + '.' : ''));
    // The album's own description is the better text; the artist's bio stays as the fallback when there is none.
    const paragraphs = description && Array.isArray(description.paragraphs) ? description.paragraphs : [];
    const text = tile.querySelector('.zine-desc');
    if (paragraphs.length) {
      text.textContent = zineExcerpt(paragraphs, 720);
      text.hidden = false;
      let credit = tile.querySelector('.zine-desc-credit');
      if (!credit) {
        credit = document.createElement('p');
        credit.className = 'zine-desc-credit';
        text.after(credit);
      }
      credit.textContent = 'About the album · ' + (description.source || 'Apple Music');
      tile.classList.add('has-desc');
    }
  });
}

// The lead story: a kicker, a headline sentence about what the library holds, a blurb that places the pick on your shelf and says why it
// was chosen, then the album's own description (the artist's bio when there is none), set in two columns.
function zineComposeLead(tile, item, rank) {
  const meta = tile.querySelector('.dashboard-tile-meta');
  if (!meta) return;
  const artist = item.artist || item.album_artist || 'this artist';
  const kicker = meta.querySelector('.card-category') || document.createElement('p');
  kicker.className = 'card-category zine-kicker';
  kicker.textContent = 'Lead story · missing from your shelf';
  const headline = document.createElement('h3');
  headline.className = 'zine-headline';
  headline.textContent = artist + ', picked for you today.';
  const blurb = document.createElement('p');
  blurb.className = 'zine-blurb';
  const albumHeading = meta.querySelector('h3:not(.zine-headline)');
  if (albumHeading) {
    // Only the album's own link goes into the blurb; the year and the listen count are written out or dropped.
    const link = albumHeading.querySelector('a, button');
    if (link) blurb.append(link);
    albumHeading.remove();
  }
  const text = document.createElement('p');
  text.className = 'zine-desc';
  text.hidden = true;
  meta.prepend(kicker, headline, blurb, text);
  zineApplyLead(tile, item, rank);
}

function zineVisiblePicks() {
  const picks = dashboardPickItems;
  if (!picks.length) return [];
  zineLeadIndex = ((zineLeadIndex % picks.length) + picks.length) % picks.length;
  return picks.map((item, index) => picks[(zineLeadIndex + index) % picks.length]);
}

function renderZineFront() {
  updateZineTicker();
  if (!zineFrontActive()) return;
  const lead = $('zineLead');
  const ads = $('zineClassifieds');
  lead.replaceChildren();
  ads.replaceChildren();
  const ordered = zineVisiblePicks();
  if (ordered.length) {
    const tile = buildDashboardTile(ordered[0]);
    tile.classList.add('zine-lead-tile');
    zineLabelActions(tile);
    zineComposeLead(tile, ordered[0], dashboardPickItems.indexOf(ordered[0]));
    lead.append(tile);
    for (const item of ordered.slice(1, 5)) {
      const ad = buildDashboardTile(item);
      ad.classList.add('zine-ad');
      zineLabelActions(ad);
      ads.append(ad);
    }
  }
  const wanted = ads.childElementCount;
  $('zineWanted').textContent = wanted ? 'Wanted: ' + wanted + ' albums, picked for your shelf.' : '';
  $('zineGetAll').hidden = !wanted;
  $('zineLeadStatus').textContent = ordered.length ? '' : ($('dashboardPicksStatus').textContent || 'No suggestions yet.');
  const fresh = $('zineNew');
  fresh.replaceChildren(...(shelfItems.NewReleases || []).slice(0, 6).map(item => {
    const card = buildShelfCard(item, true);
    const artistLine = card.querySelector('.card-artist');
    if (artistLine) artistLine.append(' · ' + (item.owned ? 'owned' : 'missing'));
    return card;
  }));
}

function focusZineLead() {
  const open = document.querySelector('#zineLead .dashboard-tile-open');
  if (open) open.focus();
}

// Next or previous story: the next recommendation takes the lead and the classifieds follow it.
function zineStep(delta) {
  const total = dashboardPickItems.length;
  if (total < 2) return;
  zineLeadIndex += delta;
  renderZineFront();
  $('zineLeadStatus').textContent = 'Story ' + (zineLeadIndex + 1) + ' of ' + total;
}

function zineGetAll() {
  const buttons = [...document.querySelectorAll('#zineClassifieds .get-album:not(:disabled)')];
  buttons.forEach((button, index) => setTimeout(() => button.click(), index * 150));
}

// The index at the foot of the front page opens the library at that range of letters.
const ZINE_RANGES = ['ABCD', 'EFGH', 'IJKL', 'MNOP', 'QRST', 'UVWXYZ'];
let zinePendingRange = null;
let zinePendingLoads = 0;

function zineBuildIndexFoot() {
  const holder = $('zineIndexChips');
  if (!holder || holder.childElementCount) return;
  for (const range of ZINE_RANGES) {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.textContent = range.charAt(0) + '–' + range.charAt(range.length - 1);
    chip.setAttribute('aria-label', 'Open the library index at ' + range.charAt(0) + ' to ' + range.charAt(range.length - 1));
    chip.addEventListener('click', () => zineOpenIndex(range));
    holder.append(chip);
  }
}

function zineOpenIndex(range) {
  zinePendingRange = range;
  zinePendingLoads = 0;
  libraryView.tab = 'artists';
  libraryView.sort = 'name';
  libraryView.order = 'asc';
  navigateTo('library');
}

/* ---------------------------------------------------------------- library: vertical letter margin, big letter headings */
function zineLetterOf(name) {
  const first = String(name || '').trim().charAt(0).normalize('NFD').charAt(0).toUpperCase();
  return /[A-Z]/.test(first) ? first : '#';
}

let zineLettersObserver = null;

function zineJumpTo(row) {
  row.scrollIntoView({block: 'start', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  const button = row.querySelector('button');
  if (button) button.focus({preventScroll: true});
}

function zineSyncActiveLetter() {
  const strip = $('zineLetters');
  if (!strip || !zineOn() || $('libraryListView').hidden || $('library').classList.contains('hidden')) return;
  const edge = 210;
  const rows = [...$('libraryList').querySelectorAll('.library-artist')];
  const row = rows.find(candidate => candidate.getBoundingClientRect().top > edge) || rows[rows.length - 1];
  const name = row && row.querySelector('.library-artist-name');
  const letter = name ? zineLetterOf(name.textContent) : '';
  for (const button of strip.querySelectorAll('button')) {
    if (button.textContent === letter) button.setAttribute('aria-current', 'true');
    else button.removeAttribute('aria-current');
  }
}

function updateZineLetters() {
  const strip = $('zineLetters');
  const list = $('libraryList');
  if (!strip || !zineOn()) return;
  if (zineLettersObserver) zineLettersObserver.disconnect();
  for (const old of list.querySelectorAll('.zine-letter-head')) old.remove();
  const firstRows = new Map();
  for (const row of [...list.children]) {
    const name = row.querySelector('.library-artist-name');
    if (!name) continue;
    const letter = zineLetterOf(name.textContent);
    if (!firstRows.has(letter)) firstRows.set(letter, row);
  }
  // The big letter heads only make sense while the list is in name order.
  if (libraryView.sort === 'name' && libraryView.display === 'list') {
    for (const [letter, row] of firstRows) {
      const head = document.createElement('li');
      head.className = 'zine-letter-head';
      head.setAttribute('aria-hidden', 'true');
      head.textContent = letter;
      list.insertBefore(head, row);
    }
  }
  const letters = [...'ABCDEFGHIJKLMNOPQRSTUVWXYZ', '#'];
  strip.replaceChildren(...letters.map(letter => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = letter;
    const row = firstRows.get(letter);
    if (row) {
      button.setAttribute('aria-label', 'Jump to ' + letter);
      button.addEventListener('click', () => zineJumpTo(row.previousElementSibling && row.previousElementSibling.classList.contains('zine-letter-head') ? row.previousElementSibling : row));
    } else {
      button.disabled = true;
      button.title = 'No loaded entry starts with ' + letter;
      button.setAttribute('aria-label', letter + ': no loaded entry');
    }
    return button;
  }));
  zineLettersObserver = zineLettersObserver || new MutationObserver(updateZineLetters);
  zineLettersObserver.observe(list, {childList: true});
  zineSyncActiveLetter();
  if (zinePendingRange) {
    const target = [...firstRows].find(([letter]) => zinePendingRange.includes(letter));
    if (target) {
      const row = target[1];
      zinePendingRange = null;
      zineJumpTo(row.previousElementSibling && row.previousElementSibling.classList.contains('zine-letter-head') ? row.previousElementSibling : row);
    } else if (libraryView.cursor && zinePendingLoads < 12 && !$('libraryMore').disabled) {
      zinePendingLoads += 1;
      $('libraryMore').click();
    } else if (!libraryView.cursor && list.querySelector('.library-artist')) {
      zinePendingRange = null;
    }
  }
}

/* ---------------------------------------------------------------- album: article byline, pull quote, missing-track coupon */
function zineDuration(tracks) {
  const seconds = tracks.reduce((sum, track) => sum + (Number(track.duration_seconds) || 0), 0);
  if (!seconds) return '';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);
  return (hours ? hours + 'h ' : '') + minutes + 'm';
}

function renderZineAlbum() {
  updateZineMast();
  const by = $('zineAlbumBy');
  if (!by || !zineOn()) return;
  const album = albumPage.album;
  const tracks = albumPage.tracks || [];
  const pull = $('zinePull');
  const getMissing = $('zineGetMissing');
  if (!album) {
    by.hidden = pull.hidden = getMissing.hidden = true;
    return;
  }
  const owned = tracks.filter(track => track.owned).length;
  const missing = tracks.length - owned;
  const line1 = [album.artist, tracks.length ? tracks.length + ' tracks' : '', zineDuration(tracks)].filter(Boolean).join(' · ');
  const line2 = [album.quality, tracks.length ? 'owned ' + owned + ' of ' + tracks.length : ''].filter(Boolean).join(' · ');
  by.replaceChildren(line1);
  if (line2) by.append(document.createElement('br'), line2);
  by.hidden = false;
  if (tracks.length) {
    let quote;
    if (!missing) quote = 'Every song is on your shelf.';
    else if (!owned) quote = zineSentence(zineWord(tracks.length)) + ' songs, none on your shelf yet.';
    else quote = zineSentence(zineWord(owned)) + ' of ' + zineWord(tracks.length) + ' songs on your shelf. ' + (missing === 1 ? 'One is a coupon.' : zineSentence(zineWord(missing)) + ' are coupons.');
    pull.textContent = '“' + quote + '”';
    pull.hidden = false;
  } else {
    pull.hidden = true;
  }
  getMissing.hidden = !(owned && missing);
  getMissing.textContent = missing === 1 ? 'Get missing track' : 'Get ' + missing + ' missing tracks';
}

function zineGetMissing() {
  const buttons = [...document.querySelectorAll('#albumTracks .get-track:not(:disabled)')];
  buttons.forEach((button, index) => setTimeout(() => button.click(), index * 150));
}

/* ---------------------------------------------------------------- artist: cover lines and back issues */
function zineIssueCard(item) {
  const row = document.createElement('li');
  row.className = 'zine-issue' + (item.owned ? '' : ' is-missing');
  const open = document.createElement('button');
  open.type = 'button';
  open.className = 'zine-issue-open';
  open.append(buildAlbumArtwork(item, 'zine-issue-art', 300));
  addTextElement(open, 'span', 'zine-issue-name', displayAlbumName(item.name));
  open.addEventListener('click', () => libraryOpen(albumTarget(item)));
  row.append(open);
  addTextElement(row, 'span', 'zine-issue-state', item.owned ? 'Owned' : 'Missing · Get');
  if (!item.owned) row.append(wrapInActionGroup(buildAlbumState(item), 'Actions for ' + item.name));
  return row;
}

function renderZineArtist(ctx) {
  const lines = $('zineCoverLines');
  if (!lines || !zineOn() || !ctx) return;
  updateZineMast();
  const owned = ctx.ownedAlbums || [];
  const missing = (ctx.missing || []).slice(0, 15);
  const songs = (ctx.topSongs || []).map(song => song.name);
  const rows = [];
  if (songs[0]) rows.push('Inside: ' + songs[0]);
  if (songs.length > 1) rows.push(songs.slice(1, 3).join(' · '));
  if (ctx.missing) rows.push(owned.length + ' of ' + (owned.length + ctx.missing.length) + ' issues on your shelf');
  else if (owned.length) rows.push(pluralize(owned.length, 'issue', 'issues') + ' on your shelf');
  const similar = (ctx.similar || []).map(entry => entry.name).filter(Boolean).slice(0, 2);
  if (similar.length) rows.push('Also: ' + similar.join(', '));
  lines.replaceChildren(...rows.map(text => addTextElement(lines, 'div', '', text)));
  lines.hidden = !rows.length;
  const section = $('zineIssuesSection');
  const items = [...owned, ...missing];
  $('zineIssues').replaceChildren(...items.map(zineIssueCard));
  section.hidden = !items.length;
}

/* ---------------------------------------------------------------- keys: J / K, / */
document.addEventListener('keydown', event => {
  if (!zineOn() || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
  const target = event.target;
  if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
  if (!$('albumModalBackdrop').hidden) return;
  const key = event.key.toLowerCase();
  const page = ['dashboard', 'library'].find(id => !$(id).classList.contains('hidden'));
  if (key === '/' && page === 'library' && !$('libraryListView').hidden) {
    event.preventDefault();
    $('libraryFilter').focus();
    return;
  }
  if (key !== 'j' && key !== 'k') return;
  if (page === 'dashboard' && zineFrontActive()) {
    event.preventDefault();
    zineStep(key === 'j' ? 1 : -1);
    return;
  }
  if (page !== 'library' || $('libraryListView').hidden) return;
  const lines = [...document.querySelectorAll('#libraryList .library-artist')].filter(el => el.getClientRects().length > 0);
  if (!lines.length) return;
  event.preventDefault();
  const at = lines.indexOf(document.activeElement);
  lines[key === 'j' ? Math.min(at + 1, lines.length - 1) : Math.max(at < 0 ? 0 : at - 1, 0)].focus();
});

/* ---------------------------------------------------------------- wiring */
function zineWire() {
  if ($('zineShuffle')) $('zineShuffle').addEventListener('click', () => $('shuffleDashboard').click());
  if ($('zineGetAll')) $('zineGetAll').addEventListener('click', zineGetAll);
  if ($('zineGetMissing')) $('zineGetMissing').addEventListener('click', zineGetMissing);
  zineBuildIndexFoot();
  // The picks' own status line is mirrored under the lead story, because the layout hides the panel that holds it.
  if ($('dashboardPicksStatus')) {
    new MutationObserver(() => {
      if (zineFrontActive() && !dashboardPickItems.length) $('zineLeadStatus').textContent = $('dashboardPicksStatus').textContent;
    }).observe($('dashboardPicksStatus'), {childList: true, characterData: true, subtree: true});
  }
  window.addEventListener('scroll', zineSyncActiveLetter, {passive: true});
  // The layout is chosen in Settings without a reload, so build (or clear) what it shows when it changes.
  new MutationObserver(() => {
    renderZineFront();
    updateZineLetters();
    updateZineMast();
  }).observe(document.documentElement, {attributes: true, attributeFilter: ['data-layout']});
  if (zineOn()) {
    renderZineFront();
    updateZineLetters();
    updateZineMast();
  }
}

zineWire();
