# APR資産運用管理システム（分割版）

## 構成
- `app.py` : 起動入口
- `config.py` : 定数定義
- `core/` : 共通処理（認証・ユーティリティ）
- `services/` : 外部接続（LINE / OCR / Google Sheets）
- `repository/` : シート読み書き
- `engine/` : APR計算ロジック
- `store/` : セッション / データ再読込
- `ui/` : 画面別UI
- `controller/` : 画面遷移と起動制御

## 起動
```bash
cd apr_system
streamlit run app.py
```

## 追加・修正しやすい場所
- OCR関連: `services/external_service.py`, `ui/apr.py`, `ui/help.py`
- LINE送信関連: `services/external_service.py`, `ui/apr.py`, `ui/cash.py`, `ui/admin.py`
- APR計算式: `engine/finance_engine.py`
- シート列追加: `config.py`, `repository/repository.py`
- セッション関連: `config.py`, `store/datastore.py`

## この版で追加した整理
- 画面ごとに UI を分離
- 計算ロジックを分離
- Google Sheets 処理を分離
- 後から機能追加しやすい構成へ整理
- 元コードの機能を維持しやすい責務分離
