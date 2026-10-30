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

async function guideLifecycle() {
  let clock = now;
  class Clock extends Date {static now() {return clock;}}
  const node = () => ({innerHTML:'', textContent:'', listeners:{}, addEventListener(type, callback) {this.listeners[type] = callback;}});
  const grid = node(), status = node(), timers = [], events = [];
  const nodes = {'guide-cards':grid, 'guide-status':status};
  const context = {
    Date:Clock, URL, Intl, console,
    GUIDE_CONFIG:battery,
    document:{getElementById:id => nodes[id], addEventListener() {}, hidden:false},
    location:{href:'https://example.test/products/mobile-battery.html', pathname:'/products/mobile-battery.html'},
    addEventListener() {}, setInterval:callback => {timers.push(callback); return timers.length;}, clearInterval() {},
    gtag:(...args) => events.push(args),
    fetch:async () => ({ok:true, json:async () => ({updated_at:'2026-10-31T01:00:00+09:00', items:[product, {...product, id:'monitor', title:'4K モニター'}]})}),
  };
  context.window = context;
  vm.createContext(context);
  for (const script of ['commerce.js', 'guide.js']) vm.runInContext(fs.readFileSync(path.join(__dirname, '../portal-assets', script), 'utf8'), context);
  await new Promise(resolve => setImmediate(resolve));
  check(grid.innerHTML.includes('モバイルバッテリー'), true, 'guide renders its matching live product');
  check(grid.innerHTML.includes('4K モニター'), false, 'same-category unrelated products are hidden');
  const link = {dataset:{itemId:'battery'}, href:product.url};
  grid.listeners.click({target:{closest:() => link}, preventDefault() {throw Error('fresh click blocked');}});
  check(events[0][1], 'portal_outbound_click', 'real guide click emits conversion precursor');
  check(events[0][2].item_id, 'battery', 'clicked product ID included');
  check(events[0][2].guide_slug, 'mobile-battery', 'article identity included');
  check(JSON.stringify(events).includes(product.url), false, 'full affiliate URL is not sent to analytics');
  clock = Date.parse(product.expires_at) + 1;
  let blocked = false;
  grid.listeners.click({target:{closest:() => link}, preventDefault() {blocked = true;}});
  check(blocked, true, 'expired product click blocked before timer fires');
  check(grid.innerHTML.includes('data-rakuten-link'), false, 'expired product removed without page reload');
  check(timers.length, 1, 'one freshness timer registered');
}

guideLifecycle().then(() => console.log('PASS:', checks, 'commerce arithmetic, matching, dates, expiry and click regressions'))
  .catch(error => {console.error(error); process.exitCode = 1;});
