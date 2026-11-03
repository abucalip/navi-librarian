/* Theme and font for the web UI (owner-approved 2026-11-02). Loaded synchronously in <head> on every page so the
   saved choice is on <html> before first paint (no flash). The choice lives in localStorage on this browser only.
     data-theme  the theme id; data-brut is set on the Neobrut themes; data-font is the font pair id;
     data-layout is set on the themes that rearrange the pages (Tape Deck: "tape", Ledger Room: "ledger", Crate Wall: "crate", Zine Spread: "zine", Pipeline Board: "pipeline"; static/layouts.css) and absent otherwise.
   Settings > Appearance (static/app.js) reads the catalogue below and calls set(). The defaults are today's look:
   the Ink theme and the Discair font pair. */
(function () {
  'use strict';
  var THEMES = [
    { id: 'ink', label: 'Ink', group: 'Dark', dark: true, bar: '#0f0e0d' },
    { id: 'vinyl', label: 'Vinyl', group: 'Dark', dark: true, bar: '#080808' },
    { id: 'nocturne', label: 'Nocturne', group: 'Dark', dark: true, bar: '#0c0a14' },
    { id: 'parchment', label: 'Parchment', group: 'Light', dark: false, bar: '#ebe2cf' },
    { id: 'gallery', label: 'Gallery', group: 'Light', dark: false, bar: '#e8ecf1' },
    { id: 'sleeve', label: 'Sleeve', group: 'Light', dark: false, bar: '#ddd0bb' },
    { id: 'cassette', label: 'Brut \u00b7 Cassette', group: 'Neobrut', dark: false, brut: true, bar: '#fbe9a9' },
    { id: 'mintdesk', label: 'Brut \u00b7 Mint Desk', group: 'Neobrut', dark: false, brut: true, bar: '#cff3c8' },
    { id: 'nightshift', label: 'Brut \u00b7 Night Shift', group: 'Neobrut', dark: true, brut: true, bar: '#0a0a0a' },
    { id: 'tapelime', label: 'Tape \u00b7 Lime', group: 'Tape Deck', dark: false, brut: true, layout: 'tape', bar: '#fffdf6' },
    { id: 'tapecobalt', label: 'Tape \u00b7 Cobalt', group: 'Tape Deck', dark: false, brut: true, layout: 'tape', bar: '#fbfcff' },
    { id: 'tapetangerine', label: 'Tape \u00b7 Tangerine', group: 'Tape Deck', dark: false, brut: true, layout: 'tape', bar: '#fffaf2' },
    { id: 'ledgerslate', label: 'Ledger \u00b7 Slate', group: 'Ledger Room', dark: false, brut: true, layout: 'ledger', bar: '#fbfcff' },
    { id: 'ledgerplum', label: 'Ledger \u00b7 Plum', group: 'Ledger Room', dark: false, brut: true, layout: 'ledger', bar: '#fffaff' },
    { id: 'ledgermono', label: 'Ledger \u00b7 Mono', group: 'Ledger Room', dark: false, brut: true, layout: 'ledger', bar: '#ffffff' },
    { id: 'cratekraft', label: 'Crate \u00b7 Kraft', group: 'Crate Wall', dark: false, brut: true, layout: 'crate', bar: '#d9b98a' },
    { id: 'cratemint', label: 'Crate \u00b7 Mint', group: 'Crate Wall', dark: false, brut: true, layout: 'crate', bar: '#a9d9b4' },
    { id: 'cratenight', label: 'Crate \u00b7 Night', group: 'Crate Wall', dark: true, brut: true, layout: 'crate', bar: '#1b1713' },
    { id: 'zine', label: 'Zine \u00b7 Yellow', group: 'Zine Spread', dark: false, brut: true, layout: 'zine', bar: '#ffde59' },
    { id: 'pipeline', label: 'Pipeline \u00b7 Orange', group: 'Pipeline Board', dark: false, brut: true, layout: 'pipeline', bar: '#ff7a1a' }
  ];
  var FONTS = [
    { id: 'discair', label: 'Discair (current)' },
    { id: 'baseline', label: 'Brut \u00b7 Baseline' },
    { id: 'technical', label: 'Brut \u00b7 Technical' },
    { id: 'editorial', label: 'Brut \u00b7 Editorial' },
    { id: 'modern', label: 'Brut \u00b7 Modern' },
    { id: 'shout', label: 'Brut \u00b7 Poster shout' },
    { id: 'swiss', label: 'Brut \u00b7 Swiss brut' }
  ];
  var KEY = { theme: 'discair.theme', font: 'discair.font' };
  var DEFAULT = { theme: 'ink', font: 'discair' };

  function read(key) { try { return window.localStorage.getItem(key); } catch (e) { return null; } }
  function write(key, value) { try { window.localStorage.setItem(key, value); } catch (e) { /* private mode: applies for this page only */ } }
  function byId(id) { for (var i = 0; i < THEMES.length; i++) if (THEMES[i].id === id) return THEMES[i]; return null; }
  function fontOk(id) { for (var i = 0; i < FONTS.length; i++) if (FONTS[i].id === id) return true; return false; }

  // A saved id that no longer exists (or a value kept from an older version) falls back to the default.
  function get(kind) {
    var value = read(KEY[kind]);
    if (kind === 'theme') return byId(value) ? value : DEFAULT.theme;
    return fontOk(value) ? value : DEFAULT.font;
  }

  function resolve() { return byId(get('theme')); }

  function apply() {
    var root = document.documentElement, theme = resolve();
    root.setAttribute('data-theme', theme.id);
    if (theme.brut) root.setAttribute('data-brut', ''); else root.removeAttribute('data-brut');
    if (theme.layout) root.setAttribute('data-layout', theme.layout); else root.removeAttribute('data-layout');
    root.setAttribute('data-font', get('font'));
    // The browser's own bar (a phone's address bar) takes the theme's top-bar colour.
    var meta = document.querySelector('meta[name="theme-color"]');
    if (!meta) { meta = document.createElement('meta'); meta.setAttribute('name', 'theme-color'); document.head.appendChild(meta); }
    meta.setAttribute('content', theme.bar);
  }

  function set(kind, id) {
    if (!KEY[kind]) return;
    write(KEY[kind], id);
    apply();
  }

  apply();
  window.DiscairAppearance = { THEMES: THEMES, FONTS: FONTS, get: get, set: set, resolve: resolve };
})();
