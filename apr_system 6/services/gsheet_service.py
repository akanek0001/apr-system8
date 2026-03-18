from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

from config import AppConfig
from core.utils import U


@dataclass
class SheetNames:
    SETTINGS: str
    MEMBERS: str
    LEDGER: str
    LINEUSERS: str
    APR_SUMMARY: str
    SMARTVAULT_HISTORY: str


class GSheetService:
    def __init__(self, spreadsheet_id: str, namespace: str):
        self.spreadsheet_id = spreadsheet_id
        self.namespace = namespace
        self.names = SheetNames(
            SETTINGS=U.sheet_name(AppConfig.SHEET["SETTINGS"], namespace),
            MEMBERS=U.sheet_name(AppConfig.SHEET["MEMBERS"], namespace),
            LEDGER=U.sheet_name(AppConfig.SHEET["LEDGER"], namespace),
            LINEUSERS=U.sheet_name(AppConfig.SHEET["LINEUSERS"], namespace),
            APR_SUMMARY=U.sheet_name(AppConfig.SHEET["APR_SUMMARY"], namespace),
            SMARTVAULT_HISTORY=U.sheet_name(AppConfig.SHEET["SMARTVAULT_HISTORY"], namespace),
        )

        con = st.secrets.get("connections", {}).get("gsheets", {})
        creds_info = con.get("credentials")
        if not creds_info:
            st.error("Secrets に [connections.gsheets.credentials] がありません。")
            st.stop()

        creds = Credentials.from_service_account_info(
            dict(creds_info),
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
        )
        self.gc = gspread.authorize(creds)
        self.book = self.gc.open_by_key(self.spreadsheet_id)

        ensure_key = (
            f"_sheet_ensured_{self.names.SETTINGS}_{self.names.MEMBERS}_{self.names.LEDGER}_"
            f"{self.names.LINEUSERS}_{self.names.APR_SUMMARY}_{self.names.SMARTVAULT_HISTORY}"
        )
        if not st.session_state.get(ensure_key, False):
            for key in AppConfig.HEADERS:
                self.ensure_sheet(key)
            st.session_state[ensure_key] = True

    def actual_name(self, key: str) -> str:
        return getattr(self.names, key)

    def ws(self, key_or_name: str):
        name = self.actual_name(key_or_name) if hasattr(self.names, key_or_name) else key_or_name
        return self.book.worksheet(name)

    def spreadsheet_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"

    def ensure_sheet(self, key: str) -> None:
        name = self.actual_name(key)
        headers = AppConfig.HEADERS[key]
        try:
            ws = self.ws(key)
        except Exception:
            ws = self.book.add_worksheet(title=name, rows=3000, cols=max(30, len(headers) + 10))
            ws.append_row(headers, value_input_option="USER_ENTERED")
            return

        try:
            first = ws.row_values(1)
        except APIError:
            return

        if not first:
            ws.append_row(headers, value_input_option="USER_ENTERED")
            return

        colset = [str(c).strip() for c in first if str(c).strip()]
        missing = [h for h in headers if h not in colset]
        if missing:
            ws.update("1:1", [colset + missing])

    @st.cache_data(ttl=600)
    def load_df(_self, key: str) -> pd.DataFrame:
        try:
            values = _self.ws(key).get_all_values()
        except APIError as e:
            raise RuntimeError(f"Google Sheets 読み取りエラー: {_self.actual_name(key)} を取得できません。") from e
        except Exception as e:
            raise RuntimeError(f"{_self.actual_name(key)} の読み取り中にエラーが発生しました: {e}") from e
        if not values:
            return pd.DataFrame()
        return U.clean_cols(pd.DataFrame(values[1:], columns=values[0]))

    def write_df(self, key: str, df: pd.DataFrame) -> None:
        ws = self.ws(key)
        out = df.fillna("").astype(str)
        ws.clear()
        ws.update([out.columns.tolist()] + out.values.tolist(), value_input_option="USER_ENTERED")

    def append_row(self, key: str, row: List[Any]) -> None:
        try:
            self.ws(key).append_row([("" if x is None else x) for x in row], value_input_option="USER_ENTERED")
        except Exception as e:
            raise RuntimeError(f"{self.actual_name(key)} への追記に失敗しました: {e}")

    def overwrite_rows(self, key: str, rows: List[List[Any]]) -> None:
        ws = self.ws(key)
        ws.clear()
        ws.update(rows, value_input_option="USER_ENTERED")

    def clear_cache(self) -> None:
        st.cache_data.clear()
