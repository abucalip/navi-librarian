const $ = id => document.getElementById(id);

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
const NAV_MORE_PAGES = ['classics', 'artistDeepDive'];

function showPage(name) {
  activePage = name;
  document.querySelectorAll('.page').forEach(el =>
    el.classList.toggle('hidden', el.id !== name));
  document.querySelectorAll('nav button[data-page]').forEach(el =>
    el.classList.toggle('active', el.dataset.page === name));
  // Settings lives in the header menu, so the gear toggle carries the "you are here" cue.
  $('appMenuButton').classList.toggle('is-current', name === 'settings' || name === 'saved');
  // The phone bar's More control carries the cue when one of its two destinations is current.
  $('navMoreButton').classList.toggle('is-current', NAV_MORE_PAGES.includes(name));
  moveNavIndicator();
  syncNavAria();
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
  else if (name === 'classics') loadDiscovery('classics', {rotate: true});
  else if (name === 'artistDeepDive') loadDiscovery('artist_deep_dive', {rotate: true});
  else if (name === 'settings') { loadNavidromeSettings(); loadSlskdSettings(); loadLastfmSettings(); loadListenbrainzSettings(); }
  else if (name === 'acquisitions') startAcquisitionStream();
}

// One navigation path for the rail and the header menu, so Settings in the menu still runs
// initializePage('settings') and loads its panels rather than opening an empty page.
function navigateTo(name) {
  showPage(name);
  initializePage(name);
  // Saved is read on every visit: saves made on other pages since the last visit must appear.
  if (name === 'saved') loadSaved();
  if (name !== 'acquisitions') stopAcquisitionStream();
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
  button.addEventListener('click', () => showPage(button.dataset.go)));

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
      const album = job.album || 'Unknown album';
      const row = document.createElement('article');
      row.className = 'acq-row';
      row.dataset.status = String(job.status || 'unknown');
      makeAlbumCardInteractive(row, artist, album, details, true);
      applyAlbumYear(row, metadata.year || metadata.release_year || metadata.first_release_year || details.year || job.year);
      attachArtwork(row, artist, album);

      const main = document.createElement('div');
      main.className = 'acq-main';
      row.append(main);
      addTextElement(main, 'h3', '', album);
      ensureAlbumYearBadge(row);
      addTextElement(main, 'p', 'acq-artist', artist);
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
      if (job.status === 'downloading' && details.stall_detected_at && Number(details.fallback_count) > 0) {
        const stallButton = document.createElement('button');
        stallButton.type = 'button';
        stallButton.className = 'skip-source-button';
        const secondsLeft = Math.max(0, 15 - Math.floor(Date.now() / 1000 - Number(details.stall_detected_at)));
        stallButton.textContent = secondsLeft > 0
          ? 'Skip to next source (' + secondsLeft + 's)'
          : 'Switching source…';
        stallButton.disabled = secondsLeft <= 0;
        stallButton.addEventListener('click', async () => {
          stallButton.disabled = true;
          stallButton.textContent = 'Requesting source switch…';
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
        actions.append(stallButton);
      }
      if (job.status !== 'dismissed') {
        const retryableStatuses = new Set(['no_matches', 'queue_failed', 'settings_required', 'slskd_error']);
        if (retryableStatuses.has(job.status)) {
          const retry = document.createElement('button');
          retry.type = 'button';
          retry.textContent = 'Try again';
          retry.addEventListener('click', async () => {
            retry.disabled = true;
            retry.textContent = 'Retrying…';
            try {
              await sendJSON('/api/acquire', 'POST', {
                artist: job.artist, album: job.album,
                metadata: details.metadata || {}, auto_queue: true
              });
              await loadAcquisitions();
            } catch (error) {
              status.textContent = error.message;
              retry.disabled = false;
              retry.textContent = 'Try again';
            }
          });
          actions.append(retry);
        }
        const dismiss = document.createElement('button');
        dismiss.type = 'button';
        dismiss.textContent = 'Dismiss';
        // Repeated on every row, so the name says which acquisition it dismisses.
        dismiss.setAttribute('aria-label', 'Dismiss ' + (job.album || job.artist || 'acquisition'));
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
        actions.append(dismiss);
      }
      if (actions.childElementCount) row.append(actions);
      row.dataset.acqKey = dismissalKey;
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
      addTextElement(el, 'span', 'album-year', String(year));
    }
  }
  return el;
}

