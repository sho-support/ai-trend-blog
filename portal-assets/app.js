(()=>{
'use strict';
const DATA = window.PORTAL_DATA || {};
let ALL = Array.isArray(DATA.items) ? DATA.items.slice() : [];
const prefectures = ('北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県').split(' ');
const regionMap = {
 '北海道・東北':prefectures.slice(0,7),
 '関東':prefectures.slice(7,14),
 '中部':prefectures.slice(14,23),
 '近畿':prefectures.slice(23,30),
 '中国・四国':prefectures.slice(30,39),
 '九州・沖縄':prefectures.slice(39)
};
const s={category:'すべて',term:'',shop:'すべて',pref:'すべて',region:'すべて',when:'any',saved:false};
const esc = v => String(v??'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const today = new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const key='sho-portal-saved-'+DATA.kind;
let favorites;try{favorites=JSON.parse(localStorage.getItem(key)||'[]')}catch(e){favorites=[]}
const saved=new Set(favorites);
const node=id=>document.getElementById(id);
const uniq=arr=>[...new Set(arr.filter(Boolean))];
const option=(a)=>a.map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');
const isExpired=x=>(x.expires_at && Date.parse(x.expires_at)<=Date.now()) || (x.end && x.end<today);
const dateText=x=>x.start?(x.end&&x.end!==x.start?x.start+' 〜 '+x.end:x.start):'公式で確認';
function setup(){
 const filter=node('filters'),chipbox=node('chips');
 const cats=['すべて',...uniq(ALL.map(x=>x.category))];
 const shops=['すべて',...uniq(ALL.map(x=>x.shop))];
 let html='<input id="query" type="search" placeholder="キーワードで探す（ジャンル・名称）" aria-label="検索">';
 if(DATA.kind==='events'){
  html+='<select id="region" aria-label="地方">'+option(['すべて',...Object.keys(regionMap)])+'</select>';
  html+='<select id="pref" aria-label="都道府県">'+option(['すべて',...prefectures])+'</select>';
  html+='<select id="when" aria-label="開催時期"><option value="any">すべての開催日</option><option value="weekend">今週末</option><option value="next7">7日以内に開催</option><option value="month">今月開催</option><option value="nextmonth">来月開催</option></select>';
 }else{
  html+='<select id="shop" aria-label="ショップ">'+option(shops)+'</select>';
 }
 html+='<select id="savedOnly" aria-label="保存"><option value="all">すべて表示</option><option value="saved">保存済みだけ</option></select>';
 filter.innerHTML=html;
 node('query').addEventListener('input',e=>{s.term=e.target.value.trim().toLowerCase();render()});
 if(DATA.kind==='events'){
  node('region').addEventListener('change',e=>{
   s.region=e.target.value;s.pref='すべて';
   node('pref').innerHTML=option(['すべて',...(regionMap[s.region]||prefectures)]);
   render();
  });
  node('pref').addEventListener('change',e=>{s.pref=e.target.value;render()});
  node('when').addEventListener('change',e=>{s.when=e.target.value;render()});
 }else node('shop').addEventListener('change',e=>{s.shop=e.target.value;render()});
 node('savedOnly').addEventListener('change',e=>{s.saved=e.target.value==='saved';render()});
 chipbox.innerHTML=cats.map(c=>'<button type="button" class="chip '+(c==='すべて'?'on':'')+'" data-cat="'+esc(c)+'">'+esc(c)+'</button>').join('');
 chipbox.addEventListener('click',e=>{const b=e.target.closest('[data-cat]');if(!b)return;s.category=b.dataset.cat;chipbox.querySelectorAll('.chip').forEach(c=>c.classList.toggle('on',c.dataset.cat===s.category));render()});
 node('cards').addEventListener('click',e=>{
  const outbound=e.target.closest('a.go');
  if(outbound && typeof window.gtag === 'function'){
   try{
    window.gtag('event','portal_outbound_click',{
     portal_kind:DATA.kind,
     destination_host:new URL(outbound.href).hostname
    });
   }catch(err){}
  }
  const b=e.target.closest('[data-save]');if(!b)return;
  const id=b.dataset.save;
  saved.has(id)?saved.delete(id):saved.add(id);
  try{localStorage.setItem(key,JSON.stringify([...saved]))}catch(e){}
  render();
 });
 render();
}
function render(){
 let arr=ALL.filter(x=>!isExpired(x));
 if(s.category!=='すべて')arr=arr.filter(x=>x.category===s.category);
 if(s.shop!=='すべて')arr=arr.filter(x=>x.shop===s.shop);
 if(s.region!=='すべて')arr=arr.filter(x=>(regionMap[s.region]||[]).includes(x.prefecture));
 if(s.pref!=='すべて')arr=arr.filter(x=>x.prefecture===s.pref);
 if(DATA.kind==='events' && s.when!=='any'){
  const start=today;
  const jstDate=t=>new Date(t+'T00:00:00Z');
  const pad=n=>String(n).padStart(2,'0');
  const iso=t=>t.getUTCFullYear()+'-'+pad(t.getUTCMonth()+1)+'-'+pad(t.getUTCDate());
  const base=jstDate(start);
  let low=start,high=start;
  if(s.when==='next7'){
   high=iso(new Date(base.getTime()+6*86400000));
  }else if(s.when==='weekend'){
   const day=base.getUTCDay();
   let until=(6-day+7)%7;
   const sat=new Date(base.getTime()+until*86400000);
   const sun=new Date(sat.getTime()+86400000);
   low=iso(sat);high=iso(sun);
  }else if(s.when==='month'){
   low=start.slice(0,7)+'-01';
   const next=new Date(Date.UTC(base.getUTCFullYear(),base.getUTCMonth()+1,0));
   high=iso(next);
   low=low<start?start:low;
  }else if(s.when==='nextmonth'){
   const next=new Date(Date.UTC(base.getUTCFullYear(),base.getUTCMonth()+1,1));
   const end=new Date(Date.UTC(base.getUTCFullYear(),base.getUTCMonth()+2,0));
   low=iso(next);high=iso(end);
  }
  arr=arr.filter(x=>!!x.start && !!x.end && x.start<=high && x.end>=low);
 }
 if(s.saved)arr=arr.filter(x=>saved.has(x.id));
 if(s.term)arr=arr.filter(x=>[x.title,x.category,x.description,x.shop,x.prefecture,x.place].join(' ').toLowerCase().includes(s.term));
 arr.sort((a,b)=>(a.start||a.end||'').localeCompare(b.start||b.end||''));
 node('count').textContent=arr.length+'件の情報';
 const grid=node('cards');
 if(!arr.length){
  grid.innerHTML='<div class="empty">条件に合う掲載情報がありません。現在は確認済みの情報のみ掲載しています。'+(DATA.kind==='events'?'<p>全国のイベント情報は、<a href="https://www.japan47go.travel/ja/event" target="_blank" rel="noopener noreferrer" style="color:#326a89;text-decoration:underline">日本観光振興協会のイベントカレンダー</a>でも探せます。</p>':'対象ジャンルや店舗を変えて検索してください。')+'</div>';
  return;
 }
 grid.innerHTML=arr.map(x=>{
  const hasDate=DATA.kind==='events';
  const place=hasDate?[x.prefecture,x.place].filter(Boolean).join('・'):x.shop;
  const label=hasDate?dateText(x):(x.label||'公式情報を確認');
  const url=typeof x.url==='string'&&/^https:\/\//.test(x.url)?x.url:'#';
  const old=x.verified && x.verified < today;
  const isFuture=x.start && x.start>today;
  const displayLabel=isFuture && DATA.kind==='deals' ? '開催予定｜'+label : label;
  const stamp=hasDate?(x.start||'日程要確認'):('参照日 '+(x.verified||'記載なし'));
  const urlImage=typeof x.image==='string' && /^https:\/\//.test(x.image) ? x.image : '';
  const picture=urlImage ? '<img loading="lazy" decoding="async" class="product-pic" src="'+esc(urlImage)+'" alt="'+esc(x.title)+'">' : esc(x.icon||'✨');
  return '<article class="tile"><div class="tile-top"><div class="emblem" aria-hidden="true">'+picture+'</div><button class="save '+(saved.has(x.id)?'saved':'')+'" data-save="'+esc(x.id)+'" aria-label="保存">'+(saved.has(x.id)?'★':'☆')+'</button></div><div class="tile-body"><div class="tile-tags"><span class="tag highlight">'+esc(x.category)+'</span><span class="tag">'+esc(place)+'</span></div><h3>'+esc(x.title)+'</h3><p>'+esc(x.description)+'</p><span class="badge">'+esc(displayLabel)+'</span></div><div class="tile-foot"><small>'+esc(stamp)+(old&&!hasDate?'時点':'')+'</small><a class="go" href="'+esc(url)+'" target="_blank" rel="noopener noreferrer" aria-label="'+esc(x.title)+' 公式情報">公式情報を確認 ↗</a></div></article>';
 }).join('');
}
if(node('cards')){
 const urls=DATA.kind==='events'?[]:[
  '../portal-assets/rakuten-feed.json',
  ...(DATA.kind==='products'?['../portal-assets/a8-approved.json']:[])
 ];
 if(!urls.length){setup();}else{
  Promise.all(urls.map(url=>fetch(url,{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null))).then(feeds=>{
   const additions=[];
   for(let i=0;i<feeds.length;i++){
    const feed=feeds[i], type=urls[i].includes('a8-')?'a8':'rakuten';
    if(!Array.isArray(feed?.items))continue;
    for(const x of feed.items){
     if(!x || typeof x!=='object' || !/^https:\/\/\S+$/.test(x.url||''))continue;
     if(!x.id||!x.title||!x.category)continue;
     if(type==='a8'){
      // A8.netの承認済み「フリー素材」の正規広告URLのみ使用。
      if(x.approved!==true||x.material_type!=='free_link')continue;
      additions.push({...x,shop:x.shop||'A8.net提携店',icon:x.icon||'🎁',label:'PR｜提携確認済み'});
     }else if(x.approved===true){
      additions.push({...x,shop:x.shop||'楽天市場',icon:x.icon||'📦',label:x.label||'楽天公式API情報'});
     }
    }
   }
   ALL=[...additions,...ALL];
  }).finally(setup);
 }
}
})();