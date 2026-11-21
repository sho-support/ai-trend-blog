# モノより継続集客 運用指示
作成日: 2026-11-16 JST
目的: 購入の判断に役立つ記事を増やし、検索・Xから読者を呼び、確定アフィリエイト報酬につなげる。訪問数や商品数だけを成功にしない。

## 実行範囲と公開経路
- サイト: https://sho-monoyori-review.zodiac-suu.workers.dev/
- 記事: /products/stories/。モノより主力。イベントは集客の優先対象にしない。
- ソース: sho-support/ai-trend-blog。現在の公開ソースは、sho-support/sho-support.github.io の main:.github/workflows/monoyori-live.yml に固定された40桁 ref を必ず確認してから読む。mainの古いテンプレートをそのまま公開しない。
- 実装: improvement branch improve/purchase-guides-event-photos-20261114 の最新を取得し、既存変更を保存して差分編集。公開後は同ホスティングworkflowの固定refを更新して既存チェックを通す。このWorker以外・顧客サイト・DNS・課金は変更しない。
- feed更新は既存の commerce-rakuten.yml、公開と検索通知は monoyori-live.yml の既存処理を活用。別の同機能スケジューラーを重ねない。
- 独立した有料AI/Gemini APIは残高不足により停止中。再開・入金・有料広告の契約はしない。ChatGPT作業内で一次情報に基づき執筆する。

## 編集と配信
- 毎日既存処理の失敗、リンク切れ、古い価格・期限、投稿重複を確認し、修正できるものを修正。
- 月・水・金: 新記事1本を目標。良い口コミと注意点、用途別の違い、総額・単価、写真・出典・更新日・関連商品導線を含める。新規調査が不十分なら既存記事の実質改善を優先し、薄い記事を本数稼ぎで増やさない。
- 火・木・土: 公開確認済みの未紹介記事を優先してXに紹介。1日最大1投稿。直近24時間に別のモノより投稿があれば無理に追加しない。既存記事URLの再紹介は14日以上空け、実質的に新しい見せ方や更新が必要。日曜は集計・改善を優先。
- 初期重点: 食品・手土産、飲料の単価比較、暮らしの便利用品。カテゴリーを無秩序に増やさず読者の購入理由を具体化する。
- 実食・実機使用の捏造、架空の口コミ・点数、全件集計していない声の頻度断定、終了した特売や未確認の開催日は禁止。
- SNS写真はSNS利用が確認された販売店素材のみ。API画像のサイト表示許可をSNS転載許可と混同しない。許可不明なら自作の比較図を使い、商品写真と偽らない。
- X @monoyori_sale、既存Buffer channel_id 6aec855be29c69a1716f545b のみ。既存 BUFFER_API_KEY はGitHub Actionsのsecretで利用し、読み出しやログ出力はしない。ほかのアカウントやDMは対象外。
- 成果物はまずサイトに公開しHTTP200・本文・画像・購入導線・canonicalを確認後、UTM付き記事URLで配信。PR表示必須。既存 publish_water_launch.py / monoyori-water-launch.yml が実績ある原型。これら既存ワンショットのreceiptを消して再送しない。
- 新キャンペーンごとに固有manifest・receiptを持つ。Buffer履歴とreceiptを確認し、一度だけ送信、送信前にattempt_started保存、応答不明は再送せず照合。投稿成功はstatus sentとexternalLink、画像assetを確認。受け付けただけを公開済みと言わない。

## 最初の調査候補（未公開・未検証）
1. お菓子の手土産: 人数別の個数・個包装・配送条件を比較。既存ヨックモック記事の未紹介部分を優先し新たな写真/図解で配信。
2. ブラックフライデー前の比較: 現在応募/購入可能な公式企画だけ確認。開催日・割引率を推測せず、送料・クーポン条件・通常価格の根拠を示す。
3. モバイルバッテリー: 端子/出力/重量/安全情報を公式で確認し、同一条件の候補を比較。既存Anker A1257の回収案内を無視した宣伝はしない。
4. 炭酸水: 同じ容量・本数と送料込み総額を比較。現在価格と計算例を明確に分ける。
5. テント記事: 日よけと宿泊用が一覧で混在するため用途を確認。最安順や星だけで宿泊用と判断しない。

## 測定と報告
- 検索表示/クリック、サイト訪問、販売店へのクリック、確定報酬を別指標で扱う。
- GA4タグの存在≠GA4の受信実績。Search Consoleのサイトマップ送信/IndexNow受理≠インデックス登録。自分の表示確認≠外部流入。QAには ?qa=1 を付ける。
- 2026-11-16時点で新サイトのアクセス数・購入数・確定報酬は未取得。不明を0としない。
- GSC Wizardは以前subscription expired/payment_required。課金契約をしない。利用可能な既存接続で実データを取得できれば比較し、取れなければ明記。毎回同じログイン依頼をしない。
- 毎週日曜に、公開記事/投稿URL、取得できた実績、次の改善を簡潔に報告。重大障害・認証切れは発生時だけ報告。毎日の「確認しました」「該当なし」は通知しない。
- 変更と配信記録をこのrepoの growth/continuous-log/ 日付別JSON/Markdownへ保存。実施済み/未確認/予定を分ける。