const artworkLoaders = new WeakMap();
const bioLoaders = new WeakMap();
const artworkRequests = new Map();
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
    const query = new URLSearchParams({artist: String(artist), album: String(album)});
    // The year is looked up only when the card is near the viewport, and never when the artwork
    // response has already supplied one by the time its turn in the queue comes.
    const loadYear = () => {
      if (card.dataset.releaseYear) return;
      if (!albumYearRequests.has(cacheKey)) {
        const url = '/api/album-year?' + query.toString();
        albumYearRequests.set(cacheKey, yearQueue.run(
          () => (card.dataset.releaseYear ? null : fetchJSONOrNull(url))
        ).then(data => {
          if (data === null) albumYearRequests.delete(cacheKey);
          return data;
        }));
      }
      albumYearRequests.get(cacheKey)
        .then(data => { if (data && data.year) applyAlbumYear(card, data.year); })
        .catch(() => {});
    };
    albumYearLoaders.set(card, loadYear);
    if (albumYearObserver) albumYearObserver.observe(card);
    else loadYear();
  }
}

function ensureAlbumYearBadge(card) {
  const year = Number(card && card.dataset ? card.dataset.releaseYear : 0);
  // Deep Dive cards put the artist in the heading, so their year belongs on the album line.
  const title = card && card.querySelector(card.dataset.yearTarget === 'supporting' ? '.card-artist' : 'h3');
  if (title && year >= 1900 && year <= 2100 && !title.querySelector('.album-year')) {
    addTextElement(title, 'span', 'album-year', String(year));
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

function setAlbumPlatformLinks(artist, album) {
  const query = [artist, album].filter(Boolean).join(' ').trim();
  const encoded = encodeURIComponent(query);
  // Every image is a local file under /static/vendor (AGENTS.md: no runtime third-party assets).
  // The visible text is kept beside each mark, so the name never depends on the picture. Only
  // the services with a vendored mark have an icon (see static/vendor/simple-icons/NOTICE.md).
  const links = [
    ['ListenBrainz', 'https://listenbrainz.org/search/?query=' + encoded, null],
    ['Apple Music', 'https://music.apple.com/search?term=' + encoded, '/static/vendor/simple-icons/applemusic.svg'],
    ['Spotify', 'https://open.spotify.com/search/' + encoded, '/static/vendor/simple-icons/spotify.svg'],
    ['Qobuz', 'https://www.qobuz.com/us-en/search/albums/' + encoded, null],
    ['Bandcamp', 'https://bandcamp.com/search?q=' + encoded, '/static/vendor/simple-icons/bandcamp.svg']
  ];
  const nav = $('albumModalPlatformLinks');
  nav.replaceChildren();
  for (const [label, href, iconSrc] of links) {
    const link = document.createElement('a');
    link.href = href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.title = 'Search ' + artist + ' ' + album + ' on ' + label;
    link.setAttribute('aria-label', 'Search ' + artist + ' ' + album + ' on ' + label);
    if (iconSrc) {
      const icon = document.createElement('img');
      icon.src = iconSrc;
      icon.alt = '';
      icon.width = 18;
      icon.height = 18;
      link.append(icon);
    }
    link.append(label);
    nav.append(link);
  }
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
  $('albumModalTitle').textContent = album;
  $('albumModalArtist').textContent = artist;
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
      requestJSON('/api/album-details?' + query.toString()),
      requestJSON('/api/artwork?' + query.toString()).catch(() => null)
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
  meta.setAttribute('aria-hidden', 'true');
  addTextElement(meta, 'p', 'card-category', item.dashboard_category || 'Discovery');
  const title = document.createElement('h3');
  title.append(document.createTextNode(album));
  const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, tile.dataset.releaseYear);
  if (year !== null) addTextElement(title, 'span', 'album-year', String(year));
  meta.append(title);
  addTextElement(meta, 'p', 'card-artist', artist);
  if (artist !== 'Unknown artist') attachCardArtistBio(tile, meta, artist);
  tile.append(meta);
  ensureAlbumYearBadge(tile);

  tile.querySelector('.card-art').append(createGetButton(artist, album, item));
  return tile;
}

async function loadDashboardPicks() {
  const target = $('dashboardCarousel');
  const status = $('dashboardPicksStatus');
  const shuffle = $('shuffleDashboard');
  target.replaceChildren();
  status.textContent = 'Picking ten albums across your discovery lists…';
  // A second shuffle while one is pending would race two responses into the same strip.
  shuffle.disabled = true;
  try {
    const data = await requestJSON('/api/dashboard-picks?count=10&nonce=' + Date.now());
    const items = (data.items || []).filter(isAlbumRecommendation);
    for (const item of items) target.append(buildDashboardTile(item));
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

function attachArtwork(card, artist, album) {
  const art = document.createElement('div');
  art.className = 'card-art';
  // A div has no role, and ARIA forbids naming a generic element, so the label was never
  // announced. A group gives the artwork and its Get control a name.
  art.setAttribute('role', 'group');
  art.setAttribute('aria-label', 'Album artwork and acquisition actions');

  const placeholder = document.createElement('div');
  placeholder.className = 'card-art-placeholder';
  placeholder.textContent = 'COVER NOT FOUND';

  const image = document.createElement('img');
  image.alt = '';
  image.loading = 'lazy';
  image.decoding = 'async';
  art.append(image, placeholder);
  card.append(art);

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

  filtered.forEach((item, index) => {
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
// metadata lines, and `onDismiss` / `onDismissArtist` route dismissal to the server feedback
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
  title.textContent = album || 'Untitled album';
  title.setAttribute('title', album || 'Untitled album');
  main.append(title);
  addTextElement(main, 'p', 'row-artist', artist || 'Unknown artist');
  if (options.artistBio) attachArtistBio(row, main, artist);
  row.append(main);
  // The release-date column already shows the year, so a release-date row carries no year badge.
  if (!options.releaseDate) {
    const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, row.dataset.releaseYear);
    if (year !== null) addTextElement(title, 'span', 'album-year', String(year));
    ensureAlbumYearBadge(row);
  }

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
  // An album already in the library has nothing to get.
  if (!options.owned) actions.append(createGetButton(artist, album, item));
  if (options.listName) actions.append(createSaveButton(artist, album, item, options.listName));
  if (options.saved) {
    // Every row on the Saved page is saved: the control starts pressed, and its next press undoes.
    setSaveButtonState(actions.querySelector('.save-album'), true, album);
    row.append(actions);
    return row;
  }
  const dismissButton = document.createElement('button');
  dismissButton.type = 'button';
  dismissButton.className = 'deep-dive-dismiss';
  dismissButton.textContent = '×';
  dismissButton.title = 'Not for me';
  dismissButton.setAttribute('aria-label', 'Not for me: ' + album);
  dismissButton.addEventListener('click', () => {
    if (options.onDismiss) {
      options.onDismiss(artist, album, item, row);
      return;
    }
    const key = [artist, album].map(value => String(value).trim().toLocaleLowerCase()).join('::');
    const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-recommendations') || '[]'));
    dismissed.add(key);
    localStorage.setItem('navidrome-dismissed-recommendations', JSON.stringify([...dismissed]));
    applyRecommendationFilters();
  });
  actions.append(dismissButton);
  if (options.onDismissArtist) {
    const dismissArtist = document.createElement('button');
    dismissArtist.type = 'button';
    dismissArtist.className = 'row-dismiss-artist';
    dismissArtist.textContent = 'Dismiss artist';
    dismissArtist.setAttribute('aria-label', 'Dismiss artist ' + artist);
    dismissArtist.addEventListener('click', () => options.onDismissArtist(artist, album, item, row));
    actions.append(dismissArtist);
  }
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
    onDismiss: (artist, album, metadata, row) => sendFeedback('dismiss', artist, album, metadata, 'new_releases', row),
    onDismissArtist: (artist, album, metadata, row) => sendFeedback('dismiss_artist', artist, album, metadata, 'new_releases', row)
  });
}

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
        ? 'Low confidence: genre data unavailable' : '',
      item.lastfm_playcount ? 'Last.fm playcount: ' + Number(item.lastfm_playcount).toLocaleString() : ''
    ],
    listName: 'personal',
    onDismiss: (artist, album, metadata, row) => sendFeedback('dismiss', artist, album, metadata, 'personal', row),
    onDismissArtist: (artist, album, metadata, row) => sendFeedback('dismiss_artist', artist, album, metadata, 'personal', row)
  });
}

