(() => {
  const api = '/api/playlists/inbox';
  const section = $('playlistInbox');
  const shelf = $('inboxShelf');
  const detail = $('inboxDetail');
  const editions = $('inboxEditions');
  const tracks = $('inboxTracks');
  const heading = $('inboxDetailHeading');
  const status = $('inboxStatus');
  const retry = $('inboxRetry');
  const refreshButton = $('inboxRefresh');
  const settings = $('inboxSettings');
  const detailMeta = $('inboxDetailMeta');
  const dateFormat = new Intl.DateTimeFormat(undefined, {dateStyle: 'medium'});
  const countFormat = new Intl.NumberFormat();
  const sources = {hosted: 'ListenBrainz · Created for Me', cf: 'ListenBrainz · Recommendations', local: 'Discair'};
  const copyStates = {
    linked: 'Navidrome copy linked', pending: 'Navidrome copy pending',
    unlinked: 'Navidrome copy unlinked', not_linked: 'No Navidrome copy linked',
    unconfigured: 'Navidrome unconfigured',
  };
  const matchStates = {owned: 'Owned', missing: 'Missing', ambiguous: 'Ambiguous match'};
  const activeStatuses = new Set([
    'retry_requested', 'searching', 'queued', 'queued_unconfirmed', 'already_in_progress',
    'recovery_started', 'downloading', 'download_complete_waiting_for_folder', 'importing',
  ]);
  const transferStatuses = new Set([
    'queued', 'queued_unconfirmed', 'already_in_progress', 'recovery_started',
    'downloading', 'download_complete_waiting_for_folder',
  ]);
  const retryStatuses = new Set([
    'no_matches', 'queue_failed', 'settings_required', 'slskd_error', 'download_failed', 'dismissed',
  ]);
  const unresolvedCodes = new Set(['ambiguous_track', 'unresolved_track', 'unresolved_album']);
  let edition = null;
  let requestId = 0;
  let current = null;
  let timer;

  function renderMeta(parent, item) {
    const source = addTextElement(parent, 'p', 'lr-inbox-source', sources[item.source_kind] || 'Playlist');
    source.setAttribute('translate', 'no');
    const generated = item.generated_at ? new Date(item.generated_at) : null;
    if (generated && Number.isFinite(generated.getTime())) {
      addTextElement(parent, 'time', '', dateFormat.format(generated)).dateTime = item.generated_at;
    } else {
      addTextElement(parent, 'p', '', 'Generation date unavailable');
    }
    const total = countFormat.format(item.total_count);
    const owned = item.owned_count == null ? `${total} tracks · Ownership unavailable`
      : `${countFormat.format(item.owned_count)} of ${total} owned`;
    addTextElement(parent, 'p', 'lr-inbox-count', owned);
    const badge = addTextElement(parent, 'span', 'lr-inbox-badge',
      copyStates[item.navidrome_sync_state] || 'Navidrome copy status unavailable');
    badge.dataset.state = item.navidrome_sync_state || '';
    if (item.stale) addTextElement(parent, 'p', '', 'Snapshot is at least 7 days old');
  }

  function renderShelf(data) {
    if (!data.items.length) {
      status.textContent = data.state === 'unconfigured'
        ? 'Add your ListenBrainz username and token in Settings to receive playlists.'
        : 'No playlists have been saved to your Inbox yet.';
      settings.hidden = data.state !== 'unconfigured';
      return;
    }
    const cards = document.createDocumentFragment();
    for (const item of data.items) {
      const row = document.createElement('li');
      const link = addTextElement(row, 'a', 'lr-inbox-card', '');
      link.href = `#playlistInbox/${item.edition_id}`;
      link.dataset.edition = item.edition_id;
      addTextElement(link, 'h3', '', item.title || 'Untitled Playlist');
      renderMeta(link, item);
      cards.append(row);
    }
    editions.replaceChildren(cards);
    editions.hidden = false;
  }

  function trackKey(track) {
    return JSON.stringify([
      track.artist, track.title, track.album, track.recording_mbid, track.release_mbid,
      track.duration_ms, track.conflicting_recording_mbids,
    ]);
  }

  function unavailableReason(track, indexState) {
    if (track.conflicting_recording_mbids) return 'Conflicting recording identifiers.';
    if (!track.artist?.trim() || !track.title?.trim()) return 'An artist and title are required.';
    if (track.match_state === 'ambiguous' && track.album?.trim()) return 'This recording cannot be identified safely.';
    if (!track.match_state) return indexState === 'building'
      ? 'Waiting for the library index.' : 'Library ownership could not be checked.';
    return '';
  }

  function setText(element, value) {
    if (element.textContent !== value) element.textContent = value;
  }

  function jobKey({artist, job_album: album}) {
    return JSON.stringify([artist, album]);
  }

  function trackJob(view, row) {
    const action = view.actions.get(row.key);
    const result = action?.result;
    if (result && (action.awaitingDetail || result.status === 'identity_conflict')) return result;
    return view.jobs.get(row.key) || result;
  }

  function renderTrack(view, row) {
    const track = row.track;
    const action = view.actions.get(row.key);
    const state = action?.result?.status === 'owned' ? 'owned' : track.match_state;
    const request = action?.result;
    const job = trackJob(view, row);
    const jobStatus = job?.status;
    const observed = job?.job_album && view.progress.get(jobKey(job));
    const live = observed?.status === jobStatus ? observed : null;
    const detailMessage = live?.details?.message;
    const active = activeStatuses.has(jobStatus);
    const owned = state === 'owned';
    const error = active ? null : action?.error;
    const blocked = unavailableReason(track, view.data.index_state);
    const canRetry = error ? !unresolvedCodes.has(error.code) : retryStatuses.has(jobStatus);
    const showAction = !owned && (action?.pending || (!blocked && (canRetry || (!error && !jobStatus))));
    const verb = canRetry ? 'Retry' : 'Download';
    const label = jobStatus === 'imported' ? 'Imported. Waiting for Navidrome to index the track.'
      : jobStatus === 'already_in_progress' ? 'Download already in progress.'
      : jobStatus ? acquisitionStatusInfo(jobStatus).label : '';
    const jobMessage = jobStatus === 'imported' ? label
      : detailMessage || (request?.status === jobStatus && request?.message) || label;
    const message = owned ? '' : action?.pending ? 'Requesting download…' : error?.message || jobMessage || blocked;
    const percent = !owned && !action?.pending && active ? live?.details?.live_progress?.percent : null;

    setText(row.match, matchStates[state] || 'Ownership unavailable');
    row.match.dataset.state = state || '';
    setText(row.status, Number.isFinite(percent) ? label : message);
    setText(row.percent, Number.isFinite(percent) ? `${Math.round(percent)}%` : '');
    row.meter.hidden = !Number.isFinite(percent);
    if (!row.meter.hidden) row.meter.value = percent;
    if (row.button !== document.activeElement || showAction) row.button.hidden = !showAction;
    else {
      (owned ? row.match : row.status).focus({preventScroll: true});
      row.button.hidden = true;
    }
    setText(row.button, verb);
    row.button.setAttribute('aria-label', `${verb} ${row.title}`);
    row.button.setAttribute('aria-disabled', String(Boolean(action?.pending)));
  }

  function renderTracks(view) {
    view.rows.forEach(row => renderTrack(view, row));
  }

  function renderDetail(view) {
    const data = view.data;
    heading.textContent = data.title || 'Untitled Playlist';
    if (!data.tracks.length) {
      renderMeta(detailMeta, data);
      status.textContent = 'This playlist is empty.';
      return;
    }
    const rows = document.createDocumentFragment();
    view.rows = data.tracks.map(track => {
      const row = document.createElement('li');
      const content = addTextElement(row, 'div', 'lr-inbox-track', '');
      const labels = addTextElement(content, 'div', 'lr-inbox-track-labels', '');
      const title = track.title || 'Unknown Track';
      addTextElement(labels, 'strong', '', title);
      const metadata = [track.artist, track.album].filter(Boolean).join(' · ');
      if (metadata) addTextElement(labels, 'p', '', metadata);
      const actions = addTextElement(content, 'div', 'lr-inbox-track-actions', '');
      const match = addTextElement(actions, 'span', 'lr-inbox-match', '');
      match.tabIndex = -1;
      match.setAttribute('role', 'status');
      const rowStatus = addTextElement(actions, 'p', 'lr-inbox-track-status', '');
      rowStatus.tabIndex = -1;
      rowStatus.setAttribute('role', 'status');
      const meter = document.createElement('progress');
      meter.className = 'lr-inbox-track-progress';
      meter.max = 100;
      meter.setAttribute('aria-label', `Download progress for ${title}`);
      const percent = addTextElement(actions, 'span', 'lr-inbox-track-status', '');
      percent.setAttribute('aria-hidden', 'true');
      const button = document.createElement('button');
      button.className = 'lr-btn';
      button.type = 'button';
      const entry = {key: trackKey(track), track, title, match, status: rowStatus, percent, meter, button};
      button.addEventListener('click', () => download(view, entry));
      actions.append(meter, percent, button);
      rows.append(row);
      return entry;
    });
    tracks.replaceChildren(rows);
    tracks.hidden = false;
    refreshButton.hidden = false;
    updateDetail(view, data);
    schedule(view, 0);
  }

  function updateDetail(view, data) {
    view.data = data;
    view.jobs = new Map();
    view.rows.forEach((row, index) => {
      row.track = data.tracks[index];
      if (row.track.acquisition_key) {
        view.jobs.set(row.key, {...row.track.acquisition_key, status: row.track.acquisition_status});
      }
    });
    const confirmed = data.tracks.filter(track =>
      track.match_state !== 'owned' && view.actions.get(trackKey(track))?.result?.status === 'owned').length;
    const ownedCount = data.owned_count == null ? null : data.owned_count + confirmed;
    const metaKey = JSON.stringify([ownedCount, data.navidrome_sync_state, data.stale]);
    if (view.metaKey !== metaKey) {
      view.metaKey = metaKey;
      detailMeta.replaceChildren();
      renderMeta(detailMeta, {...data, owned_count: ownedCount});
    }
    renderTracks(view);
  }

  function jobStatuses(view) {
    return view.rows.filter(row => row.track.match_state !== 'owned').map(row => trackJob(view, row)?.status);
  }

  function schedule(view, delay) {
    if (current !== view || view.refreshing || document.hidden) return;
    clearTimeout(timer);
    const statuses = jobStatuses(view);
    if (statuses.some(value => activeStatuses.has(value))) {
      timer = setTimeout(() => refresh(view), delay ?? 5000);
    } else if (statuses.includes('imported') && view.importChecks < 8) {
      timer = setTimeout(() => refresh(view), 15000);
    }
  }

  async function refresh(view) {
    if (current !== view || view.refreshing) return;
    clearTimeout(timer);
    view.refreshing = true;
    refreshButton.setAttribute('aria-disabled', 'true');
    const statuses = jobStatuses(view);
    const awaitingDetail = [...view.actions.values()].filter(action => action.awaitingDetail);
    if (statuses.includes('imported')) view.importChecks += 1;
    const progress = statuses.some(value => transferStatuses.has(value))
      ? requestJSON('/api/acquisitions').catch(() => null) : Promise.resolve(null);
    try {
      const [data, jobs] = await Promise.all([requestJSON(`${api}/${view.id}`), progress]);
      if (current !== view) return;
      awaitingDetail.forEach(action => { action.awaitingDetail = false; });
      view.progress = new Map((jobs?.acquisitions || []).filter(job => job.details?.kind === 'track')
        .map(job => [jobKey({artist: job.artist, job_album: job.album}), job]));
      status.textContent = data.index_state === 'stale' ? 'Ownership uses the last available library index.' : '';
      updateDetail(view, data);
    } catch {
      if (current === view) status.textContent = 'Couldn’t refresh track status. Try Refresh Status.';
    } finally {
      view.refreshing = false;
      if (current === view) {
        refreshButton.removeAttribute('aria-disabled');
        schedule(view);
      }
    }
  }

  async function download(view, row) {
    if (current !== view || row.button.hidden || view.actions.get(row.key)?.pending) return;
    const action = {pending: true};
    view.actions.set(row.key, action);
    renderTracks(view);
    try {
      const response = await fetch(`${api}/${view.id}/tracks/${row.track.position}/download`, {method: 'POST'});
      const data = await response.json();
      if (response.ok) {
        action.result = data;
        action.awaitingDetail = true;
      } else {
        action.error = {
          code: data.detail?.code,
          message: data.detail?.message || 'Couldn’t request this track.',
        };
      }
    } catch {
      action.error = {message: 'Couldn’t confirm the download request. Try again.'};
    } finally {
      action.pending = false;
      if (current === view) {
        updateDetail(view, view.data);
        if (action.result?.status) view.importChecks = 0;
        refresh(view);
      }
    }
  }

  function leave() {
    requestId += 1;
    current = null;
    clearTimeout(timer);
    refreshButton.removeAttribute('aria-disabled');
  }

  async function load(id) {
    leave();
    edition = id;
    const request = requestId;
    shelf.hidden = Boolean(id);
    detail.hidden = !id;
    for (const list of [editions, tracks]) {
      list.replaceChildren();
      list.hidden = true;
    }
    detailMeta.replaceChildren();
    heading.textContent = 'Playlist Details';
    settings.hidden = true;
    retry.hidden = true;
    refreshButton.hidden = true;
    status.textContent = id ? 'Loading playlist…' : 'Loading playlists…';
    try {
      const data = await requestJSON(id ? `${api}/${id}` : api);
      if (request !== requestId) return;
      status.textContent = data.index_state === 'stale' ? 'Ownership uses the last available library index.' : '';
      if (id) {
        current = {id, data, rows: [], jobs: new Map(), actions: new Map(), progress: new Map(), importChecks: 0};
        renderDetail(current);
      } else renderShelf(data);
    } catch (error) {
      if (request !== requestId) return;
      if (id && [404, 422].includes(error.status)) {
        status.textContent = 'This edition is unavailable. Return to the Inbox to browse saved playlists.';
      } else {
        status.textContent = 'Couldn’t load the Playlist Inbox. Try again.';
        retry.hidden = false;
      }
    }
  }

  function focusHeading(id) {
    (id ? heading : $('playlistInboxHeading')).focus();
  }

  section.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link || (!link.dataset.edition && link.hash !== '#playlistInbox')
        || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    const inboxEdition = link.dataset.edition || null;
    navigateTo('playlistInbox', {inboxEdition});
    focusHeading(inboxEdition);
  });
  retry.addEventListener('click', () => {
    focusHeading(edition);
    load(edition);
  });
  refreshButton.addEventListener('click', () => {
    if (!current) return;
    current.importChecks = 0;
    refresh(current);
  });
  document.addEventListener('visibilitychange', () => {
    if (!current) return;
    if (document.hidden) clearTimeout(timer);
    else schedule(current, 0);
  });
  window.playlistInbox = {load, leave};
})();
