# トクサーチ / マチより / モノより 運用引き継ぎ

更新: 2026-10-30

## 収益化のゴール
実際の売上・利益を発生させる。記事数やデザインだけをKPIにしない。GA4イベント portal_outbound_click → アフィリエイト管理画面の承認売上 → API運用費を測る。

## 3サイト
- /deals/: 公式キャンペーン・クーポン確認（初期16件、楽天/Yahoo!/Amazon/Qoo10/無印/ユニクロ/LOHACO/ヨドバシ）
- /events/: 都道府県/地方/ジャンルでイベントを探す（47都道府県のフィルタ、開催情報は公式で確認済みの地域のみ初期14件）。全47県のイベントが揃ったとは表示しない。
- /products/: 商品ジャンルの比較テーマ（初期14件）。A8.netの承認済み広告リンクは現在0件。
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
