"""Reusable shopping calculator, no purchase prices fetched or invented."""
from storefront_seo import inventory_entry
BODY = r'''
<style>
.unit-tool{max-width:960px;margin:auto}.unit-tool>p{margin:14px 0;line-height:1.9}.unit-panels{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:24px 0}.unit-option{background:white;border:1px solid #dce2d5;border-radius:18px;padding:24px;min-width:0}.unit-option h2{margin:0 0 16px}.unit-option label{display:block;font-size:14px;margin:14px 0}.unit-option input{display:block;width:100%;box-sizing:border-box;min-height:46px;padding:10px;border:1px solid #aebcab;border-radius:8px;font:inherit}.unit-result{padding:20px;background:#eaf0e3;border-radius:12px;margin-top:20px;min-height:80px}.unit-result strong{font-size:28px;display:block}.unit-actions{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}.unit-actions button,.unit-actions a{padding:12px 18px;border-radius:10px;border:1px solid #204739;background:white;color:#204739;cursor:pointer;font:inherit}.unit-verdict{background:#204739;color:white;padding:22px;border-radius:14px;font-size:18px}.unit-tool details{margin:20px 0;padding:18px;background:white;border-radius:12px}.unit-tool summary{cursor:pointer;font-weight:bold}.unit-tool details p{margin-top:12px}.unit-tool ul{padding-left:24px}.unit-tool li{margin:8px 0}@media(max-width:600px){.unit-panels{grid-template-columns:1fr}.unit-option{padding:18px}.unit-result strong{font-size:24px}}
</style>
<article class="unit-tool">
<p class="eyebrow">MONOYORI / SHOPPING TOOL</p>
<h1>送料込み単価比較｜1本・1個あたり、どちらがお得？</h1>
<p>飲料の箱買い、個包装のお菓子、日用品のまとめ買いに。商品代・送料・値引き・数量を入れると、支払総額と1個あたりを比較できます。</p>
<p class="small-text">初期値は計算例です。特定商品の現在価格・販売条件を示すものではありません。入力内容はサーバーに送信しません。</p>
<form id="unit-form">
<div class="unit-panels">
<section class="unit-option"><h2>候補A</h2>
<label for="a-price">商品代（税込・円）<input id="a-price" name="ap" type="number" min="0" max="10000000" step="1" value="1440" required inputmode="numeric"></label>
<label for="a-ship">送料（税込・円）<input id="a-ship" name="as" type="number" min="0" max="10000000" step="1" value="0" required inputmode="numeric"></label>
<label for="a-discount">使える値引き・クーポン（円）<input id="a-discount" name="ad" type="number" min="0" max="10000000" step="1" value="0" required inputmode="numeric"></label>
<label for="a-count">本数・個数<input id="a-count" name="an" type="number" min="1" max="1000000" step="1" value="24" required inputmode="numeric"></label>
<div class="unit-result" id="result-a"></div></section>
<section class="unit-option"><h2>候補B</h2>
<label for="b-price">商品代（税込・円）<input id="b-price" name="bp" type="number" min="0" max="10000000" step="1" value="2640" required inputmode="numeric"></label>
<label for="b-ship">送料（税込・円）<input id="b-ship" name="bs" type="number" min="0" max="10000000" step="1" value="0" required inputmode="numeric"></label>
<label for="b-discount">使える値引き・クーポン（円）<input id="b-discount" name="bd" type="number" min="0" max="10000000" step="1" value="0" required inputmode="numeric"></label>
<label for="b-count">本数・個数<input id="b-count" name="bn" type="number" min="1" max="1000000" step="1" value="48" required inputmode="numeric"></label>
<div class="unit-result" id="result-b"></div></section>
</div><p class="unit-verdict" id="unit-verdict" role="status" aria-live="polite"></p>
<div class="unit-actions"><button type="reset">計算例に戻す</button>
<a href="https://www.pinterest.com/pin/create/button/?url=https%3A%2F%2Fsho-monoyori-review.zodiac-suu.workers.dev%2Fproducts%2Ftools%2Funit-price&amp;media=https%3A%2F%2Fraw.githubusercontent.com%2Fsho-support%2Fai-trend-blog%2Fmain%2Fgrowth%2Fsocial-assets%2Funit-price-pinterest.png&amp;description=%E9%80%81%E6%96%99%E8%BE%BC%E3%81%BF%E5%8D%98%E4%BE%A1%E3%82%92%E6%AF%94%E8%BC%83%EF%BD%9C%E3%83%A2%E3%83%8E%E3%82%88%E3%82%8A" target="_blank" rel="noopener noreferrer">Pinterestに計算ツールを保存 ↗</a></div>
</form>
<noscript><p>入力して比較するにはJavaScriptを有効にしてください。計算式：商品代＋送料−適用できる値引き。その総額を本数・個数で割ります。</p></noscript>
<details open><summary>同じ条件で比べるための確認点</summary><ul><li>500mlと1Lなど容量の違う商品は、1本単価だけでは比較できません。同じ容量に揃えてください。</li><li>セット数ではなく、実際の合計本数・個数を入力してください。</li><li>クーポンは対象商品・最低購入額・利用上限を確認し、使えるものだけ入力します。</li><li>ポイントは付与条件や期限があるため、支払総額から自動で差し引きません。</li><li>小数点以下2桁の表示は四捨五入。比較は丸める前の値を使います。</li></ul></details>
<h2>計算のあとに、買う前の条件も確認</h2>
<p><a href="../stories/sparkling-water-case-cost">炭酸水48本：単価・保管場所・味の確認点 →</a></p>
<p><a href="../stories/yokumoku-delices-gift">配るお菓子：人数・個包装・配送条件の選び方 →</a></p>
<p><a href="../">写真と口コミ点数から商品を探す →</a></p>
</article>
<script>
(()=>{'use strict';const form=document.getElementById('unit-form'),verdict=document.getElementById('unit-verdict');
const yen=n=>n.toLocaleString('ja-JP',{minimumFractionDigits:2,maximumFractionDigits:2});
function option(prefix){const fields=['price','ship','discount','count'].map(x=>document.getElementById(prefix+'-'+x));if(fields.some(x=>!x.value.trim()||!x.validity.valid))return null;const [p,s,d,n]=fields.map(x=>Number(x.value));if(d>p+s)return null;return {total:p+s-d,n,unit:(p+s-d)/n};}
function draw(){const a=option('a'),b=option('b');for(const [prefix,v] of [['a',a],['b',b]]){const out=document.getElementById('result-'+prefix);out.replaceChildren();if(!v){out.textContent='入力を確認してください。数量は1以上、値引きは商品代＋送料以下にします。';continue;}const strong=document.createElement('strong');strong.textContent='1個あたり '+yen(v.unit)+'円';out.append(strong,document.createTextNode('支払総額 '+v.total.toLocaleString('ja-JP')+'円 / '+v.n.toLocaleString('ja-JP')+'個'));}if(!a||!b){verdict.textContent='両方の入力が揃うと単価を比較できます。';return;}const cross=a.total*b.n-b.total*a.n;if(cross===0){verdict.textContent='1個あたりの単価は同じです。必要な個数と支払総額で選びましょう。';}else{verdict.textContent='候補'+(cross>0?'B':'A')+'が、1個あたり '+yen(Math.abs(a.unit-b.unit))+'円安い計算です。';}}
form.addEventListener('submit',e=>e.preventDefault());form.addEventListener('input',draw);form.addEventListener('reset',()=>setTimeout(draw,0));draw();})();
</script>
'''
def build_unit_tool(document,write):
    path='products/tools/unit-price.html'
    write(path,document('送料込み単価比較｜1本・1個あたりの価格計算｜モノより',path,BODY,depth=2,description='商品代・送料・クーポン・本数を入力して支払総額と1本・1個単価を無料で比較。炭酸水や日用品のまとめ買いに。',image_url='https://raw.githubusercontent.com/sho-support/ai-trend-blog/main/growth/social-assets/unit-price-pinterest.png'))
    return [inventory_entry(path,BODY)]
