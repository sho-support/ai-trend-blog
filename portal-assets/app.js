(()=>{
'use strict';
const DATA = window.PORTAL_DATA || {};
const ALL = Array.isArray(DATA.items) ? DATA.items : [];
const prefectures = ('北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県').split(' ');
const regionMap = {
 '北海道・東北':prefectures.slice(0,7),
 '関東':prefectures.slice(7,14),
 '中部':prefectures.slice(14,23),
 '近畿':prefectures.slice(23,30),
 '中国・四国':prefectures.slice(30,39),
 '九州・沖縄':prefectures.slice(39)
};
const s={category:'すべて',term:'',shop:'すべて',pref:'すべて',region:'すべて',saved:false};
const esc = v => String(v??'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const today = new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const key='sho-portal-saved-'+DATA.kind;
let favorites;try{favorites=JSON.parse(localStorage.getItem(key)||'[]')}catch(e){favorites=[]}
const saved=new Set(favorites);
const node=id=>document.getElementById(id);
const uniq=arr=>[...new Set(arr.filter(Boolean))];
const option=(a)=>a.map(v=>'<option value="'+esc(v)+'">'+esc(v)+'</option>').join('');
const isExpired=x=>x.end && x.end < today;
const dateText=x=>x.start?(x.end&&x.end!==x.start?x.start+' 〜 '+x.end:x.start):'公式で確認';
const a8=DATA.kind==='products'?[]:[];
function setup(){
 const filter=node('filters'),chipbox=node('chips');
 const cats=['すべて',...uniq(ALL.map(x=>x.category))];
 const shops=['すべて',...uniq(ALL.map(x=>x.shop))];
 let html='<input id="query" type="search" placeholder="キーワードで探す（ジャンル・名称）" aria-label="検索">';
 if(DATA.kind==='events'){
  html+='<select id="region" aria-label="地方">'+option(['すべて',...Object.keys(regionMap)])+'</select>';
  html+='<select id="pref" aria-label="都道府県">'+option(['すべて',...prefectures])+'</select>';
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
 }else node('shop').addEventListener('change',e=>{s.shop=e.target.value;render()});
 node('savedOnly').addEventListener('change',e=>{s.saved=e.target.value==='saved';render()});
 chipbox.innerHTML=cats.map(c=>'<button type="button" class="chip '+(c==='すべて'?'on':'')+'" data-cat="'+esc(c)+'">'+esc(c)+'</button>').join('');
 chipbox.addEventListener('click',e=>{const b=e.target.closest('[data-cat]');if(!b)return;s.category=b.dataset.cat;chipbox.querySelectorAll('.chip').forEach(c=>c.classList.toggle('on',c.dataset.cat===s.category));render()});
 node('cards').addEventListener('click',e=>{
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
 if(s.saved)arr=arr.filter(x=>saved.has(x.id));
 if(s.term)arr=arr.filter(x=>[x.title,x.category,x.description,x.shop,x.prefecture,x.place].join(' ').toLowerCase().includes(s.term));
 arr.sort((a,b)=>(a.start||a.end||'').localeCompare(b.start||b.end||''));
 node('count').textContent=arr.length+'件の情報';
 const grid=node('cards');
 if(!arr.length){
  grid.innerHTML='<div class="empty">条件に合う掲載情報がありません。全国47都道府県から検索できますが、現段階では確認済みの情報のみ掲載しています。条件を変更するか、後日ご確認ください。</div>';
  return;
 }
 grid.innerHTML=arr.map(x=>{
  const hasDate=DATA.kind==='events';
  const place=hasDate?[x.prefecture,x.place].filter(Boolean).join('・'):x.shop;
  const label=hasDate?dateText(x):(x.label||'公式情報を確認');
  const url=typeof x.url==='string'&&/^https:\/\//.test(x.url)?x.url:'#';
  const old=x.verified && x.verified < today;
  const stamp=hasDate?(x.start||'日程要確認'):('参照日 '+(x.verified||'記載なし'));
  return '<article class="tile"><div class="tile-top"><div class="emblem" aria-hidden="true">'+esc(x.icon||'✨')+'</div><button class="save '+(saved.has(x.id)?'saved':'')+'" data-save="'+esc(x.id)+'" aria-label="保存">'+(saved.has(x.id)?'★':'☆')+'</button></div><div class="tile-body"><div class="tile-tags"><span class="tag highlight">'+esc(x.category)+'</span><span class="tag">'+esc(place)+'</span></div><h3>'+esc(x.title)+'</h3><p>'+esc(x.description)+'</p><span class="badge">'+esc(label)+'</span></div><div class="tile-foot"><small>'+esc(stamp)+(old&&!hasDate?'時点':'')+'</small><a class="go" href="'+esc(url)+'" target="_blank" rel="noopener noreferrer" aria-label="'+esc(x.title)+' 公式情報">公式情報を確認 ↗</a></div></article>';
 }).join('');
}
if(node('cards'))setup();
})();