(() => {
  'use strict';
  const C=window.PortalCommerce, config=window.CATALOG_CONFIG;
  if(!C||!config)return;
  const categories=window.CATALOG_CATEGORIES||[];
  const assetBase=new URL('.',document.currentScript.src);
  const productBase=new URL('../products/',assetBase);
  const esc=C.escape;
  const query=config.mode==='search'?new URLSearchParams(location.search).get('q')?.trim()||'':'';
  const searchKey=value=>String(value??'').normalize('NFKC').toLowerCase().replace(/[\s\p{Dash_Punctuation}×・]+/gu,'');
  const words=query.normalize('NFKC').split(/[\s・]+/).map(searchKey).filter(Boolean);
  const queryKinds=new Set(categories.filter(c=>query&&searchKey(c.name)===searchKey(query)).map(c=>c.key));
  const queryInput=document.getElementById('product-query');
  if(config.mode==='search'&&queryInput)queryInput.value=query;
  let feed=[],copies={},lastSignature='',failed=false,completeFeed=false;
  const viewedItems=new Set();
  const activeCategory=document.querySelector('.category-nav a[aria-current]');
  if(activeCategory){
    const nav=activeCategory.parentElement;
    nav.scrollLeft=activeCategory.getBoundingClientRect().left-nav.getBoundingClientRect().left-(nav.clientWidth-activeCategory.clientWidth)/2;
  }
  const get=url=>fetch(new URL(url,assetBase),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('unavailable');return r.json()});
  const getItems=file=>get(file).then(data=>{
    if(!Array.isArray(data?.items))throw Error('invalid product feed');
    return data.items;
  });
  const copyFor=x=>{
    if(copies[x.id])return copies[x.id];
    const title=String(x.title||x.display_title||'商品')
      .replace(/【[^】]*(?:】|$)/g,' ').replace(/＼[^／]*／|★[^★]*★/g,' ')
      .split(/[|｜]/)[0].replace(/\s+/g,' ').trim();
    return {name:title.length>32?title.slice(0,32).trimEnd()+'…':title,description:''};
  };
  const live=x=>x?.source==='a8'?C.isA8Live(x):C.isLive(x);
  const inCategory=(x,key)=>x.kind===key;
  const priceText=(item,copy)=>{
    const amount=Number(item.price_yen).toLocaleString('ja-JP');
    return copy.price_from===true?amount+'円〜':'¥'+amount;
  };
  function image(x,priority=false,large=false){
    if(!x.image||!/^https:\/\//.test(x.image))return '<span class="photo-unavailable">商品写真は販売店で</span>';
    let srcset='';
    try{
      const larger=new URL(x.image);
      if(larger.hostname==='thumbnail.image.rakuten.co.jp'&&larger.searchParams.has('_ex')){
        larger.searchParams.set('_ex','600x600');
        srcset=' srcset="'+esc(x.image)+' 128w, '+esc(larger.href)+' 600w" sizes="'+(large?'(max-width:600px) 90vw, 460px':'(max-width:600px) 45vw, 300px')+'"';
      }
    }catch(_){}
    return '<img class="product-image" src="'+esc(x.image)+'"'+srcset+' alt="'+esc(copyFor(x).name)+'" width="600" height="600" decoding="async"'+(priority?' fetchpriority="high"':' loading="lazy"')+'>';
  }
  const detailURL=x=>new URL('items/'+encodeURIComponent(x.id)+'.html',productBase).href;
  function rating(x){
    return x.source==='rakuten'&&typeof x.review_average==='number'&&x.review_average>0&&x.review_average<=5&&Number.isInteger(x.review_count)&&x.review_count>0
      ?'<p class="review-summary"><span aria-hidden="true">★</span> '+x.review_average.toFixed(2)+' <small>/ 5・楽天市場 '+x.review_count.toLocaleString('ja-JP')+'件</small></p><p class="review-date">'+esc(x.rating_verified||x.verified||'')+'取得・販売ページ全体の評価</p>':'';
  }
  function cardNotes(copy){return (copy.card_reason?'<p class="card-reason"><span>選ぶ理由</span>'+esc(copy.card_reason)+'</p>':'')+(copy.card_caution?'<p class="card-caution"><span>確認したい点</span>'+esc(copy.card_caution)+'</p>':'');}
  function productCards(items){
    return items.map((x,index)=>{
      const copy=copyFor(x),url=detailURL(x);
      return '<article class="product-card" data-kind="'+esc(x.kind)+'">'
        +'<a class="product-photo" href="'+esc(url)+'">'+image(x,index===0)+'</a>'
        +'<div class="product-card-body"><h2><a href="'+esc(url)+'">'+esc(copy.name)+'</a></h2>'
        +(copy.description?'<p class="product-intro">'+esc(copy.description)+'</p>':'')
        +rating(x)+cardNotes(copy)+'<a class="guide-link" href="'+esc(url)+'">特徴・購入前の確認点を読む →</a>'
        +'<div class="product-card-bottom">'+(x.price_yen!=null?'<p class="product-price">'+priceText(x,copy)+'</p>':'')
        +'<a class="product-open product-buy" href="'+esc(x.url)+'" data-buy="'+esc(x.id)+'" target="_blank" rel="noopener noreferrer sponsored" aria-label="'+esc(copy.name)+'を'+(x.source==='a8'?'公式ショップ':'楽天市場')+'で見る">'+(x.source==='a8'?'公式ショップで見る':'楽天市場で見る')+' <span aria-hidden="true">↗</span></a></div></div></article>';
    }).join('');
  }
  function trackView(item,copy){
    if(viewedItems.has(item.id)||typeof window.gtag!=='function')return;
    try{
      const data={item_id:item.id,item_name:copy.name,item_category:item.kind,affiliation:item.seller||item.shop||'楽天市場'};
      if(Number.isFinite(item.price_yen))data.price=item.price_yen;
      window.gtag('event','view_item',{portal_kind:'product',item_id:item.id,category:item.kind,source:item.source||'rakuten',currency:'JPY',items:[data]});
      viewedItems.add(item.id);
    }catch(_){ /* Measurement must not affect the shop link. */ }
  }
  function render(){
    const rows=feed.filter(live);
    const signature=JSON.stringify([rows,copies,failed,completeFeed]);
    if(signature===lastSignature)return;lastSignature=signature;
    if(config.mode==='directory'){
      document.querySelectorAll('[data-category],[data-department]').forEach((tile,index)=>{
        const selected=rows.filter(x=>tile.dataset.department?x.department===tile.dataset.department:inCategory(x,tile.dataset.category));
        tile.hidden=!selected.length;
        const item=selected.find(x=>x.image);
        const photo=tile.querySelector('.category-photo');
        if(photo)photo.innerHTML=item?image(item,index===0):'<span class="photo-unavailable">'+esc(tile.querySelector('h2').textContent)+'</span>';
      });
      const curated=document.getElementById('editorial-picks-grid');
      if(curated){
        const ids=['rakuten-lifedrinkcompany-10000022','rakuten-yokumoku-10000435','rakuten-anker-10001908'];
        const chosen=rows.filter(x=>ids.includes(x.id));
        curated.innerHTML=productCards(chosen);
        const shelf=document.querySelector('.editorial-picks');if(shelf)shelf.hidden=!chosen.length;
      }
      const status=document.getElementById('directory-status');
      if(status)status.textContent=rows.length?'':failed?'商品を読み込めませんでした。':'現在掲載できる商品はありません。';
      return;
    }
    if(config.mode==='category'||config.mode==='search'){
      const grid=document.getElementById('catalog-grid'),status=document.getElementById('catalog-status');
      if(config.mode==='search'&&!completeFeed&&!failed)return;
      const selected=config.mode==='search'?rows.filter(x=>{
        if(queryKinds.size)return queryKinds.has(x.kind);
        const genre=categories.find(c=>c.key===x.kind)?.name;
        const keys=[x.title,copyFor(x).name,x.category,genre,x.seller||x.shop].map(searchKey);
        return words.length>0&&words.every(word=>keys.some(key=>key.includes(word)));
      }):rows.filter(x=>inCategory(x,config.kind));
      document.querySelectorAll('.category-nav a').forEach(link=>{
        if(!completeFeed)return;
        const c=categories.find(c=>link.getAttribute('href')===c.file);
        if(c)link.hidden=!rows.some(x=>inCategory(x,c.key))&&c.key!==config.kind;
      });
      if(!selected.length){
        grid.innerHTML='';
        status.textContent=failed?'商品を読み込めませんでした。しばらくしてからお試しください。':
          config.mode==='search'?(words.length?'条件に合う商品はありません。':'商品名やジャンルを入力してください。'):'現在掲載できる商品はありません。';
        status.hidden=false;return;
      }
      status.textContent='';status.hidden=true;
      grid.innerHTML=productCards(selected);
      return;
    }
    if(config.mode==='product'){
      const root=document.getElementById('product-detail');
      const item=rows.find(x=>x.id===config.id&&inCategory(x,config.kind));
      if(!item){
        const related=rows.filter(x=>inCategory(x,config.kind)).slice(0,3);
        const categoryURL=new URL(categories.find(c=>c.key===config.kind)?.file||'./',productBase);
        root.innerHTML='<div class="unavailable-product"><h1>現在、この商品の掲載はありません</h1>'
          +(related.length?'<p>同じジャンルの商品 <span class="ad-label">PR</span></p><div class="product-grid">'+productCards(related)+'</div>':'')
          +'<p><a class="buy-button secondary" href="'+esc(categoryURL.href)+'">商品一覧へ</a></p></div>';
        return;
      }
      const copy=copyFor(item);
      root.innerHTML='<div class="detail-photo">'+image(item,true,true)+'</div><div class="detail-info"><span class="ad-label">PR</span>'
        +'<h1>'+esc(copy.headline||copy.name)+'</h1>'
        +(copy.description?'<p class="detail-intro">'+esc(copy.description)+'</p>':'')
        +(item.price_yen!=null?'<p class="detail-price">'+priceText(item,copy)+'</p>':'')
        +'<a class="buy-button" href="'+esc(item.url)+'" data-buy="'+esc(item.id)+'" target="_blank" rel="noopener noreferrer sponsored">'+esc(item.source==='a8'?'公式ショップで価格を見る':'楽天市場で見る')+' <span aria-hidden="true">↗</span></a>'
        +'<p class="seller">'+esc(item.seller||(item.source==='a8'?item.shop||'公式ショップ':'楽天市場'))+'</p>'
        +'</div>';
      trackView(item,copy);
    }
  }
  const initial=window.CATALOG_INITIAL;
  if(initial&&Array.isArray(initial.items)){
    feed=initial.items;copies=initial.copies||{};render();
  }
  Promise.allSettled([getItems('rakuten-feed.json'),getItems('a8-approved.json'),get('product-copy.json')])
    .then(([rakuten,a8,copy])=>{
      const rakutenItems=rakuten.status==='fulfilled'?rakuten.value:feed.filter(x=>x?.source!=='a8');
      // The current approval list must load before retaining any A8 offers.
      const a8Items=a8.status==='fulfilled'?a8.value.map(x=>({...x,source:'a8'})):[];
      feed=[...rakutenItems,...a8Items];
      if(copy.status==='fulfilled'&&copy.value&&typeof copy.value==='object')copies={...copies,...copy.value};
      failed=rakuten.status==='rejected'||a8.status==='rejected';
      completeFeed=!failed;
      render();
    });
  C.observe(render);
  document.addEventListener('click',event=>{
    const link=event.target.closest('a[data-buy]');if(!link)return;
    const item=feed.find(x=>x.id===link.dataset.buy);
    if(!live(item)){event.preventDefault();render();return;}
    link.dataset.itemId=item.id;
    const placement=config.mode==='product'?(item.id===config.id?'detail':'related'):'list';
    C.track(link,{portal_kind:'product',category:item.kind,source:item.source||'rakuten',placement});
  });
  document.addEventListener('error',event=>{
    if(event.target instanceof HTMLImageElement&&event.target.classList.contains('product-image')){
      event.target.classList.add('image-error');
      event.target.alt='商品写真は販売店でご確認ください';
    }
  },true);
})();
