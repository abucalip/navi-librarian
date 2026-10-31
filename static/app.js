const $ = id => document.getElementById(id);

// The phone layout (the same 620px breakpoint as the stylesheet). Phone-only behaviour (the search
// toggle, the swipeable picks, album cards in place of ranked rows) is chosen from this, and a
// change of layout re-renders what was built for the other one (see the end of this file).
const mobileLayoutQuery = window.matchMedia('(max-width: 620px)');
const isMobileLayout = () => mobileLayoutQuery.matches;

function isAlbumRecommendation(item) {
  if (!item || typeof item !== 'object') return false;
  const title = String(item.album || item.title || item.name || '').trim();
  if (!title) return false;
  const primary = String(item.primary_type || item['primary-type'] || item.album_type || item.release_type || '').trim().toLowerCase();
  if (primary && !['album', 'full length album'].includes(primary)) return false;
  const secondary = item.secondary_types || item['secondary-types'] || item.secondary_type || [];
  const types = (Array.isArray(secondary) ? secondary : String(secondary).split(/[,;/|]/))
    .map(value => String(value).toLowerCase().replace(/[^a-z]+/g, ' ').trim());
  if (types.some(value => ['compilation', 'soundtrack', 'live', 'remix', 'dj mix', 'mixtape', 'ep', 'single', 'karaoke', 'tribute'].includes(value))) return false;
  const normalized = title.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  return ![/\bcompilations?\b/, /\bremixes?\b/, /\bremixed\b/, /\bdj\s*mix(?:es)?\b/, /\bmixtapes?\b/, /\bsoundtracks?\b/, /\bkaraoke\b/, /\btribute\b/, /\bgreatest hits\b/, /\bbest of\b/, /\banthology\b/, /\bsamplers?\b/, /\blive\b/]
    .some(pattern => pattern.test(normalized));
}

let activePage = 'dashboard';
// Destinations behind the phone bottom bar's More control (under 620px); see index.html.
const NAV_MORE_PAGES = ['newReleases', 'classics', 'artistDeepDive'];

function showPage(name) {
  activePage = name;
  document.querySelectorAll('.page').forEach(el =>
    el.classList.toggle('hidden', el.id !== name));
  document.querySelectorAll('nav button[data-page]').forEach(el =>
    el.classList.toggle('active', el.dataset.page === name));
  // Settings lives in the header menu, so the gear toggle carries the "you are here" cue.
  $('appMenuButton').classList.toggle('is-current', name === 'settings' || name === 'saved' || name === 'library');
  // The phone bar's More control carries the cue when one of its two destinations is current.
  $('navMoreButton').classList.toggle('is-current', NAV_MORE_PAGES.includes(name));
  moveNavIndicator();
  syncNavAria();
  syncLocationHash();
}

// Slide the navigation indicator to the active item using translateY only. The indicator is a
// fixed-height bar, so only the offset changes; animating top would force layout on every
// navigation. Rows inside .nav-list share one width, so no width term is needed.
function moveNavIndicator() {
  const indicator = document.querySelector('.nav-indicator');
  if (!indicator) return;
  const active = document.querySelector('.nav-list button.active');
  if (!active) { indicator.hidden = true; return; }
  indicator.hidden = false;
  indicator.style.transform = 'translateY(' + active.offsetTop + 'px)';
}

// The reference component ships no aria-selected or role=tablist, so this is added here:
// the sidebar is a navigation landmark, and the current page is exposed as aria-current.
function syncNavAria() {
  document.querySelectorAll('nav button[data-page], .header-menu button[data-page]').forEach(el => {
    if (el.dataset.page === activePage) el.setAttribute('aria-current', 'page');
    else el.removeAttribute('aria-current');
  });
}

const initializedPages = new Set(['dashboard']);

function initializePage(name) {
  if (initializedPages.has(name)) return;
  initializedPages.add(name);
  if (name === 'recommendations') $('loadRecommendations').click();
  else if (name === 'newReleases') loadDiscovery('new_releases');
  else if (name === 'personalDiscoveries') loadDiscovery('personal');
  else if (name === 'lensLists') loadLensList(activeLens);
  else if (name === 'classics') loadDiscovery('classics', {rotate: true});
  else if (name === 'artistDeepDive') loadDiscovery('artist_deep_dive', {rotate: true});
  else if (name === 'settings') { loadNavidromeSettings(); loadSlskdSettings(); loadLastfmSettings(); loadListenbrainzSettings(); loadDiscogsSettings(); }
}

// One navigation path for the rail and the header menu, so Settings in the menu still runs
// initializePage('settings') and loads its panels rather than opening an empty page.
function navigateTo(name) {
  showPage(name);
  initializePage(name);
  // Saved is read on every visit: saves made on other pages since the last visit must appear.
  if (name === 'saved') loadSaved();
  // The library restarts from the first page on every visit, so new artists appear.
  if (name === 'library') { libraryReset(); loadLibrary({reset: true}); }
  // The stream is closed on leaving Acquisitions, so it must restart on every visit, not only
  // the first one that initializePage handles; startAcquisitionStream is a no-op while open.
  if (name === 'acquisitions') startAcquisitionStream();
  else stopAcquisitionStream();
  // Grab the radio (static/radio.js): the log changes while the owner listens, so every visit reloads.
  if (name === 'radio') loadRadio();
}

document.querySelectorAll('nav button[data-page], .header-menu button[data-page]').forEach(button =>
  button.addEventListener('click', () => {
    setAppMenuOpen(false, {focusToggle: true});
    // A choice from the phone More panel closes it and returns focus to More, since the
    // panel is hidden once the choice is made.
    setNavMoreOpen(false, {focusToggle: navMorePanel.contains(button)});
    navigateTo(button.dataset.page);
  }));

// Header gear menu: a disclosure (aria-expanded and aria-controls) over a plain group of
// buttons, not role="menu". Pointer dismissal is handled by the document click listener;
// focus leaving the container closes it only when the new focus target is a real element
// outside it, because Safari does not focus buttons on click and would otherwise close the
// panel on mousedown and swallow the item click.
const appMenuButton = $('appMenuButton');
const appMenu = $('appMenu');
const appMenuContainer = appMenuButton.parentElement;
const appMenuItems = () => Array.from(appMenu.querySelectorAll('button'));

function setAppMenuOpen(open, {focusToggle = false, focusFirst = false} = {}) {
  appMenu.hidden = !open;
  appMenuButton.setAttribute('aria-expanded', String(open));
  if (open && focusFirst) appMenuItems()[0].focus();
  if (!open && focusToggle) appMenuButton.focus();
}

appMenuButton.addEventListener('click', () => setAppMenuOpen(appMenu.hidden));
appMenuButton.addEventListener('keydown', event => {
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    setAppMenuOpen(true, {focusFirst: true});
  }
});
appMenu.addEventListener('keydown', event => {
  const items = appMenuItems();
  const index = items.indexOf(document.activeElement);
  let target = null;
  if (event.key === 'ArrowDown') target = items[(index + 1) % items.length];
  else if (event.key === 'ArrowUp') target = items[(index - 1 + items.length) % items.length];
  else if (event.key === 'Home') target = items[0];
  else if (event.key === 'End') target = items[items.length - 1];
  if (target) { event.preventDefault(); target.focus(); }
});
appMenuContainer.addEventListener('focusout', event => {
  const next = event.relatedTarget;
  if (next && !appMenuContainer.contains(next)) setAppMenuOpen(false);
});
// Phone bottom bar More control: a disclosure over two destinations, the same pattern as the
// header menu, with Escape added because it is the only way out of the panel from the keyboard.
const navMoreButton = $('navMoreButton');
const navMorePanel = $('navMorePanel');
const navMoreContainer = navMoreButton.parentElement;
const navMoreItems = () => Array.from(navMorePanel.querySelectorAll('button'));

function setNavMoreOpen(open, {focusToggle = false, focusFirst = false} = {}) {
  navMorePanel.hidden = !open;
  navMoreButton.setAttribute('aria-expanded', String(open));
  if (open && focusFirst) navMoreItems()[0].focus();
  if (!open && focusToggle) navMoreButton.focus();
}

navMoreButton.addEventListener('click', () => setNavMoreOpen(navMorePanel.hidden));
navMoreButton.addEventListener('keydown', event => {
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    setNavMoreOpen(true, {focusFirst: true});
  } else if (event.key === 'Escape' && !navMorePanel.hidden) {
    event.preventDefault();
    setNavMoreOpen(false);
  }
});
navMorePanel.addEventListener('keydown', event => {
  const items = navMoreItems();
  const index = items.indexOf(document.activeElement);
  let target = null;
  if (event.key === 'ArrowDown') target = items[(index + 1) % items.length];
  else if (event.key === 'ArrowUp') target = items[(index - 1 + items.length) % items.length];
  else if (event.key === 'Home') target = items[0];
  else if (event.key === 'End') target = items[items.length - 1];
  else if (event.key === 'Escape') { event.preventDefault(); setNavMoreOpen(false, {focusToggle: true}); return; }
  if (target) { event.preventDefault(); target.focus(); }
});
navMoreContainer.addEventListener('focusout', event => {
  const next = event.relatedTarget;
  if (!navMorePanel.hidden && next && !navMoreContainer.contains(next)) setNavMoreOpen(false);
});

document.addEventListener('click', event => {
  if (!appMenu.hidden && !(event.target.closest && event.target.closest('.header-menu'))) setAppMenuOpen(false);
  if (!navMorePanel.hidden && !(event.target.closest && event.target.closest('nav'))) setNavMoreOpen(false);
});

document.querySelectorAll('button[data-go]').forEach(button =>
  button.addEventListener('click', () => navigateTo(button.dataset.go)));

// Place the indicator once layout is settled, and keep it aligned when the rail is
// resized. offsetTop is only meaningful after layout, so the first move waits a frame.
syncNavAria();
requestAnimationFrame(moveNavIndicator);
window.addEventListener('resize', moveNavIndicator);
// Web fonts change row metrics after first paint; re-align once they are ready.
if (document.fonts && document.fonts.ready) document.fonts.ready.then(moveNavIndicator);

async function requestJSON(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

async function checkConnection() {
  const el = $('connection');
  el.textContent = 'Checking Navidrome…';
  setStatusState(el, 'loading');
  try {
    const data = await requestJSON('/api/health');
    el.textContent = 'Connected to Navidrome';
    setStatusState(el, 'success');
  } catch (error) {
    el.textContent = error.message;
    setStatusState(el, 'error');
  }
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function formatDownloadBytes(value) {
  if (value === null || value === undefined || value === '') return null;
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return null;
  if (bytes < 1024) return Math.round(bytes) + ' B';
  const units = ['KB', 'MB', 'GB', 'TB'];
  let amount = bytes / 1024;
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) {
    amount /= 1024;
    unit += 1;
  }
  return amount.toFixed(amount >= 100 ? 0 : 1) + ' ' + units[unit];
}

/* --------------------------------------------------------------- acquisition status rows

   Acquisitions are status records, so each one is a row, not an artwork card (DESIGN_SYSTEM.md 9.5).
   The server's job statuses are the vocabulary and are not renamed. This table gives each one a
   glyph and a human label. The glyph and label carry the state; the tone only adds emphasis, so
   no state is carried by colour alone. A status missing from the table still renders with a bullet
   and its own name, never a blank cell. */
const ACQUISITION_STATUS_TABLE = {
  searching: {glyph: '…', label: 'Searching sources', tone: 'active'},
  requested: {glyph: '›', label: 'Requested', tone: 'active'},
  queued: {glyph: '›', label: 'Queued', tone: 'active'},
  queued_unconfirmed: {glyph: '?', label: 'Queued, not yet confirmed', tone: 'caution'},
  downloading: {glyph: '↓', label: 'Downloading', tone: 'active'},
  download_complete_waiting_for_folder: {glyph: '↓', label: 'Download complete, waiting for folder', tone: 'active'},
  importing: {glyph: '›', label: 'Importing', tone: 'active'},
  imported: {glyph: '✓', label: 'Imported', tone: 'ok'},
  monitoring: {glyph: '…', label: 'Monitoring download', tone: 'active'},
  recovery_started: {glyph: '…', label: 'Recovery started', tone: 'active'},
  queue_uncertain: {glyph: '?', label: 'Queue status uncertain', tone: 'caution'},
  review_required: {glyph: '?', label: 'Needs review', tone: 'caution'},
  source_switching: {glyph: '…', label: 'Switching source', tone: 'active'},
  skip_requested: {glyph: '›', label: 'Skip requested', tone: 'active'},
  retry_requested: {glyph: '›', label: 'Retry requested', tone: 'active'},
  dismissed: {glyph: '—', label: 'Dismissed', tone: 'muted'},
  no_matches: {glyph: '!', label: 'No matches found', tone: 'error'},
  queue_failed: {glyph: '!', label: 'Could not queue', tone: 'error'},
  settings_required: {glyph: '!', label: 'Settings required', tone: 'error'},
  slskd_error: {glyph: '!', label: 'Soulseek connection error', tone: 'error'},
  download_failed: {glyph: '!', label: 'Download failed', tone: 'error'},
  download_complete_move_failed: {glyph: '!', label: 'Could not move download', tone: 'error'},
  source_switch_failed: {glyph: '!', label: 'Source switch failed', tone: 'error'},
  monitor_error: {glyph: '!', label: 'Monitor error', tone: 'error'},
  monitor_timeout: {glyph: '!', label: 'Monitor timed out', tone: 'error'},
  monitor_recovery_failed: {glyph: '!', label: 'Recovery failed', tone: 'error'},
  recovery_unavailable: {glyph: '!', label: 'Recovery unavailable', tone: 'error'},
  error: {glyph: '!', label: 'Error', tone: 'error'},
  failed: {glyph: '!', label: 'Failed', tone: 'error'},
};

function acquisitionStatusInfo(status) {
  const key = String(status || '').toLowerCase();
  if (Object.prototype.hasOwnProperty.call(ACQUISITION_STATUS_TABLE, key)) return ACQUISITION_STATUS_TABLE[key];
  const name = key ? key.replaceAll('_', ' ') : 'unknown status';
  return {glyph: '•', label: name.charAt(0).toUpperCase() + name.slice(1), tone: 'muted'};
}

// Skeleton rows are shown only while the list is empty, so a refresh never blanks known rows.
function showAcquisitionSkeleton() {
  const target = $('acquisitionCards');
  if (target.children.length) return;
  const rows = [0, 1, 2].map(() => {
    const row = document.createElement('div');
    row.className = 'acq-row is-skeleton';
    row.setAttribute('aria-hidden', 'true');
    const art = document.createElement('span');
    art.className = 'skeleton-art';
    const main = document.createElement('div');
    main.className = 'acq-main';
    const title = document.createElement('span');
    title.className = 'skeleton-main';
    const meta = document.createElement('span');
    meta.className = 'skeleton-meta';
    main.append(title, meta);
    const state = document.createElement('div');
    state.className = 'acq-state';
    const stateLine = document.createElement('span');
    stateLine.className = 'skeleton-meta';
    state.append(stateLine);
    row.append(art, main, state);
    return row;
  });
  target.replaceChildren(...rows);
}

// The stream resends the whole list every second, and the server orders it by last update, so an
// active download kept moving to the top. Rows are ordered by when they were requested instead,
// which never changes, and render in place: a row whose data is unchanged is kept as the same
// element (so its artwork does not reload and focus is not lost), and a changed row takes over
// the artwork element of the row it replaces.
function acquisitionRowKey(job) {
  return [job.artist || '', job.album || ''].join('::').toLocaleLowerCase();
}

function orderAcquisitions(jobs) {
  return jobs.map((job, index) => ({job, index})).sort((a, b) =>
    (Number(b.job.created_at) || 0) - (Number(a.job.created_at) || 0) ||
    acquisitionRowKey(a.job).localeCompare(acquisitionRowKey(b.job)) ||
    a.index - b.index
  ).map(entry => entry.job);
}

function acquisitionRowSignature(job) {
  const details = job.details || {};
  // The skip-source button counts down from the clock, so a stalled row changes every second.
  const tick = job.status === 'downloading' && details.stall_detected_at ? Math.floor(Date.now() / 1000) : 0;
  return JSON.stringify([job, tick]);
}

function renderAcquisitions(data, targetOverride = null, statusOverride = null, onlyIdentity = null) {
  const target = targetOverride || $('acquisitionCards');
  const status = statusOverride || $('acquisitionsStatus');
  try {
    const existingRows = new Map();
    for (const child of Array.from(target.children)) {
      if (child.dataset && child.dataset.acqKey) existingRows.set(child.dataset.acqKey, child);
      else child.remove();
    }
    const orderedRows = [];
    const jobs = orderAcquisitions(Array.isArray(data.acquisitions) ? data.acquisitions : []);
    updateActiveDownloadBadge(data);
    const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-acquisitions') || '[]'));
    status.textContent = jobs.length
      ? pluralize(jobs.length, 'acquisition record', 'acquisition records') + '.'
      : 'No acquisition records yet. Requests you make from a discovery page appear here.';
    // renderAcquisitions used to set only the text, so the element kept the is-loading class
    // applied by loadAcquisitions and an empty list rendered with the loading ellipsis: the
    // message said "no records" while the glyph said "still working". The kind now travels
    // with the message. A detached override element is excluded because a caller rendering a
    // single identity owns its own node.
    if (status === $('acquisitionsStatus')) {
      setStatusState(status, jobs.length ? 'progress' : 'empty');
    }
    for (const job of jobs) {
      if (onlyIdentity && [job.artist || '', job.album || ''].join('::').toLocaleLowerCase() !== onlyIdentity) continue;
      const dismissalKey = acquisitionRowKey(job);
      if (job.status === 'imported' && dismissed.has(dismissalKey)) continue;
      const signature = acquisitionRowSignature(job);
      const existing = existingRows.get(dismissalKey);
      if (existing && existing.dataset.sig === signature) {
        orderedRows.push(existing);
        existingRows.delete(dismissalKey);
        continue;
      }
      const details = job.details || {};
      const metadata = details.metadata || {};
      const info = acquisitionStatusInfo(job.status);
      const artist = job.artist || 'Unknown artist';
      // A song's row is named after the song; its album is the one it belongs to.
      const isSong = details.kind === 'track';
      const album = (isSong ? details.album_name : job.album) || 'Unknown album';
      const row = document.createElement('article');
      row.className = 'acq-row';
      row.dataset.status = String(job.status || 'unknown');
      makeAlbumCardInteractive(row, artist, album, details, true);
      applyAlbumYear(row, metadata.year || metadata.release_year || metadata.first_release_year || details.year || job.year);
      attachArtwork(row, artist, album);

      const main = document.createElement('div');
      main.className = 'acq-main';
      row.append(main);
      if (isSong) addTextElement(main, 'h3', '', details.track_title || job.album || 'Unknown song');
      else linkAlbumName(addTextElement(main, 'h3', '', ''), artist, album, details);
      ensureAlbumYearBadge(row);
      linkArtistName(addTextElement(main, 'p', 'acq-artist', ''), artist);
      if (isSong) linkAlbumName(addTextElement(main, 'p', 'acq-artist', 'Song on '), artist, album, details);
      const qualityLabels = {
        mp3_320: 'MP3 320 kbps', mp3_193_319: 'MP3 193–319 kbps',
        mp3_192: 'MP3 192 kbps', flac_cd: 'FLAC / CD quality',
        flac_16_44: 'FLAC 16-bit / 44.1 kHz',
      };
      const quality = Array.isArray(details.quality_summary) ? details.quality_summary : [];
      addTextElement(main, 'p', 'acq-profile',
        'Quality profile: ' + (quality.length
          ? quality.map(value => qualityLabels[value] || String(value).replaceAll('_', ' ')).join(' · ')
          : 'Not reported'));
      const lines = [
        details.message,
        details.error,
        details.source_folder ? 'Source: ' + details.source_folder : '',
        details.destination ? 'Destination: ' + details.destination : '',
        details.downloads_path ? 'Downloads: ' + details.downloads_path : '',
        details.source_username ? 'Peer: ' + details.source_username : '',
        details.file_count ? 'Expected files: ' + details.file_count : '',
        details.states ? 'Transfer states: ' + details.states.join(', ') : '',
        details.transfer_states ? 'Transfer states: ' + details.transfer_states.join(', ') : '',
        details.expected_folder ? 'Expected folder: ' + details.expected_folder : '',
        details.matched_transfer_records !== undefined ? 'Matched transfer records: ' + details.matched_transfer_records + ' / ' + (details.expected_files ?? details.file_count ?? '?') : '',
        details.downloads_path_available === false ? 'Completed-download directory is not accessible to the backend.' : '',
        details.completion_evidence ? 'Completion evidence: ' + details.completion_evidence : '',
        job.updated_at ? 'Updated: ' + new Date(job.updated_at * 1000).toLocaleString() : ''
      ].filter(Boolean);
      if (lines.length) {
        const transport = document.createElement('div');
        transport.className = 'acq-transport';
        for (const line of lines) addTextElement(transport, 'p', 'acq-line', line);
        main.append(transport);
      }
      if (details.status && details.status !== job.status) {
        addTextElement(main, 'pre', 'debug', pretty(details));
      }

      // State: the glyph and label are the status; the bar and figures only add detail.
      const state = document.createElement('div');
      state.className = 'acq-state';
      row.append(state);
      const statusLine = document.createElement('p');
      statusLine.className = 'acq-status is-' + info.tone;
      const glyph = document.createElement('span');
      glyph.className = 'acq-glyph';
      glyph.setAttribute('aria-hidden', 'true');
      glyph.textContent = info.glyph;
      const statusLabel = document.createElement('span');
      statusLabel.textContent = info.label;
      statusLine.append(glyph, statusLabel);
      state.append(statusLine);

      const progress = details.live_progress;
      if (['downloading', 'download_complete_waiting_for_folder'].includes(job.status) && progress) {
        const percent = Number.isFinite(Number(progress.percent)) && progress.percent !== null
          ? Math.max(0, Math.min(100, Number(progress.percent))) : null;
        // The bar is scaled with transform only (DESIGN_SYSTEM.md 11). Its value is also written as
        // text, so the percentage never depends on the bar being seen.
        const meter = document.createElement('div');
        meter.className = 'acq-progress';
        meter.setAttribute('role', 'progressbar');
        meter.setAttribute('aria-label', 'Download progress');
        meter.setAttribute('aria-valuemin', '0');
        meter.setAttribute('aria-valuemax', '100');
        const fill = document.createElement('span');
        fill.className = 'acq-progress-fill';
        if (percent === null) {
          meter.setAttribute('aria-valuetext', 'Progress unavailable');
          fill.style.setProperty('--progress', '0');
        } else {
          meter.setAttribute('aria-valuenow', String(Math.round(percent)));
          fill.style.setProperty('--progress', String(percent / 100));
        }
        meter.append(fill);
        const percentText = document.createElement('p');
        percentText.className = 'acq-percent';
        percentText.textContent = percent === null ? 'Progress unavailable' : Math.round(percent) + '% complete';
        const speed = progress.speed_bytes_per_second;
        let speedText = 'Speed unavailable';
        if (Number.isFinite(Number(speed)) && speed !== null) {
          const value = Math.max(0, Number(speed));
          speedText = value >= 1024 * 1024
            ? (value / (1024 * 1024)).toFixed(1) + ' MB/s'
            : value >= 1024 ? (value / 1024).toFixed(0) + ' KB/s' : Math.round(value) + ' B/s';
        }
        const remaining = Number.isFinite(Number(progress.remaining_tracks)) ? Math.max(0, Number(progress.remaining_tracks)) : null;
        const totalTracks = Number.isFinite(Number(progress.total_tracks)) ? Math.max(0, Number(progress.total_tracks)) : null;
        const totalSize = formatDownloadBytes(progress.total_size_bytes);
        const remainingSize = formatDownloadBytes(progress.remaining_size_bytes);
        state.append(meter, percentText);
        addTextElement(state, 'p', 'acq-stat', speedText);
        if (totalSize !== null && remainingSize !== null) {
          addTextElement(state, 'p', 'acq-stat', 'Total ' + totalSize + ' · ' + remainingSize + ' remaining');
        }
        addTextElement(state, 'p', 'acq-stat',
          remaining === null ? 'Tracks remaining unavailable' :
          String(remaining) + ' of ' + (totalTracks === null ? '?' : totalTracks) + ' tracks remaining');
      }

      const actions = document.createElement('div');
      actions.className = 'acq-actions';
      // The row's controls share one icon group, the frame the Get, Save and Not for me controls use.
      const group = document.createElement('div');
      group.className = 'action-group';
      group.setAttribute('role', 'group');
      group.setAttribute('aria-label', 'Actions for ' + (job.album || job.artist || 'acquisition'));
      if (job.status === 'downloading' && details.stall_detected_at && Number(details.fallback_count) > 0) {
        const secondsLeft = Math.max(0, 15 - Math.floor(Date.now() / 1000 - Number(details.stall_detected_at)));
        const stallButton = buildAcquisitionIconButton('skip-forward', 'skip-source-button', secondsLeft > 0
          ? 'Use next source (' + secondsLeft + 's)'
          : 'Switching source…');
        stallButton.disabled = secondsLeft <= 0;
        stallButton.addEventListener('click', async () => {
          stallButton.disabled = true;
          setAcquisitionButtonLabel(stallButton, 'Requesting source switch…');
          try {
            const result = await sendJSON('/api/acquisitions/skip', 'POST', {
              artist: job.artist, album: job.album
            });
            status.textContent = result.message || 'Source switch requested.';
          } catch (error) {
            status.textContent = error.message;
            stallButton.disabled = false;
          }
        });
        group.append(stallButton);
      }
      if (job.status !== 'dismissed') {
        const retryableStatuses = new Set(['no_matches', 'queue_failed', 'settings_required', 'slskd_error']);
        if (retryableStatuses.has(job.status)) {
          const retry = buildAcquisitionIconButton('rotate-cw', 'retry-acquisition', 'Try again');
          retry.addEventListener('click', async () => {
            retry.disabled = true;
            setAcquisitionButtonLabel(retry, 'Retrying…');
            try {
              await sendJSON(isSong ? '/api/acquire/track' : '/api/acquire', 'POST', isSong ? {
                artist: job.artist, album, title: details.track_title,
                track_number: details.track_number || undefined, year: details.year || undefined,
                metadata: details.metadata || {}
              } : {
                artist: job.artist, album: job.album,
                metadata: details.metadata || {}, auto_queue: true
              });
              await loadAcquisitions();
            } catch (error) {
              status.textContent = error.message;
              retry.disabled = false;
              setAcquisitionButtonLabel(retry, 'Try again');
            }
          });
          group.append(retry);
        }
        // Repeated on every row, so the name says which acquisition it dismisses.
        const dismiss = buildAcquisitionIconButton('trash-2', 'dismiss-album',
          'Dismiss ' + (job.album || job.artist || 'acquisition'), 'Dismiss');
        dismiss.addEventListener('click', async () => {
          // A disabled control drops focus, so remember it and hand focus to a neighbour on success
          // (or back to this control on failure) instead of leaving the keyboard user on <body>.
          const hadFocus = document.activeElement === dismiss;
          dismiss.disabled = true;
          try {
            await sendJSON('/api/acquisitions/dismiss', 'POST', {
              artist: job.artist, album: job.album
            });
            const stored = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-acquisitions') || '[]'));
            stored.add(dismissalKey);
            localStorage.setItem('navidrome-dismissed-acquisitions', JSON.stringify([...stored]));
            const neighbour = row.nextElementSibling || row.previousElementSibling;
            row.remove();
            if (hadFocus) {
              const nextControl = neighbour && neighbour.querySelector('button');
              if (nextControl) nextControl.focus();
              else { status.tabIndex = -1; status.focus(); }
            }
            const visibleRows = target.querySelectorAll('.acq-row').length;
            status.textContent = visibleRows
              ? pluralize(visibleRows, 'acquisition record', 'acquisition records') + '.'
              : 'No acquisition records to show.';
            if (status === $('acquisitionsStatus')) {
              setStatusState(status, visibleRows ? 'progress' : 'empty');
            }
          } catch (error) {
            status.textContent = error.message;
            if (status === $('acquisitionsStatus')) setStatusState(status, 'error');
            dismiss.disabled = false;
            if (hadFocus) dismiss.focus();
          }
        });
        group.append(dismiss);
      }
      if (group.childElementCount) actions.append(group);
      if (actions.childElementCount) row.append(actions);
      row.dataset.acqKey = dismissalKey;
      row.dataset.acqArtist = job.artist || '';
      row.dataset.acqAlbum = job.album || '';
      row.dataset.sig = signature;
      const oldArt = existing && existing.querySelector('.card-art');
      const newArt = row.querySelector('.card-art');
      if (oldArt && newArt) newArt.replaceWith(oldArt);
      if (existing) {
        existing.replaceWith(row);
        existingRows.delete(dismissalKey);
      }
      orderedRows.push(row);
    }
    for (const stale of existingRows.values()) stale.remove();
    orderedRows.forEach((node, index) => {
      if (target.children[index] !== node) target.insertBefore(node, target.children[index] || null);
    });
  } catch (error) {
    status.textContent = error.message;
  }
}

// "Dismiss all successful imports": the bar above the rows shows only while an imported row is on the
// page. Each record goes through the same dismiss endpoint as the per-row control; a record that fails
// stays on the page and the status line says how many were left.
function importedAcquisitionRows() {
  return [...$('acquisitionCards').querySelectorAll('.acq-row[data-status="imported"]')];
}

function updateDismissImportedBar() {
  $('acquisitionsToolbar').hidden = importedAcquisitionRows().length === 0;
}

new MutationObserver(updateDismissImportedBar).observe($('acquisitionCards'), {childList: true});

$('dismissImportedAcquisitions').addEventListener('click', async () => {
  const button = $('dismissImportedAcquisitions');
  const status = $('acquisitionsStatus');
  const rows = importedAcquisitionRows();
  if (!rows.length) return;
  button.disabled = true;
  const stored = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-acquisitions') || '[]'));
  let failed = 0;
  for (const row of rows) {
    try {
      await sendJSON('/api/acquisitions/dismiss', 'POST', {artist: row.dataset.acqArtist, album: row.dataset.acqAlbum});
      stored.add(row.dataset.acqKey);
      row.remove();
    } catch (error) {
      failed += 1;
    }
  }
  localStorage.setItem('navidrome-dismissed-acquisitions', JSON.stringify([...stored]));
  const visibleRows = $('acquisitionCards').querySelectorAll('.acq-row').length;
  status.textContent = failed
    ? pluralize(failed, 'import', 'imports') + ' could not be dismissed.'
    : visibleRows ? pluralize(visibleRows, 'acquisition record', 'acquisition records') + '.' : 'No acquisition records to show.';
  setStatusState(status, failed ? 'error' : visibleRows ? 'progress' : 'empty');
  button.disabled = false;
  if (failed) button.focus();
  else { status.tabIndex = -1; status.focus(); }
});

const ACTIVE_DOWNLOAD_STATUSES = new Set([
  'searching', 'requested', 'queued', 'downloading',
  'download_complete_waiting_for_folder', 'importing',
  'queue_uncertain', 'recovery_started', 'monitoring',
]);

function updateActiveDownloadBadge(data) {
  const badge = $('activeDownloadBadge');
  if (!badge) return;
  const jobs = Array.isArray(data && data.acquisitions) ? data.acquisitions : [];
  const count = jobs.filter(job => ACTIVE_DOWNLOAD_STATUSES.has(String(job.status || '').toLowerCase())).length;
  badge.textContent = String(count);
  badge.hidden = count === 0;
  badge.setAttribute('aria-label', count + ' active download' + (count === 1 ? '' : 's'));
}

async function refreshActiveDownloadBadge() {
  try {
    updateActiveDownloadBadge(await requestJSON('/api/acquisitions'));
  } catch (_) {
    // The navigation badge is advisory; do not surface transient polling errors.
  }
}

// Icon-only control for an acquisition row. The name lives in aria-label and title, so a state
// change (a countdown, "Retrying…") is announced and shown as a tooltip instead of resizing the button.
function buildAcquisitionIconButton(icon, className, label, title = label) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = className;
  button.append(spriteIcon(icon));
  button.setAttribute('aria-label', label);
  button.title = title;
  return button;
}

