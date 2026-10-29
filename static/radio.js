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
      radioElement('p', 'radio-meta', station.proxied ? 'On: relayed through this app' : 'Off: plays directly'));
    const toggle = radioElement('button', 'radio-switch');
    toggle.type = 'button';
    toggle.setAttribute('role', 'switch');
    toggle.setAttribute('aria-checked', String(station.proxied));
    toggle.setAttribute('aria-label', 'Grab ' + station.name);
    toggle.append(radioElement('span', 'radio-switch-knob'));
    toggle.addEventListener('click', async () => {
      toggle.disabled = true;
      try {
        // The address the owner reached this app at is the one the Navidrome clients can use.
        await sendJSON('/api/radio/stations/' + encodeURIComponent(station.id) + (station.proxied ? '/disable' : '/enable'),
          'POST', {base_url: window.location.origin});
        await loadRadio();
      } catch (error) {
        radioStatus(error.message, 'error');
        toggle.disabled = false;
      }
    });
    row.append(main, toggle);
    list.append(row);
  }
}

// The app's own Get button (app.js), so a logged song looks and behaves like Get everywhere else.
function createRadioGetButton(play) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'get-album get-track';
  button.dataset.noun = 'song';
  decorateGetButton(button);
  setGetButtonState(button, play.grabbed ? 'requested' : 'idle', play.artist, play.title);
  if (!play.artist) {
    button.disabled = true;
    button.title = 'The station did not name an artist';
    return button;
  }
  button.addEventListener('click', async () => {
    if (button.disabled && !button.classList.contains('is-failed')) return;
    setGetButtonState(button, 'pending', play.artist, play.title);
    try {
      const result = await sendJSON('/api/radio/plays/' + play.id + '/get', 'POST', {});
      if (result.ok === false || result.status === 'no_matches') {
        setGetButtonState(button, 'failed', play.artist, play.title);
        reportAcquisitionOutcome(result.message || result.error || 'The request could not be placed.', 'error');
      } else {
        setGetButtonState(button, 'requested', play.artist, play.title);
        reportAcquisitionOutcome(result.message, 'success');
      }
      if (typeof loadAcquisitions === 'function') loadAcquisitions();
    } catch (error) {
      setGetButtonState(button, 'failed', play.artist, play.title);
      reportAcquisitionOutcome(error.message, 'error');
    }
  });
  return button;
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
    const get = createRadioGetButton(play);
    const remove = radioElement('button', 'radio-remove');
    remove.type = 'button';
    remove.setAttribute('aria-label', 'Remove ' + play.title + ' from the log');
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    icon.setAttribute('class', 'icon');
    icon.setAttribute('viewBox', '0 0 24 24');
    icon.setAttribute('aria-hidden', 'true');
    icon.setAttribute('focusable', 'false');
    const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    use.setAttribute('href', '/static/icons.svg#x');
    icon.append(use);
    remove.append(icon);
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
