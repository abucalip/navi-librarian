// Listening Room renders Home, Library shelves and acquisition progress in the rail.
(() => {
  const home = $('lrHome');
  const lead = $('lrLead');
  const tabs = $('lrLensTabs');
  const panels = $('lrDailyPanels');
  const getting = $('lrGetting');
  const libraryShelves = $('lrLibraryShelves');
  const menu = $('lrPickMenu');
  const menuItems = $('lrPickMenuItems');
  const heroOrder = ['deep_cuts', 'current_tastes', 'genre_spread'];
  const lenses = new Map([
    ['deep_cuts', ['Deep cuts', 'layers']],
    ['current_tastes', ['Current tastes', 'spark']],
    ['genre_spread', ['Genre spread', 'compass-spread']],
    ['repeated_tracks', ['Repeated tracks', 'repeat']],
    ['obsessions', ['Obsessions', 'flame']],
  ]);
  const reasonIcons = {
    bridge: 'layers', tag: 'tag', similar_artists: 'people', deep_dive_missing: 'library',
    deep_dive_similar: 'people', new_release: 'calendar', collection: 'disc', owned: 'check',
  };
  const discoverIcons = {
    adjacent: 'discover', cross_genre: 'compass-spread', adventurous: 'spark', unclassified: 'info',
  };

  let results = null;
  let heroLens = null;
  let selectedLens = null;
  let lensChosen = false;
  let latestRequest = null;
  let renderedHero;
  let renderedDaily;
  let menuOwner = null;
  let loadedLegacy = !isListeningRoom();
  const dismissed = new Set();
  const dismissedArtists = new Set();
  const getButtons = new WeakMap();
  const saveButtons = new WeakMap();
  const tintOutcomes = new Map();
  const servedLenses = new Set();

  function element(tag, className, text = '') {
    const node = document.createElement(tag);
    node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function icon(name, small = false) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', small ? 'lr-icon-sm' : 'lr-icon');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    const use = document.createElementNS(svg.namespaceURI, 'use');
    use.setAttribute('href', '#lr-' + name);
    svg.append(use);
    return svg;
  }

  function button(text, glyph, className) {
    const control = element('button', className);
    control.type = 'button';
    control.append(icon(glyph), text);
    return control;
  }

  function link(text, target, className = '') {
    const anchor = element('a', className, text);
    anchor.href = encodeLibraryHash(target);
    anchor.addEventListener('click', event => {
      if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      openLibraryTarget(target);
    });
    return anchor;
  }

  const artistName = item => item.artist || item.album_artist || 'Unknown artist';
  const albumName = item => item.album || item.title || item.name || 'Untitled album';
  const pickKey = item => [artistName(item), albumName(item)].map(foldKey).join('::');

  function albumLink(item, text, listName) {
    const target = namedAlbumTarget(artistName(item), albumName(item), item, listName);
    if (item.owned && (item.navidrome_id || item.id)) {
      target.id = item.navidrome_id || item.id;
      target.owned = true;
      target.artworkUrl = '/api/owned/artwork/' + encodeURIComponent(target.id);
    }
    return link(text, target);
  }

  function artistPhoto(artist, className = 'lr-chip-avatar') {
    const initials = artist.trim().split(/\s+/).slice(0, 2).map(word => Array.from(word)[0]).join('').toLocaleUpperCase();
    const frame = element('span', className, initials);
    frame.setAttribute('aria-hidden', 'true');
    cachedJSONRequest(artistImageRequests, artist.trim().toLocaleLowerCase(),
      '/api/artist-image?' + new URLSearchParams({name: artist}))
      .then(data => {
        if (!data?.artwork_url) return;
        const image = new Image();
        image.alt = '';
        image.onload = () => frame.replaceChildren(image);
        image.src = data.artwork_url;
      });
    return frame;
  }

  function reasonChip(chip, seedTag, artistReason) {
    const value = String(chip.value ?? '');
    const isSeed = chip.type === 'tag' && value === seedTag;
    let target;
    if (chip.href_kind === 'genre' && value) target = {type: 'genre', tag: value.toLocaleLowerCase()};
    if (chip.href_kind === 'artist' && value) target = namedArtistTarget(value);
    const node = target ? link('', target, 'lr-chip') : element('span', 'lr-chip');
    if (chip.type === 'artist' && value) node.append(artistPhoto(value));
    if (chip.type === 'listeners') {
      const full = Number(chip.value).toLocaleString('en-US') + ' listeners';
      node.title = full;
      node.setAttribute('aria-label', full);
      node.append(icon('listeners', true));
    }
    if (artistReason && chip.type === 'library_count') node.append(icon('disc', true));
    if (isSeed) node.append(icon('tag', true), element('span', 'lr-chip-k', 'Seed tag'));
    else if (chip.type === 'tag' && seedTag) node.append(element('span', 'lr-chip-k', 'Tag'));
    node.append(element('span', 'lr-chip-value', chip.label));
    return node;
  }

  function renderReason(item, size, grouped = false, headingText) {
    const why = item.why;
    if (typeof why?.sentence !== 'string' || !why.sentence.trim()) return null;
    if (size === 'line') return element('p', 'lr-reason-line', why.sentence);
    const artistReason = ['deep_dive_missing', 'deep_dive_similar'].includes(why.kind);
    const text = (grouped && why.panel_sentence) || why.sentence;
    const label = artistReason ? 'Why this artist' : 'Why this pick';
    const glyph = why.kind === 'lens' ? lenses.get(item.lens)?.[1]
      : why.kind === 'discover' ? discoverIcons[item.discovery_category] : reasonIcons[why.kind];
    const box = element('div', 'lr-reason');
    const heading = element('p', 'lr-reason-label');
    heading.append(icon(glyph || 'layers', true), headingText || label);
    const sentence = element('p', 'lr-reason-head');
    sentence.append(element('span', size === 'hero' ? 'lr-reason-hero' : 'lr-reason-text', text));
    box.append(heading, sentence);
    if (why.chips?.length) {
      const evidence = element('ul', 'lr-evidence');
      evidence.setAttribute('aria-label', label);
      for (const chip of why.chips.slice(0, 4)) {
        const row = element('li', '');
        row.append(reasonChip(chip, why.kind === 'lens' ? item.seed_tag : '', artistReason));
        evidence.append(row);
      }
      box.append(evidence);
    }
    return box;
  }

  function clampTint(rgb) {
    const max = Math.max(...rgb);
    const min = Math.min(...rgb);
    const range = max - min;
    const lightness = (max + min) / 2;
    const saturation = range ? Math.min(0.5, range / (1 - Math.abs(2 * lightness - 1))) : 0;
    // Each channel's position in the original range preserves the hue as the HLS range shrinks.
    const channels = range ? rgb.map(value => (value - min) / range) : [0, 0, 0];
    const linear = value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    for (let step = 20; step >= 6; step--) {
      const light = step / 100;
      const chroma = 2 * light * saturation;
      const color = channels.map(value => light - chroma / 2 + value * chroma);
      const luminance = color.reduce((sum, value, index) => sum + linear(value) * [0.2126, 0.7152, 0.0722][index], 0);
      if (luminance <= 0.04 || step === 6) return 'rgb(' + color.map(value => (value * 255).toFixed(4)).join(', ') + ')';
    }
  }

  function sampleTint(image) {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 16;
      const context = canvas.getContext('2d', {willReadFrequently: true});
      context.drawImage(image, 0, 0, 16, 16);
      const {data} = context.getImageData(0, 0, 16, 16);
      const rgb = [0, 0, 0];
      let total = 0;
      for (let index = 0; index < data.length; index += 4) {
        const pixel = data.subarray(index, index + 3);
        const weight = 1 + (Math.max(...pixel) - Math.min(...pixel)) / 32;
        for (let channel = 0; channel < 3; channel++) rgb[channel] += pixel[channel] * weight;
        total += weight;
      }
      return clampTint(rgb.map(channel => channel / total / 255));
    } catch {
      return null;
    }
  }

  function recordTint(hero, item, tint) {
    if (!hero.isConnected) return;
    if (tint) hero.style.setProperty('--lr-hero-tint', tint);
    const outcome = tint ? 'sampled' : 'fallback';
    hero.dataset.tint = outcome;
    tintOutcomes.set(pickKey(item), outcome);
    const outcomes = [...tintOutcomes.values()];
    home.dataset.tintCovers = outcomes.length;
    home.dataset.tintFallbacks = outcomes.filter(value => value === 'fallback').length;
  }

  function sampleCover(hero, item, image) {
    if (new URL(image.src).origin === location.origin) {
      recordTint(hero, item, sampleTint(image));
      return;
    }
    // A provider without CORS may still serve the visible image. Only this detached probe requests CORS.
    const probe = new Image();
    probe.crossOrigin = 'anonymous';
    probe.onload = () => recordTint(hero, item, sampleTint(probe));
    probe.onerror = () => recordTint(hero, item, null);
    probe.src = image.src;
  }

  function artwork(item, className, hero = null) {
    const frame = element('div', className);
    const placeholder = icon('disc');
    frame.append(placeholder);
    const ownedId = item.owned && (item.navidrome_id || item.id);
    const known = ownedId ? '/api/owned/artwork/' + encodeURIComponent(ownedId) : item.artwork_url;

    function show(url) {
      if (!url) {
        if (hero) recordTint(hero, item, null);
        return;
      }
      const image = new Image();
      image.alt = '';
      image.decoding = 'async';
      image.hidden = true;
      image.onload = () => {
        image.hidden = false;
        placeholder.remove();
        if (hero) sampleCover(hero, item, image);
      };
      image.onerror = () => {
        image.remove();
        if (hero) recordTint(hero, item, null);
      };
      image.src = url;
      frame.append(image);
    }

    if (known || item.owned) {
      // Let the renderer attach the hero before recording even a missing cover.
      queueMicrotask(() => show(known));
    } else {
      const artist = artistName(item);
      const album = albumName(item);
      frame.loadRemoteArtwork = () => {
        const key = artist.trim().toLocaleLowerCase() + '::' + album.trim().toLocaleLowerCase();
        cachedJSONRequest(artworkRequests, key, '/api/artwork?' + new URLSearchParams({artist, album}))
          .then(data => show(data?.artwork_url));
      };
      if (!hero && remoteArtworkObserver) remoteArtworkObserver.observe(frame);
      else frame.loadRemoteArtwork();
    }
    return frame;
  }

  function artistAndYear(item, main) {
    const artist = artistName(item);
    const meta = element('p', main ? 'lr-hero-artist' : 'lr-meta');
    if (main) meta.append(artistPhoto(artist));
    const name = link(artist, namedArtistTarget(artist));
    const year = firstReleaseYear(item.year, item.release_year, item.first_release_year);
    const line = element('span', 'lr-artist-year');
    line.append(name);
    if (year !== null) line.append(' · ', element('span', '', String(year)));
    meta.append(line);
    return meta;
  }

  function getControl(item, main) {
    let control = getButtons.get(item);
    if (!control) {
      control = createGetButton(artistName(item), albumName(item), item);
      setGetButtonLabel(control, 'Get this album');
      control.prepend(icon('get'));
      control.append(element('span', 'lr-get-requested', 'Requested'));
      getButtons.set(item, control);
    }
    control.classList.add('lr-btn');
    for (const name of ['lr-btn-primary', 'lr-lead-get']) control.classList.toggle(name, main);
    for (const name of ['lr-btn-quiet', 'lr-btn-icon', 'lr-card-get']) control.classList.toggle(name, !main);
    return control;
  }

  function moreControl(item, row, get, main) {
    const more = button('', 'more', 'lr-btn lr-btn-icon' + (main ? '' : ' lr-btn-quiet'));
    more.setAttribute('aria-label', 'More actions for ' + albumName(item));
    more.setAttribute('aria-haspopup', 'menu');
    more.setAttribute('aria-expanded', 'false');
    more.setAttribute('aria-controls', menuItems.id);
    more.addEventListener('click', () => openMenu(more, item, row, get, main));
    return more;
  }

  function dismiss(item, row, artistOnly = false) {
    const exclusions = artistOnly ? dismissedArtists : dismissed;
    const key = artistOnly ? foldKey(artistName(item)) : pickKey(item);
    const hadFocus = row.contains(document.activeElement);
    exclusions.add(key);
    render();
    const restore = () => {
      exclusions.delete(key);
      render();
      const restored = [...home.querySelectorAll('[data-lr-pick]')].find(node => node.dataset.lrPick === pickKey(item));
      if (document.activeElement.id === 'undoSnackbarAction') restored?.querySelector('a')?.focus();
    };
    if (hadFocus) {
      (lead.querySelector('.lr-hero-title a') || tabs.querySelector('[aria-selected="true"]') || $('lrDailyHeading')).focus();
    }
    sendFeedback(artistOnly ? 'dismiss_artist' : 'dismiss', artistName(item), albumName(item), item, 'listening_room', row, restore);
  }

  function renderHero(name, items) {
    const [item, ...next] = items.slice(0, 5);
    const [label] = lenses.get(name);
    const hero = element('article', 'lr-hero');
    hero.dataset.lrPick = pickKey(item);
    hero.dataset.tint = 'pending';
    hero.setAttribute('aria-labelledby', 'lrLeadTitle');
    const title = element('h1', 'lr-hero-title');
    title.id = 'lrLeadTitle';
    title.append(albumLink({...item, lens: item.lens || name}, albumName(item), 'lens_lists'));
    const body = element('div', 'lr-hero-body');
    body.append(element('p', 'lr-eyebrow', 'Daily picks · ' + label + ' · Lead pick'), title, artistAndYear(item, true));
    const reason = renderReason({...item, lens: item.lens || name}, 'hero');
    if (reason) body.append(reason);
    const actions = element('div', 'lr-actions');
    const get = item.owned ? null : getControl(item, true);
    const lean = button('More like this', 'lean-more', 'lr-btn');
    lean.addEventListener('click', () => sendArtistLean(artistName(item), 'more', item));
    const skip = button('Skip', 'skip', 'lr-btn');
    skip.addEventListener('click', () => dismiss(item, hero));
    if (get) actions.append(get);
    actions.append(lean, skip, moreControl(item, hero, get, true));
    body.append(actions);
    hero.append(artwork(item, 'lr-hero-cover', hero), body);
    if (next.length) {
      const aside = element('aside', 'lr-upnext');
      aside.setAttribute('aria-label', 'Up next in ' + label);
      aside.append(element('p', 'lr-eyebrow', 'Up next in ' + label));
      for (const pick of next) {
        const anchor = albumLink({...pick, lens: pick.lens || name}, '', 'lens_lists');
        const info = element('div', 'lr-upnext-copy');
        info.append(element('p', 'lr-card-title', albumName(pick)));
        const line = renderReason(pick, 'line');
        if (line) info.append(line);
        anchor.append(artwork(pick, 'lr-cover'), info);
        aside.append(anchor);
      }
      hero.append(aside);
    } else {
      hero.classList.add('lr-hero-solo');
    }
    return hero;
  }

  function renderCard(item, lens) {
    const card = element('article', 'lr-card');
    card.dataset.lrPick = pickKey(item);
    const title = element('h3', 'lr-card-title');
    title.append(albumLink({...item, lens: item.lens || lens}, albumName(item), 'lens_lists'));
    const copy = element('div', 'lr-card-copy');
    copy.append(title, artistAndYear(item, false));
    card.append(artwork(item, 'lr-cover'), copy);
    const line = renderReason(item, 'line');
    if (line) card.append(line);
    const evidence = item.why?.chips?.find(chip => chip.type === 'listeners') || item.why?.chips?.[0];
    if (evidence) card.append(element('p', 'lr-meta', evidence.label));
    const actions = element('div', 'lr-card-tools');
    const get = item.owned ? null : getControl(item, false);
    if (get) actions.append(get);
    actions.append(moreControl(item, card, get, false));
    card.append(actions);
    return card;
  }

  function getItems(result) {
    if (result?.data?.disabled) return [];
    const items = result?.data?.items;
    if (!Array.isArray(items)) return [];
    return items.filter(item =>
      item && !dismissed.has(pickKey(item)) && !dismissedArtists.has(foldKey(artistName(item))));
  }

  function status(text, {retry, detail, settings} = {}) {
    const note = element('div', 'lr-home-note');
    const copy = element('div', 'lr-note-copy');
    const title = element('p', 'lr-note-title', text);
    title.setAttribute('role', 'status');
    copy.append(title);
    if (detail || settings || retry) {
      const description = element('p', 'lr-note-text', detail);
      if (settings) {
        const link = element('a', '', 'Settings');
        bindPageLink(link, 'settings');
        if (detail) description.append(' ');
        description.append('Turn on lens lists in ', link, ' to see them here.');
      }
      if (retry) {
        if (detail) description.append(' ');
        const again = element('button', 'lr-note-retry', 'Try again');
        again.type = 'button';
        again.addEventListener('click', retry);
        description.append(again);
      }
      copy.append(description);
    }
    note.append(icon(retry ? 'alert' : 'info'), copy);
    return note;
  }

  function loading(label, layout) {
    const placeholder = element('div', 'lr-loading lr-loading-' + layout);
    const shapes = element('div', 'lr-loading-shapes');
    shapes.setAttribute('aria-hidden', 'true');
    const count = layout === 'grid' ? 6 : 1;
    for (let index = 0; index < count; index++) {
      const item = element('div', 'lr-loading-item');
      const lines = element('div', 'lr-loading-lines');
      const widths = layout === 'hero' ? ['40%', '80%', '60%'] : ['80%'];
      for (const width of widths) {
        const line = element('div', 'lr-skel-line');
        line.style.width = width;
        lines.append(line);
      }
      item.append(element('div', 'lr-skel'), lines);
      shapes.append(item);
    }
    placeholder.append(element('span', 'lr-visually-hidden', label), shapes);
    return placeholder;
  }

  async function retryPicks(event) {
    const control = event.currentTarget;
    await refresh();
    if (!control.isConnected && document.activeElement === document.body) {
      (tabs.querySelector('[aria-selected="true"]') || $('lrDailyHeading')).focus();
    }
  }

  function renderLead() {
    heroLens = null;
    // A lower-priority response cannot claim the lead until the preceding lenses have settled.
    let pending = false;
    for (const name of heroOrder) {
      const result = results.get(name);
      if (!result) { pending = true; break; }
      if (getItems(result).length) { heroLens = name; break; }
    }
    const result = heroLens ? results.get(heroLens) : null;
    const items = getItems(result).slice(0, 5);
    const message = pending ? 'Loading the lead pick…' : '';
    if (renderedHero?.message === message && renderedHero.items.length === items.length &&
        items.every((item, index) => item === renderedHero.items[index])) return;
    lead.toggleAttribute('hidden', !heroLens && !pending);
    lead.setAttribute('aria-busy', String(pending));
    lead.replaceChildren(...(heroLens ? [renderHero(heroLens, items)]
      : pending ? [loading(message, 'hero')] : []));
    renderedHero = {message, items};
  }

  function renderTabs() {
    const available = [...lenses.keys()].filter(name => {
      const result = results.get(name);
      if (name === 'deep_cuts' || name === 'current_tastes') return !result?.unavailable;
      return result?.data ? !result.data.disabled : servedLenses.has(name) && !result?.unavailable;
    });
    if (!lensChosen && heroLens) selectedLens = heroLens;
    if (!available.includes(selectedLens)) selectedLens = available[0] || null;
    tabs.hidden = !available.length;
    for (const tab of [...tabs.children]) {
      if (!available.includes(tab.dataset.lrLens)) tab.remove();
    }
    available.forEach((name, index) => {
      let tab = $(`lrLens-${name}`);
      if (!tab) {
        const [label, glyph] = lenses.get(name);
        tab = button(label, glyph, 'lr-tab');
        tab.querySelector('svg').setAttribute('class', 'lr-icon-sm');
        tab.id = `lrLens-${name}`;
        tab.dataset.lrLens = name;
        tab.setAttribute('role', 'tab');
        tab.setAttribute('aria-controls', `lrDaily-${name}`);
        tab.addEventListener('click', () => selectLens(name));
        tabs.insertBefore(tab, tabs.children[index] || null);
      }
      const selected = name === selectedLens;
      tab.setAttribute('aria-selected', selected);
      tab.tabIndex = selected ? 0 : -1;
      // Keep an ARIA target for each tab, even when its content is hidden.
      let panel = $(`lrDaily-${name}`);
      if (!panel) {
        panel = element('div', 'lr-daily-panel');
        panel.id = `lrDaily-${name}`;
        panel.setAttribute('role', 'tabpanel');
        panel.setAttribute('aria-labelledby', tab.id);
        panels.append(panel);
      }
      panel.hidden = !selected;
    });
    for (const panel of [...panels.children]) {
      if (panel.id && !available.includes(panel.id.slice('lrDaily-'.length))) panel.remove();
    }
  }

  function renderDaily() {
    const target = selectedLens ? $(`lrDaily-${selectedLens}`) : panels;
    const result = results.get(selectedLens);
    // Daily picks for a possible hero lens depend on whether an earlier lens supplies the lead.
    const leadPending = heroOrder.includes(selectedLens) && !heroLens && heroOrder
      .slice(0, heroOrder.indexOf(selectedLens)).some(name => !results.has(name));
    const offset = selectedLens === heroLens ? 5 : 0;
    const items = leadPending ? [] : getItems(result).slice(offset, offset + 6);
    const pending = Boolean(selectedLens && (!result || leadPending));
    const disabled = Boolean(result?.data?.disabled && !result.error);
    const label = lenses.get(selectedLens)?.[0];
    const message = pending ? 'Loading Daily picks…'
      : result?.error ? (items.length ? 'This list could not be refreshed' : 'Could not load ' + label + '.')
      : disabled ? 'Daily picks are off'
      : !selectedLens ? 'No Daily picks are available.'
      : result?.data?.message || (getItems(result).length ? 'No more albums in this lens today.' : 'No ' + label + ' list yet');
    if (renderedDaily?.target === target && renderedDaily.message === message &&
        items.length === renderedDaily.items.length && items.every((item, index) => item === renderedDaily.items[index])) return;
    panels.querySelector(':scope > .lr-home-note')?.remove();
    target.setAttribute('aria-busy', String(pending));
    const content = [];
    if (pending) content.push(loading(message, 'grid'));
    else if (!items.length || result?.error) {
      const detail = result?.error && items.length ? 'Showing the previous list.'
        : disabled ? result.data.message : '';
      content.push(status(message, {detail, settings: disabled, retry: result?.error ? retryPicks : null}));
    }
    if (items.length) {
      const grid = element('div', 'lr-grid');
      grid.append(...items.map(item => renderCard(item, selectedLens)));
      content.push(grid);
    }
    if (target === panels) panels.append(...content);
    else target.replaceChildren(...content);
    renderedDaily = {target, items, message};
  }

  function bindPageLink(anchor, page) {
    anchor.href = '#' + page;
    anchor.addEventListener('click', event => {
      if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      navigateTo(page);
      const heading = $(page).querySelector('h2');
      heading.tabIndex = -1;
      heading.focus();
    });
  }

  function groupDiveAlbums(items) {
    const groups = new Map();
    for (const item of items) {
      const key = foldKey(artistName(item));
      if (!groups.has(key)) groups.set(key, []);
      const albums = groups.get(key);
      if (albums.length < 4 && !albums.some(album => pickKey(album) === pickKey(item))) albums.push(item);
    }
    return [...groups.values()];
  }

  function renderDive(target, groups, index = 0, focusNext = false) {
    const albums = groups[index];
    const artist = artistName(albums[0]);
    const heading = element('h2', 'lr-dive-name');
    heading.id = 'lrDiveTitle';
    heading.append(link(artist, namedArtistTarget(artist)));
    const copy = element('div', 'lr-dive-copy');
    copy.append(element('p', 'lr-eyebrow', 'Artist Deep Dives'), heading);
    const reasonItem = albums.find(item =>
      ['deep_dive_missing', 'deep_dive_similar'].includes(item.why?.kind));
    const reason = reasonItem && renderReason(reasonItem, 'card', albums.length > 1);
    if (reason) copy.append(reason);

    const grid = element('div', 'lr-dive-albums');
    for (const item of albums) {
      const card = albumLink(item, '', 'artist_deep_dive');
      card.className = 'lr-card';
      card.append(artwork(item, 'lr-cover'), element('p', 'lr-card-title', albumName(item)));
      const year = firstReleaseYear(item.year, item.release_year, item.first_release_year);
      if (year !== null) card.append(element('p', 'lr-meta', String(year)));
      grid.append(card);
    }
    const actions = element('div', 'lr-actions');
    const open = element('a', 'lr-btn', 'Open the deep dive');
    bindPageLink(open, 'artistDeepDive');
    actions.append(open);
    const next = button('Next artist', 'next', 'lr-btn');
    if (groups.length > 1) {
      next.addEventListener('click', () => renderDive(target, groups, (index + 1) % groups.length, true));
      actions.append(next);
    }
    copy.append(grid, actions);
    target.classList.add('lr-panel', 'lr-dive');
    target.replaceChildren(artistPhoto(artist, 'lr-dive-photo'), copy);
    if (focusNext) {
      next.focus();
      $('lrPickStatus').textContent = artist;
    }
  }

  function renderPreview(item, listName) {
    const card = element('article', 'lr-rowcard');
    const body = element('div', 'lr-rowcard-body');
    const info = element('div', '');
    const title = element('h3', 'lr-card-title');
    title.append(albumLink(item, albumName(item), listName));
    info.append(title, artistAndYear(item, false));
    body.append(info);
    const reason = renderReason(item, 'card');
    if (reason) body.append(reason);
    card.append(artwork(item, 'lr-cover'), body);
    return card;
  }

  function renderDiveStatus(target, note) {
    const heading = element('h2', 'lr-section-title', 'Artist Deep Dives');
    heading.id = 'lrDiveTitle';
    target.replaceChildren(heading, note);
  }

  const albumItems = data => (Array.isArray(data?.items) ? data.items : getRecommendations(data))
    .filter(isAlbumRecommendation);
  const sectionItems = data => Array.isArray(data?.items) ? data.items : [];
  const showNote = (target, note) => target.replaceChildren(note);

  async function loadSection(target, url, label, empty, renderItems, renderStatus = showNote, readItems = albumItems) {
    const load = () => loadSection(target, url, label, empty, renderItems, renderStatus, readItems);
    const hadFocus = target.contains(document.activeElement);
    target.setAttribute('aria-busy', 'true');
    renderStatus(target, loading('Loading ' + label + '…', 'section'));
    if (hadFocus) {
      target.tabIndex = -1;
      target.focus();
    }
    let items;
    let data;
    try {
      data = await requestJSON(url);
      if (data?.error) throw new Error(data.error);
      items = readItems(data);
    } catch {
      target.removeAttribute('aria-busy');
      renderStatus(target, status('Could not load ' + label + '.', {retry: load}));
      if (document.activeElement === target) target.querySelector('.lr-note-retry')?.focus();
      return;
    }
    target.removeAttribute('aria-busy');
    if (items.length) renderItems(target, items);
    else renderStatus(target, status(empty, {detail: data?.message}));
    if (document.activeElement === target) target.querySelector('a')?.focus();
  }

  function previewReason(why, year, release) {
    if (!why?.sentence) return '';
    const libraryCount = why.chips?.find(chip => chip.type === 'library_count');
    return release && why.kind === 'new_release' && year && libraryCount?.label
      ? 'New in ' + year + ' · ' + libraryCount.label
      : why.sentence;
  }

  function renderMiniCard(item, preview = '') {
    const card = element('article', 'lr-card');
    const title = element('h3', 'lr-card-title');
    const listName = {collection: 'classics', release: 'new_releases'}[preview];
    title.append(albumLink(item, albumName(item), listName));
    const year = firstReleaseYear(item.year, item.release_year, item.first_release_year);
    const meta = [artistName(item), preview === 'collection' && year].filter(Boolean).join(' · ');
    card.append(artwork(item, 'lr-cover'), title, element('p', 'lr-meta', meta));
    const reason = preview && previewReason(item.why, year, preview === 'release');
    if (reason) card.append(element('p', 'lr-reason-line', reason));
    return card;
  }

  function showMiniCards(target, items, preview) {
    const grid = element('div', 'lr-mini-grid');
    grid.append(...items.slice(0, 3).map(item => renderMiniCard(item, preview)));
    target.replaceChildren(grid);
  }

  function showGenres(target, items) {
    const links = element('div', 'lr-tabs lr-genre-links');
    links.append(...items.slice(0, 6).map(genre => link(genre.name, {type: 'genre', tag: genre.tag}, 'lr-genre')));
    target.replaceChildren(links);
  }

  function loadLibraryShelves() {
    for (const [id, source, label] of [
      ['Recent', 'recent', 'Recently played'],
      ['Frequent', 'frequent', 'Most played'],
      ['Newest', 'newest', 'Newly added'],
    ]) {
      loadSection($('lrShelf' + id), '/api/dashboard/albums/' + source + '?count=6',
        label, 'Nothing to show yet.', (target, items) => {
          const grid = element('div', 'lr-grid lr-shelf');
          grid.append(...items.slice(0, 6).map(item => renderMiniCard(item)));
          target.replaceChildren(grid);
        }, showNote, sectionItems);
    }
  }

  let gettingActive = false;
  let gettingArtworkKey;
  const gettingArtwork = $('lrGettingArtwork');
  const gettingTitle = $('lrGettingTitle');
  const gettingProgress = $('lrGettingProgress');
  const gettingSummary = $('lrGettingSummary');

  function syncGettingVisibility() {
    getting.hidden = !isListeningRoom() || !gettingActive || activePage === 'acquisitions';
  }

  function updateGetting(jobs) {
    if (!isListeningRoom()) return;
    const statusOf = job => String(job.status || '').toLowerCase();
    const active = jobs.filter(job => ACTIVE_DOWNLOAD_STATUSES.has(statusOf(job)));
    const current = active.find(job => statusOf(job) === 'downloading') || active[0];
    gettingActive = Boolean(current);
    syncGettingVisibility();
    if (!current) return;

    const details = current.details || {};
    const title = (details.kind === 'track' ? details.track_title : current.album) || current.album || 'Acquisition';
    const item = {artist: current.artist, album: details.kind === 'track' ? details.album_name : current.album};
    const key = pickKey(item);
    if (key !== gettingArtworkKey) {
      gettingArtworkKey = key;
      gettingArtwork.replaceChildren(artwork(item, 'lr-cover'));
    }
    gettingTitle.textContent = title;

    const percent = details.live_progress?.percent;
    const value = percent == null ? NaN : Number(percent);
    gettingProgress.hidden = !Number.isFinite(value);
    if (!gettingProgress.hidden) {
      const bounded = Math.max(0, Math.min(100, value));
      gettingProgress.setAttribute('aria-label', title + ' download');
      gettingProgress.setAttribute('aria-valuenow', String(Math.round(bounded)));
      gettingProgress.firstElementChild.style.width = bounded + '%';
    }

    const counts = new Map();
    for (const job of active) {
      const label = acquisitionStatusInfo(statusOf(job)).label.toLowerCase();
      counts.set(label, (counts.get(label) || 0) + 1);
    }
    gettingSummary.textContent = [...counts].map(([label, count]) => count + ' ' + label).join(' · ');
  }

  function loadHomeSections() {
    loadSection($('lrDive'), '/api/discovery/artist_deep_dive?count=150',
      'Artist Deep Dives', 'No artist deep dives yet.',
      (target, items) => renderDive(target, groupDiveAlbums(items)), renderDiveStatus);
    const showRows = listName => (target, items) => {
      const rows = element('div', 'lr-rows');
      rows.append(...items.slice(0, 3).map(item => renderPreview(item, listName)));
      target.replaceChildren(rows);
    };
    loadSection($('lrPersonalRows'), '/api/discovery/personal?count=3',
      'Personal Discoveries', 'No personal discoveries yet.', showRows('personal'), showNote);
    loadSection($('lrDiscoverRows'), '/api/recommendations?count=3',
      'Discover music', 'No recommendations yet.', showRows('recommendations'), showNote);
    loadSection($('lrCollection'), '/api/discovery/classics?count=3',
      'Add to your collection', 'No albums to add yet.', (target, items) => showMiniCards(target, items, 'collection'));
    loadSection($('lrNewReleases'), '/api/discovery/new_releases?count=3',
      'New releases', 'No new releases yet.', (target, items) => showMiniCards(target, items, 'release'));
    loadSection($('lrGenres'), '/api/dashboard/genres?limit=6',
      'Genres', 'No genres in your library yet.', showGenres, showNote, sectionItems);
  }

  function render() {
    if (!results) return;
    renderLead();
    renderTabs();
    renderDaily();
    if (menuOwner && !menuOwner.isConnected) closeMenu(false);
  }

  function selectLens(name) {
    lensChosen = true;
    selectedLens = name;
    render();
    const tab = $(`lrLens-${name}`);
    tab.focus({preventScroll: true});
    if (listeningRoomPhone.matches) tab.scrollIntoView({block: 'nearest', inline: 'nearest'});
  }

  tabs.addEventListener('keydown', event => {
    const options = [...tabs.children];
    const index = options.indexOf(event.target);
    if (index === -1) return;
    const direction = {ArrowLeft: -1, ArrowRight: 1}[event.key];
    let next = direction ? options[(index + direction + options.length) % options.length] : null;
    if (event.key === 'Home') next = options[0];
    if (event.key === 'End') next = options.at(-1);
    if (!next) return;
    event.preventDefault();
    selectLens(next.dataset.lrLens);
  });

  async function refresh() {
    if (!isListeningRoom() || activePage !== 'dashboard') return;
    const current = new Map();
    latestRequest = current;
    // Stream the first load. Refreshes leave the current sections usable until new data is ready.
    const firstLoad = !results?.size;
    if (firstLoad) {
      results = current;
      render();
    }
    const nonce = Date.now();
    await Promise.all([...lenses.keys()].map(async name => {
      let result;
      try {
        const data = await requestJSON(`/api/discovery/${name}?count=11&nonce=${nonce}`);
        result = data?.error ? {error: true, data: results?.get(name)?.data} : {data};
      } catch (error) {
        result = error.status === 404 ? {unavailable: true} : {error: true, data: results?.get(name)?.data};
      }
      if (latestRequest !== current) return;
      if (result.data && !result.data.disabled) servedLenses.add(name);
      else if (result.unavailable || result.data?.disabled) servedLenses.delete(name);
      current.set(name, result);
      if (firstLoad) render();
    }));
    if (latestRequest !== current || firstLoad) return;
    const focused = document.activeElement;
    const row = focused.closest('[data-lr-pick]');
    const pick = row?.dataset.lrPick;
    const controls = 'a, button';
    const position = row ? [...row.querySelectorAll(controls)].indexOf(focused) : -1;
    results = current;
    render();
    if (position >= 0 && !focused.isConnected) {
      const replacement = [...home.querySelectorAll('[data-lr-pick]')].find(node => node.dataset.lrPick === pick);
      (replacement?.querySelectorAll(controls)[position] || tabs.querySelector('[aria-selected="true"]'))?.focus();
    }
  }

  function closeMenu(focus = true) {
    if (!menu.open) return;
    const owner = menuOwner;
    menuOwner = null;
    menu.close();
    owner?.setAttribute('aria-expanded', 'false');
    if (focus) owner?.focus();
  }

  function addMenuItem(label, glyph, run, dangerous = false) {
    const option = button(label, glyph, 'lr-menu-item' + (dangerous ? ' lr-menu-danger' : ''));
    option.setAttribute('role', 'menuitem');
    option.tabIndex = -1;
    option.addEventListener('click', () => {
      closeMenu();
      run();
    });
    menuItems.append(option);
    return option;
  }

  function openMenu(owner, item, row, get, main) {
    closeMenu(false);
    menuOwner = owner;
    owner.setAttribute('aria-expanded', 'true');
    $('lrPickMenuTitle').textContent = 'Actions for ' + albumName(item);
    menuItems.replaceChildren();
    const album = albumName(item);
    const artist = artistName(item);
    if (get && !main && listeningRoomPhone.matches) {
      const requested = get.classList.contains('requested');
      const option = addMenuItem(requested ? 'Requested' : 'Get this album', requested ? 'check' : 'get', () => get.click());
      option.disabled = get.disabled;
    }
    let save = saveButtons.get(item);
    if (!save) {
      save = createSaveButton(artist, album, item, 'listening_room');
      saveButtons.set(item, save);
    }
    const saved = save.getAttribute('aria-pressed') === 'true';
    const saveItem = addMenuItem(saved ? 'Remove from Saved' : 'Save', 'saved', () => save.click());
    saveItem.disabled = save.getAttribute('aria-busy') === 'true';
    addMenuItem('More like this', 'lean-more', () => sendArtistLean(artist, 'more', item));
    addMenuItem('Less like this', 'lean-less', () => sendArtistLean(artist, 'less', item));
    addMenuItem('Not this artist', 'person', () => dismiss(item, row, true), true);
    for (const genre of albumGenres(item)) {
      addMenuItem('Block genre: ' + genre, 'block', () => sendGenreBlock(genre, 'listening_room'), true);
    }
    addMenuItem('Find on music services', 'external', () => {
      makeAlbumCardInteractive(row, artist, album, item, false, false);
      openAlbumModal(row, owner);
      $('albumModalPlatformLinks').querySelector('a')?.focus();
    });
    if (listeningRoomPhone.matches) {
      menu.showModal();
    } else {
      menu.show();
      const box = owner.getBoundingClientRect();
      const below = box.bottom + 4;
      menu.style.left = Math.max(8, box.right - menu.offsetWidth) + 'px';
      menu.style.top = (below + menu.offsetHeight > innerHeight
        ? Math.max(8, box.top - menu.offsetHeight - 4) : below) + 'px';
    }
    menuItems.querySelector('button:not(:disabled)').focus();
  }

  menu.addEventListener('cancel', event => { event.preventDefault(); closeMenu(); });
  menu.addEventListener('keydown', event => {
    const items = [...menuItems.querySelectorAll('button:not(:disabled)')];
    const index = items.indexOf(document.activeElement);
    const moves = {ArrowDown: (index + 1) % items.length, ArrowUp: (index - 1 + items.length) % items.length,
      Home: 0, End: items.length - 1};
    if (event.key === 'Escape') {
      event.preventDefault();
      closeMenu();
    } else if (event.key === 'Tab') {
      if (listeningRoomPhone.matches) {
        event.preventDefault();
        items[(index + (event.shiftKey ? -1 : 1) + items.length) % items.length].focus();
      } else closeMenu();
    } else if (Object.hasOwn(moves, event.key)) {
      event.preventDefault();
      items[moves[event.key]].focus();
    }
  });
  document.addEventListener('pointerdown', event => {
    if (!menu.open || menu.contains(event.target) || menuOwner?.contains(event.target)) return;
    closeMenu(false);
  });
  let gesture = null;
  menu.addEventListener('pointerdown', event => {
    if (!listeningRoomPhone.matches || !event.isPrimary || event.button !== 0) return;
    const grip = event.target.closest('.lr-pick-grip');
    if (grip) grip.setPointerCapture(event.pointerId);
    if (grip || event.target === menu) gesture = {id: event.pointerId, y: event.clientY, grip};
  });
  menu.addEventListener('pointerup', event => {
    if (gesture?.id !== event.pointerId) return;
    const {grip, y} = gesture;
    gesture = null;
    const top = menu.getBoundingClientRect().top;
    if (grip ? event.clientY - y >= 56 : y < top && event.clientY < top) closeMenu();
  });
  menu.addEventListener('pointercancel', () => { gesture = null; });
  listeningRoomPhone.addEventListener('change', () => closeMenu());
  window.addEventListener('resize', () => closeMenu());
  window.addEventListener('scroll', event => {
    if (!listeningRoomPhone.matches && !menu.contains(event.target)) closeMenu();
  }, true);

  let wasOnHome = false;
  let sectionsLoaded = false;
  let wasOnLibrary = false;
  let wasEnabled = isListeningRoom();
  function syncHome() {
    const enabled = isListeningRoom();
    if (enabled && !wasEnabled) refreshActiveDownloadBadge();
    const onHome = enabled && activePage === 'dashboard';
    const onLibrary = enabled && activePage === 'library' && !$('libraryListView').hidden;
    libraryShelves.hidden = !enabled;
    if (onLibrary && !wasOnLibrary) loadLibraryShelves();
    wasOnLibrary = onLibrary;
    home.hidden = !enabled;
    $('dashboardPicksPanel').hidden = enabled;
    if (enabled) {
      $('dashboard').setAttribute('aria-label', 'Home');
      $('dashboard').removeAttribute('aria-labelledby');
    } else {
      $('dashboard').removeAttribute('aria-label');
      $('dashboard').setAttribute('aria-labelledby', 'dashboardHeading');
    }
    if (onHome && !wasOnHome) {
      refresh();
      if (!sectionsLoaded) {
        sectionsLoaded = true;
        loadHomeSections();
      }
    }
    if (!onHome) closeMenu(false);
    if (!enabled && wasEnabled && !loadedLegacy) {
      loadedLegacy = true;
      loadDashboardPicks();
      loadDashboardShelves();
    }
    wasOnHome = onHome;
    wasEnabled = enabled;
  }

  window.listeningRoomHome = {refresh, updateGetting, syncGettingVisibility,
    renderReason, artistPhoto, icon, sampleTint};
  bindPageLink($('lrRadioGrab'), 'radio');
  $('lrRadioHeard').addEventListener('click', event => {
    if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    window.history.pushState(null, '', '#radio/heard');
    applyHash(window.location.hash);
  });
  bindPageLink($('lrPersonalRows').parentElement.querySelector('.lr-section-link'), 'personalDiscoveries');
  bindPageLink($('lrDiscoverRows').parentElement.querySelector('.lr-section-link'), 'recommendations');
  const observer = new MutationObserver(syncHome);
  observer.observe(document.documentElement, {attributes: true, attributeFilter: ['data-layout']});
  observer.observe($('dashboard'), {attributes: true, attributeFilter: ['class']});
  observer.observe($('library'), {attributes: true, attributeFilter: ['class']});
  observer.observe($('libraryListView'), {attributes: true, attributeFilter: ['hidden']});
  syncHome();
})();
