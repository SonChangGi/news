/* News reader adapter. Native article nodes, content and state remain authoritative. */
(() => {
  'use strict';
  const root = document.documentElement;
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const library = !!$('.library');
  const shell = $('.shell');
  if (!shell) return;
  const toc = $('.weekly-contents');
  const header = $('.briefing-header') || $('.library .page-header');
  if (header) {
    const quick = document.createElement('nav'); quick.className = 'nd-quick'; quick.setAttribute('aria-label', '뉴스 빠른 이동');
    quick.innerHTML = `<button type="button" class="nd-search-jump">뉴스 검색 <kbd>/</kbd></button>`;
    (header.querySelector('.header-meta') || header).append(quick);
    quick.querySelector('button').addEventListener('click', focusSearch);
  }
  function focusSearch() {
    const search = $(library ? '#query' : '#search');
    if (search) { search.scrollIntoView({block:'center', behavior:'instant'}); search.focus({preventScroll:true}); }
  }
  document.addEventListener('keydown', event => {
    if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey || event.isComposing || $('dialog[open]') || event.target.closest('input,textarea,select,[contenteditable="true"]')) return;
    event.preventDefault(); focusSearch();
  });
  // Keep ordinary filters visible; disclose less frequent reading preferences.
  const controls = library ? $('.tool-right') : $('.reading-controls');
  if (controls) {
    const prefs = document.createElement('details'); prefs.className = 'nd-preferences';
    const summary = document.createElement('summary'); summary.textContent = '읽기 설정';
    controls.before(prefs); prefs.append(summary, controls);
    prefs.addEventListener('keydown', event => {if (event.key === 'Escape') {prefs.open=false; summary.focus();}});
    document.addEventListener('pointerdown', event => {if(prefs.open && !prefs.contains(event.target)) prefs.open=false;});
  }
  // Native card handlers own background/title toggling and ignore links, controls
  // and text selections. Do not intercept those clicks in the presentation layer.
  const live = document.createElement('div'); live.className='nd-toast'; live.setAttribute('role','status'); live.setAttribute('aria-live','polite'); document.body.append(live);
  let toastTimer;
  document.addEventListener('click', event => {
    const save = event.target.closest?.('.reader-save,.save');
    if (!save) return;
    const saving=save.getAttribute('aria-pressed') !== 'true';
    requestAnimationFrame(() => {
      live.textContent = saving ? '나중에 읽을 이슈에 저장했습니다.' : '저장을 해제했습니다.';
      live.classList.add('is-visible'); clearTimeout(toastTimer); toastTimer=setTimeout(()=>live.classList.remove('is-visible'),2200);
    });
  }, true);
  if (!library) {
    const empty = $('#no-results');
    const recovery = document.createElement('button'); recovery.type='button'; recovery.className='nd-empty-reset'; recovery.textContent='모든 뉴스 다시 보기'; recovery.hidden=true;
    empty?.after(recovery); recovery.addEventListener('click',()=>$('#filter-reset').click());
    if (empty) new MutationObserver(()=>{recovery.hidden=empty.hidden;}).observe(empty,{attributes:true,attributeFilter:['hidden']});
  }
  // A small reading dock remains available after the overview leaves the screen.
  const dock = document.createElement('nav'); dock.className='nd-dock'; dock.setAttribute('aria-label','읽는 중 빠른 탐색'); dock.hidden=true;
  dock.innerHTML='<span class="nd-current">뉴스 읽기</span><button type="button" class="nd-dock-search">검색</button><button type="button" class="nd-dock-toc">목차</button><a href="#top" aria-label="맨 위로">↑</a><span class="nd-progress" aria-hidden="true"></span>';
  document.body.append(dock);
  dock.querySelector('.nd-dock-search').addEventListener('click',focusSearch);
  dock.querySelector('.nd-dock-toc').addEventListener('click',()=>$('.q4-outline')?.click());
  let queued=false;
  const onScroll=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{
    queued=false; dock.hidden=scrollY<650 && !dock.contains(document.activeElement);
    const denominator=document.documentElement.scrollHeight-innerHeight;
    dock.querySelector('.nd-progress').style.transform=`scaleX(${denominator>0?scrollY/denominator:0})`;
  });};
  addEventListener('scroll',onScroll,{passive:true}); onScroll();
  const sectionNodes = $$('[data-report-section]');
  const chapters = new IntersectionObserver(entries => {
    for (const entry of entries) if(entry.isIntersecting) {
      const heading = entry.target.querySelector('h2');
      dock.querySelector('.nd-current').textContent=heading?.textContent||'뉴스 읽기';
      toc?.querySelectorAll('a').forEach(a=>{
        if(a.hash==='#'+heading?.id)a.setAttribute('aria-current','location');
        else a.removeAttribute('aria-current');
      });
    }
  }, {rootMargin:'-15% 0px -65% 0px',threshold:0});
  sectionNodes.forEach(n=>chapters.observe(n));
  const reset = $('#filter-reset');
  if (reset) {
    const syncFiltered=()=>{root.dataset.ndFiltered=String(!reset.hidden);};
    new MutationObserver(syncFiltered).observe(reset,{attributes:true,attributeFilter:['hidden']});
    syncFiltered();
  }
  document.body.dataset.designReady='true';
})();

/* Weekly display controls: preserve every claim and citation in the native DOM. */
(() => {
  'use strict';
  const root = document.querySelector('[data-weekly-reading="judgment-first-v1"]');
  if (!root) return;
  const controls = root.querySelector('.narrative-reading-controls');
  const judgments = root.querySelector('#weekly-judgments');
  const developments = root.querySelector('#weekly-developments');
  const sections = [...root.querySelectorAll('.narrative-development')];
  if (!controls || !judgments || !developments || !sections.length) return;
  // Default is the HTML's expanded account. No URL, storage or analysis input changes.
  controls.hidden = false;
  const sync = () => {
    judgments.setAttribute('aria-pressed', String(sections.every(node => !node.open)));
    developments.setAttribute('aria-pressed', String(sections.every(node => node.open)));
  };
  for (const [button, expanded] of [[judgments, false], [developments, true]]) {
    button.addEventListener('click', () => {sections.forEach(node => {node.open = expanded;}); sync();});
  }
  sections.forEach(node => node.addEventListener('toggle', sync));
  const reveal = () => {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    const section = target?.closest('.narrative-development');
    if (section && root.contains(section)) {section.open = true; sync();}
  };
  window.addEventListener('hashchange', reveal);
  reveal(); sync();
})();
