# TrendBlog / 買い物・イベントポータル 引き継ぎ

更新：2026-10-31（日本時間）

## 目的と判断基準

目的は収益。記事数・生成成功・リンク取得は売上ではない。記事と商品を読者の用途に合わせ、商品クリック→楽天等の成果承認→運用費を含めた利益で判断する。

ユーザーは「AI特有の読む気を失う文章」を避けること、手作業を最小限にして収益化へ進めることを明示している。既存の楽天API登録・3つのSecrets設定をやり直す依頼はしない。キーの値をログ・コードへ出さない。

## 既存の構成

リポジトリ：`sho-support/ai-trend-blog`、既定ブランチ `main`。

- `/`：AI Trend Blog（AIニュース）。既存トップのデザインは維持。
- `/deals/`：トクサーチ（公式セール・クーポン情報）。編集掲載16件。
- `/products/`：モノより（購入ガイド＋楽天商品の候補）。ガイド9本。
- `/events/`：マチより（イベント検索＋宿泊候補）。編集掲載18件・8都道府県。47都道府県の検索UIがあることと全国を網羅したことを混同しない。
- 非公開の有料note原稿：`sho-support/ai-trend-private`。公開ポータル用ビルドには含めない。

現行URL： https://sho-support.github.io/ai-trend-blog/

## 今回の文章・導線の変更

`portal-tools/guide_content.py` が編集本文の正本。`portal-tools/build_guides.py` でHTML・一覧の入口・サイトマップを再生成する。日々のデータ更新で本文や編集日を勝手に書き換えない。

9本のURL：

- `products/okome-5kg.html`：送料込み1kg単価。
- `products/okashi-matome.html`：配布人数・個数・送料。
- `products/nichiyohin-matome.html`：洗濯洗剤の1回当たり費用。食器用洗剤を混ぜない。容量単位で計算する記事のため、ジェルボール等も一覧から外す。
- `products/mobile-battery.html`：バッテリーの用途・出力・容量。
- `products/work-monitor.html`：27型4Kと34型UWQHDの解像度・設置・端子。
- `products/mobile-battery-monitors.html`：従来URLを維持した家電ガイドの入口。
- `products/sneakers.html`：サイズ・販売店別の返品条件。
- `products/skincare.html`：セット内容と同じ規格の比較。
- `products/pet-supplies.html`：ペット用ウェットシートの寸法・枚数・単価。

お米・お菓子・洗剤・ペット用シートの4記事にブラウザー内の比較計算機を設置。送料とクーポンを含め、洗剤は1回の使用量を掛ける。入力値を保存・送信しない。例は架空と表示し、実商品価格や性能テストとして使わない。

`portal-assets/commerce.js` に価格の有効期限、楽天リンクの判定、用途別分類、比較計算、日曜の「今週末」判定を共通化。バッテリーの「ディスプレイ搭載」をモニターと誤認しない。期限切れは再表示時・定期確認・クリック時にも判定する。

固定の通販トップへ飛ばすだけだった商品テーマの入口は、対応する購入ガイドへのリンクに変更。広告である商品リンクにはPRと `rel=sponsored` を付ける。実測・体験談・架空の値引きを作らない。

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
- 今回の更新後、2026-10-31 02:46 JSTに27件を取得。内訳はモニター6件、ほか7用途が各3件。後続の調整ではボール型を除外して液体洗剤を再取得する。
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
python portal-tools/build_guides.py
python portal-tools/refresh_portals.py
python portal-tools/test_portals.py
python portal-tools/build_commercial_site.py
```

テスト内容：9記事のリンク・アンカー・PR・構造、各フィード、JS構文、単価・濃縮度・不正入力、用途の誤分類、日曜・月跨ぎ、有効期限を過ぎたクリック、記事／商品別のイベント情報。

`portal-tools/test_commerce.js` はNode標準機能だけを使う。
`portal-tools/test_article_quality.py` は実際の生成関数を切り出してスタブで動かし、自然な見出しの受理・重複原稿の修正・上限の伝播を検証。課金APIは呼ばない。

PCブラウザーで9記事の描画を確認。320px・390px幅の本文／計算機を確認。お米796円/kg対814円/kg、洗剤30円/回対20円/回の架空例とゼロ量エラーを実画面で確認。ローカルQAは実機スマホや全ブラウザーの保証ではない。

プレビューは `dist` を削除・作り直した後に再起動が必要になる場合がある。内部QA用ファイルやローカル `.openai/hosting.json` をコミットしない。

## 計測と未完了

GA4：`G-J5ZDLF30CS`。商品クリックの `portal_outbound_click` に `portal_kind`、`item_id`、`guide_slug`、ジャンルを付与。完全な広告URLや計算機入力は送信しない。ローカルプレビューを本番のGA4計測対象から除外。

未完了を「完成済み」としない：

1. 商用ホストへの本番移行。Netlify用 `netlify.toml` / `build_commercial_site.py` はあるが、この会話でNetlifyアカウントへの接続・デプロイは確認できていない。既存の公開先は維持し、別のホストへ勝手に登録しない。
2. 楽天アフィリエイトの掲載サイト登録状況、実クリックのGA4への受信、楽天での成果発生・承認は未確認。
3. このポータルに登録済みのA8広告素材は `a8-approved.json` の0件。他の媒体での提携状況と混同しない。承認済みの正式素材と対象媒体を確認してから追加する。
4. GSC Wizardは契約が有効でないため実データを読めなかった。未取得の流入・売上数値を推測で埋めない。費用の追加や新規契約は行っていない。
5. AIニュースの本番再開にはGemini側の月間利用上限状態の確認が必要。
6. イベントの全国網羅は未完了。確認したイベントだけを掲載する。

次の判断は、商用公開先・掲載媒体の登録を確かめたうえで、実際にクリックされた記事／商品のテーマへ集中すること。現時点の月収見込みや売上は分かっていない。