// Add to your collection rows (DESIGN_SYSTEM.md sections 8 and 9.4). The server orders candidates
// by an exploration score that includes random jitter, and Load albums rotates them on the client,
// so the order is not a ranking. Rows show a muted position and no red rank numeral, and the
// status line says what the order is. Not for me and Dismiss artist go through the server
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
      hasBio ? '' : item.reason,
      item.lastfm_playcount ? 'Last.fm playcount: ' + Number(item.lastfm_playcount).toLocaleString() : ''
    ],
    listName: 'classics',
    onDismiss: (artist, album, metadata, row) => sendFeedback('dismiss', artist, album, metadata, 'classics', row),
    onDismissArtist: (artist, album, metadata, row) => sendFeedback('dismiss_artist', artist, album, metadata, 'classics', row)
  });
}

// Lazy artist bio for a card (Deep Dives, Discover cards, dashboard tiles). One request per artist
// (cached in artistBioRequests), made when the card nears the viewport; the paragraph stays hidden
// unless the API returns a bio. Text is set with textContent.
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
    const genreLine = addTextElement(meta, 'p', 'row-meta-line row-genres', genres.join(' · '));
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
  button.textContent = 'Generating…';
  allRecommendations = [];
  $('recommendationCount').textContent = 'Generating recommendations…';
  $('recommendationCards').replaceChildren(...skeletonRows(Number($('count').value) || 5));
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
    button.textContent = 'Generate recommendations';
  }
});

