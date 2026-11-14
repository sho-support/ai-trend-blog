"""Source-backed editorial content; kept outside the live price component."""
from html import escape as e

GUIDES = {
'rakuten-logicool-10000417': {
 'title':'G335は、軽さと扱いやすさを優先する人の候補',
 'verdict':'編集部の判断：3.5mm有線で接続し、充電せず使いたい人向け。装着感とマイク音質は好みが分かれるため、軽量という理由だけで決めず、試着や録音サンプルも確認したい製品です。',
 'sections':[
 ('公式情報から分かる良さ','ロジクールの発売時資料では240g。サスペンション式ヘッドバンドとメッシュ製イヤーパッドを採用しています。マイクを跳ね上げるとミュートできるため、通話を一時的に止める操作が分かりやすい構造です。3.5mm接続なので、接続先に対応端子があるかを先に確認してください。'),
 ('実機レビューでは、どこが評価されている？','FPS酒場の実機レビューは、装着時の負担や通気性を好意的に評価しています。一方、FPSの足音については中音域が弱く感じるという指摘もあります。同記事の感想であり、すべての利用者に共通する性能評価ではありません。'),
 ('購入者の声との違い','価格.comの購入者投稿には、締め付けが気になり長時間で痛みを感じたという声もあります。装着感を評価する実機記事と意見が分かれるため、「誰でも快適」とは判断できません。頭の大きさや眼鏡との相性も含めて試着を優先すると判断しやすくなります。'),
 ('向く人・別候補も比較したい人','軽い有線ヘッドセットを探す人、マイクのミュートを手元の設定画面に頼らず操作したい人には候補です。無線で移動したい人や音楽鑑賞・配信音声の質を最優先する人は、用途に合う別候補の試聴もおすすめします。これは仕様と参照記事を踏まえた編集部の判断です。'),
 ('購入前の確認','掲載価格の対象色・型番、接続先の3.5mm端子、マイク入力方式、保証と返品条件を販売店で確認してください。発売時の参考価格を現在価格として扱っていません。')],
 'sources':[
 ('ロジクール公式・発売時の仕様','https://press.logicool.co.jp/ja-jp/g335/'),
 ('FPS酒場・実機レビュー','https://vanillaice-fps.com/logicool-g335-review/'),
 ('価格.com・ユーザーレビュー（個人の感想）','https://review.kakaku.com/review/J0000036134/')]
}}

GUIDES['rakuten-yorozuyasan-reiwa-10000001'] = {
 'title':'このノートPCは、価格より先に「選ぶ構成」を確認',
 'verdict':'編集部の判断：現段階では一律におすすめできません。取得した販売タイトルに複数のCPU・メモリ・SSD容量が混在しており、掲載価格の対象構成を特定できていないためです。',
 'sections':[
 ('画像の「第14世代」だけでは性能を判断できない','取得した販売タイトルには「第14世代CPU」と「N3450」「Core i5 i7」が併記されています。Intel公式ではN3450はCeleronで、発売時期は2016年第3四半期です。したがって、この商品ページの全選択肢を第14世代Core搭載機として紹介することはできません。販売店に選択構成の正確なCPU型番を確認してください。'),
 ('購入判断に必要な5項目','CPUの完全な型番、価格に含まれるメモリとSSD容量、画面サイズ、Officeの製品名・ライセンス条件、保証対象と修理時の送料を確認してください。最大32GB・最大1TBなどの表記を、最低価格で買える仕様と混同しないことが大切です。'),
 ('口コミを読む際の注意','今回、同一構成と確認できる複数媒体の口コミは確保できていません。別のCPUや容量を選んだ人の評価は、そのまま自分の購入構成の評価には使えません。レビュー内の購入オプションと、ショップ対応への評価か製品への評価かを分けて読んでください。'),
 ('どんな条件が確認できたら比較できる？','同じCPU・メモリ・SSD・Office条件にそろえて、他社ノートPCの総額と保証を比較します。現段階では性能、電池持ち、静音性を確認できていないため、「仕事に十分」「長時間使える」などの推奨はしません。')],
 'sources':[
 ('販売店の商品ページ・選択構成と価格の確認先','https://item.rakuten.co.jp/yorozuyasan-reiwa/yypc01/'),
 ('Intel公式・Celeron N3450の仕様と発売時期','https://www.intel.co.jp/content/www/jp/ja/products/sku/95596/intel-celeron-processor-n3450-2m-cache-up-to-2-20-ghz/specifications.html')]
}

def buying_guide(ident, item):
    g=GUIDES.get(ident)
    if not g:return ''
    out='<section class="buying-guide" aria-label="購入判断ガイド"><p class="guide-source">調査日：2026年11月14日｜当サイトでの実機使用・測定は行っていません。</p><h2>'+e(g['title'])+'</h2><p class="guide-verdict">'+e(g['verdict'])+'</p>'
    out+=''.join('<h3>'+e(h)+'</h3><p>'+e(t)+'</p>' for h,t in g['sections'])
    out+='<h3>調査した情報源</h3><ul>'+''.join('<li><a target="_blank" rel="noopener noreferrer" href="'+e(u,quote=True)+'">'+e(n)+'</a></li>' for n,u in g['sources'])+'</ul>'
    out+='<a class="buy-button" data-buy="'+e(ident,quote=True)+'" target="_blank" rel="noopener noreferrer sponsored" href="'+e(item['url'],quote=True)+'">楽天市場で対象モデル・価格・保証を確認 ↗</a></section>'
    return out
