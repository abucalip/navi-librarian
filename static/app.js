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

function showPage(name) {
  document.querySelectorAll('.page').forEach(el =>
    el.classList.toggle('hidden', el.id !== name));
  document.querySelectorAll('nav button[data-page]').forEach(el =>
    el.classList.toggle('active', el.dataset.page === name));
  moveNavBlob();
  syncNavAria();
}

// Slide the navigation indicator to the active item using translateY only. The blob is
// height-locked to a nav row, so only the offset changes; animating top would force layout
// on every navigation. Rows inside .nav-list share one width, so no width term is needed.
function moveNavBlob() {
  const blob = document.querySelector('.nav-blob');
  if (!blob) return;
  const active = document.querySelector('.nav-list > button.active');
  if (!active) { blob.hidden = true; return; }
  blob.hidden = false;
  blob.style.transform = 'translateY(' + active.offsetTop + 'px)';
}

// The reference component ships no aria-selected or role=tablist, so this is added here:
// the sidebar is a navigation landmark, and the current page is exposed as aria-current.
function syncNavAria() {
  document.querySelectorAll('nav button[data-page]').forEach(el => {
    if (el.classList.contains('active')) el.setAttribute('aria-current', 'page');
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

document.querySelectorAll('nav button[data-page]').forEach(button =>
  button.addEventListener('click', () => {
    const name = button.dataset.page;
    showPage(name);
    initializePage(name);
    if (name !== 'acquisitions') stopAcquisitionStream();
  }));

document.querySelectorAll('button[data-go]').forEach(button =>
  button.addEventListener('click', () => showPage(button.dataset.go)));

// Place the indicator once layout is settled, and keep it aligned when the rail is
// resized. offsetTop is only meaningful after layout, so the first move waits a frame.
syncNavAria();
requestAnimationFrame(moveNavBlob);
window.addEventListener('resize', moveNavBlob);
// Web fonts change row metrics after first paint; re-align once they are ready.
if (document.fonts && document.fonts.ready) document.fonts.ready.then(moveNavBlob);

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

function renderAcquisitions(data, targetOverride = null, statusOverride = null, onlyIdentity = null) {
  const target = targetOverride || $('acquisitionCards');
  const status = statusOverride || $('acquisitionsStatus');
  try {
    target.replaceChildren();
    const jobs = Array.isArray(data.acquisitions) ? data.acquisitions : [];
    updateActiveDownloadBadge(data);
    const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-acquisitions') || '[]'));
    status.textContent = jobs.length
      ? `${jobs.length} acquisition record(s).`
      : 'No acquisition records yet.';
    for (const job of jobs) {
      if (onlyIdentity && [job.artist || '', job.album || ''].join('::').toLocaleLowerCase() !== onlyIdentity) continue;
      const dismissalKey = [job.artist || '', job.album || ''].join('::').toLocaleLowerCase();
      if (job.status === 'imported' && dismissed.has(dismissalKey)) continue;
      const card = document.createElement('article');
      card.className = 'card';
      makeAlbumCardInteractive(card, job.artist || 'Unknown artist', job.album || 'Unknown album', job.details || {}, true);
      addTextElement(card, 'p', 'card-category', String(job.status || 'unknown').replaceAll('_', ' '));
      addTextElement(card, 'h3', '', job.album || 'Unknown album');
      const details = job.details || {};
      const metadata = details.metadata || {};
      applyAlbumYear(card, metadata.year || metadata.release_year || metadata.first_release_year || details.year || job.year);
      addTextElement(card, 'p', 'card-artist', job.artist || 'Unknown artist');
      const qualityLabels = {
        mp3_320: 'MP3 320 kbps', mp3_193_319: 'MP3 193–319 kbps',
        mp3_192: 'MP3 192 kbps', flac_cd: 'FLAC / CD quality',
        flac_16_44: 'FLAC 16-bit / 44.1 kHz',
      };
      const quality = Array.isArray(details.quality_summary) ? details.quality_summary : [];
      addTextElement(card, 'p', 'card-meta',
        'Quality profile: ' + (quality.length
          ? quality.map(value => qualityLabels[value] || String(value).replaceAll('_', ' ')).join(' · ')
          : 'Not reported'));
      const progress = details.live_progress;
      if (['downloading', 'download_complete_waiting_for_folder'].includes(job.status) && progress) {
        const progressRow = document.createElement('div');
        progressRow.className = 'download-progress';
        const ring = document.createElement('div');
        ring.className = 'progress-ring';
        const percent = Number.isFinite(Number(progress.percent)) && progress.percent !== null
          ? Math.max(0, Math.min(100, Number(progress.percent))) : null;
        ring.style.setProperty('--progress', percent === null ? '0%' : percent + '%');
        ring.setAttribute('role', 'img');
        ring.setAttribute('aria-label', percent === null ? 'Download progress unavailable' : 'Download ' + Math.round(percent) + ' percent complete');
        const percentText = document.createElement('span');
        percentText.textContent = percent === null ? '—' : Math.round(percent) + '%';
        ring.append(percentText);
        const copy = document.createElement('div');
        copy.className = 'download-progress-copy';
        addTextElement(copy, 'p', 'download-progress-label', 'Download progress');
        const speed = progress.speed_bytes_per_second;
        let speedText = 'Speed unavailable';
        if (Number.isFinite(Number(speed)) && speed !== null) {
          const value = Math.max(0, Number(speed));
          speedText = value >= 1024 * 1024
            ? (value / (1024 * 1024)).toFixed(1) + ' MB/s'
            : value >= 1024 ? (value / 1024).toFixed(0) + ' KB/s' : Math.round(value) + ' B/s';
        }
        const speedAndSize = document.createElement('div');
        speedAndSize.className = 'download-progress-speed-row';
        addTextElement(speedAndSize, 'p', 'download-progress-stat', speedText);
        const totalSize = formatDownloadBytes(progress.total_size_bytes);
        const remainingSize = formatDownloadBytes(progress.remaining_size_bytes);
        if (totalSize !== null && remainingSize !== null) {
          addTextElement(speedAndSize, 'p', 'download-progress-stat',
            'Total ' + totalSize + ' · ' + remainingSize + ' remaining');
        }
        copy.append(speedAndSize);
        const remaining = Number.isFinite(Number(progress.remaining_tracks)) ? Math.max(0, Number(progress.remaining_tracks)) : null;
        const totalTracks = Number.isFinite(Number(progress.total_tracks)) ? Math.max(0, Number(progress.total_tracks)) : null;
        addTextElement(copy, 'p', 'download-progress-stat',
          remaining === null ? 'Tracks remaining unavailable' :
          String(remaining) + ' of ' + (totalTracks === null ? '?' : totalTracks) + ' tracks remaining');
        progressRow.append(ring, copy);
        card.append(progressRow);
      }
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
        card.append(stallButton);
      }
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
      for (const line of lines) addTextElement(card, 'p', 'card-meta', line);
      if (job.status !== 'dismissed') {
        const actions = document.createElement('div');
        actions.className = 'card-actions';
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
        {
          const dismiss = document.createElement('button');
        dismiss.type = 'button';
        dismiss.textContent = 'Dismiss';
        dismiss.addEventListener('click', async () => {
          dismiss.disabled = true;
          try {
            await sendJSON('/api/acquisitions/dismiss', 'POST', {
              artist: job.artist, album: job.album
            });
            const stored = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-acquisitions') || '[]'));
            stored.add(dismissalKey);
            localStorage.setItem('navidrome-dismissed-acquisitions', JSON.stringify([...stored]));
            card.remove();
            const visibleCards = target.querySelectorAll('.card').length;
            status.textContent = visibleCards
              ? visibleCards + ' acquisition record(s).'
              : 'No acquisition records to show.';
            if (status === $('acquisitionsStatus')) {
              setStatusState(status, visibleCards ? 'progress' : 'empty');
            }
          } catch (error) {
            status.textContent = error.message;
            if (status === $('acquisitionsStatus')) setStatusState(status, 'error');
            dismiss.disabled = false;
          }
        });
          actions.append(dismiss);
        }
        if (actions.childElementCount) card.append(actions);
      }
      if (details.status && details.status !== job.status) {
        addTextElement(card, 'pre', 'debug', pretty(details));
      }
      target.append(card);
    }
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
  try {
    renderAcquisitions(await requestJSON('/api/acquisitions'));
  } catch (error) {
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
const artistBioRequests = new Map();
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
const artworkObserver = 'IntersectionObserver' in window
  ? new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const load = artworkLoaders.get(entry.target);
        if (load) load();
        artworkObserver.unobserve(entry.target);
      }
    }, {rootMargin: '220px'})
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

function makeAlbumCardInteractive(card, artist, album, metadata = {}, fetchYear = true) {
  card.dataset.albumArtist = String(artist || '');
  card.dataset.albumTitle = String(album || '');
  albumCardMetadata.set(card, metadata && typeof metadata === 'object' ? metadata : {});
  card.setAttribute('tabindex', '0');
  card.setAttribute('role', 'button');
  card.setAttribute('aria-label', 'View details for ' + album + ' by ' + artist);
  const nested = metadata && typeof metadata.metadata === 'object' ? metadata.metadata : {};
  const year = firstReleaseYear(
    metadata.year, metadata.release_year, metadata.first_release_year,
    nested.year, nested.release_year, nested.first_release_year
  );
  if (year !== null) applyAlbumYear(card, year);
  else if (fetchYear && artist && album) {
    const cacheKey = String(artist).trim().toLocaleLowerCase() + '::' + String(album).trim().toLocaleLowerCase();
    const query = new URLSearchParams({artist: String(artist), album: String(album)});
    cachedJSONRequest(albumYearRequests, cacheKey, '/api/album-year?' + query.toString())
      .then(data => { if (data && data.year) applyAlbumYear(card, data.year); })
      .catch(() => {});
  }
}

function ensureAlbumYearBadge(card) {
  const year = Number(card && card.dataset ? card.dataset.releaseYear : 0);
  const title = card && card.querySelector('h3');
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
  const links = [
    ['ListenBrainz', 'https://listenbrainz.org/search/?query=' + encoded, 'https://raw.githubusercontent.com/metabrainz/metabrainz-logos/master/logos/ListenBrainz/SVG/ListenBrainz_logo_icon.svg'],
    ['Apple Music', 'https://music.apple.com/search?term=' + encoded, 'https://cdn.simpleicons.org/applemusic/FA243C'],
    ['Spotify', 'https://open.spotify.com/search/' + encoded, 'https://cdn.simpleicons.org/spotify/1DB954'],
    ['Qobuz', 'https://www.qobuz.com/us-en/search/albums/' + encoded, 'https://community.qobuz.com/s/Qobuz_logo_black-l2kk.jpg'],
    ['Bandcamp', 'https://bandcamp.com/search?q=' + encoded, 'https://cdn.simpleicons.org/bandcamp/1DA0C3']
  ];
  const nav = $('albumModalPlatformLinks');
  nav.replaceChildren();
  for (const [label, href, iconUrl] of links) {
    const link = document.createElement('a');
    link.href = href;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.title = 'Search ' + artist + ' ' + album + ' on ' + label;
    link.setAttribute('aria-label', 'Search ' + artist + ' ' + album + ' on ' + label);
    const icon = document.createElement('img');
    icon.src = iconUrl;
    icon.alt = '';
    icon.loading = 'lazy';
    icon.width = 18;
    icon.height = 18;
    icon.onerror = () => {
      icon.remove();
      link.textContent = label.slice(0, 2);
      link.classList.add('platform-icon-fallback');
    };
    link.append(icon);
    nav.append(link);
  }
}
function closeAlbumModal() {
  $('albumModalBackdrop').hidden = true;
  activeAlbumModal = null;
}

async function openAlbumModal(card) {
  const artist = card.dataset.albumArtist || 'Unknown artist';
  const album = card.dataset.albumTitle || 'Unknown album';
  const metadata = albumCardMetadata.get(card) || {};
  const backdrop = $('albumModalBackdrop');
  const artwork = $('albumModalArtwork');
  const tracklist = $('albumModalTracklist');
  const get = $('albumModalGet');
  activeAlbumModal = {card, artist, album, metadata};
  $('albumModalTitle').textContent = album;
  $('albumModalArtist').textContent = artist;
  $('albumModalYear').textContent = String(firstReleaseYear(metadata.year, metadata.release_year, metadata.first_release_year, card.dataset.releaseYear) || '');
  setAlbumPlatformLinks(artist, album);
  $('albumModalStatus').textContent = 'Loading artwork and tracklist…';
  setStatusState($('albumModalStatus'), 'loading');
  tracklist.replaceChildren();
  artwork.removeAttribute('src');
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
  const card = event.target.closest && event.target.closest('.card[data-album-title]');
  if (!card || event.target.closest('button, a, input, select, textarea')) return;
  openAlbumModal(card);
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !$('albumModalBackdrop').hidden) closeAlbumModal();
  if ((event.key === 'Enter' || event.key === ' ') && event.target.matches('.card[data-album-title]')) {
    event.preventDefault(); openAlbumModal(event.target);
  }
});
$('albumModalClose').addEventListener('click', closeAlbumModal);
$('albumModalBackdrop').addEventListener('click', event => {
  if (event.target === $('albumModalBackdrop')) closeAlbumModal();
});

