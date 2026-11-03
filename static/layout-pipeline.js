/* Pipeline Board layout behaviour (D-024, docs/BRUT_ROUND3_PLAN.md, phases P2 and P2b). app.js calls the render functions below through
   zineHook(). Every function returns at once unless <html data-layout="pipeline"> is set and the window is 901px or wider, and every element
   they fill is hidden by default, so no other theme changes. Cards are built with the app's own builders (buildShelfCard, buildSavedCard,
   createGetButton, createSaveButton) so Get, Save and their states have one source of truth. A drop never calls the network itself: Queued
   clicks the card's real Get button (searchAlbum) and Saved clicks its real Save button. Retry and Dismiss on the Acquisitions board click the
   real row's own buttons. The board redraws from the acquisition list, so a card moves only when the server reports it. Destructive actions
   (Not for me, Dismiss) have no drop target. The only network reads are the existing ones: /api/discovery/for_me, /api/dashboard/genres and
   /api/genres/{tag}. */

const PIPELINE_COLUMNS = [
  {key: 'recommended', title: 'Recommended'},
  {key: 'saved', title: 'Saved'},
  {key: 'queued', title: 'Queued'},
  {key: 'downloading', title: 'Downloading'},
  {key: 'library', title: 'In library'}
];
// Columns a card can be dropped on. Not for me has no drop target: it stays a button.
const PIPELINE_DROP = new Set(['queued', 'saved']);
const PIPELINE_ACQ_COLUMNS = [
  {key: 'queued', title: 'Queued'},
  {key: 'downloading', title: 'Downloading'},
  {key: 'done', title: 'Done (Imported)'},
  {key: 'failed', title: 'Failed'}
];
const PIPELINE_RETRYABLE = new Set(['no_matches', 'queue_failed', 'settings_required', 'slskd_error']);
const PIPELINE_DOWNLOADING = new Set(['downloading', 'download_complete_waiting_for_folder', 'importing', 'monitoring']);
const PIPELINE_STAGES = ['Recommended', 'Saved', 'Queued', 'Downloaded', 'In library'];
const PIPELINE_STAGE_WORDS = {done: 'Done', current: 'Now', todo: 'To do'};
const PIPELINE_LANE_ALBUMS = 12;
const PIPELINE_ARTIST_HEADINGS = {
  artistOwnedHeading: ['In your library', 'In library'],
  artistMissingHeading: ['Missing albums', 'Missing (drag to Queued)'],
  artistSimilarHeading: ['Similar artists', 'Similar artists'],
};

let pipelineJobs = [];
let pipelineSaved = null;      // entries from /api/discovery/for_me
let pipelineSavedAt = 0;       // when they were read; the list is read again after a minute
let pipelineSavedLoading = null;
let pipelineGenres = null;     // the dashboard genre list, read once per page load
let pipelineGenresLoading = null;
let pipelineDragged = null;    // the card being dragged, set on dragstart and cleared on dragend
let pipelineLaneSeq = 0;

function pipelineOn() {
  return document.documentElement.dataset.layout === 'pipeline';
}

// The board, lanes and stage tracker show only in this layout, from 901px up (below that the phone shell is kept).
function pipelineWide() {
  return pipelineOn() && !isMobileLayout() && window.matchMedia('(min-width: 901px)').matches;
}

function pipelineActive() {
  return Boolean($('pipelineBoard')) && pipelineWide();
}

function pipelineSay(text, target = 'pipelineToast') {
  const toast = $(target);
  if (toast) toast.textContent = text;
}

// The Saved list, read with the Saved page's own endpoint and kept for a minute so redraws do not refetch.
function pipelineLoadSaved() {
  if (pipelineSaved && Date.now() - pipelineSavedAt < 60000) return Promise.resolve(pipelineSaved);
  if (!pipelineSavedLoading) {
    pipelineSavedLoading = requestJSON('/api/discovery/for_me?count=150&nonce=' + Date.now())
      .then(data => {
        pipelineSaved = data.items || [];
        pipelineSavedAt = Date.now();
        return pipelineSaved;
      })
      .catch(() => {
        pipelineSaved = [];
        return pipelineSaved;
      })
      .finally(() => {
        pipelineSavedLoading = null;
      });
  }
  return pipelineSavedLoading;
}

