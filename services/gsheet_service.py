from __future__ import annotations

import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials


# =========================
# シート名ルール
# =========================
def sheet_name(base: str, namespace: str) -> str:
    return f"{str(base).strip()}__{str(namespace).strip()}"


# =========================
# メインサービス
# =========================
class GSheetService:

    def __init__(self, namespace: str = "A"):
        self.namespace = namespace

        self.gc = self._connect()
        self.spreadsheet_id = self._get_spreadsheet_id()
        self.sh = self.gc.open_by_key(self.spreadsheet_id)

        # シート名定義（完全固定）
        self.names = {
            "SETTINGS": sheet_name("Settings", namespace),
            "MEMBERS": sheet_name("Members", namespace),
            "LEDGER": sheet_name("Ledger", namespace),
            "LINEUSERS": sheet_name("LineUsers", namespace),
            "APR_SUMMARY": sheet_name("APR_Summary", namespace),
            "SMARTVAULT_HISTORY": sheet_name("SmartVault_History", namespace),
            "OCR_TRANSACTION": sheet_name("OCR_Transaction", namespace),
            "OCR_TRANSACTION_HISTORY": sheet_name("OCR_Transaction_History", namespace),
            "APR_AUTO_QUEUE": sheet_name("APR_Auto_Queue", namespace),
        }

        if "gsheet_cache" not in st.session_state:
            st.session_state["gsheet_cache"] = {}

    # =========================
    # 認証
    # =========================
    def _get_spreadsheet_id(self) -> str:
        return st.secrets["connections"]["gsheets"]["spreadsheet"]

    def _connect(self):
        creds_dict = dict(st.secrets["connections"]["gsheets"]["credentials"])

        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        return gspread.authorize(creds)

    # =========================
    # シート取得
    # =========================
    def worksheet(self, key: str):
        name = self.names[key]
        return self.sh.worksheet(name)

    # =========================
    # 読み込み
    # =========================
    def load_df(self, key: str) -> pd.DataFrame:

        cache = st.session_state["gsheet_cache"]

        if key in cache:
            return cache[key].copy()

        try:
            ws = self.worksheet(key)
            values = ws.get_all_values()

            if not values:
                df = pd.DataFrame()
            else:
                df = pd.DataFrame(values[1:], columns=values[0])

        except gspread.exceptions.WorksheetNotFound:
            df = pd.DataFrame()

        # 🔥 重複列除去（絶対必要）
        df = df.loc[:, ~df.columns.duplicated()]

        cache[key] = df.copy()
        return df.copy()

    # =========================
    # 書き込み
    # =========================
    def write_df(self, key: str, df: pd.DataFrame):
        ws = self.worksheet(key)

        if df is None or df.empty:
            ws.clear()
            return

        df = df.loc[:, ~df.columns.duplicated()]

        data = [df.columns.tolist()] + df.fillna("").astype(str).values.tolist()

        ws.clear()
        ws.update(data)

    # =========================
    # 追加
    # =========================
    def append_row(self, key: str, row: list):
        ws = self.worksheet(key)
        ws.append_row(row, value_input_option="USER_ENTERED")

    # =========================
    # キャッシュクリア
    # =========================
    def clear_cache(self):
        st.session_state["gsheet_cache"] = {}