async function loadDashboardPicks() {
  const target = $('dashboardCarousel');
  const status = $('dashboardPicksStatus');
  target.replaceChildren();
  status.textContent = 'Picking ten albums across your discovery lists…';
  try {
    const data = await requestJSON('/api/dashboard-picks?count=10&nonce=' + Date.now());
    const items = (data.items || []).filter(isAlbumRecommendation);
    for (const item of items) {
      const artist = item.artist || item.album_artist || 'Unknown artist';
      const album = item.album || item.title || 'Untitled album';
      const card = document.createElement('article');
      card.className = 'card editorial-card';
      makeAlbumCardInteractive(card, artist, album, item);
      attachArtwork(card, artist, album);
      addTextElement(card, 'p', 'card-category', item.dashboard_category || 'Discovery');
      const title = document.createElement('h3');
      title.append(document.createTextNode(album));
      const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, card.dataset.releaseYear);
      if (year !== null) addTextElement(title, 'span', 'album-year', String(year));
      card.append(title);
      ensureAlbumYearBadge(card);
      addTextElement(card, 'p', 'card-artist', artist);
      const art = card.querySelector('.card-art');
      const get = createGetButton(artist, album, item);
      art.append(get);
      target.append(card);
    }
    status.textContent = items.length
      ? `${items.length} randomly selected albums from ${data.pool_size || items.length} available suggestions.`
      : 'No suggestions yet. Open a discovery page and refresh its list first.';
  } catch (error) {
    status.textContent = error.message;
  }
}

