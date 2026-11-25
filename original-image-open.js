/* Open a catalog image's recorded source file directly from its preview. */
(() => {
  let byId;
  let byPreview;

  function records() {
    return [
      window.ARCHIVE_DATA,
      window.ATLAS_CANDIDATES,
      window.EASTERN_HAN_DATA,
      window.JIN_DATA,
      window.LIAO_DATA,
      window.QIN_DATA,
      window.SHANG_DATA,
      window.SONG_DATA,
      window.SPRING_AUTUMN_DATA,
      window.SUI_DATA,
      window.WARRING_STATES_DATA,
      window.WEIJIN_DATA,
      window.WESTERN_HAN_DATA,
      window.WESTERN_ZHOU_DATA,
    ].flatMap(data => data?.records || []);
  }

  function index() {
    if (byId) return;
    byId = new Map();
    byPreview = new Map();
    for (const row of records()) {
      if (!row) continue;
      const original = row.originalImageUrl || row.imageUrl;
      if (row.displayMode === 'source-only' || !/^https?:\/\//i.test(original || '')) continue;
      if (!byId.has(row.id)) byId.set(row.id, original);
      for (const preview of [row.localImage, row.previewUrl, row.imageUrl]) {
        if (!preview) continue;
        let key;
        try { key = new URL(preview, location.href).href; } catch { continue; }
        if (!byPreview.has(key)) byPreview.set(key, original);
        else if (byPreview.get(key) !== original) byPreview.set(key, null);
      }
    }
  }

  function openPreview(event) {
    const button = event.target.closest('button[data-detail]');
    const image = event.target.closest('img') || button?.querySelector('img');
    if (!image) return;
    if (image.closest('a[href]')) return;
    const direct = image.getAttribute('data-original-image');
    if (!/^https?:\/\//i.test(direct || '')) index();
    const id = image.closest('[data-detail]')?.dataset.detail;
    const original = /^https?:\/\//i.test(direct || '') ? direct : byId.get(id) || byPreview.get(image.src);
    if (!original) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    window.open(original, '_blank', 'noopener');
  }

  document.addEventListener('click', openPreview, true);
  document.addEventListener('keydown', event => {
    if (!['Enter', ' '].includes(event.key)) return;
    const button = event.target.closest('button[data-detail]');
    if (button?.querySelector('img')) openPreview({
      target: button.querySelector('img'),
      preventDefault: () => event.preventDefault(),
      stopImmediatePropagation: () => event.stopImmediatePropagation(),
    });
  }, true);
})();
