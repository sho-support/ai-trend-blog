/* Shared product eligibility and shopping arithmetic. No credentials. */
((root) => {
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g,
    c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const isRakutenURL = value => {
    try {
      const u = new URL(value);
      return u.protocol === 'https:' && !u.username && !u.password
        && (u.hostname === 'rakuten.co.jp' || u.hostname.endsWith('.rakuten.co.jp'));
    } catch (_) { return false; }
  };
  const isFresh = (item, now = Date.now()) => !!item && typeof item.expires_at === 'string'
    && Number.isFinite(Date.parse(item.expires_at)) && Date.parse(item.expires_at) > now;
  const isLive = (item, now = Date.now()) => isFresh(item, now)
    && item.approved === true && item.affiliate === true
    && Number.isFinite(item.price_yen) && item.price_yen > 0
    && !!item.id && !!item.title && isRakutenURL(item.url);
  const isA8Live = (item, now = Date.now()) => {
    if (!isFresh(item, now) || item.approved !== true || item.affiliate !== true
      || item.site_registered !== true || item.material_type !== 'free_link'
      || !item.id || !item.title || !item.kind) return false;
    try {
      const u = new URL(item.url), site = new URL(item.site_url);
      return u.protocol === 'https:' && !u.username && !u.password
        && ['px.a8.net','rpx.a8.net','ad.a8.net'].includes(u.hostname)
        && site.origin === 'https://sho-support.github.io'
        && (site.pathname === '/ai-trend-blog' || site.pathname.startsWith('/ai-trend-blog/'))
        && (!item.image || item.image_authorized === true)
        && (item.price_yen == null || Number.isFinite(item.price_yen) && item.price_yen > 0);
    } catch (_) { return false; }
  };
  const kinds = {
    'power-bank': /モバイルバッテリー|Power Bank/i,
    monitor: /モニター|液晶ディスプレイ|PCディスプレイ|有機ELディスプレイ/,
    'laundry-detergent': /洗濯|衣料用|アタック|アリエール|ナノックス|NANOX|ランドリー/i,
    'pet-wipes': /ウェット|ウエット/,
  };
  const matches = (item, config) => {
    if (!item || !config || item.category !== config.category) return false;
    if (!Array.isArray(config.kinds) || !config.kinds.length) return true;
    return config.kinds.some(kind => {
      const title = item.title || '';
      if (kind === 'monitor' && /モバイルバッテリー|Power Bank|モニターアーム|保護フィルム|保護カバー|スタンドのみ/i.test(title)) return false;
      if (kind === 'laundry-detergent' && /食器|台所|柔軟剤|ジェルボール|パーフェクトスティック|洗剤シート/.test(title)) return false;
      return item.kind ? item.kind === kind : !!kinds[kind] && kinds[kind].test(title);
    });
  };
  const unitCost = ({price, shipping, coupon, quantity, dose}) => {
    if (![price, shipping, coupon, quantity].every(Number.isFinite)
      || price < 0 || shipping < 0 || coupon < 0 || quantity <= 0
      || coupon > price + shipping) return null;
    if (dose !== undefined && (!Number.isFinite(dose) || dose <= 0)) return null;
    const total = price + shipping - coupon;
    return {total, unit: total / quantity, perUse: dose === undefined ? null : total / quantity * dose};
  };
  const eventWindow = (kind, today) => {
    const base = new Date(today + 'T00:00:00Z'), day = base.getUTCDay();
    const iso = d => d.toISOString().slice(0, 10);
    const later = days => new Date(base.getTime() + days * 86400000);
    if (kind === 'weekend') {
      // On Sunday, this weekend still includes today; do not jump a week ahead.
      if (day === 0) return {low: today, high: today};
      const until = (6 - day + 7) % 7;
      return {low: iso(later(until)), high: iso(later(until + 1))};
    }
    if (kind === 'next7') return {low: today, high: iso(later(6))};
    const year = base.getUTCFullYear(), month = base.getUTCMonth();
    if (kind === 'month') return {low: today, high: iso(new Date(Date.UTC(year, month + 1, 0)))};
    if (kind === 'nextmonth') return {low: iso(new Date(Date.UTC(year, month + 1, 1))), high: iso(new Date(Date.UTC(year, month + 2, 0)))};
    return null;
  };
  const observe = callback => {
    // A tab can remain open past a feed's expiry. Revalidate on return and at
    // least once per minute instead of retaining yesterday's price indefinitely.
    const timer = setInterval(callback, 60000);
    root.addEventListener('focus', callback);
    root.document.addEventListener('visibilitychange', () => {
      if (!root.document.hidden) callback();
    });
    return () => clearInterval(timer);
  };
  const track = (link, details) => {
    if (typeof root.gtag !== 'function') return;
    try {
      const u = new URL(link.href, root.location.href);
      root.gtag('event', 'portal_outbound_click', {
        ...details, destination_host: u.hostname,
        // Send identifiers, never the full referral URL, search text or form input.
        item_id: link.dataset.itemId || '',
        guide_slug: root.location.pathname.split('/').pop().replace(/\.html$/, ''),
        transport_type: 'beacon',
      });
    } catch (_) { /* Analytics must not prevent navigation. */ }
  };
  const api = Object.freeze({escape, isRakutenURL, isFresh, isLive, isA8Live, matches, unitCost, eventWindow, observe, track});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PortalCommerce = api;
})(typeof window !== 'undefined' ? window : globalThis);
