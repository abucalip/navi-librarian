(() => {
  const byId = id => document.getElementById('radioMix' + id);
  const dialog = byId('Dialog');
  const form = byId('Form');
  const kind = byId('Kind');
  const seedType = byId('SeedType');
  const seed = byId('Seed');
  const status = byId('Status');
  const save = byId('Save');
  const refresh = byId('Refresh');
  const list = byId('Tracks');
  const artistResults = byId('ArtistResults');
  const active = new Set(['retry_requested', 'searching', 'queued', 'queued_unconfirmed',
    'already_in_progress', 'recovering', 'recovery_started', 'downloading',
    'download_complete_waiting_for_folder', 'importing', 'pending', 'requested']);
  const failures = new Set(['no_matches', 'queue_failed', 'settings_required', 'slskd_error', 'download_failed', 'dismissed']);
  const states = {
    unconfigured: 'Add your ListenBrainz username and token in Settings to make mixes.',
    empty: 'No tracks were found for this seed. Try another artist or tag.',
    index_unavailable: 'Your library index is unavailable. Try again shortly.',
  };
  let preview = null;
  let epoch = 0;
  let timer;
  let checks = 0;
  let busy = false;
  let saved = false;
  let opener;
  let selectedArtist = null;
  const rows = new Map();

  async function request(url, body) {
    const response = await fetch('/api/radio-mixes/' + url, body === undefined ? {} : {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail
      : 'This mix is unavailable right now. Try again shortly.');
    return data;
  }

  function controls() {
    const discovery = kind.value === 'discovery';
    if (!discovery) seedType.value = 'artist';
    byId('SeedTypeLabel').hidden = !discovery;
    byId('ModeLabel').hidden = !discovery;
    byId('FamiliarityLabel').hidden = discovery;
    byId('SeedLabel').textContent = seedType.value === 'tag' ? 'Tag' : 'Artist name';
    byId('ArtistSearch').hidden = seedType.value === 'tag';
    artistResults.hidden = seedType.value === 'tag';
    seed.placeholder = seedType.value === 'tag' ? 'e.g. jazz' : 'Search your library';
    save.textContent = discovery ? 'Save owned to Navidrome' : 'Save to Navidrome';
    save.disabled = busy || saved || !preview?.tracks.some(track => track.song_id);
    refresh.disabled = busy || !preview;
    for (const control of form.elements) control.disabled = busy;
  }

  function invalidate() {
    epoch += 1;
    clearTimeout(timer);
    preview = null;
    saved = false;
    checks = 0;
    rows.clear();
    artistResults.replaceChildren();
    list.replaceChildren();
    status.textContent = '';
    controls();
  }

  function open(type, artist, button) {
    opener = button;
    invalidate();
    kind.value = type;
    selectedArtist = artist || null;
    seedType.value = artist || type === 'artist' ? 'artist' : 'tag';
    seed.value = artist?.name || '';
    byId('Title').textContent = artist ? 'Make a mix · ' + artist.name : 'Make a mix';
    controls();
    dialog.showModal();
    seed.focus();
  }

  function render(data) {
    preview = data;
    for (const track of data.tracks) {
      let entry = rows.get(track.position);
      if (!entry) {
        const li = document.createElement('li');
        const text = document.createElement('div');
        const title = document.createElement('strong');
        const meta = document.createElement('p');
        const note = document.createElement('p');
        const button = document.createElement('button');
        button.type = 'button';
        button.addEventListener('click', () => download(track.position));
        text.append(title, meta, note);
        li.append(text, button);
        list.append(li);
        entry = {title, meta, note, button, pending: false, result: null, error: null};
        rows.set(track.position, entry);
      }
      entry.title.textContent = track.title || 'Untitled track';
      entry.meta.textContent = [track.artist, track.album].filter(Boolean).join(' · ');
      const job = track.acquisition_status || entry.result?.status;
      const owned = !!track.song_id || entry.result?.status === 'owned';
      const blocked = track.match_state === 'ambiguous' ? 'Recording identity is ambiguous.'
        : track.match_state == null ? 'Ownership is unavailable.'
          : !track.artist?.trim() || !track.title?.trim() ? 'An artist and title are required.' : '';
      entry.note.textContent = owned ? 'Owned' : entry.pending ? 'Requesting download…'
        : entry.error || blocked || (job === 'imported' ? 'Imported; waiting for library indexing.'
          : job ? job.replaceAll('_', ' ') : 'Not in your library');
      entry.button.hidden = owned || data.kind === 'artist';
      entry.button.disabled = !!blocked || entry.pending || active.has(job) || job === 'imported';
      entry.button.textContent = entry.error || failures.has(job) ? 'Retry download' : 'Download';
      entry.button.setAttribute('aria-label', entry.button.textContent + ' ' + (track.title || 'track'));
    }
    const count = data.tracks.filter(track => track.song_id).length;
    if (!saved) status.textContent = `${data.tracks.length} tracks · ${data.owned_count == null ? 'ownership unavailable' : count + ' owned'}`
      + (data.index_state === 'stale' ? ' · Ownership uses the last available library index.' : '');
    controls();
  }

  function schedule() {
    clearTimeout(timer);
    if (!dialog.open || document.hidden || busy || !preview || checks >= 24) return;
    const pending = preview.tracks.some(track => active.has(track.acquisition_status)
      || track.acquisition_status === 'imported') || [...rows.values()].some(row => active.has(row.result?.status));
    if (pending) timer = setTimeout(() => { checks += 1; refreshStatus(); }, 10000);
  }

  async function refreshStatus() {
    if (!preview || busy) return;
    const current = epoch;
    const id = preview.preview_id;
    refresh.disabled = true;
    try {
      const data = await request(id);
      if (current === epoch && dialog.open) render(data);
    } catch (error) {
      if (current === epoch) status.textContent = error.message;
    } finally {
      if (current === epoch) { controls(); schedule(); }
    }
  }

  async function download(position) {
    const row = rows.get(position);
    if (!preview || row.button.disabled || busy) return;
    const current = epoch;
    const id = preview.preview_id;
    row.pending = true;
    row.error = null;
    render(preview);
    try {
      const result = await request(`${id}/tracks/${position}/download`, {});
      row.result = result;
      if (result.ok === false) row.error = result.message || 'Could not request this track.';
    } catch (error) { row.error = error.message; }
    finally {
      row.pending = false;
      if (current === epoch && dialog.open) { render(preview); checks = 0; refreshStatus(); }
    }
  }

  form.addEventListener('change', invalidate);
  seed.addEventListener('input', () => { selectedArtist = null; invalidate(); });
  byId('ArtistSearch').addEventListener('click', async () => {
    if (busy || !seed.value.trim()) return;
    invalidate();
    const current = epoch;
    status.textContent = 'Finding artists…';
    try {
      const response = await fetch('/api/library/artists?limit=20&q=' + encodeURIComponent(seed.value.trim()));
      const data = await response.json();
      if (!response.ok) throw new Error('Could not search your library. Try again.');
      if (current !== epoch || !dialog.open) return;
      const artists = (data.items || []).filter(item => item.mbid);
      for (const item of artists) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = item.name;
        button.addEventListener('click', () => {
          invalidate();
          selectedArtist = item;
          seed.value = item.name;
          status.textContent = 'Selected ' + item.name + '. Preview your mix.';
          byId('Generate').focus();
        });
        artistResults.append(button);
      }
      status.textContent = artists.length ? 'Choose an artist below.'
        : data.total == null ? 'Your library index is unavailable. Try again shortly.'
          : 'No matching artists with a confirmed identity. Try another name, or discover a mix by tag.';
    } catch (error) { if (current === epoch) status.textContent = error.message; }
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy) return;
    invalidate();
    if (seedType.value === 'artist' && (!selectedArtist || selectedArtist.name !== seed.value.trim())) {
      status.textContent = 'Use Find artist and choose an artist before previewing.';
      return;
    }
    const current = epoch;
    busy = true;
    status.textContent = 'Building your mix…';
    controls();
    try {
      const data = await request('preview', {
        kind: kind.value, [seedType.value === 'tag' ? 'tag' : 'artist_mbid']:
          seedType.value === 'tag' ? seed.value.trim() : selectedArtist.mbid,
        familiarity: byId('Familiarity').value, mode: byId('Mode').value,
      });
      if (current !== epoch || !dialog.open) return;
      if (data.state === 'ready') render(data);
      else status.textContent = states[data.state] || 'This mix is unavailable. Try again.';
    } catch (error) { if (current === epoch) status.textContent = error.message; }
    finally { busy = false; controls(); }
  });
  save.addEventListener('click', async () => {
    if (!preview || busy || saved) return;
    const current = epoch;
    busy = true;
    clearTimeout(timer);
    controls();
    status.textContent = 'Saving private playlist…';
    try {
      const data = await request(preview.preview_id + '/save', {});
      if (current === epoch) {
        saved = true;
        status.textContent = `Saved ${data.saved_count} tracks to a private Navidrome playlist. Find it in Navidrome’s Playlists.`;
      }
    } catch (error) { if (current === epoch) status.textContent = error.message; }
    finally { busy = false; controls(); }
  });
  refresh.addEventListener('click', () => { checks = 0; refreshStatus(); });
  byId('Close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    epoch += 1;
    clearTimeout(timer);
    if (opener?.isConnected) opener.focus();
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) clearTimeout(timer); else schedule(); });
  document.querySelectorAll('[data-mix-kind]').forEach(button => button.addEventListener('click', () => {
    if (!busy) open(button.dataset.mixKind, null, button);
  }));
  window.radioMixes = {setArtist(artist) {
    const actions = document.getElementById('artistMixActions');
    actions.replaceChildren();
    actions.hidden = !artist?.mbid;
    if (!artist?.mbid) return;
    for (const [type, label] of [['artist', 'Artist Radio'], ['discovery', 'Discover a mix']]) {
      if (type === 'artist' && !artist.owned) continue;
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = label;
      button.addEventListener('click', () => { if (!busy) open(type, artist, button); });
      actions.append(button);
    }
  }};
  if (typeof libraryView !== 'undefined' && libraryView.artistCtx?.artistShown) {
    window.radioMixes.setArtist(libraryView.artistCtx);
  }
})();
