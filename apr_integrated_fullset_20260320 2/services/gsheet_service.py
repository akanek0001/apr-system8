from __future__ import annotations

import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials


class GSheetService:
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.gc = self._connect()
        self.sh = self.gc.open_by_key(spreadsheet_id)

        if "gsheet_cache" not in st.session_state:
            st.session_state["gsheet_cache"] = {}

    def _connect(self):
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        return gspread.authorize(creds)

    def clear_cache(self):
        st.session_state["gsheet_cache"] = {}

    def worksheet(self, sheet_name: str):
        return self.sh.worksheet(sheet_name)

    def ensure_sheet(self, sheet_name: str, headers: list[str]) -> None:
        try:
            ws = self.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = self.sh.add_worksheet(title=sheet_name, rows=1000, cols=max(20, len(headers)))
            ws.append_row(headers, value_input_option="USER_ENTERED")
            return

        values = ws.get_all_values()
        if not values:
            ws.append_row(headers, value_input_option="USER_ENTERED")
            return

        current_headers = values[0]
        if current_headers != headers:
            ws.clear()
            ws.append_row(headers, value_input_option="USER_ENTERED")
            if len(values) > 1:
                ws.append_rows(values[1:], value_input_option="USER_ENTERED")

    def _read_sheet(self, sheet_name: str) -> pd.DataFrame:
        ws = self.worksheet(sheet_name)
        values = ws.get_all_values()

        if not values:
            return pd.DataFrame()

        headers = values[0]
        rows = values[1:]

        if not rows:
            return pd.DataFrame(columns=headers)

        return pd.DataFrame(rows, columns=headers)

    def load_df(self, sheet_name: str) -> pd.DataFrame:
        cache = st.session_state["gsheet_cache"]

        if sheet_name in cache:
            return cache[sheet_name].copy()

        try:
            df = self._read_sheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            df = pd.DataFrame()

        cache[sheet_name] = df.copy()
        return df.copy()

    def write_df(self, sheet_name: str, df: pd.DataFrame):
        ws = self.worksheet(sheet_name)

        if df is None or df.empty:
            ws.clear()
            return

        data = [df.columns.tolist()] + df.fillna("").astype(str).values.tolist()
        ws.clear()
        ws.update(data)

    def append_row(self, sheet_name: str, row: list):
        ws = self.worksheet(sheet_name)
        ws.append_row(row, value_input_option="USER_ENTERED")