// The genre list the dashboard reads (the same request as its genre tiles). A failure is not kept, so the next open tries again.
function pipelineLoadGenres() {
  if (pipelineGenres) return Promise.resolve(pipelineGenres);
  if (!pipelineGenresLoading) {
    pipelineGenresLoading = requestJSON('/api/dashboard/genres?limit=60')
      .then(data => {
        pipelineGenres = data.items || [];
        return pipelineGenres;
      })
      .finally(() => {
        pipelineGenresLoading = null;
      });
  }
  return pipelineGenresLoading;
}

// A pick as a shelf item, so the shelf card (and its real Get and Save) is built by the existing builder.
function pipelinePickAsShelf(item) {
  return {
    ...item,
    name: item.album || item.title || item.name || 'Untitled album',
    artist: item.artist || item.album_artist || 'Unknown artist',
    owned: false
  };
}

// Album names and artists in the different lists use different keys (album/name/title); compare them folded.
function pipelineNameOf(entry) {
  return String(entry.album || entry.name || entry.title || '');
}

function pipelineSameAlbum(entry, artist, album) {
  return pipelineNameOf(entry).toLocaleLowerCase() === String(album || '').toLocaleLowerCase()
    && String(entry.artist || entry.album_artist || '').toLocaleLowerCase() === String(artist || '').toLocaleLowerCase();
}

// A tile is the mockup's card: a small cover, the title and the artist, with the genre colour edge. Its controls are the app's own
// Get, Save and Not for me (createActionGroup), so a tile that is not in the library carries the real request and bookmark.
function pipelineTile(item, options = {}) {
  const name = item.name || item.album || 'Untitled album';
  const artist = item.artist || item.album_artist || 'Unknown artist';
  const owned = Boolean(item.owned);
  const tile = document.createElement('article');
  tile.className = 'card pipeline-tile' + (owned ? ' is-owned' : '');
  tile.dataset.album = name;
  tile.style.setProperty('--tc', 'hsl(' + genreTileHue(artist) + ' 70% 45%)');
  const open = document.createElement('button');
  open.type = 'button';
  open.className = 'pipeline-tile-open';
  open.setAttribute('aria-label', 'Open ' + name + ' by ' + artist);
  open.append(buildAlbumArtwork({artwork_url: item.artwork_url, owned, artist, name}, 'pipeline-tile-art', 84));
  const text = document.createElement('span');
  text.className = 'pipeline-tile-text';
  addTextElement(text, 'b', '', displayAlbumName(name));
  addTextElement(text, 'small', '', artist);
  const genre = options.genre || (Array.isArray(item.genres) && item.genres[0]) || '';
  if (genre) addTextElement(text, 'small', 'pipeline-tile-genre', genre);
  open.append(text);
  open.addEventListener('click', () => openLibraryTarget(owned
    ? albumTarget({...item, name, artist, key: foldKey(artist) + '/' + foldKey(name)})
    : namedAlbumTarget(artist, name, item)));
  tile.append(open);
  // Not in the library: the app's own Get, Save and Not for me stay in the tile, hidden, so a drop can click them. The album page
  // shows them as visible buttons (the tile opens it).
  if (!owned) {
    const metadata = {artist, album: name, year: item.year || null, release_group_mbid: item.release_group_mbid || null};
    const group = createActionGroup(artist, name, metadata, {
      listName: options.listName || 'dashboard_shelf',
      onDismiss: () => sendFeedback('dismiss', artist, name, metadata, options.listName || 'dashboard_shelf', tile),
    });
    group.classList.add('pipeline-hidden-controls');
    if (options.saved) setSaveButtonState(group.querySelector('.save-album'), true, name);
    tile.append(group);
  }
  return tile;
}

function pipelineColumnElement(column) {
  const section = document.createElement('section');
  section.className = 'pipeline-col';
  section.dataset.col = column.key;
  const head = document.createElement('h3');
  head.className = 'pipeline-col-head';
  head.id = 'pipelineCol-' + column.key;
  head.textContent = column.title;
  const badge = document.createElement('em');
  badge.textContent = '0';
  head.append(badge);
  const list = document.createElement('div');
  list.className = 'pipeline-list';
  list.setAttribute('aria-labelledby', head.id);
  section.append(head, list);
  if (PIPELINE_DROP.has(column.key)) {
    section.addEventListener('dragover', event => {
      if (!pipelineDragged) return;
      event.preventDefault();
      section.classList.add('over');
    });
    section.addEventListener('dragleave', event => {
      if (!section.contains(event.relatedTarget)) section.classList.remove('over');
    });
    section.addEventListener('drop', event => {
      if (!pipelineDragged) return;
      event.preventDefault();
      section.classList.remove('over');
      pipelineAct(pipelineDragged, column.key);
    });
  }
  return {section, list};
}