$('shuffleDashboard').addEventListener('click', loadDashboardPicks);

function attachArtwork(card, artist, album) {
  const art = document.createElement('div');
  art.className = 'card-art';
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
    const key = [item.artist || item.album_artist || '', item.album || item.title || item.name || '']
      .map(value => String(value).trim().toLocaleLowerCase()).join('::');
    return !dismissed.has(key) && (!query || searchable.includes(query)) &&
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

  $('recommendationCount').textContent =
    `Showing ${filtered.length} of ${allRecommendations.length} recommendations`;

  for (const item of filtered) {
    const card = document.createElement('article');
    card.className = 'card editorial-card';
    const artist = item.artist || item.album_artist || '';
    const album = item.album || item.title || item.name || '';
    makeAlbumCardInteractive(card, artist, album, item);
    attachArtwork(card, artist, album);
    const artContainer = card.querySelector('.card-art');
    artContainer.append(createGetButton(artist, album, item));
    const dismissButton = document.createElement('button');
    dismissButton.className = 'deep-dive-dismiss';
    dismissButton.textContent = '×';
    dismissButton.title = 'Not for me';
    dismissButton.setAttribute('aria-label', 'Not for me');
    dismissButton.addEventListener('click', () => {
      const key = [artist, album].map(value => String(value).trim().toLocaleLowerCase()).join('::');
      const dismissed = new Set(JSON.parse(localStorage.getItem('navidrome-dismissed-recommendations') || '[]'));
      dismissed.add(key);
      localStorage.setItem('navidrome-dismissed-recommendations', JSON.stringify([...dismissed]));
      applyRecommendationFilters();
    });
    artContainer.append(dismissButton);

    const categoryName = (item.discovery_category || 'Unclassified')
      .replaceAll('_', ' ');

    addTextElement(card, 'p', 'card-category', categoryName);

    const title = document.createElement('h3');
    title.append(document.createTextNode(item.album || item.title || item.name || 'Untitled album'));
    const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, card.dataset.releaseYear);
    if (year !== null) addTextElement(title, 'span', 'album-year', String(year));
    card.append(title);
    ensureAlbumYearBadge(card);

    addTextElement(
      card, 'p', 'card-artist',
      item.artist || item.album_artist || 'Unknown artist'
    );

    const genres = [
      ...(Array.isArray(item.genres) ? item.genres : []),
      ...(Array.isArray(item.genre_families) ? item.genre_families : [])
    ];

    if (genres.length) {
      const genreList = document.createElement('div');
      genreList.className = 'genre-list';

      for (const genre of [...new Set(genres)]) {
        addTextElement(genreList, 'span', 'genre-tag', genre);
      }

      card.append(genreList);
    }

    if (item.diversity_style) {
      addTextElement(
        card, 'p', 'card-meta',
        'Style: ' + item.diversity_style.replaceAll('_', ' ')
      );
    }

    const listeners = numeric(item.lastfm_listeners);
    if (listeners !== null) {
      addTextElement(
        card, 'p', 'card-meta',
        'Last.fm artist listeners: ' + listeners.toLocaleString()
      );
    }

    const score = numeric(item.discovery_score);
    if (score !== null) {
      addTextElement(
        card, 'p', 'card-meta',
        'Discovery score: ' + score.toFixed(4)
      );
    }

    if (item.discovery_source) {
      addTextElement(
        card, 'p', 'card-source',
        'Source: ' + item.discovery_source.replaceAll('_', ' ')
      );
    }

    cards.append(card);
  }

  if (!filtered.length) {
    addTextElement(
      cards, 'p', '',
      allRecommendations.length
        ? 'No recommendations match these filters. Try another search or category.'
        : 'No recommendations returned. Generate recommendations to try again.'
    );
  }
}

