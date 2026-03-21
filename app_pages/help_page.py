from __future__ import annotations

import pandas as pd
import streamlit as st

from config import AppConfig
from repository.repository import Repository
from services.ocr_processor import OCRProcessor


class HelpPage:
    def __init__(self, repo: Repository):
        self.repo = repo

    def render(self) -> None:
        st.subheader("ヘルプ / OCR設定")

        settings_df = self.repo.load_settings()
        projects = self.repo.active_projects(settings_df)
        if not projects:
            st.warning("有効なプロジェクトがありません。")
            return

        project = st.selectbox("OCR設定対象プロジェクト", projects, key="help_project")
        row = settings_df[settings_df["Project_Name"].astype(str).str.strip() == str(project).strip()].iloc[0]

        st.markdown("### 必要な設定")
        st.code(
            """config.py
SPREADSHEET_ID = "YOUR_SPREADSHEET_ID"

Streamlit Secrets
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = \"\"\"-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----\"\"\"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[ocrspace]
api_key = "YOUR_OCR_SPACE_API_KEY"

[line.tokens]
A = "YOUR_LINE_CHANNEL_ACCESS_TOKEN"
"""
        )

        st.markdown("### 使用シート")
        st.code(
            "\n".join(
                [
                    f'Settings  = {AppConfig.SHEET["SETTINGS"]}',
                    f'Members   = {AppConfig.SHEET["MEMBERS"]}',
                    f'Ledger    = {AppConfig.SHEET["LEDGER"]}',
                    f'LineUsers = {AppConfig.SHEET["LINEUSERS"]}',
                ]
            )
        )

        st.markdown("### SmartVault Mobile OCR座標")
        c1, c2, c3, c4 = st.columns(4)
        sv_liq_left = c1.number_input("SV_Total_Liquidity_Left_Mobile", 0.0, 1.0, float(row.get("SV_Total_Liquidity_Left_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["TOTAL_LIQUIDITY"]["left"])), 0.01)
        sv_liq_top = c2.number_input("SV_Total_Liquidity_Top_Mobile", 0.0, 1.0, float(row.get("SV_Total_Liquidity_Top_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["TOTAL_LIQUIDITY"]["top"])), 0.01)
        sv_liq_right = c3.number_input("SV_Total_Liquidity_Right_Mobile", 0.0, 1.0, float(row.get("SV_Total_Liquidity_Right_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["TOTAL_LIQUIDITY"]["right"])), 0.01)
        sv_liq_bottom = c4.number_input("SV_Total_Liquidity_Bottom_Mobile", 0.0, 1.0, float(row.get("SV_Total_Liquidity_Bottom_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["TOTAL_LIQUIDITY"]["bottom"])), 0.01)

        c5, c6, c7, c8 = st.columns(4)
        sv_profit_left = c5.number_input("SV_Yesterday_Profit_Left_Mobile", 0.0, 1.0, float(row.get("SV_Yesterday_Profit_Left_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["YESTERDAY_PROFIT"]["left"])), 0.01)
        sv_profit_top = c6.number_input("SV_Yesterday_Profit_Top_Mobile", 0.0, 1.0, float(row.get("SV_Yesterday_Profit_Top_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["YESTERDAY_PROFIT"]["top"])), 0.01)
        sv_profit_right = c7.number_input("SV_Yesterday_Profit_Right_Mobile", 0.0, 1.0, float(row.get("SV_Yesterday_Profit_Right_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["YESTERDAY_PROFIT"]["right"])), 0.01)
        sv_profit_bottom = c8.number_input("SV_Yesterday_Profit_Bottom_Mobile", 0.0, 1.0, float(row.get("SV_Yesterday_Profit_Bottom_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["YESTERDAY_PROFIT"]["bottom"])), 0.01)

        c9, c10, c11, c12 = st.columns(4)
        sv_apr_left = c9.number_input("SV_APR_Left_Mobile", 0.0, 1.0, float(row.get("SV_APR_Left_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["APR"]["left"])), 0.01)
        sv_apr_top = c10.number_input("SV_APR_Top_Mobile", 0.0, 1.0, float(row.get("SV_APR_Top_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["APR"]["top"])), 0.01)
        sv_apr_right = c11.number_input("SV_APR_Right_Mobile", 0.0, 1.0, float(row.get("SV_APR_Right_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["APR"]["right"])), 0.01)
        sv_apr_bottom = c12.number_input("SV_APR_Bottom_Mobile", 0.0, 1.0, float(row.get("SV_APR_Bottom_Mobile", AppConfig.SMARTVAULT_BOXES_MOBILE["APR"]["bottom"])), 0.01)

        st.markdown("### 3領域OCR座標")
        tx_defaults = OCRProcessor.get_tx_layout(settings_df, project)
        c13, c14, c15 = st.columns(3)
        tx_base_top = c13.number_input("TX_Scan_BaseTop_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["base_top"]), 0.01)
        tx_step = c14.number_input("TX_Scan_Step_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["step"]), 0.01)
        tx_max_rows = c15.number_input("TX_Scan_MaxRows_Mobile", 1, 30, int(tx_defaults["max_rows"]), 1)

        st.markdown("#### Date")
        d1, d2, d3, d4 = st.columns(4)
        tx_date_left = d1.number_input("TX_Date_Left_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["date_left"]), 0.01)
        tx_date_right = d2.number_input("TX_Date_Right_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["date_right"]), 0.01)
        tx_date_top = d3.number_input("TX_Date_Top_Offset_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["date_top_offset"]), 0.01)
        tx_date_bottom = d4.number_input("TX_Date_Bottom_Offset_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["date_bottom_offset"]), 0.01)

        st.markdown("#### Type")
        t1, t2, t3, t4 = st.columns(4)
        tx_type_left = t1.number_input("TX_Type_Left_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["type_left"]), 0.01)
        tx_type_right = t2.number_input("TX_Type_Right_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["type_right"]), 0.01)
        tx_type_top = t3.number_input("TX_Type_Top_Offset_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["type_top_offset"]), 0.01)
        tx_type_bottom = t4.number_input("TX_Type_Bottom_Offset_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["type_bottom_offset"]), 0.01)

        st.markdown("#### USD")
        u1, u2, u3, u4 = st.columns(4)
        tx_usd_left = u1.number_input("TX_USD_Left_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["usd_left"]), 0.01)
        tx_usd_right = u2.number_input("TX_USD_Right_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["usd_right"]), 0.01)
        tx_usd_top = u3.number_input("TX_USD_Top_Offset_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["usd_top_offset"]), 0.01)
        tx_usd_bottom = u4.number_input("TX_USD_Bottom_Offset_Ratio_Mobile", 0.0, 1.0, float(tx_defaults["usd_bottom_offset"]), 0.01)

        preview = st.file_uploader("OCR確認画像", type=["png", "jpg", "jpeg"], key="help_preview")

        if preview is not None:
            file_bytes = preview.getvalue()

            smart_boxes = {
                "TOTAL_LIQUIDITY": {
                    "left": sv_liq_left,
                    "top": sv_liq_top,
                    "right": sv_liq_right,
                    "bottom": sv_liq_bottom,
                },
                "YESTERDAY_PROFIT": {
                    "left": sv_profit_left,
                    "top": sv_profit_top,
                    "right": sv_profit_right,
                    "bottom": sv_profit_bottom,
                },
                "APR": {
                    "left": sv_apr_left,
                    "top": sv_apr_top,
                    "right": sv_apr_right,
                    "bottom": sv_apr_bottom,
                },
            }
            st.image(OCRProcessor.draw_ocr_boxes(file_bytes, smart_boxes), caption="SmartVault 赤枠", width=500)

            tx_boxes = {
                "ROW1_DATE": OCRProcessor.build_region_box(tx_base_top + tx_step * 0, tx_date_left, tx_date_right, tx_date_top, tx_date_bottom).to_dict(),
                "ROW1_TYPE": OCRProcessor.build_region_box(tx_base_top + tx_step * 0, tx_type_left, tx_type_right, tx_type_top, tx_type_bottom).to_dict(),
                "ROW1_USD": OCRProcessor.build_region_box(tx_base_top + tx_step * 0, tx_usd_left, tx_usd_right, tx_usd_top, tx_usd_bottom).to_dict(),
                "ROW2_DATE": OCRProcessor.build_region_box(tx_base_top + tx_step * 1, tx_date_left, tx_date_right, tx_date_top, tx_date_bottom).to_dict(),
                "ROW2_TYPE": OCRProcessor.build_region_box(tx_base_top + tx_step * 1, tx_type_left, tx_type_right, tx_type_top, tx_type_bottom).to_dict(),
                "ROW2_USD": OCRProcessor.build_region_box(tx_base_top + tx_step * 1, tx_usd_left, tx_usd_right, tx_usd_top, tx_usd_bottom).to_dict(),
                "ROW3_DATE": OCRProcessor.build_region_box(tx_base_top + tx_step * 2, tx_date_left, tx_date_right, tx_date_top, tx_date_bottom).to_dict(),
                "ROW3_TYPE": OCRProcessor.build_region_box(tx_base_top + tx_step * 2, tx_type_left, tx_type_right, tx_type_top, tx_type_bottom).to_dict(),
                "ROW3_USD": OCRProcessor.build_region_box(tx_base_top + tx_step * 2, tx_usd_left, tx_usd_right, tx_usd_top, tx_usd_bottom).to_dict(),
            }
            st.image(OCRProcessor.draw_ocr_boxes(file_bytes, tx_boxes), caption="3領域OCR 赤枠", width=500)

        if st.button("OCR設定を保存", use_container_width=True):
            idx = settings_df[settings_df["Project_Name"].astype(str).str.strip() == str(project).strip()].index[0]

            settings_df.loc[idx, "SV_Total_Liquidity_Left_Mobile"] = sv_liq_left
            settings_df.loc[idx, "SV_Total_Liquidity_Top_Mobile"] = sv_liq_top
            settings_df.loc[idx, "SV_Total_Liquidity_Right_Mobile"] = sv_liq_right
            settings_df.loc[idx, "SV_Total_Liquidity_Bottom_Mobile"] = sv_liq_bottom

            settings_df.loc[idx, "SV_Yesterday_Profit_Left_Mobile"] = sv_profit_left
            settings_df.loc[idx, "SV_Yesterday_Profit_Top_Mobile"] = sv_profit_top
            settings_df.loc[idx, "SV_Yesterday_Profit_Right_Mobile"] = sv_profit_right
            settings_df.loc[idx, "SV_Yesterday_Profit_Bottom_Mobile"] = sv_profit_bottom

            settings_df.loc[idx, "SV_APR_Left_Mobile"] = sv_apr_left
            settings_df.loc[idx, "SV_APR_Top_Mobile"] = sv_apr_top
            settings_df.loc[idx, "SV_APR_Right_Mobile"] = sv_apr_right
            settings_df.loc[idx, "SV_APR_Bottom_Mobile"] = sv_apr_bottom

            settings_df.loc[idx, "TX_Scan_BaseTop_Ratio_Mobile"] = tx_base_top
            settings_df.loc[idx, "TX_Scan_Step_Ratio_Mobile"] = tx_step
            settings_df.loc[idx, "TX_Scan_MaxRows_Mobile"] = tx_max_rows
            settings_df.loc[idx, "TX_Date_Left_Ratio_Mobile"] = tx_date_left
            settings_df.loc[idx, "TX_Date_Right_Ratio_Mobile"] = tx_date_right
            settings_df.loc[idx, "TX_Date_Top_Offset_Ratio_Mobile"] = tx_date_top
            settings_df.loc[idx, "TX_Date_Bottom_Offset_Ratio_Mobile"] = tx_date_bottom
            settings_df.loc[idx, "TX_Type_Left_Ratio_Mobile"] = tx_type_left
            settings_df.loc[idx, "TX_Type_Right_Ratio_Mobile"] = tx_type_right
            settings_df.loc[idx, "TX_Type_Top_Offset_Ratio_Mobile"] = tx_type_top
            settings_df.loc[idx, "TX_Type_Bottom_Offset_Ratio_Mobile"] = tx_type_bottom
            settings_df.loc[idx, "TX_USD_Left_Ratio_Mobile"] = tx_usd_left
            settings_df.loc[idx, "TX_USD_Right_Ratio_Mobile"] = tx_usd_right
            settings_df.loc[idx, "TX_USD_Top_Offset_Ratio_Mobile"] = tx_usd_top
            settings_df.loc[idx, "TX_USD_Bottom_Offset_Ratio_Mobile"] = tx_usd_bottom
            settings_df.loc[idx, "UpdatedAt_JST"] = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d %H:%M:%S")

            self.repo.write_settings(settings_df)
            try:
                self.repo.gs.clear_cache()
            except Exception:
                pass
            st.success("OCR設定を保存しました。")
            st.rerun()