## 既知の送信実績
- 2026-11-16: ダンベル記事。growth/story-launch-receipt.json。https://x.com/monoyori_sale/status/2122018958630900092
- 2026-11-16: 炭酸水記事・自作単価図。growth/water-launch-receipt.json。https://x.com/monoyori_sale/status/2122264267973861606
両方の同日再送は禁止。

## 2026-11-16 追加: Pinterestと比較ツール
- 単価比較ツール /products/tools/unit-price。商品代+送料-適用可能値引き、個数、同条件比較。商品一覧と全紹介記事からリンク。Pinterest保存ボタン付き。
- Pinterest用オリジナル縦長図解と初回投稿原稿: growth/pinterest-launch.json、growth/social-assets/unit-price-pinterest.png。
- Metricool brand7401771はSNS接続なしとの応答を確認。Pinterestは未接続・未投稿。接続先 https://app.metricool.com/brands/connections?blogId=7401771 。ユーザーに接続を依頼済みとして扱い、毎日の同じ依頼はしない。既存Pinterestアカウント/ボードが接続され正しいモノより用途と確認できたらこの原稿を使い、公開済みツールを検証後に初回投稿。アカウント新規登録/規約同意/架空ボードIDはしない。
- 接続後は火木土の配信作業にPinterestも含める。X本文をそのまま複製せず、独自の縦長画像と用途別タイトル/説明を作りUTM流入を区別する。同じPin大量反復は禁止。投稿先未接続を投稿成功扱いしない。

## 最新のPinterest運用経路（2026-11-16、前のMetricool案より優先）
- API読取確認: growth/buffer-connection-check.json。既存Buffer接続2件、Pinterest0件。登録歴そのものは不明。
- Metricool新規登録不要。既存Bufferを優先し、本人が https://publish.buffer.com/settings/channels でPinterestを接続。正しいアカウント/ボード確認後に配信。新規費用/トライアルなし。
- 初回単価比較素材: growth/pinterest-launch.json と growth/social-assets/unit-price-pinterest.png。manifest内のMetricool brand_idはBuffer宛先に使わず、実在Buffer channel_id/board_idを取得した専用manifestへ移す。
- 手土産紹介の追加原稿/縦長画像: growth/pinterest-buffer-queue.json と growth/social-assets/gift-check-pinterest.png。未投稿。接続後、重複/鮮度を確認して配信する。
- 公開ツール /products/tools/unit-price のSNSプレビューと保存用画像は縦長図解へ更新済み。2026-11-16公開workflow43884270698成功。
- 接続未完了の同じ依頼を毎日繰り返さない。

## 2026-11-18 投稿履歴の再照合
- 読み取り専用チェックは growth/buffer-post-history.json に保存。送信済み取得は公式APIの status:[sent] と dueAt.start の組み合わせを使用。startDateだけの旧クエリでは既知の送信済み投稿が空配列となったため、空配列を「投稿なし」と判断しない。
- complete / receipt_reconciled を確認し、最新receiptとAPIが一致しない場合は送信せず照合。effective_last_sent_at はAPIと既存receiptの最新を採用。過去receiptは削除しない。
- 2026-11-18 20:06 JSTの照合で最新投稿は11月17日21:38 JST、直近24h制限内。Pinterestは引き続き0接続。これは当日全体の禁止ではなく照合時点の判定。

## 2026-11-21 追加：季節ニュースを楽しめる商品紹介ブログ
- 商品の説明だけでなく、短い季節・地域ニュース、前年や平年との比較、暮らしの実用情報を入口にした読み物を追加する。
- 構成の基本は「確認済みの季節ニュース → 読者の生活で気になること → 選び方・良い点と注意点 → 必要な関連商品や比較ツール」。ニュースと関連が薄い商品を無理に並べない。購入しなくても役立つ情報を含める。
- 初雪なら気象庁・地方気象台の観測発表を確認し、観測地点・発生日・前年日・平年日を区別する。差の日数を実計算し、未確認の「昨日初雪」「例年より早い」は書かない。ユーザーの初雪の例は実際の観測の報告ではない。
- クリスマスなら人数・予算・包装・到着日、寒さなら防寒用品の素材・使う場所・手入れなど、季節から自然につながる購入判断を扱う。イベント開催・セール期間・配送締切は主催者や販売店の一次情報を確認する。
- 公開日が変わっても誤読されないよう、ニュースには具体的な日付と出典リンクを付ける。「昨日」だけの記載は避ける。写真は内容に合う許可済み素材または自作図解を使う。
- ニュース導入を加えても従来の一次情報2件以上、実体験/口コミの捏造禁止、公開検証、SNS配信制限を維持する。新記事1日1本まで。次の編集回から優先して適用する。