$('recommendationSearch').addEventListener('input', applyRecommendationFilters);
$('categoryFilter').addEventListener('change', applyRecommendationFilters);
$('recommendationSort').addEventListener('change', applyRecommendationFilters);

$('checkConnection').addEventListener('click', async () => {
  $('connection').textContent = 'Testing Navidrome…';
  await testServiceConnection('/api/settings/navidrome/test', 'connection');
});

$('loadRecommendations').addEventListener('click', async () => {
  const button = $('loadRecommendations');
  button.disabled = true;
  button.textContent = 'Generating…';
  $('recommendationCards').replaceChildren();
  $('recommendationDebug').textContent = '';
  try {
    const data = await requestJSON(
      '/api/recommendations?count=' + encodeURIComponent($('count').value));
    renderRecommendations(data);
  } catch (error) {
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
  new_releases: ['newReleasesCards','newReleasesStatus']
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

/** ResizeObservers watching genre-row overflow, disconnected on every re-render. */
const genreRowObservers = [];
const genreRowResizeHandlers = [];

function disconnectGenreRowObservers() {
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
  target.replaceChildren();
  target.classList.toggle('deep-dive-rows', name === 'artist_deep_dive');
  const destinationByItem = new Map();

  try {
    const poolCount = name === 'artist_deep_dive' ? 150 : name === 'classics' ? 100 : 30;
    const data = await requestJSON(`/api/discovery/${name}?count=${poolCount}&nonce=${Date.now()}`);
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
        addTextElement(heading, 'span', 'genre-row-count', `${genreItems.length} albums`);
        const arrows = document.createElement('div');
        arrows.className = 'genre-row-arrows';
        const track = document.createElement('div');
        track.className = 'genre-row-track';
        const arrowList = [];
        for (const [symbol, direction] of [['<', -1], ['>', 1]]) {
          const arrow = document.createElement('button');
          arrow.className = 'genre-row-arrow';
          arrow.type = 'button';
          arrow.textContent = symbol;
          arrow.setAttribute('aria-label', direction < 0 ? 'Scroll albums left' : 'Scroll albums right');
          arrow.addEventListener('click', () => track.scrollBy({left: direction * Math.max(250, track.clientWidth * 0.8), behavior: 'smooth'}));
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
      discoveryStatus(name, `${items.length} item(s)`);
    }

    for (const item of items) {
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
          (item.discovery_type || item.discovery_category || name).replaceAll('_',' '));
      }
      const title = document.createElement('h3');
      // This section's task is artist-led: its own copy reads "Explore missing albums by
      // artists in your library". The artist therefore takes the card's heading role and the
      // album becomes the supporting line, rather than the reverse inherited from the
      // album-grid sections.
      title.append(document.createTextNode(isDeepDive ? artist : album));
      const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, card.dataset.releaseYear);
      if (year !== null) addTextElement(title, 'span', 'album-year', String(year));
      card.append(title);
      ensureAlbumYearBadge(card);
      // Mirrors the swap above: with the artist in the heading, the supporting line carries
      // the album so no information is lost or duplicated.
      addTextElement(card, 'p', 'card-artist', isDeepDive ? album : artist);

      const needsBio = isDeepDive ||
        /Genre tags connect this artist to your established musical interests/i.test(item.reason || '');
      if (needsBio) {
        const bio = addTextElement(card, 'p', 'artist-bio', '');
        bio.hidden = true;
        const loadBio = () => {
          if (card.dataset.bioRequested) return;
          card.dataset.bioRequested = 'true';
          const bioKey = artist.trim().toLocaleLowerCase();
          cachedJSONRequest(artistBioRequests, bioKey, '/api/artist-bio?artist=' + encodeURIComponent(artist))
            .then(result => {
              if (!result || !result.bio) return;
              bio.textContent = result.bio;
              bio.hidden = false;
            })
            .catch(() => {});
        };
        bioLoaders.set(card, loadBio);
        if (artistBioObserver) artistBioObserver.observe(card);
        else loadBio();
      }

      if (item.reason && !needsBio) addTextElement(card, 'p', 'card-meta', item.reason);
      if (item.anchor_artist) addTextElement(card, 'p', 'card-meta',
        `Similar to ${item.anchor_artist}`);
      if (item.lastfm_playcount) addTextElement(card, 'p', 'card-meta',
        `Last.fm playcount: ${Number(item.lastfm_playcount).toLocaleString()}`);

        const actions = document.createElement('div');
      actions.className = 'card-actions';

      const button = (label, callback, className = '') => {
        const b = document.createElement('button');
        b.textContent = label;
        if (className) b.className = className;
        b.addEventListener('click', callback);
        actions.append(b);
      };

      const artContainer = card.querySelector('.card-art');
      artContainer.append(createGetButton(artist, album, item));

      const notForMe = document.createElement('button');
      notForMe.className = 'deep-dive-dismiss';
      notForMe.textContent = '×';
      notForMe.title = 'Not for me';
      notForMe.setAttribute('aria-label', notForMe.title);
      notForMe.addEventListener('click', () => sendFeedback('dismiss', artist, album, item, name));
      artContainer.append(notForMe);

      if (name !== 'artist_deep_dive') {
        button('Dismiss artist',
          () => sendFeedback('dismiss_artist', artist, album, item, name));
      }

      card.append(actions);
      (destinationByItem.get(item) || target).append(card);
    }

    if (!items.length && !autoRefreshStarted.has(name)) {
      const empty = addTextElement(target, 'p', 'status-line',
        'No results. Try refreshing this list.');
      setStatusState(empty, 'empty');
    }
  } catch (error) {
    discoveryStatus(name, error.message);
  }
}

