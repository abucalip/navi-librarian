(() => {
  const badges = document.querySelectorAll('.version-update-badge');
  const dialog = document.getElementById('dockerUpdateDialog');
  const version = document.getElementById('dockerUpdateVersion');
  const status = document.getElementById('dockerUpdateStatus');
  const install = document.getElementById('dockerUpdateInstall');
  const releaseLink = document.getElementById('dockerUpdateRelease');
  const endpoint = '/api/docker-update';
  let release;
  let pendingDigest;

  async function request(path, options) {
    const response = await fetch(endpoint + path, { cache: 'no-store', ...options });
    if (!response.ok) throw new Error('Update request failed');
    return response.json();
  }

  async function check() {
    try {
      const result = await request('');
      release = result.available;
      version.textContent = release ? `Version ${release.version} is available.` : '';
      releaseLink.hidden = !release;
      if (release) {
        releaseLink.href = 'https://github.com/abucalip/navi-librarian/tree/' +
          encodeURIComponent(release.version);
      }
      const job = result.installer;
      if (job?.state === 'running' && !pendingDigest) {
        status.textContent = 'Installing update. Discair may briefly disconnect.';
        monitor(job.digest);
      }
      install.hidden = !release || !job;
      install.disabled = Boolean(pendingDigest);
      badges.forEach(badge => { badge.hidden = !release && !pendingDigest; });
      if (release && !job) status.textContent = 'Install this update from the Docker host.';
      if (release && job?.state === 'failed' && job.digest === release.digest) {
        status.textContent = 'The previous install failed. Check the host updater logs.';
      }
    } catch {
      // Keep the last known badge state when the app is temporarily unreachable.
    }
  }

  async function monitor(digest) {
    pendingDigest = digest;
    install.disabled = true;
    // The host may need time to pull the image and wait for both health checks.
    for (let attempt = 0; attempt < 255; attempt += 1) {
      await new Promise(resolve => setTimeout(resolve, 5000));
      let job;
      try {
        job = await request('/install', { signal: AbortSignal.timeout(4000) });
      } catch {
        continue;
      }
      if (job?.digest !== digest || job.state === 'running') continue;
      if (job.state === 'succeeded') {
        window.location.reload();
        return;
      }
      if (job.state === 'failed') {
        status.textContent = 'Install failed. Check the host updater logs.';
        pendingDigest = null;
        install.disabled = false;
        return;
      }
    }
    pendingDigest = null;
    install.disabled = false;
    status.textContent = 'Could not confirm the update. Check the host updater logs.';
  }

  install.addEventListener('click', async () => {
    if (!release || pendingDigest ||
        !window.confirm(`Install ${release.version}? Discair will briefly restart.`)) return;
    const digest = release.digest;
    install.disabled = true;
    status.textContent = 'Starting the update…';
    try {
      await request('/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Discair-Update': 'install' },
        body: JSON.stringify({ digest }),
      });
      status.textContent = 'Installing update. Discair may briefly disconnect.';
      monitor(digest);
    } catch {
      status.textContent = 'Could not start the update. Check availability and try again.';
      install.disabled = false;
      await check();
    }
  });

  badges.forEach(badge => badge.addEventListener('click', () => dialog.showModal()));
  check();
  const checkTimer = setInterval(() => {
    if (!document.hidden && !pendingDigest) check();
  }, 15 * 60 * 1000);
  window.addEventListener('pagehide', event => {
    if (!event.persisted) clearInterval(checkTimer);
  });
})();