function setAcquisitionButtonLabel(button, label) {
  button.setAttribute('aria-label', label);
  button.title = label;
}

async function loadAcquisitions() {
  $('acquisitionsStatus').textContent = 'Connecting to acquisition status…';
  setStatusState($('acquisitionsStatus'), 'loading');
  showAcquisitionSkeleton();
  try {
    renderAcquisitions(await requestJSON('/api/acquisitions'));
  } catch (error) {
    // Placeholder rows must not outlive a failed load; known rows are kept as they were.
    if ($('acquisitionCards').querySelector('.is-skeleton')) $('acquisitionCards').replaceChildren();
    $('acquisitionsStatus').textContent = error.message;
    setStatusState($('acquisitionsStatus'), 'error');
  }
}

refreshActiveDownloadBadge();
setInterval(refreshActiveDownloadBadge, 30000);

let acquisitionStream = null;
function startAcquisitionStream() {
  if (acquisitionStream) return;
  loadAcquisitions();
  acquisitionStream = new EventSource('/api/acquisitions/stream');
  acquisitionStream.onmessage = event => {
    try {
      renderAcquisitions(JSON.parse(event.data));
    } catch (error) {
      console.error('Could not render acquisition update:', error);
    }
  };
  acquisitionStream.onerror = () => {
    $('acquisitionsStatus').textContent = 'Reconnecting to live download updates…';
    setStatusState($('acquisitionsStatus'), 'loading');
  };
}
function stopAcquisitionStream() {
  if (!acquisitionStream) return;
  acquisitionStream.close();
  acquisitionStream = null;
}

$('refreshAcquisitions').addEventListener('click', loadAcquisitions);

function getRecommendations(data) {
  if (Array.isArray(data)) return data;
  return data.recommendations || [];
}

function getRecommendations(data) {
  if (Array.isArray(data)) return data;
  return Array.isArray(data.recommendations) ? data.recommendations : [];
}

function addTextElement(parent, tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  el.textContent = text ?? '';
  parent.append(el);
  // Some renderers know the year before creating the title. Preserve that
  // year in data-release-year, then attach the badge as soon as the h3 exists.
  if (String(tag).toLowerCase() === 'h3' && parent.dataset && parent.dataset.releaseYear) {
    const year = Number(parent.dataset.releaseYear);
    if (year >= 1900 && year <= 2100 && !el.querySelector('.album-year')) {
      addAlbumYear(el, year, parent.classList.contains('card'));
    }
  }
  return el;
}

const artworkLoaders = new WeakMap();
const bioLoaders = new WeakMap();
const artworkRequests = new Map();
const albumDetailRequests = new Map();
const albumYearRequests = new Map();
const albumYearLoaders = new WeakMap();
const artistBioRequests = new Map();
// Browsers allow about six connections to this server at once, and the server answers some
// metadata lookups slowly (outside services, rate limits). A page that fires one per card filled
// every connection and left artwork requests waiting behind them for many seconds. These lookups
// go through small queues instead, so artwork always has connections free.
function createRequestQueue(limit) {
  const waiting = [];
  let active = 0;
  function drain() {
    while (active < limit && waiting.length) {
      active += 1;
      waiting.shift()();
    }
  }
  return {
    // Runs `task` when a slot is free. A failed task resolves to null. `urgent` goes first.
    run(task, urgent = false) {
      return new Promise(resolve => {
        const start = () => {
          Promise.resolve().then(task).catch(() => null).then(value => {
            active -= 1;
            drain();
            resolve(value);
          });
        };
        if (urgent) waiting.unshift(start); else waiting.push(start);
        drain();
      });
    }
  };
}

const fetchJSONOrNull = url => fetch(url).then(response => response.ok ? response.json() : null);
// Two bios at a time; a bio the person asked for by opening an album goes to the front.
const bioQueue = createRequestQueue(2);
// Album years come from a rate-limited catalog and are cosmetic: one at a time.
const yearQueue = createRequestQueue(1);

function cachedBioRequest(key, artist, urgent = false) {
  if (!artistBioRequests.has(key)) {
    const url = '/api/artist-bio?artist=' + encodeURIComponent(artist);
    artistBioRequests.set(key, bioQueue.run(() => fetchJSONOrNull(url), urgent).then(data => {
      if (data === null) artistBioRequests.delete(key);
      return data;
    }));
  }
  return artistBioRequests.get(key);
}
const albumCardMetadata = new WeakMap();
let activeAlbumModal = null;

function cachedJSONRequest(cache, key, url) {
  if (!cache.has(key)) {
    const request = fetch(url)
      .then(response => response.ok ? response.json() : null)
      .then(data => {
        if (data === null) cache.delete(key);
        return data;
      })
      .catch(() => {
        cache.delete(key);
        return null;
      });
    cache.set(key, request);
  }
  return cache.get(key);
}
const artistBioObserver = 'IntersectionObserver' in window
  ? new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const load = bioLoaders.get(entry.target);
        if (load) load();
        artistBioObserver.unobserve(entry.target);
      }
    }, {rootMargin: '240px'})
  : null;
const albumYearObserver = 'IntersectionObserver' in window
  ? new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const load = albumYearLoaders.get(entry.target);
        if (load) load();
        albumYearObserver.unobserve(entry.target);
      }
    }, {rootMargin: '240px'})
  : null;
const artworkObserver = 'IntersectionObserver' in window
  ? new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const load = artworkLoaders.get(entry.target);
        if (load) load();
        artworkObserver.unobserve(entry.target);
      }
    }, {rootMargin: '400px 600px'})
  : null;

function parseReleaseYear(value) {
  if (value === null || value === undefined || value === '') return null;
  const text = String(value).trim();
  const match = text.match(/^(\d{4})/);
  const year = Number(match ? match[1] : value);
  return Number.isInteger(year) && year >= 1900 && year <= 2100 ? year : null;
}

function firstReleaseYear(...values) {
  for (const value of values) {
    const year = parseReleaseYear(value);
    if (year !== null) return year;
  }
  return null;
}

function makeAlbumCardInteractive(card, artist, album, metadata = {}, fetchYear = true, interactive = true) {
  card.dataset.albumArtist = String(artist || '');
  card.dataset.albumTitle = String(album || '');
  albumCardMetadata.set(card, metadata && typeof metadata === 'object' ? metadata : {});
  if (interactive) {
    // No button role: these articles contain their own Get, Dismiss and Try again buttons, and a
    // button role would hide them from assistive technology (nested interactive controls, found
    // by the Phase 7 audit). Focus and Enter/Space still open the modal through the keydown handler.
    card.setAttribute('tabindex', '0');
    card.setAttribute('aria-label', 'View details for ' + album + ' by ' + artist);
  }
  const nested = metadata && typeof metadata.metadata === 'object' ? metadata.metadata : {};
  const year = firstReleaseYear(
    metadata.year, metadata.release_year, metadata.first_release_year,
    nested.year, nested.release_year, nested.first_release_year
  );
  if (year !== null) applyAlbumYear(card, year);
  else if (fetchYear && artist && album) {
    const cacheKey = String(artist).trim().toLocaleLowerCase() + '::' + String(album).trim().toLocaleLowerCase();
    // The year is looked up only when the card is near the viewport, in groups with the other
    // cards doing the same, and never when the artwork response has already supplied one.
    const loadYear = () => {
      if (card.dataset.releaseYear) return;
      requestAlbumYear(cacheKey, String(artist), String(album), card)
        .then(data => { if (data && data.year) applyAlbumYear(card, data.year); })
        .catch(() => {});
    };
    albumYearLoaders.set(card, loadYear);
    if (albumYearObserver) albumYearObserver.observe(card);
    else loadYear();
  }
}

// Album years are fetched in groups: one request carries up to YEAR_BATCH_SIZE albums, because the
// catalog behind them answers one lookup a second and a page of cards used to send a request each.
const YEAR_BATCH_SIZE = 15;
const YEAR_BATCH_DELAY_MS = 200;
const pendingYears = [];
let yearFlushTimer = null;

function albumYearKey(artist, album) {
  return String(artist).trim().toLocaleLowerCase() + '::' + String(album).trim().toLocaleLowerCase();
}

function requestAlbumYear(cacheKey, artist, album, card) {
  if (!albumYearRequests.has(cacheKey)) {
    albumYearRequests.set(cacheKey, new Promise(resolve => {
      pendingYears.push({cacheKey, artist, album, card, resolve});
      if (pendingYears.length >= YEAR_BATCH_SIZE) flushAlbumYears();
      else if (yearFlushTimer === null) yearFlushTimer = setTimeout(flushAlbumYears, YEAR_BATCH_DELAY_MS);
    }));
  }
  return albumYearRequests.get(cacheKey);
}

function flushAlbumYears() {
  clearTimeout(yearFlushTimer);
  yearFlushTimer = null;
  while (pendingYears.length) {
    const group = pendingYears.splice(0, YEAR_BATCH_SIZE);
    // A card whose artwork already supplied a year needs no lookup. The key is released so a
    // later card for the same album can still ask.
    const live = group.filter(item => {
      if (!item.card.dataset.releaseYear) return true;
      albumYearRequests.delete(item.cacheKey);
      item.resolve(null);
      return false;
    });
    if (!live.length) continue;
    yearQueue.run(() => sendJSON('/api/album-years', 'POST', {
      items: live.map(item => ({artist: item.artist, album: item.album}))
    })).then(data => {
      const years = new Map(((data && data.years) || []).map(entry => [albumYearKey(entry.artist, entry.album), entry.year]));
      for (const item of live) {
        // An album the request did not answer for (a failed catalog call) is released to retry.
        if (!years.has(item.cacheKey)) albumYearRequests.delete(item.cacheKey);
        item.resolve(years.has(item.cacheKey) ? {year: years.get(item.cacheKey)} : null);
      }
    });
  }
}

// Year and listen count beside an album name. In a card they take their own line under the title
// (inside an .album-sub block); in a list row they stay on the title line. The year always comes
// first, whichever of the two is added first.
function albumSubline(title, block) {
  if (!block) return title;
  let sub = title.querySelector(':scope > .album-sub');
  if (!sub) {
    sub = document.createElement('span');
    sub.className = 'album-sub';
    title.append(sub);
  }
  return sub;
}

function addAlbumYear(title, year, block) {
  const host = albumSubline(title, block);
  if (title.querySelector('.album-year')) return;
  const span = document.createElement('span');
  span.className = 'album-year';
  span.textContent = String(year);
  host.insertBefore(span, host.querySelector('.album-listens'));
}

// "12.3K listens" from the Last.fm playcount, else "12.3K listeners"; nothing when neither is known.
function listenCountLabel(item) {
  const plays = Number(item && item.lastfm_playcount);
  if (Number.isFinite(plays) && plays > 0) return compactCount(plays) + ' listens';
  const listeners = Number(item && (item.lastfm_listeners || item.album_listeners));
  if (Number.isFinite(listeners) && listeners > 0) return compactCount(listeners) + ' listeners';
  return '';
}

function addAlbumListens(title, item, block) {
  const label = listenCountLabel(item);
  if (!label || title.querySelector('.album-listens')) return;
  addTextElement(albumSubline(title, block), 'span', 'album-listens', label);
}

function ensureAlbumYearBadge(card) {
  const year = Number(card && card.dataset ? card.dataset.releaseYear : 0);
  // Deep Dive cards put the artist in the heading, so their year belongs on the album line.
  const title = card && card.querySelector(card.dataset.yearTarget === 'supporting' ? '.card-artist' : 'h3');
  if (title && year >= 1900 && year <= 2100 && !title.querySelector('.album-year')) {
    addAlbumYear(title, year, card.classList.contains('card'));
  }
}

function applyAlbumYear(card, value) {
  const year = parseReleaseYear(value);
  if (year === null) return;
  card.dataset.releaseYear = String(year);
  ensureAlbumYearBadge(card);
  const modalYear = $('albumModalYear');
  if (activeAlbumModal && activeAlbumModal.card === card && modalYear) modalYear.textContent = String(year);
}

// Logo-only service links. Each opens a search page at once and is upgraded to the album's own
// page when /api/album-links finds an exact match. Every mark is a local file under
// /static/vendor (AGENTS.md: no runtime third-party assets); see static/vendor/simple-icons/NOTICE.md
// for which marks are the services' own and which are monograms. The service name is the link's
// accessible name and tooltip, since no text is drawn.
const PLATFORM_ICONS = {
  'Apple Music': '/static/vendor/simple-icons/applemusic.svg',
  'Spotify': '/static/vendor/simple-icons/spotify.svg',
  'Bandcamp': '/static/vendor/simple-icons/bandcamp.svg',
  'Deezer': '/static/vendor/simple-icons/deezer.svg',
  'MusicBrainz': '/static/vendor/simple-icons/musicbrainz.svg',
  'Qobuz': '/static/vendor/simple-icons/qobuz.svg',
  'ListenBrainz': '/static/vendor/simple-icons/listenbrainz.svg'
};
const PLATFORM_LINK_KEYS = {
  'Apple Music': 'apple_music', 'Spotify': 'spotify', 'Deezer': 'deezer',
  'MusicBrainz': 'musicbrainz', 'ListenBrainz': 'listenbrainz'
};
const albumLinkRequests = new Map();

function platformSearchLinks(encoded) {
  return {
    'ListenBrainz': 'https://listenbrainz.org/search/?query=' + encoded,
    'Apple Music': 'https://music.apple.com/search?term=' + encoded,
    'Spotify': 'https://open.spotify.com/search/' + encoded,
    'Deezer': 'https://www.deezer.com/search/' + encoded,
    'MusicBrainz': 'https://musicbrainz.org/search?type=release_group&query=' + encoded,
    'Qobuz': 'https://www.qobuz.com/us-en/search/albums/' + encoded,
    'Bandcamp': 'https://bandcamp.com/search?q=' + encoded
  };
}

function setAlbumPlatformLinks(artist, album, mbid) {
  fillPlatformLinks($('albumModalPlatformLinks'), artist, album, mbid,
    ['ListenBrainz', 'Apple Music', 'Spotify', 'Qobuz', 'Bandcamp']);
}

// The album page's links: the same chips as the album panel, for the services it names.
function setAlbumPagePlatformLinks(artist, album, mbid) {
  fillPlatformLinks($('albumPlatformLinks'), artist, album, mbid, ['Apple Music', 'Deezer', 'MusicBrainz', 'Qobuz']);
}

function fillPlatformLinks(nav, artist, album, mbid, services) {
  const stamp = [artist, album, mbid || ''].join('|');
  // The same album again keeps the links already upgraded.
  if (nav.dataset.albumStamp === stamp && nav.childElementCount) return;
  nav.dataset.albumStamp = stamp;
  nav.replaceChildren();
  const searches = platformSearchLinks(encodeURIComponent([artist, album].filter(Boolean).join(' ').trim()));
  const anchors = new Map();
  for (const label of services) {
    const link = document.createElement('a');
    link.href = searches[label];
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.title = 'Search ' + artist + ' ' + album + ' on ' + label;
    link.setAttribute('aria-label', link.title);
    const icon = document.createElement('img');
    icon.src = PLATFORM_ICONS[label];
    icon.alt = '';
    icon.width = 22;
    icon.height = 22;
    link.append(icon);
    nav.append(link);
    anchors.set(label, link);
  }
  if (!artist || !album) return;
  const query = new URLSearchParams({artist, album});
  if (mbid) query.set('mbid', mbid);
  cachedJSONRequest(albumLinkRequests, stamp, '/api/album-links?' + query)
    .then(links => {
      if (!links || nav.dataset.albumStamp !== stamp) return;
      for (const [label, link] of anchors) {
        const url = links[PLATFORM_LINK_KEYS[label]];
        if (!url) continue;
        link.href = url;
        link.title = 'Open ' + album + ' on ' + label;
        link.setAttribute('aria-label', link.title);
      }
    })
    .catch(() => {});
}
// The dialog sets aria-modal, which tells assistive tech the rest of the page is inert, but
// nothing contained Tab, so it walked straight out of the dialog into the sidebar behind it.
// Closing the dialog had the same shape of problem: the close button it had focused is
// hidden by the close, so focus fell back to the top of the document rather than the card
// that opened it. Both are handled here. Focus returns to the originating card rather than
// to document.activeElement because Safari does not focus a tabindex element on click, so
// the active element at open time is not a reliable record of what the user was on.
const ALBUM_MODAL_FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
let albumModalReturnFocus = null;

function albumModalFocusable() {
  const modal = document.querySelector('.album-modal');
  if (!modal) return [];
  // getClientRects rather than offsetParent: the dialog sits in a position:fixed backdrop,
  // for which offsetParent is always null and would filter out every control.
  return [...modal.querySelectorAll(ALBUM_MODAL_FOCUSABLE)]
    .filter(element => element.getClientRects().length > 0);
}

function trapAlbumModalFocus(event) {
  const focusable = albumModalFocusable();
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  // The platform links are rebuilt while the dialog is open, so focus can end up on the
  // backdrop or on <body>. Anything outside the list is pulled back inside rather than
  // being allowed to continue through the page behind the dialog.
  if (!focusable.includes(active)) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
    return;
  }
  if (event.shiftKey && active === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

function closeAlbumModal() {
  $('albumModalBackdrop').hidden = true;
  activeAlbumModal = null;
  const returnTo = albumModalReturnFocus;
  albumModalReturnFocus = null;
  // isConnected guards the case where a lane re-rendered while the dialog was open and the
  // originating card is gone; focusing a detached node would silently do nothing.
  if (returnTo && returnTo.isConnected) returnTo.focus();
}

// The artist bio loads on its own, so a slow or missing bio never delays the tracklist. The
// paragraph stays hidden unless the API returns a bio, and the text is set with textContent.
function loadAlbumModalBio(card, artist) {
  const bio = $('albumModalBio');
  bio.textContent = '';
  bio.hidden = true;
  if (!artist || artist === 'Unknown artist') return;
  const bioKey = artist.trim().toLocaleLowerCase();
  cachedBioRequest(bioKey, artist, true)
    .then(result => {
      if (!result || !result.bio || !activeAlbumModal || activeAlbumModal.card !== card) return;
      bio.textContent = result.bio;
      bio.hidden = false;
    })
    .catch(() => {});
}

async function openAlbumModal(card, returnFocus = card) {
  const artist = card.dataset.albumArtist || 'Unknown artist';
  const album = card.dataset.albumTitle || 'Unknown album';
  const metadata = albumCardMetadata.get(card) || {};
  const backdrop = $('albumModalBackdrop');
  const artwork = $('albumModalArtwork');
  const tracklist = $('albumModalTracklist');
  const get = $('albumModalGet');
  activeAlbumModal = {card, artist, album, metadata};
  albumModalReturnFocus = returnFocus;
  $('albumModalTitle').replaceChildren();
  linkAlbumName($('albumModalTitle'), artist, album, metadata);
  $('albumModalArtist').replaceChildren();
  linkArtistName($('albumModalArtist'), artist);
  $('albumModalYear').textContent = String(firstReleaseYear(metadata.year, metadata.release_year, metadata.first_release_year, card.dataset.releaseYear) || '');
  setAlbumPlatformLinks(artist, album);
  loadAlbumModalBio(card, artist);
  $('albumModalStatus').textContent = 'Loading artwork and tracklist…';
  setStatusState($('albumModalStatus'), 'loading');
  tracklist.replaceChildren();
  artwork.removeAttribute('src');
  artwork.hidden = true; // no broken-image glyph while artwork is pending or absent (Phase 7 audit)
  // Name the artwork with the album it actually shows. The card artwork uses empty alt
  // because each card is already labelled by its own heading; the modal image is a
  // distinct, larger depiction and is the element a user lands on when the dialog opens,
  // so it carries its own description rather than relying on the heading further down
  // the reading order. Cleared again below when no artwork resolves.
  artwork.alt = 'Album artwork for ' + album + ' by ' + artist;
  setGetButtonState(get, 'idle', artist, album);
  get.onclick = () => searchAlbum(artist, album, metadata, get);
  backdrop.hidden = false;
  $('albumModalClose').focus();
  try {
    const query = new URLSearchParams({artist, album});
    const [details, art] = await Promise.all([
      cachedJSONRequest(albumDetailRequests, artist.trim().toLocaleLowerCase() + '::' + album.trim().toLocaleLowerCase(), '/api/album-details?' + query.toString())
        .then(data => data || Promise.reject(new Error('album details unavailable'))),
      // Same key as the card artwork, so a cover the card already fetched is not asked for again.
      cachedJSONRequest(artworkRequests, artist.trim().toLocaleLowerCase() + '::' + album.trim().toLocaleLowerCase(), '/api/artwork?' + query.toString()).catch(() => null)
    ]);
    if (!activeAlbumModal || activeAlbumModal.card !== card) return;
    const artworkUrl = details.artwork_url || (art && art.artwork_url);
    if (artworkUrl) {
      artwork.hidden = false;
      artwork.src = artworkUrl;
    } else {
      // No artwork resolved. An <img> with an alt but no source is announced as a
      // broken image, so this falls back to a decorative empty alt.
      artwork.alt = '';
    }
    const year = details.year || (art && art.year) || metadata.year || metadata.release_year || metadata.first_release_year || card.dataset.releaseYear;
    if (year) {
      $('albumModalYear').textContent = String(year);
      applyAlbumYear(card, year);
    }
    const tracks = Array.isArray(details.tracks) ? details.tracks : [];
    if (tracks.length) {
      tracks.forEach((track, index) => {
        const row = document.createElement('li');
        const number = document.createElement('span');
        number.className = 'track-number';
        number.textContent = String(track.track_number || index + 1).padStart(2, '0');
        const title = document.createElement('span');
        title.textContent = track.title || 'Untitled track';
        const duration = document.createElement('span');
        duration.className = 'track-duration';
        const seconds = Number(track.duration_seconds);
        duration.textContent = Number.isFinite(seconds) && seconds > 0 ? Math.floor(seconds / 60) + ':' + String(Math.floor(seconds % 60)).padStart(2, '0') : '';
        row.append(number, title, duration);
        tracklist.append(row);
      });
      $('albumModalStatus').textContent = tracks.length + ' tracks';
      setStatusState($('albumModalStatus'), 'success');
    } else {
      $('albumModalStatus').textContent = details.message || 'Tracklist unavailable for this release.';
      setStatusState($('albumModalStatus'), 'empty');
    }
  } catch (error) {
    if (activeAlbumModal && activeAlbumModal.card === card) {
      $('albumModalStatus').textContent = 'Could not load tracklist: ' + error.message;
      setStatusState($('albumModalStatus'), 'error');
    }
  }
}

document.addEventListener('click', event => {
  const card = event.target.closest && event.target.closest('.card[data-album-title], .ranked-row[data-album-title], .acq-row[data-album-title]');
  if (!card || event.target.closest('button, a, input, select, textarea')) return;
  openAlbumModal(card);
});
document.addEventListener('keydown', event => {
  const albumModalOpen = !$('albumModalBackdrop').hidden;
  if (event.key === 'Escape' && albumModalOpen) closeAlbumModal();
  else if (event.key === 'Escape' && !appMenu.hidden) setAppMenuOpen(false, {focusToggle: true});
  if (event.key === 'Tab' && albumModalOpen) trapAlbumModalFocus(event);
  if ((event.key === 'Enter' || event.key === ' ') && event.target.matches('.card[data-album-title], .ranked-row[data-album-title], .acq-row[data-album-title]')) {
    event.preventDefault(); openAlbumModal(event.target);
  }
});
$('albumModalClose').addEventListener('click', closeAlbumModal);
// The artwork image is created here rather than written into the markup, so the page never ships
// an <img> without a source. It stays hidden until openAlbumModal sets a URL.
const albumArtworkImage = document.createElement('img');
albumArtworkImage.id = 'albumModalArtwork';
albumArtworkImage.alt = 'Album artwork';
albumArtworkImage.hidden = true;
$('albumModalGet').parentElement.before(albumArtworkImage);
// An artwork URL that fails to load hides the image instead of showing a broken-image glyph.
$('albumModalArtwork').addEventListener('error', () => { $('albumModalArtwork').hidden = true; });
$('albumModalBackdrop').addEventListener('click', event => {
  if (event.target === $('albumModalBackdrop')) closeAlbumModal();
});

// Horizontal scroll tracks — the dashboard carousel and the per-genre rows — are native
// overflow containers. A card inside one is reachable by Tab, because the browser scrolls a
// focused child into view, but the container itself is neither focusable nor named, so the
// row can only be walked one card at a time and cannot be scrolled, paged or jumped as a
// unit. Giving the container a tab stop, an accessible name and arrow/Home/End handling is
// what makes the row itself operable. When no label is passed the container keeps the
// accessible name already in the markup, so a static region stays named in one place.
const trackScrollStep = track => Math.max(250, track.clientWidth * 0.8);
const trackScrollBehavior = () =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';

function scrollTrackBy(track, delta) {
  track.scrollBy({left: delta, behavior: trackScrollBehavior()});
}

function makeScrollTrackFocusable(track, label) {
  track.setAttribute('tabindex', '0');
  track.setAttribute('role', 'group');
  if (label) track.setAttribute('aria-label', label);
  track.addEventListener('keydown', event => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === 'ArrowRight') scrollTrackBy(track, trackScrollStep(track));
    else if (event.key === 'ArrowLeft') scrollTrackBy(track, -trackScrollStep(track));
    else if (event.key === 'Home') track.scrollTo({left: 0, behavior: trackScrollBehavior()});
    else if (event.key === 'End') track.scrollTo({left: track.scrollWidth, behavior: trackScrollBehavior()});
    else return;
    event.preventDefault();
  });
}

/* --------------------------------------------------------------- dashboard tiles

   The picks are a static, unranked strip of artwork tiles (DESIGN_SYSTEM.md 8 and 15, D1). The
   order is random, so no numeral is shown. Each tile has one named button that opens the album
   dialog, laid over the artwork and text, and a separate Get control (9.2) that keeps its own
   state machine. The strip is a native horizontal scroller with arrow, Home and End handling. */
function buildDashboardTile(item) {
  const artist = item.artist || item.album_artist || 'Unknown artist';
  const album = item.album || item.title || 'Untitled album';
  const tile = document.createElement('article');
  tile.className = 'card editorial-card dashboard-tile';
  // On a phone the year and listen count sit under the artist, as on the Deep Dives cards.
  const phone = isMobileLayout();
  if (phone) tile.dataset.yearTarget = 'supporting';
  // Data only: the tile is not a button itself, so the Get control is never nested in one.
  makeAlbumCardInteractive(tile, artist, album, item, true, false);

  // Placed before the artwork so this is the first focus stop on the tile, with Get after it.
  const open = document.createElement('button');
  open.type = 'button';
  open.className = 'dashboard-tile-open';
  open.setAttribute('aria-label', 'View details for ' + album + ' by ' + artist);
  open.addEventListener('click', () => openAlbumModal(tile, open));
  tile.append(open);

  attachArtwork(tile, artist, album);

  // The name above carries the album and artist, so the visible copy is hidden from assistive tech.
  const meta = document.createElement('div');
  meta.className = 'dashboard-tile-meta';
  addTextElement(meta, 'p', 'card-category', dashboardTag(item.dashboard_category, phone));
  const title = document.createElement('h3');
  linkAlbumName(title, artist, album, item);
  const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, tile.dataset.releaseYear);
  meta.append(title);
  linkArtistName(addTextElement(meta, 'p', 'card-artist', ''), artist);
  // Phone: album, artist, then year and listens on one line. Desktop keeps the year and listens
  // under the album name.
  const detail = phone ? meta.querySelector('.card-artist') : title;
  if (year !== null) addAlbumYear(detail, year, true);
  addAlbumListens(detail, item, true);
  // Phone: the bio is the About overlay on the artwork. Desktop shows it in the feature slide.
  if (artist !== 'Unknown artist') attachCardArtistBio(tile, phone ? tile.querySelector('.card-art') : meta, artist);
  tile.append(meta);
  ensureAlbumYearBadge(tile);

  tile.querySelector('.card-art').append(createActionGroup(artist, album, item, {
    listName: 'dashboard_picks',
    onDismiss: () => dismissDashboardPick(tile, artist, album, item)
  }));
  return tile;
}

// Not for me on a pick takes the slide out of the strip at once, so the slider never shows an empty
// feature, and puts it back where it was if the owner undoes the dismissal or the request fails.
// The tag over a pick. The phone layout has room for one short word, so the two list names shrink
// to "discovery" and "deep dive"; any other label is shown as the server sent it.
function dashboardTag(label, phone) {
  const text = String(label || 'Discovery');
  if (!phone) return text;
  if (/discover/i.test(text)) return 'discovery';
  if (/deep dive/i.test(text)) return 'deep dive';
  return text;
}

