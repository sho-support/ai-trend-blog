/* API observations are not cash discounts. Hide expired prices and conditions. */
(()=>{
'use strict';
const C=window.PortalCommerce,root=document.getElementById('point-offers');if(!C||!root)return;
const esc=C.escape;
let rows=window.POINT_OFFERS_INITIAL||[],last='';
function render(){
 const active=rows.filter(x=>C.isLive(x)&&(!x.point_end||Date.parse(x.point_end)>Date.now()));
 const html=active.map(x=>'<article class="deal-news-card"><a class="deal-news-photo" href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer sponsored" data-point-buy="'+esc(x.id)+'"><img src="'+esc(x.image||'')+'" alt="'+esc(x.news_copy.name)+'" loading="lazy" width="600" height="600"></a><div class="deal-news-body"><span class="offer-pill">API取得時 '+esc(Number(x.point_rate))+'倍</span><span class="ad-label"> PR</span><h3>'+esc(x.news_copy.name)+'</h3><p class="point-price">'+Number(x.price_yen).toLocaleString('ja-JP')+'円〜</p><p class="small-text">'+esc(x.verified)+'取得。対象期間・会員条件・付与上限を購入先で確認。現金値引きではありません。</p><a class="buy-button" href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer sponsored" data-point-buy="'+esc(x.id)+'">対象条件を楽天市場で確認 ↗</a></div></article>').join('')||'<p class="empty-results">ポイント倍率付きの商品情報は現在更新待ちです。公式キャンペーンからも探せます。</p>';
 if(html!==last){root.innerHTML=html;last=html;}
}
root.addEventListener('click',e=>{const a=e.target.closest('[data-point-buy]');if(!a)return;const x=rows.find(x=>x.id===a.dataset.pointBuy);if(!C.isLive(x)||(x.point_end&&Date.parse(x.point_end)<=Date.now())){e.preventDefault();render();return;}a.dataset.itemId=x.id;C.track(a,{portal_kind:'deals',category:x.category,placement:'point_offer'});});
const base=new URL('.',document.currentScript.src);
fetch(new URL('rakuten-feed.json',base),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(feed=>{rows=(feed.items||[]).filter(x=>C.isLive(x)).flatMap(x=>{const match=(x.description||'').match(/API掲載ポイント倍率: ([0-9.]+)倍/);const rate=x.point_rate??(match?Number(match[1]):0);return rate>1?[{...x,point_rate:rate,news_copy:(window.DEAL_NEWS_COPY||{})[x.id]||{name:x.display_title||x.title}}]:[]}).sort((a,b)=>b.point_rate-a.point_rate||a.id.localeCompare(b.id)).slice(0,12);render();}).catch(()=>render());
render();C.observe(render);
})();
