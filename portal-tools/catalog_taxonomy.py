"""Store departments, product shelves and title-based relevance checks."""
import re

LEGACY = {'snacks':'okashi-matome.html','rice':'okome-5kg.html','monitor':'work-monitor.html','power-bank':'mobile-battery.html','laundry-detergent':'nichiyohin-matome.html','sneakers':'sneakers.html','skincare':'skincare.html','pet-wipes':'pet-supplies.html'}

def shelf(key, name, query, accept, exclude='', minimum=300):
    return {'key':key,'name':name,'query':query,'accept':accept,'exclude':exclude,'min_price':minimum,'file':LEGACY.get(key,key+'.html')}

def department(key,name,icon,rows):
    for row in rows:row['department']=key
    return {'key':key,'name':name,'icon':icon,'file':'departments/'+key+'.html','children':rows}

DEPARTMENTS = [
 department('pc','PC・周辺機器','💻',[
  shelf('laptops','ノートPC','ノートパソコン 新品','ノートパソコン|ノートPC|MacBook','ケース|バッグ|カバー|フィルム|中古|スタンドのみ',25000),
  shelf('desktops','デスクトップPC','デスクトップパソコン 新品','デスクトップ|ミニPC|ミニパソコン','中古|ケースのみ|電源のみ',25000),
  shelf('monitor','PCモニター','液晶ディスプレイ IPS','モニター|ディスプレイ','ゲーミング|gaming|アーム|フィルム|カバー|スタンドのみ|中古',6000),
  shelf('keyboards','キーボード','キーボード ワイヤレス','キーボード','ゲーミング|gaming|カバー|ケース|キーキャップ|キースイッチ|楽器',1000),
  shelf('mice','マウス','マウス ワイヤレス','マウス','ゲーミング|gaming|マウスパッド|ケース|スプレー',700),
  shelf('routers','Wi-Fiルーター','Wi-Fi ルーター','ルーター|ルータ','収納|スタンド|ケース|レンタル',2500),
  shelf('printers','プリンター','プリンター 本体','プリンター|プリンタ|複合機','インクのみ|トナー|用紙|カートリッジのみ|中古',6000),
  shelf('storage','SSD・外付けストレージ','外付け SSD','SSD|ハードディスク|HDD','ケースのみ|収納|ケーブルのみ',2000),
 ]),
 department('gaming','ゲーム','🎮',[
  shelf('gaming-monitor','ゲーミングモニター','ゲーミングモニター','ゲーミングモニター|ゲーミング モニター|gaming monitor','アーム|保護|スタンドのみ|中古',9000),
  shelf('game-consoles','ゲーム機本体','ゲーム機 本体 新品','Nintendo Switch|ニンテンドースイッチ|PlayStation|プレイステーション|PS5|Xbox','ソフトのみ|ケース|フィルム|カバー|スタンド|コントローラー|修理|ジャンク|中古',20000),
  shelf('game-controllers','コントローラー','ゲーム コントローラー','コントローラー|コントローラ|ゲームパッド','カバー|ケース|スティックのみ',1500),
  shelf('gaming-headsets','ゲーミングヘッドセット','ゲーミングヘッドセット','ゲーミング|gaming','イヤーパッド|ケース|スタンド|交換用',1500),
  shelf('game-software','ゲームソフト','Nintendo Switch ソフト','Switch|PS5|PlayStation','本体|ケース|収納|カバー|フィルム|中古',2000),
 ]),
 department('appliances','生活家電・テレビ','🏠',[
  shelf('televisions','テレビ','4K テレビ','テレビ','スタンド|壁掛け金具|リモコン|保護|アンテナ|台のみ|チューナーのみ|中古',18000),
  shelf('refrigerators','冷蔵庫','冷蔵庫 本体','冷蔵庫','冷蔵庫用|マット|ラック|レンタル|交換用|冷蔵庫台|中古',15000),
  shelf('washing-machines','洗濯機','全自動洗濯機','洗濯機','洗濯機用|台のみ|ホース|カバー|ラック|レンタル|中古',18000),
  shelf('air-conditioners','エアコン','エアコン 本体','エアコン','リモコン|カバー|フィルター|洗浄|クリーニング|配管のみ|中古',25000),
  shelf('vacuum-cleaners','掃除機','掃除機 コードレス','掃除機|クリーナー','フィルター|バッテリーのみ|交換用|紙パック|替えブラシ',4000),
  shelf('microwave-ovens','電子レンジ・オーブン','電子レンジ 本体','電子レンジ|オーブンレンジ','ラック|台のみ|調理器|容器|中古',7000),
  shelf('rice-cookers','炊飯器','炊飯器 本体','炊飯器|炊飯ジャー','内釜のみ|内なべ|部品|用パッキン|中古',5000),
  shelf('air-purifiers','空気清浄機','空気清浄機 本体','空気清浄機','交換用|フィルターのみ|フィルタのみ|中古',5000),
  shelf('electric-kettles','電気ケトル','電気ケトル','ケトル|電気ポット','フィルター|交換用|中古',2000),
 ]),
 department('cameras','カメラ','📷',[
  shelf('mirrorless-cameras','ミラーレスカメラ','ミラーレス カメラ 新品','ミラーレス|ミラーレス一眼','ケース|バッグ|フィルム|カバー|バッテリー|中古',40000),
  shelf('digital-cameras','コンパクトカメラ','デジタルカメラ 新品','デジタルカメラ|デジカメ|コンパクトカメラ','ケース|バッグ|フィルム|カバー|中古',6000),
  shelf('action-cameras','アクションカメラ','アクションカメラ 本体','アクションカメラ|GoPro|Osmo Action|Insta360','ケース|フィルム|カバー|マウント|バッテリー|中古',15000),
  shelf('camera-lenses','交換レンズ','交換レンズ カメラ','レンズ','レンズキャップ|レンズカバー|フィルター|フィルタ|保護|中古',10000),
  shelf('tripods','三脚・撮影用品','カメラ 三脚','三脚','ケースのみ|ネジのみ',1500),
 ]),
 department('mobile','スマホ・タブレット','📱',[
  shelf('smartphones','スマートフォン本体','スマートフォン 本体 新品','スマートフォン|iPhone|Xperia|Galaxy|Pixel|AQUOS|OPPO|Xiaomi','ケース|フィルム|カバー|ガラス|修理|ジャンク|中古',18000),
  shelf('tablets','タブレット本体','タブレット 本体 新品','タブレット|iPad','ケース|フィルム|カバー|保護|スタンド|中古',9000),
  shelf('phone-cases','スマホケース','スマホケース','ケース','イヤホンケース|収納箱',500),
  shelf('power-bank','モバイルバッテリー','モバイルバッテリー USB-C','モバイルバッテリー|Power Bank','ケースのみ',800),
  shelf('phone-chargers','充電器・ケーブル','USB-C 充電器','充電器|充電ケーブル|USB-C|Type-C','収納|ケースのみ',700),
 ]),
 department('audio','オーディオ','🔊',[
  shelf('speakers','スピーカー','Bluetooth スピーカー','スピーカー','スタンド|ケーブルのみ|ブラケット|中古',1500),
  shelf('earbuds','ワイヤレスイヤホン','完全ワイヤレス イヤホン','イヤホン|イヤフォン|AirPods','ケースのみ|ケースカバー|イヤーピース|交換用|中古',1500),
  shelf('headphones','ヘッドホン','ワイヤレス ヘッドホン','ヘッドホン|ヘッドフォン','ゲーミング|gaming|スタンド|イヤーパッド|交換用|ケースのみ|中古',2000),
  shelf('soundbars','サウンドバー','サウンドバー','サウンドバー|ホームシアター','金具|スタンド|中古',5000),
  shelf('audio-players','音楽プレーヤー','デジタルオーディオプレーヤー','プレーヤー|ウォークマン|WALKMAN','ケース|フィルム|カバー|中古',5000),
 ]),
 department('beauty','美容・コスメ','🧴',[
  shelf('hair-dryers','ドライヤー','ヘアドライヤー','ドライヤー','ホルダー|スタンド|交換用|ペット用',2500),
  shelf('hair-irons','ヘアアイロン','ヘアアイロン','ヘアアイロン|ストレートアイロン|カールアイロン','ケースのみ|ホルダー',2000),
  shelf('shavers','電気シェーバー','電気シェーバー 本体','シェーバー|電気カミソリ','替刃|替え刃|交換用|カバー|洗浄液',2500),
  shelf('beauty-devices','美顔器・スチーマー','美顔器','美顔器|スチーマー','カバー|交換用',4000),
  shelf('skincare','スキンケア','スキンケア','美容液|化粧水|乳液|クレンジング|クリーム|スキンケア','ペット',800),
  shelf('haircare','ヘアケア','シャンプー トリートメント','シャンプー|トリートメント','ペット|犬用|猫用',800),
  shelf('makeup','メイクアップ','ファンデーション','ファンデーション|フェイスパウダー|化粧下地','ケースのみ',1000),
 ]),
 department('food','食品・お菓子','🍴',[
  shelf('snacks','お菓子・スイーツ','お菓子 詰め合わせ','菓子|スイーツ|クッキー|チョコ|スナック|せんべい|煎餅|駄菓子','ペット',400),
  shelf('rice','お米','白米 5kg','白米|無洗米|精米|米 5kg|米5kg','容器|ストッカー|保管庫',2000),
  shelf('noodles','麺類','ラーメン うどん そば セット','ラーメン|うどん|そば|パスタ|そうめん','食器|丼|メーカー|調理器',800),
  shelf('prepared-food','惣菜・冷凍食品','冷凍 惣菜','惣菜|餃子|ハンバーグ|唐揚げ|コロッケ|弁当|おかず','容器|タッパー',1000),
  shelf('meat','肉・加工肉','牛肉 豚肉 セット','牛肉|豚肉|鶏肉|ハム|ソーセージ|ステーキ','ペット|ドッグ|犬用',1500),
  shelf('seafood','魚介・水産品','魚介 海鮮 セット','海鮮|魚介|鮭|さけ|ホタテ|ほたて|まぐろ|マグロ|干物|蟹|かに','ペット|ドッグ|犬用',1500),
  shelf('fruit','フルーツ','フルーツ 果物','みかん|りんご|リンゴ|ぶどう|梨|いちご|マンゴー|フルーツ|果物','模型|レプリカ|香水|芳香',1000),
  shelf('water','水・炭酸水','ミネラルウォーター 炭酸水','ミネラルウォーター|炭酸水|天然水','メーカー|生成|浄水器',800),
  shelf('coffee','コーヒー','コーヒー 豆 ドリップ','コーヒー|珈琲','メーカー|ミル|ドリッパー|フィルター|サーバー|カップ',800),
  shelf('tea','お茶・紅茶','お茶 紅茶 ティーバッグ','お茶|紅茶|緑茶|ティー|ほうじ茶','ポット|急須|カップ',800),
 ]),
 department('toys','おもちゃ・ホビー','🧩',[
  shelf('building-blocks','ブロック','レゴ ブロック','レゴ|LEGO|ブロック','収納|ケースのみ',1500),
  shelf('board-games','ボードゲーム','ボードゲーム','ボードゲーム|カードゲーム|人生ゲーム|オセロ','ケースのみ',1000),
  shelf('plastic-models','プラモデル','プラモデル','プラモデル|ガンプラ','工具のみ|塗料|ニッパー|接着剤',1000),
  shelf('figures','フィギュア','フィギュア 完成品','フィギュア','ケース|スタンドのみ|台座のみ',1500),
  shelf('learning-toys','知育玩具','知育玩具','知育|パズル|おもちゃ','収納|ケースのみ',800),
 ]),
 department('watches','時計','⌚',[
  shelf('wristwatches','腕時計','腕時計','腕時計','ベルトのみ|替えベルト|バンドのみ|ケースのみ|工具|電池のみ|修理',2000),
  shelf('smartwatches','スマートウォッチ','スマートウォッチ 本体','スマートウォッチ|Apple Watch|GARMIN','バンド|ベルト|カバー|フィルム|充電器|中古',2500),
 ]),
 department('fitness','フィットネス・スポーツ','🏋️',[
  shelf('dumbbells','ダンベル・筋トレ','ダンベル','ダンベル|バーベル','ラックのみ|スタンドのみ',2000),
  shelf('yoga','ヨガ・ストレッチ','ヨガマット','ヨガマット|ストレッチマット','ケースのみ',1000),
  shelf('fitness-bikes','フィットネスバイク','フィットネスバイク','フィットネスバイク|エアロバイク|スピンバイク','カバー|マットのみ|中古',15000),
  shelf('treadmills','ランニングマシン','ランニングマシン','ランニングマシン|ルームランナー|ウォーキングマシン','マットのみ|カバー|中古',18000),
  shelf('sportswear','スポーツウェア','スポーツウェア トレーニング','ウェア|シャツ|パンツ|ジャージ','ペット',1000),
 ]),
 department('stationery','文房具・事務用品','✏️',[
  shelf('pens','ペン・筆記具','ボールペン','ボールペン|シャープペン|万年筆','替芯のみ|替え芯のみ|リフィルのみ',400),
  shelf('notebooks','ノート・手帳','ノート 文具','ノート|手帳','ノートパソコン|ノートPC|ケース|カバーのみ',400),
  shelf('files','ファイル・収納','クリアファイル 文具','ファイル|バインダー','ネイル|爪',400),
  shelf('desk-tools','デスク小物','文具 ペンケース','ペンケース|筆箱|ペン立て|ペンスタンド','ドライバー',500),
  shelf('calculators','電卓','電卓','電卓','カバーのみ|ケースのみ',700),
 ]),
 department('bags','バッグ・旅行用品','🎒',[
  shelf('backpacks','リュック','リュック','リュック|バックパック','カバーのみ|雨よけのみ',1500),
  shelf('shoulder-bags','ショルダーバッグ','ショルダーバッグ','ショルダー|サコッシュ','ストラップのみ|ベルトのみ',1500),
  shelf('business-bags','ビジネスバッグ','ビジネスバッグ','ビジネスバッグ|ブリーフケース','ストラップのみ',2500),
  shelf('suitcases','スーツケース','スーツケース','スーツケース|キャリーケース','カバー|キャスターのみ|交換用',4000),
 ]),
 department('fashion','ファッション・靴','👟',[
  shelf('menswear','メンズ服','メンズ シャツ','シャツ|ジャケット|ニット|パーカー','レディース|犬用',1000),
  shelf('womenswear','レディース服','レディース ブラウス','ブラウス|シャツ|ワンピース','メンズ|犬用',1000),
  shelf('sneakers','スニーカー','スニーカー','スニーカー','クリーナー|シューキーパー|収納|インソールのみ',2000),
  shelf('wallets','財布・小物','財布','財布|ウォレット|コインケース','補修|修理',1500),
 ]),
 department('home','家具・キッチン','🪑',[
  shelf('cookware','鍋・フライパン','フライパン','フライパン|鍋','収納|スタンド|取っ手のみ|ふたのみ',1500),
  shelf('tableware','食器・カップ','マグカップ','カップ|マグ|食器|プレート','カップ麺|コーヒー豆',700),
  shelf('bedding','寝具','掛け布団','布団|ふとん|寝具','カバーのみ|圧縮袋|収納袋',3000),
  shelf('home-storage','収納家具','収納 チェスト','チェスト|収納棚|キャビネット|ラック','カバー|部品のみ',3000),
  shelf('office-chairs','デスクチェア','デスクチェア','チェア|椅子|イス','カバー|キャスターのみ|脚のみ',4000),
  shelf('lighting','照明','LED シーリングライト','シーリングライト|ペンダントライト|デスクライト','リモコンのみ|カバーのみ',2000),
 ]),
 department('daily','日用品','🧺',[
  shelf('laundry-detergent','洗濯洗剤','液体 洗濯洗剤 詰め替え','洗濯|衣料用|アタック|アリエール|ナノックス|NANOX|ランドリー','食器|台所|柔軟剤|ジェルボール|パーフェクトスティック|洗剤シート',500),
  shelf('tissues','ティッシュ・紙類','ティッシュ トイレットペーパー','ティッシュ|トイレットペーパー','ケースのみ|ホルダー|収納',700),
  shelf('cleaning-tools','掃除用品','掃除 モップ','モップ|ワイパー|ブラシ|掃除','洗顔|歯ブラシ|化粧|メイク',500),
  shelf('towels','タオル','タオル セット','タオル','ペーパータオル|ハンガー|ラック|干し',500),
 ]),
 department('pets','ペット用品','🐾',[
  shelf('pet-wipes','ウェットシート','ペット ウェットシート','ウェット|ウエット','ケースのみ',500),
  shelf('dog-food','ドッグフード','ドッグフード','ドッグフード|犬用|成犬|幼犬','食器|ボウル|保存容器|ストッカー',1000),
  shelf('cat-food','キャットフード','キャットフード','キャットフード|猫用|成猫|子猫','食器|ボウル|保存容器|ストッカー',1000),
  shelf('pet-beds','ペットベッド','ペット ベッド','ベッド|クッション|マット','カバーのみ',1000),
 ]),
 department('outdoors','アウトドア・防災','🏕️',[
  shelf('tents','テント','キャンプ テント','テント','タープのみ|ペグ|補修|ポールのみ|グランドシート',4000),
  shelf('sleeping-bags','寝袋','寝袋','寝袋|シュラフ','カバーのみ|収納袋のみ',2000),
  shelf('camping-chairs','アウトドアチェア','アウトドア チェア','チェア|椅子|イス','カバー|交換用',1500),
  shelf('lanterns','ランタン','LED ランタン','ランタン','ケースのみ|カバー|交換用',1500),
  shelf('portable-power','ポータブル電源','ポータブル電源 本体','ポータブル電源','カバー|ケース|ケーブルのみ|中古',15000),
 ]),
]
CATEGORIES=[c for d in DEPARTMENTS for c in d['children']]
BY_KIND={c['key']:c for c in CATEGORIES}
BY_DEPARTMENT={d['key']:d for d in DEPARTMENTS}

