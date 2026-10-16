# Vendored: Notyf

Transient toast notifications, used for acquisition success/error feedback in `app.js`.

Vendored rather than loaded from a CDN so the application keeps working without a
third-party network dependency at runtime (see `AGENTS.md` and
`docs/FRONTEND_DESIGN_GUIDE.md`, which require approval for new external asset
dependencies; this addition was approved for that reason).

## Provenance

| Field | Value |
|---|---|
| Package | `notyf` |
| Version | `3.10.0` (pinned) |
| Upstream | https://github.com/caroso1222/notyf |
| Source | `https://registry.npmjs.org/notyf/-/notyf-3.10.0.tgz` |
| License | MIT (`LICENSE` in this directory, © 2016-2020 Carlos Roso) |

The tarball was verified against the npm registry metadata before extraction:

- `dist.shasum` (sha1): `67a64443c69ea0e6495c56ea0f91198860163d06`
- `dist.integrity` (sha512): `sha512-Mtnp+0qiZxgrH+TzVlzhWyZceHdAZ/UWK0/ju9U0HQeDpap1mZ8cC7H5wSI5mwgni6yeAjaxsTw0sbMK+aSuHw==`

Both matched the downloaded archive exactly.

## Vendored files

| File | sha256 |
|---|---|
| `notyf.min.js` | `52796990c2dab1a4f1d99aa8bf105751c4398eade829769967569610d3451131` |
| `notyf.min.css` | `23092f64d442ff74b6e8ed605b08c120d9ab3d9e3362f3d7e33ffdf0e2961e44` |

Only the two prebuilt distribution files are vendored. `notyf.es.js`, `notyf.umd.js`,
the `.d.ts` files and the unminified source are not needed and are intentionally omitted.
Nothing in the vendored files was modified.

## Update procedure

1. Download the new version's tarball from the npm registry and verify `shasum` and
   `integrity` against `https://registry.npmjs.org/notyf/<version>`.
2. Replace `notyf.min.js`, `notyf.min.css` and `LICENSE`, and update the hashes above.
3. Re-check the integration points in `app.js` (`acquisitionToasts`) and the theming in
   `app.css`, since both depend on Notyf's generated class names
   (`notyf`, `notyf__toast`, `notyf__message`, `notyf-announcer`).
