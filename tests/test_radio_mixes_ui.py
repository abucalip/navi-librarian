"""Exercise production dialog handlers; visual/browser verification remains separate."""

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
  constructor(tag = 'div') {
    this.tag = tag; this.children = []; this.listeners = {}; this.attrs = {};
    this.value = ''; this.hidden = false; this.disabled = false;
    this.textContent = ''; this.isConnected = true;
  }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(key, value) { this.attrs[key] = value; }
  addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
  async emit(name) { for (const fn of this.listeners[name] || []) await fn({preventDefault() {}}); }
  focus() { document.activeElement = this; }
  showModal() { this.open = true; }
  close() { this.open = false; return this.emit('close'); }
}
const html = fs.readFileSync(process.argv[2], 'utf8');
const ids = new Map([...html.matchAll(/id="(radioMix[^"]+|artistMixActions)"/g)]
  .map(match => [match[1], new Element()]));
const el = name => ids.get('radioMix' + name);
const discover = new Element('button'); discover.dataset = {mixKind: 'discovery'};
const artist = new Element('button'); artist.dataset = {mixKind: 'artist'};
el('Kind').value = 'artist'; el('SeedType').value = 'artist';
el('Mode').value = 'easy'; el('Familiarity').value = 'familiar';
el('Form').elements = ['Kind', 'SeedType', 'Seed', 'Mode', 'Familiarity', 'Generate', 'ArtistSearch'].map(el);
const document = {
  hidden: false, getElementById: id => ids.get(id),
  createElement: tag => new Element(tag), querySelectorAll: () => [discover, artist],
  addEventListener() {},
};
const calls = [];
let handler;
const context = {document, window: {}, console,
  setTimeout: () => 1, clearTimeout() {},
  fetch: async (url, options) => {
    calls.push({url, options});
    return handler(url, options);
  },
};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const reply = (data, ok = true) => ({ok, json: async () => data});
const data = {kind: 'discovery', state: 'ready', preview_id: 'a'.repeat(32),
  index_state: 'fresh', owned_count: 2, tracks: [
    {position: 0, title: 'Owned', artist: 'Band', song_id: 'one', match_state: 'owned'},
    {position: 1, title: '<img src=x onerror=alert(1)>', artist: 'Band', match_state: 'missing'},
    {position: 2, title: 'Versions', artist: 'Band', match_state: 'ambiguous'},
    {position: 3, title: 'Unknown', artist: 'Band', match_state: null},
    {position: 4, title: 'Owned', artist: 'Band', song_id: 'one', match_state: 'owned'},
  ]};
const clone = () => JSON.parse(JSON.stringify(data));
const flush = async () => { for (let n = 0; n < 20; n++) await Promise.resolve(); };
(async () => {
  await discover.emit('click');
  assert(el('Dialog').open);
  assert.equal(el('SeedType').value, 'tag');
  assert.equal(document.activeElement, el('Seed'));
  el('Seed').value = 'jazz';
  handler = () => reply(clone());
  await el('Form').emit('submit');
  const rows = el('Tracks').children;
  assert.equal(rows.length, 5);
  assert.equal(rows[0].children[1].hidden, true);
  assert.equal(rows[1].children[1].disabled, false);
  assert.equal(rows[1].children[0].children[0].textContent, data.tracks[1].title);
  assert.equal(rows[2].children[1].disabled, true);
  assert.equal(rows[3].children[1].disabled, true);
  assert.equal(el('Save').disabled, false);
  assert.equal(JSON.parse(calls[0].options.body).tag, 'jazz');

  let resolveDownload;
  handler = (url, options) => options?.method === 'POST'
    ? new Promise(resolve => { resolveDownload = resolve; }) : reply(clone());
  const downloading = rows[1].children[1].emit('click');
  await flush();
  await rows[1].children[1].emit('click');
  assert.equal(calls.filter(call => call.url.endsWith('/tracks/1/download')).length, 1);
  resolveDownload(reply({ok: true, status: 'queued_unconfirmed'}));
  await downloading;
  await flush();
  assert(rows[1].children[1].disabled);

  let resolveSave;
  handler = () => new Promise(resolve => { resolveSave = resolve; });
  const saving = el('Save').emit('click');
  await flush();
  await el('Save').emit('click');
  assert.equal(calls.filter(call => call.url.endsWith('/save')).length, 1);
  resolveSave(reply({state: 'saved', saved_count: 2, playlist_id: 'private'}));
  await saving;
  assert(el('Save').disabled);
  assert.match(el('Status').textContent, /Saved 2 tracks/);
  await el('Close').emit('click');
  assert.equal(document.activeElement, discover);

  context.window.radioMixes.setArtist({mbid: 'artist-id', name: 'Artist', owned: false});
  assert.equal(ids.get('artistMixActions').children.length, 1);
  context.window.radioMixes.setArtist({mbid: 'artist-id', name: 'Artist', owned: true});
  assert.equal(ids.get('artistMixActions').children.length, 2);
  const artistButton = ids.get('artistMixActions').children[0];
  await artistButton.emit('click');
  assert.equal(el('Kind').value, 'artist');
  assert.equal(el('Seed').value, 'Artist');
  assert.equal(el('SeedTypeLabel').hidden, true);
  assert.equal(el('ModeLabel').hidden, true);
  context.window.radioMixes.setArtist(null);
  assert(ids.get('artistMixActions').hidden);

  let resolvePreview;
  handler = () => new Promise(resolve => { resolvePreview = resolve; });
  const generating = el('Form').emit('submit');
  await flush();
  await el('Dialog').close();
  resolvePreview(reply(clone()));
  await generating;
  assert.equal(el('Tracks').children.length, 0);
  await discover.emit('click');
  el('Seed').value = 'jazz';
  handler = () => reply({state: 'unconfigured', tracks: []});
  await el('Form').emit('submit');
  assert.match(el('Status').textContent, /Settings/);
  assert(el('Save').disabled);
  handler = () => reply({detail: 'Provider unavailable'}, false);
  await el('Form').emit('submit');
  assert.equal(el('Status').textContent, 'Provider unavailable');
  assert.equal(el('Generate').disabled, false);
  await el('Dialog').close();
  await artist.emit('click');
  el('Seed').value = 'Band';
  await el('Seed').emit('input');
  await el('Form').emit('submit');
  assert.match(el('Status').textContent, /Find artist/);
  handler = () => reply({items: [{name: 'Band', mbid: 'selected-id'}, {name: 'Unresolved'}], total: 2});
  await el('ArtistSearch').emit('click');
  assert.equal(el('ArtistResults').children.length, 1);
  await el('ArtistResults').children[0].emit('click');
  assert.equal(el('Seed').value, 'Band');
  handler = () => reply({...clone(), kind: 'artist'});
  await el('Form').emit('submit');
  assert.equal(JSON.parse(calls.at(-1).options.body).artist_mbid, 'selected-id');
  assert(el('Tracks').children[1].children[1].hidden);
  console.log('Dialog handlers passed: ordering, refusal states, duplicate actions, stale replies, focus and recovery.');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""


@pytest.mark.skipif(shutil.which('node') is None, reason='Node is needed for dialog handler verification')
def test_dialog_actions_and_recovery():
    result = subprocess.run(
        ['node', '-e', RUNNER, str(ROOT / 'static/listening-room/radio-mixes.js'),
         str(ROOT / 'app/templates/index.html')], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
