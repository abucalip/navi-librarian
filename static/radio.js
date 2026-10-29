// Grab the radio page: relay a Navidrome station through this app, list the songs that were heard,
// and hand one to the song-only Get. Loaded after app.js and uses its $, sendJSON and
// reportAcquisitionOutcome. All text is set with textContent.

function radioElement(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function radioStatus(message, kind) {
  const el = $('radioStatus');
  el.textContent = message || '';
  setStatusState(el, message ? (kind || classifyStatus(message)) : 'idle');
}

function radioHeard(seconds) {
  const minutes = Math.round(seconds / 60);
  return minutes >= 1 ? minutes + ' min' : seconds + ' s';
}

function radioWhen(epoch) {
  return new Date(epoch * 1000).toLocaleString([], {dateStyle: 'medium', timeStyle: 'short'});
}

async function loadRadio() {
  radioStatus('Loading…', 'loading');
  const [stations, plays] = await Promise.allSettled([
    sendJSON('/api/radio/stations', 'GET'), sendJSON('/api/radio/plays', 'GET')]);
  const failure = [stations, plays].find(result => result.status === 'rejected');
  if (stations.status === 'fulfilled') renderRadioStations(stations.value.items);
  else renderRadioStations([]);
  if (plays.status === 'fulfilled') renderRadioPlays(plays.value.items);
  radioStatus(failure ? failure.reason.message : '');
}

function renderRadioStations(items) {
  const list = $('radioStations');
  list.replaceChildren();
  if (!items.length) {
    list.append(radioElement('p', 'muted', 'No radio stations in Navidrome.'));
    return;
  }
  for (const station of items) {
    const row = radioElement('div', 'radio-row');
    const main = radioElement('div', 'radio-main');
    main.append(radioElement('p', 'radio-title', station.name),
      radioElement('p', 'radio-meta', station.proxied ? 'Relayed through this app' : 'Direct'));
    const button = radioElement('button', '', station.proxied ? 'Turn off' : 'Turn on');
    button.type = 'button';
    button.setAttribute('aria-label', (station.proxied ? 'Turn off ' : 'Turn on ') + station.name);
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        // The address the owner reached this app at is the one the Navidrome clients can use.
        await sendJSON('/api/radio/stations/' + encodeURIComponent(station.id) + (station.proxied ? '/disable' : '/enable'),
          'POST', {base_url: window.location.origin});
        await loadRadio();
      } catch (error) {
        radioStatus(error.message, 'error');
        button.disabled = false;
      }
    });
    row.append(main, button);
    list.append(row);
  }
}

function renderRadioPlays(items) {
  const list = $('radioPlays');
  list.replaceChildren();
  if (!items.length) {
    list.append(radioElement('p', 'muted', 'Nothing heard yet. Play a relayed station in a Navidrome client.'));
    return;
  }
  for (const play of items) {
    const row = radioElement('div', 'radio-row');
    const main = radioElement('div', 'radio-main');
    main.append(radioElement('p', 'radio-title', play.title),
      radioElement('p', 'radio-meta', [play.artist || 'Unknown artist', play.album].filter(Boolean).join(' · ')),
      radioElement('p', 'radio-meta', play.station_name + ' · ' + radioWhen(play.heard_at) + ' · heard ' + radioHeard(play.listened_seconds)));
    const actions = radioElement('div', 'radio-actions');
    const get = radioElement('button', '', play.grabbed ? 'Requested' : 'Get');
    get.type = 'button';
    get.disabled = !play.artist;
    get.setAttribute('aria-label', 'Get ' + play.title);
    get.addEventListener('click', async () => {
      get.disabled = true;
      get.textContent = 'Searching…';
      try {
        const result = await sendJSON('/api/radio/plays/' + play.id + '/get', 'POST', {});
        const ok = result.ok !== false && result.status !== 'no_matches';
        reportAcquisitionOutcome(result.message || (ok ? 'Download requested.' : 'The request could not be placed.'), ok ? 'success' : 'error');
        await loadRadio();
        if (typeof loadAcquisitions === 'function') loadAcquisitions();
      } catch (error) {
        radioStatus(error.message, 'error');
        get.disabled = false;
        get.textContent = 'Get';
      }
    });
    const remove = radioElement('button', '', 'Remove');
    remove.type = 'button';
    remove.setAttribute('aria-label', 'Remove ' + play.title + ' from the log');
    remove.addEventListener('click', async () => {
      remove.disabled = true;
      try {
        await sendJSON('/api/radio/plays/' + play.id, 'DELETE');
        await loadRadio();
      } catch (error) {
        radioStatus(error.message, 'error');
        remove.disabled = false;
      }
    });
    actions.append(get, remove);
    row.append(main, actions);
    list.append(row);
  }
}

$('refreshRadio').addEventListener('click', loadRadio);
