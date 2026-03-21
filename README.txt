このZIPは、現時点での統合版です。

含まれるもの
- Google Sheets 接続
- Dashboard / APR / Cash / Admin / Help ページ
- SmartVault mobile OCR
- 3領域OCR
- OCR座標のHelp画面保存
- 本日APR重複防止
- 本日APRリセット
- 任意のLINE送信

未実装 / 未検証
- SmartVault PC OCR
- Compound_Timing 本番実装
- 管理者A〜D namespace 完全切替
- 本番LINE文面の最終整形
- 全実環境での動作検証

必要なSecrets
[gcp_service_account]
...

[ocrspace]
api_key = "..."

[line.tokens]
A = "..."
