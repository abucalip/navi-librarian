(() => {
  const tabs = [...lrDiscovery.querySelectorAll('a')];
  const heading = $('lrDiscoverHeading');
  const recommendationStatus = $('recommendationCount');
  const refine = recommendationStatus.parentElement;
  const preference = 'discair-listening-room-discover-list';
  const {icon, renderReason, artistPhoto} = window.listeningRoomHome;
  const listIcons = ['discover', 'layers', 'people', 'disc', 'library', 'calendar'];
  const primaryLinks = lrLinks.filter(link => !lrDiscovery.contains(link) && link.dataset.lrPage === 'recommendations');
  const lensPicker = document.querySelector('#lensLists .lens-picker');
  const lensResults = $('lensListsCards');
  const lensTabs = document.createElement('div');
  lensTabs.className = 'lr-lens-tabs lr-tabs';
  lensTabs.setAttribute('role', 'tablist');
  lensTabs.setAttribute('aria-label', 'Daily picks lens');
  const lensIcons = {deep_cuts: 'layers', current_tastes: 'spark', genre_spread: 'compass-spread',
    repeated_tracks: 'repeat', obsessions: 'flame'};
  let lastList = 'recommendations';
  try {
    const saved = localStorage.getItem(preference);
    if (lrDiscoverPages.has(saved)) lastList = saved;
  } catch {
    // The current list can still be remembered for this session.
  }

  function activateTab(event, controls) {
    const index = controls.indexOf(event.target);
    if (index < 0) return;
    const targets = {
      ArrowLeft: controls[(index + controls.length - 1) % controls.length],
      ArrowRight: controls[(index + 1) % controls.length],
      Home: controls[0],
      End: controls.at(-1),
    };
    const next = targets[event.key];
    if (!next || typeof next.focus !== 'function') return;
    event.preventDefault();
    next.focus();
    next.click();
  }

  function selectTab(tab, selected) {
    tab.tabIndex = selected ? 0 : -1;
    tab.setAttribute('aria-selected', String(selected));
  }

  tabs.forEach((tab, index) => {
    const page = tab.dataset.lrPage;
    tab.id = `lr-discover-tab-${page}`;
    tab.classList.add('lr-tab');
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-controls', page);
    tab.prepend(icon(listIcons[index], true));
    tab.addEventListener('keydown', event => {
      if (event.key === ' ') {
        event.preventDefault();
        tab.click();
      }
    });
  });
  lrDiscovery.addEventListener('keydown', event => activateTab(event, tabs));

  for (const [lens, glyph] of Object.entries(lensIcons)) {
    const tab = document.createElement('button');
    tab.type = 'button';
    tab.className = 'lr-tab';
    tab.id = `lr-discover-lens-${lens}`;
    tab.dataset.lrDiscoverLens = lens;
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-controls', 'lrLensPanel');
    tab.hidden = lens === 'genre_spread';
    tab.append(icon(glyph, true), listeningRoomLenses[lens]);
    tab.addEventListener('click', () => loadLensList(lens));
    lensTabs.append(tab);
  }
  lensTabs.addEventListener('keydown', event => activateTab(event, [...lensTabs.children].filter(tab => !tab.hidden)));
  lensPicker.after(lensTabs);
  const lensPanel = document.createElement('div');
  lensPanel.id = 'lrLensPanel';
  $('lensListsStatus').before(lensPanel);
  lensPanel.append($('lensListsStatus'), lensResults);

  function showGenreSpread() {
    $('lr-discover-lens-genre_spread').hidden = false;
  }

  function syncLens(lens) {
    for (const tab of lensTabs.children) selectTab(tab, tab.dataset.lrDiscoverLens === lens);
    lensPanel.setAttribute('aria-labelledby', `lr-discover-lens-${lens}`);
  }

  function sync(page) {
    const enabled = isListeningRoom();
    const inDiscover = enabled && lrDiscoverPages.has(page);
    heading.hidden = !inDiscover;
    if (enabled && recommendationStatus.parentElement === refine) refine.after(recommendationStatus);
    else if (!enabled && recommendationStatus.parentElement !== refine) refine.prepend(recommendationStatus);
    lrDiscovery.hidden = !inDiscover;
    if (inDiscover && lastList !== page) {
      lastList = page;
      try { localStorage.setItem(preference, page); } catch { /* Session preference is already set. */ }
    }
    for (const link of primaryLinks) link.href = '#' + (enabled ? lastList : 'recommendations');
    for (const tab of tabs) {
      const selected = tab.dataset.lrPage === page;
      selectTab(tab, selected);
      if (inDiscover && selected && lrDiscovery.scrollWidth > lrDiscovery.clientWidth) {
        const bounds = lrDiscovery.getBoundingClientRect();
        const tabBounds = tab.getBoundingClientRect();
        if (tabBounds.left < bounds.left) lrDiscovery.scrollLeft += tabBounds.left - bounds.left - 4;
        else if (tabBounds.right > bounds.right) lrDiscovery.scrollLeft += tabBounds.right - bounds.right + 4;
      }
      tab.removeAttribute('aria-current');
      const panel = $(tab.dataset.lrPage);
      if (enabled) {
        panel.setAttribute('role', 'tabpanel');
        panel.setAttribute('aria-labelledby', tab.id);
      } else {
        panel.removeAttribute('role');
        panel.setAttribute('aria-labelledby', panel.querySelector('h2').id);
      }
    }
    if (enabled) {
      lensPanel.setAttribute('role', 'tabpanel');
      syncLens(activeLens);
    } else {
      lensPanel.removeAttribute('role');
      lensPanel.removeAttribute('aria-labelledby');
    }
  }

  function destination(link) {
    return isListeningRoom() && primaryLinks.includes(link) ? lastList : null;
  }

  function tools(item, listName, entry, dismiss, save) {
    const {albumArtist: artist, albumTitle: album} = entry.dataset;
    const group = document.createElement('div');
    group.className = 'lr-rank-tools';
    group.setAttribute('role', 'group');
    group.setAttribute('aria-label', 'Actions for ' + album);
    if (!item.owned) group.append(createGetButton(artist, album, item));
    const bookmark = createSaveButton(artist, album, item, listName);
    if (save) group.append(bookmark);
    group.append(createFeedbackMenuButton(artist, album, item, {
      listName,
      bookmark: save ? null : bookmark,
      dismissFromMenu: dismiss || (() => sendFeedback('dismiss', artist, album, item, listName, entry)),
    }));
    return group;
  }

  function albumEntry(item, className, rank, listName) {
    const entry = document.createElement('article');
    entry.className = className;
    const artist = item.artist || item.album_artist || 'Unknown artist';
    const album = item.album || item.title || item.name || 'Untitled album';
    makeAlbumCardInteractive(entry, artist, album, item, false);
    entry.dataset.albumDiscoveryList = listName;
    if (rank !== null) {
      addTextElement(entry, 'span', 'lr-rank-n', String(rank)).setAttribute('aria-hidden', 'true');
    }
    const ownedId = item.owned && (item.navidrome_id || item.id);
    attachArtwork(entry, artist, album, ownedId ? '/api/owned/artwork/' + encodeURIComponent(ownedId) : item.artwork_url);
    const cover = entry.querySelector('.card-art');
    cover.classList.add('lr-cover');
    const placeholder = cover.querySelector('.card-art-placeholder');
    placeholder.replaceChildren(icon('disc'));
    placeholder.setAttribute('aria-label', 'Cover unavailable');
    placeholder.setAttribute('role', 'img');
    if (item.owned) {
      const mark = addTextElement(cover, 'span', 'lr-discover-owned', '');
      mark.append(icon('check', true), addTextElement(mark, 'span', 'sr-only', 'In your library'));
    }
    const main = addTextElement(entry, 'div', 'lr-rank-main', '');
    const title = addTextElement(main, 'p', 'lr-card-title', '');
    linkAlbumName(title, artist, album, item, listName);
    const meta = addTextElement(main, 'p', 'lr-meta', '');
    linkArtistName(meta, artist);
    const year = firstReleaseYear(item.year, item.release_year, item.first_release_year, item.first_release_date);
    if (year !== null) meta.append(' · ' + year);
    return entry;
  }

  function row(item, rank, listName, dismiss) {
    const entry = albumEntry(item, 'ranked-row lr-rank', rank, listName);
    entry.classList.toggle('lr-rank-norank', rank === null);
    entry.setAttribute('role', 'listitem');
    const reason = renderReason(item, 'card');
    if (reason) entry.append(reason);
    entry.append(tools(item, listName, entry, dismiss, true));
    return entry;
  }

  function dives(target, items) {
    const groups = new Map();
    for (const item of items) {
      const key = foldKey(item.artist || item.album_artist || 'Unknown artist');
      if (!groups.has(key)) groups.set(key, new Map());
      groups.get(key).set(recommendationKey(item), item);
    }
    for (const group of groups.values()) {
      const albums = [...group.values()];
      const artist = albums[0].artist || albums[0].album_artist || 'Unknown artist';
      const panel = addTextElement(target, 'section', 'lr-panel lr-discover-dive', '');
      panel.setAttribute('aria-label', artist);
      const head = addTextElement(panel, 'div', 'lr-discover-dive-head', '');
      const photo = artistPhoto(artist);
      head.append(photo);
      const copy = addTextElement(head, 'div', 'lr-discover-dive-name', '');
      addTextElement(copy, 'p', 'lr-eyebrow', 'Artist');
      const title = addTextElement(copy, 'h3', 'lr-section-title', '');
      linkArtistName(title, artist);
      const source = albums.find(item => ['deep_dive_missing', 'deep_dive_similar'].includes(item.why?.kind));
      const reason = source && renderReason(source, 'card', albums.length > 1);
      if (reason) panel.append(reason);
      const grid = addTextElement(panel, 'div', 'lr-dive-albums', '');
      for (const item of albums) {
        const card = albumEntry(item, 'card lr-card lr-discover-dive-card', null, 'artist_deep_dive');
        card.append(tools(item, 'artist_deep_dive', card, null, false));
        grid.append(card);
      }
    }
  }

  for (const tab of tabs) {
    const panel = $(tab.dataset.lrPage);
    const btn = panel.querySelector('[data-refresh-discovery], #loadRecommendations');
    if (btn) {
      const label = btn.id === 'loadRecommendations' ? 'Generate recommendations' : 'Refresh';
      btn.append(addTextElement(btn, 'span', 'lr-discover-button-label', label));
    }
  }

  let wasEnabled = isListeningRoom();
  new MutationObserver(() => {
    const enabled = isListeningRoom();
    if (wasEnabled === enabled) return;
    wasEnabled = enabled;
    if (!enabled && activeLens === 'genre_spread') setActiveLens('repeated_tracks');
    // An initialized list may contain markup from the previous layout.
    for (const page of lrDiscoverPages) {
      if (page !== 'recommendations') initializedPages.delete(page);
    }
    if (allRecommendations.length) applyRecommendationFilters();
    if (lrDiscoverPages.has(activePage)) {
      if (activePage === 'recommendations' && !enabled && !recommendationData && !$('loadRecommendations').disabled) {
        $('loadRecommendations').click();
      }
      initializePage(activePage);
    }
  }).observe(document.documentElement, {attributes: true, attributeFilter: ['data-layout']});

  window.listeningRoomDiscover = {sync, syncLens, showGenreSpread, destination, row, dives};
  sync(activePage);
})();
