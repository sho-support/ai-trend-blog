(()=>{
'use strict';
const root=document.getElementById('watch-items'),status=document.getElementById('watch-status');
const cat=document.getElementById('watch-category'),sort=document.getElementById('watch-sort');
const C=window.PortalCommerce;
if(!root||!status||!cat||!sort||!C)return;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const yen=v=>Number(v).toLocaleString('ja-JP');
let rows=[];
function render(){
 const current=cat.value;
 let list=rows.filter(x=>C.isLive(x)&&(current==='all'||x.category===current));
 if(sort.value==='cheap')list.sort((a,b)=>a.price_yen-b.price_yen);
 else if(sort.value==='expensive')list.sort((a,b)=>b.price_yen-a.price_yen);
 else list.sort((a,b)=>(b.verified_deal?.drop_percent||0)-(a.verified_deal?.drop_percent||0));
 const trueDrops=list.filter(x=>!!x.verified_deal).length;
 status.textContent='掲載可能 '+list.length+'件・当サイトで確認できた値下がり '+trueDrops+'件｜確認できない値下がりは表示しません。';
 if(!list.length){root.innerHTML='<div class="empty">該当する商品情報がありません。次回の自動更新後に確認してください。</div>';return}
 root.innerHTML=list.map(x=>{
  const tracked=x._tracked||0;
  const deal=x.verified_deal;
  const label=deal ? '当サイト観測価格 '+yen(deal.previous_observed_low_yen)+'円 → '+yen(x.price_yen)+'円（'+deal.drop_percent+'%低下）'
   :tracked<4 ? '価格を記録中｜比較には過去3日以上の記録が必要':'観測価格の値下がり判定なし';
  return '<article class="watch-card"><div><span class="tag highlight">'+esc(x.category)+'</span><h3>'+esc(x.display_title||x.title)+'</h3><p>'+esc(x.seller||'楽天市場出店ショップ')+'</p></div>'
  +'<div class="watch-num">'+yen(x.price_yen)+'円<small>API取得時の参考価格</small></div>'
  +'<div class="watch-bottom"><span class="watch-signal '+(deal?'verified':'')+'">'+esc(label)+'</span><a class="go" href="'+esc(x.url)+'" rel="noopener noreferrer sponsored" target="_blank" data-item-id="'+esc(x.id)+'" data-buy-link>楽天市場で確認 ↗</a></div></article>';
 }).join('');
}
Promise.all([
 fetch('../portal-assets/rakuten-feed.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('feed');return r.json()}),
 fetch('../portal-assets/price-history.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('history');return r.json()})
]).then(([feed,history])=>{
 if(!Array.isArray(feed.items)||!history.items||typeof history.items!=='object')throw Error('bad feed');
 rows=feed.items.filter(x=>C.isLive(x))
 .map(x=>({...x,_tracked:new Set((history.items[x.id]||[]).map(y=>y.date)).size}));
 const cats=[...new Set(rows.map(x=>x.category))];
 cat.innerHTML='<option value="all">すべてのジャンル</option>'+cats.map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');
 render();
}).catch(()=>{status.textContent='価格情報を取得できませんでした。';root.innerHTML='';});
cat.addEventListener('change',render);
sort.addEventListener('change',render);
C.observe(render);
root.addEventListener('click',e=>{
 const a=e.target.closest('a[data-buy-link]');if(!a)return;
 const item=rows.find(x=>x.id===a.dataset.itemId);
 if(!C.isLive(item)){e.preventDefault();render();return}
 C.track(a,{portal_kind:'price_watch',category:item.category});
});
})();
