/* Keep price news and merchant links current even in a tab left open overnight. */
((root)=>{
 'use strict';
 const C=typeof module!=='undefined'&&module.exports?require('./commerce.js'):root.PortalCommerce;
 function selectedDeals(feed,history,copies,now=Date.now()){
  const rows=[];
  for(const item of feed.items||[]){
   if(item.source!=='rakuten'||!C.isLive(item,now)||!/^\d{4}-\d{2}-\d{2}$/.test(item.verified||''))continue;
   const day=item.verified,stamp=Date.parse(day+'T00:00:00Z');if(!Number.isFinite(stamp)||new Date(stamp).toISOString().slice(0,10)!==day)continue;
   const low=new Date(stamp-30*86400000).toISOString().slice(0,10);
   const records=(history.items?.[item.id]||[]).filter(x=>typeof x.date==='string'&&x.date>=low&&x.date<day&&typeof x.price==='number'&&Number.isFinite(x.price)&&x.price>0);
   if(new Set(records.map(x=>x.date)).size<3)continue;
   const previous=Math.min(...records.map(x=>x.price)),deal=item.verified_deal||{};
   if(item.price_yen>=previous||deal.previous_observed_low_yen!==previous||deal.current_yen!==item.price_yen)continue;
   rows.push({...item,news_copy:copies[item.id]||{name:item.display_title||item.title.slice(0,32),description:''},previous_price:previous,
    previous_date:records.filter(x=>x.price===previous).map(x=>x.date).sort().pop()});
  }
  return rows.sort((a,b)=>(a.price_yen/a.previous_price-b.price_yen/b.previous_price)||a.id.localeCompare(b.id)).slice(0,12);
 }
 if(typeof module!=='undefined'&&module.exports){module.exports={selectedDeals};return;}
 const grid=document.getElementById('deal-news-grid'),filter=document.getElementById('deal-category'),status=document.getElementById('deal-news-status');
 if(!C||!grid||!filter||!status)return;
 const esc=C.escape,yen=n=>Number(n).toLocaleString('ja-JP');
 let rows=root.DEAL_NEWS_INITIAL||[],updatedAt=root.DEAL_NEWS_UPDATED_AT,markup='';
 const photo=url=>{try{const u=new URL(url);if(u.hostname==='thumbnail.image.rakuten.co.jp')u.searchParams.set('_ex','600x600');return esc(u.href)}catch{return ''}};
 function render(){
  const active=rows.filter(x=>C.isLive(x)),categories=[...new Set(active.map(x=>x.category))],value=filter.value;
  const options='<option value="all">すべてのジャンル</option>'+categories.map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join('');
  if(filter.innerHTML!==options){filter.innerHTML=options;filter.value=categories.includes(value)?value:'all';}
  const selected=active.filter(x=>filter.value==='all'||x.category===filter.value);
  const stamp=Date.parse(updatedAt),checked=Number.isFinite(stamp)?new Intl.DateTimeFormat('ja-JP',{timeZone:'Asia/Tokyo',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(stamp)):'';
  status.textContent=selected.length+'件'+(checked?' · '+checked+'確認':'');
  const next=selected.map(x=>{
   const copy=x.news_copy,attrs=' href="'+esc(x.url)+'" data-deal-buy="'+esc(x.id)+'" target="_blank" rel="noopener noreferrer sponsored"';
   return '<article class="deal-news-card"><a class="deal-news-photo"'+attrs+'>'+(x.image?'<img src="'+photo(x.image)+'" alt="'+esc(copy.name)+'" width="600" height="600" loading="lazy" decoding="async">':'<span>商品写真は販売店で</span>')+'</a><div class="deal-news-body"><span class="ad-label">PR · 楽天市場</span><h2><a'+attrs+'>'+esc(copy.name)+'、<span class="price-token">'+yen(x.price_yen)+'円〜</span></a></h2><p class="deal-news-intro">'+esc(copy.description||'')+'</p><p class="deal-news-before">'+esc(x.previous_date.slice(5).replace('-','/'))+'記録：'+yen(x.previous_price)+'円</p><a class="buy-button"'+attrs+'>楽天市場で見る ↗</a></div></article>';
  }).join('')||'<p class="empty-results">現在、値下がりを確認できる商品はありません。</p>';
  if(next!==markup){grid.innerHTML=next;markup=next;}
 }
 filter.addEventListener('change',render);
 grid.addEventListener('click',e=>{
  const a=e.target.closest('[data-deal-buy]');if(!a)return;
  const item=rows.find(x=>x.id===a.dataset.dealBuy);
  if(!C.isLive(item)){e.preventDefault();render();return;}
  a.dataset.itemId=item.id;C.track(a,{portal_kind:'deals',category:item.category,placement:'deal_news'});
 });
 const base=new URL('.',document.currentScript.src);
 Promise.all(['rakuten-feed.json','price-history.json'].map(path=>fetch(new URL(path,base),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('feed');return r.json()})))
  .then(([feed,history])=>{rows=selectedDeals(feed,history,root.DEAL_NEWS_COPY||{});updatedAt=feed.updated_at;render()}).catch(()=>render());
 render();C.observe(render);
})(typeof window!=='undefined'?window:globalThis);