// The toast follows the real Get control's own state, so a failed request is reported in words instead of the pending line.
function pipelineFollowGet(get, album, target) {
  const watch = new MutationObserver(() => {
    if (get.classList.contains('is-pending')) return;
    watch.disconnect();
    if (get.classList.contains('is-failed')) pipelineSay(get.title || album + ' could not be requested. Try again.', target);
    else pipelineSay(album + ' is requested. It moves to Queued when the server confirms.', target);
  });
  watch.observe(get, {attributes: true, attributeFilter: ['class', 'title', 'disabled']});
}

// The card's own controls, reached by a pointer drop. The drop ends in the same click the album page offers.
function pipelineAct(card, target) {
  const album = card.dataset.album || 'this album';
  if (target === 'queued') {
    const get = card.querySelector('.get-album');
    if (!get || get.disabled) {
      pipelineSay(get ? album + ' is already being requested.' : album + ' has no Get to run: it is already in your library.');
      return;
    }
    pipelineSay('Requesting ' + album + '. It moves to Queued when the server confirms.');
    pipelineFollowGet(get, album, 'pipelineToast');
    get.click();
  } else if (target === 'saved') {
    const save = card.querySelector('.save-album');
    if (!save || save.getAttribute('aria-pressed') === 'true') {
      pipelineSay(album + ' is already saved.');
      return;
    }
    save.click();
  }
}

function pipelineMakeDraggable(card) {
  card.classList.add('pipeline-card');
  card.draggable = true;
  card.addEventListener('dragstart', event => {
    pipelineDragged = card;
    card.classList.add('is-dragging');
    event.dataTransfer.effectAllowed = 'copy';
    event.dataTransfer.setData('text/plain', card.dataset.album || '');
  });
  card.addEventListener('dragend', () => {
    card.classList.remove('is-dragging');
    pipelineDragged = null;
    document.querySelectorAll('.pipeline-col.over, .pipeline-drop.over').forEach(col => col.classList.remove('over'));
  });
}

// One card for a request: the title and state in words, a bar and percentage while it downloads.
function pipelineJobCard(job) {
  const info = acquisitionStatusInfo(job.status);
  const card = document.createElement('article');
  card.className = 'card pipeline-job';
  card.dataset.album = job.album || '';
  card.append(buildAlbumArtwork({artist: job.artist, name: job.album, artwork_url: null}, 'pipeline-tile-art', 84));
  const text = document.createElement('span');
  text.className = 'pipeline-tile-text';
  addTextElement(text, 'b', '', job.album || 'Untitled album');
  addTextElement(text, 'small', '', [job.artist, info.label].filter(Boolean).join(' · '));
  card.append(text);
  const details = job.details || {};
  const progress = details.live_progress;
  if (String(job.status || '').toLowerCase() === 'downloading' && progress && Number.isFinite(Number(progress.percent))) {
    const percent = Math.max(0, Math.min(100, Math.round(Number(progress.percent))));
    const bar = document.createElement('div');
    bar.className = 'pipeline-bar';
    bar.setAttribute('aria-hidden', 'true');
    const fill = document.createElement('i');
    fill.style.width = percent + '%';
    bar.append(fill);
    const text = document.createElement('small');
    const speed = Number(progress.speed_bytes_per_second);
    text.textContent = percent + '% downloaded' + (Number.isFinite(speed) && speed > 0 ? ' · ' + (speed / (1024 * 1024)).toFixed(1) + ' MB/s' : '');
    card.append(bar, text);
  }
  return card;
}

// Which dashboard column a request belongs in. Imported requests are in the library column, from the recent shelf.
function pipelineJobColumn(job) {
  const status = String(job.status || '').toLowerCase();
  if (status === 'imported') return null;
  // A failed request has no column on the dashboard board; it is on the Acquisitions board's Failed column.
  if (acquisitionStatusInfo(job.status).tone === 'error') return null;
  if (PIPELINE_DOWNLOADING.has(status)) return 'downloading';
  return 'queued';
}

