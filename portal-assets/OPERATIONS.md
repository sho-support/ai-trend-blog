# TrendBlog / 買い物・イベントポータル 引き継ぎ

更新：2026-10-31（日本時間）

## 目的と判断基準

目的は収益。記事数・生成成功・リンク取得は売上ではない。記事と商品を読者の用途に合わせ、商品クリック→楽天等の成果承認→運用費を含めた利益で判断する。

ユーザーは「AI特有の読む気を失う文章」を避けること、手作業を最小限にして収益化へ進めることを明示している。既存の楽天API登録・3つのSecrets設定をやり直す依頼はしない。キーの値をログ・コードへ出さない。

## 既存の構成

リポジトリ：`sho-support/ai-trend-blog`、既定ブランチ `main`。

- `/`：AI Trend Blog（AIニュース）。既存トップのデザインは維持。
- `/deals/`：トクサーチ（公式セール・クーポン情報）。編集掲載16件。
- `/products/`：モノより（写真から探す商品カテゴリー）。8ジャンル・商品詳細27ページ。
- `/events/`：マチより（イベント検索＋宿泊候補）。編集掲載18件・8都道府県。47都道府県の検索UIがあることと全国を網羅したことを混同しない。
- 非公開の有料note原稿：`sho-support/ai-trend-private`。公開ポータル用ビルドには含めない。

現行URL： https://sho-support.github.io/ai-trend-blog/

## 2026-10-31の再設計：ユーザーの明示した優先事項

説明が多く商品が下に埋まっている、ジャンルが混在する、大きな見出しと不自然な改行が読みにくい、という指摘を受けて全面的に組み替えた。以前の長文ガイド・計算機・仮の比較表を入口へ戻さない。

- 商品トップは8ジャンルへの入口だけ。商品カードを混在させない。
- 各ジャンルに該当する商品だけを表示。写真→短い商品名→商品固有の紹介1文→価格→詳細。
- 商品詳細は写真を先に置き、短い見出し・紹介・価格・購入ボタンを表示。人数と個数の計算、一般論の選び方、機能バッジの重複、長い免責の前置きを足さない。
- 大型の暗色ヒーロー、英語ラベル、強制改行、タイトルの部分的な巨大文字を廃止。
- セールとイベントも一覧・絞り込みを最初に置く。価格蓄積状況や内部運用の説明をトップで読者に見せない。

正本は `portal-tools/build_storefront.py`、編集コピーは `portal-tools/product_copy.json`、セール・イベントの元データは `portal-tools/portal_content.json`。`build_guides.py` と `refresh_portals.py` は互換入口として同じビルダーを呼ぶ。古い `guide_content.py` / `guide.js` は現行商品のHTMLから参照しない。

8ジャンルのURL：

- `products/okashi-matome.html`：お菓子・スイーツ
- `products/okome-5kg.html`：お米
- `products/work-monitor.html`：モニター
- `products/mobile-battery.html`：モバイルバッテリー
- `products/nichiyohin-matome.html`：洗濯洗剤
- `products/sneakers.html`：スニーカー
- `products/skincare.html`：スキンケア
- `products/pet-supplies.html`：ペット用品

`products/mobile-battery-monitors.html` は家電2ジャンルへの入口として維持。個別商品は `products/items/<id>.html`。商品更新ワークフローで新しい商品IDのページを生成し、サイトマップへ追加する。

写真・価格は `catalog.js` が有効なフィードを確認してから表示する。楽天の公式画像を使い、実測・体験談・架空の値引きやランキングを作らない。APIの商品名の情報だけから短い紹介を書く。新規IDの短い商品名は、途中にある宣伝用の【…】も除去して32文字程度に抑える。切り詰め済みのdisplay_titleより元のtitleを優先し、閉じていない括弧を表示しない。広告リンクにはPRと `rel=sponsored`。共通の期限・分類・日付・計測処理は `commerce.js`。

## 楽天の接続と自動更新

既存Secrets：

- `RAKUTEN_APP_ID`
- `RAKUTEN_ACCESS_KEY`
- `RAKUTEN_AFFILIATE_ID`

商品：`.github/workflows/commerce-rakuten.yml` / `portal-tools/refresh_rakuten.py`。
宿泊：`.github/workflows/commerce-travel.yml` / `portal-tools/refresh_travel.py`。

更新時刻は今回から商品06:00・18:00、宿泊06:20・18:20（日本時間）。毎日1回では23時間の表示期限より更新間隔が長かったため、1日2回に変更。どちらもGeminiを呼ばない。

商品検索は用途キー `kind` を出力する。洗濯洗剤は「液体 洗濯洗剤 詰め替え」で検索し、衣料用を確認。4Kと3440×1440のモニター検索を分け、重複コードは排除。型番の末尾・選択する規格・送料を揃えた商品ランキングではない。

既存の接続成功実績（今回以前）：