function dismissDashboardPick(tile, artist, album, item) {
  const slider = $('dashboardCarousel');
  const before = tile.nextElementSibling;
  // The kept list loses the pick too, so a rebuild for the other layout does not bring it back.
  const position = dashboardPickItems.indexOf(item);
  if (position >= 0) dashboardPickItems.splice(position, 1);
  const restore = () => {
    if (position >= 0) dashboardPickItems.splice(position, 0, item);
    slider.insertBefore(tile, before && before.parentNode === slider ? before : null);
    syncDashboardSlider();
  };
  tile.remove();
  syncDashboardSlider();
  sendFeedback('dismiss', artist, album, item, 'dashboard_picks', tile, restore);
}

/* The picks are a slider: the first slide after the one just passed is the feature (slot 1), the next
   three are thumbnails (slots 2 to 4). Rotating moves a slide from one end of the strip to the other,
   and the slots are read back from the DOM order. */
function syncDashboardSlider() {
  const slider = $('dashboardCarousel');
  const tiles = [...slider.children];
  if (isMobileLayout()) {
    // Phone: a swipeable strip with one card per page and a dot for each. Every card is a tab
    // stop, and there are no slots, arrows or "x of n" count.
    tiles.forEach(tile => {
      tile.dataset.slot = '1';
      const open = tile.querySelector('.dashboard-tile-open');
      if (open) open.tabIndex = 0;
    });
    $('dashboardSliderCount').textContent = '';
    syncDashboardDots();
    return;
  }
  tiles.forEach((tile, index) => {
    const slot = tiles.length === 1 ? 1 : Math.min(index, 5);
    tile.dataset.slot = String(slot);
    // Only the feature slide is a tab stop; a thumbnail is reached by Previous, Next or a click.
    const open = tile.querySelector('.dashboard-tile-open');
    if (open) open.tabIndex = slot === 1 ? 0 : -1;
  });
  const active = tiles.find(tile => tile.dataset.slot === '1');
  $('dashboardSliderCount').textContent = active ? `${Number(active.dataset.pick) + 1} of ${tiles.length}` : '';
  $('dashboardPrev').disabled = $('dashboardNext').disabled = tiles.length < 2;
  tintDashboardSlider(active);
}

// The strip takes its background from the feature slide's cover, the same colour the album and
// artist pages use (dominantColor, backdropTint). A cover that cannot be read leaves the plain
// background. Colours are kept by cover URL, so rotating back to a slide costs nothing.
const sliderTintByUrl = new Map();
let sliderTintTile = null;

function setSliderTint(color) {
  const slider = $('dashboardCarousel');
  if (color) {
    slider.style.setProperty('--slider-tint', color);
    slider.classList.add('has-tint');
  } else {
    slider.classList.remove('has-tint');
  }
}

function tintDashboardSlider(tile) {
  sliderTintTile = tile || null;
  const image = tile && tile.querySelector('.card-art img');
  if (!image) { setSliderTint(null); return; }
  const apply = () => {
    if (sliderTintTile !== tile) return;
    const url = image.currentSrc || image.src;
    if (!url) return;
    if (sliderTintByUrl.has(url)) { setSliderTint(sliderTintByUrl.get(url)); return; }
    const copy = new Image();
    copy.crossOrigin = 'anonymous';
    copy.decoding = 'async';
    copy.onload = () => {
      let tint = null;
      try {
        const color = dominantColor(copy);
        if (color) tint = backdropTint(color);
      } catch (error) { /* tainted canvas: keep the default background */ }
      sliderTintByUrl.set(url, tint);
      if (sliderTintTile === tile) setSliderTint(tint);
    };
    copy.onerror = () => sliderTintByUrl.set(url, null);
    copy.src = url;
  };
  if (image.complete && image.naturalWidth) apply();
  else {
    // Keep the previous colour until this cover arrives.
    image.addEventListener('load', apply, {once: true});
  }
}

// The card the phone strip is showing: the one whose left edge is nearest the strip's.
function currentDashboardIndex() {
  const slider = $('dashboardCarousel');
  const width = slider.clientWidth;
  return width ? Math.max(0, Math.min(slider.children.length - 1, Math.round(slider.scrollLeft / width))) : 0;
}

// One dot per card under the phone strip, the current one filled. Tapping a dot scrolls to its card.
function syncDashboardDots() {
  const slider = $('dashboardCarousel');
  const dots = $('dashboardDots');
  const count = slider.children.length;
  if (dots.children.length !== count) {
    dots.replaceChildren(...Array.from({length: count}, (unused, index) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'dashboard-dot';
      dot.setAttribute('aria-label', `Show album ${index + 1} of ${count}`);
      dot.addEventListener('click', () =>
        slider.scrollTo({left: index * slider.clientWidth, behavior: trackScrollBehavior()}));
      return dot;
    }));
  }
  const current = currentDashboardIndex();
  [...dots.children].forEach((dot, index) => {
    if (index === current) dot.setAttribute('aria-current', 'true');
    else dot.removeAttribute('aria-current');
  });
  // The tint follows the card on show, and is worked out once per card, not on every scroll event.
  const key = `${count}:${current}`;
  if (slider.dataset.tintedFor !== key) {
    slider.dataset.tintedFor = key;
    tintDashboardSlider(slider.children[current]);
  }
}

$('dashboardCarousel').addEventListener('scroll', () => {
  if (isMobileLayout()) syncDashboardDots();
}, {passive: true});

function rotateDashboardSlider(direction) {
  const slider = $('dashboardCarousel');
  const tiles = [...slider.children];
  if (tiles.length < 2) return;
  if (isMobileLayout()) {
    slider.scrollBy({left: direction * slider.clientWidth, behavior: trackScrollBehavior()});
    return;
  }
  if (direction > 0) slider.append(tiles[0]);
  else slider.prepend(tiles[tiles.length - 1]);
  syncDashboardSlider();
}

$('dashboardPrev').addEventListener('click', () => rotateDashboardSlider(-1));
$('dashboardNext').addEventListener('click', () => rotateDashboardSlider(1));
$('dashboardCarousel').addEventListener('keydown', event => {
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  if (event.key === 'ArrowRight') rotateDashboardSlider(1);
  else if (event.key === 'ArrowLeft') rotateDashboardSlider(-1);
  else return;
  event.preventDefault();
});
// A click on a thumbnail brings that album forward instead of opening it.
$('dashboardCarousel').addEventListener('click', event => {
  const tile = event.target.closest('.dashboard-tile');
  const slot = tile ? Number(tile.dataset.slot) : 1;
  if (!tile || slot < 2 || slot > 4) return;
  event.preventDefault();
  event.stopPropagation();
  for (let step = 1; step < slot; step += 1) rotateDashboardSlider(1);
}, true);

// The picks last fetched, kept so the strip can be rebuilt for the other layout without choosing
// new albums (see the layout change handler at the end of this file).
let dashboardPickItems = [];

function renderDashboardPicks() {
  const target = $('dashboardCarousel');
  target.replaceChildren();
  delete target.dataset.tintedFor;
  dashboardPickItems.forEach((item, index) => {
    const tile = buildDashboardTile(item);
    tile.dataset.pick = String(index);
    target.append(tile);
  });
  // Slot 0 is the slide just passed, so the first pick starts as the feature by moving the last one
  // before it. The phone strip has no slots and starts at the first card.
  if (!isMobileLayout() && target.children.length > 1) target.prepend(target.lastElementChild);
  target.scrollLeft = 0;
  syncDashboardSlider();
}

async function loadDashboardPicks() {
  const target = $('dashboardCarousel');
  const status = $('dashboardPicksStatus');
  const shuffle = $('shuffleDashboard');
  target.replaceChildren();
  syncDashboardSlider();
  status.textContent = 'Picking ten albums across your discovery lists…';
  // A second shuffle while one is pending would race two responses into the same strip.
  shuffle.disabled = true;
  try {
    const data = await requestJSON('/api/dashboard-picks?count=10&nonce=' + Date.now());
    const items = (data.items || []).filter(isAlbumRecommendation);
    dashboardPickItems = items;
    renderDashboardPicks();
    status.textContent = items.length
      ? `${items.length} randomly selected albums from ${data.pool_size || items.length} available suggestions.`
      : 'No suggestions yet. Open a discovery page and refresh its list first.';
  } catch (error) {
    status.textContent = error.message;
  } finally {
    shuffle.disabled = false;
  }
}

$('shuffleDashboard').addEventListener('click', loadDashboardPicks);

/* ------------------------------------------------------------ phone album cards

   On a phone, Recommendations, New releases, Personal Discoveries and Daily picks show album cards
   in a row that scrolls sideways, as on the Deep Dives page, instead of ranked rows. The card is the
   Deep Dives card: artwork with the About overlay, tag, album with year and listens, artist, and the
   Get, Save and Not for me group. A list that is not shown as cards keeps its rows. */
function setCardTrack(target, on) {
  target.classList.toggle('ranked-list', !on);
  target.classList.toggle('genre-row-track', on);
  if (on && !target.dataset.trackFocusable) {
    target.dataset.trackFocusable = 'true';
    makeScrollTrackFocusable(target, target.getAttribute('aria-label') || 'Albums');
  } else if (!on && target.dataset.trackFocusable) {
    delete target.dataset.trackFocusable;
    target.removeAttribute('tabindex');
    target.removeAttribute('role');
  }
}

// `options`: `tag` (the small label over the title), `meta` (extra lines), `listName` (for Save and
// the dismiss feedback), `onDismiss(artist, album, item, card)`.
function buildListCard(item, options = {}) {
  const artist = item.artist || item.album_artist || 'Unknown artist';
  const album = item.album || item.title || item.name || 'Untitled album';
  const card = document.createElement('article');
  card.className = 'card editorial-card';
  makeAlbumCardInteractive(card, artist, album, item);
  attachArtwork(card, artist, album);
  if (options.tag) addTextElement(card, 'p', 'card-category', options.tag);
  const title = document.createElement('h3');
  linkAlbumName(title, artist, album, item);
  const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, card.dataset.releaseYear);
  if (year !== null) addAlbumYear(title, year, true);
  addAlbumListens(title, item, true);
  card.append(title);
  linkArtistName(addTextElement(card, 'p', 'card-artist', ''), artist);
  ensureAlbumYearBadge(card);
  if (artist !== 'Unknown artist') attachCardArtistBio(card, card.querySelector('.card-art'), artist);
  for (const line of options.meta || []) if (line) addTextElement(card, 'p', 'card-meta', line);
  // Saved cards are bookmarks: no Not for me, no Get for an album already in the library, and Save
  // starts pressed (its next press undoes), as on the Saved rows.
  const group = createActionGroup(artist, album, item, {
    owned: options.owned,
    listName: options.listName,
    onDismiss: options.onDismiss && (() => options.onDismiss(artist, album, item, card))
  });
  if (options.saved) setSaveButtonState(group.querySelector('.save-album'), true, album);
  card.append(group);
  return card;
}

function dismissRecommendationLocally(artist, album) {
  const key = [artist, album].map(value => String(value).trim().toLocaleLowerCase()).join('::');
  const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-recommendations') || '[]'));
  dismissed.add(key);
  localStorage.setItem('navidrome-dismissed-recommendations', JSON.stringify([...dismissed]));
  applyRecommendationFilters();
}

function buildRecommendationCard(item) {
  const card = buildListCard(item, {
    tag: categoryLabel(item.discovery_category || 'unclassified'),
    meta: [item.discovery_category === 'adjacent' && Array.isArray(item.similar_to) && item.similar_to.length
      ? 'Similar to: ' + item.similar_to.join(', ') : ''],
    onDismiss: dismissRecommendationLocally
  });
  card.dataset.key = recommendationKey(item);
  return card;
}

function buildClassicsCard(item) {
  const hasBio = /Genre tags connect this artist to your established musical interests/i.test(item.reason || '');
  return buildListCard(item, {
    tag: categoryLabel(item.discovery_type || item.discovery_category || ''),
    meta: [item.anchor_artist ? 'Similar to: ' + item.anchor_artist : '', hasBio ? '' : item.reason],
    listName: 'classics',
    onDismiss: (artist, album, metadata, card) => sendFeedback('dismiss', artist, album, metadata, 'classics', card)
  });
}

function buildSavedCard(entry) {
  const item = {...(entry.metadata || {}), artist: entry.artist, album: entry.album};
  const owned = entry.acquired === true;
  return buildListCard(item, {
    tag: formatSavedDate(entry.saved_at),
    meta: [owned ? 'Already in your library' : ''],
    owned,
    saved: true,
    listName: 'saved'
  });
}

function buildNewReleaseCard(item) {
  const parts = releaseDateParts(item.first_release_date);
  return buildListCard(item, {
    tag: parts ? parts.label : 'New release',
    listName: 'new_releases',
    onDismiss: (artist, album, metadata, card) => sendFeedback('dismiss', artist, album, metadata, 'new_releases', card)
  });
}

function buildPersonalCard(item) {
  return buildListCard(item, {
    tag: categoryLabel(item.discovery_category || ''),
    meta: [item.discovery_category === 'unclassified' || item.genre_metadata_available === false
      ? 'Low confidence: genre data unavailable' : ''],
    listName: 'personal',
    onDismiss: (artist, album, metadata, card) => sendFeedback('dismiss', artist, album, metadata, 'personal', card)
  });
}

function buildLensCard(item, name) {
  const listeners = Number(item.album_listeners);
  return buildListCard(item, {
    tag: item.seed_tag || LENS_LISTS[name],
    meta: [Number.isFinite(listeners) && listeners > 0 ? listeners.toLocaleString() + ' listeners' : ''],
    listName: 'lens_lists',
    onDismiss: (artist, album, metadata, card) => sendFeedback('dismiss', artist, album, metadata, 'lens_lists', card)
  });
}

// Daily picks on a phone: the four lists one after the other, each a heading over a row of cards,
// so there is no lens picker. A list that cannot load says so in its own place.
async function loadAllLensLists() {
  const requestId = ++lensRequestId;
  const status = $('lensListsStatus');
  const target = $('lensListsCards');
  target.classList.remove('ranked-list');
  target.classList.add('lens-sections');
  target.removeAttribute('role');
  status.textContent = 'Loading daily picks…';
  setStatusState(status, 'loading');
  target.replaceChildren();
  const names = Object.keys(LENS_LISTS);
  const results = await Promise.allSettled(names.map(name =>
    requestJSON(`/api/discovery/${name}?count=10&nonce=${Date.now()}`)));
  if (requestId !== lensRequestId) return;
  let total = 0;
  let disabled = false;
  let failure = '';
  results.forEach((result, index) => {
    const name = names[index];
    const section = document.createElement('section');
    section.className = 'genre-row';
    const heading = document.createElement('div');
    heading.className = 'genre-row-heading';
    addTextElement(heading, 'h3', '', LENS_LISTS[name]);
    section.append(heading);
    if (result.status === 'rejected') {
      failure = result.reason && result.reason.message ? result.reason.message : 'Request failed.';
      addTextElement(section, 'p', 'status-line is-error', LENS_LISTS[name] + ' could not be loaded: ' + failure);
    } else {
      const items = Array.isArray(result.value.items) ? result.value.items : [];
      disabled = disabled || Boolean(result.value.disabled);
      total += items.length;
      addTextElement(heading, 'span', 'genre-row-count', pluralize(items.length, 'album', 'albums'));
      const track = document.createElement('div');
      track.className = 'genre-row-track';
      makeScrollTrackFocusable(track, LENS_LISTS[name] + ' albums');
      track.append(...items.map(item => buildLensCard(item, name)));
      if (!items.length) addTextElement(track, 'p', 'ranked-empty', result.value.message || LENS_LISTS[name] + ' has no albums today.');
      section.append(track);
    }
    target.append(section);
  });
  status.textContent = total
    ? pluralize(total, 'album', 'albums') + ' · Fixed for today, rebuilt each morning'
    : disabled ? 'Daily picks are turned off in Settings.'
    : failure ? 'Daily picks could not be loaded: ' + failure : 'No albums today.';
  setStatusState(status, total ? 'progress' : failure ? 'error' : 'empty');
}

/* ------------------------------------------------------- dashboard genres and album shelves

   Genre tiles and the album shelves below the picks. Newly added, Recently played and Most played
   come from Navidrome in its own order; New releases comes from the discovery list. Each card
   shows a check when the library has the album and the Get control when it does not. */
const GENRE_TILES_COLLAPSED = 12;

// A stable hue per genre, so a tile keeps its colour across loads.
function genreTileHue(tag) {
  let hash = 0;
  for (const char of tag) hash = (hash * 31 + char.codePointAt(0)) % 360;
  return hash;
}

function buildGenreTile(genre) {
  const tile = document.createElement('button');
  tile.type = 'button';
  tile.className = 'genre-tile';
  tile.style.setProperty('--genre-hue', String(genreTileHue(genre.tag)));
  tile.textContent = genre.name;
  tile.title = pluralize(genre.album_count, 'album', 'albums');
  tile.addEventListener('click', () => openLibraryTarget({type: 'genre', tag: genre.tag}));
  return tile;
}

async function loadDashboardGenres() {
  const target = $('dashboardGenreTiles');
  const status = $('dashboardGenresStatus');
  const more = $('dashboardGenresMore');
  status.textContent = 'Loading genres…';
  try {
    const data = await requestJSON('/api/dashboard/genres?limit=60');
    const genres = data.items || [];
    const render = expanded => {
      target.replaceChildren(...(expanded ? genres : genres.slice(0, GENRE_TILES_COLLAPSED)).map(buildGenreTile));
      more.setAttribute('aria-expanded', String(expanded));
      more.textContent = expanded ? 'Show fewer' : 'View more';
    };
    render(false);
    more.hidden = genres.length <= GENRE_TILES_COLLAPSED;
    more.onclick = () => render(more.getAttribute('aria-expanded') !== 'true');
    status.textContent = genres.length ? '' : 'No genres in your library yet.';
  } catch (error) {
    status.textContent = error.message;
  }
}

function buildShelfCard(item, withActions = false) {
  const card = document.createElement('article');
  card.className = 'card shelf-card';
  const open = document.createElement('button');
  open.type = 'button';
  open.className = 'dashboard-tile-open';
  open.setAttribute('aria-label', 'Open ' + item.name + ' by ' + item.artist);
  open.addEventListener('click', () => openLibraryTarget(item.owned
    ? albumTarget({...item, key: foldKey(item.artist) + '/' + foldKey(item.name)})
    : namedAlbumTarget(item.artist, item.name, item)));
  card.append(open);

  attachArtwork(card, item.artist, item.name, item.owned ? sizedArtwork(item.artwork_url, 300) : null);
  let footGroup = null;
  // The New releases shelf carries the same group as the cards; an album already in the library
  // keeps the check, and the other shelves keep their single Get.
  if (withActions && !item.owned) {
    const metadata = {
      artist: item.artist, album: item.name, year: item.year || null, release_group_mbid: item.release_group_mbid || null,
    };
    // As on the discovery cards, the group sits at the foot of the card and the bio overlays the
    // artwork on hover.
    footGroup = createActionGroup(item.artist, item.name, metadata, {
      listName: 'dashboard_shelf',
      onDismiss: () => dismissShelfCard(card, item.artist, item.name, metadata)
    });
    if (item.artist) attachCardArtistBio(card, card.querySelector('.card-art'), item.artist);
  } else {
    const state = buildAlbumState(item);
    card.querySelector('.card-art').append(item.owned ? state : wrapInActionGroup(state, 'Actions for ' + item.name));
  }

  const meta = document.createElement('div');
  meta.className = 'dashboard-tile-meta';
  const title = document.createElement('h3');
  title.append(buildInlineLink(item.name, item.owned
    ? albumTarget({...item, key: foldKey(item.artist) + '/' + foldKey(item.name)})
    : namedAlbumTarget(item.artist, item.name, item)));
  if (item.year) addAlbumYear(title, item.year, true);
  if (withActions) addAlbumListens(title, item, true);
  meta.append(title);
  if (item.artist) linkArtistName(addTextElement(meta, 'p', 'card-artist', ''), item.artist);
  card.append(meta);
  if (footGroup) card.append(footGroup);
  return card;
}

// Not for me on a shelf card removes it at once and restores it on Undo or on a failed request.
function dismissShelfCard(card, artist, album, metadata) {
  const parent = card.parentNode;
  const before = card.nextElementSibling;
  card.remove();
  sendFeedback('dismiss', artist, album, metadata, 'dashboard_shelf', card,
    () => parent.insertBefore(card, before && before.parentNode === parent ? before : null));
}

// Discovery items name the album "album"; Navidrome shelves name it "name".
function shelfItemFromDiscovery(item) {
  return {
    name: item.album || item.title || '', artist: item.artist || item.album_artist || '',
    year: firstReleaseYear(item.year, item.release_year, item.first_release_year),
    release_group_mbid: item.release_group_mbid || null, owned: item.owned === true,
    lastfm_listeners: item.lastfm_listeners || null, lastfm_playcount: item.lastfm_playcount || null,
  };
}

async function loadShelf(name, url, mapItems, withActions = false) {
  const target = $('shelf' + name);
  const status = $('shelf' + name + 'Status');
  status.textContent = 'Loading…';
  try {
    const data = await requestJSON(url);
    const items = mapItems(data).filter(item => item.name);
    target.replaceChildren(...items.map(item => buildShelfCard(item, withActions)));
    status.textContent = items.length ? '' : 'Nothing to show yet.';
  } catch (error) {
    status.textContent = error.message;
  }
}

function loadDashboardShelves() {
  loadDashboardGenres();
  loadShelf('NewReleases', '/api/discovery/new_releases?count=30',
    data => (data.items || data.recommendations || []).filter(isAlbumRecommendation).map(shelfItemFromDiscovery), true);
  loadShelf('Newest', '/api/dashboard/albums/newest?count=20', data => data.items || []);
  loadShelf('Recent', '/api/dashboard/albums/recent?count=20', data => data.items || []);
  loadShelf('Frequent', '/api/dashboard/albums/frequent?count=20', data => data.items || []);
}

function attachArtwork(card, artist, album, knownUrl = null) {
  const art = document.createElement('div');
  art.className = 'card-art';
  // A div has no role, and ARIA forbids naming a generic element, so the label was never
  // announced. A group gives the artwork and its Get control a name.
  art.setAttribute('role', 'group');
  art.setAttribute('aria-label', 'Album artwork');

  const placeholder = document.createElement('div');
  placeholder.className = 'card-art-placeholder';
  placeholder.textContent = 'COVER NOT FOUND';

  const image = document.createElement('img');
  image.alt = '';
  image.loading = 'lazy';
  image.decoding = 'async';
  art.append(image, placeholder);
  card.append(art);

  // The library already holds this cover, so there is nothing to look up.
  if (knownUrl) {
    image.onload = () => art.classList.add('has-image');
    image.onerror = () => art.classList.remove('has-image');
    image.src = knownUrl;
    return;
  }

  const loadArtwork = () => {
    if (art.dataset.requested) return;
    art.dataset.requested = 'true';
    const query = new URLSearchParams({artist: artist || '', album: album || ''});
    const cacheKey = (artist || '').trim().toLocaleLowerCase() + '::' + (album || '').trim().toLocaleLowerCase();
    cachedJSONRequest(artworkRequests, cacheKey, '/api/artwork?' + query.toString())
      .then(data => {
        if (data && data.retryable) {
          const retries = Number(art.dataset.artworkRetries || 0);
          if (retries < 3) {
            art.dataset.artworkRetries = String(retries + 1);
            // Provider outages are transient. Clear the in-page promise cache and
            // retry with backoff instead of permanently leaving this card blank.
            artworkRequests.delete(cacheKey);
            art.dataset.requested = '';
            setTimeout(loadArtwork, [2000, 5000, 10000][retries]);
          }
          return;
        }
        if (!data) return;
        if (data.year) applyAlbumYear(card, data.year);
        if (!data.artwork_url) return;
        image.onload = () => art.classList.add('has-image');
        image.onerror = () => art.classList.remove('has-image');
        image.fetchPriority = art.getBoundingClientRect().top < window.innerHeight ? 'high' : 'auto';
        image.src = data.artwork_url;
      })
      .catch(() => {});
  };

  artworkLoaders.set(art, loadArtwork);
  if (artworkObserver) artworkObserver.observe(art);
  else loadArtwork();
}

let allRecommendations = [];
let recommendationData = null;

function renderRecommendations(data) {
  recommendationData = data;
  allRecommendations = getRecommendations(data).filter(isAlbumRecommendation);
  $('recommendationDebug').textContent = pretty(data);
  applyRecommendationFilters();
}

function applyRecommendationFilters() {
  const cards = $('recommendationCards');
  cards.replaceChildren();

  const query = $('recommendationSearch').value.trim().toLocaleLowerCase();
  const category = $('categoryFilter').value;
  const sort = $('recommendationSort').value;

  const filtered = allRecommendations.filter(item => {
    const searchable = [
      item.artist,
      item.album_artist,
      item.album,
      item.title,
      ...(Array.isArray(item.genres) ? item.genres : []),
      ...(Array.isArray(item.genre_families) ? item.genre_families : []),
      item.diversity_style,
      item.discovery_category
    ].filter(Boolean).join(' ').toLocaleLowerCase();

    const itemCategory = item.discovery_category || 'unclassified';

    const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-recommendations') || '[]'));
    return !dismissed.has(recommendationKey(item)) && (!query || searchable.includes(query)) &&
      (category === 'all' || itemCategory === category);
  });

  const numeric = value =>
    value !== null && value !== undefined && value !== '' &&
    Number.isFinite(Number(value)) ? Number(value) : null;

  if (sort === 'popularity') {
    filtered.sort((a, b) =>
      (numeric(b.lastfm_listeners) ?? -1) -
      (numeric(a.lastfm_listeners) ?? -1));
  } else if (sort === 'score') {
    filtered.sort((a, b) =>
      (numeric(b.discovery_score) ?? -Infinity) -
      (numeric(a.discovery_score) ?? -Infinity));
  } else if (sort === 'artist') {
    filtered.sort((a, b) =>
      (a.artist || a.album_artist || '').localeCompare(
        b.artist || b.album_artist || ''
      ));
  }

  const basis = rankingBasis(sort, filtered);
  $('recommendationCount').textContent =
    `Showing ${filtered.length} of ${allRecommendations.length} recommendations · ${basis.label}`;

  const asCards = isMobileLayout();
  setCardTrack(cards, asCards);
  filtered.forEach((item, index) => {
    if (asCards) { cards.append(buildRecommendationCard(item)); return; }
    const row = buildRecommendationRow(item, basis.numbered ? index + 1 : null, {artistBio: true});
    row.dataset.key = recommendationKey(item);
    cards.append(row);
  });

  if (!filtered.length) {
    addTextElement(
      cards, 'p', 'ranked-empty',
      allRecommendations.length
        ? 'No recommendations match these filters. Try another search or category.'
        : 'No recommendations returned. Generate recommendations to try again.'
    );
  }
}

// Stable identity for a recommendation: the same key the dismiss list uses, so a row keeps its
// identity across re-sorts and the reorder animation can follow it.
function recommendationKey(item) {
  return [item.artist || item.album_artist || '', item.album || item.title || item.name || '']
    .map(value => String(value).trim().toLocaleLowerCase()).join('::');
}

// Re-renders the recommendation list and, for a sort change only, slides each row from its old
// position to its new one (FLIP, DESIGN_SYSTEM.md 11). Only transform animates. Reduced motion
// shows the new order at once, and no animation is created.
function reorderRecommendations(render) {
  const cards = $('recommendationCards');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const before = new Map();
  if (!reduced) {
    cards.querySelectorAll('[data-key]').forEach(row => before.set(row.dataset.key, row.getBoundingClientRect().top));
  }
  render();
  if (reduced || !before.size) return;
  const rootStyle = getComputedStyle(document.documentElement);
  const duration = parseFloat(rootStyle.getPropertyValue('--dur-slow')) || 260;
  const easing = rootStyle.getPropertyValue('--ease-out').trim() || 'ease-out';
  // Read every new position first, then write the animations, so layout is not forced per row.
  const moves = [];
  cards.querySelectorAll('[data-key]').forEach(row => {
    const previous = before.get(row.dataset.key);
    if (previous === undefined) return;
    const distance = previous - row.getBoundingClientRect().top;
    if (Math.abs(distance) >= 1) moves.push({row, distance});
  });
  moves.forEach(({row, distance}) => {
    row.animate(
      [{transform: `translateY(${distance}px)`}, {transform: 'translateY(0)'}],
      {duration, easing}
    );
  });
}

// Describes the order the rows are shown in. A numeral is only honest when the order is a real
// one the API returns (server order, discovery_score, lastfm_listeners); a sort that has missing
// values, or an alphabetical sort, shows no numerals and says so (DESIGN_SYSTEM.md section 8).
function rankingBasis(sort, items) {
  const numeric = value =>
    value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const complete = field => items.length > 0 && items.every(item => numeric(item[field]));
  if (sort === 'score') {
    return complete('discovery_score')
      ? {label: 'Ranked by discovery score', numbered: true}
      : {label: 'Sorted by discovery score; some albums have no score', numbered: false};
  }
  if (sort === 'popularity') {
    return complete('lastfm_listeners')
      ? {label: 'Ranked by Last.fm artist listeners', numbered: true}
      : {label: 'Sorted by Last.fm artist listeners; some albums have no count', numbered: false};
  }
  if (sort === 'artist') return {label: 'Sorted A–Z by artist', numbered: false};
  return {label: 'Recommended order', numbered: true};
}

