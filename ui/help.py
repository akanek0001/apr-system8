from __future__ import annotations

import pandas as pd
import streamlit as st

from config import AppConfig
from core.auth import AdminAuth
from core.utils import U
from repository.repository import Repository
from services.gsheet_service import GSheetService
from store.datastore import DataStore


class HelpPage:
    def __init__(self, repo: Repository, store: DataStore):
        self.repo = repo
        self.store = store

    def render(self, gs: GSheetService, settings_df: pd.DataFrame) -> None:
        st.subheader("❓ ヘルプ / 使い方")
        st.caption(f"{AppConfig.RANK_LABEL} / 管理者: {AdminAuth.current_label()}")
        st.markdown("""
このアプリは、APR運用の記録、入出金、メンバー管理、LINE通知をまとめて扱う管理システムです。
左メニューの **📊 ダッシュボード / 📈 APR / 💸 入金/出金 / ⚙️ 管理 / ❓ ヘルプ** で画面を切り替えます。
""")
        with st.expander("1. 現在の接続情報", expanded=False):
            st.code(f"""参照シート
Settings           = {gs.names.SETTINGS}
Members            = {gs.names.MEMBERS}
Ledger             = {gs.names.LEDGER}
LineUsers          = {gs.names.LINEUSERS}
APR_Summary        = {gs.names.APR_SUMMARY}
SmartVault_History = {gs.names.SMARTVAULT_HISTORY}

Spreadsheet ID
{gs.spreadsheet_id}

Spreadsheet URL
{gs.spreadsheet_url()}
""")
        with st.expander("2. シート構成", expanded=False):
            for key, title in [("SETTINGS","Settings"),("MEMBERS","Members"),("LEDGER","Ledger"),("LINEUSERS","LineUsers"),("APR_SUMMARY","APR Summary"),("SMARTVAULT_HISTORY","SmartVault_History")]:
                st.markdown(f"### {title}")
                st.code("\t".join(AppConfig.HEADERS[key]))
        with st.expander("3. Compound_Timing の意味", expanded=False):
            st.markdown("""
- `daily`
  APR確定時に元本へ即時加算します。次回以降は増えた元本で計算します。

- `monthly`
  APR確定時は Ledger に記録のみ行います。元本への反映は APR画面の「未反映APRを元本へ反映」でまとめて行います。

- `none`
  単利です。APRは Ledger に記録しますが、元本には加算しません。
""")
        with st.expander("4. APR計算ロジック", expanded=False):
            st.markdown("""
### PERSONAL
`DailyAPR = Principal × (最終APR% / 100) × Rank係数 ÷ 365`

### GROUP（PERSONAL以外）
`グループ総配当 = グループ総元本 × (最終APR% / 100) × Net_Factor ÷ 365`

`1人あたり配当 = グループ総配当 ÷ 人数`

### 重複防止
同日・同一プロジェクト・同一人物の APR は Ledger を見て1回だけ記録します。
""")
        with st.expander("5. Make連携", expanded=False):
            st.markdown("`LINE Watch Events → HTTP(プロフィール取得) → Google Sheets Search Rows → Filter(0件のみ) → Google Sheets Add a Row`")
            st.code("\t".join(AppConfig.HEADERS["LINEUSERS"]))
        with st.expander("6. Settings自動修復", expanded=False):
            if st.button("Settingsを自動修復", key="help_fix_settings", use_container_width=True):
                try:
                    self.repo.repair_settings(self.repo.load_settings())
                    self.store.persist_and_refresh()
                    st.success(f"{self.repo.gs.names.SETTINGS} を修復しました。")
                    st.rerun()
                except Exception as e:
                    st.error(f"Settings修復でエラー: {e}")
        with st.expander("7. OCR設定（座標設定 + 赤枠プレビュー）", expanded=False):
            projects = self.repo.active_projects(settings_df)
            if not projects:
                st.warning("有効なプロジェクトがありません。")
                return
            ocr_project = st.selectbox("OCR設定対象プロジェクト", projects, key="help_ocr_project")
            row_setting = settings_df[settings_df["Project_Name"] == ocr_project].iloc[0]
            current_vals = pd.DataFrame([{k: row_setting.get(k, v) for k, v in {**AppConfig.OCR_DEFAULTS_PC, **AppConfig.OCR_DEFAULTS_MOBILE}.items()}])
            st.dataframe(current_vals, use_container_width=True, hide_index=True)
            preview = st.file_uploader("画像をアップロードすると赤枠プレビューします", type=["png", "jpg", "jpeg"], key="help_ocr_preview")
            if preview is not None:
                st.image(U.draw_ocr_boxes(preview.getvalue(), AppConfig.SMARTVAULT_BOXES_MOBILE), caption="SmartVault固定赤枠", use_container_width=True)
