(() => {
  'use strict';
  const C = window.PortalCommerce;
  const config = window.GUIDE_CONFIG || {category: window.GUIDE_CATEGORY};
  const grid = document.getElementById('guide-cards'), status = document.getElementById('guide-status');
  if (!C || !grid || !status || !config.category) return;
  const esc = C.escape;
  let items = [], updatedAt = '', unavailable = false, lastRender = '';
  const when = value => {
    const stamp = Date.parse(value);
    return Number.isFinite(stamp) ? new Date(stamp).toLocaleString('ja-JP', {
      timeZone:'Asia/Tokyo', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit',
    }) : '日時不明';
  };
  function render() {
    const matches = items.filter(x => C.isLive(x) && C.matches(x, config)).slice(0, 9);
    const signature = JSON.stringify([matches, updatedAt, unavailable]);
    if (signature === lastRender) return;
    lastRender = signature;
    if (!matches.length) {
      status.textContent = unavailable ? '商品情報を読み込めませんでした。選び方と比較計算は引き続き使えます。'
        : 'このテーマで現在表示できる商品はありません。古い価格や別の用途の商品は掲載していません。';
      grid.innerHTML = '<div class="empty">次回の更新をお待ちください。<a href="./">ほかの買い物ガイドを読む →</a></div>';
      return;
    }
    status.textContent = matches.length + '件の商品候補 · 情報確認 ' + when(updatedAt) + '（日本時間）· PRを含む';
    grid.innerHTML = matches.map(item => {
      const picture = typeof item.image === 'string' && /^https:\/\//i.test(item.image)
        ? '<img class="product-pic" loading="lazy" decoding="async" src="' + esc(item.image) + '" alt="' + esc(item.title) + '">'
        : esc(item.icon || '📦');
      return '<article class="tile"><div class="tile-top"><div class="emblem">' + picture + '</div></div>'
        + '<div class="tile-body"><div class="tile-tags"><span class="tag highlight">PR｜楽天市場</span></div>'
        + '<h3 title="' + esc(item.title) + '">' + esc(item.display_title || item.title) + '</h3>'
        + '<div class="product-price">' + Number(item.price_yen).toLocaleString('ja-JP') + '円<small>情報確認時の参考価格・送料は購入先で確認</small></div>'
        + '<p>' + esc(item.seller || '楽天市場出店ショップ') + '</p></div>'
        + '<div class="tile-foot"><small>PR｜規格・在庫は購入先で確認</small>'
        + '<a class="go" target="_blank" rel="noopener noreferrer sponsored" data-rakuten-link="1" data-item-id="' + esc(item.id) + '"'
        + ' href="' + esc(item.url) + '" aria-label="' + esc(item.title) + 'を楽天市場で見る（広告）">商品と送料を確認 ↗</a></div></article>';
    }).join('');
  }
  fetch('../portal-assets/rakuten-feed.json', {cache:'no-store'})
    .then(response => {if (!response.ok) throw Error('unavailable'); return response.json();})
    .then(data => {if (!Array.isArray(data.items)) throw Error('invalid'); items = data.items; updatedAt = data.updated_at; render();})
    .catch(() => {unavailable = true; render();});
  C.observe(render);
  grid.addEventListener('click', event => {
    const link = event.target.closest('a[data-rakuten-link]');
    if (!link) return;
    const item = items.find(x => x.id === link.dataset.itemId);
    if (!C.isLive(item)) {event.preventDefault(); render(); return;}
    C.track(link, {portal_kind:'product_guide', category:config.category});
  });
})();