// One ranked row (DESIGN_SYSTEM.md 9.4): numeral, artwork, title and artist, metadata, action.
// The whole row opens the album modal; the Get and dismiss controls are separate focus stops.
// Built with text APIs only; every value from the API is set through textContent or as text nodes.
// `options` lets other lists reuse this row (New releases): `releaseDate` puts the API's
// first_release_date in the leading column instead of a numeral, `meta` replaces the Discover
// metadata lines, and `onDismiss` routes dismissal to the server feedback
// that list already uses instead of the Discover local list.
function buildRecommendationRow(item, rank, options = {}) {
  const row = document.createElement('article');
  row.className = options.releaseDate ? 'ranked-row is-dated' : 'ranked-row';
  const artist = item.artist || item.album_artist || '';
  const album = item.album || item.title || item.name || '';
  makeAlbumCardInteractive(row, artist, album, item);
  // Icon-only and repeated controls name the album and artist they act on.

  if (options.releaseDate) {
    row.append(releaseDateColumn(item, row));
  } else {
    const numeral = document.createElement('span');
    // `indexed` lists show a muted position, not the red rank: the order is not a score order.
    numeral.className = options.indexed ? 'rank-numeral is-index' : 'rank-numeral';
    numeral.setAttribute('aria-hidden', 'true');
    if (rank !== null) numeral.textContent = String(rank).padStart(2, '0');
    row.append(numeral);
  }

  attachArtwork(row, artist, album);

  const main = document.createElement('div');
  main.className = 'row-main';
  const title = document.createElement('h3');
  title.setAttribute('title', album || 'Untitled album');
  linkAlbumName(title, artist, album || 'Untitled album', item);
  main.append(title);
  linkArtistName(addTextElement(main, 'p', 'row-artist', ''), artist || 'Unknown artist');
  if (options.artistBio) attachArtistBio(row, main, artist);
  row.append(main);
  // The release-date column already shows the year, so a release-date row carries no year badge.
  if (!options.releaseDate) {
    const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, row.dataset.releaseYear);
    if (year !== null) addAlbumYear(title, year, false);
    ensureAlbumYearBadge(row);
  }
  addAlbumListens(title, item, false);

  const meta = document.createElement('div');
  meta.className = 'row-meta';
  if (options.meta) {
    for (const line of options.meta) if (line) addTextElement(meta, 'p', 'row-meta-line', line);
  } else {
    addRecommendationMeta(meta, item);
  }
  // A row with nothing to say in the metadata column drops it, so the bio gets the width.
  if (meta.childElementCount) row.append(meta);
  else row.classList.add('no-meta');

  const actions = document.createElement('div');
  actions.className = 'row-actions';
  // Every row on the Saved page is saved and cannot be dismissed: the Save control starts
  // pressed, and its next press undoes. The other lists dismiss through the server feedback
  // endpoint they pass in, or through the Discover local list.
  const onDismiss = options.saved ? null : options.onDismiss || (() => {
    const key = [artist, album].map(value => String(value).trim().toLocaleLowerCase()).join('::');
    const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-recommendations') || '[]'));
    dismissed.add(key);
    localStorage.setItem('navidrome-dismissed-recommendations', JSON.stringify([...dismissed]));
    applyRecommendationFilters();
  });
  const group = createActionGroup(artist, album, item, {
    owned: options.owned,
    listName: options.listName,
    onDismiss: onDismiss && (() => options.onDismiss ? options.onDismiss(artist, album, item, row) : onDismiss())
  });
  if (options.saved) setSaveButtonState(group.querySelector('.save-album'), true, album);
  actions.append(group);
  row.append(actions);
  return row;
}

const monthAbbreviations = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// Formats first_release_date as the API returns it: YYYY-MM-DD, or a partial YYYY-MM or YYYY
// from MusicBrainz. Returns null for anything else, so the column stays empty rather than
// showing a date the server did not return (DESIGN_SYSTEM.md section 8).
function releaseDateParts(value) {
  const match = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(String(value || '').trim());
  if (!match) return null;
  const [, year, monthText, dayText] = match;
  const month = monthText ? Number(monthText) : 0;
  const day = dayText ? Number(dayText) : 0;
  if (monthText && (month < 1 || month > 12)) return null;
  if (dayText && (day < 1 || day > 31)) return null;
  const monthName = month ? monthAbbreviations[month - 1] : '';
  return {
    day: day ? `${day} ${monthName}` : monthName,
    year,
    label: [day || '', monthName, year].filter(Boolean).join(' ')
  };
}

// The leading column of a release-date row: the release date in place of the rank numeral.
// Missing or unrecognised dates leave the column empty. The date is also added to the row's
// accessible name, because the row is a button and its visible children are not announced.
function releaseDateColumn(item, row) {
  const column = document.createElement('span');
  column.className = 'row-date';
  const parts = releaseDateParts(item.first_release_date);
  if (parts) {
    if (parts.day) addTextElement(column, 'span', 'row-date-day', parts.day);
    addTextElement(column, 'span', 'row-date-year', parts.year);
    row.setAttribute('aria-label', `${row.getAttribute('aria-label')}, released ${parts.label}`);
  }
  return column;
}

// New releases rows (DESIGN_SYSTEM.md section 8). The list is ordered by release date on the
// server (newest first), which the status line names. Dismiss goes through the same feedback
// endpoint the card used, so the server's dismiss and dismiss-artist rules still apply.
function buildNewReleaseRow(item) {
  return buildRecommendationRow(item, null, {
    releaseDate: true,
    artistBio: true,
    meta: [],
    listName: 'new_releases',
    onDismiss: (artist, album, metadata, row) => sendFeedback('dismiss', artist, album, metadata, 'new_releases', row)
  });
}

// Daily lens lists (Engine 2, Phase 4 slice 4). Each lens has one stored list for the day, served
// by /api/discovery/<lens>. While engine2_lens_lists_enabled is off the server answers with
// `disabled` and a message; that is shown in the status line, not as an error. The lens seed tag
// and listener count are the only extra lines, so each album shows why it was picked.
const LENS_LISTS = {
  repeated_tracks: 'Repeated tracks',
  deep_cuts: 'Deep cuts',
  obsessions: 'Obsessions',
  current_tastes: 'Current tastes'
};
let activeLens = 'repeated_tracks';
let lensRequestId = 0;

function setActiveLens(name) {
  activeLens = name;
  document.querySelectorAll('[data-lens]').forEach(button =>
    button.setAttribute('aria-pressed', String(button.dataset.lens === name)));
}

// Each row is a list item, so assistive tech announces the list and each row's position in it.
function buildLensRow(item) {
  const listeners = Number(item.album_listeners);
  const row = buildRecommendationRow(item, item.rank, {
    indexed: true,
    meta: [
      item.seed_tag ? 'Seed tag: ' + item.seed_tag : '',
      Number.isFinite(listeners) && listeners > 0 ? listeners.toLocaleString() + ' listeners' : ''
    ],
    listName: 'lens_lists',
    onDismiss: (artist, album, metadata, row) => sendFeedback('dismiss', artist, album, metadata, 'lens_lists', row)
  });
  row.setAttribute('role', 'listitem');
  return row;
}

async function loadLensList(name) {
  if (isMobileLayout()) return loadAllLensLists();
  const lensTarget = $('lensListsCards');
  lensTarget.classList.add('ranked-list');
  lensTarget.classList.remove('lens-sections');
  lensTarget.setAttribute('role', 'list');
  setActiveLens(name);
  const requestId = ++lensRequestId;
  const label = LENS_LISTS[name];
  const status = $('lensListsStatus');
  const target = $('lensListsCards');
  status.textContent = 'Loading ' + label + '…';
  setStatusState(status, 'loading');
  target.replaceChildren(...skeletonRows(6));
  try {
    const data = await requestJSON(`/api/discovery/${name}?count=10&nonce=${Date.now()}`);
    // A slower response for a lens the user has already left must not overwrite the current one.
    if (requestId !== lensRequestId) return;
    const items = Array.isArray(data.items) ? data.items : [];
    target.replaceChildren(...items.map(buildLensRow));
    // Off is a neutral empty state with plain copy; the config key stays out of the UI.
    const message = items.length
      ? pluralize(items.length, 'album', 'albums') + ' · ' + label + ' · Fixed for today, rebuilt each morning'
      : data.disabled ? 'Daily picks are turned off in Settings.'
      : data.message || label + ' has no albums today.';
    status.textContent = message;
    setStatusState(status, items.length ? 'progress' : 'empty');
  } catch (error) {
    if (requestId !== lensRequestId) return;
    target.replaceChildren();
    status.textContent = label + ' could not be loaded: ' + error.message;
    setStatusState(status, 'error');
  }
}

document.querySelectorAll('[data-lens]').forEach(button =>
  button.addEventListener('click', () => loadLensList(button.dataset.lens)));

// Personal Discoveries rows (DESIGN_SYSTEM.md sections 8 and 9.4). The server returns these in its
// selection order, which balances categories and diversity styles; it is not a discovery_score
// order, so rows show a muted position and no red rank numeral. The status line names that basis.
// Dismiss and dismiss-artist go through the same feedback endpoint the old card used.
function buildPersonalRow(item, index) {
  return buildRecommendationRow(item, index + 1, {
    indexed: true,
    // Every row shows the artist bio, fetched when the row scrolls near the viewport.
    artistBio: true,
    meta: [
      categoryLine(item),
      item.discovery_category === 'unclassified' || item.genre_metadata_available === false
        ? 'Low confidence: genre data unavailable' : ''
    ],
    listName: 'personal',
    onDismiss: (artist, album, metadata, row) => sendFeedback('dismiss', artist, album, metadata, 'personal', row)
  });
}

// Add to your collection rows (DESIGN_SYSTEM.md sections 8 and 9.4). The server orders candidates
// by an exploration score that includes random jitter, and Load albums rotates them on the client,
// so the order is not a ranking. Rows show a muted position and no red rank numeral, and the
// status line says what the order is. Not for me goes through the server
// feedback endpoint for this list, as the old card did, and the artist bio follows the same
// connection-reason rule as the card.
function buildClassicsRow(item, index) {
  const hasBio = /Genre tags connect this artist to your established musical interests/i.test(item.reason || '');
  return buildRecommendationRow(item, index + 1, {
    indexed: true,
    artistBio: hasBio,
    meta: [
      categoryLabel(item.discovery_type || item.discovery_category || ''),
      item.anchor_artist ? 'Similar to: ' + item.anchor_artist : '',
      hasBio ? '' : item.reason
    ],
    listName: 'classics',
    onDismiss: (artist, album, metadata, row) => sendFeedback('dismiss', artist, album, metadata, 'classics', row)
  });
}

// Lazy artist bio for a card (Deep Dives, Discover cards, dashboard tiles). One request per artist
// (cached in artistBioRequests), made when the card nears the viewport; the paragraph stays hidden
// unless the API returns a bio. Text is set with textContent.
// Shows as much of the bio as fits the artwork square, ending at the last full stop that fits. When
// not even the first sentence fits, it is cut at a word with an ellipsis. Measured when the card is
// hovered or focused, because the box has no size until the card is laid out; the result is kept
// per box size, so a resize is re-fitted on the next hover.
function fitBioToArt(bio) {
  const full = bio.dataset.fullBio;
  const key = bio.clientWidth + 'x' + bio.clientHeight;
  if (!full || !bio.clientHeight || bio.dataset.fitKey === key) return;
  bio.dataset.fitKey = key;
  const fits = text => { bio.textContent = text; return bio.scrollHeight <= bio.clientHeight; };
  if (fits(full)) return;
  const ends = [];
  const sentenceEnd = /[.!?]["')\]]*(?=\s|$)/g;
  for (let match = sentenceEnd.exec(full); match; match = sentenceEnd.exec(full)) {
    if (!/\b(?:Mr|Mrs|Ms|Dr|St|Jr|Sr|vs|No)$/.test(full.slice(0, match.index))) ends.push(match.index + match[0].length);
  }
  const search = (candidates, build) => {
    let low = 0, high = candidates.length - 1, best = -1;
    while (low <= high) {
      const mid = (low + high) >> 1;
      if (fits(build(candidates[mid]))) { best = mid; low = mid + 1; } else high = mid - 1;
    }
    return best;
  };
  const sentence = search(ends, end => full.slice(0, end));
  if (sentence >= 0) { bio.textContent = full.slice(0, ends[sentence]); return; }
  const words = [];
  const wordEnd = /\S+/g;
  for (let match = wordEnd.exec(full); match; match = wordEnd.exec(full)) words.push(match.index + match[0].length);
  const word = search(words, end => full.slice(0, end).trimEnd() + '…');
  bio.textContent = word >= 0 ? full.slice(0, words[word]).trimEnd() + '…' : full;
}

// Phone only (the stylesheet shows the control under 620px; hover does not exist on a touch screen).
// "About" sits in the artwork's bottom-left corner and stays visible; each tap shows or hides the
// bio that overlays the artwork. The control is added once the bio has loaded, so a card without a
// bio has none.
function addAboutToggle(card, art, bio, fit) {
  if (art.querySelector(':scope > .about-toggle')) return;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'about-toggle';
  button.textContent = 'ⓘ';
  button.setAttribute('aria-label', 'About the artist');
  button.setAttribute('aria-pressed', 'false');
  button.addEventListener('click', event => {
    event.stopPropagation();
    const open = !card.classList.contains('is-bio-open');
    card.classList.toggle('is-bio-open', open);
    button.setAttribute('aria-pressed', String(open));
    if (open) fit();
  });
  art.append(button);
}

function attachCardArtistBio(card, container, artist) {
  // The paragraph keeps its two-line space while the bio loads, so the card does not jump.
  const bio = addTextElement(container, 'p', 'artist-bio is-pending', '');
  const loadBio = () => {
    if (card.dataset.bioRequested) return;
    card.dataset.bioRequested = 'true';
    const bioKey = artist.trim().toLocaleLowerCase();
    cachedBioRequest(bioKey, artist)
      .then(result => {
        if (!result || !result.bio) return;
        bio.textContent = result.bio;
        // The card clamps the bio; the full text stays available on hover.
        bio.title = result.bio;
        bio.classList.remove('is-pending');
        // A bio overlaid on the artwork is cut to the sentence that best fills the square.
        if (container.classList.contains('card-art')) {
          bio.dataset.fullBio = result.bio;
          const fit = () => fitBioToArt(bio);
          card.addEventListener('pointerenter', fit);
          card.addEventListener('focusin', fit);
          addAboutToggle(card, container, bio, fit);
        }
      })
      .catch(() => {});
  };
  bioLoaders.set(card, loadBio);
  if (artistBioObserver) artistBioObserver.observe(card);
  else loadBio();
}

// Lazy artist bio for a ranked row. Same contract as the editorial card: one request per artist
// (cached in artistBioRequests), made only when the row is near the viewport, and the paragraph
// stays hidden unless the API returns a bio. Text is set with textContent.
function attachArtistBio(row, container, artist) {
  const bio = addTextElement(container, 'p', 'artist-bio', '');
  bio.hidden = true;
  const loadBio = () => {
    if (row.dataset.bioRequested) return;
    row.dataset.bioRequested = 'true';
    const bioKey = artist.trim().toLocaleLowerCase();
    cachedBioRequest(bioKey, artist)
      .then(result => {
        if (!result || !result.bio) return;
        bio.textContent = result.bio;
        bio.hidden = false;
        // Rows stay one height. A bio that does not fit in its two lines can be clicked open.
        requestAnimationFrame(() => makeBioExpandable(row, bio));
      })
      .catch(() => {});
  };
  bioLoaders.set(row, loadBio);
  if (artistBioObserver) artistBioObserver.observe(row);
  else loadBio();
}

// Turns a clamped bio into a toggle that grows only its own row. Clicks and keys stop here so they
// do not also open the album modal.
function makeBioExpandable(row, bio) {
  if (bio.scrollHeight <= bio.clientHeight + 1) return;
  bio.classList.add('is-expandable');
  bio.setAttribute('role', 'button');
  bio.setAttribute('tabindex', '0');
  bio.setAttribute('aria-expanded', 'false');
  const toggle = () => {
    const open = row.classList.toggle('is-bio-open');
    bio.setAttribute('aria-expanded', String(open));
  };
  bio.addEventListener('click', event => { event.stopPropagation(); toggle(); });
  bio.addEventListener('keydown', event => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    event.preventDefault();
    event.stopPropagation();
    toggle();
  });
}

// "adventurous" is shown as "Adventurous discovery"; other categories keep their plain name.
function categoryLabel(category) {
  const name = String(category || '').replaceAll('_', ' ');
  return name === 'adventurous' ? 'Adventurous discovery' : name;
}

// An adjacent pick is named by the artists you play that share its genres ("Similar to: A, B");
// the server computes them. With none to name, or for any other category, the category label shows.
function categoryLine(item) {
  const similar = Array.isArray(item.similar_to) ? item.similar_to.filter(Boolean) : [];
  if (item.discovery_category === 'adjacent' && similar.length) return 'Similar to: ' + similar.join(', ');
  return categoryLabel(item.discovery_category);
}

// Discover music metadata lines. Each line appears only when the API returned the value.
function addRecommendationMeta(meta, item) {
  addTextElement(meta, 'p', 'row-meta-line row-category', categoryLine({...item, discovery_category: item.discovery_category || 'Unclassified'}));
  const genres = [...new Set([
    ...(Array.isArray(item.genres) ? item.genres : []),
    ...(Array.isArray(item.genre_families) ? item.genre_families : [])
  ])];
  if (genres.length) {
    const genreLine = addTextElement(meta, 'p', 'row-meta-line row-genres', '');
    linkGenres(genreLine, genres);
    genreLine.title = genres.join(' · ');
  }
  if (item.diversity_style) {
    addTextElement(meta, 'p', 'row-meta-line', 'Style: ' + item.diversity_style.replaceAll('_', ' '));
  }
  const listeners = item.lastfm_listeners;
  if (listeners !== null && listeners !== undefined && Number.isFinite(Number(listeners))) {
    addTextElement(meta, 'p', 'row-meta-line', 'Last.fm artist listeners: ' + Number(listeners).toLocaleString());
  }
  if (item.discovery_score !== null && item.discovery_score !== undefined && Number.isFinite(Number(item.discovery_score))) {
    addTextElement(meta, 'p', 'row-meta-line', 'Discovery score: ' + Number(item.discovery_score).toFixed(4));
  }
  if (item.discovery_source) {
    addTextElement(meta, 'p', 'row-meta-line row-source', 'Source: ' + item.discovery_source.replaceAll('_', ' '));
  }
}

$('recommendationSearch').addEventListener('input', applyRecommendationFilters);
$('categoryFilter').addEventListener('change', applyRecommendationFilters);
$('recommendationSort').addEventListener('change', () => reorderRecommendations(applyRecommendationFilters));

$('checkConnection').addEventListener('click', async () => {
  $('connection').textContent = 'Testing Navidrome…';
  await testServiceConnection('/api/settings/navidrome/test', 'connection');
});

// Loading variant of the ranked row (DESIGN_SYSTEM.md 9.6): same grid, opacity pulse only.
// Hidden from assistive tech; the count line above carries the loading status.
function skeletonRows(count) {
  return Array.from({length: Math.min(Math.max(count, 1), 20)}, () => {
    const row = document.createElement('div');
    row.className = 'ranked-row is-skeleton';
    row.setAttribute('aria-hidden', 'true');
    for (const cls of ['rank-numeral', 'skeleton-art', 'skeleton-main', 'skeleton-meta']) {
      const part = document.createElement('span');
      part.className = cls;
      row.append(part);
    }
    return row;
  });
}

$('loadRecommendations').addEventListener('click', async () => {
  const button = $('loadRecommendations');
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  allRecommendations = [];
  $('recommendationCount').textContent = 'Generating recommendations…';
  $('recommendationCards').replaceChildren(...(isMobileLayout() ? [] : skeletonRows(Number($('count').value) || 5)));
  $('recommendationDebug').textContent = '';
  try {
    const data = await requestJSON(
      '/api/recommendations?count=' + encodeURIComponent($('count').value));
    renderRecommendations(data);
  } catch (error) {
    // The failure is shown where the user is looking, not only in the diagnostics panel.
    $('recommendationCards').replaceChildren();
    $('recommendationCount').textContent = 'Recommendations could not be loaded: ' + error.message;
    $('recommendationDebug').textContent = error.message;
  } finally {
    button.disabled = false;
    button.removeAttribute('aria-busy');
  }
});

const discoveryViews = {
  personal: ['personalCards','personalStatus'],
  classics: ['classicsCards','classicsStatus'],
  artist_deep_dive: ['artistDeepDiveCards','artistDeepDiveStatus'],
  new_releases: ['newReleasesCards','newReleasesStatus'],
  // Lens rows: status for dismiss and Save errors. Lens lists reload through loadLensList.
  lens_lists: ['lensListsCards','lensListsStatus'],
  saved: ['savedCards','savedStatus']
};

const qualityOptions = [
  ['mp3_320','MP3 320 kbps'],
  ['mp3_193_319','MP3 193–319 kbps'],
  ['mp3_192','MP3 192 kbps'],
  ['flac_cd','FLAC (CD quality preferred)'],
  ['flac_16_44','FLAC 16-bit / 44.1 kHz'],
  ['flac_hires','FLAC Hi-Res (24-bit or above 44.1 kHz)']
];

async function sendJSON(url, method='POST', body={}) {
  const response = await fetch(url, {
    method,
    headers: {'Content-Type':'application/json'},
    body: method === 'GET' ? undefined : JSON.stringify(body)
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || data.message || `HTTP ${response.status}`);
  return data;
}

function discoveryStatus(name, message, kind) {
  // The dashboard picks, the New releases shelf and the radio log are not discovery views; each
  // reports on its own status line.
  const own = {dashboard_shelf: 'shelfNewReleasesStatus', radio: 'radioStatus'};
  const el = $(discoveryViews[name] ? discoveryViews[name][1] : own[name] || 'dashboardPicksStatus');
  el.textContent = message;
  setStatusState(el, kind === undefined ? classifyStatus(message) : kind);
}

// Derive a state kind from the text a caller already passes, so every existing
// message gains the right treatment without threading a second argument through
// every call site. Colour is never the only signal: the CSS pairs each kind with
// a distinct leading glyph as well.
function classifyStatus(message) {
  const text = String(message || '').trim();
  if (!text) return 'idle';
  if (/\b(error|could not|failed|unavailable|refus|denied|invalid|timed out|timed-out)\b/i.test(text)) return 'error';
  if (/\.\.\.|\u2026|loading|connecting|generating|rotating|building|checking|saving|refreshing|reconnecting/i.test(text)) return 'loading';
  if (/\bno\b|\bnone\b|nothing|empty/i.test(text)) return 'empty';
  return 'progress';
}

function setStatusState(el, kind) {
  if (!el) return;
  el.classList.remove('is-loading', 'is-empty', 'is-error', 'is-success', 'is-progress');
  if (kind && kind !== 'idle') el.classList.add('is-' + kind);
}

// The server decides each Deep Dives row (genre_row) and its display label.
function deepDiveGenre(item) {
  return String(item.genre_row || 'other');
}

function genreRowLabel(key, labels) {
  return (labels && labels.get(key)) || key.replaceAll('-', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
}

/** Icon from the vendored sprite (DESIGN_SYSTEM.md 10). The name is always a literal, so no
 *  markup is built from data; the element is created with DOM APIs, not innerHTML. */
function spriteIcon(name) {
  const svgNs = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNs, 'svg');
  svg.setAttribute('class', 'icon');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  const use = document.createElementNS(svgNs, 'use');
  use.setAttribute('href', '/static/icons.svg#' + name);
  svg.append(use);
  return svg;
}

/** ResizeObservers watching genre-row overflow, disconnected on every re-render. */
const genreRowObservers = [];
const genreRowResizeHandlers = [];

const laneArtworkObservers = new Map();

function laneArtworkObserver(track) {
  if (!laneArtworkObservers.has(track)) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const load = artworkLoaders.get(entry.target);
        if (load) load();
        observer.unobserve(entry.target);
      }
    }, {root: track, rootMargin: '0px 700px 0px 700px'});
    laneArtworkObservers.set(track, observer);
    genreRowObservers.push(observer);
  }
  return laneArtworkObservers.get(track);
}

function disconnectGenreRowObservers() {
  laneArtworkObservers.clear();
  while (genreRowObservers.length) genreRowObservers.pop().disconnect();
  while (genreRowResizeHandlers.length) {
    window.removeEventListener('resize', genreRowResizeHandlers.pop());
  }
}

async function loadDiscovery(name, options = {}) {
  discoveryStatus(name, options.rotate ? 'Rotating suggestions…' : 'Loading…');
  const target = $(discoveryViews[name][0]);
  // Observers outlive the nodes they watch unless disconnected here, so a section that is
  // reloaded repeatedly would accumulate them.
  disconnectGenreRowObservers();
  // The ranked-row lists show skeleton rows while they load (DESIGN_SYSTEM.md 9.6). They are
  // removed as soon as the response arrives, before any row is rendered, and on failure.
  const rankedRowList = name === 'new_releases' || name === 'personal' || name === 'classics';
  // On a phone these lists are rows of album cards that scroll sideways; the card row has no
  // skeleton, so the status line carries the loading state.
  const cardList = isMobileLayout() && rankedRowList;
  if (rankedRowList) setCardTrack(target, cardList);
  target.replaceChildren(...(rankedRowList ? skeletonRows(6) : []));
  if (cardList) target.replaceChildren();
  target.classList.toggle('deep-dive-rows', name === 'artist_deep_dive');
  const destinationByItem = new Map();

  try {
    const poolCount = name === 'artist_deep_dive' ? 150 : name === 'classics' ? 100 : 30;
    const data = await requestJSON(`/api/discovery/${name}?count=${poolCount}&nonce=${Date.now()}`);
    if (rankedRowList) target.replaceChildren();
    let items = data.items || data.recommendations || [];
    if (name !== 'for_me') items = items.filter(isAlbumRecommendation);
    if ((name === 'classics' || name === 'artist_deep_dive') && options.rotate) {
      items = [...items].sort(() => Math.random() - 0.5);
    }
    if (name === 'classics') {
      if (items.length > 30) items = items.slice(0, 30);
      const artistCounts = new Map();
      items = items.filter(item => {
        const key = String(item.artist || item.album_artist || '').trim().toLocaleLowerCase();
        const count = artistCounts.get(key) || 0;
        if (count >= 3) return false;
        artistCounts.set(key, count + 1);
        return true;
      });
    }
    if (name !== 'for_me' && !data.generated_at && !items.length && !autoRefreshStarted.has(name)) {
      autoRefreshStarted.add(name);
      discoveryStatus(name, 'Building the first list in the background…');
      try {
        await sendJSON(`/api/discovery/${name}/refresh`, 'POST', {count: 20});
        pollDiscoveryUntilReady(name);
      } catch (error) {
        autoRefreshStarted.delete(name);
        discoveryStatus(name, error.message);
      }
    }

    if (name === 'artist_deep_dive') {
      const grouped = new Map();
      const artistsByGenre = new Map();
      const rowLabels = new Map(items.map(item => [deepDiveGenre(item), item.genre_row_label]));
      for (const item of items) {
        const key = deepDiveGenre(item);
        const artistKey = String(item.artist || item.album_artist || '').trim().toLocaleLowerCase();
        if (!grouped.has(key)) {
          grouped.set(key, []);
          artistsByGenre.set(key, new Set());
        }
        const seenArtists = artistsByGenre.get(key);
        if (seenArtists.has(artistKey)) continue;
        seenArtists.add(artistKey);
        grouped.get(key).push(item);
      }
      // Show no more than 15 albums per genre row. Randomize the larger
      // saved pool first so Load albums can rotate choices without waiting
      // for expensive upstream metadata requests.
      for (const [genre, genreItems] of grouped) {
        if (genreItems.length > 15) {
          grouped.set(genre, genreItems.slice(0, 15));
        }
      }
      const orderedGroups = [...grouped.entries()].sort((a, b) =>
        (b[1].length - a[1].length) || a[0].localeCompare(b[0]));
      items = orderedGroups.flatMap(([, genreItems]) => genreItems);
      for (const [genre, genreItems] of orderedGroups) {
        const row = document.createElement('section');
        row.className = 'genre-row';
        const heading = document.createElement('div');
        heading.className = 'genre-row-heading';
        const genreTitle = addTextElement(heading, 'h3', '', '');
        genreTitle.append(buildInlineLink(genreRowLabel(genre, rowLabels), {type: 'genre', tag: String(genre).toLocaleLowerCase()}));
        addTextElement(heading, 'span', 'genre-row-count', pluralize(genreItems.length, 'album', 'albums'));
        const arrows = document.createElement('div');
        arrows.className = 'genre-row-arrows action-group';
        arrows.setAttribute('role', 'group');
        arrows.setAttribute('aria-label', genreRowLabel(genre, rowLabels) + ' scroll');
        const track = document.createElement('div');
        track.className = 'genre-row-track';
        makeScrollTrackFocusable(track, genreRowLabel(genre, rowLabels) + ' albums');
        const arrowList = [];
        for (const [icon, direction] of [['chevron-left', -1], ['chevron-right', 1]]) {
          const arrow = document.createElement('button');
          arrow.className = 'genre-row-arrow';
          arrow.type = 'button';
          arrow.append(spriteIcon(icon));
          arrow.title = direction < 0 ? 'Scroll albums left' : 'Scroll albums right';
          arrow.setAttribute('aria-label', arrow.title);
          arrow.addEventListener('click', () => scrollTrackBy(track, direction * trackScrollStep(track)));
          arrows.append(arrow);
          arrowList.push(arrow);
        }
        // A row that fits renders no usable scroll action. The arrows used to stay visible and
        // keyboard-focusable anyway, so a row of one to three albums put two dead controls in
        // the tab order that did nothing when activated. They are hidden and removed from the
        // tab order unless the track actually overflows, re-evaluated on resize and on content
        // change because neither is known at construction time.
        const syncArrows = () => {
          const overflows = track.scrollWidth > track.clientWidth + 1;
          arrows.hidden = !overflows;
          for (const arrow of arrowList) {
            if (overflows) arrow.removeAttribute('tabindex');
            else arrow.setAttribute('tabindex', '-1');
          }
        };
        track.addEventListener('scroll', syncArrows, {passive: true});
        if (typeof ResizeObserver === 'function') {
          const observer = new ResizeObserver(syncArrows);
          observer.observe(track);
          genreRowObservers.push(observer);
        } else {
          window.addEventListener('resize', syncArrows);
          genreRowResizeHandlers.push(syncArrows);
        }
        requestAnimationFrame(syncArrows);
        heading.append(arrows);
        row.append(heading, track);
        target.append(row);
        for (const item of genreItems) destinationByItem.set(item, track);
      }
    }

    if (items.length || data.generated_at) {
      const count = pluralize(items.length, 'item', 'items');
      discoveryStatus(name, name === 'new_releases' && items.length
        ? count + ' · Sorted by release date, newest first'
        : name === 'personal' && items.length
          ? count + ' · Engine order, not ranked by discovery score'
          : name === 'classics' && items.length
            ? count + ' · Picked for exploration, not ranked by score'
            : count);
    }

    for (const [index, item] of items.entries()) {
      if (cardList) {
        target.append({personal: buildPersonalCard, classics: buildClassicsCard, new_releases: buildNewReleaseCard}[name](item));
        continue;
      }
      if (name === 'personal') {
        target.append(buildPersonalRow(item, index));
        continue;
      }
      if (name === 'classics') {
        target.append(buildClassicsRow(item, index));
        continue;
      }
      if (name === 'new_releases') {
        target.append(buildNewReleaseRow(item));
        continue;
      }
      const artist = item.artist || item.album_artist || 'Unknown artist';
      const album = item.album || item.title || 'Untitled album';
      const isDeepDive = name === 'artist_deep_dive';
      const card = document.createElement('article');
      card.className = 'card editorial-card';
      makeAlbumCardInteractive(card, artist, album, item);
      attachArtwork(card, artist, album);

      // The category tag carries no information here: every card in this section is a deep
      // dive, and the row heading already names the genre. Rendering it on all of them was
      // repetition, not labelling, so proximity does the grouping instead of a tag per card.
      if (!isDeepDive) {
        addTextElement(card, 'p', 'card-category',
          categoryLabel(item.discovery_type || item.discovery_category || name));
      }
      const title = document.createElement('h3');
      // This section's task is artist-led: its own copy reads "Explore missing albums by
      // artists in your library". The artist therefore takes the card's heading role and the
      // album becomes the supporting line, rather than the reverse inherited from the
      // album-grid sections.
      if (isDeepDive) linkArtistName(title, artist);
      else linkAlbumName(title, artist, album, item);
      const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, card.dataset.releaseYear);
      if (year !== null && !isDeepDive) addAlbumYear(title, year, true);
      if (!isDeepDive) addAlbumListens(title, item, true);
      card.append(title);
      // Mirrors the swap above: with the artist in the heading, the supporting line carries
      // the album so no information is lost or duplicated.
      const supportingLine = addTextElement(card, 'p', 'card-artist', '');
      if (isDeepDive) linkAlbumName(supportingLine, artist, album, item);
      else linkArtistName(supportingLine, artist);
      if (isDeepDive) card.dataset.yearTarget = 'supporting';
      // Keep release-year metadata with the album when the artist is the primary heading.
      if (year !== null && isDeepDive) addAlbumYear(supportingLine, year, true);
      if (isDeepDive) addAlbumListens(supportingLine, item, true);
      ensureAlbumYearBadge(card);

      const needsBio = isDeepDive ||
        /Genre tags connect this artist to your established musical interests/i.test(item.reason || '');
      // The bio overlays the artwork on hover, so it takes no room in the card's text.
      attachCardArtistBio(card, card.querySelector('.card-art'), artist);

      if (item.reason && !needsBio) addTextElement(card, 'p', 'card-meta', item.reason);
      if (item.anchor_artist) addTextElement(card, 'p', 'card-meta',
        `Similar to: ${item.anchor_artist}`);

      // The group sits at the foot of the card, below the last line of text.
      card.append(createActionGroup(artist, album, item, {
        listName: name,
        onDismiss: () => sendFeedback('dismiss', artist, album, item, name, card)
      }));
      const destination = destinationByItem.get(item) || target;
      destination.append(card);
      // A lane scrolls sideways, and the page-wide artwork observer cannot see past the lane's own
      // edge. Observing against the lane itself starts the next few covers before they scroll in.
      const art = card.querySelector('.card-art');
      if (art && destination !== target && 'IntersectionObserver' in window) {
        laneArtworkObserver(destination).observe(art);
      }
    }

    // Each section explains its own precondition and names the action that resolves it,
    // rather than sharing one generic string. clarify.md requires an empty state to explain
    // the state and offer the next useful action, and these sections need different things
    // before they can return results: new releases needs a full album already in the
    // library, the artist and library views need a connected Navidrome, and the personal
    // view needs listening history. One shared sentence could only ever name the symptom.
    if (!items.length && !autoRefreshStarted.has(name)) {
      const emptyCopy = {
        new_releases: 'No new releases found. This view lists albums from the last 24 months by artists who already have a full album in your library, so it needs a connected Navidrome library to find candidates.',
        personal: 'No personal discoveries yet. These recommendations are based on your listening history, so they need Last.fm or ListenBrainz configured in Settings before there is anything to work from.',
        classics: 'No albums to add yet. This view looks for acclaimed albums missing from your library, so it needs a connected Navidrome library to compare against.',
        artist_deep_dive: 'No deep dives yet. This view finds missing albums by artists already in your library, so it needs a connected Navidrome library to find them.'
      }[name] || 'No results for this list yet.';
      const empty = addTextElement(target, 'p', 'status-line', emptyCopy);
      setStatusState(empty, 'empty');
    }
  } catch (error) {
    if (rankedRowList) target.replaceChildren();
    discoveryStatus(name, error.message);
  }
}

