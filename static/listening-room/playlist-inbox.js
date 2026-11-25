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
  let edition = null;
  let requestId = 0;

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

  function renderDetail(data) {
    heading.textContent = data.title || 'Untitled Playlist';
    renderMeta(detailMeta, data);
    if (!data.tracks.length) {
      status.textContent = 'This playlist is empty.';
      return;
    }
    const rows = document.createDocumentFragment();
    for (const track of data.tracks) {
      const row = document.createElement('li');
      const content = addTextElement(row, 'div', 'lr-inbox-track', '');
      const labels = addTextElement(content, 'div', 'lr-inbox-track-labels', '');
      addTextElement(labels, 'strong', '', track.title || 'Unknown Track');
      const metadata = [track.artist, track.album].filter(Boolean).join(' · ');
      if (metadata) addTextElement(labels, 'p', '', metadata);
      const match = addTextElement(content, 'span', 'lr-inbox-match',
        matchStates[track.match_state] || 'Ownership unavailable');
      match.dataset.state = track.match_state || '';
      rows.append(row);
    }
    tracks.replaceChildren(rows);
    tracks.hidden = false;
  }

  async function load(id) {
    edition = id;
    const request = ++requestId;
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
    status.textContent = id ? 'Loading playlist…' : 'Loading playlists…';
    try {
      const data = await requestJSON(id ? `${api}/${id}` : api);
      if (request !== requestId) return;
      status.textContent = data.index_state === 'stale' ? 'Ownership uses the last available library index.' : '';
      if (id) renderDetail(data);
      else renderShelf(data);
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
  window.playlistInbox = {load};
})();
