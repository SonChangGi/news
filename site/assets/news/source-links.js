/* Surface existing source URLs without changing provenance or article content. */
(() => {
  'use strict';
  const seen = new WeakSet();
  const labels = window.NEWS_SOURCE_LABELS || {};
  const make = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  };
  function enhance(card) {
    if (seen.has(card)) return;
    const heading = card.querySelector('h3');
    if (!heading) return;
    seen.add(card);
    const isLibrary = card.classList.contains('card');
    const anchors = isLibrary
      ? [...card.querySelectorAll('.body > .links > a')].filter(a => /^원문(?:\s|$)/.test(a.textContent.trim()))
      : [...card.querySelectorAll('.source-list > li > a[href]')];
    const urls = new Set();
    const sources = [];
    for (const a of anchors) {
      let url;
      try { url = new URL(a.getAttribute('href'), location.href); } catch { continue; }
      if (!['https:', 'http:'].includes(url.protocol) || urls.has(url.href)) continue;
      urls.add(url.href);
      const existing = labels[url.href] || {};
      const meta = isLibrary ? '' : a.closest('li')?.querySelector('.source-meta > span')?.textContent.trim();
      sources.push({url, title: isLibrary ? existing.title : a.textContent.trim().replace(/\s*↗\s*$/, ''), publisher: meta || existing.publisher || ''});
    }
    const block = make('section', 'nd-source-access');
    block.setAttribute('aria-label', '원문 바로가기');
    const header = make('div', 'nd-source-heading');
    header.append(make('h4', '', '원문 바로가기'), make('span', '', sources.length ? `${sources.length}개 · 새 탭` : ''));
    block.append(header);
    if (!sources.length) block.append(make('p', 'nd-source-unavailable', '연결된 원문 링크가 없습니다.'));
    else {
      const list = make('ol', 'nd-source-list');
      sources.forEach((source, i) => {
        const li = make('li');
        const a = make('a', 'nd-source-link');
        a.href = source.url.href; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.referrerPolicy = 'no-referrer';
        const number = make('span', 'nd-source-number', String(i + 1).padStart(2, '0'));
        number.setAttribute('aria-hidden', 'true');
        const text = make('span', 'nd-source-copy');
        const host = source.url.hostname.replace(/^www\./, '');
        text.append(make('span', 'nd-source-publisher', source.publisher && source.publisher !== host ? `${source.publisher} · ${host}` : host));
        text.append(make('span', 'nd-source-title', source.title || `원문 ${i + 1} 열기`));
        const arrow = make('span', 'nd-source-arrow', '↗'); arrow.setAttribute('aria-hidden', 'true');
        a.setAttribute('aria-label', `${source.publisher || host} · ${source.title || `원문 ${i + 1}`} · 새 탭에서 열기`);
        a.append(number, text, arrow); li.append(a); list.append(li);
      });
      block.append(list);
    }
    // Keep original links at the end of the article, immediately before evidence.
    // The library has no evidence disclosure, so use its existing links footer.
    const footer = isLibrary ? card.querySelector('.body > .links') : card.querySelector('.issue-reading > .evidence-panel');
    const body = card.querySelector(isLibrary ? '.body' : '.issue-reading');
    if (footer) footer.before(block);
    else if (body) body.append(block);
  }
  function scan() { document.querySelectorAll('.issue,.library .card').forEach(enhance); }
  scan();
  const results = document.querySelector('.library #results');
  if (results) new MutationObserver(scan).observe(results, {childList:true, subtree:true});
})();
