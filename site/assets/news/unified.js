/* News owns loading; the shared foundation remains pinned and initializes once. */
(() => {
  'use strict';
  const state = window.__quantDesignUnified = {version:'0.5.0',foundation:'0.4.0',state:'loading',project:'news'};
  function ready() {
    const links = [...document.querySelectorAll('link[rel="stylesheet"]')].filter(link => link.href.includes('/assets/news/extensions/0.5.0/'));
    if (window.__quantNewsExtensionErrors?.length || links.length !== 2 || links.some(link => !link.sheet) || window.__quantDesignV4?.state !== 'ready') {
      state.state='failed';
      return;
    }
    document.documentElement.dataset.unifiedDesign='0.5.0';
    state.state='ready';
    dispatchEvent(new Event('quant-design-unified-ready'));
  }
  if (document.readyState === 'complete') ready();
  else addEventListener('load',ready,{once:true});
})();