function renderPipelineBoard(jobs) {
  if (Array.isArray(jobs)) pipelineJobs = jobs;
  renderPipelineAcquisitions();
  const board = $('pipelineBoard');
  if (!board) return;
  if (!pipelineActive()) {
    board.hidden = true;
    return;
  }
  board.hidden = false;
  const cols = $('pipelineCols');
  const lists = new Map();
  cols.replaceChildren(...PIPELINE_COLUMNS.map(column => {
    const built = pipelineColumnElement(column);
    lists.set(column.key, built.list);
    return built.section;
  }));

  // Recommended: the same picks the carousel shows, as shelf cards with their real Get and Save.
  const picks = (typeof dashboardPickItems !== 'undefined' ? dashboardPickItems : []);
  for (const item of picks.slice(0, 12)) {
    const shelf = pipelinePickAsShelf(item);
    pipelinePlaceCard(pipelineTile(shelf, {listName: 'dashboard_shelf'}), lists.get('recommended'), shelf.name);
  }
  // Queued and Downloading: from the acquisition list already loaded.
  for (const job of pipelineJobs) {
    const column = pipelineJobColumn(job);
    if (column) lists.get(column).append(pipelineJobCard(job));
  }
  // In library: the recent library shelf, already loaded by the dashboard.
  for (const item of (shelfItems.Recent || []).slice(0, 12)) {
    pipelinePlaceCard(pipelineTile({...item, owned: true}), lists.get('library'), item.name);
  }

  // Saved: the Saved page's list, with the existing Saved card. The column waits for its list, so it shows no empty message until then.
  pipelineLoadSaved().then(entries => {
    if (!pipelineActive()) return;
    const list = lists.get('saved');
    if (!list) return;
    list.replaceChildren();
    for (const entry of entries.slice(0, 12)) pipelinePlaceCard(pipelineTile({...entry, name: pipelineNameOf(entry)}, {listName: 'saved', saved: true}), list, pipelineNameOf(entry));
    finishPipelineColumns(cols, lists);
    renderPipelineAlbum();
  });
  finishPipelineColumns(cols, lists, new Set(['saved']));
}

// Every card gets a drag handle; the card itself stays the element the tile builder made.
function pipelinePlaceCard(card, list, album) {
  card.dataset.album = album || '';
  pipelineMakeDraggable(card);
  list.append(card);
}

// Counts follow the cards; an empty column says so in words.
function finishPipelineColumns(cols, lists, waiting = new Set()) {
  for (const [key, list] of lists) {
    const empty = list.querySelector(':scope > .pipeline-empty');
    if (empty) empty.remove();
    if (!waiting.has(key) && !list.querySelector(':scope > .card')) list.append(pipelineEmpty(key));
  }
  updatePipelineCounts(cols);
}

function pipelineEmpty(key) {
  const text = document.createElement('p');
  text.className = 'pipeline-empty';
  const names = {recommended: 'No picks yet.', saved: 'Nothing saved yet.', queued: 'Nothing queued.', downloading: 'Nothing downloading.', library: 'Nothing imported recently.', done: 'Nothing imported yet.', failed: 'Nothing has failed.'};
  text.textContent = names[key] || 'Nothing here.';
  return text;
}

function updatePipelineCounts(cols) {
  for (const section of cols.querySelectorAll('.pipeline-col')) {
    const list = section.querySelector('.pipeline-list');
    const badge = section.querySelector('.pipeline-col-head em');
    if (badge && list) badge.textContent = String(list.querySelectorAll(':scope > .card').length);
  }
}

/* ---------------------------------------------------------------- Acquisitions board (P2b)
   Four columns from the same list the Acquisitions page renders. Retry and Dismiss are proxies: each click runs the real row's own button,
   so its handler, its state and its request are the existing ones. Imported requests the user dismissed stay hidden, as on the page. */

function pipelineAcqColumn(job) {
  const status = String(job.status || '').toLowerCase();
  if (status === 'dismissed') return null;
  if (status === 'imported') return dismissedImports().has(acquisitionRowKey(job)) ? null : 'done';
  if (acquisitionStatusInfo(job.status).tone === 'error') return 'failed';
  if (PIPELINE_DOWNLOADING.has(status)) return 'downloading';
  return 'queued';
}

function dismissedImports() {
  try {
    return new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-acquisitions') || '[]'));
  } catch (error) {
    return new Set();
  }
}

// The real row for a request, found by its key. Its own buttons do the work.
function pipelineRealRow(key) {
  return Array.from(document.querySelectorAll('#acquisitionCards .acq-row')).find(row => row.dataset.acqKey === key) || null;
}

