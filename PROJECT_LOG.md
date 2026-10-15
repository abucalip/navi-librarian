## 2026-10-15 — PR #147 merged: slskd settings boolean validation

- Audited the settings API and identified that `PUT /api/settings/slskd` silently dropped `auto_acquire_for_me`; unvalidated forwarding could cause string truthiness to enable a setting unintentionally.
- Added strict JSON-boolean validation, explicit boolean forwarding, omission preservation, and regression tests for accepted and rejected values.
- PR #147 merged by squash. Tested head: `22db7e7b4414f1ff3df7440bc47aece41bf0ae1d`; merge commit: `9ce0ae37ae207f79180d98b10f71147736fe2a75`.
- All four required PR-head workflows passed: syntax, container runtime smoke, Docker packaging, and Docker image validation. Image publication remains paused. No deployment or production runtime verification claimed.