async function sendFeedback(action, artist, album, metadata, listName) {
  try {
    await sendJSON('/api/discovery/feedback', 'POST',
      {action, artist, album, metadata});
    await loadDiscovery(listName);
  } catch (error) {
    discoveryStatus(listName, error.message);
  }
}

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
function createGetButton(artist, album, metadata) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'get-album';
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
    button.textContent = '…';
    button.title = album ? 'Requesting ' + album : 'Requesting';
    button.setAttribute('aria-label', button.title);
    button.setAttribute('aria-busy', 'true');
  } else if (state === 'requested') {
    button.disabled = true;
    button.classList.add('requested');
    button.textContent = 'requested';
    button.title = album ? 'Acquisition requested: ' + album : 'Acquisition requested';
    button.setAttribute('aria-label', button.title);
  } else if (state === 'failed') {
    // Usable again immediately: the user can retry without a reload.
    button.disabled = false;
    button.classList.add('is-failed');
    button.textContent = 'retry';
    button.title = album ? 'Request failed. Try again: ' + album : 'Request failed. Try again';
    button.setAttribute('aria-label', button.title);
  } else {
    button.disabled = false;
    button.textContent = 'get';
    button.title = 'Get this album';
    button.setAttribute('aria-label', album ? 'Get ' + album : 'Get this album');
  }
}

