/* Business-logic regressions, using Node's built-in assertions and VM. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const C = require('../portal-assets/commerce.js');
const now = Date.parse('2026-10-31T01:00:00+09:00');
const product = {
  id:'battery', title:'モバイルバッテリー USB-C', category:'家電・デジタル',
  approved:true, affiliate:true, price_yen:3000,
  url:'https://hb.afl.rakuten.co.jp/hgc/example/',
  expires_at:'2026-11-01T00:00:00+09:00',
};
let checks = 0;
const check = (value, expected, label) => {assert.deepEqual(value, expected, label); checks++;};
check(C.isLive(product, now), true, 'fresh approved referral is usable');
for (const patch of [
  {expires_at:null}, {expires_at:'broken'}, {expires_at:'2026-10-30T12:00:00+09:00'},
  {approved:false}, {affiliate:false}, {price_yen:0}, {price_yen:NaN},
  {url:'https://rakuten.co.jp.attacker.example/item'},
  {url:'https://rakuten.co.jp@attacker.example/item'},
  {url:'http://hb.afl.rakuten.co.jp/item'},
]) check(C.isLive({...product, ...patch}, now), false, 'reject invalid offer ' + JSON.stringify(patch));
check(C.isLive(product, Date.parse(product.expires_at)), false, 'expiry boundary is exclusive');
const battery = {category:'家電・デジタル', kinds:['power-bank']};
const monitor = {category:'家電・デジタル', kinds:['monitor']};
check(C.matches(product, battery), true, 'battery belongs in battery article');
check(C.matches(product, monitor), false, 'battery never appears in monitor article');
check(C.matches({...product,title:'Anker モバイルバッテリー ディスプレイ搭載'}, monitor), false, 'a battery with a display is not a PC monitor');
check(C.matches({...product,title:'4Kモニターアーム'}, monitor), false, 'monitor accessories are not monitors');
check(C.matches({...product, title:'4K モニター'}, monitor), true, 'old feed can classify by title');
check(C.matches({...product, kind:'monitor'}, battery), false, 'typed feed is filtered by exact kind');
check(C.matches({title:'キュキュット 食器用洗剤', category:'日用品・生活'}, {category:'日用品・生活', kinds:['laundry-detergent']}), false, 'dish detergent never shown as laundry');
check(C.matches({title:'衣料用 アタック 洗濯洗剤', category:'日用品・生活'}, {category:'日用品・生活', kinds:['laundry-detergent']}), true, 'laundry match');
check(C.matches({title:'ボールド 洗濯洗剤 ジェルボール', kind:'laundry-detergent',category:'日用品・生活'}, {category:'日用品・生活', kinds:['laundry-detergent']}), false, 'capsules are excluded from a mass/volume dose comparison');
check(C.unitCost({price:3980, shipping:0, coupon:0, quantity:5}).unit, 796, 'rice A includes delivery');
check(C.unitCost({price:7480, shipping:660, coupon:0, quantity:10}).unit, 814, 'delivery reverses rice ranking');
check(C.unitCost({price:1800, shipping:0, coupon:0, quantity:1500, dose:25}).perUse, 30, 'detergent A');
check(C.unitCost({price:1400, shipping:0, coupon:0, quantity:700, dose:10}).perUse, 20, 'concentration reverses detergent ranking');
check(C.unitCost({price:1800, shipping:0, coupon:0, quantity:960}).unit, 1.875, 'fractional per-sheet cost retained');
for (const patch of [{quantity:0}, {coupon:5001}, {shipping:-1}, {price:NaN}, {dose:0}])
  check(C.unitCost({price:4000, shipping:500, coupon:0, quantity:5, ...patch}), null, 'invalid arithmetic inputs are rejected');
check(C.eventWindow('weekend','2026-11-01'), {low:'2026-11-01',high:'2026-11-01'}, 'Sunday stays in the current weekend');
check(C.eventWindow('weekend','2026-10-31'), {low:'2026-10-31',high:'2026-11-01'}, 'Saturday includes Sunday');
check(C.eventWindow('next7','2026-10-31'), {low:'2026-10-31',high:'2026-11-06'}, '7-day window crosses month');
check(C.eventWindow('nextmonth','2026-12-31'), {low:'2027-01-01',high:'2027-01-31'}, 'next month crosses year');
check(C.eventWindow('month','2026-10-31'), {low:'2026-10-31',high:'2026-10-31'}, 'month ends at month end');

const a8={id:'a8-test',title:'テスト商品',kind:'hair-dryers',source:'a8',approved:true,affiliate:true,site_registered:true,site_url:'https://sho-support.github.io/ai-trend-blog/products/',material_type:'free_link',url:'https://px.a8.net/svt/ejp?a8mat=unit-test',expires_at:'2026-11-01T00:00:00+09:00'};
check(C.isA8Live(a8,now),true,'registered and approved A8 free link is usable');
for(const patch of [{approved:false},{site_registered:false},{site_url:'https://www.youtube.com/channel/test'},{material_type:'banner'},{image:'https://example.test/photo.jpg',image_authorized:false},{url:'https://px.a8.net.attacker.example/'},{expires_at:'2020-01-01T00:00:00+09:00'}])check(C.isA8Live({...a8,...patch},now),false,'reject unapproved or wrong-site A8 material');

async function catalogLifecycle() {
  async function fixture(mode,query='',{
    rakutenOffline=false,a8Offline=false,a8Items=[],initialItems=[{...product,kind:'power-bank'}],itemId='battery',
  }={}) {
    let clock = now;
    class Clock extends Date {static now() {return clock;}}
    const node = () => ({innerHTML:'', textContent:'', hidden:false});
    const grid=node(),status=node(),detail=node(),input=node(),timers=[],events=[],listeners={};
    const nodes={'catalog-grid':grid,'catalog-status':status,'product-detail':detail,'product-query':input};
    const context={Date:Clock,URL,URLSearchParams,Intl,console,HTMLImageElement:class {},
      CATALOG_CONFIG:{mode,kind:'power-bank',id:itemId},CATALOG_CATEGORIES:[{key:'power-bank',file:'mobile-battery.html'}],
      CATALOG_INITIAL:mode==='search'?undefined:{items:initialItems,copies:{}},
      document:{currentScript:{src:'https://example.test/portal-assets/catalog.js'},getElementById:id=>nodes[id],querySelector:()=>null,querySelectorAll:()=>[],addEventListener:(type,callback)=>{listeners[type]=callback;},hidden:false},
      location:{href:'https://example.test/products/items/battery.html',pathname:'/products/items/battery.html',search:'?q='+encodeURIComponent(query)},
      addEventListener(){},setInterval:callback=>{timers.push(callback);return timers.length;},clearInterval(){},
      gtag:(...args)=>events.push(args),
      fetch:async url=>{
        if(String(url).endsWith('product-copy.json'))return {ok:true,json:async()=>({soda:{name:'OZA SODA 48本',price_from:true}})};
        if(String(url).endsWith('a8-approved.json'))return {ok:!a8Offline,json:async()=>({items:a8Items})};
        return {ok:!rakutenOffline,json:async()=>({items:[
          {...product,kind:'power-bank',title:product.title+'【公式店 ポイント10倍 ギフト 送料無料】',display_title:product.title+'【公式店 ポイント10倍 ギフト 送料'},
          {...product,id:'monitor',kind:'monitor',title:'4K モニター'},
          {...product,id:'headset',kind:'gaming-headsets',title:'Logicool G335 ヘッドセット',seller:'ロジクール 公式ストア'},
          {...product,id:'pro-x',kind:'gaming-headsets',title:'Logicool G PRO X G-PHS-003'},
          {...product,id:'soda',kind:'water',title:'炭酸水 500ml 48本 OZA SODA',price_yen:2370},
        ]})};
      },
    };
    context.window=context;vm.createContext(context);
    for(const script of ['commerce.js','catalog.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../portal-assets',script),'utf8'),context);
    await new Promise(resolve=>setImmediate(resolve));
    return {grid,status,detail,input,timers,events,listeners,expire:()=>{clock=Date.parse(product.expires_at)+1;}};
  }
  const category=await fixture('category');
  check(category.grid.innerHTML.includes('モバイルバッテリー'),true,'category renders relevant product');
  check(category.grid.innerHTML.includes('4K モニター'),false,'category never mixes another genre');
  check(category.grid.innerHTML.includes('ポイント10倍'),false,'new items strip promotional metadata after the product name');
  check(category.grid.innerHTML.includes('【'),false,'new items never show a cut-off marketing bracket');
  check(category.grid.innerHTML.includes('data-buy="battery"'),true,'category can open the actual shop without another page');
  check(category.grid.innerHTML.includes('rel="noopener noreferrer sponsored"'),true,'direct shop link is marked as advertising');
  const listLink={dataset:{buy:'battery'},href:product.url};
  category.listeners.click({target:{closest:()=>listLink},preventDefault(){throw Error('fresh list purchase blocked');}});
  check(category.events[0][2].placement,'list','list clicks are distinguishable from detail clicks');
  category.expire();category.timers[0]();
  check(category.grid.innerHTML,'','category removes expired offers without a reload');
  let listBlocked=false;
  category.listeners.click({target:{closest:()=>listLink},preventDefault(){listBlocked=true;}});
  check(listBlocked,true,'an expired list link cannot bypass eligibility');
  check(category.events.length,1,'blocked list purchase is not counted as a click');
  const detail=await fixture('product');
  check(detail.detail.innerHTML.includes('data-buy="battery"'),true,'product detail has one real purchase action');
  const views=detail.events.filter(x=>x[1]==='view_item');
  check(views.length,1,'seed plus fresh feed counts only one detail view');
  check(views[0][2].items[0].item_id,'battery','view uses the actual product identity');
  check(views[0][2].items[0].price,3000,'known price is recorded without inventing revenue');
  const link={dataset:{buy:'battery'},href:product.url};
  detail.listeners.click({target:{closest:()=>link},preventDefault(){throw Error('fresh purchase link blocked');}});
  const click=detail.events.find(x=>x[1]==='portal_outbound_click');
  check(click[1],'portal_outbound_click','purchase action emits a measurable click');
  check(click[2].item_id,'battery','correct product identity is recorded');
  check(click[2].placement,'detail','detail click source can be compared with list clicks');
  check(detail.events.some(x=>x[1]==='purchase'),false,'visits and outbound clicks never pretend to be sales');
  check(JSON.stringify(detail.events).includes(product.url),false,'full referral URL is not sent to analytics');
  detail.expire();let blocked=false;
  detail.listeners.click({target:{closest:()=>link},preventDefault(){blocked=true;}});
  check(blocked,true,'expired purchase action is blocked immediately');
  check(detail.detail.innerHTML.includes('data-buy'),false,'expired product is removed');
  check(detail.events.filter(x=>x[1]==='view_item').length,1,'expiry and repeated renders do not inflate views');

  const retired=await fixture('product','',{
    itemId:'retired-a8',initialItems:[],a8Items:[{...a8,id:'retired-a8',kind:'power-bank',expires_at:'2020-01-01T00:00:00Z'}],
  });
  check(retired.detail.innerHTML.match(/data-buy="[^"]+"/g),['data-buy="battery"'],'a retired detail offers only eligible products in its own genre');
  check(retired.detail.innerHTML.includes('class="ad-label">PR'),true,'replacement offers disclose advertising next to the products');
  retired.listeners.click({target:{closest:()=>listLink},preventDefault(){throw Error('fresh alternative purchase blocked');}});
  check(retired.events[0][2].placement,'related','replacement purchase links are distinguishable from detail clicks');
  retired.expire();retired.timers[0]();
  check(retired.detail.innerHTML.includes('data-buy'),false,'replacement offers also disappear on expiry');

  for(const [query,id] of [['ロジクール　Ｇ３３５','headset'],['ＧＰＨＳ－００３','pro-x'],['５００ｍｌ×４８本','soda'],['ﾓﾆﾀｰ','monitor']]){
    const search=await fixture('search',query);
    check(search.grid.innerHTML.match(/data-buy="[^"]+"/g),['data-buy="'+id+'"'],'find the actual listing for '+query);
    check(search.input.value,query,'keep the original input visible');
  }
  const soda=await fixture('search','OZA SODA');
  check(soda.grid.innerHTML.includes('2,370円〜'),true,'a listing with several prices shows its price as a starting amount');
  const missing=await fixture('search','unavailable-model');
  check(missing.status.textContent,'条件に合う商品はありません。','report no results only after a successful load');
  const unavailable=await fixture('search','Ｇ３３５',{rakutenOffline:true});
  check(unavailable.status.textContent,'商品を読み込めませんでした。しばらくしてからお試しください。','distinguish a failed feed from an empty search');
  const a8Only=await fixture('search','テスト商品',{rakutenOffline:true,a8Items:[a8]});
  check(a8Only.grid.innerHTML.includes('data-buy="a8-test"'),true,'a Rakuten outage leaves the confirmed A8 search result and shop link available');
  const rakutenOnly=await fixture('search','Ｇ３３５',{a8Offline:true});
  check(rakutenOnly.grid.innerHTML.includes('data-buy="headset"'),true,'an A8 outage leaves Rakuten search results available');
  const unconfirmedA8=await fixture('category','',{rakutenOffline:true,a8Offline:true,initialItems:[{...a8,kind:'power-bank'}]});
  check(unconfirmedA8.grid.innerHTML,'','a missing approval list removes A8 links from the initial HTML');
}

catalogLifecycle().then(()=>console.log('PASS:',checks,'commerce and storefront regressions'))
  .catch(error=>{console.error(error);process.exitCode=1;});
