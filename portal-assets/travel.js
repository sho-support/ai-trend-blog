(()=>{
'use strict';
const root=document.getElementById('event-stays'),status=document.getElementById('stay-status');
const C=window.PortalCommerce;
if(!root||!status||!C)return;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let feed=[];
const write=()=>{
 const selected=document.getElementById('pref')?.value||'すべて';
 const region=document.getElementById('region')?.value||'すべて';
 const allowed=Array.from(document.getElementById('pref')?.options||[]).map(x=>x.value);
 const all=feed.filter(x=>C.isFresh(x)&&(selected!=='すべて'?x.prefecture===selected:region==='すべて'||allowed.includes(x.prefecture)));
 const visible=selected==='すべて' ? all.filter((x,i)=>all.findIndex(y=>y.city===x.city)===i).slice(0,9):all.slice(0,9);
 if(!visible.length){
  status.textContent=selected==='すべて'?'現在は宿泊施設の紹介データを取得できていません。':'この地域の宿泊施設情報は未取得です。';
  root.innerHTML='';
  return;
 }
 status.textContent='楽天トラベルの宿泊施設情報 '+visible.length+'件｜宿泊日・空室・料金は未確認';
 root.innerHTML=visible.map(x=>'<article class="tile" style="min-height:195px">'
  +'<div class="tile-top"><div class="emblem" aria-hidden="true">🛏️</div><span class="badge">PR</span></div>'
  +'<div class="tile-body"><div class="tile-tags"><span class="tag highlight">エリア検索：'+esc(x.city)+'</span></div>'
  +'<h3>'+esc(x.name)+'</h3><p>'+(x.address?'所在地：'+esc(x.address)+'。':'')+'検索エリアの宿泊候補です。会場までの距離や当日の空室は要確認。</p></div>'
  +'<div class="tile-foot"><small>PR｜楽天トラベル</small><a class="go" href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer sponsored" data-item-id="'+esc(x.id)+'" data-travel-link>宿泊プランを確認 ↗</a></div></article>').join('');
};
fetch('../portal-assets/travel-feed.json',{cache:'no-store'})
 .then(r=>{if(!r.ok)throw Error('hotel feed unavailable');return r.json()})
 .then(d=>{
  if(!Array.isArray(d.items))throw Error('hotel feed invalid');
  feed=d.items.filter(x=>x&&x.affiliate===true&&x.name&&x.city&&x.prefecture
    &&C.isRakutenURL(x.url)&&C.isFresh(x));
  write();
 }).catch(()=>{status.textContent='現在、宿泊施設情報を取得できません。';root.innerHTML='';});
document.addEventListener('change',e=>{
 if(e.target && (e.target.id==='pref'||e.target.id==='region'))write();
});
C.observe(write);
root.addEventListener('click',e=>{
 const link=e.target.closest('a[data-travel-link]');
 if(!link)return;
 const hotel=feed.find(x=>x.url===link.href);
 if(!C.isFresh(hotel)){e.preventDefault();write();return}
 C.track(link,{portal_kind:'travel',category:hotel.prefecture});
});
})();