- 商品： https://github.com/sho-support/ai-trend-blog/actions/runs/41083604065
- 今回の更新後、2026-10-31 02:46 JSTに27件を取得。内訳はモニター6件、ほか7用途が各3件。その後、ボール型を除外して液体洗剤を再取得済み。
- 宿泊： https://github.com/sho-support/ai-trend-blog/actions/runs/41085961921

`rakuten-feed.json` / `travel-feed.json` の有効期限は23時間。期限切れ・不正な期限・取得失敗では古い価格を売るために残さない。取得した紹介URLと承認売上は別。

価格履歴：`portal-tools/track_prices.py` / `portal-assets/price-history.json`。
過去30日内の別日3回以上の記録があり、過去観測最低価格より5%以上低い場合のみ観測上の低下を表示。商品ページの選択肢・送料・クーポンは別条件で、楽天全体の最安値や同一規格の値引きは保証しない。

公式資料： https://webservice.rakuten.co.jp/documentation/ichiba-item-search
楽天の公式クレジットをAPI情報の利用ページに保持する。

## 元のAIニュース自動生成

最新確認した定期実行は、Gemini APIの月間利用上限で停止していた。

https://github.com/sho-support/ai-trend-blog/actions/runs/41057068317

`gemini_budget_guard.py` は上限時にモデル切替・再試行せず停止する。今回、Google AI Studio側の課金設定・上限・APIキーは変更していない。

今回の `generate_article.py` 変更：全記事に同じ8見出しと1,800〜3,000文字を要求する方式を廃止。話題に合う2〜5見出し、事実の量に合わせた簡潔な本文、結論からの導入、内容のない締めを省く指示へ変更。

`article_quality.py` は実行コード、未確認の外部リンク、重複段落、構造不足などを検出する。自動の事実検証や読み物としての品質を保証するものではない。LLMをスタブにした実コード検証は実施できるが、上限解消後の本番記事生成は未確認。ニュース生成で固定ガイドの `dateModified` を当日へ変えないようにも修正。

## 検査と公開

基本検査：

```bash
python portal-tools/build_storefront.py
python portal-tools/test_portals.py
python portal-tools/build_commercial_site.py
```

テスト内容：8ジャンルの分離・27商品ルート・短いコピー・ローカル参照・PR・楽天クレジット、JS構文、用途の誤分類、日曜・月跨ぎ、期限切れの商品表示／クリック、商品別の計測。

`test_commerce.js` はNode標準機能のみ。旧計算関数の回帰検証も残るが、商品画面へ計算機を戻す根拠にはしない。`test_article_quality.py` はLLMをスタブにして既存の品質制御と課金上限の伝播を検証する。課金APIは呼ばない。

2026-10-31：ブラウザーで8ジャンルを巡回し、27商品詳細すべてで写真・購入リンク・PC画面のはみ出しを検査済み。スクリーンショットを目視し、写真の切れ・カテゴリー名の孤立した折り返し・日本語見出しの折り返しを修正。320px・390px・768px・PCの表示と、セール／イベントの地域絞り込みも確認済み。次の変更時も同じ流れを巡回する。DOM検査の合格だけで見た目が良いとは判定しない。ローカルQAは実機や全ブラウザーの保証ではない。

プレビューは `dist` を削除・作り直した後に再起動が必要になる場合がある。内部QA用ファイルやローカル `.openai/hosting.json` をコミットしない。

## 計測と未完了

GA4：`G-J5ZDLF30CS`。商品クリックの `portal_outbound_click` に `portal_kind`、`item_id`、`guide_slug`（旧ガイドのみ）、ジャンルを付与。完全な広告URLや計算機入力は送信しない。ローカルプレビューを本番のGA4計測対象から除外。

未完了を「完成済み」としない：

1. 商用ホストへの本番移行。Netlify用 `netlify.toml` / `build_commercial_site.py` はあるが、この会話でNetlifyアカウントへの接続・デプロイは確認できていない。既存の公開先は維持し、別のホストへ勝手に登録しない。
2. 楽天アフィリエイトの掲載サイト登録状況、実クリックのGA4への受信、楽天での成果発生・承認は未確認。
3. このポータルに登録済みのA8広告素材は `a8-approved.json` の0件。他の媒体での提携状況と混同しない。承認済みの正式素材と対象媒体を確認してから追加する。
4. GSC Wizardは契約が有効でないため実データを読めなかった。未取得の流入・売上数値を推測で埋めない。費用の追加や新規契約は行っていない。
5. AIニュースの本番再開にはGemini側の月間利用上限状態の確認が必要。
6. イベントの全国網羅は未完了。確認したイベントだけを掲載する。

次の判断は、商用公開先・掲載媒体の登録を確かめたうえで、実際にクリックされた記事／商品のテーマへ集中すること。現時点の月収見込みや売上は分かっていない。