function pipelineProxyButton(label, className, job) {
  const album = job.album || job.artist || 'this acquisition';
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'pipeline-proxy ' + className;
  button.textContent = label;
  button.setAttribute('aria-label', label + ' ' + album);
  button.addEventListener('click', () => {
    const real = pipelineRealRow(acquisitionRowKey(job));
    const control = real && real.querySelector('.' + className);
    if (!control || control.disabled) {
      pipelineSay(label + ' is not available for ' + album + ' right now.', 'pipelineAcqStatus');
      return;
    }
    control.click();
  });
  return button;
}

function pipelineAcqCard(job) {
  const card = pipelineJobCard(job);
  card.classList.add('pipeline-acq-card');
  card.dataset.status = String(job.status || 'unknown');
  const actions = document.createElement('div');
  actions.className = 'pipeline-acq-actions';
  if (PIPELINE_RETRYABLE.has(String(job.status || '').toLowerCase())) actions.append(pipelineProxyButton('Retry', 'retry-acquisition', job));
  actions.append(pipelineProxyButton('Dismiss', 'dismiss-album', job));
  card.append(actions);
  return card;
}

function renderPipelineAcquisitions() {
  const board = $('pipelineAcq');
  if (!board) return;
  board.hidden = !pipelineWide();
  if (board.hidden) return;
  const cols = $('pipelineAcqCols');
  if (!cols.childElementCount) {
    cols.replaceChildren(...PIPELINE_ACQ_COLUMNS.map(column => {
      const built = pipelineColumnElement({key: 'acq-' + column.key, title: column.title});
      built.section.dataset.acq = column.key;
      built.section.classList.add('pipeline-acq-col');
      built.section.querySelector('.pipeline-col-head').id = 'pipelineAcq-' + column.key;
      built.list.setAttribute('aria-labelledby', 'pipelineAcq-' + column.key);
      return built.section;
    }));
  }
  const buckets = new Map(PIPELINE_ACQ_COLUMNS.map(column => [column.key, []]));
  for (const job of pipelineJobs) {
    const key = pipelineAcqColumn(job);
    if (key) buckets.get(key).push(job);
  }
  for (const column of PIPELINE_ACQ_COLUMNS) {
    const section = cols.querySelector('[data-acq="' + column.key + '"]');
    const list = section.querySelector('.pipeline-list');
    const items = buckets.get(column.key);
    section.querySelector('.pipeline-col-head em').textContent = String(items.length);
    // A column is redrawn only when its own content changed, so a button a keyboard user is on keeps its focus.
    const signature = JSON.stringify(items);
    if (section.dataset.sig === signature) continue;
    section.dataset.sig = signature;
    const cards = items.map(pipelineAcqCard);
    list.replaceChildren(...(cards.length ? cards : [pipelineEmpty(column.key)]));
  }
}

/* ---------------------------------------------------------------- Library: genre swimlanes (P2b)
   One lane per genre from the dashboard's genre list. A lane loads its albums the first time it is opened, from the genre endpoint the
   accordion uses, and shows them as the app's own shelf cards with their real Get and Save. */

function renderPipelineLanes() {
  const box = $('pipelineLanes');
  if (!box) return;
  box.hidden = !pipelineWide();
  if (box.hidden || box.dataset.built === '1') return;
  box.dataset.built = '1';
  const status = $('pipelineLanesStatus');
  const list = $('pipelineLaneList');
  status.textContent = 'Loading genres…';
  pipelineLoadGenres().then(genres => {
    status.textContent = genres.length ? '' : 'No genres in your library yet.';
    $('pipelineLanesCount').textContent = pluralize(genres.length, 'genre', 'genres');
    list.replaceChildren(...genres.map(buildPipelineLane));
    const genreSelect = $('pipelineFilterGenre');
    genreSelect.replaceChildren(new Option('All genres', ''), ...genres.map(genre => new Option(genre.name, genre.tag)));
    pipelineApplyLaneFilters();
  }).catch(() => {
    box.dataset.built = '';
    status.textContent = 'Genres could not be loaded. Open Library again to retry.';
  });
}

// Each lane's albums load once, when the lane first comes into view (the mockup's lanes are always open, so "open" means "seen").
const pipelineLaneObserver = typeof IntersectionObserver === 'function'
  ? new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      pipelineLaneObserver.unobserve(entry.target);
      pipelineLoadLane(entry.target);
    }
  }, {rootMargin: '200px'})
  : null;

