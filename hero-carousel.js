/* One existing, sourced collection record for each of the archive's 28 periods. */
window.HERO_SELECTION = [
  'prehistory-renmianyuwen-pen', 'xia-erlitou-jue', 'shang-houmuwu-ding',
  'cn-baoji-he-cAR7d', 'spring-autumn-caihou-fanghu', 'north-nmc-247419-1',
  'qin-double-edict-plate', 'western-han-rhino-zun', 'xin-guobao-jinkui-zhiwan',
  'nmc-247253', 'middle-wu-lamp', 'middle-westjin-officials',
  'middle-eastjin-woman', 'middle-sixteen-tile', 'middle-south-travel-brick',
  'middle-north-officials', 'middle-sui-bottle', 'tang-objects-camel-musicians',
  'middle-five-teaware', 'middle-liao-cup', 'met-44735', 'xixia-arch-red-kalavinka',
  'middle-jin-cymbals', 'met-52611', 'middle-dali-guanyin',
  'mural-yuan-yongle-chaoyuan-detail', 'late-ming-crown', 'late-qing-court-robe'
];

window.initHeroCarousel = function (records, showDetail) {
  const root = document.getElementById('heroCarousel');
  if (!root || root.dataset.initialized) return;
  root.dataset.initialized = 'true';
  const slides = window.HERO_SELECTION.map(id => records.find(record => record.id === id)).filter(Boolean);
  if (!slides.length) return;
  const find = id => document.getElementById(id);
  const stage = find('heroStage');
  const caption = find('heroCaption');
  const picker = find('heroEraPicker');
  const toggle = find('heroPlay');
  const progress = root.querySelector('.hero-progress span');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const hoverDevice = window.matchMedia('(hover: hover)');
  const interval = 6000;
  let index = 0;
  let timer;
  let userPaused = reducedMotion.matches;
  let hovered = false;
  let focused = false;
  let inView = true;
  let touchStart = null;
  let touchSwiped = false;
  const shortEra = record => record.era === '夏／二里头文化' ? '夏 · 二里头' : record.era;

  const panels = slides.map((record, i) => {
    const panel = document.createElement('div');
    panel.className = 'hero-slide' + (i === 0 ? ' is-active' : '');
    panel.setAttribute('role', 'group');
    panel.setAttribute('aria-roledescription', '幻灯片');
    panel.setAttribute('aria-label', `${i + 1} / ${slides.length} · ${shortEra(record)} · ${record.title}`);
    panel.setAttribute('aria-hidden', String(i !== 0));
    const image = document.createElement('img');
    image.alt = `${shortEra(record)} · ${record.title}`;
    image.referrerPolicy = 'no-referrer';
    image.decoding = 'async';
    image.draggable = false;
    if (i === 0) image.fetchPriority = 'high';
    const fallback = document.createElement('span');
    fallback.className = 'hero-image-message';
    fallback.textContent = '影像载入中';
    image.onload = () => { panel.classList.add('is-loaded'); fallback.hidden = true; };
    image.onerror = () => {
      image.hidden = true;
      panel.classList.add('has-error');
      fallback.hidden = false;
      fallback.textContent = '原图暂时无法载入，可查看下方出处';
    };
    panel.append(image, fallback);
    stage.append(panel);
    const option = document.createElement('option');
    option.value = String(i);
    option.textContent = `${String(i + 1).padStart(2, '0')} · ${shortEra(record)}`;
    picker.append(option);
    return { panel, image, record };
  });
  stage.querySelector('.hero-initial')?.remove();
  const loadImage = i => {
    const { image, record } = panels[(i + slides.length) % slides.length];
    if (!image.getAttribute('src')) image.src = record.localImage || record.previewUrl || record.imageUrl;
  };
  const canPlay = () => slides.length > 1 && !userPaused && !hovered && !focused && inView && !document.hidden && !document.querySelector('dialog[open]') && !find('hero').hidden;
  function schedule() {
    clearTimeout(timer);
    root.classList.remove('is-playing');
    progress.style.animation = 'none';
    void progress.offsetWidth;
    progress.style.animation = '';
    const playing = canPlay();
    root.classList.toggle('is-playing', playing);
    toggle.setAttribute('aria-label', userPaused ? '播放朝代轮播' : '暂停朝代轮播');
    toggle.setAttribute('aria-pressed', String(userPaused));
    const icon = userPaused ? '▶' : 'Ⅱ';
    const label = userPaused ? '播放' : '暂停';
    if (toggle.firstElementChild.textContent !== icon) toggle.firstElementChild.textContent = icon;
    if (toggle.lastElementChild.textContent !== label) toggle.lastElementChild.textContent = label;
    find('heroPlayStatus').textContent = userPaused ? '已暂停' : playing ? '每 6 秒切换' : '浏览中暂停';
    caption.setAttribute('aria-live', playing ? 'off' : 'polite');
    if (playing) timer = setTimeout(() => go(index + 1), interval);
  }
  function go(next) {
    index = (next + slides.length) % slides.length;
    const record = slides[index];
    root.dataset.index = String(index);
    root.dataset.recordId = record.id;
    panels.forEach(({ panel }, i) => {
      panel.classList.toggle('is-active', i === index);
      panel.setAttribute('aria-hidden', String(i !== index));
    });
    loadImage(index);
    loadImage(index + 1);
    find('heroCount').textContent = `${String(index + 1).padStart(2, '0')} / ${String(slides.length).padStart(2, '0')}`;
    find('heroTitle').textContent = record.title;
    find('heroEra').textContent = shortEra(record);
    find('heroSource').textContent = record.imageCredit || record.institutionShort || record.institution;
    find('heroSource').title = `${record.institution}${record.objectNumber && !/未载|不适用/.test(record.objectNumber) ? ' · ' + record.objectNumber : ''}`;
    find('heroMark').textContent = record.era === '夏／二里头文化' ? '夏' : record.era;
    find('heroMark').classList.toggle('is-long', find('heroMark').textContent.length > 2);
    find('heroDetail').setAttribute('aria-label', `查看${record.title}的原始著录`);
    picker.value = String(index);
    schedule();
  }
  find('heroPrevious').addEventListener('click', () => go(index - 1));
  find('heroNext').addEventListener('click', () => go(index + 1));
  toggle.addEventListener('click', () => { userPaused = !userPaused; schedule(); });
  picker.addEventListener('change', () => go(Number(picker.value)));
  find('heroDetail').onclick = () => { showDetail(slides[index].id); schedule(); };
  root.addEventListener('pointerenter', () => { if (hoverDevice.matches) { hovered = true; schedule(); } });
  root.addEventListener('pointerleave', () => { hovered = false; schedule(); });
  root.addEventListener('focusin', () => { focused = true; schedule(); });
  root.addEventListener('focusout', event => {
    if (!root.contains(event.relatedTarget)) { focused = false; schedule(); }
  });
  root.addEventListener('keydown', event => {
    if (event.target.tagName === 'SELECT' || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault();
    go(index + (event.key === 'ArrowRight' ? 1 : -1));
  });
  stage.addEventListener('pointerdown', event => {
    if (event.pointerType !== 'touch') return;
    touchStart = { x: event.clientX, y: event.clientY };
    touchSwiped = false;
  });
  stage.addEventListener('pointermove', event => {
    if (!touchStart || touchSwiped) return;
    const dx = event.clientX - touchStart.x;
    const dy = event.clientY - touchStart.y;
    if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      touchSwiped = true;
      go(index + (dx < 0 ? 1 : -1));
    }
  });
  for (const name of ['pointerup', 'pointercancel']) stage.addEventListener(name, () => { touchStart = null; });
  document.addEventListener('visibilitychange', schedule);
  reducedMotion.addEventListener('change', () => { userPaused = reducedMotion.matches; schedule(); });
  new IntersectionObserver(entries => { inView = entries[0].isIntersecting; schedule(); }, { threshold: 0.1 }).observe(root);
  new MutationObserver(schedule).observe(find('hero'), { attributes: true, attributeFilter: ['hidden'] });
  document.querySelectorAll('dialog').forEach(dialog => {
    new MutationObserver(schedule).observe(dialog, { attributes: true, attributeFilter: ['open'] });
  });
  go(0);
};
