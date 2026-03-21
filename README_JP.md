# APR資産運用管理システム（分割版 完全パッケージ）

このパッケージは、元の `app.py` をベースに、機能を維持したままクラス単位で分割した版です。

## 目的
- 後からの追加・修正をしやすくする
- 修正場所をすぐ特定できるようにする
- 元コードの構造を壊さずに整理する

## 起動方法
```bash
cd apr_system
streamlit run app.py
```

## 主な修正先
- APR画面: `ui/apr.py`
- 入出金画面: `ui/cash.py`
- 管理画面: `ui/admin.py`
- ダッシュボード: `ui/dashboard.py`
- ヘルプ: `ui/help.py`
- 計算ロジック: `engine/finance_engine.py`
- Sheets入出力: `services/gsheet_service.py`
- Repository: `repository/repository.py`
- 認証: `core/auth.py`
- 共通関数: `core/utils.py`
- 外部API: `services/external_service.py`
- 全体制御: `controller/app_controller.py`

## 収録ファイル
- `FULL_CODE_REFERENCE.py`
  - 分割後コードを1本に連結した参照用ファイル
- `CLASS_MAP.txt`
  - どのクラスがどこにあるかの一覧
- `ORIGINAL_REFERENCE.txt`
  - 元コード参照メモ

## 補足
- 実行入口は `app.py` です。
- 将来の機能追加は、画面ごとの `ui/` とロジック側 `engine/`, `repository/`, `services/` に分けて行えます。