function buildPipelineLane(genre) {
  const lane = document.createElement('section');
  lane.className = 'pipeline-lane';
  lane.dataset.tag = genre.tag;
  lane.dataset.name = genre.name;
  lane.style.setProperty('--tc', 'hsl(' + genreTileHue(genre.tag) + ' 70% 45%)');
  addTextElement(lane, 'b', 'pipeline-lane-name', genre.name);
  const tiles = document.createElement('div');
  tiles.className = 'pipeline-lane-tiles';
  tiles.setAttribute('aria-label', genre.name + ' albums');
  const note = addTextElement(tiles, 'p', 'pipeline-lane-note', 'Loading albums…');
  note.dataset.loading = '1';
  lane.append(tiles);
  if (pipelineLaneObserver) pipelineLaneObserver.observe(lane);
  else pipelineLoadLane(lane);
  return lane;
}

async function pipelineLoadLane(lane) {
  const tiles = lane.querySelector('.pipeline-lane-tiles');
  try {
    const data = await requestJSON('/api/genres/' + encodeURIComponent(lane.dataset.tag));
    const section = data.sections && data.sections.albums;
    const items = section && section.available ? section.items.filter(item => item.name).slice(0, PIPELINE_LANE_ALBUMS) : [];
    tiles.replaceChildren();
    if (!items.length) {
      addTextElement(tiles, 'p', 'pipeline-lane-note', 'No albums could be listed for this genre right now.');
    } else {
      for (const item of items) {
        const tile = pipelineTile({...item, owned: Boolean(item.owned)}, {listName: 'library_lane', genre: lane.dataset.name});
        tile.dataset.year = item.year ? String(item.year) : '';
        tile.dataset.genre = lane.dataset.tag;
        tiles.append(tile);
      }
    }
    const all = document.createElement('button');
    all.type = 'button';
    all.className = 'link-button pipeline-lane-all';
    all.textContent = 'Open the ' + lane.dataset.name + ' page';
    all.addEventListener('click', () => openLibraryTarget({type: 'genre', tag: lane.dataset.tag}));
    tiles.append(all);
    pipelineApplyLaneFilters();
  } catch (error) {
    tiles.replaceChildren();
    addTextElement(tiles, 'p', 'pipeline-lane-note', 'This genre could not be loaded. Reload Library to try again.');
  }
}

// Filter ▸ genre · year. Quality is shown in the mockup but the library rows carry no quality field, so it is shown disabled.
function pipelineApplyLaneFilters() {
  const genre = $('pipelineFilterGenre') ? $('pipelineFilterGenre').value : '';
  const year = $('pipelineFilterYear') ? $('pipelineFilterYear').value : '';
  const years = new Set();
  for (const lane of document.querySelectorAll('#pipelineLaneList .pipeline-lane')) {
    const onGenre = !genre || lane.dataset.tag === genre;
    lane.hidden = !onGenre;
    for (const tile of lane.querySelectorAll('.pipeline-tile')) {
      if (tile.dataset.year) years.add(tile.dataset.year);
      tile.hidden = Boolean(year) && tile.dataset.year !== year;
    }
  }
  const yearSelect = $('pipelineFilterYear');
  if (yearSelect && yearSelect.dataset.count !== String(years.size)) {
    const current = yearSelect.value;
    yearSelect.replaceChildren(new Option('Any year', ''), ...[...years].sort().reverse().map(value => new Option(value, value)));
    yearSelect.value = years.has(current) ? current : '';
    yearSelect.dataset.count = String(years.size);
  }
}

/* ---------------------------------------------------------------- Album: stage tracker (P2b)
   Five stages, each shown as a word and a position. The stage is the furthest one the page knows about: recommended, saved, queued,
   downloaded, in library. The buttons beside it are the non-drag path: Save is the album's real Save control and Get the album's real Get. */

