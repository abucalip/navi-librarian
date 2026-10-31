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
  const [stations, plays, settings] = await Promise.allSettled([
    sendJSON('/api/radio/stations', 'GET'), sendJSON('/api/radio/plays', 'GET'),
    sendJSON('/api/radio/settings', 'GET')]);
  const failure = [stations, plays, settings].find(result => result.status === 'rejected');
  if (settings.status === 'fulfilled') $('radioAppUrl').value = settings.value.app_url;
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
    toggle.addEventListener('click', async () => {
      toggle.disabled = true;
      try {
        // The saved app address wins on the server; without one, the address this tab was opened at.
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
    // The song opens its album's page (or the artist's, when the station named no album); the
    // artist and album in the meta line open theirs.
    const title = radioElement('p', 'radio-title');
    if (play.artist) {
      title.append(buildInlineLink(play.title, play.album
        ? namedAlbumTarget(play.artist, play.album) : namedArtistTarget(play.artist)));
    } else {
      title.textContent = play.title;
    }
    const meta = radioElement('p', 'radio-meta');
    linkArtistName(meta, play.artist || 'Unknown artist');
    if (play.album) {
      meta.append(document.createTextNode(' · '));
      linkAlbumName(meta, play.artist, play.album);
    }
    main.append(title, meta,
      radioElement('p', 'radio-meta', play.station_name + ' · ' + radioWhen(play.heard_at) + ' · heard ' + radioHeard(play.listened_seconds)));
    const actions = radioElement('div', 'radio-actions');
    // The app's action group: this song's own Get, Save, and Remove, which takes the song out of
    // the log. A song the station gave no album for is saved under its own title.
    const saveAlbum = play.album || play.title;
    actions.append(createActionGroup(play.artist, saveAlbum, {artist: play.artist, album: saveAlbum}, {
      getButton: createRadioGetButton(play),
      listName: play.artist ? 'radio' : null,
      dismissTitle: 'Remove from the log',
      dismissLabel: 'Remove ' + play.title + ' from the log',
      onDismiss: async event => {
        const remove = event.currentTarget;
        remove.disabled = true;
        try {
          await sendJSON('/api/radio/plays/' + play.id, 'DELETE');
          await loadRadio();
        } catch (error) {
          radioStatus(error.message, 'error');
          remove.disabled = false;
        }
      }
    }));
    row.append(main, actions);
    list.append(row);
  }
}

$('refreshRadio').addEventListener('click', loadRadio);

$('clearRadioPlays').addEventListener('click', async event => {
  if (!window.confirm('Clear every song from the Heard list?')) return;
  const button = event.currentTarget;
  button.disabled = true;
  try {
    await sendJSON('/api/radio/plays', 'DELETE');
    await loadRadio();
  } catch (error) {
    radioStatus(error.message, 'error');
  } finally {
    button.disabled = false;
  }
});

$('radioAddressForm').addEventListener('submit', async event => {
  event.preventDefault();
  const button = $('saveRadioAddress');
  button.disabled = true;
  try {
    const result = await sendJSON('/api/radio/settings', 'PUT', {app_url: $('radioAppUrl').value});
    await loadRadio();
    radioStatus(result.moved ? 'Saved. ' + result.moved + ' relayed station(s) now use this address.' : 'Saved.', 'success');
  } catch (error) {
    radioStatus(error.message, 'error');
  } finally {
    button.disabled = false;
  }
});
