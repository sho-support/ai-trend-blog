# note下書き自動入力

このツールは、Private Repo `ai-trend-private` の最新 `note_publish_packages` を読み、
noteの投稿画面へタイトルと本文を自動入力します。

## 安全設計

- 公開ボタンは押しません
- 有料ライン・価格・最終プレビューは人が確認します
- noteのログイン情報をGitHub Actionsへ保存しません
- 初回だけブラウザでnoteへログインします
- 以後は専用ChromeプロファイルをローカルPCに保存します

## 事前準備

### 1. GitHub認証

どちらか一つ。

- GitHub CLIで `gh auth login` 済みにする
- またはWindows環境変数 `NOTE_BOT_GITHUB_TOKEN` に、`ai-trend-private` のContents read権限だけを持つFine-grained tokenを設定

### 2. 実行

`start_note_bot.bat` をダブルクリック。

初回は専用Chromeが開くのでnoteへログインします。

## 自動で行うこと

1. Private Repoの最新noteパッケージを取得
2. title.txtを取得
3. free_part.txt / paid_part.txtを取得
4. MarkdownをHTML化
5. noteの投稿画面を開く
6. タイトルを入力
7. 本文をリッチテキストとして貼り付け

## 手動で残すこと

1. 「=== ここでNOTEの有料ラインを設定 ===」の位置に有料ラインを設定
2. マーカー文字を削除
3. 販売価格を確認
4. プレビュー
5. 公開

note側の画面仕様が変わった場合はセレクタ修正が必要です。