// Dismiss is reversible for a short window (see queueDismiss). Nothing is sent to the server
// until the window closes, so Undo never has to reverse a server change.
async function sendFeedback(action, artist, album, metadata, listName, row = null, restore = null) {
  if (action === 'dismiss' || action === 'dismiss_artist') {
    queueDismiss(action, artist, album, metadata, listName, row, restore);
    return;
  }
  try {
    await sendJSON('/api/discovery/feedback', 'POST',
      {action, artist, album, metadata});
    await loadDiscovery(listName);
  } catch (error) {
    discoveryStatus(listName, error.message);
  }
}

// Undo window for dismissals. The row leaves the list at once, a snackbar offers Undo, and the
// POST to /api/discovery/feedback is sent only when the window closes. Undo cancels it. Only
// one dismissal waits at a time; a second one commits the first immediately.
const UNDO_WINDOW_MS = 4200;
let pendingDismiss = null;

function queueDismiss(action, artist, album, metadata, listName, row, restore = null) {
  if (pendingDismiss) commitDismiss();
  const label = action === 'dismiss_artist'
    ? 'Dismissed artist ' + artist + '.'
    : 'Dismissed ' + album + (artist ? ' by ' + artist : '') + '.';
  const entry = {action, artist, album, metadata, listName, row, restore, timer: null};
  if (row) {
    // Keyboard focus would be lost when the row hides, so it moves to the page heading first.
    if (row.contains(document.activeElement)) {
      const heading = document.querySelector('section.page:not(.hidden) h2');
      if (heading) { heading.tabIndex = -1; heading.focus(); }
    }
    row.classList.add('is-dismissing');
  }
  entry.timer = setTimeout(commitDismiss, UNDO_WINDOW_MS);
  pendingDismiss = entry;
  showUndoSnackbar(label);
}

async function commitDismiss() {
  const entry = pendingDismiss;
  if (!entry) return;
  pendingDismiss = null;
  clearTimeout(entry.timer);
  hideUndoSnackbar();
  try {
    await sendJSON('/api/discovery/feedback', 'POST',
      {action: entry.action, artist: entry.artist, album: entry.album, metadata: entry.metadata});
    // Lens rows are not in discoveryViews; they reload the lens that is on screen.
    if (entry.listName === 'lens_lists') await loadLensList(activeLens);
    else if (!['dashboard_picks', 'dashboard_shelf'].includes(entry.listName)) await loadDiscovery(entry.listName);
  } catch (error) {
    if (entry.row) entry.row.classList.remove('is-dismissing');
    if (entry.restore) entry.restore();
    if (entry.listName === 'lens_lists') {
      const status = $('lensListsStatus');
      status.textContent = error.message;
      setStatusState(status, 'error');
    } else {
      discoveryStatus(entry.listName, error.message);
    }
  }
}

function undoDismiss() {
  const entry = pendingDismiss;
  if (!entry) return;
  pendingDismiss = null;
  clearTimeout(entry.timer);
  const undoButton = $('undoSnackbarAction');
  const hadFocus = !!undoButton && undoButton.contains(document.activeElement);
  if (entry.row) {
    entry.row.classList.remove('is-dismissing');
    if (entry.restore) entry.restore();
    // The snackbar hides on this click, so focus moves back to the restored row first.
    if (hadFocus) { const first = entry.row.querySelector('button'); if (first) first.focus(); }
  }
  hideUndoSnackbar();
  const announcer = $('appStatusAnnouncer');
  if (announcer) announcer.textContent = 'Restored. The dismissal was not sent.';
}

function showUndoSnackbar(message) {
  const bar = $('undoSnackbar');
  if (!bar) return;
  $('undoSnackbarText').textContent = message;
  const timer = $('undoSnackbarTimer');
  // Restart the drain on every show. Reflow between the two class changes makes the animation run again.
  timer.style.animationDuration = UNDO_WINDOW_MS + 'ms';
  timer.classList.remove('is-running');
  void timer.offsetWidth;
  timer.classList.add('is-running');
  bar.inert = false;
  bar.classList.add('is-open');
  // The announcer is always present in the DOM, so the message is spoken exactly once here.
  const announcer = $('appStatusAnnouncer');
  if (announcer) announcer.textContent = message + ' Undo is available for a few seconds.';
}

function hideUndoSnackbar() {
  const bar = $('undoSnackbar');
  if (!bar) return;
  bar.classList.remove('is-open');
  bar.inert = true;
}

if ($('undoSnackbarAction')) $('undoSnackbarAction').addEventListener('click', undoDismiss);

// One joined control for the actions on an album (Get, Save, Not for me), shared by the ranked
// rows and the editorial cards. The buttons keep their own behavior, state and accessible names;
// the group only seats them side by side. An album already in the library has no Get, a list
// without a `listName` has no Save, and a missing `onDismiss` leaves out Not for me.
function createActionGroup(artist, album, metadata, options = {}) {
  const group = document.createElement('div');
  group.className = 'action-group';
  group.setAttribute('role', 'group');
  group.setAttribute('aria-label', 'Actions for ' + album);
  // `getButton` lets a list with its own request flow (the radio log) seat that button instead.
  if (options.getButton) group.append(options.getButton);
  else if (!options.owned) group.append(createGetButton(artist, album, metadata));
  if (options.listName) group.append(createSaveButton(artist, album, metadata, options.listName));
  if (options.onDismiss) {
    const dismissButton = document.createElement('button');
    dismissButton.type = 'button';
    dismissButton.className = 'dismiss-album';
    dismissButton.append(spriteIcon('trash-2'));
    dismissButton.title = options.dismissTitle || 'Not for me';
    dismissButton.setAttribute('aria-label', options.dismissLabel || 'Not for me: ' + album);
    dismissButton.addEventListener('click', options.onDismiss);
    group.append(dismissButton);
  }
  return group;
}

// A lone control seated in the action group's frame, so a Get on its own matches the group.
function wrapInActionGroup(control, label) {
  const group = document.createElement('div');
  group.className = 'action-group';
  group.setAttribute('role', 'group');
  if (label) group.setAttribute('aria-label', label);
  group.append(control);
  return group;
}

// Save is a bookmark: the server stores the album and its metadata and starts no search, so
// nothing here touches /api/acquire. The list is deliberately not reloaded. The list endpoints
// hide saved albums, so a reload would remove the card the user just saved and take Undo with
// it. The control updates in place instead and the album leaves the list on the next load.
function setSaveButtonState(button, saved, album, busy = false, failed = false) {
  button.classList.toggle('is-saved', saved);
  button.classList.toggle('is-failed', failed);
  button.setAttribute('aria-pressed', saved ? 'true' : 'false');
  button.toggleAttribute('aria-busy', busy);
  button.replaceChildren(spriteIcon(saved ? 'bookmark-check' : 'bookmark'));
  addTextElement(button, 'span', 'save-album-label', failed ? 'Retry' : saved ? 'Saved' : 'Save');
  button.title = failed
    ? 'Could not ' + (saved ? 'undo the save' : 'save') + '. Try again: ' + album
    : saved ? 'Saved as a bookmark. Select to undo: ' + album : 'Save as a bookmark: ' + album;
}

function createSaveButton(artist, album, metadata, listName) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'save-album';
  // The name stays constant and aria-pressed carries the state, so a screen reader hears
  // "Save <album>, toggle button, pressed" rather than a name that changes under it.
  button.setAttribute('aria-label', 'Save ' + album);
  setSaveButtonState(button, false, album);
  button.addEventListener('click', async () => {
    if (button.getAttribute('aria-busy') === 'true') return;
    // The state the server last confirmed. It is what the button shows while the request is in
    // flight and what it returns to if the request fails.
    const wasSaved = button.getAttribute('aria-pressed') === 'true';
    setSaveButtonState(button, wasSaved, album, true);
    try {
      const data = await sendJSON('/api/discovery/feedback', 'POST',
        {action: wasSaved ? 'remove_for_me' : 'save', artist, album, metadata});
      if (data && data.ok === false) throw new Error(data.error || 'The server did not save this album.');
      setSaveButtonState(button, !wasSaved, album);
    } catch (error) {
      setSaveButtonState(button, wasSaved, album, false, true);
      discoveryStatus(listName, error.message || 'Could not update the bookmark.');
    }
  });
  return button;
}

// Saved page: the albums bookmarked with Save, read from the For Me list. A row stays after Remove
// so the bookmark can be restored; it leaves the list on the next visit or Refresh (same rule as
// the Save control on the other lists). Saved albums already in the library show no Get button.
function formatSavedDate(seconds) {
  const date = new Date(Number(seconds) * 1000);
  if (!Number.isFinite(date.getTime())) return '';
  return 'Saved ' + monthAbbreviations[date.getMonth()] + ' ' + date.getDate() + ', ' + date.getFullYear();
}

function buildSavedRow(entry, index) {
  const item = {...(entry.metadata || {}), artist: entry.artist, album: entry.album};
  const owned = entry.acquired === true;
  return buildRecommendationRow(item, index + 1, {
    indexed: true,
    saved: true,
    owned,
    listName: 'saved',
    meta: [formatSavedDate(entry.saved_at), owned ? 'Already in your library' : '']
  });
}

async function loadSaved() {
  const target = $('savedCards');
  discoveryStatus('saved', 'Loading saved albums…', 'loading');
  const asCards = isMobileLayout();
  setCardTrack(target, asCards);
  target.replaceChildren(...(asCards ? [] : skeletonRows(4)));
  try {
    const data = await requestJSON('/api/discovery/for_me?count=150&nonce=' + Date.now());
    const entries = data.items || [];
    target.replaceChildren();
    if (!entries.length) {
      discoveryStatus('saved', '', 'idle');
      const empty = addTextElement(target, 'p', 'status-line',
        'Nothing saved yet. Select Save on any album in Personal Discoveries, New releases or the other lists to keep it here.');
      setStatusState(empty, 'empty');
      return;
    }
    const total = Number(data.total) || entries.length;
    discoveryStatus('saved', total > entries.length
      ? 'Showing ' + entries.length + ' of ' + total + ' saved albums · Newest first'
      : pluralize(entries.length, 'saved album', 'saved albums') + ' · Newest first', 'idle');
    for (const [index, entry] of entries.entries()) target.append(asCards ? buildSavedCard(entry) : buildSavedRow(entry, index));
  } catch (error) {
    target.replaceChildren();
    discoveryStatus('saved', 'Saved albums could not be loaded: ' + error.message);
  }
}

document.querySelectorAll('[data-refresh-saved]').forEach(button =>
  button.addEventListener('click', loadSaved));

async function refreshDiscovery(name) {
  discoveryStatus(name, 'Starting a fresh discovery pass…');
  try {
    const before = await requestJSON(`/api/discovery/${name}?count=1&nonce=${Date.now()}`);
    const previous = Number(before.generated_at || 0);
    const started = await sendJSON(`/api/discovery/${name}/refresh`, 'POST', {count:20});
    if (started.status === 'already_running') {
      discoveryStatus(name, 'A refresh is already running; waiting for its new results…');
    } else {
      discoveryStatus(name, 'Generating fresh suggestions. This may take a few minutes…');
    }
    const deadline = Date.now() + 5 * 60 * 1000;
    while (Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 2500));
      const current = await requestJSON(`/api/discovery/${name}?count=1&nonce=${Date.now()}`);
      const stamp = Number(current.generated_at || 0);
      if (stamp > previous) {
        await loadDiscovery(name, {rotate: true});
        if ($('dashboard').classList.contains('hidden') === false) loadDashboardPicks();
        return;
      }
    }
    discoveryStatus(name, 'The refresh is still running. Try Load albums again in a little while.');
  } catch (error) {
    discoveryStatus(name, error.message);
  }
}

document.querySelectorAll('[data-load-discovery]').forEach(button =>
  button.addEventListener('click', async () => {
    const name = button.dataset.loadDiscovery;
    if (name === 'classics' || name === 'artist_deep_dive') {
      await loadDiscovery(name, {rotate: true});
    } else {
      await loadDiscovery(name);
    }
  }));

document.querySelectorAll('[data-refresh-discovery]').forEach(button =>
  button.addEventListener('click', () => refreshDiscovery(button.dataset.refreshDiscovery)));

const autoRefreshStarted = new Set();
const autoRefreshPolls = new Map();

async function pollDiscoveryUntilReady(name) {
  const attempts = autoRefreshPolls.get(name) || 0;
  if (attempts >= 60) {
    discoveryStatus(name, 'Still generating in the background. You can keep browsing; reload this list later.');
    autoRefreshStarted.delete(name);
    autoRefreshPolls.delete(name);
    return;
  }
  autoRefreshPolls.set(name, attempts + 1);
  setTimeout(async () => {
    try {
      const data = await requestJSON(`/api/discovery/${name}?count=${name === 'artist_deep_dive' ? 150 : 30}`);
      if (data.generated_at) {
        autoRefreshStarted.delete(name);
        autoRefreshPolls.delete(name);
        await loadDiscovery(name, {rotate: name === 'classics' || name === 'artist_deep_dive'});
        loadDashboardPicks();
      } else {
        await pollDiscoveryUntilReady(name);
      }
    } catch (error) {
      discoveryStatus(name, error.message);
    }
  }, 5000);
}

// One get/request control, used by the modal, the artwork overlay and the card
// actions. Consolidates five former creation sites that each repeated the same
// label, title and aria attributes and could drift apart.
//
// States: idle -> pending -> requested, or idle -> pending -> failed. "pending" is
// applied while the request is in flight so the control never claims success before
// the server confirms; "requested" is applied only after a successful response.
// The Get button is a fixed-size circle — 44px in card actions, 46px over artwork, 58px in the
// dialog — so its state lives in an icon slot rather than in a word: "requested" is nine
// characters at 11px mono, wider than the 44px button it has to fit. Static markup with no
// interpolation, so no user-controlled string reaches innerHTML. The arc carries no pathLength,
// because its dash pattern is written in real user units. The tick carries pathLength, and its
// entrance is a transform and opacity transition (static/app.css), not a dash offset.
const GET_BUTTON_ICON =
  '<svg class="get-album-glyph" viewBox="0 0 44 44" aria-hidden="true" focusable="false"' +
  ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">' +
  '<circle class="get-album-arc" cx="22" cy="22" r="11.5"/>' +
  '<path class="get-album-tick" d="M14.5 22.6 19.6 27.7 29.5 16.4" pathLength="1"/>' +
  '<path class="get-album-arrow" d="M30.8 15.2A11 11 0 1 0 33 22"/>' +
  '<path class="get-album-arrow-head" d="M25.9 16.9 30.9 15.1 29.1 20.1"/>' +
  '<path class="get-album-down" d="M22 11.5V25M15.8 19.3 22 25.5l6.2-6.2"/>' +
  '<path class="get-album-tray" d="M13.5 28v4h17v-4"/>' +
  '<g class="get-album-cloud" transform="scale(1.8333)" stroke-width="1.5" stroke-linejoin="round">' +
  '<path d="M12 9.75v6.75m0 0-3-3m3 3 3-3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75z"/>' +
  '</g>' +
  '</svg>';

function decorateGetButton(button) {
  if (button.dataset.getDecorated) return button;
  button.dataset.getDecorated = 'true';
  const label = document.createElement('span');
  label.className = 'get-album-label';
  label.textContent = (button.textContent || '').trim() || 'get';
  button.textContent = '';
  button.insertAdjacentHTML('afterbegin', GET_BUTTON_ICON);
  button.append(label);
  return button;
}

// The word is only shown when idle. In every other state the icon slot carries the state and the
// accessible name carries it for assistive tech, so the face never depends on reading a word that
// does not fit.
function setGetButtonLabel(button, text) {
  decorateGetButton(button).querySelector('.get-album-label').textContent = text;
}

function createGetButton(artist, album, metadata) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'get-album';
  decorateGetButton(button);
  setGetButtonState(button, 'idle', artist, album);
  button.addEventListener('click', () => searchAlbum(artist, album, metadata, button));
  return button;
}

function setGetButtonState(button, state, artist, album) {
  if (!button) return;
  button.classList.remove('is-pending', 'requested', 'is-failed');
  button.removeAttribute('aria-busy');
  if (state === 'pending') {
    button.disabled = true;
    button.classList.add('is-pending');
    setGetButtonLabel(button, '');
    button.title = album ? 'Requesting ' + album : 'Requesting';
    button.setAttribute('aria-label', button.title);
    button.setAttribute('aria-busy', 'true');
  } else if (state === 'requested') {
    button.disabled = true;
    button.classList.add('requested');
    setGetButtonLabel(button, '');
    button.title = album ? 'Acquisition requested: ' + album : 'Acquisition requested';
    button.setAttribute('aria-label', button.title);
  } else if (state === 'failed') {
    // Usable again immediately: the user can retry without a reload.
    button.disabled = false;
    button.classList.add('is-failed');
    setGetButtonLabel(button, '');
    button.title = album ? 'Request failed. Try again: ' + album : 'Request failed. Try again';
    button.setAttribute('aria-label', button.title);
  } else {
    const noun = button.dataset.noun || 'album';
    button.disabled = false;
    setGetButtonLabel(button, 'get');
    button.title = 'Get this ' + noun;
    button.setAttribute('aria-label', album ? 'Get ' + album : 'Get this ' + noun);
  }
}

// Transient acquisition feedback. Notyf is vendored under static/vendor/notyf; that
// directory's README records the pinned version, integrity hashes and update procedure.
// Errors are held longer than successes because the status line that also carries them is
// easy to overwrite, while a failure is the message a user is most likely to need again.
const acquisitionToasts = typeof Notyf === 'function'
  ? new Notyf({
      ripple: false,
      dismissible: false,
      position: {x: 'right', y: 'bottom'},
      // Only the surface colour and duration are overridden. registerTypes merges each entry
      // over the default for that type, so the built-in class names and icon markup survive.
      // Motion is handled in app.css so reduced-motion preferences are respected.
      types: [
        {type: 'success', backgroundColor: 'var(--surface-raised)', duration: 5000},
        {type: 'error', backgroundColor: 'var(--surface-raised)', duration: 8000}
      ]
    })
  : null;

if (acquisitionToasts) {
  // Visual channel only. Every message is announced exactly once by the live region chosen
  // below, so the toast container is hidden from assistive tech and Notyf's built-in
  // announcer — which would otherwise speak each message a second time — is switched off.
  acquisitionToasts.view.container.setAttribute('aria-hidden', 'true');
  acquisitionToasts.view.a11yContainer.setAttribute('aria-live', 'off');
}

async function searchAlbum(artist, album, metadata, button = null) {
  if (button && button.disabled && !button.classList.contains('is-failed')) return;
  // A disabled control cannot keep focus, so disabling the Get that has focus dropped the
  // keyboard user onto <body>. Focus moves to the nearest stable owner (the card, or the
  // dialog's close button) while the request is in flight, and returns to Get if it fails.
  const hadFocus = !!button && document.activeElement === button;
  const focusOwner = hadFocus ? getFocusOwner(button) : null;
  // Pending, not requested. The former code marked the button as requested before
  // awaiting the response, which claimed success the server had not confirmed.
  setGetButtonState(button, 'pending', artist, album);
  if (focusOwner) focusOwner.focus();
  try {
    const data = await sendJSON('/api/acquire', 'POST',
      {artist, album, metadata, auto_queue:true});
    // This endpoint can answer 200 with ok:false and an explanatory message, for
    // example when no slskd API key is configured. Treating every 2xx as success
    // would mark the button "requested" for a request that was never made.
    if (data && data.ok === false) {
      setGetButtonState(button, 'failed', artist, album);
      if (hadFocus) button.focus();
      reportAcquisitionOutcome(data.message || data.error || 'The request could not be placed.', 'error');
      return;
    }
    setGetButtonState(button, 'requested', artist, album);
    reportAcquisitionOutcome(data && data.message, 'success');
    // Keep the user on the current page. Acquisition cards are shown only in the Acquisitions view.
    await loadAcquisitions();
  } catch (error) {
    setGetButtonState(button, 'failed', artist, album);
    if (hadFocus) button.focus();
    reportAcquisitionOutcome(error.message, 'error');
  }
}

// The control to hold focus while a Get request is in flight: the album dialog's close button
// inside the modal, otherwise the card or row that owns the Get control.
function getFocusOwner(button) {
  if (button.closest('.album-modal')) return $('albumModalClose');
  const owner = button.closest('[tabindex="0"]') || button.closest('article');
  // Dashboard tiles are articles without a tab stop of their own; -1 makes them focusable by
  // script only and leaves the tab order unchanged.
  if (owner && !owner.hasAttribute('tabindex')) owner.setAttribute('tabindex', '-1');
  return owner;
}

// Route acquisition feedback to a status region that actually exists. Two former
// problems are fixed here: the selector was '.page:not(.hidden) .status', which matched
// nothing outside Settings, and the Recommendations section has no .status-line at all,
// so its messages had nowhere to land either.
// Complete messages rather than a parenthesised pseudo-plural. clarify.md asks for
// translatable whole sentences and for pluralization to be handled rather than faked, and
// "1 item(s)" reads as a fragment to a person as well as to a translator.
function pluralize(count, singular, plural) {
  return count + ' ' + (count === 1 ? singular : plural);
}

function reportAcquisitionOutcome(message, kind) {
  if (!message) return;
  if (acquisitionToasts) acquisitionToasts[kind === 'error' ? 'error' : 'success'](message);
  // Announce through exactly one live region: the active view's own status line when it has
  // one, otherwise the shared #appStatusAnnouncer. Views without a status line previously
  // received no feedback at all, which is the defect the selector comment above describes.
  const page = document.querySelector('section.page:not(.hidden)');
  const target = page && (page.querySelector('.status-line') || page.querySelector('.muted[aria-live]'));
  const liveRegion = target || $('appStatusAnnouncer');
  if (!liveRegion) return;
  liveRegion.textContent = message;
  if (target) setStatusState(target, kind);
}
// Get one song of an album. The server chooses the file and files it with the album.
async function searchTrack(song, button) {
  if (button.disabled && !button.classList.contains('is-failed')) return;
  const hadFocus = document.activeElement === button;
  setGetButtonState(button, 'pending', song.artist, song.title);
  if (hadFocus) button.parentElement.focus();
  try {
    const data = await sendJSON('/api/acquire/track', 'POST', {
      artist: song.artist, album: song.album, title: song.title,
      track_number: song.track_number || undefined, year: song.year || undefined,
    });
    if (data && data.ok === false) {
      setGetButtonState(button, 'failed', song.artist, song.title);
      if (hadFocus) button.focus();
      reportAcquisitionOutcome(data.message || data.error || 'The request could not be placed.', 'error');
      return;
    }
    // A search that finds nothing is a finished request, not a pending one: Get stays usable.
    if (data && data.status === 'no_matches') {
      setGetButtonState(button, 'failed', song.artist, song.title);
      if (hadFocus) button.focus();
      reportAcquisitionOutcome(data.message, 'error');
      await loadAcquisitions();
      return;
    }
    setGetButtonState(button, 'requested', song.artist, song.title);
    reportAcquisitionOutcome(data && data.message, 'success');
    await loadAcquisitions();
  } catch (error) {
    setGetButtonState(button, 'failed', song.artist, song.title);
    if (hadFocus) button.focus();
    reportAcquisitionOutcome(error.message, 'error');
  }
}

function createTrackGetButton(song) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'get-album get-track';
  button.dataset.noun = 'song';
  decorateGetButton(button);
  setGetButtonState(button, 'idle', song.artist, song.title);
  button.addEventListener('click', () => searchTrack(song, button));
  return button;
}

async function loadNavidromeSettings() {
  try {
    const data = await requestJSON('/api/settings/navidrome');
    $('navidromeUrl').value = data.navidrome_url || '';
    $('navidromeUser').value = data.username || '';
    $('musicLibraryPath').value = data.music_library_path || '';
    $('navidromePassword').value = '';
    $('navidromeStatus').textContent = data.password_configured ? 'Password configured.' : 'Password not configured.';
    setStatusState($('navidromeStatus'), classifyStatus($('navidromeStatus').textContent));
  } catch (error) { $('navidromeStatus').textContent = error.message; setStatusState($('navidromeStatus'), 'error'); }
}
$('saveNavidrome').addEventListener('click', async () => {
  try {
    const result = await sendJSON('/api/settings/navidrome', 'PUT', {
      navidrome_url: $('navidromeUrl').value.trim(),
      username: $('navidromeUser').value.trim(),
      password: $('navidromePassword').value,
      music_library_path: $('musicLibraryPath').value.trim()
    });
    $('navidromePassword').value = '';
    $('navidromeStatus').textContent = result.message || 'Settings saved.';
    setStatusState($('navidromeStatus'), 'success');
    await loadNavidromeSettings();
  } catch (error) { $('navidromeStatus').textContent = error.message; setStatusState($('navidromeStatus'), 'error'); }
});

async function loadLastfmSettings() {
  try {
    const data = await requestJSON('/api/settings/lastfm');
    $('lastfmUsername').value = data.username || '';
    $('lastfmApiKey').value = '';
    $('lastfmStatus').textContent = data.api_key_configured ? 'API key configured.' : 'API key not configured (optional).';
    setStatusState($('lastfmStatus'), classifyStatus($('lastfmStatus').textContent));
  } catch (error) { $('lastfmStatus').textContent = error.message; setStatusState($('lastfmStatus'), 'error'); }
}
$('saveLastfm').addEventListener('click', async () => {
  try {
    const result = await sendJSON('/api/settings/lastfm', 'PUT', {
      api_key: $('lastfmApiKey').value,
      username: $('lastfmUsername').value.trim()
    });
    $('lastfmApiKey').value = '';
    $('lastfmStatus').textContent = result.message || 'Settings saved.';
    setStatusState($('lastfmStatus'), 'success');
    await loadLastfmSettings();
  } catch (error) { $('lastfmStatus').textContent = error.message; setStatusState($('lastfmStatus'), 'error'); }
});

async function loadListenbrainzSettings(keepStatus = false) {
  try {
    const data = await requestJSON('/api/settings/listenbrainz');
    $('listenbrainzUsername').value = data.username || '';
    $('listenbrainzToken').value = '';
    if (keepStatus) return;
    $('listenbrainzStatus').textContent = data.token_configured ? 'Username set. User token configured.' : 'Username set. User token not configured (optional).';
    setStatusState($('listenbrainzStatus'), 'idle');
  } catch (error) { $('listenbrainzStatus').textContent = error.message; setStatusState($('listenbrainzStatus'), 'error'); }
}
$('saveListenbrainz').addEventListener('click', async () => {
  try {
    const result = await sendJSON('/api/settings/listenbrainz', 'PUT', {
      username: $('listenbrainzUsername').value.trim(),
      token: $('listenbrainzToken').value.trim()
    });
    $('listenbrainzToken').value = '';
    $('listenbrainzStatus').textContent = result.message || 'Settings saved.';
    setStatusState($('listenbrainzStatus'), 'success');
    await loadListenbrainzSettings(true);
  } catch (error) { $('listenbrainzStatus').textContent = error.message; setStatusState($('listenbrainzStatus'), 'error'); }
});

