(() => {
  'use strict';
  const C=window.PortalCommerce,D=window.PORTAL_DATA||{};
  const filters=document.getElementById('listing-filters'),grid=document.getElementById('listing-grid'),count=document.getElementById('listing-count'),chips=document.getElementById('listing-chips');
  if(!C||!filters||!grid||!chips)return;
  const esc=C.escape,items=Array.isArray(D.items)?D.items:[];
  const prefs='北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県'.split(' ').filter((x,i,a)=>a.indexOf(x)===i);
  const regions={'北海道・東北':prefs.slice(0,7),'関東':prefs.slice(7,14),'中部':prefs.slice(14,23),'近畿':prefs.slice(23,30),'中国・四国':prefs.slice(30,39),'九州・沖縄':prefs.slice(39)};
  const state={term:'',category:'すべて',shop:'すべて',region:'すべて',pref:'すべて',when:'any'};
  const options=rows=>rows.map(v=>'<option value="'+esc(v)+'">'+esc(v==='すべて'?'すべて':v)+'</option>').join('');
  const today=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  const shortDate=t=>t?String(Number(t.slice(5,7)))+'/'+String(Number(t.slice(8,10))):'';
  const dates=x=>shortDate(x.start)+(x.end&&x.end!==x.start?' – '+shortDate(x.end):'');
  let hotels=[],lastMarkup='';
  filters.classList.toggle('events',D.kind==='events');
  filters.innerHTML='<input id="listing-query" type="search" placeholder="'+(D.kind==='events'?'イベント名で探す':'ショップ・キーワードで探す')+'" aria-label="キーワード検索">'+
   (D.kind==='events'?'<select id="region" aria-label="地方"><option value="すべて">全国</option>'+options(Object.keys(regions))+'</select><select id="pref" aria-label="都道府県"><option value="すべて">都道府県</option>'+options(prefs)+'</select><select id="when" aria-label="開催日"><option value="any">開催日</option><option value="weekend">今週末</option><option value="next7">7日以内</option><option value="month">今月</option><option value="nextmonth">来月</option></select>'
   :'<select id="listing-shop" aria-label="ショップ"><option value="すべて">すべてのショップ</option>'+options([...new Set(items.map(x=>x.shop).filter(Boolean))])+'</select>');
  const categories=['すべて',...new Set(items.map(x=>x.category).filter(Boolean))];
  chips.innerHTML=categories.map(x=>'<button type="button" class="filter-chip" data-category="'+esc(x)+'" aria-pressed="'+(x==='すべて')+'">'+esc(x)+'</button>').join('');
  function render(){
    const day=today();let rows=items.filter(x=>!x.end||x.end>=day);
    if(state.term)rows=rows.filter(x=>[x.title,x.shop,x.place,x.prefecture].join(' ').toLowerCase().includes(state.term));
    if(state.category!=='すべて')rows=rows.filter(x=>x.category===state.category);
    if(state.shop!=='すべて')rows=rows.filter(x=>x.shop===state.shop);
    if(D.kind==='events'){
      if(state.region!=='すべて')rows=rows.filter(x=>(regions[state.region]||[]).includes(x.prefecture));
      if(state.pref!=='すべて')rows=rows.filter(x=>x.prefecture===state.pref);
      if(state.when!=='any'){const {low,high}=C.eventWindow(state.when,day);rows=rows.filter(x=>x.start<=high&&x.end>=low);}
      rows.sort((a,b)=>a.start.localeCompare(b.start));
    }
    count.textContent=rows.length+'件';
    const markup=rows.length?rows.map(x=>D.kind==='events'?
      '<article class="event-card"><div class="event-date">'+esc(dates(x))+'</div><div><span class="event-category">'+esc(x.category)+'</span><h2><a href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer">'+esc(x.title)+'</a></h2><p class="event-place">'+esc([x.prefecture,x.place].filter(Boolean).join('・'))+'</p></div><a class="text-link" href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer">詳細 →</a></article>'
      :'<article class="offer-card"><span class="store-name">'+esc(x.shop||'')+'</span><h2><a href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer">'+esc(x.title)+'</a></h2><p class="offer-label">'+esc(x.label||'')+'</p>'+(x.start?'<p class="offer-dates">'+(x.start>day?'開催予定 · ':'')+esc(dates(x))+'</p>':'')+'<a class="text-link" href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer">公式サイトへ →</a></article>'
    ).join(''):'<p class="empty-results">条件に合う情報がありません。条件を変えてお探しください。</p>';
    if(markup!==lastMarkup){grid.innerHTML=markup;lastMarkup=markup;}
    renderStays();
  }
  function renderStays(){
    const root=document.getElementById('event-stays'),status=document.getElementById('stay-status');if(!root)return;
    const selected=hotels.filter(x=>C.isFresh(x)&&(state.pref!=='すべて'?x.prefecture===state.pref:state.region==='すべて'||(regions[state.region]||[]).includes(x.prefecture)));
    const rows=state.pref==='すべて'?selected.filter((x,i)=>selected.findIndex(y=>y.city===x.city)===i).slice(0,6):selected.slice(0,6);
    status.textContent=rows.length?'料金・空室は楽天トラベルで確認できます。':'この地域の宿泊候補は現在ありません。';
    const markup=rows.map(x=>'<article class="stay-card"><span class="event-category">'+esc(x.city)+'</span><h3>'+esc(x.name)+'</h3><a class="text-link" href="'+esc(x.url)+'" data-hotel="'+esc(x.id)+'" target="_blank" rel="noopener noreferrer sponsored">宿泊プランを見る ↗</a></article>').join('');
    if(root.innerHTML!==markup)root.innerHTML=markup;
  }
  document.getElementById('listing-query').addEventListener('input',e=>{state.term=e.target.value.trim().toLowerCase();render();});
  chips.addEventListener('click',e=>{const b=e.target.closest('[data-category]');if(!b)return;state.category=b.dataset.category;chips.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b?'true':'false'));render();});
  if(D.kind==='events'){
    document.getElementById('region').addEventListener('change',e=>{state.region=e.target.value;state.pref='すべて';document.getElementById('pref').innerHTML='<option value="すべて">都道府県</option>'+options(regions[state.region]||prefs);render();});
    document.getElementById('pref').addEventListener('change',e=>{state.pref=e.target.value;render();});
    document.getElementById('when').addEventListener('change',e=>{state.when=e.target.value;render();});
    const base=new URL('.',document.currentScript.src);
    fetch(new URL('travel-feed.json',base),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{hotels=Array.isArray(data.items)?data.items.filter(x=>x.affiliate&&x.name&&C.isFresh(x)&&C.isRakutenURL(x.url)):[];renderStays();}).catch(()=>renderStays());
  }else document.getElementById('listing-shop').addEventListener('change',e=>{state.shop=e.target.value;render();});
  document.addEventListener('click',e=>{
    const link=e.target.closest('a[data-hotel]');if(!link)return;
    const item=hotels.find(x=>x.id===link.dataset.hotel);if(!C.isFresh(item)){e.preventDefault();renderStays();return;}
    link.dataset.itemId=item.id;C.track(link,{portal_kind:'travel',category:item.prefecture});
  });
  render();C.observe(render);
})();
