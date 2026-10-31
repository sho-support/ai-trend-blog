(() => {
  'use strict';
  const C=window.PortalCommerce, config=window.CATALOG_CONFIG;
  if(!C||!config)return;
  const categories=window.CATALOG_CATEGORIES||[];
  const assetBase=new URL('.',document.currentScript.src);
  const productBase=new URL('../products/',assetBase);
  const esc=C.escape;
  let feed=[],copies={},lastSignature='',failed=false;
  const activeCategory=document.querySelector('.category-nav a[aria-current]');
  if(activeCategory){
    const nav=activeCategory.parentElement;
    nav.scrollLeft=activeCategory.getBoundingClientRect().left-nav.getBoundingClientRect().left-(nav.clientWidth-activeCategory.clientWidth)/2;
  }
  const get=url=>fetch(new URL(url,assetBase),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('unavailable');return r.json()});
  const copyFor=x=>{
    if(copies[x.id])return copies[x.id];
    const title=String(x.title||x.display_title||'商品')
      .replace(/【[^】]*(?:】|$)/g,' ').replace(/＼[^／]*／|★[^★]*★/g,' ')
      .split(/[|｜]/)[0].replace(/\s+/g,' ').trim();
    return {name:title.length>32?title.slice(0,32).trimEnd()+'…':title,description:''};
  };
  const live=x=>C.isLive(x);
  const inCategory=(x,key)=>x.kind===key;
  function image(x,cls=''){
    if(!x.image||!/^https:\/\//.test(x.image))return '<span class="photo-unavailable">商品写真は販売店で</span>';
    let srcset='';
    try{
      const larger=new URL(x.image);
      if(larger.hostname==='thumbnail.image.rakuten.co.jp'&&larger.searchParams.has('_ex')){
        larger.searchParams.set('_ex','600x600');
        srcset=' srcset="'+esc(x.image)+' 128w, '+esc(larger.href)+' 600w" sizes="'+(config.mode==='product'?'(max-width:600px) 90vw, 460px':'(max-width:600px) 45vw, 300px')+'"';
      }
    }catch(_){}
    return '<img class="product-image '+cls+'" src="'+esc(x.image)+'"'+srcset+' alt="'+esc(copyFor(x).name)+'" decoding="async">';
  }
  const detailURL=x=>new URL('items/'+encodeURIComponent(x.id)+'.html',productBase).href;
  function render(){
    const rows=feed.filter(live);
    const signature=JSON.stringify([rows,copies,failed]);
    if(signature===lastSignature)return;lastSignature=signature;
    if(config.mode==='directory'){
      document.querySelectorAll('[data-category]').forEach(tile=>{
        const key=tile.dataset.category;
        const item=rows.find(x=>inCategory(x,key)&&x.image);
        const photo=tile.querySelector('.category-photo');
        if(item&&photo)photo.innerHTML=image(item);
      });
      return;
    }
    if(config.mode==='category'){
      const grid=document.getElementById('catalog-grid'),status=document.getElementById('catalog-status');
      const selected=rows.filter(x=>inCategory(x,config.kind));
      if(!selected.length){
        grid.innerHTML='';status.textContent=failed?'商品を読み込めませんでした。しばらくしてからお試しください。':'現在掲載できる商品はありません。';
        status.hidden=false;return;
      }
      status.textContent='';status.hidden=true;
      grid.innerHTML=selected.map(x=>{
        const copy=copyFor(x),url=detailURL(x);
        return '<article class="product-card" data-kind="'+esc(x.kind)+'">'
          +'<a class="product-photo" href="'+esc(url)+'">'+image(x)+'</a>'
          +'<div class="product-card-body"><h2><a href="'+esc(url)+'">'+esc(copy.name)+'</a></h2>'
          +(copy.description?'<p class="product-intro">'+esc(copy.description)+'</p>':'')
          +'<div class="product-card-bottom"><p class="product-price">¥'+Number(x.price_yen).toLocaleString('ja-JP')+'</p>'
          +'<a class="product-open" href="'+esc(url)+'" aria-label="'+esc(copy.name)+'の詳細">詳しく見る <span aria-hidden="true">→</span></a></div></div></article>';
      }).join('');
      return;
    }
    if(config.mode==='product'){
      const root=document.getElementById('product-detail');
      const item=rows.find(x=>x.id===config.id&&inCategory(x,config.kind));
      if(!item){
        root.innerHTML='<div class="unavailable-product"><h1>現在の商品情報を表示できません</h1><p>同じジャンルの商品から探せます。</p><a class="buy-button secondary" href="'+new URL(categories.find(c=>c.key===config.kind)?.file||'./',productBase).href+'">商品一覧へ</a></div>';return;
      }
      const copy=copyFor(item);
      root.innerHTML='<div class="detail-photo">'+image(item)+'</div><div class="detail-info"><span class="ad-label">PR</span>'
        +'<h1>'+esc(copy.headline||copy.name)+'</h1>'
        +(copy.description?'<p class="detail-intro">'+esc(copy.description)+'</p>':'')
        +'<p class="detail-price">¥'+Number(item.price_yen).toLocaleString('ja-JP')+'</p>'
        +'<a class="buy-button" href="'+esc(item.url)+'" data-buy="'+esc(item.id)+'" target="_blank" rel="noopener noreferrer sponsored">楽天市場で見る <span aria-hidden="true">↗</span></a>'
        +'<p class="seller">'+esc(item.seller||'楽天市場')+'</p>'
        +'</div>';
    }
  }
  Promise.all([get('rakuten-feed.json'),get('product-copy.json').catch(()=>({}))])
    .then(([data,copy])=>{if(!Array.isArray(data.items))throw Error('invalid');feed=data.items;copies=copy&&typeof copy==='object'?copy:{};render();})
    .catch(()=>{failed=true;render();});
  C.observe(render);
  document.addEventListener('click',event=>{
    const link=event.target.closest('a[data-buy]');if(!link)return;
    const item=feed.find(x=>x.id===link.dataset.buy);
    if(!live(item)){event.preventDefault();render();return;}
    link.dataset.itemId=item.id;
    C.track(link,{portal_kind:'product',category:config.kind});
  });
  document.addEventListener('error',event=>{
    if(event.target instanceof HTMLImageElement&&event.target.classList.contains('product-image')){
      event.target.classList.add('image-error');
      event.target.alt='商品写真は販売店でご確認ください';
    }
  },true);
})();
