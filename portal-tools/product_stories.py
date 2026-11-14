"""Source-based shopping articles; no fabricated tasting or hands-on reviews."""
from html import escape as e
from storefront_seo import cards, image, inventory_entry, live

STORIES=[
 dict(slug='yokumoku-delices-gift',id='rakuten-yokumoku-10000435',title='配りやすいお菓子を探すなら。ヨックモック「サンク デリス」の選び方',intro='5種類40個の詰め合わせ。職場への差し入れや手土産で、人数・個包装・配送条件をどう見るか整理しました。',sections=[
 ('同じお菓子を配るか、選ぶ楽しさを贈るか','公式販売ページで確認した商品は、シガールと秋冬向けの4種類を組み合わせた40個入り。1種類を全員に同じ数ずつ渡したい用途と、箱から好きな種類を選んでもらう用途では、選ぶポイントが変わります。後者なら複数の味や形がある詰め合わせを検討できます。これは商品の構成から考えた編集上の提案です。'),
 ('40個は何人分？','単純計算では20人なら1人2個、10人なら1人4個です。ただし種類ごとの数量は均等とは限りません。40人に1個ずつ配る場合も、全員が同じ種類を選べるとは限らないので、人数だけでなく箱の内訳まで確認すると選びやすくなります。'),
 ('価格だけでなく届け先まで見る','この販売ページでは北海道・九州・沖縄を送料無料の対象外とする案内があります。商品名の「送料無料」だけで判断せず、配送先を選んだあとの注文合計、到着予定日、包装・のし・手提げ袋の対応を確認しましょう。季節や販売単位が異なる商品との取り違えにも注意が必要です。'),
 ('食べる人への確認も贈り物の一部','公式表示には卵、小麦、乳成分、大豆、アーモンド、マカダミアナッツが含まれています。アレルギーがある人へ渡す場合は、現行商品の原材料表示を確認してください。当サイトでの試食は行っていません。味の好みや「誰にでも喜ばれる」といった評価は断定しません。')],sources=[('公式・楽天市場店の商品説明と配送条件','https://item.rakuten.co.jp/yokumoku/1010011309010/'),('ヨックモック公式の商品一覧','https://yokumoku.co.jp/collections/all')]),
 dict(slug='sparkling-water-case-cost',id='rakuten-lifedrinkcompany-10000022',title='炭酸水48本、安さはどう比べる？ OZA SODAの箱買い前チェック',intro='1本単価、送料、置き場所。毎日飲む炭酸水だからこそ、箱の価格だけで決めない比較方法を紹介します。',sections=[
 ('まずは1本あたりで比較する','掲載する販売ページは500ml×48本。商品代が2,550円なら1本約53.13円です。この例は11月14日に取得した商品代だけの計算で、現在価格を保証するものではありません。24本商品と比較するときは、いずれも送料込みの支払総額を本数で割ると条件が揃います。'),
 ('クーポンとポイントを一緒に引かない','複数購入が条件のクーポンは1箱だけでは使えないことがあります。ポイントも付与上限、対象者、有効期限などの条件があります。まず送料と適用できるクーポンを含めた支払額を確認し、ポイントは別の情報として比較しましょう。'),
 ('48本を置けるかも購入条件','500mlを48本買うと飲料の総量は24L、中身だけでおよそ24kgです。配達された箱を置く場所、玄関から保管場所への移動、冷蔵庫への補充を考えておくと、値段以外の負担も見えてきます。保管は直射日光と高温を避ける案内です。'),
 ('好きな味とラベルの有無を選ぶ','販売店ではプレーンやフレーバー、ラベルレスなどの選択肢を案内しています。選んだ組み合わせで価格や在庫が異なる可能性があります。当サイトで飲み比べはしていないため、炭酸の強さやおいしさの実体験としては紹介しません。初めてなら少量で味を確かめてから箱買いする方法もあります。')],sources=[('メーカー直営・楽天市場店の48本商品','https://item.rakuten.co.jp/lifedrinkcompany/zaosoda-500-48/'),('メーカー直営・プレーンの原材料説明（24本商品）','https://lifedrink.jp/Form/Product/ProductDetail.aspx?pid=OZASODA-plain-500&shop=0')])
]

def story_index(items,copies,prefix='stories/'):
    by_id={x['id']:x for x in items if live(x)}
    out=[]
    for s in STORIES:
        x=by_id.get(s['id'])
        photo=image(x,copies[x['id']]) if x else ''
        out.append('<a class="story-card" href="'+prefix+s['slug']+'.html">'+photo+'<h3>'+e(s['title'])+'</h3><p>'+e(s['intro'])+'</p><p>商品紹介記事を読む →</p></a>')
    return '<section class="story-index"><p class="eyebrow">SHOPPING JOURNAL</p><h2>写真から気になった、その先へ。</h2><p>商品の特徴と買う前の確認点を紹介します。</p><div class="story-grid">'+''.join(out)+'</div></section>'

def build_stories(items,copies,document,write):
    by_id={x['id']:x for x in items if live(x)};inventory=[]
    for s in STORIES:
        x=by_id.get(s['id']);path='products/stories/'+s['slug']+'.html'
        cover=image(x,copies[x['id']],eager=True,large=True) if x else ''
        body='<article class="product-story"><p><a href="../">モノより</a> / 商品紹介ブログ</p><p class="eyebrow">SHOPPING JOURNAL · PR</p><h1>'+e(s['title'])+'</h1><p>'+e(s['intro'])+'</p><p class="small-text">2026年11月15日公開／商品情報確認：2026年11月14日。実食・実機使用レビューではありません。</p><div class="story-cover">'+cover+'</div>'
        body+=''.join('<section><h2>'+e(h)+'</h2><p>'+e(p)+'</p></section>' for h,p in s['sections'])
        body+='<section><h2>確認した情報源</h2><ul>'+''.join('<li><a href="'+e(u,quote=True)+'" target="_blank" rel="noopener noreferrer">'+e(t)+'</a></li>' for t,u in s['sources'])+'</ul></section>'
        # A live product block supplies the exact seller link and the standard expiry guard.
        body+='<section><h2>掲載商品の価格・販売条件</h2>'+ (cards([x],copies).replace('href="items/','href="../items/') if x else '<p>現在、販売情報を確認できません。最新情報は公式の商品ページでご確認ください。</p>')+'</section><p><a href="../">ジャンルからほかの商品を探す →</a></p></article>'
        write(path,document(s['title']+'｜モノより',path,body,depth=2,description=s['intro'],image_url=x.get('image') if x else None,config={'mode':'category','kind':x['kind']} if x else None,scripts=('catalog.js',) if x else (),initial={'items':[x],'copies':copies} if x else None,structured=[{'@type':'BlogPosting','headline':s['title'],'datePublished':'2026-11-15','author':{'@type':'Organization','name':'モノより'}}]))
        inventory.append(inventory_entry(path,s))
    return inventory
