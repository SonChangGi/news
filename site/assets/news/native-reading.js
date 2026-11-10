/* Native cards remain the only reading surface. */
(() => {
  'use strict';
  if (!location.pathname.startsWith('/news/')) return;
  const root = document.querySelector('.library') || document.querySelector('main');
  if (!root) return;
  const deduplicate = () => root.querySelectorAll('.issue .location,.card .location').forEach(label => {
    let next = label.nextElementSibling;
    while (next?.matches('.location') && next.outerHTML === label.outerHTML) {
      const duplicate = next;
      next = duplicate.nextElementSibling;
      duplicate.remove();
    }
  });
  deduplicate();
  new MutationObserver(deduplicate).observe(root, {childList:true, subtree:true});
})();

/* Weekly narrative navigation: presentation only, with native content ownership. */
(() => {
  'use strict';
  function enhanceWeekly() {
    if (document.body.dataset.qdProject !== 'news') return;
    const narrative = document.querySelector('.weekly-narrative');
    if (!narrative || narrative.dataset.nw4Reader || narrative.dataset.weeklyReading) return;
    const stories = [...narrative.querySelectorAll('.narrative-story')].filter(story =>
      /^[A-Za-z0-9_-]+$/.test(story.id) && story.querySelector('h3'));
    const nativeNav = narrative.querySelector('.narrative-contents');
    if (!stories.length || !nativeNav) return;

    const aside = document.createElement('aside');
    aside.className = 'nw4-weekly-outline';
    aside.setAttribute('aria-label', '주간 이야기 탐색');
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = '이번 주 이야기';
    const count = document.createElement('span');
    count.className = 'nw4-outline-count';
    count.textContent = String(stories.length);
    summary.append(count);
    details.append(summary);
    const list = document.createElement('ol');
    const targets = [];
    const links = [];
    function linkTo(target, text, className) {
      const a = document.createElement('a');
      a.href = '#' + target.id;
      a.className = className;
      a.textContent = text;
      a.addEventListener('click', event => {
        const original = [...nativeNav.querySelectorAll('a')].find(link => link.hash === a.hash);
        if (original) {
          event.preventDefault();
          const reading = target.closest('.weekly-reading-details')
            || target.querySelector('.weekly-reading-details');
          if (reading && !reading.open) reading.querySelector('summary')?.click();
          original.click(); // Native archive/search/hash handlers remain authoritative.
        } else {
          const previous = target.getAttribute('tabindex');
          target.setAttribute('tabindex', '-1');
          target.focus({preventScroll: true});
          target.scrollIntoView({block: 'start', behavior: 'instant'});
          current();
          target.addEventListener('blur', () => previous === null
            ? target.removeAttribute('tabindex') : target.setAttribute('tabindex', previous), {once: true});
        }
        // Keep an explicit mobile disclosure usable while reading. Its state
        // is not saved and never changes the source article's reader state.
      });
      links.push(a);
      targets.push(target);
      return a;
    }
    stories.forEach(story => {
      const item = document.createElement('li');
      const heading = story.querySelector('h3').cloneNode(true);
      heading.querySelectorAll('.narrative-story-number').forEach(node => node.remove());
      const a = linkTo(story, heading.textContent.trim(), 'nw4-story-link');
      item.append(a);
      list.append(item);
    });
    details.append(list);
    const sections = document.createElement('nav');
    sections.className = 'nw4-outline-sections';
    sections.setAttribute('aria-label', '주간 브리핑 구간');
    [...nativeNav.querySelectorAll('a')].forEach(original => {
      if (!original.hash || original.hash === '#weekly-key-stories') return;
      const target = document.getElementById(original.hash.slice(1));
      if (target) sections.append(linkTo(target, original.textContent.trim(), 'nw4-section-link'));
    });
    details.append(sections);
    aside.append(details);
    narrative.prepend(aside);
    narrative.classList.add('nw4-weekly');
    narrative.dataset.nw4Reader = '1';

    const desktop = matchMedia('(min-width: 1180px)');
    const adapt = () => { details.open = desktop.matches; };
    adapt();
    if (desktop.addEventListener) desktop.addEventListener('change', adapt);
    let queued = false;
    const current = () => {
      queued = false;
      const rootStyle = getComputedStyle(document.documentElement);
      const offset = Math.max((parseFloat(rootStyle
        .getPropertyValue('--qd-header-height')) || 64) + 40,
      (parseFloat(rootStyle.scrollPaddingTop) || 0) + 24);
      // Heading elements inside a section have the same logical position as
      // their containing story/section. No URL or stored reading state changes.
      const positions = targets.map((target, index) => ({target, index,
        top: target.getBoundingClientRect().top})).filter(row => row.target.getClientRects().length);
      const past = positions.filter(row => row.top <= offset).sort((a, b) => b.top - a.top);
      const chosen = past[0] || positions.sort((a, b) => a.top - b.top)[0];
      links.forEach((link, index) => index === chosen?.index
        ? link.setAttribute('aria-current', 'location') : link.removeAttribute('aria-current'));
    };
    const queue = () => {if (!queued) {queued = true; requestAnimationFrame(current);}};
    window.addEventListener('scroll', queue, {passive: true});
    window.addEventListener('resize', queue, {passive: true});
    window.addEventListener('hashchange', queue);
    current();
  }
  if (window.__quantDesignV4?.state === 'ready') enhanceWeekly();
  else window.addEventListener('quant-design-ready', enhanceWeekly, {once: true});
})();