def normalized_kind(item):
    kind=item.get('kind','')
    if kind=='monitor' and re.search(r'ゲーミング|gaming',item.get('title',''),re.I):return 'gaming-monitor'
    return kind

def eligible_title(title,kind):
    c=BY_KIND.get(kind)
    if not c or re.search(r'ふるさと納税|返礼品|寄附金',title):return False
    return bool(re.search(c['accept'],title,re.I)) and not (c['exclude'] and re.search(c['exclude'],title,re.I))

def public_category(c):
    d=BY_DEPARTMENT[c['department']]
    return {k:c[k] for k in ('key','name','file','department')}|{'department_name':d['name'],'department_file':d['file']}

# IDs resolved from Rakuten's published genre directory, not guessed.
import json
from pathlib import Path
_GENRES=json.loads((Path(__file__).parent/'rakuten_genres.json').read_text())
_ROOTS={'pc':'パソコン・周辺機器','gaming':'テレビゲーム','appliances':'家電','cameras':'カメラ・ビデオカメラ・光学機器','mobile':'スマートフォン・タブレット','audio':'オーディオ','beauty':'美容・コスメ・香水','food':'食品','toys':'おもちゃ','watches':'腕時計','fitness':'スポーツ・アウトドア','stationery':'文房具・事務用品','bags':'バッグ・小物・ブランド雑貨','fashion':'靴','home':'インテリア・寝具・収納','daily':'日用品雑貨・文房具・手芸','pets':'ペット・ペットグッズ','outdoors':'スポーツ・アウトドア'}
_SPECIFIC={'monitor':'ディスプレイ','gaming-monitor':'ディスプレイ','gaming-headsets':'ゲーム用機器','televisions':'テレビ','hair-dryers':'美容・健康家電','hair-irons':'美容・健康家電','shavers':'美容・健康家電','beauty-devices':'美顔器・スチーマー','snacks':'スイーツ・お菓子','water':'水・ソフトドリンク','coffee':'コーヒー','tea':'お茶・紅茶','plastic-models':'ホビー','figures':'ホビー','smartwatches':'スマートウォッチ本体','menswear':'メンズファッション','womenswear':'レディースファッション','wallets':'財布・ケース','cookware':'キッチン用品・食器・調理器具','tableware':'キッチン用品・食器・調理器具','lighting':'ライト・照明器具','portable-power':'防災関連グッズ'}
for _c in CATEGORIES:
    _c['genre_id']=_GENRES.get(_SPECIFIC.get(_c['key'],_ROOTS[_c['department']]),0)
    if _c['key']=='noodles':_c['query']='麺類 セット'
    if _c['key']=='meat':_c['query']='肉 詰め合わせ'
    if _c['key']=='water':_c['query']='炭酸水'
    if _c['key']=='coffee':_c['query']='コーヒー'
    if _c['key']=='tea':_c['query']='紅茶 ティーバッグ'
