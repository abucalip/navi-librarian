/* Pipeline Board layout behaviour (D-024, docs/BRUT_ROUND3_PLAN.md, phase P2). Loaded after static/app.js; app.js calls renderPipelineBoard()
   through zineHook(). It returns at once unless <html data-layout="pipeline"> is set and the window is 901px or wider, and #pipelineBoard is
   hidden by default and shown only in that case, so no other theme changes. The board builds its cards with the app's own builders
   (buildShelfCard, buildSavedCard) so Get, Save and their states have one source of truth. A drop never calls the network itself: Queued
   clicks the card's real Get button (searchAlbum) and Saved clicks its real Save button. The card moves only when the acquisition list
   reports it, because the board is redrawn from that list. Destructive actions (Not for me, Dismiss) have no drop target. */

const PIPELINE_COLUMNS = [
  {key: 'recommended', title: 'Recommended'},
  {key: 'saved', title: 'Saved'},
  {key: 'queued', title: 'Queued'},
  {key: 'downloading', title: 'Downloading'},
  {key: 'library', title: 'In library'}
];
// Columns a card can be dropped on. Not for me has no drop target: it stays a button.
const PIPELINE_DROP = new Set(['queued', 'saved']);

let pipelineJobs = [];
let pipelineSaved = null;      // entries from /api/discovery/for_me
let pipelineSavedAt = 0;       // when they were read; the list is read again after a minute
let pipelineSavedLoading = null;
let pipelineDragged = null;    // the card being dragged, set on dragstart and cleared on dragend

function pipelineOn() {
  return document.documentElement.dataset.layout === 'pipeline';
}

function pipelineActive() {
  return Boolean($('pipelineBoard')) && pipelineOn() && !isMobileLayout() && window.matchMedia('(min-width: 901px)').matches;
}

function pipelineSay(text) {
  const toast = $('pipelineToast');
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

// A pick as a shelf item, so the shelf card (and its real Get and Save) is built by the existing builder.
function pipelinePickAsShelf(item) {
  return {
    ...item,
    name: item.album || item.title || item.name || 'Untitled album',
    artist: item.artist || item.album_artist || 'Unknown artist',
    owned: false
  };
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
  badge.textContent = String(count);
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

// The card's own controls, reached by a pointer drop or by the Move to menu. Both paths end in the same click.
function pipelineAct(card, target) {
  const album = card.dataset.album || 'this album';
  if (target === 'queued') {
    const get = card.querySelector('.get-album');
    if (!get || get.disabled) {
      pipelineSay(get ? album + ' is already being requested.' : album + ' has no Get to run: it is already in your library.');
      return;
    }
    pipelineSay('Requesting ' + album + '. It moves to Queued when the server confirms.');
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

// Move to…: the non-drag, non-chord equivalent of a drop. Opens a short list of the real actions this card offers.
function pipelineMoveMenu(card) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'pipeline-move';
  button.textContent = 'Move to…';
  button.setAttribute('aria-expanded', 'false');
  button.addEventListener('click', () => {
    const open = card.querySelector('.pipeline-menu');
    if (open) {
      open.remove();
      button.setAttribute('aria-expanded', 'false');
      return;
    }
    const menu = document.createElement('div');
    menu.className = 'pipeline-menu';
    menu.setAttribute('role', 'group');
    menu.setAttribute('aria-label', 'Move ' + (card.dataset.album || 'this album'));
    const options = [];
    if (card.querySelector('.get-album')) options.push(['Queued: Get it', 'queued']);
    if (card.querySelector('.save-album')) options.push(['Saved: Save it', 'saved']);
    if (!options.length) options.push(['Nothing to move to', null]);
    for (const [label, target] of options) {
      const option = document.createElement('button');
      option.type = 'button';
      option.textContent = label;
      if (target) option.addEventListener('click', () => {
        menu.remove();
        button.setAttribute('aria-expanded', 'false');
        pipelineAct(card, target);
      });
      else option.disabled = true;
      menu.append(option);
    }
    button.setAttribute('aria-expanded', 'true');
    card.append(menu);
    menu.querySelector('button').focus();
  });
  return button;
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
    document.querySelectorAll('.pipeline-col.over').forEach(col => col.classList.remove('over'));
  });
}

// One card for a request: the title and state in words, a bar and percentage while it downloads. Retry and Dismiss stay on Acquisitions.
function pipelineJobCard(job) {
  const info = acquisitionStatusInfo(job.status);
  const card = document.createElement('article');
  card.className = 'card pipeline-job';
  card.dataset.album = job.album || '';
  const name = document.createElement('b');
  name.textContent = job.album || 'Untitled album';
  const who = document.createElement('small');
  who.textContent = [job.artist, info.label].filter(Boolean).join(' · ');
  card.append(name, who);
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
    text.textContent = percent + '% downloaded';
    card.append(bar, text);
  }
  return card;
}

// Which board column a request belongs in. Imported requests are in the library column, from the recent shelf.
function pipelineJobColumn(job) {
  const status = String(job.status || '').toLowerCase();
  if (status === 'imported') return null;
  if (acquisitionStatusInfo(job.status).tone === 'error') return 'downloading';
  if (['downloading', 'download_complete_waiting_for_folder', 'importing', 'monitoring'].includes(status)) return 'downloading';
  return 'queued';
}

function renderPipelineBoard(jobs) {
  if (Array.isArray(jobs)) pipelineJobs = jobs;
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
    pipelinePlaceCard(buildShelfCard(shelf, true), lists.get('recommended'), shelf.name);
  }
  // Saved: the Saved page's list, with the existing Saved card.
  // Queued and Downloading: from the acquisition list already loaded.
  for (const job of pipelineJobs) {
    const column = pipelineJobColumn(job);
    if (column) lists.get(column).append(pipelineJobCard(job));
  }
  // In library: the recent library shelf, already loaded by the dashboard.
  for (const item of (shelfItems.Recent || []).slice(0, 12)) {
    pipelinePlaceCard(buildShelfCard({...item, owned: true}, false), lists.get('library'), item.name);
  }

  pipelineLoadSaved().then(entries => {
    if (!pipelineActive()) return;
    const list = lists.get('saved');
    if (!list) return;
    list.replaceChildren();
    for (const entry of entries.slice(0, 12)) pipelinePlaceCard(buildSavedCard(entry), list, entry.album);
    finishPipelineColumns(cols, lists);
  });
  // The Saved column waits for its list, so it shows no empty message until the answer arrives.
  finishPipelineColumns(cols, lists, new Set(['saved']));
}

// Every card gets a drag handle and the Move to menu; the card itself stays the element the existing builder made.
function pipelinePlaceCard(card, list, album) {
  card.dataset.album = album || '';
  pipelineMakeDraggable(card);
  card.append(pipelineMoveMenu(card));
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
  const names = {recommended: 'No picks yet.', saved: 'Nothing saved yet.', queued: 'Nothing queued.', downloading: 'Nothing downloading.', library: 'Nothing imported recently.'};
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

function pipelineWire() {
  const board = $('pipelineBoard');
  if (!board) return;
  // Enter and Escape close an open Move to menu; focus returns to its button.
  board.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const menu = event.target.closest && event.target.closest('.pipeline-menu');
    if (!menu) return;
    const owner = menu.closest('.pipeline-card');
    const move = owner && owner.querySelector('.pipeline-move');
    menu.remove();
    if (move) {
      move.setAttribute('aria-expanded', 'false');
      move.focus();
    }
  });
}

document.addEventListener('DOMContentLoaded', pipelineWire);