const discoveryViews = {
  personal: ['personalCards','personalStatus'],
  classics: ['classicsCards','classicsStatus'],
  artist_deep_dive: ['artistDeepDiveCards','artistDeepDiveStatus'],
  new_releases: ['newReleasesCards','newReleasesStatus'],
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
  const el = $(discoveryViews[name][1]);
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

function deepDiveGenre(item) {
  const families = Array.isArray(item.genre_families) ? item.genre_families : [];
  const family = families.find(value => String(value || '').trim());
  if (family) return String(family).replaceAll('_', '-').toLocaleLowerCase();
  const tags = Array.isArray(item.genres) ? item.genres : [];
  const text = tags.join(' ').toLocaleLowerCase();
  const rules = [
    ['jazz', /jazz|bebop|swing/],
    ['african', /african|afrobeat|afropop|highlife|soukous|malian|tuareg|desert blues|ethiopian/],
    ['alternative', /alternative|indie rock|post-punk|art rock|garage rock|shoegaze/],
    ['brazilian', /brazilian|samba|bossa nova|\bmpb\b|tropic[aá]lia/],
    ['hip-hop', /hip.?hop|rap/],
    ['rnb-soul', /r&b|rnb|neo-soul|soul/],
    ['electronic', /electronic|electronica|house|techno|trip.?hop|downtempo/],
    ['funk', /funk/],
    ['north-african-middle-eastern', /arabic|ra[iï]|maghreb|north african|algerian|moroccan|tunisian|gnawa|chaabi|middle eastern/],
    ['rock', /rock|punk|metal|grunge/],
    ['pop', /pop/],
  ];
  const match = rules.find(([, pattern]) => pattern.test(text));
  return match ? match[0] : 'other';
}

function genreRowLabel(key) {
  const labels = {
    'jazz': 'Jazz', 'african': 'African Music', 'alternative': 'Alternative',
    'brazilian': 'Brazilian Music', 'hip-hop': 'Hip-Hop', 'rnb-soul': 'R&B / Soul',
    'electronic': 'Electronic', 'funk': 'Funk',
    'north-african-middle-eastern': 'North African & Middle Eastern',
    'north-african': 'North African', 'bossa-nova-brazilian': 'Brazilian / Bossa Nova',
    'rock': 'Rock', 'pop': 'Pop', 'other': 'Other Discoveries',
  };
  return labels[key] || key.replaceAll('-', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
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
  target.replaceChildren(...(rankedRowList ? skeletonRows(6) : []));
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
        addTextElement(heading, 'h3', '', genreRowLabel(genre));
        addTextElement(heading, 'span', 'genre-row-count', pluralize(genreItems.length, 'album', 'albums'));
        const arrows = document.createElement('div');
        arrows.className = 'genre-row-arrows';
        const track = document.createElement('div');
        track.className = 'genre-row-track';
        makeScrollTrackFocusable(track, genreRowLabel(genre) + ' albums');
        const arrowList = [];
        for (const [icon, direction] of [['chevron-left', -1], ['chevron-right', 1]]) {
          const arrow = document.createElement('button');
          arrow.className = 'genre-row-arrow';
          arrow.type = 'button';
          arrow.append(spriteIcon(icon));
          arrow.setAttribute('aria-label', direction < 0 ? 'Scroll albums left' : 'Scroll albums right');
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
      title.append(document.createTextNode(isDeepDive ? artist : album));
      const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, card.dataset.releaseYear);
      if (year !== null && !isDeepDive) addTextElement(title, 'span', 'album-year', String(year));
      card.append(title);
      // Mirrors the swap above: with the artist in the heading, the supporting line carries
      // the album so no information is lost or duplicated.
      const supportingLine = addTextElement(card, 'p', 'card-artist', isDeepDive ? album : artist);
      if (isDeepDive) card.dataset.yearTarget = 'supporting';
      // Keep release-year metadata with the album when the artist is the primary heading.
      if (year !== null && isDeepDive) addTextElement(supportingLine, 'span', 'album-year', String(year));
      ensureAlbumYearBadge(card);

      const needsBio = isDeepDive ||
        /Genre tags connect this artist to your established musical interests/i.test(item.reason || '');
      if (needsBio) {
        attachCardArtistBio(card, card, artist);
      }

      if (item.reason && !needsBio) addTextElement(card, 'p', 'card-meta', item.reason);
      if (item.anchor_artist) addTextElement(card, 'p', 'card-meta',
        `Similar to: ${item.anchor_artist}`);
      if (item.lastfm_playcount) addTextElement(card, 'p', 'card-meta',
        `Last.fm playcount: ${Number(item.lastfm_playcount).toLocaleString()}`);

        const actions = document.createElement('div');
      actions.className = 'card-actions';

      const button = (label, callback, className = '', accessibleName = label) => {
        const b = document.createElement('button');
        b.textContent = label;
        if (accessibleName !== label) b.setAttribute('aria-label', accessibleName);
        if (className) b.className = className;
        b.addEventListener('click', callback);
        actions.append(b);
      };

      const artContainer = card.querySelector('.card-art');
      artContainer.append(createGetButton(artist, album, item));

      const notForMe = document.createElement('button');
      notForMe.className = 'deep-dive-dismiss';
      notForMe.append(spriteIcon('x'));
      notForMe.title = 'Not for me';
      notForMe.setAttribute('aria-label', 'Not for me: ' + album);
      notForMe.addEventListener('click', () => sendFeedback('dismiss', artist, album, item, name, card));
      artContainer.append(notForMe);

      actions.append(createSaveButton(artist, album, item, name));

      if (name !== 'artist_deep_dive') {
        button('Dismiss artist',
          () => sendFeedback('dismiss_artist', artist, album, item, name, card), '', 'Dismiss artist ' + artist);
      }

      card.append(actions);
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
async function sendFeedback(action, artist, album, metadata, listName, row = null) {
  if (action === 'dismiss' || action === 'dismiss_artist') {
    queueDismiss(action, artist, album, metadata, listName, row);
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

function queueDismiss(action, artist, album, metadata, listName, row) {
  if (pendingDismiss) commitDismiss();
  const label = action === 'dismiss_artist'
    ? 'Dismissed artist ' + artist + '.'
    : 'Dismissed ' + album + (artist ? ' by ' + artist : '') + '.';
  const entry = {action, artist, album, metadata, listName, row, timer: null};
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
    await loadDiscovery(entry.listName);
  } catch (error) {
    if (entry.row) entry.row.classList.remove('is-dismissing');
    discoveryStatus(entry.listName, error.message);
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
  target.replaceChildren(...skeletonRows(4));
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
    for (const [index, entry] of entries.entries()) target.append(buildSavedRow(entry, index));
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
  ' fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round">' +
  '<circle class="get-album-arc" cx="22" cy="22" r="11.5"/>' +
  '<path class="get-album-tick" d="M14.5 22.6 19.6 27.7 29.5 16.4" pathLength="1"/>' +
  '<path class="get-album-arrow" d="M30.8 15.2A11 11 0 1 0 33 22"/>' +
  '<path class="get-album-arrow-head" d="M25.9 16.9 30.9 15.1 29.1 20.1"/>' +
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
    button.disabled = false;
    setGetButtonLabel(button, 'get');
    button.title = 'Get this album';
    button.setAttribute('aria-label', album ? 'Get ' + album : 'Get this album');
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
    $('lastfmApiKey').value = '';
    $('lastfmStatus').textContent = data.api_key_configured ? 'API key configured.' : 'API key not configured (optional).';
    setStatusState($('lastfmStatus'), classifyStatus($('lastfmStatus').textContent));
  } catch (error) { $('lastfmStatus').textContent = error.message; setStatusState($('lastfmStatus'), 'error'); }
}
$('saveLastfm').addEventListener('click', async () => {
  try {
    const result = await sendJSON('/api/settings/lastfm', 'PUT', {api_key: $('lastfmApiKey').value});
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

async function testServiceConnection(endpoint, statusId) {
  const status = $(statusId);
  status.textContent = 'Testing connection…';
  setStatusState(status, 'loading');
  try {
    const data = await sendJSON(endpoint, 'POST');
    status.textContent = data.message || (data.ok ? 'Connection successful.' : 'Test failed.');
    setStatusState(status, data.ok ? 'success' : 'error');
  } catch (error) {
    status.textContent = error.message;
    setStatusState(status, 'error');
  }
}
$('testLastfm').addEventListener('click', () => testServiceConnection('/api/settings/lastfm/test', 'lastfmStatus'));
$('testListenbrainz').addEventListener('click', () => testServiceConnection('/api/settings/listenbrainz/test', 'listenbrainzStatus'));

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
  lastfm: 'settingsLastfm', listenbrainz: 'settingsListenbrainz'
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
    item.className = 'quality-priority-item';
    item.draggable = true;
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
    moves.className = 'quality-priority-moves';
    for (const [direction, text] of [['up', '↑'], ['down', '↓']]) {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.qualityMove = direction;
      button.setAttribute('aria-label', `Move ${label} ${direction}`);
      button.textContent = text;
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

const qualityPriorityList = $('qualityPriorityList');
let draggedQualityItem = null;
qualityPriorityList.addEventListener('dragstart', event => {
  const item = event.target.closest('.quality-priority-item');
  if (!item) return;
  draggedQualityItem = item;
  item.classList.add('dragging');
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', item.dataset.quality);
  }
});
qualityPriorityList.addEventListener('dragover', event => {
  event.preventDefault();
  const target = event.target.closest('.quality-priority-item');
  if (!draggedQualityItem || !target || target === draggedQualityItem) return;
  const bounds = target.getBoundingClientRect();
  const insertAfter = event.clientY > bounds.top + bounds.height / 2;
  qualityPriorityList.querySelectorAll('.drop-target').forEach(item => item.classList.remove('drop-target'));
  target.classList.add('drop-target');
  qualityPriorityList.insertBefore(draggedQualityItem, insertAfter ? target.nextSibling : target);
});
qualityPriorityList.addEventListener('drop', event => {
  event.preventDefault();
  if (draggedQualityItem) {
    const index = [...qualityPriorityList.children].indexOf(draggedQualityItem);
    updateQualityPriorityPositions();
    announceQualityPriority(draggedQualityItem, index);
  }
});
qualityPriorityList.addEventListener('dragend', () => {
  qualityPriorityList.querySelectorAll('.dragging, .drop-target').forEach(item => {
    item.classList.remove('dragging', 'drop-target');
  });
  draggedQualityItem = null;
  updateQualityPriorityPositions();
});

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

makeScrollTrackFocusable($('dashboardCarousel'));

// Populate only the visible dashboard on startup. Other pages load on first visit
// so their API requests don't compete with the page the user is currently viewing.
loadDashboardPicks();