function renderPipelineAlbum() {
  const box = $('pipelineStages');
  if (!box) return;
  const album = albumPage.album;
  if (!pipelineWide() || !album) {
    box.hidden = true;
    return;
  }
  if (!pipelineSaved) {
    pipelineLoadSaved().then(() => renderPipelineAlbum());
    return;
  }
  const artist = album.artist;
  const name = album.name;
  const matches = entry => pipelineSameAlbum(entry, artist, name);
  const tracks = albumPage.tracks;
  const owned = tracks ? tracks.every(track => track.owned) : Boolean(album.owned);
  const jobs = pipelineJobs.filter(matches);
  const saved = pipelineSaved.some(matches);
  const recommended = dashboardPickItems.some(matches);
  const downloaded = owned || jobs.some(job => ['importing', 'imported', 'download_complete_waiting_for_folder'].includes(String(job.status || '').toLowerCase()));
  const queued = downloaded || jobs.some(job => acquisitionStatusInfo(job.status).tone !== 'error' && String(job.status || '').toLowerCase() !== 'dismissed');
  const reached = [recommended, saved, queued, downloaded, owned];
  const current = reached.lastIndexOf(true);
  const getControl = $('albumAction').querySelector('.get-album');
  const getState = getControl ? (getControl.disabled ? 'busy' : 'ready') : 'none';
  const signature = JSON.stringify([artist, name, current, saved, owned, getState]);
  box.hidden = false;
  pipelineLabelTracks();
  if (box.dataset.sig === signature) return;
  box.dataset.sig = signature;

  const list = document.createElement('ol');
  list.className = 'pipeline-stage-list';
  list.setAttribute('aria-label', 'Stage of ' + name);
  PIPELINE_STAGES.forEach((stageName, index) => {
    const state = index < current ? 'done' : index === current ? 'current' : 'todo';
    const item = document.createElement('li');
    item.className = 'pipeline-stage is-' + state;
    if (state === 'current') item.setAttribute('aria-current', 'step');
    const label = stageName === 'In library' && tracks && tracks.length ? stageName + ' ' + tracks.filter(track => track.owned).length + '/' + tracks.length : stageName;
    addTextElement(item, 'span', 'pipeline-stage-name', label);
    addTextElement(item, 'span', 'pipeline-stage-word', PIPELINE_STAGE_WORDS[state]);
    addTextElement(item, 'span', 'pipeline-stage-pos', 'Step ' + (index + 1) + ' of ' + PIPELINE_STAGES.length);
    list.append(item);
  });
  const now = current < 0
    ? 'Not started yet.'
    : 'Now: ' + PIPELINE_STAGES[current] + ', step ' + (current + 1) + ' of ' + PIPELINE_STAGES.length + '.';
  const actions = document.createElement('div');
  actions.className = 'pipeline-stage-actions';
  actions.setAttribute('role', 'group');
  actions.setAttribute('aria-label', 'Move ' + name);
  const metadata = {artist, album: name, year: album.year || null, release_group_mbid: album.release_group_mbid || null};
  if (!owned) {
    const save = createSaveButton(artist, name, metadata, 'pipeline_album');
    setSaveButtonState(save, saved, name);
    actions.append(save);
    if (getControl) {
      const get = document.createElement('button');
      get.type = 'button';
      get.className = 'pipeline-stage-get';
      const partial = tracks && tracks.some(track => track.owned);
      get.textContent = getState === 'busy' ? 'Requesting…' : partial ? 'Queue the rest' : 'Get the album';
      get.disabled = getState === 'busy';
      get.setAttribute('aria-label', getState === 'busy' ? 'Requesting ' + name : 'Get ' + name);
      get.addEventListener('click', () => getControl.click());
      actions.append(get);
    }
    // Not for me: the app's own feedback action, with its undo, as on the cards.
    const dismiss = document.createElement('button');
    dismiss.type = 'button';
    dismiss.className = 'pipeline-stage-dismiss';
    dismiss.textContent = 'Not for me';
    dismiss.setAttribute('aria-label', 'Not for me: ' + name);
    dismiss.addEventListener('click', () => sendFeedback('dismiss', artist, name, metadata, 'pipeline_album', null));
    actions.append(dismiss);
  }
  const line = document.createElement('p');
  line.className = 'pipeline-stage-now';
  line.textContent = now;
  box.replaceChildren(list, line, actions);
}

// The tracklist rows read as the mockup's rows. An owned track gets an OWNED tag; a missing track keeps its own Get button, which the
// layout styles as the GET tag.
function pipelineLabelTracks() {
  for (const row of document.querySelectorAll('#albumTracks > li.track')) {
    if (row.querySelector(':scope > .pipeline-tag')) continue;
    const control = row.querySelector('.get-track');
    if (control) continue;
    const tag = document.createElement('span');
    tag.className = 'pipeline-tag is-owned';
    tag.textContent = 'Owned';
    row.append(tag);
  }
}