const DISCOGS_SOURCE_LABELS = {
  settings: 'Token configured.',
  environment: 'Token configured from the DISCOGS_TOKEN environment variable.',
  none: 'Token not configured (optional).'
};
async function loadDiscogsSettings(keepStatus = false) {
  try {
    const data = await requestJSON('/api/settings/discogs');
    $('discogsToken').value = '';
    if (keepStatus) return;
    $('discogsStatus').textContent = DISCOGS_SOURCE_LABELS[data.source] || DISCOGS_SOURCE_LABELS.none;
    setStatusState($('discogsStatus'), 'idle');
  } catch (error) { $('discogsStatus').textContent = error.message; setStatusState($('discogsStatus'), 'error'); }
}
// An empty token clears the saved one; the Save button never sends an empty field.
async function saveDiscogsToken(token) {
  try {
    const result = await sendJSON('/api/settings/discogs', 'PUT', {token});
    $('discogsToken').value = '';
    $('discogsStatus').textContent = (token ? 'Token saved. ' : 'Saved token removed. ') + (DISCOGS_SOURCE_LABELS[result.source] || '');
    setStatusState($('discogsStatus'), 'success');
  } catch (error) { $('discogsStatus').textContent = error.message; setStatusState($('discogsStatus'), 'error'); }
}
$('saveDiscogs').addEventListener('click', () => {
  const token = $('discogsToken').value.trim();
  if (!token) {
    $('discogsStatus').textContent = 'Enter a token to save, or use Remove saved token.';
    setStatusState($('discogsStatus'), 'error');
    return;
  }
  saveDiscogsToken(token);
});
$('removeDiscogs').addEventListener('click', () => saveDiscogsToken(''));

async function testServiceConnection(endpoint, statusId) {
  const status = $(statusId);
  status.textContent = 'Testing connection…';
  setStatusState(status, 'loading');
  try {
    const data = await sendJSON(endpoint, 'POST');
    status.textContent = data.message || data.error || (data.ok ? 'Connection successful.' : 'Test failed.');
    setStatusState(status, data.ok ? 'success' : 'error');
  } catch (error) {
    status.textContent = error.message;
    setStatusState(status, 'error');
  }
}
$('testLastfm').addEventListener('click', () => testServiceConnection('/api/settings/lastfm/test', 'lastfmStatus'));
$('testListenbrainz').addEventListener('click', () => testServiceConnection('/api/settings/listenbrainz/test', 'listenbrainzStatus'));
$('testDiscogs').addEventListener('click', () => testServiceConnection('/api/settings/discogs/test', 'discogsStatus'));

// Complete the tabs pattern. The markup already had role=tablist/tab/tabpanel and
// aria-controls, but the widget was missing the two halves that make it operable rather than
// merely announced: panels had no accessible name, and every tab was its own Tab stop with no
// arrow-key navigation. A keyboard user had to Tab through all four tabs to leave the group,
// which is the behaviour the pattern exists to avoid.
//
// Roving tabindex: exactly one tab is tabbable (the selected one). The others are reachable
// with the arrow keys, Home and End, per the tabs pattern. Activation follows focus, so an
// arrow key both moves focus and switches panel.
const settingsTabs = [...document.querySelectorAll('[data-settings-tab]')];
const settingsPanels = {
  navidrome: 'settingsNavidrome', slskd: 'settingsSlskd',
  lastfm: 'settingsLastfm', listenbrainz: 'settingsListenbrainz', discogs: 'settingsDiscogs'
};

function selectSettingsTab(button, moveFocus = true) {
  if (!button) return;
  const name = button.dataset.settingsTab;
  for (const tab of settingsTabs) {
    const active = tab === button;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
    // Only the selected tab stays in the document tab order.
    tab.setAttribute('tabindex', active ? '0' : '-1');
  }
  for (const panel of document.querySelectorAll('.settings-tab-panel')) {
    panel.hidden = panel.id !== settingsPanels[name];
  }
  if (moveFocus) button.focus();
}

function moveSettingsTab(from, step) {
  const index = settingsTabs.indexOf(from);
  if (index === -1) return;
  const next = settingsTabs[(index + step + settingsTabs.length) % settingsTabs.length];
  selectSettingsTab(next);
}

settingsTabs.forEach(button => {
  button.addEventListener('click', () => selectSettingsTab(button, false));
  button.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      event.preventDefault(); moveSettingsTab(button, 1);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      event.preventDefault(); moveSettingsTab(button, -1);
    } else if (event.key === 'Home') {
      event.preventDefault(); selectSettingsTab(settingsTabs[0]);
    } else if (event.key === 'End') {
      event.preventDefault(); selectSettingsTab(settingsTabs[settingsTabs.length - 1]);
    }
  });
  // Set the initial roving state without moving focus on page load.
  button.setAttribute('tabindex', button.classList.contains('active') ? '0' : '-1');
});

async function loadSlskdSettings() {
  try {
    const data = await requestJSON('/api/settings/slskd');
    $('slskdUrl').value = data.slskd_url || '';
    $('slskdDownloadsPath').value = data.slskd_downloads_path || '';

    renderQualityPriority(data.quality_priority);

    $('slskdStatus').textContent =
      `API key ${data.api_key_configured ? 'configured' : 'not configured'}.`;
    setStatusState($('slskdStatus'), classifyStatus($('slskdStatus').textContent));
  } catch (error) {
    $('slskdStatus').textContent = error.message;
    setStatusState($('slskdStatus'), 'error');
  }
}

function qualityPriorityValues() {
  return [...$('qualityPriorityList').querySelectorAll('.quality-priority-item')]
    .map(item => item.dataset.quality);
}

function updateQualityPriorityPositions() {
  const items = [...$('qualityPriorityList').querySelectorAll('.quality-priority-item')];
  items.forEach((item, index) => {
    item.querySelector('.quality-priority-position').textContent = String(index + 1).padStart(2, '0');
    item.querySelector('[data-quality-move="up"]').disabled = index === 0;
    item.querySelector('[data-quality-move="down"]').disabled = index === items.length - 1;
  });
}

function announceQualityPriority(item, index) {
  const label = qualityOptions.find(([value]) => value === item.dataset.quality)?.[1] || item.dataset.quality;
  $('qualityPriorityAnnouncement').textContent = `${label} moved to priority ${index + 1} of ${$('qualityPriorityList').children.length}.`;
}

function moveQualityPriority(item, destination, direction) {
  const list = $('qualityPriorityList');
  const items = [...list.querySelectorAll('.quality-priority-item')];
  const current = items.indexOf(item);
  if (current < 0 || destination < 0 || destination >= items.length || current === destination) return;
  const reference = items[destination];
  if (destination < current) list.insertBefore(item, reference);
  else list.insertBefore(item, reference.nextSibling);
  updateQualityPriorityPositions();
  announceQualityPriority(item, destination);
  // Moving a node drops focus, and the pressed button can become disabled at either end of the list.
  // Return focus to the same row so keyboard users can keep moving it.
  if (direction) focusQualityMove(item, direction);
}

function focusQualityMove(item, direction) {
  const opposite = direction === 'up' ? 'down' : 'up';
  const pressed = item.querySelector(`[data-quality-move="${direction}"]`);
  const other = item.querySelector(`[data-quality-move="${opposite}"]`);
  (pressed.disabled ? other : pressed).focus();
}

function renderQualityPriority(savedValues) {
  const supported = new Set(qualityOptions.map(([value]) => value));
  const saved = Array.isArray(savedValues) ? savedValues.filter(value => supported.has(value)) : [];
  const priorities = [...new Set(saved)];
  for (const [value] of qualityOptions) if (!priorities.includes(value)) priorities.push(value);
  const list = $('qualityPriorityList');
  list.replaceChildren();
  for (const value of priorities) {
    const [, label] = qualityOptions.find(([optionValue]) => optionValue === value);
    const item = document.createElement('li');
    item.className = 'quality-priority-item is-idle';
    item.dataset.quality = value;
    const grip = document.createElement('span');
    grip.className = 'quality-priority-grip';
    grip.setAttribute('aria-hidden', 'true');
    grip.textContent = '⠿';
    const position = document.createElement('span');
    position.className = 'quality-priority-position';
    position.setAttribute('aria-hidden', 'true');
    const name = document.createElement('span');
    name.className = 'quality-priority-label';
    name.textContent = label;
    const moves = document.createElement('div');
    moves.className = 'quality-priority-moves action-group';
    moves.setAttribute('role', 'group');
    moves.setAttribute('aria-label', `Move ${label}`);
    for (const direction of ['up', 'down']) {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.qualityMove = direction;
      button.title = `Move ${label} ${direction}`;
      button.setAttribute('aria-label', `Move ${label} ${direction}`);
      button.append(spriteIcon(direction === 'up' ? 'chevron-up' : 'chevron-down'));
      button.addEventListener('click', () => {
        const current = [...list.children].indexOf(item);
        moveQualityPriority(item, current + (direction === 'up' ? -1 : 1), direction);
      });
      moves.append(button);
    }
    item.append(grip, position, name, moves);
    list.append(item);
  }
  updateQualityPriorityPositions();
}

// Drag-to-reorder (adapted from https://tahazsh.com/blog/seamless-ui-with-js-drag-to-reorder-example):
// the grabbed row follows the pointer while the rows it passes slide out of the way with a transform.
const qualityPriorityList = $('qualityPriorityList');
const qualityDrag = { item: null, startX: 0, startY: 0, lastX: 0, lastY: 0, gap: 0, items: [], startRect: null };

function qualityIdleItems() {
  return qualityDrag.items.filter(item => item !== qualityDrag.item);
}

qualityPriorityList.addEventListener('pointerdown', event => {
  const handle = event.target.closest('.quality-priority-grip');
  if (!handle || qualityDrag.item || (event.pointerType === 'mouse' && event.button !== 0)) return;
  const item = handle.closest('.quality-priority-item');
  qualityDrag.items = [...qualityPriorityList.querySelectorAll('.quality-priority-item')];
  qualityDrag.item = item;
  qualityDrag.startX = qualityDrag.lastX = event.clientX;
  qualityDrag.startY = qualityDrag.lastY = event.clientY;
  qualityDrag.startRect = item.getBoundingClientRect();
  const [first, second] = qualityDrag.items;
  qualityDrag.gap = second ? Math.abs(first.getBoundingClientRect().bottom - second.getBoundingClientRect().top) : 0;
  const dragIndex = qualityDrag.items.indexOf(item);
  qualityDrag.items.forEach((other, index) => {
    if (other !== item && index < dragIndex) other.dataset.isAbove = '';
  });
  item.classList.remove('is-idle');
  item.classList.add('is-draggable');
  handle.setPointerCapture(event.pointerId);
  event.preventDefault();
});

function updateQualityDragPositions() {
  const rect = qualityDrag.item.getBoundingClientRect();
  const dragY = rect.top + rect.height / 2;
  for (const other of qualityIdleItems()) {
    const otherRect = other.getBoundingClientRect();
    const otherY = otherRect.top + otherRect.height / 2;
    const above = 'isAbove' in other.dataset;
    if (above ? dragY <= otherY : dragY >= otherY) other.dataset.isToggled = '';
    else delete other.dataset.isToggled;
    other.style.transform = 'isToggled' in other.dataset
      ? `translateY(${(above ? 1 : -1) * (rect.height + qualityDrag.gap)}px)`
      : '';
  }
}

qualityPriorityList.addEventListener('pointermove', event => {
  if (!qualityDrag.item) return;
  event.preventDefault();
  qualityDrag.lastX = event.clientX;
  qualityDrag.lastY = event.clientY;
  qualityDrag.item.style.transform =
    `translate(${event.clientX - qualityDrag.startX}px, ${event.clientY - qualityDrag.startY}px)`;
  updateQualityDragPositions();
});

function finishQualityDrag() {
  const { item, items } = qualityDrag;
  if (!item) return;
  const from = items.indexOf(item);
  const passed = qualityIdleItems().filter(other => 'isToggled' in other.dataset);
  const to = from + passed.filter(other => !('isAbove' in other.dataset)).length
    - passed.filter(other => 'isAbove' in other.dataset).length;
  const others = items.filter(other => other !== item);
  others.splice(to, 0, item);
  qualityPriorityList.append(...others);
  for (const other of others) {
    delete other.dataset.isAbove;
    delete other.dataset.isToggled;
    if (other !== item) other.style.transform = '';
  }
  // The row is now in its new slot; offset it back to where the pointer left it, then let the
  // idle transition glide it home.
  const { startRect, startX, startY, lastX, lastY } = qualityDrag;
  item.style.transform = '';
  requestAnimationFrame(() => {
    const rect = item.getBoundingClientRect();
    item.style.transform =
      `translate(${lastX - startX}px, ${lastY - startY + startRect.y - rect.y}px)`;
    requestAnimationFrame(() => {
      item.style.transform = '';
      item.classList.remove('is-draggable');
      item.classList.add('is-idle');
    });
  });
  qualityDrag.item = null;
  qualityDrag.items = [];
  updateQualityPriorityPositions();
  announceQualityPriority(item, to);
}

qualityPriorityList.addEventListener('pointerup', finishQualityDrag);
qualityPriorityList.addEventListener('pointercancel', finishQualityDrag);

$('saveSlskd').addEventListener('click', async () => {
  const priorities = qualityPriorityValues();
  if (priorities.length !== qualityOptions.length || new Set(priorities).size !== qualityOptions.length) {
    $('slskdStatus').textContent = 'Each of the six quality preferences must appear exactly once.';
    setStatusState($('slskdStatus'), 'error');
    return;
  }

  const payload = {
    slskd_url: $('slskdUrl').value.trim(),
    slskd_downloads_path: $('slskdDownloadsPath').value.trim(),
    quality_priority: priorities
  };
  if ($('slskdApiKey').value) payload.api_key = $('slskdApiKey').value;

  try {
    await sendJSON('/api/settings/slskd', 'PUT', payload);
    $('slskdApiKey').value = '';
    $('slskdStatus').textContent = 'Settings saved.';
    setStatusState($('slskdStatus'), 'success');
    await loadSlskdSettings();
  } catch (error) {
    $('slskdStatus').textContent = error.message;
    setStatusState($('slskdStatus'), 'error');
  }
});

$('testSlskd').addEventListener('click', async () => {
  $('slskdStatus').textContent = 'Testing connection…';
  try {
    const data = await sendJSON('/api/settings/slskd/test');
    $('slskdStatus').textContent = data.message || (data.ok ? 'Connection successful.' : 'Test failed.');
  } catch (error) {
    $('slskdStatus').textContent = error.message;
  }
});


document.getElementById('logoutButton').addEventListener('click', async event => {
  // Prevent a second submission while the request is in flight. The redirect in finally
  // ends the page either way, so the disabled state never needs to be cleared.
  const button = event.currentTarget;
  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  try { await fetch('/api/auth/logout', {method: 'POST', cache: 'no-store'}); }
  finally { window.location.replace('/login'); }
});

for (const id of ['shelfNewReleases', 'shelfNewest', 'shelfRecent', 'shelfFrequent']) makeScrollTrackFocusable($(id));

// Populate only the visible dashboard on startup. Other pages load on first visit
// so their API requests don't compete with the page the user is currently viewing.
loadDashboardPicks();
loadDashboardShelves();

// ---- Library and global search (SEARCH_CONTRACT P1) --------------------------------
// Data comes from /api/search (SSE), /api/library/artists and /api/artists/{key}. Every
// value is written with textContent or attributes, never through HTML strings.

const SEARCH_DEBOUNCE_MS = 250;
const SEARCH_GROUPS = [['artist', 'Artists'], ['album', 'Albums'], ['song', 'Songs'], ['genre', 'Genres']];
const LIBRARY_PAGE_SIZE = 60;
const TYPE_LABELS = {artist: 'Artist', album: 'Album', song: 'Song', genre: 'Genre'};
const INDEX_REASON_MESSAGES = {
  index_building: 'Your library is still being indexed. Try again in a moment.',
  index_unavailable: 'Your library could not be indexed right now.',
};

// A search surface is one place that shows a streamed search: the top bar's drop-down or the library
// page's results. Each has its own stream and sequence number, so the two never overwrite each other.
function makeSearchSurface({status, groups, external, externalList, setOpen, setLive}) {
  return {source: null, seq: 0, timer: 0, status, groups, external, externalList, setOpen, setLive};
}

const globalSearch = makeSearchSurface({
  status: $('globalSearchStatus'),
  groups: $('globalSearchGroups'),
  external: $('globalSearchExternal'),
  externalList: $('globalSearchExternalList'),
  setOpen: open => setGlobalSearchOpen(open),
  setLive: live => setSearchStatusLive(live),
});
// The library page's search is owned-only, so it has no "Not in your library" group. A query replaces the browse list with grouped results; no query brings it back.
const librarySearch = makeSearchSurface({
  status: $('librarySearchStatus'),
  groups: $('librarySearchGroups'),
  external: null,
  externalList: null,
  setOpen: open => {
    $('librarySearchResults').hidden = !open;
    $('libraryBrowse').hidden = open;
  },
  setLive: live => $('librarySearchStatus').setAttribute('aria-live', live ? 'polite' : 'off'),
});
const libraryView = {query: '', tab: 'artists', sort: 'name', order: '', display: 'list', tileSize: 180, cursor: null, seq: 0, cursor: null, seq: 0, resetOnRetry: false, detailSeq: 0, albumSeq: 0, genreSeq: 0, listReturn: null, artistCtx: null};
// Open artist and album streams, so leaving a page closes them.
const libraryStreams = new Set();
let libraryFilterTimer = 0;

function setStatus(el, message, kind) {
  el.textContent = message;
  setStatusState(el, kind);
}

// Artwork is optional. A failed image is removed, so the row keeps its text and layout.
function buildArtwork(url, className) {
  const frame = document.createElement('div');
  frame.className = className;
  if (!url) return frame;
  const image = document.createElement('img');
  image.alt = '';
  image.loading = 'lazy';
  image.decoding = 'async';
  image.onerror = () => image.remove();
  image.src = url;
  frame.append(image);
  return frame;
}

// ---- Global search ----

function setGlobalSearchOpen(open) {
  $('globalSearchResults').hidden = !open;
  if (open) $('globalSearchRecent').hidden = true;
}

// The last three submitted searches, newest first. Storage can be unavailable or hold bad data,
// so every access degrades to "no history" instead of throwing.
const RECENT_SEARCHES_KEY = 'navidrome-recent-searches';
const RECENT_SEARCHES_MAX = 3;

function loadRecentSearches() {
  try {
    const stored = JSON.parse(localStorage.getItem(RECENT_SEARCHES_KEY) || '[]');
    return Array.isArray(stored) ? stored.filter(item => typeof item === 'string' && item).slice(0, RECENT_SEARCHES_MAX) : [];
  } catch (error) {
    return [];
  }
}

function rememberSearch(rawQuery) {
  const query = rawQuery.trim();
  if (!query) return;
  const recent = [query, ...loadRecentSearches().filter(item => item.toLowerCase() !== query.toLowerCase())];
  try {
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recent.slice(0, RECENT_SEARCHES_MAX)));
  } catch (error) {
    // History is a convenience; a full or blocked store only means nothing is remembered.
  }
}

function hideRecentSearches() {
  $('globalSearchRecent').hidden = true;
}

// Shown on click or focus while the field is empty; once the person types, results take over.
function showRecentSearches() {
  const recent = loadRecentSearches();
  if ($('globalSearchInput').value.trim() || !recent.length || !$('globalSearchResults').hidden) {
    hideRecentSearches();
    return;
  }
  const list = $('globalSearchRecentList');
  list.replaceChildren();
  for (const term of recent) {
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'search-item-content';
    button.dataset.recentSearch = term;
    addTextElement(button, 'span', 'search-item-name', term);
    item.append(button);
    list.append(item);
  }
  $('globalSearchRecent').hidden = false;
}

// Phone only: the search is a magnifier in the top bar that grows into the field when tapped, and
// folds back when it is left empty. The form is the same one the desktop bar uses.
function setSearchExpanded(open, {focus = false} = {}) {
  $('globalSearch').classList.toggle('is-expanded', open);
  $('searchToggle').setAttribute('aria-expanded', String(open));
  document.querySelector('header').classList.toggle('is-searching', open);
  if (open && focus) $('globalSearchInput').focus();
}

// Stops a surface's pending and running search and hides its results.
function closeSearchSurface(surface) {
  clearTimeout(surface.timer);
  if (surface.source) {
    surface.source.close();
    surface.source = null;
  }
  surface.seq += 1;
  surface.setOpen(false);
}

function closeGlobalSearch({focusInput = false} = {}) {
  closeSearchSurface(globalSearch);
  hideRecentSearches();
  if (focusInput) $('globalSearchInput').focus();
  else if (!$('globalSearchInput').value.trim()) setSearchExpanded(false);
}

// The status line is quiet while results stream in, so a screen reader hears the final count once,
// not one announcement per result. It becomes polite again when the stream ends.
function setSearchStatusLive(live) {
  $('globalSearchStatus').setAttribute('aria-live', live ? 'polite' : 'off');
}

// Each result lands in its type group as it arrives. Groups are created on first use and kept in
// SEARCH_GROUPS order, so a late type never lands above an earlier one.
function searchGroupList(surface, type) {
  const groupsEl = surface.groups;
  const existing = Array.from(groupsEl.children).find(child => child.dataset.searchType === type);
  if (existing) return existing.querySelector('ul');
  const rank = SEARCH_GROUPS.findIndex(([kind]) => kind === type);
  const section = document.createElement('section');
  section.className = 'search-group';
  section.dataset.searchType = type;
  addTextElement(section, 'p', 'search-group-heading', SEARCH_GROUPS[rank][1]);
  const list = document.createElement('ul');
  list.className = 'search-group-list';
  section.append(list);
  const after = Array.from(groupsEl.children).find(child =>
    SEARCH_GROUPS.findIndex(([kind]) => kind === child.dataset.searchType) > rank);
  groupsEl.insertBefore(section, after || null);
  return list;
}

function startGlobalSearch(rawQuery) {
  startSearch(globalSearch, rawQuery, closeGlobalSearch);
}

// Streams /api/search into a surface. ``close`` is what an empty query does.
function startSearch(surface, rawQuery, close = () => closeSearchSurface(surface)) {
  const query = rawQuery.trim();
  clearTimeout(surface.timer);
  if (surface.source) {
    surface.source.close();
    surface.source = null;
  }
  const seq = ++surface.seq;
  if (!query) {
    close();
    return;
  }
  const status = surface.status;
  const groupsEl = surface.groups;
  const externalEl = surface.external;
  const externalList = surface.externalList;
  let shown = 0;
  let external = 0;
  let capabilities = null;
  const isCurrent = () => seq === surface.seq;
  // The previous results stay on screen until this stream's first event, so the list does not
  // blank between keystrokes.
  surface.setOpen(true);
  surface.setLive(false);
  setStatus(status, 'Searching…', 'loading');

  // The library page searches owned music only; the top bar also looks at the outside sources.
  const params = {q: query, limit: '10'};
  if (surface === librarySearch) params.scope = 'owned';
  const source = new EventSource('/api/search?' + new URLSearchParams(params));
  surface.source = source;
  const finish = () => {
    source.close();
    if (surface.source === source) surface.source = null;
  };

  source.addEventListener('capabilities', event => {
    if (!isCurrent()) return;
    capabilities = JSON.parse(event.data);
    groupsEl.replaceChildren();
    if (externalEl) {
      externalList.replaceChildren();
      externalEl.hidden = true;
    }
  });
  source.addEventListener('result', event => {
    if (!isCurrent()) return;
    const item = JSON.parse(event.data);
    if (!SEARCH_GROUPS.some(([type]) => type === item.type)) return;
    if (item.owned) {
      searchGroupList(surface, item.type).append(buildSearchItem(item, surface));
      shown += 1;
    } else if (externalEl) {
      externalEl.hidden = false;
      externalList.append(buildSearchItem(item));
      external += 1;
    }
    setStatus(status, 'Searching… ' + pluralize(shown + external, 'match', 'matches') + ' so far', 'loading');
  });
  source.addEventListener('done', () => {
    finish();
    if (isCurrent()) {
      surface.setLive(true);
      renderSearchSummary(status, query, shown, external, capabilities);
    }
  });
  source.addEventListener('error', event => {
    finish();
    if (!isCurrent()) return;
    // Results already shown stay on screen. A server "error" event carries data; a dropped connection does not.
    surface.setLive(true);
    const message = event.data
      ? 'Search stopped before it finished. Showing ' + pluralize(shown, 'match', 'matches') + '. Try again.'
      : 'Search is unavailable right now. Try again.';
    setStatus(status, message, 'error');
  });
}

function renderSearchSummary(status, query, owned, external, capabilities) {
  const index = capabilities && capabilities.owned_index;
  const parts = [];
  let kind = 'progress';
  if (index && !index.available) {
    parts.push(INDEX_REASON_MESSAGES[index.reason] || 'Your library is not available right now.');
    kind = index.reason === 'index_building' ? 'loading' : 'error';
  } else if (owned) {
    parts.push(pluralize(owned, 'match', 'matches') + ' in your library');
  } else if (!external) {
    parts.push('No matches in your library for “' + query + '”.');
    kind = 'empty';
  }
  if (external) parts.push(pluralize(external, 'match', 'matches') + ' not in your library');
  setStatus(status, parts.join(' · '), kind);
}

// Artists with a genre show it after the name, so two artists with the same name can be told apart.
// Without one, the album count on the detail line does that job.
function searchItemName(item) {
  return item.type === 'artist' && item.genre ? item.name + ' (' + item.genre + ')' : item.name;
}

function searchItemDetail(item) {
  // Provider artists have no album count, so the detail line only states the type.
  if (item.type === 'genre') return item.owned ? 'Genre · in your library' : TYPE_LABELS.genre;
  if (!item.owned && item.type === 'artist') return TYPE_LABELS.artist;
  if (item.type === 'artist') return pluralize(item.album_count, 'album', 'albums');
  const details = item.type === 'album' ? [item.artist, item.year] : [item.artist, item.album];
  return details.filter(Boolean).join(' · ');
}

// Artists, albums and genres open their page, owned or not; a song opens its album.
// The album part of a route key: lower case, as the server normalises it again.
function normalizeAlbumKey(name) {
  return String(name).trim().toLocaleLowerCase();
}

function searchItemTarget(item) {
  if (item.type === 'artist') return artistTarget(item);
  if (item.type === 'album') return albumTarget(item);
  if (item.type === 'genre') return {type: 'genre', tag: item.tag};
  if (item.type === 'song' && item.album) {
    // A song opens the album that holds it.
    return albumTarget({
      owned: item.owned, id: item.album_id, key: (item.artist_key || '') + '/' + normalizeAlbumKey(item.album),
      artist: item.artist, name: item.album,
      artwork_url: item.artwork_url,
    });
  }
  return null;
}

function buildSearchItem(item, surface = globalSearch) {
  const row = document.createElement('li');
  row.className = 'search-item';
  const target = searchItemTarget(item);
  const content = target ? document.createElement('button') : document.createElement('div');
  if (target) {
    content.type = 'button';
    content.addEventListener('click', () => (surface === librarySearch ? openFromLibrarySearch(content, target) : openFromSearch(target)));
  }
  content.className = 'search-item-content';
  content.append(buildArtwork(item.type === 'album' ? sizedArtwork(item.artwork_url, 96) : item.artwork_url, 'search-item-art'));
  const text = document.createElement('span');
  text.className = 'search-item-text';
  addTextElement(text, 'span', 'search-item-name', searchItemName(item));
  addTextElement(text, 'span', 'search-item-detail', searchItemDetail(item));
  content.append(text);
  row.append(content);
  return row;
}

function openFromSearch(target) {
  // Opening a result is a signal the query was worth keeping; save it before the field is cleared.
  rememberSearch($('globalSearchInput').value);
  closeGlobalSearch();
  $('globalSearchInput').value = '';
  openLibraryTarget(target);
}

// A result opened from the library page keeps the search where it was, so Back returns to the results.
function openFromLibrarySearch(button, target) {
  libraryView.listReturn = button;
  libraryOpen(target);
}

// ---- Library list ----

function showLibraryListMore(visible, label, resetOnRetry) {
  const more = $('libraryMore');
  $('libraryMoreGroup').hidden = !visible;
  more.title = label;
  more.setAttribute('aria-label', label);
  more.replaceChildren(spriteIcon(label === 'Load more' ? 'plus' : 'rotate-cw'));
  libraryView.resetOnRetry = resetOnRetry;
}

// What each tab browses: its route, its words, and the sorts it offers. The first sort is the default.
const LIBRARY_TABS = {
  artists: {
    url: '/api/library/artists', noun: ['artist', 'artists'],
    sorts: [['name', 'Name'], ['album_count', 'Album count'], ['added', 'Date added']],
  },
  albums: {
    url: '/api/library/albums', noun: ['album', 'albums'],
    sorts: [['name', 'Album name'], ['artist', 'Artist'], ['year', 'Album year'], ['added', 'Date added'], ['song_count', 'Track count']],
  },
};
// The direction a sort starts in (the server uses the same table); the direction button flips it.
const LIBRARY_DEFAULT_ORDER = {name: 'asc', artist: 'asc', album_count: 'desc', added: 'desc', year: 'desc', song_count: 'desc'};
const LIBRARY_PREFS_KEY = 'navidrome-library-view';
const TILE_SIZE_MIN = 110;
const TILE_SIZE_MAX = 320;

function libraryOrder() {
  return libraryView.order || LIBRARY_DEFAULT_ORDER[libraryView.sort];
}

// Tab, sort, direction, display and tile size are remembered between visits. Storage can be
// unavailable or hold bad data, so each value is checked and a failure only means the defaults.
function loadLibraryPrefs() {
  const view = libraryView;
  try {
    const stored = JSON.parse(localStorage.getItem(LIBRARY_PREFS_KEY) || '{}') || {};
    if (stored.tab in LIBRARY_TABS) view.tab = stored.tab;
    if (LIBRARY_TABS[view.tab].sorts.some(([value]) => value === stored.sort)) view.sort = stored.sort;
    if (stored.order === 'asc' || stored.order === 'desc') view.order = stored.order;
    if (stored.display === 'list' || stored.display === 'grid') view.display = stored.display;
    const size = Number(stored.tileSize);
    if (Number.isFinite(size)) view.tileSize = Math.min(TILE_SIZE_MAX, Math.max(TILE_SIZE_MIN, Math.round(size)));
  } catch (error) {
    // Defaults stay.
  }
  if (!LIBRARY_TABS[view.tab].sorts.some(([value]) => value === view.sort)) view.sort = LIBRARY_TABS[view.tab].sorts[0][0];
}

