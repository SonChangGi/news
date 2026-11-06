/* News owns loading; the shared foundation remains pinned and initializes once. */
(() => {
  'use strict';
  const state = window.__quantDesignUnified ||= {version:'0.7.0',foundation:'0.4.0',state:'loading',project:'news'};
  function ready() {
    clearTimeout(window.__quantNewsPaintTimer);
    const links = [...document.querySelectorAll('link[rel="stylesheet"]')].filter(link => /\/assets\/news\/extensions\/(?:0\.5\.0|0\.7\.0)\//.test(link.href));
    if (window.__quantNewsExtensionErrors?.length || links.length !== 6 || links.some(link => !link.sheet) || window.__quantDesignV4?.state !== 'ready' || window.QuantRange?.version !== '1.3.0' || window.QuantFormat?.version !== '1.0.0') {
      state.state='failed';
      document.documentElement.dataset.quantPaint='fallback';
      delete document.documentElement.dataset.quantSilicon;
      delete document.documentElement.dataset.unifiedDesign;
      return;
    }
    document.documentElement.dataset.unifiedDesign=state.version;
    document.documentElement.dataset.quantSilicon='true';
    state.state='ready';
    document.documentElement.dataset.quantPaint='ready';
    const footer = document.querySelector('.qd-side-footer small');
    if (footer) footer.textContent = 'Quant Research · v' + state.version;
    dispatchEvent(new Event('quant-design-unified-ready'));
  }
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded',ready,{once:true});
  else ready();
})();