/* ---------------------------------------------------------------- Artist: lanes and drop to Queued (P2b)
   The three artist sections read as lanes: In library, Missing (each row draggable to Queued), Similar artists. The Queued strip accepts a
   drop and clicks the dropped row's own Get; the row's Get button is the keyboard and touch path to the same request. */

function renderPipelineArtist() {
  const strip = $('pipelineArtistQueue');
  if (!strip) return;
  const wide = pipelineWide();
  for (const [id, [normal, lane]] of Object.entries(PIPELINE_ARTIST_HEADINGS)) {
    const heading = $(id);
    if (!heading) continue;
    if (!heading.dataset.defaultText) heading.dataset.defaultText = normal;
    heading.textContent = wide ? lane : heading.dataset.defaultText;
  }
  const rows = Array.from($('artistMissingAlbums').children);
  for (const row of rows) {
    if (wide) {
      row.draggable = true;
      row.classList.add('pipeline-card');
      if (!row.dataset.pipeDrag) {
        row.dataset.pipeDrag = '1';
        row.addEventListener('dragstart', event => {
          pipelineDragged = row;
          row.classList.add('is-dragging');
          event.dataTransfer.effectAllowed = 'copy';
          event.dataTransfer.setData('text/plain', row.textContent.trim().slice(0, 120));
        });
        row.addEventListener('dragend', () => {
          row.classList.remove('is-dragging');
          pipelineDragged = null;
          document.querySelectorAll('.pipeline-drop.over').forEach(el => el.classList.remove('over'));
        });
      }
    } else {
      row.removeAttribute('draggable');
      row.classList.remove('pipeline-card');
    }
  }
  strip.hidden = !(wide && rows.length);
  // The mockup's header line: owned of the known albums (owned plus the missing list, which the API caps at 50).
  const owned = $('artistOwnedAlbums').children.length;
  if (wide && $('artistDetailStatus') && owned + rows.length) {
    $('artistDetailStatus').textContent = owned + ' of ' + (owned + rows.length) + ' known albums in your library';
  }
}

function pipelineWireArtistStrip() {
  const strip = $('pipelineArtistQueue');
  if (!strip) return;
  strip.addEventListener('dragover', event => {
    if (!pipelineDragged) return;
    event.preventDefault();
    strip.classList.add('over');
  });
  strip.addEventListener('dragleave', event => {
    if (!strip.contains(event.relatedTarget)) strip.classList.remove('over');
  });
  strip.addEventListener('drop', event => {
    if (!pipelineDragged) return;
    event.preventDefault();
    strip.classList.remove('over');
    const get = pipelineDragged.querySelector('.get-album');
    const label = pipelineDragged.querySelector('.album-row-name');
    const album = label ? label.textContent : 'this album';
    if (!get || get.disabled) {
      pipelineSay(get ? album + ' is already being requested.' : album + ' has no Get to run.', 'pipelineArtistStatus');
      return;
    }
    pipelineSay('Requesting ' + album + '. It moves to Queued when the server confirms.', 'pipelineArtistStatus');
    pipelineFollowGet(get, album, 'pipelineArtistStatus');
    get.click();
  });
}

/* ---------------------------------------------------------------- refresh and wiring */

// Everything the layout shows, brought up to date. Called on load, on a layout change and on a width change across 900px.
function pipelineRefresh() {
  renderPipelineBoard();
  renderPipelineLanes();
  renderPipelineAlbum();
  renderPipelineArtist();
}

function pipelineWire() {
  for (const id of ['pipelineFilterGenre', 'pipelineFilterYear']) if ($(id)) $(id).addEventListener('change', pipelineApplyLaneFilters);
  const board = $('pipelineBoard');
  pipelineWireArtistStrip();
  // The layout is chosen in Settings without a reload, so the layout's parts are built (or cleared) when it changes.
  new MutationObserver(pipelineRefresh).observe(document.documentElement, {attributes: true, attributeFilter: ['data-layout']});
  window.matchMedia('(min-width: 901px)').addEventListener('change', pipelineRefresh);
  // The album's own Get changes state in place; the stage's Get follows it.
  if ($('albumAction')) new MutationObserver(() => renderPipelineAlbum()).observe($('albumAction'), {attributes: true, childList: true, subtree: true, attributeFilter: ['class', 'disabled']});
  pipelineRefresh();
}

document.addEventListener('DOMContentLoaded', pipelineWire);