function saveLibraryPrefs() {
  const {tab, sort, order, display, tileSize} = libraryView;
  try {
    localStorage.setItem(LIBRARY_PREFS_KEY, JSON.stringify({tab, sort, order, display, tileSize}));
  } catch (error) {
    // Preferences are a convenience; nothing breaks without them.
  }
}

// Brings every toolbar control in line with libraryView.
function syncLibraryControls() {
  const view = libraryView;
  const tab = LIBRARY_TABS[view.tab];
  for (const button of document.querySelectorAll('[data-library-tab]')) {
    button.setAttribute('aria-pressed', String(button.dataset.libraryTab === view.tab));
  }
  const select = $('librarySort');
  select.replaceChildren(...tab.sorts.map(([value, label]) => {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    return option;
  }));
  select.value = view.sort;
  const order = libraryOrder();
  const label = 'Sort direction: ' + (order === 'asc' ? 'ascending' : 'descending');
  const orderButton = $('libraryOrder');
  orderButton.title = label;
  orderButton.setAttribute('aria-label', label);
  orderButton.replaceChildren(spriteIcon(order === 'asc' ? 'chevron-up' : 'chevron-down'));
  for (const button of document.querySelectorAll('[data-library-display]')) {
    button.setAttribute('aria-pressed', String(button.dataset.libraryDisplay === view.display));
  }
  const grid = view.display === 'grid';
  $('libraryTileSizeControl').hidden = !grid;
  $('libraryTileSize').value = String(view.tileSize);
  $('libraryTileSize').setAttribute('aria-valuetext', view.tileSize + ' pixels');
  const list = $('libraryList');
  list.classList.toggle('is-grid', grid);
  list.classList.toggle('is-albums', view.tab === 'albums');
  list.style.setProperty('--tile-size', view.tileSize + 'px');
}

async function loadLibrary({reset = true} = {}) {
  const view = libraryView;
  const tab = LIBRARY_TABS[view.tab];
  if (reset) {
    view.cursor = null;
    view.seq += 1;
  }
  const seq = view.seq;
  const list = $('libraryList');
  const status = $('libraryStatus');
  const params = new URLSearchParams({limit: String(LIBRARY_PAGE_SIZE), sort: view.sort, order: libraryOrder()});
  if (!reset && view.cursor) params.set('cursor', view.cursor);
  if (reset) {
    list.replaceChildren();
    showLibraryListMore(false, 'Load more', false);
    setStatus(status, 'Loading ' + tab.noun[1] + '…', 'loading');
  } else {
    $('libraryMore').disabled = true;
  }
  try {
    const data = await requestJSON(tab.url + '?' + params);
    if (seq !== view.seq) return;
    $('libraryMore').disabled = false;
    if (data.index_state === 'building' || data.index_state === 'unavailable') {
      const message = data.index_state === 'building'
        ? 'Your library is still being indexed. Try again in a moment.'
        : 'Your library could not be indexed right now.';
      setStatus(status, message, data.index_state === 'building' ? 'loading' : 'error');
      showLibraryListMore(true, 'Try again', true);
      return;
    }
    for (const item of data.items) list.append(buildLibraryRow(item));
    view.cursor = data.next_cursor;
    const shown = list.children.length;
    if (!data.total) {
      setStatus(status, 'No ' + tab.noun[1] + ' in your library.', 'empty');
    } else {
      const countText = data.next_cursor
        ? 'Showing ' + shown + ' of ' + pluralize(data.total, tab.noun[0], tab.noun[1])
        : pluralize(data.total, tab.noun[0], tab.noun[1]);
      setStatus(status, countText + (data.index_state === 'stale' ? ' · Showing the last indexed library' : ''), 'progress');
    }
    showLibraryListMore(Boolean(data.next_cursor), 'Load more', false);
  } catch (error) {
    if (seq !== view.seq) return;
    $('libraryMore').disabled = false;
    setStatus(status, 'Your library could not be loaded. Try again.', 'error');
    // A failed append retries the append, so the rows already loaded stay in place.
    showLibraryListMore(true, 'Try again', reset);
  }
}

function formatLibraryDate(iso) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString(undefined, {year: 'numeric', month: 'short', day: 'numeric'});
}

function libraryItemDetail(item) {
  const added = libraryView.sort === 'added' && item.added ? 'Added ' + formatLibraryDate(item.added) : '';
  const base = libraryView.tab === 'albums'
    ? [item.artist, item.year]
    : [pluralize(item.album_count, 'album', 'albums')];
  return [...base, added].filter(Boolean).join(' · ');
}

function buildLibraryRow(item) {
  const albums = libraryView.tab === 'albums';
  const row = document.createElement('li');
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'library-artist';
  // A grid tile is much larger than a list thumbnail, so it asks for a bigger image.
  const art = libraryView.display === 'grid' ? 400 : 96;
  button.append(buildArtwork(sizedArtwork(item.artwork_url, art), 'library-art'));
  const text = document.createElement('span');
  text.className = 'library-artist-text';
  addTextElement(text, 'span', 'library-artist-name', item.name);
  addTextElement(text, 'span', 'library-artist-count', libraryItemDetail(item));
  button.append(text);
  button.addEventListener('click', () => {
    libraryView.listReturn = button;
    libraryOpen(albums ? albumTarget(item) : artistTarget(item));
  });
  row.append(button);
  return row;
}

// ---- Navigation between library views ----
// One stack serves the artist, album and genre views, so every name in the library can open its
// page and Back always returns to the page the reader came from. The list is the stack's floor.

const LIBRARY_VIEWS = {
  list: 'libraryListView',
  artist: 'libraryDetailView',
  album: 'libraryAlbumView',
  genre: 'libraryGenreView',
};
const libraryNav = {stack: [], current: null};

function sizedArtwork(url, size) {
  return url ? url + (url.includes('?') ? '&' : '?') + 'size=' + size : null;
}

function libraryShow(name) {
  for (const [view, id] of Object.entries(LIBRARY_VIEWS)) $(id).hidden = view !== name;
  // The page intro belongs to the list; every other view is the reading path.
  $('libraryIntro').hidden = name !== 'list';
  // The artist and album pages open on the picture: the section heading would only repeat the sidebar tab.
  $('libraryHeading').hidden = name === 'artist' || name === 'album';
}

function closeLibraryStreams() {
  libraryView.detailSeq += 1;
  libraryView.albumSeq += 1;
  libraryView.genreSeq += 1;
  for (const source of libraryStreams) source.close();
  libraryStreams.clear();
}

function libraryReset() {
  closeLibraryStreams();
  // Each visit starts without a search; the tab, sort and display stay as they were.
  closeSearchSurface(librarySearch);
  $('libraryFilter').value = '';
  syncLibraryFilterClear();
  syncLibraryControls();
  libraryNav.stack = [];
  libraryNav.current = null;
  libraryShow('list');
  syncLocationHash();
}

function libraryOpen(target) {
  if (libraryNav.current) libraryNav.stack.push(libraryNav.current);
  libraryNav.current = target;
  renderLibraryTarget(target);
  syncLocationHash();
}

function libraryBack() {
  closeLibraryStreams();
  const previous = libraryNav.stack.pop() || null;
  libraryNav.current = previous;
  syncLocationHash({replace: true});
  if (previous) {
    renderLibraryTarget(previous);
    return;
  }
  libraryShow('list');
  const back = libraryView.listReturn;
  if (back && back.isConnected) back.focus();
  else $('libraryHeading').focus();
}

// ---- The address keeps the current page across a browser refresh ----
// The hash is '#<page>' for a top-level page and '#library/<artist|album|genre>?<fields>' for a
// library page, every field URI-encoded by URLSearchParams. It carries only names, keys and
// catalog IDs, never a token or secret. Each page change pushes a history entry and popstate
// reapplies it. The in-app library stack is not stored, so after a refresh the in-app Back
// button returns to the library list.
const HASH_FIELDS = {
  artist: ['key', 'id', 'name', 'mbid'],
  album: ['key', 'id', 'artist', 'name', 'year', 'mbid'],
  genre: ['tag'],
};
const HASH_FIELD_MAX = 300;

function encodeLibraryHash(target) {
  const fields = target && HASH_FIELDS[target.type];
  if (!fields) return '#library';
  const params = new URLSearchParams();
  for (const field of fields) {
    const value = field === 'tag' ? target.tag : target[field];
    if (value !== null && value !== undefined && value !== '') params.set(field, String(value));
  }
  return '#library/' + target.type + '?' + params;
}

// Returns a library target, or null for anything that is not a well-formed library address.
function decodeLibraryHash(hash) {
  const match = /^#library\/(artist|album|genre)\?(.*)$/.exec(hash || '');
  if (!match) return null;
  const type = match[1];
  let params;
  try {
    params = new URLSearchParams(match[2]);
    for (const value of params.values()) if (value.length > HASH_FIELD_MAX) return null;
  } catch (error) {
    return null;
  }
  const get = field => params.get(field) || null;
  if (type === 'genre') return get('tag') ? {type, tag: get('tag')} : null;
  if (type === 'artist') {
    if (!get('key')) return null;
    return {type, id: get('id'), key: get('key'), name: get('name') || '', mbid: get('mbid'), artworkUrl: null};
  }
  if (!(get('key') || '').includes('/') || !get('name')) return null;
  return {
    type, key: get('key'), id: get('id'), artist: get('artist') || '', name: get('name'),
    year: get('year'), mbid: get('mbid'), artworkUrl: get('id') ? '/api/owned/artwork/' + get('id') : null,
    owned: Boolean(get('id')),
  };
}

function currentLocationHash() {
  if (activePage === 'library' && libraryNav.current) return encodeLibraryHash(libraryNav.current);
  return '#' + activePage;
}

// Pushes a history entry, so the browser Back and Forward buttons step through the in-app pages.
// Backing out of a library page with the in-app button replaces the entry instead of pushing.
// The library views move focus to their heading on a user's navigation; restoring from the address
// skips that, or a refresh would show the browser's focus ring around the heading.
let applyingHash = false;

function syncLocationHash({replace = false} = {}) {
  if (applyingHash) return;
  const hash = currentLocationHash();
  if (window.location.hash === hash) return;
  try {
    const url = window.location.pathname + window.location.search + hash;
    if (replace) window.history.replaceState(null, '', url);
    else window.history.pushState(null, '', url);
  } catch (error) {
    // The address is a convenience; a browser that refuses the update keeps working without it.
  }
}

// Show the page the hash names without writing the hash back. An unknown or malformed hash
// shows the dashboard.
function applyHash(hash) {
  const name = hash.slice(1).split('/')[0].split('?')[0];
  const section = name ? $(name) : null;
  const page = section && section.classList.contains('page') ? name : 'dashboard';
  applyingHash = true;
  try {
    if (!$('albumModalBackdrop').hidden) closeAlbumModal();
    navigateTo(page);
    if (page !== 'library') return;
    const target = decodeLibraryHash(hash);
    if (target) {
      libraryView.listReturn = null;
      libraryOpen(target);
    }
  } finally {
    applyingHash = false;
  }
}

window.addEventListener('popstate', () => applyHash(window.location.hash));

function renderLibraryTarget(target) {
  closeLibraryStreams();
  if (target.type === 'artist') renderArtist(target);
  else if (target.type === 'album') renderAlbum(target);
  else renderGenre(target.tag);
}

// Targets are built from any item that names an artist, album or genre: search results, library
// rows, album rows, similar artists and genre items. Only an owned item carries a Navidrome ID.
function artistTarget(item) {
  const owned = item.owned !== false;
  return {
    type: 'artist',
    id: owned ? item.id || null : null,
    key: item.key || item.artist_key,
    name: item.name || item.artist || '',
    mbid: item.mbid || null,
    artworkUrl: item.artwork_url || null,
  };
}

function albumRouteKey(item) {
  const key = item.key || '';
  return key.includes('/') ? key : (item.artist_key || '') + '/' + key;
}

function albumTarget(item) {
  const owned = item.owned !== false;
  return {
    type: 'album',
    key: albumRouteKey(item),
    id: owned ? item.id || null : null,
    artist: item.artist || '',
    name: item.name || '',
    year: item.year || null,
    mbid: item.release_group_mbid || null,
    artworkUrl: item.artwork_url || (owned && item.id ? '/api/owned/artwork/' + item.id : null),
    owned,
  };
}

// ---- Links from cards and rows elsewhere in the app ----
// Album names, artist names and tags on cards, rows and the album panel open the matching library
// page. These items carry names, not library keys, so the keys are derived the way the server
// derives them (accents and punctuation folded, a leading "The" dropped).
function foldKey(name) {
  const folded = String(name || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  return folded.replace(/^the (?=.)/, '');
}

function namedArtistTarget(name, mbid = null) {
  return {type: 'artist', id: null, key: foldKey(name), name, mbid, artworkUrl: null};
}

function namedAlbumTarget(artist, album, item = {}) {
  return {
    type: 'album', key: foldKey(artist) + '/' + foldKey(album), id: null, artist, name: album,
    year: firstReleaseYear(item.year, item.release_year, item.first_release_year),
    mbid: item.release_group_mbid || null, artworkUrl: null, owned: false,
  };
}

function openLibraryTarget(target) {
  if (!$('albumModalBackdrop').hidden) closeAlbumModal();
  navigateTo('library');
  libraryView.listReturn = null;
  libraryOpen(target);
}

// A text link inside a card or row: it inherits the surrounding type and opens the page on click.
// The card's own click handler ignores clicks on buttons, so it does not also open the album panel.
function buildInlineLink(text, target) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'inline-link';
  button.textContent = text;
  button.addEventListener('click', event => {
    event.stopPropagation();
    openLibraryTarget(target);
  });
  return button;
}

function linkArtistName(parent, artist) {
  if (!artist || artist === 'Unknown artist') {
    parent.append(document.createTextNode(artist || ''));
    return;
  }
  parent.append(buildInlineLink(artist, namedArtistTarget(artist)));
}

function linkAlbumName(parent, artist, album, item) {
  if (!artist || !album || artist === 'Unknown artist') {
    parent.append(document.createTextNode(album || ''));
    return;
  }
  parent.append(buildInlineLink(album, namedAlbumTarget(artist, album, item)));
}

// Genres and tags as links, separated by a middle dot.
function linkGenres(parent, genres) {
  genres.forEach((genre, index) => {
    if (index) parent.append(document.createTextNode(' · '));
    parent.append(buildInlineLink(genre, {type: 'genre', tag: String(genre).toLocaleLowerCase()}));
  });
}

// A name in the library that opens a page. The caller says which page by passing the target.
function buildLibraryLink(text, target, className = 'library-link') {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = className;
  button.textContent = text;
  button.addEventListener('click', () => libraryOpen(target));
  return button;
}

// Covers for albums the library does not have come from the artwork service, one request per
// visible row, and are cached for the page's life.
const remoteArtworkObserver = typeof IntersectionObserver === 'function'
  ? new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        remoteArtworkObserver.unobserve(entry.target);
        entry.target.loadRemoteArtwork();
      }
    }, {rootMargin: '200px'})
  : null;

function buildAlbumArtwork(item, className, size) {
  if (item.artwork_url) return buildArtwork(sizedArtwork(item.artwork_url, size), className);
  const frame = buildArtwork(null, className);
  if (item.owned || !item.artist) return frame;
  frame.loadRemoteArtwork = () => {
    const cacheKey = item.artist.trim().toLocaleLowerCase() + '::' + item.name.trim().toLocaleLowerCase();
    const query = new URLSearchParams({artist: item.artist, album: item.name});
    cachedJSONRequest(artworkRequests, cacheKey, '/api/artwork?' + query)
      .then(data => {
        if (!data || !data.artwork_url) return;
        const image = document.createElement('img');
        image.alt = '';
        image.decoding = 'async';
        image.onerror = () => image.remove();
        image.src = data.artwork_url;
        frame.append(image);
        if (frame.onRemoteArtwork) frame.onRemoteArtwork(data);
      })
      .catch(() => {});
  };
  if (remoteArtworkObserver) remoteArtworkObserver.observe(frame);
  else frame.loadRemoteArtwork();
  return frame;
}

function buildOwnedCheck() {
  const mark = document.createElement('span');
  mark.className = 'owned-check';
  mark.title = 'In your library';
  mark.setAttribute('role', 'img');
  mark.setAttribute('aria-label', 'In your library');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'owned-check-glyph');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  for (const [name, value] of [['fill', 'none'], ['stroke', 'currentColor'], ['stroke-width', '2.5'], ['stroke-linecap', 'round'], ['stroke-linejoin', 'round']]) {
    svg.setAttribute(name, value);
  }
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M5 12.5 10 17.5 19 7');
  svg.append(path);
  mark.append(svg);
  return mark;
}

// The state control of an album: a green check when the library has it, the Get button when not.
function buildAlbumState(item) {
  if (item.owned) return buildOwnedCheck();
  return createGetButton(item.artist, item.name, {
    artist: item.artist, album: item.name, year: item.year || null, release_group_mbid: item.release_group_mbid || null,
  });
}

function compactCount(value) {
  return new Intl.NumberFormat('en', {notation: 'compact', maximumFractionDigits: 1}).format(Number(value));
}

function buildAlbumRow(item) {
  const row = document.createElement('li');
  row.className = 'album-row';
  const open = document.createElement('button');
  open.type = 'button';
  open.className = 'album-row-open';
  open.append(buildAlbumArtwork(item, 'album-row-art', 120));
  const text = document.createElement('span');
  text.className = 'album-row-text';
  const title = document.createElement('span');
  title.className = 'album-row-title';
  addTextElement(title, 'span', 'album-row-name', item.name);
  // Rows from other artists (similar albums) name their artist, in grey, beside the album.
  if (item.showArtist && item.artist) addTextElement(title, 'span', 'album-row-artist', item.artist);
  // Listen counts (ListenBrainz) show beside the name on the artist page, where albums are ranked by them.
  if (item.showListens && item.popularity !== null && item.popularity !== undefined) {
    const listens = addTextElement(title, 'span', 'album-row-listens', compactCount(item.popularity) + ' listens');
    listens.title = Number(item.popularity).toLocaleString() + ' listens on ' + (item.popularity_source === 'lastfm' ? 'Last.fm' : 'ListenBrainz');
  }
  text.append(title);
  const detail = [item.year].filter(value => value !== null && value !== undefined && value !== '');
  if (detail.length) addTextElement(text, 'span', 'album-row-detail', detail.join(' · '));
  open.append(text);
  open.addEventListener('click', () => libraryOpen(albumTarget(item)));
  row.append(open);
  row.append(item.owned ? buildOwnedCheck() : wrapInActionGroup(buildAlbumState(item), 'Actions for ' + item.name));
  return row;
}

const artistImageRequests = new Map();

// An artist with no library cover gets a photo from the artist-image service, loaded when its row
// scrolls into view. A failed or missing photo leaves the empty frame, as for any other cover.
function buildArtistPhoto(item, size = 96) {
  if (item.artwork_url) return buildArtwork(sizedArtwork(item.artwork_url, size), 'library-art');
  const frame = buildArtwork(null, 'library-art');
  if (!item.name) return frame;
  frame.loadRemoteArtwork = () => {
    cachedJSONRequest(artistImageRequests, item.name.trim().toLocaleLowerCase(),
      '/api/artist-image?' + new URLSearchParams({name: item.name}))
      .then(data => {
        if (!data || !data.artwork_url) return;
        const image = document.createElement('img');
        image.alt = '';
        image.decoding = 'async';
        image.onerror = () => image.remove();
        image.src = data.artwork_url;
        frame.append(image);
      })
      .catch(() => {});
  };
  if (remoteArtworkObserver) remoteArtworkObserver.observe(frame);
  else frame.loadRemoteArtwork();
  return frame;
}

function buildArtistChip(item) {
  const row = document.createElement('li');
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'library-artist';
  button.append(buildArtistPhoto(item, 300));
  const text = document.createElement('span');
  text.className = 'library-artist-text';
  addTextElement(text, 'span', 'library-artist-name', item.name);
  if (item.owned) addTextElement(text, 'span', 'library-artist-count', 'In your library');
  button.append(text);
  button.addEventListener('click', () => libraryOpen(artistTarget(item)));
  row.append(button);
  return row;
}

// A section that is unavailable says why; one that is available and empty says there is nothing.
const SECTION_REASON_MESSAGES = {
  source_disabled: 'This needs a service that is not configured.',
  source_failed: 'This could not be loaded right now.',
  deadline: 'This took too long to load.',
  not_in_this_build: 'This is not available yet.',
};

function setSectionNote(id, message) {
  const note = $(id);
  note.textContent = message || '';
  note.hidden = !message;
}

function fillRows(list, items, build, limit = Infinity) {
  list.replaceChildren();
  items.slice(0, limit).forEach((item, index) => list.append(build(item, index)));
}

// Artist and album pages show a random few of the similar artists, as circles across the page.
const SIMILAR_ARTISTS_SHOWN = 5;
const SIMILAR_ALBUMS_SHOWN = 7;

function randomSample(items, count) {
  const pool = [...items];
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  return pool.slice(0, count);
}

// ---- Artist view ----
// Opens from a search result, a library row, an album, a similar artist or a genre. An owned
// artist is addressed by key and Navidrome ID; any other by key, name and MusicBrainz ID.

function setArtistHero(target, name) {
  const stage = document.querySelector('.artist-stage');
  stage.querySelector('.artist-hero-art')?.remove();
  // The photo fills a wide stage, so it asks for the large size.
  const frame = buildArtwork(sizedArtwork(target.artworkUrl, ARTIST_HERO_PHOTO_SIZE), 'artist-hero-art');
  // It is the first thing on the page, so it must not wait for the lazy-loading threshold.
  frame.querySelector('img')?.setAttribute('loading', 'eager');
  stage.prepend(frame);
  const seq = libraryView.detailSeq;
  tintArtistPage(sizedArtwork(target.artworkUrl, ARTIST_HERO_PHOTO_SIZE), seq);
  if (target.artworkUrl || !name) return;
  cachedJSONRequest(artistImageRequests, name.trim().toLocaleLowerCase(), '/api/artist-image?' + new URLSearchParams({name}))
    .then(data => {
      if (seq !== libraryView.detailSeq || !data || !data.artwork_url) return;
      const image = document.createElement('img');
      image.alt = '';
      image.decoding = 'async';
      image.onerror = () => image.remove();
      image.src = data.artwork_url;
      frame.append(image);
      tintArtistPage(data.artwork_url, seq);
    })
    .catch(() => {});
}

const ARTIST_HERO_PHOTO_SIZE = 1000;
const ARTIST_TAGS_SHOWN = 3;
const TOP_SONGS_SHOWN = 5;
const MISSING_ALBUMS_SHOWN = 10;

function setArtistBio(bio) {
  const text = $('artistBio');
  text.textContent = bio && bio.text ? bio.text : '';
  text.hidden = !text.textContent;
  $('artistBioToggle').setAttribute('aria-expanded', 'false');
  fitArtistBio();
}

// The bio is clamped to three lines on a wide screen (six on a phone). "Read more" appears only
// when the text really overflows, so a short bio shows whole and the link never opens nothing.
function fitArtistBio() {
  const text = $('artistBio');
  const toggle = $('artistBioToggle');
  // A page that is not on screen has no layout to measure; the next resize or visit fits it.
  if (text.hidden || !text.clientWidth || toggle.getAttribute('aria-expanded') === 'true') return;
  text.classList.add('is-clamped');
  const overflows = text.scrollHeight > text.clientHeight + 1;
  text.classList.toggle('is-clamped', overflows);
  toggle.hidden = !overflows;
  toggle.textContent = 'Read more';
}

function toggleArtistBio() {
  const text = $('artistBio');
  const clamped = text.classList.toggle('is-clamped');
  $('artistBioToggle').textContent = clamped ? 'Read more' : 'Show less';
  $('artistBioToggle').setAttribute('aria-expanded', String(!clamped));
}

function renderArtist(target) {
  const view = libraryView;
  const seq = ++view.detailSeq;
  libraryShow('artist');
  clearPageTint('libraryDetailView');
  setArtistHero(target, target.name);
  const heading = $('artistDetailHeading');
  const status = $('artistDetailStatus');
  heading.textContent = target.name || 'Loading artist…';
  setArtistBio(null);
  fillRows($('artistTags'), [], () => null);
  $('artistTags').hidden = true;
  for (const id of ['artistOwnedAlbums', 'artistMissingAlbums', 'artistSimilar', 'artistTopSongs']) $(id).replaceChildren();
  $('artistOwnedSection').hidden = true;
  $('artistMissingAll').hidden = true;
  $('artistTopSongsAll').hidden = true;
  $('artistTopSongsSection').hidden = false;
  document.querySelector('.artist-hero').classList.remove('no-songs');
  setSectionNote('artistTopSongsNote', 'Loading top songs…');
  setSectionNote('artistMissingNote', 'Loading missing albums…');
  setSectionNote('artistSimilarNote', 'Loading similar artists…');
  $('artistMissingSection').hidden = false;
  $('artistSimilarSection').hidden = false;
  setStatus(status, 'Loading…', 'loading');
  if (!applyingHash) heading.focus();

  const params = new URLSearchParams();
  if (target.id) params.set('id', target.id);
  if (target.name) params.set('name', target.name);
  if (target.mbid) params.set('mbid', target.mbid);
  const source = new EventSource('/api/artists/' + encodeURIComponent(target.key) + '?' + params);
  libraryStreams.add(source);
  const ctx = {name: target.name, missing: null, artistShown: false};
  libraryView.artistCtx = ctx;
  source.addEventListener('section', event => {
    if (seq !== view.detailSeq) return;
    applyArtistSection(JSON.parse(event.data), ctx);
  });
  source.addEventListener('done', () => {
    source.close();
    libraryStreams.delete(source);
    if (seq === view.detailSeq && !ctx.artistShown) setStatus(status, 'This artist could not be loaded. Try again.', 'error');
  });
  source.addEventListener('error', async () => {
    source.close();
    libraryStreams.delete(source);
    if (seq !== view.detailSeq || ctx.artistShown) return;
    // A closed stream does not say why. A plain request tells a missing artist from a failure.
    let missing = false;
    try {
      const response = await fetch('/api/artists/' + encodeURIComponent(target.key) + '?' + params);
      missing = response.status === 404;
      if (response.status === 409 && !target.id) {
        // Several library artists share this name: open the one with the most albums.
        const best = (await response.json()).candidates.sort((a, b) => b.album_count - a.album_count)[0];
        if (seq === view.detailSeq && best) {
          libraryNav.current = {...target, id: best.id};
          renderArtist(libraryNav.current);
          return;
        }
      }
    } catch (error) {
      missing = false;
    }
    if (seq !== view.detailSeq) return;
    heading.textContent = missing ? 'Artist not found' : target.name || 'Artist';
    setStatus(status, missing ? 'This artist is no longer in your library.' : 'This artist could not be loaded. Try again.', 'error');
  });
}

// Albums the providers list without a year get one from the catalogue batch lookup, one request
// for the page, and the list is repainted with what it finds.
async function fillMissingYears(ctx) {
  const missing = (ctx.missing || []).filter(item => !item.year);
  if (!missing.length || ctx.yearsRequested) return;
  ctx.yearsRequested = true;
  const seq = libraryView.detailSeq;
  try {
    const data = await sendJSON('/api/album-years', 'POST', {items: missing.map(item => ({artist: item.artist, album: item.name}))});
    if (seq !== libraryView.detailSeq) return;
    const years = new Map(((data && data.years) || []).map(entry => [albumYearKey(entry.artist, entry.album), entry.year]));
    let changed = false;
    for (const item of missing) {
      const year = years.get(albumYearKey(item.artist, item.name));
      if (year) { item.year = year; changed = true; }
    }
    if (changed) paintMissingAlbums(ctx);
  } catch (error) {
    // Years are decoration; the list stays as it is.
  }
}

function paintMissingAlbums(ctx) {
  const items = ctx.missing || [];
  fillRows($('artistMissingAlbums'), items, item => buildAlbumRow({...item, showListens: true}),
    ctx.showAllMissing ? Infinity : MISSING_ALBUMS_SHOWN);
  const allButton = $('artistMissingAll');
  allButton.hidden = ctx.showAllMissing || items.length <= MISSING_ALBUMS_SHOWN;
  allButton.onclick = () => {
    ctx.showAllMissing = true;
    paintMissingAlbums(ctx);
  };
}

// Some libraries tag albums "Re-Foc (2002)". Cards and the album page show the year on its own line,
// so the displayed name drops the suffix. Links, keys and requests keep the library's own name.
const ALBUM_YEAR_SUFFIX = /\s*[(\[]\s*(?:19|20)\d{2}\s*[)\]]\s*$/;

function displayAlbumName(name) {
  const text = String(name || '');
  return text.replace(ALBUM_YEAR_SUFFIX, '') || text;
}

// An album the library owns, as a card: cover, name, year and the green check.
function buildOwnedAlbumCard(item) {
  const row = document.createElement('li');
  const open = document.createElement('button');
  open.type = 'button';
  open.className = 'owned-album-card';
  const art = buildAlbumArtwork(item, 'owned-album-art', 400);
  art.append(buildOwnedCheck());
  open.append(art);
  addTextElement(open, 'span', 'owned-album-name', displayAlbumName(item.name));
  if (item.year) addTextElement(open, 'span', 'owned-album-year', item.year);
  open.addEventListener('click', () => libraryOpen(albumTarget(item)));
  row.append(open);
  return row;
}

// A top song: rank, title, album, listens, and a check when the library has it. Songs do not open.
function buildTopSongRow(item) {
  const row = document.createElement('li');
  row.className = 'top-song';
  addTextElement(row, 'span', 'top-song-rank', item.rank);
  const text = document.createElement('span');
  text.className = 'top-song-text';
  addTextElement(text, 'span', 'top-song-name', item.name).title = item.name;
  if (item.album) addTextElement(text, 'span', 'top-song-album', item.album);
  row.append(text);
  const listens = addTextElement(row, 'span', 'top-song-listens', item.listen_count ? compactCount(item.listen_count) : '');
  if (item.listen_count) {
    listens.title = Number(item.listen_count).toLocaleString() + ' listens on ' + (item.source === 'lastfm' ? 'Last.fm' : 'ListenBrainz');
  }
  // A song the library lacks gets its own Get when the source named its album, which is where it is filed.
  row.append(item.owned ? buildOwnedCheck()
    : item.album && item.artist
      ? wrapInActionGroup(createTrackGetButton({artist: item.artist, album: item.album, title: item.name}), 'Actions for ' + item.name)
    : document.createElement('span'));
  return row;
}

