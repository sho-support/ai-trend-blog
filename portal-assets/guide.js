(()=>{
'use strict';
const category=window.GUIDE_CATEGORY;
const grid=document.getElementById('guide-cards');
const status=document.getElementById('guide-status');
if(!grid||!status||!category)return;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const empty=()=>{status.textContent='現在掲載できる商品情報はありません。時間をおいて再確認してください。';grid.innerHTML='';};
fetch('../portal-assets/rakuten-feed.json',{cache:'no-store'})
.then(r=>{if(!r.ok)throw Error('fetch status '+r.status);return r.json()})
.then(d=>{
 if(!Array.isArray(d.items))throw Error('missing product feed');
 const now=Date.now();
 const matches=d.items.filter(x=>{
  if(!x||x.category!==category||x.approved!==true||x.affiliate!==true)return false;
  if(!x.expires_at||!Number.isFinite(Date.parse(x.expires_at))||Date.parse(x.expires_at)<=now)return false;
  if(!/^https:\/\/[a-z0-9.-]+\/\S*$/i.test(x.url||''))return false;
  return !!(x.title&&x.description&&x.id);
 }).slice(0,9);
 if(!matches.length)return empty();
 const when=d.updated_at ? new Date(d.updated_at).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}) : '不明';
 status.textContent='楽天市場API取得商品 '+matches.length+'件 ・ 取得 '+when+' （JST）・PRを含む';
 grid.innerHTML=matches.map(x=>{
  const image=typeof x.image==='string'&&/^https:\/\//i.test(x.image)?'<img class="product-pic" loading="lazy" decoding="async" src="'+esc(x.image)+'" alt="'+esc(x.title)+'">':esc(x.icon||'📦');
  const money=Number.isFinite(x.price_yen)?'参考価格 '+Number(x.price_yen).toLocaleString('ja-JP')+'円':'取得時の参考価格は商品説明を参照';
  const seller=x.seller||'楽天市場出店ショップ';
  return '<article class="tile">'
    +'<div class="tile-top"><div class="emblem" aria-hidden="true">'+image+'</div></div>'
    +'<div class="tile-body"><div class="tile-tags"><span class="tag highlight">PR｜楽天市場</span><span class="tag">'+esc(seller)+'</span></div>'
    +'<h3>'+esc(x.title)+'</h3><p>'+esc(money)+'</p><p>価格・在庫・送料は購入先で要確認。最安値とは限りません。</p></div>'
    +'<div class="tile-foot"><small>価格確認 '+esc(when)+' ／PR</small><a class="go" target="_blank" rel="noopener noreferrer sponsored" data-rakuten-link="1" href="'+esc(x.url)+'">楽天市場で確認 ↗</a></div></article>';
 }).join('');
}).catch(()=>empty());
grid.addEventListener('click',e=>{
 const link=e.target.closest('a[data-rakuten-link]');
 if(!link||typeof window.gtag!=='function')return;
 try{window.gtag('event','portal_outbound_click',{portal_kind:'product_guide',category:category,destination_host:new URL(link.href).hostname})}catch(err){}
});
})();