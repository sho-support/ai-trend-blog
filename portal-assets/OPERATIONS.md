# トクサーチ / マチより / モノより 運用引き継ぎ

更新: 2026-10-30

## 収益化のゴール
実際の売上・利益を発生させる。記事数やデザインだけをKPIにしない。GA4イベント portal_outbound_click → アフィリエイト管理画面の承認売上 → API運用費を測る。

## 3サイト
- /deals/: 公式キャンペーン・クーポン確認（16件、楽天/Yahoo!/Amazon/Qoo10/無印/ユニクロ/LOHACO/ヨドバシ）
- /events/: 都道府県/地方/ジャンルでイベントを探す（47都道府県のフィルタ、開催情報は公式で確認済みの地域のみ18件（2026-10-30時点で8都道府県））。全47県のイベントが揃ったとは表示しない。
- /products/: 商品ジャンルの比較テーマ（17件（うち実在商品3件））。A8.netの承認済み広告リンクは現在0件。
- /deals/*.html: 公式情報に基づく買い物ガイド3本。

現在は同じ GitHub Pages リポジトリ内の独立ディレクトリ。既存 AI Trend Blog のトップページ・生成プログラムには変更なし。
注: GitHub Pages は本格的なオンライン事業運営向けホスティングではないため、広告収益を本格化する前に専用ホスティング/ドメイン移行を検討する。

## 楽天 公式API 自動更新（APIキーを設定した場合のみ）
ワークフロー: .github/workflows/commerce-rakuten.yml
コード: portal-tools/refresh_rakuten.py
定期: JST 06:00、Gemini APIは使わない。
GitHub Secrets:
- RAKUTEN_APP_ID
- RAKUTEN_ACCESS_KEY
- RAKUTEN_AFFILIATE_ID （任意・楽天アフィリエイトを使う場合）

登録先: https://github.com/sho-support/ai-trend-blog/settings/secrets/actions
楽天公式API資料: https://webservice.rakuten.co.jp/documentation/ichiba-item-search-20260701

未設定時は既存JSONを上書きせず正常にスキップ。キーや秘密情報を公開リポジトリに記載してはならない。APIデータは24時間程度で自動表示終了。APIが示した価格は必ず取得日を明記し、最安値・割引保証はしない。

## A8.net
公式ヘルプ: https://support.a8.net/a8/as/faq/manual/how_to_post.php

現時点で管理画面への直接ログイン・提携案件の自動取得は未実装。GitHub内にA8ユーザーIDやパスワードを保存しない。
公開先サイトのA8メディア登録・案件への提携承認・掲載サイト許可を確認する。
広告主の広告コード・画像を勝手に改変しない。
広告主が許可した「フリー素材リンク」だけは portal-assets/a8-approved.json に次の形式で追加できる。
広告主の提供した有効なフリー素材リンクのみを url に使用する。通常のテキスト/バナー素材をそのまま流用してリンクだけ切り抜いてはいけない。

{
  "updated_at": "2026-10-30",
  "items": [
    {
      "id": "a8-partner-approved-001",
      "title": "広告プログラムで承認済みの商品・サービス名",
      "category": "日用品・生活",
      "shop": "提携済み広告主",
      "description": "確認済みの製品特徴・条件",
      "url": "https://広告主・A8が発行した正式なフリー素材URL",
      "approved": true,
      "material_type": "free_link",
      "verified": "2026-10-30",
      "icon": "🎁"
    }
  ]
}

上は説明用のダミー値。実際の広告URL・商品・承認状況が確認できるまで公開データに追加してはいけない。
現状の portal-assets/a8-approved.json の items は空リスト。秘密のログイン情報を要求・保存する方式にしない。

## イベントの拡張
地域は47都道府県から選べるが、初期イベントは北海道・宮城・東京・大阪・京都のみ。公式自治体カレンダー・主催者による公開情報を確認し、新規イベントの日時・会場・日程変更・中止を掲載前に検証。無断の画像や非公開APIへのスクレイピングは使わない。

初期情報源:
- https://www.visit-hokkaido.jp/event/index.html
- https://www.sentabi.jp/
- https://www.my.metro.tokyo.lg.jp/event/
- https://osaka-info.jp/event/semba-ichoumatsuri2026/
- https://www.city.kyoto.lg.jp/main/event1/next.html

## 分析と最適化
既存GA4 G-J5ZDLF30CSを3ポータルに設定。外部商品リンクのクリックで portal_outbound_click イベント発火。
クリック数は売上ではない。A8.net等の成果承認実績を別途照合。
初期の判断基準: 集客数、検索流入、リンククリック率、成果承認件数、実質売上、API運営費。

## 未完了
- A8.net の実アカウントで提携済み案件を確認・掲載すること
- 楽天公式APIキーと必要ならAffiliate IDを設定
- 公開URLの外部実機表示・GitHub Pagesデプロイ状態の確認
- 47都道府県のイベントデータの実掲載（現時点で網羅していない）
- Amazonの価格・画像等を正規API/許可された手段以外で自動取得しない
- 複数モール比較は商品の容量、送料、価格更新時刻、会員特典を揃えて初めて行う


## 2026-10-30 追加の仕上げ
- events/index.html: 公式情報再検証・掲載不確実な2件を外し、青森・佐賀・大分のイベントを追加。計18件・8都道府県（全国47都道府県のUIフィルタは有効）
- products/index.html: 実在商品のメーカー・販売店公式情報にリンクした3カードを追加、計17件
- portal-assets/app.js: イベント期間指定、候補外の全国イベント公式カレンダーへの案内、Rakuten API画像、23時間以内の価格表示期限、外部リンククリック計測
- portal-tools/refresh_portals.py: 日付終了イベントや終了セールが静的HTMLに残らないよう毎日再生成
- .github/workflows/refresh-portals.yml: 毎日04:15 JST、Geminiなし
- portal-tools/test_portals.py: JSON・日程・HTML・JS構文などの自動検査（本番ワークフロー成功未確認）
- 価格データのキャッシュは23時間以内。楽天APIデータの免責と取得日時をページ内に明記する（API登録後要最終検査）
- portal-tools/build_commercial_site.py と netlify.toml: 3サイトだけをdist/へ取り出してNetlifyの商用ホスティングへ移す準備
- GitHub PagesとVercel Hobbyは収益目的の本番ホスティングに不適。Netlify Freeは商用サイト利用可能というサポート案内あり（最新規約は移行時に再確認）

## 最終的な未接続項目
1. A8.netのメディア登録と、提携承認済み案件の取得。実アカウントへのアクセス権が必要。現在A8広告枠は0件。
2. 楽天のアプリID、アクセスキー、アフィリエイトIDの設定。現状商品フィードは0件。収益化に直結するので優先度高。
3. Netlifyアカウントを接続し、GitHubリポジトリから商用デプロイする。現時点でNetlifyへは未デプロイ。
4. 47都道府県のイベント情報の本格収集。現状8都道府県の18件のみ。確認していないイベントを大量掲載しない。
5. 新ホストの外部表示・GA4クリック・A8成果承認の実機検証。

## 2026-10-31 楽天API接続・商品比較記事の稼働実績

- Rakuten Ichiba API: ユーザーがGitHub Secretsに RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY / RAKUTEN_AFFILIATE_ID を設定。
- GitHub Actions「Refresh Commerce Product Feed」 #5 成功（https://github.com/sho-support/ai-trend-blog/actions/runs/41083604065）。
- 2026-10-31 00:45 JST の取得では24件中24件が楽天正規アフィリエイトURL。price_yen・seller・image・expires_atも保持。取得失敗カテゴリ0件。
- API接続と正規URL取得の成功は「購入発生」「報酬承認」を意味しない。
- 商品データの取得は原則毎朝06:00 JST、Gemini API不要。表示期限は取得から23時間。
- 新規SEO記事（自動ではなく今回手動で内容を作成した固定ガイド）7本：
  products/okashi-matome.html
  products/okome-5kg.html
  products/mobile-battery-monitors.html
  products/nichiyohin-matome.html
  products/sneakers.html
  products/skincare.html
  products/pet-supplies.html
- 7つの固定ガイドは文章を毎日作り直さず、表示する商品・価格・出店者・報酬リンクのみ公式APIデータを自動更新する設計。API失敗・期限切れなら商品は非表示。
- portal-assets/guide.js で価格の期限確認、楽天商品リンクのPR表示、クリックのGA4イベントを実装。
- portal-assets/app.js で楽天/提携商品に rel=sponsored を付与。
- 全7記事へ products/index.html からリンク。dealサイトから主要3記事へリンク。サイトマップも7記事を収録。
- テストスクリプト portal-tools/test_portals.py に7記事・PR表記・商品URL・画像・JS構文検査を追加。商品更新workflow #5で成功。
- GitHub Pagesデプロイ 511 https://github.com/sho-support/ai-trend-blog/actions/runs/41084112241 は成功。外部ブラウザ実機のクリック表示は未確認。
- Rakuten affiliate の掲載サイト登録 statusは利用者の画面で未確認。A8.net 承認済み実案件は引き続き0件。商用ホストへの移転（Netlify）・成果承認データ連携は未完了。
- 特価・最安値・レビュー実体験を装った表示は禁止。楽天API表示価格は条件により変わるためリンク先の店舗条件を案内。