function paintTopSongs(ctx) {
  const items = ctx.topSongs || [];
  fillRows($('artistTopSongs'), items.map(song => ({...song, artist: ctx.name})), buildTopSongRow, ctx.showAllSongs ? Infinity : TOP_SONGS_SHOWN);
  const allButton = $('artistTopSongsAll');
  allButton.hidden = ctx.showAllSongs || items.length <= TOP_SONGS_SHOWN;
  allButton.onclick = () => {
    ctx.showAllSongs = true;
    paintTopSongs(ctx);
  };
}

// Without top songs the panel goes away and the photo takes the full width.
function hideTopSongs() {
  $('artistTopSongsSection').hidden = true;
  document.querySelector('.artist-hero').classList.add('no-songs');
}

function applyArtistSection(section, ctx) {
  const status = $('artistDetailStatus');
  if (section.section === 'artist') {
    if (!section.available) {
      $('artistDetailHeading').textContent = ctx.name || 'Artist';
      setStatus(status, INDEX_REASON_MESSAGES[section.reason] || 'This artist is not available right now.',
        section.reason === 'index_building' ? 'loading' : 'error');
      return;
    }
    const artist = section.artist;
    ctx.artistShown = true;
    ctx.name = artist.name;
    ctx.owned = artist.owned;
    $('artistDetailHeading').textContent = artist.name;
    setStatus(status, artist.owned ? pluralize(artist.album_count, 'album', 'albums') + ' in your library' : 'Not in your library', 'idle');
  } else if (section.section === 'owned_albums') {
    if (!section.available || !section.items.length) return;
    fillRows($('artistOwnedAlbums'), section.items.map(album => ({...album, owned: true, artist: ctx.name})), buildOwnedAlbumCard);
    $('artistOwnedSection').hidden = false;
  } else if (section.section === 'bio') {
    setArtistBio(section.bio);
  } else if (section.section === 'tags') {
    const tags = $('artistTags');
    fillRows(tags, section.items || [], tag => {
      const item = document.createElement('li');
      item.append(buildLibraryLink(tag.name, {type: 'genre', tag: tag.name}, 'genre-text-link'));
      return item;
    }, ARTIST_TAGS_SHOWN);
    tags.hidden = !tags.childElementCount;
  } else if (section.section === 'top_songs') {
    if (!section.available || !section.items.length) {
      hideTopSongs();
      return;
    }
    ctx.topSongs = section.items;
    setSectionNote('artistTopSongsNote', '');
    paintTopSongs(ctx);
  } else if (section.section === 'missing_albums') {
    if (section.available) {
      ctx.missing = section.items.map(item => ({...item, artist: ctx.name, owned: false}));
      paintMissingAlbums(ctx);
      fillMissingYears(ctx);
      if (!section.items.length) setSectionNote('artistMissingNote', 'You have every album we could find.');
      else setSectionNote('artistMissingNote', section.complete ? '' : 'Some albums may be missing. Popularity could not be fully loaded.');
    } else {
      setSectionNote('artistMissingNote', SECTION_REASON_MESSAGES[section.reason] || 'Missing albums are not available right now.');
    }
  } else if (section.section === 'similar') {
    if (section.available && section.items.length) {
      fillRows($('artistSimilar'), randomSample(section.items, SIMILAR_ARTISTS_SHOWN), buildArtistChip);
      // A tag lookup that ran out of time only changes the order, so the list needs no warning.
      setSectionNote('artistSimilarNote', '');
    } else {
      setSectionNote('artistSimilarNote', section.available ? 'No similar artists found.'
        : SECTION_REASON_MESSAGES[section.reason] || 'Similar artists are not available right now.');
    }
  }
}

// ---- Album view ----
// Header, tracklist, then similar artists and similar albums the library does not have. The same
// view serves owned and unowned albums; only the state control differs.

function formatDuration(seconds) {
  if (!seconds) return '';
  return Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0');
}

// The album page's Info and Reviews tabs. Info is the description (Apple Music's notes, or the
// Wikipedia lead when Apple has none); Reviews are up to three outlets' summary lines, each with a
// link to the full review, fetched the first time the tab opens. An album with no description opens
// on Reviews unless the reader already picked a tab.
const albumTabState = {selected: 'info', chosen: false, reviews: 'idle', reviewSeq: 0};
const albumTabButtons = [...document.querySelectorAll('[data-album-tab]')];
const albumTabPanels = {info: 'albumInfoPanel', reviews: 'albumReviewsPanel'};

function selectAlbumTab(name, {byReader = true, moveFocus = false} = {}) {
  if (byReader) albumTabState.chosen = true;
  albumTabState.selected = name;
  for (const tab of albumTabButtons) {
    const active = tab.dataset.albumTab === name;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
    // Only the selected tab stays in the document tab order.
    tab.setAttribute('tabindex', active ? '0' : '-1');
    if (active && moveFocus) tab.focus();
  }
  for (const [tabName, id] of Object.entries(albumTabPanels)) $(id).hidden = tabName !== name;
  if (name === 'info') fitAlbumDescription();
  if (name === 'reviews' && albumTabState.reviews === 'idle') loadAlbumReviews();
}

function moveAlbumTab(from, step) {
  const index = albumTabButtons.indexOf(from);
  selectAlbumTab(albumTabButtons[(index + step + albumTabButtons.length) % albumTabButtons.length].dataset.albumTab,
    {moveFocus: true});
}

function resetAlbumTabs() {
  albumTabState.reviews = 'idle';
  albumTabState.reviewSeq++;
  albumTabState.chosen = false;
  $('albumReviews').replaceChildren();
  $('albumReviewsRetry').hidden = true;
  setSectionNote('albumReviewsNote', '');
  selectAlbumTab('info', {byReader: false});
}

function buildAlbumReview(review) {
  const item = document.createElement('li');
  item.className = 'album-review';
  const quote = document.createElement('blockquote');
  addTextElement(quote, 'p', '', '\u201c' + review.quote + '\u201d');
  item.append(quote);
  const link = document.createElement('a');
  link.className = 'album-review-link';
  link.href = review.url;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.textContent = 'Read the full review at ' + review.source;
  item.append(link);
  return item;
}

async function loadAlbumReviews() {
  const album = albumPage.album || albumPage.target;
  if (!album || !album.artist || !album.name) {
    setSectionNote('albumReviewsNote', 'Reviews are not available for this album.');
    return;
  }
  const seq = albumTabState.reviewSeq;
  albumTabState.reviews = 'loading';
  $('albumReviewsRetry').hidden = true;
  setSectionNote('albumReviewsNote', 'Loading reviews\u2026');
  const params = new URLSearchParams({artist: album.artist, album: album.name});
  let data;
  try {
    data = await requestJSON('/api/album-reviews?' + params);
  } catch (error) {
    if (seq !== albumTabState.reviewSeq) return;
    albumTabState.reviews = 'idle';
    setSectionNote('albumReviewsNote', 'Reviews could not be loaded.');
    $('albumReviewsRetry').hidden = false;
    return;
  }
  if (seq !== albumTabState.reviewSeq) return;
  const reviews = Array.isArray(data.reviews) ? data.reviews : [];
  $('albumReviews').replaceChildren(...reviews.map(buildAlbumReview));
  // A partial answer is shown as it is; only the button asks the outlets that failed again, so
  // switching tabs never re-requests or flickers.
  albumTabState.reviews = 'loaded';
  $('albumReviewsRetry').hidden = !data.retryable;
  setSectionNote('albumReviewsNote', reviews.length ? (data.retryable ? 'Some sources did not answer.' : '')
    : data.retryable ? 'No reviews found. Some sources did not answer.' : 'No reviews found for this album.');
}

// The description's first paragraph shows, three lines of it (six on a phone). "Read more"
// appears only when there is more to show: a second paragraph or a first one that overflows.
// null means a new album is loading; an answer without paragraphs says so on the Info tab.
function setAlbumDescription(description) {
  const box = $('albumDescription');
  const text = $('albumDescriptionText');
  const paragraphs = description && Array.isArray(description.paragraphs) ? description.paragraphs : [];
  text.replaceChildren();
  box.hidden = !paragraphs.length;
  setSectionNote('albumInfoNote', paragraphs.length ? '' : description ? 'No description found for this album.'
    : 'Loading description\u2026');
  $('albumDescriptionToggle').hidden = true;
  $('albumDescriptionToggle').setAttribute('aria-expanded', 'false');
  if (!paragraphs.length) {
    if (description && !albumTabState.chosen) selectAlbumTab('reviews', {byReader: false});
    return;
  }
  for (const paragraph of paragraphs) addTextElement(text, 'p', '', paragraph);
  const link = $('albumDescriptionLink');
  link.href = description.url || '#';
  link.hidden = !description.url;
  link.textContent = description.source || 'Apple Music';
  $('albumDescriptionLicense').textContent = description.license ? ' \u00b7 ' + description.license : '';
  fitAlbumDescription();
}

function fitAlbumDescription() {
  const box = $('albumDescription');
  const text = $('albumDescriptionText');
  const toggle = $('albumDescriptionToggle');
  // A page that is not on screen has no layout to measure; the next resize or visit fits it.
  if (box.hidden || !text.clientWidth || toggle.getAttribute('aria-expanded') === 'true') return;
  text.classList.add('is-collapsed');
  const first = text.firstElementChild;
  const long = text.childElementCount > 1 || first.scrollHeight > first.clientHeight + 1;
  text.classList.toggle('is-collapsed', long);
  toggle.hidden = !long;
  toggle.textContent = 'Read more';
}

function toggleAlbumDescription() {
  const collapsed = $('albumDescriptionText').classList.toggle('is-collapsed');
  $('albumDescriptionToggle').textContent = collapsed ? 'Read more' : 'Show less';
  $('albumDescriptionToggle').setAttribute('aria-expanded', String(!collapsed));
}

function renderAlbum(target) {
  const view = libraryView;
  const seq = ++view.albumSeq;
  libraryShow('album');
  const heading = $('albumHeading');
  const status = $('albumStatus');
  heading.textContent = displayAlbumName(target.name) || 'Loading album…';
  $('albumArtist').replaceChildren();
  $('albumYear').textContent = target.year || '';
  $('albumGenre').replaceChildren();
  $('albumSummary').textContent = '';
  $('albumOwnership').hidden = target.owned !== false;
  clearPageTint('libraryAlbumView');
  $('albumAction').replaceChildren();
  albumPage.album = null;
  albumPage.target = target;
  $('albumTracks').replaceChildren();
  for (const id of ['albumSimilarArtists', 'albumSimilarAlbums']) $(id).replaceChildren();
  $('albumSimilarAlbumsAll').hidden = true;
  resetAlbumTabs();
  setAlbumDescription(null);
  setSectionNote('albumTracksNote', 'Loading tracklist…');
  setSectionNote('albumSimilarArtistsNote', 'Loading similar artists…');
  setSectionNote('albumSimilarAlbumsNote', 'Loading similar albums…');
  setStatus(status, '', 'idle');
  setAlbumHero(target, seq);
  setAlbumPagePlatformLinks(target.artist, target.name, target.mbid);
  if (!applyingHash) heading.focus();

  const params = new URLSearchParams();
  if (target.id) params.set('id', target.id);
  if (target.artist) params.set('artist', target.artist);
  if (target.name) params.set('name', target.name);
  if (target.year) params.set('year', String(target.year));
  if (target.mbid) params.set('mbid', target.mbid);
  const source = new EventSource('/api/albums/' + target.key.split('/').map(encodeURIComponent).join('/') + '?' + params);
  libraryStreams.add(source);
  let shown = false;
  source.addEventListener('section', event => {
    if (seq !== view.albumSeq) return;
    shown = applyAlbumSection(JSON.parse(event.data), target) || shown;
  });
  source.addEventListener('done', () => {
    source.close();
    libraryStreams.delete(source);
  });
  source.addEventListener('error', () => {
    source.close();
    libraryStreams.delete(source);
    if (seq !== view.albumSeq || shown) return;
    setStatus(status, 'This album could not be loaded. Try again.', 'error');
  });
}

// The album page takes its backdrop from the cover. The picture is shrunk to a small canvas, its
// pixels are counted in coarse colour buckets (grey and near-black or near-white pixels count
// for little, so a vivid cover is not averaged to mud), and the winning bucket is darkened until
// the page text stays readable. Covers that cannot be read (a host without CORS headers, a
// failed load) leave the normal background in place.
function dominantColor(image) {
  const size = 32;
  const canvas = document.createElement('canvas');
  canvas.width = size; canvas.height = size;
  const context = canvas.getContext('2d', {willReadFrequently: true});
  context.drawImage(image, 0, 0, size, size);
  const {data} = context.getImageData(0, 0, size, size);
  const buckets = new Map();
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 200) continue;
    const r = data[i], g = data[i + 1], b = data[i + 2];
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const saturation = max ? (max - min) / max : 0;
    const weight = 0.15 + saturation * saturation * (max > 40 && max < 245 ? 1 : 0.2);
    const key = (r >> 5) << 6 | (g >> 5) << 3 | (b >> 5);
    const bucket = buckets.get(key) || {weight: 0, r: 0, g: 0, b: 0};
    bucket.weight += weight;
    bucket.r += r * weight; bucket.g += g * weight; bucket.b += b * weight;
    buckets.set(key, bucket);
  }
  let best = null;
  for (const bucket of buckets.values()) if (!best || bucket.weight > best.weight) best = bucket;
  return best ? [best.r / best.weight, best.g / best.weight, best.b / best.weight] : null;
}

// Keeps the hue, caps lightness and saturation: the page text is light, so the tint stays dark.
function backdropTint([r, g, b]) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h = 0, s = 0;
  const l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h *= 60;
  }
  return 'hsl(' + Math.round(h) + ' ' + Math.round(Math.min(s, 0.7) * 100) + '% ' + Math.round(Math.min(l, 0.3) * 100) + '%)';
}

function clearPageTint(viewId) {
  const view = $(viewId);
  view.classList.remove('has-tint');
  view.style.removeProperty('--page-tint');
}

// `current` says whether the page the picture was meant for is still the one open.
function tintPage(viewId, url, current) {
  if (!url) return;
  const image = new Image();
  image.crossOrigin = 'anonymous';
  image.decoding = 'async';
  image.onload = () => {
    if (!current()) return;
    try {
      const color = dominantColor(image);
      if (!color) return;
      const view = $(viewId);
      view.style.setProperty('--page-tint', backdropTint(color));
      view.classList.add('has-tint');
    } catch (error) { /* tainted canvas: keep the default background */ }
  };
  image.src = url;
}

function tintAlbumPage(url, seq) {
  tintPage('libraryAlbumView', url, () => seq === libraryView.albumSeq);
}

function tintArtistPage(url, seq) {
  tintPage('libraryDetailView', url, () => seq === libraryView.detailSeq);
}

function setAlbumHero(target, seq) {
  const hero = document.querySelector('.album-hero-art-wrap');
  hero.querySelector('.album-hero-art')?.remove();
  const frame = buildAlbumArtwork({
    artwork_url: target.artworkUrl, owned: target.owned, artist: target.artist, name: target.name,
  }, 'album-hero-art', 500);
  tintAlbumPage(sizedArtwork(target.artworkUrl, 500), seq);
  frame.onRemoteArtwork = data => {
    if (seq === libraryView.albumSeq && data.year && !$('albumYear').textContent) $('albumYear').textContent = data.year;
    if (seq === libraryView.albumSeq) tintAlbumPage(data.artwork_url, seq);
  };
  hero.prepend(frame);
}

// The genre sits before the year, as a link to its page; an album with none shows the year alone.
function setAlbumGenre(genre) {
  const box = $('albumGenre');
  box.replaceChildren();
  if (genre) box.append(buildLibraryLink(genre, {type: 'genre', tag: genre}, 'genre-text-link'));
}

// The album the open page shows, as its album section reported it; track rows read it for their Get.
const albumPage = {album: null, target: null};

// The album's own state: a green check when every song is in the library, the Get button when not.
// Before the tracklist arrives an owned album shows the check, as it always did.
function setAlbumAction(album, tracks) {
  const complete = tracks ? tracks.every(track => track.owned) : Boolean(album.owned);
  const state = buildAlbumState({
    owned: complete, artist: album.artist, name: album.name, year: album.year,
    release_group_mbid: album.release_group_mbid,
  });
  $('albumAction').replaceChildren(complete ? state : wrapInActionGroup(state, 'Actions for ' + album.name));
}

// A track: number, title, length, and a green check when the library has the song.
function buildTrackRow(track, index) {
  const row = document.createElement('li');
  row.className = 'track';
  addTextElement(row, 'span', 'track-number', track.track_number || index + 1);
  addTextElement(row, 'span', 'track-title', track.title);
  addTextElement(row, 'span', 'track-duration', formatDuration(track.duration_seconds));
  // A song the library lacks gets its own Get, once the album it belongs to is known.
  const album = albumPage.album;
  row.append(track.owned ? buildOwnedCheck()
    : album ? wrapInActionGroup(createTrackGetButton({
        artist: album.artist, album: album.name, title: track.title,
        track_number: track.track_number || index + 1, year: album.year,
      }), 'Actions for ' + track.title)
    : document.createElement('span'));
  return row;
}

// "17 songs, 1 hour 1 minute", plus how many the library has when it has some but not all.
function albumSummary(tracks) {
  const parts = [pluralize(tracks.length, 'song', 'songs')];
  const seconds = tracks.reduce((sum, track) => sum + (track.duration_seconds || 0), 0);
  if (tracks.every(track => track.duration_seconds) && seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.round((seconds % 3600) / 60);
    parts[0] += ', ' + [hours ? pluralize(hours, 'hour', 'hours') : '', minutes || !hours ? pluralize(minutes, 'minute', 'minutes') : ''].filter(Boolean).join(' ');
  }
  const owned = tracks.filter(track => track.owned).length;
  if (owned && owned < tracks.length) parts.push(owned + ' in your library');
  return parts.join(' · ');
}

function applyAlbumSection(section, target) {
  if (section.section === 'album') {
    const album = section.album;
    $('albumHeading').textContent = displayAlbumName(album.name);
    if (album.artwork_url && !target.artworkUrl) {
      const wrap = document.querySelector('.album-hero-art-wrap');
      wrap.querySelector('.album-hero-art')?.remove();
      wrap.prepend(buildArtwork(sizedArtwork(album.artwork_url, 500), 'album-hero-art'));
      tintAlbumPage(sizedArtwork(album.artwork_url, 500), libraryView.albumSeq);
    }
    $('albumYear').textContent = album.year || $('albumYear').textContent;
    $('albumOwnership').hidden = Boolean(album.owned);
    const artist = $('albumArtist');
    artist.replaceChildren();
    artist.append(buildLibraryLink(album.artist, {
      type: 'artist', id: album.owned ? album.artist_id : null, key: album.artist_key,
      name: album.artist, mbid: null, artworkUrl: null,
    }, 'library-link'));
    setAlbumPagePlatformLinks(album.artist, album.name, album.release_group_mbid);
    albumPage.album = album;
    setAlbumAction(album);
    return true;
  }
  if (section.section === 'year') {
    // The year may come from the library, the caller or a catalogue lookup, whichever knows it.
    if (section.year) $('albumYear').textContent = section.year;
    return false;
  }
  if (section.section === 'description') {
    setAlbumDescription(section.description);
    return false;
  }
  if (section.section === 'genre') {
    setAlbumGenre(section.available ? section.genre : null);
    return false;
  }
  if (section.section === 'tracks') {
    if (section.available && section.items.length) {
      fillRows($('albumTracks'), section.items, buildTrackRow);
      // Album Get stays until every song is in the library, then becomes the check.
      if (albumPage.album) setAlbumAction(albumPage.album, section.items);
      $('albumSummary').textContent = albumSummary(section.items);
      setSectionNote('albumTracksNote', '');
    } else {
      setSectionNote('albumTracksNote', section.available ? 'No tracklist was found for this album.'
        : SECTION_REASON_MESSAGES[section.reason] || 'The tracklist is not available right now.');
    }
  } else if (section.section === 'similar_artists') {
    if (section.available && section.items.length) {
      fillRows($('albumSimilarArtists'), randomSample(section.items, SIMILAR_ARTISTS_SHOWN), buildArtistChip);
      setSectionNote('albumSimilarArtistsNote', '');
    } else {
      setSectionNote('albumSimilarArtistsNote', section.available ? 'No similar artists found.'
        : SECTION_REASON_MESSAGES[section.reason] || 'Similar artists are not available right now.');
    }
  } else if (section.section === 'similar_albums') {
    if (section.available && section.items.length) {
      const showSimilarAlbums = all => {
        fillRows($('albumSimilarAlbums'), section.items, item => buildAlbumRow({...item, showArtist: true}),
          all ? Infinity : SIMILAR_ALBUMS_SHOWN);
      };
      showSimilarAlbums(false);
      const allButton = $('albumSimilarAlbumsAll');
      allButton.hidden = section.items.length <= SIMILAR_ALBUMS_SHOWN;
      allButton.onclick = () => {
        showSimilarAlbums(true);
        allButton.hidden = true;
      };
      setSectionNote('albumSimilarAlbumsNote', '');
    } else {
      setSectionNote('albumSimilarAlbumsNote', section.available ? 'No similar albums found.'
        : SECTION_REASON_MESSAGES[section.reason] || 'Similar albums are not available right now.');
    }
  }
  return false;
}

// ---- Genre view (SEARCH_CONTRACT P4) ----
// Opens from a tag, a genre result or a genre name. Every artist and album in it opens its page;
// items not in the library carry the Discogs attribution where Discogs supplied them.

const GENRE_SECTION_NAMES = {artists: 'artists', albums: 'albums'};

function buildGenreItem(item, type) {
  const row = document.createElement('li');
  row.className = 'library-album';
  const target = type === 'artists' ? artistTarget(item) : albumTarget(item);
  row.append(buildLibraryLink(item.name, target, 'genre-item-link'));
  const detail = [];
  if (type === 'albums') detail.push(item.artist, item.year);
  detail.push(item.owned ? 'In your library' : 'Not in your library');
  addTextElement(row, 'span', 'library-album-detail', detail.filter(value => value !== null && value !== undefined && value !== '').join(' · '));
  if (item.attribution) addTextElement(row, 'span', 'library-album-detail', item.attribution);
  return row;
}

async function renderGenre(tag) {
  const view = libraryView;
  const seq = ++view.genreSeq;
  libraryShow('genre');
  const heading = $('genreHeading');
  const status = $('genreStatus');
  heading.textContent = tag;
  $('genreArtists').replaceChildren();
  $('genreAlbums').replaceChildren();
  setStatus(status, 'Loading…', 'loading');
  if (!applyingHash) heading.focus();
  try {
    const response = await fetch('/api/genres/' + encodeURIComponent(tag));
    const data = await response.json();
    if (seq !== view.genreSeq) return;
    if (!response.ok) throw new Error(data.message || 'Request failed');
    let count = 0;
    let incomplete = false;
    for (const name of Object.keys(GENRE_SECTION_NAMES)) {
      const section = data.sections[name];
      const list = name === 'artists' ? $('genreArtists') : $('genreAlbums');
      if (!section.available) continue;
      for (const item of section.items) list.append(buildGenreItem(item, name));
      count += section.items.length;
      if (!section.complete) incomplete = true;
    }
    if (!count) {
      setStatus(status, incomplete ? 'Nothing could be loaded for this genre right now. Try again.' : 'Nothing found for this genre.', incomplete ? 'error' : 'empty');
    } else {
      setStatus(status, pluralize(count, 'item', 'items') + (incomplete ? ' · Some sources did not answer, so this list may be incomplete' : ''), 'progress');
    }
  } catch (error) {
    if (seq !== view.genreSeq) return;
    setStatus(status, 'This genre could not be loaded. Try again.', 'error');
  }
}

// ---- Wiring ----

function refreshLibrary() {
  saveLibraryPrefs();
  syncLibraryControls();
  loadLibrary({reset: true});
}
loadLibraryPrefs();
syncLibraryControls();

$('globalSearch').addEventListener('submit', event => {
  event.preventDefault();
  rememberSearch($('globalSearchInput').value);
  startGlobalSearch($('globalSearchInput').value);
});
$('searchToggle').addEventListener('click', () => setSearchExpanded(true, {focus: true}));
$('globalSearchInput').addEventListener('focus', showRecentSearches);
$('globalSearchInput').addEventListener('click', showRecentSearches);
$('globalSearchRecent').addEventListener('click', event => {
  const button = event.target.closest('button[data-recent-search]');
  if (!button) return;
  const input = $('globalSearchInput');
  input.value = button.dataset.recentSearch;
  hideRecentSearches();
  rememberSearch(input.value);
  startGlobalSearch(input.value);
  input.focus();
});
$('globalSearchInput').addEventListener('input', () => {
  hideRecentSearches();
  clearTimeout(globalSearch.timer);
  globalSearch.timer = setTimeout(() => startGlobalSearch($('globalSearchInput').value), SEARCH_DEBOUNCE_MS);
});
// Escape works from the input and from any result, because keydown bubbles to the form.
$('globalSearch').addEventListener('keydown', event => {
  if (event.key === 'Escape' && !$('globalSearchResults').hidden) {
    event.preventDefault();
    closeGlobalSearch({focusInput: true});
  } else if (event.key === 'Escape' && !$('globalSearchRecent').hidden) {
    event.preventDefault();
    closeGlobalSearch({focusInput: true});
  } else if (event.key === 'Escape' && $('globalSearch').classList.contains('is-expanded')) {
    event.preventDefault();
    setSearchExpanded(false);
    $('searchToggle').focus();
  }
});
// Close when focus moves to a real element outside the form. Safari does not focus buttons on
// click, so a null relatedTarget must not close the panel before the click lands.
$('globalSearch').addEventListener('focusout', event => {
  const next = event.relatedTarget;
  if (next && !$('globalSearch').contains(next)) closeGlobalSearch();
});
document.addEventListener('click', event => {
  if (!$('globalSearch').contains(event.target)) closeGlobalSearch();
});
// The X shows only while the field holds text, and takes the magnifier's place.
function syncLibraryFilterClear() {
  const has = Boolean($('libraryFilter').value);
  $('libraryFilterClear').hidden = !has;
  $('libraryFilterIcon').style.display = has ? 'none' : '';
}

function clearLibrarySearch() {
  $('libraryFilter').value = '';
  syncLibraryFilterClear();
  closeSearchSurface(librarySearch);
}

$('libraryFilterClear').addEventListener('click', () => {
  clearLibrarySearch();
  $('libraryFilter').focus();
});
$('libraryFilter').addEventListener('input', () => {
  syncLibraryFilterClear();
  clearTimeout(librarySearch.timer);
  librarySearch.timer = setTimeout(() => startSearch(librarySearch, $('libraryFilter').value), SEARCH_DEBOUNCE_MS);
});
// Escape clears the search and returns to the browse list.
$('libraryFilter').addEventListener('keydown', event => {
  if (event.key !== 'Escape' || !$('libraryFilter').value) return;
  event.preventDefault();
  clearLibrarySearch();
});
for (const button of document.querySelectorAll('[data-library-tab]')) {
  button.addEventListener('click', () => {
    if (libraryView.tab === button.dataset.libraryTab) return;
    libraryView.tab = button.dataset.libraryTab;
    libraryView.sort = LIBRARY_TABS[libraryView.tab].sorts[0][0];
    libraryView.order = '';
    refreshLibrary();
  });
}
$('librarySort').addEventListener('change', () => {
  libraryView.sort = $('librarySort').value;
  libraryView.order = '';
  refreshLibrary();
});
$('libraryOrder').addEventListener('click', () => {
  libraryView.order = libraryOrder() === 'asc' ? 'desc' : 'asc';
  refreshLibrary();
});
for (const button of document.querySelectorAll('[data-library-display]')) {
  button.addEventListener('click', () => {
    if (libraryView.display === button.dataset.libraryDisplay) return;
    libraryView.display = button.dataset.libraryDisplay;
    refreshLibrary();
  });
}
// The slider only resizes tiles already on screen, so dragging it never reloads the list.
$('libraryTileSize').addEventListener('input', () => {
  libraryView.tileSize = Number($('libraryTileSize').value);
  $('libraryList').style.setProperty('--tile-size', libraryView.tileSize + 'px');
  $('libraryTileSize').setAttribute('aria-valuetext', libraryView.tileSize + ' pixels');
});
$('libraryTileSize').addEventListener('change', saveLibraryPrefs);
$('libraryMore').addEventListener('click', () => loadLibrary({reset: libraryView.resetOnRetry}));
for (const id of ['libraryBack', 'albumBack', 'genreBack']) $(id).addEventListener('click', libraryBack);
$('artistBioToggle').addEventListener('click', toggleArtistBio);
window.addEventListener('resize', () => { fitArtistBio(); fitAlbumDescription(); });
$('albumDescriptionToggle').addEventListener('click', toggleAlbumDescription);
$('albumReviewsRetry').addEventListener('click', loadAlbumReviews);
albumTabButtons.forEach(button => {
  button.addEventListener('click', () => selectAlbumTab(button.dataset.albumTab));
  button.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      event.preventDefault(); moveAlbumTab(button, 1);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      event.preventDefault(); moveAlbumTab(button, -1);
    } else if (event.key === 'Home') {
      event.preventDefault(); selectAlbumTab(albumTabButtons[0].dataset.albumTab, {moveFocus: true});
    } else if (event.key === 'End') {
      event.preventDefault(); selectAlbumTab(albumTabButtons[albumTabButtons.length - 1].dataset.albumTab, {moveFocus: true});
    }
  });
});
// Crossing the phone breakpoint (a rotation, a resized window) rebuilds what was drawn for the other
// layout: the picks strip and the card or row lists. Lists already on screen are reloaded the way
// they were loaded; the picks keep the albums they had.
mobileLayoutQuery.addEventListener('change', () => {
  if (dashboardPickItems.length) renderDashboardPicks();
  if (allRecommendations.length) applyRecommendationFilters();
  for (const name of ['personal', 'new_releases', 'classics']) {
    if ($(discoveryViews[name][0]).childElementCount) loadDiscovery(name);
  }
  if ($('savedCards').childElementCount) loadSaved();
  if ($('lensListsCards').childElementCount) loadLensList(activeLens);
});
if (window.location.hash) applyHash(window.location.hash);