async function searchAlbum(artist, album, metadata, button = null) {
  if (button && button.disabled && !button.classList.contains('is-failed')) return;
  // Pending, not requested. The former code marked the button as requested before
  // awaiting the response, which claimed success the server had not confirmed.
  setGetButtonState(button, 'pending', artist, album);
  try {
    const data = await sendJSON('/api/acquire', 'POST',
      {artist, album, metadata, auto_queue:true});
    // This endpoint can answer 200 with ok:false and an explanatory message, for
    // example when no slskd API key is configured. Treating every 2xx as success
    // would mark the button "requested" for a request that was never made.
    if (data && data.ok === false) {
      setGetButtonState(button, 'failed', artist, album);
      reportAcquisitionOutcome(data.message || data.error || 'The request could not be placed.', 'error');
      return;
    }
    setGetButtonState(button, 'requested', artist, album);
    reportAcquisitionOutcome(data && data.message, 'success');
    // Keep the user on the current page. Acquisition cards are shown only in the Acquisitions view.
    await loadAcquisitions();
  } catch (error) {
    setGetButtonState(button, 'failed', artist, album);
    reportAcquisitionOutcome(error.message, 'error');
  }
}

// Route acquisition feedback to a status region that actually exists. Two former
// problems are fixed here: the selector was '.page:not(.hidden) .status', which matched
// nothing outside Settings, and the Recommendations section has no .status-line at all,
// so its messages had nowhere to land either.
function reportAcquisitionOutcome(message, kind) {
  if (!message) return;
  const page = document.querySelector('section.page:not(.hidden)');
  if (!page) return;
  const target = page.querySelector('.status-line') || page.querySelector('.muted[aria-live]');
  if (!target) return;
  target.textContent = message;
  setStatusState(target, kind);
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

async function loadListenbrainzSettings() {
  try {
    const data = await requestJSON('/api/settings/listenbrainz');
    $('listenbrainzUsername').value = data.username || '';
    $('listenbrainzStatus').textContent = 'Public profile username.';
    setStatusState($('listenbrainzStatus'), 'idle');
  } catch (error) { $('listenbrainzStatus').textContent = error.message; setStatusState($('listenbrainzStatus'), 'error'); }
}
$('saveListenbrainz').addEventListener('click', async () => {
  try {
    const result = await sendJSON('/api/settings/listenbrainz', 'PUT', {username: $('listenbrainzUsername').value.trim()});
    $('listenbrainzStatus').textContent = result.message || 'Settings saved.';
    setStatusState($('listenbrainzStatus'), 'success');
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

document.querySelectorAll('[data-settings-tab]').forEach(button => {
  button.addEventListener('click', () => {
    const name = button.dataset.settingsTab;
    document.querySelectorAll('[data-settings-tab]').forEach(tab => {
      const active = tab === button;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', String(active));
    });
    const panels = {navidrome: 'settingsNavidrome', slskd: 'settingsSlskd', lastfm: 'settingsLastfm', listenbrainz: 'settingsListenbrainz'};
    document.querySelectorAll('.settings-tab-panel').forEach(panel => { panel.hidden = panel.id !== panels[name]; });
  });
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

function moveQualityPriority(item, destination) {
  const list = $('qualityPriorityList');
  const items = [...list.querySelectorAll('.quality-priority-item')];
  const current = items.indexOf(item);
  if (current < 0 || destination < 0 || destination >= items.length || current === destination) return;
  const reference = items[destination];
  if (destination < current) list.insertBefore(item, reference);
  else list.insertBefore(item, reference.nextSibling);
  updateQualityPriorityPositions();
  announceQualityPriority(item, destination);
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
        moveQualityPriority(item, current + (direction === 'up' ? -1 : 1));
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


document.getElementById('logoutButton').addEventListener('click', async () => {
  try { await fetch('/api/auth/logout', {method: 'POST', cache: 'no-store'}); }
  finally { window.location.replace('/login'); }
});

// Populate only the visible dashboard on startup. Other pages load on first visit
// so their API requests don't compete with the page the user is currently viewing.
loadDashboardPicks();
