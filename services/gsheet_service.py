from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

from config import AppConfig
from core.utils import U


class GSheetService:
    def __init__(self, spreadsheet_id: Optional[str] = None, namespace: str = "A"):
        self.namespace = str(namespace).strip() or AppConfig.DEFAULT_NAMESPACE
        self.spreadsheet_id = self._resolve_spreadsheet_id(spreadsheet_id)
        self.gc = self._connect()
        self.sh = self.gc.open_by_key(self.spreadsheet_id)

        if "gsheet_cache" not in st.session_state:
            st.session_state["gsheet_cache"] = {}

    # =========================
    # secrets / auth
    # =========================
    def _resolve_spreadsheet_id(self, spreadsheet_id: Optional[str]) -> str:
        raw = str(spreadsheet_id or "").strip()
        if raw and raw != "YOUR_SPREADSHEET_ID":
            return U.extract_sheet_id(raw)

        try:
            sid = str(st.secrets["connections"]["gsheets"]["spreadsheet"]).strip()
            if sid:
                return U.extract_sheet_id(sid)
        except Exception:
            pass

        raise KeyError(
            "Spreadsheet ID が見つかりません。"
            " Streamlit Secrets の [connections.gsheets] spreadsheet に設定してください。"
        )

    def _read_credentials(self) -> dict[str, Any]:
        try:
            return dict(st.secrets["connections"]["gsheets"]["credentials"])
        except Exception:
            pass

        try:
            return dict(st.secrets["gcp_service_account"])
        except Exception:
            pass

        raise KeyError(
            "Google Sheets の認証情報が見つかりません。"
            " Streamlit Secrets の [connections.gsheets.credentials] に設定してください。"
        )

    def _connect(self):
        creds_dict = self._read_credentials()

        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        return gspread.authorize(creds)

    # =========================
    # names
    # =========================
    def sheet(self, key: str) -> str:
        base = AppConfig.SHEET[key]
        return U.sheet_name(base, self.namespace)

    # =========================
    # worksheet
    # =========================
    def worksheet(self, key: str):
        return self.sh.worksheet(self.sheet(key))

    # =========================
    # read / write
    # =========================
    def load_df(self, key: str) -> pd.DataFrame:
        cache_key = f"{self.namespace}:{key}"
        cache = st.session_state["gsheet_cache"]

        if cache_key in cache:
            return cache[cache_key].copy()

        try:
            ws = self.worksheet(key)
            values = ws.get_all_values()

            if not values:
                df = pd.DataFrame()
            else:
                df = pd.DataFrame(values[1:], columns=values[0])

        except gspread.exceptions.WorksheetNotFound:
            df = pd.DataFrame()
        except gspread.exceptions.APIError as e:
            raise RuntimeError(
                f"シート読み取りに失敗しました: {self.sheet(key)}。"
                f" Spreadsheet共有権限、Spreadsheet ID、API制限を確認してください。"
            ) from e

        df = df.loc[:, ~df.columns.duplicated()]
        cache[cache_key] = df.copy()
        return df.copy()

    def write_df(self, key: str, df: pd.DataFrame) -> None:
        try:
            ws = self.worksheet(key)
        except gspread.exceptions.WorksheetNotFound:
            self.ensure_sheet(key, AppConfig.HEADERS[key])
            ws = self.worksheet(key)

        if df is None or df.empty:
            ws.clear()
            return

        out = df.copy()
        out = out.loc[:, ~out.columns.duplicated()]
        data = [out.columns.tolist()] + out.fillna("").astype(str).values.tolist()

        try:
            ws.clear()
            ws.update(data)
        except gspread.exceptions.APIError as e:
            raise RuntimeError(
                f"シート書き込みに失敗しました: {self.sheet(key)}。"
                f" Spreadsheet共有権限、API制限を確認してください。"
            ) from e

    def append_row(self, key: str, row: list[Any]) -> None:
        try:
            ws = self.worksheet(key)
        except gspread.exceptions.WorksheetNotFound:
            self.ensure_sheet(key, AppConfig.HEADERS[key])
            ws = self.worksheet(key)

        try:
            ws.append_row([("" if x is None else x) for x in row], value_input_option="USER_ENTERED")
        except gspread.exceptions.APIError as e:
            raise RuntimeError(
                f"行追加に失敗しました: {self.sheet(key)}。"
                f" Spreadsheet共有権限、API制限を確認してください。"
            ) from e

    # =========================
    # ensure
    # =========================
    def ensure_sheet(self, key: str, headers: list[str]) -> None:
        name = self.sheet(key)

        try:
            ws = self.sh.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            try:
                ws = self.sh.add_worksheet(title=name, rows=2000, cols=max(20, len(headers)))
                ws.append_row(headers)
                return
            except gspread.exceptions.APIError as e:
                raise RuntimeError(
                    f"シート作成に失敗しました: {name}。"
                    f" Spreadsheet共有権限、Spreadsheet ID、API制限を確認してください。"
                ) from e
        except gspread.exceptions.APIError as e:
            raise RuntimeError(
                f"シート取得に失敗しました: {name}。"
                f" Spreadsheet共有権限、Spreadsheet ID、API制限を確認してください。"
            ) from e

        try:
            values = ws.get_all_values()
        except gspread.exceptions.APIError as e:
            raise RuntimeError(
                f"シート読み取りに失敗しました: {name}。"
                f" API制限または権限の問題の可能性があります。"
            ) from e

        if not values:
            ws.append_row(headers)
            return

        current = list(values[0])

        seen = set()
        deduped = []
        for h in current:
            hs = str(h).strip()
            if hs and hs not in seen:
                deduped.append(hs)
                seen.add(hs)

        expected = [str(h).strip() for h in headers]

        if deduped != expected:
            body = values[1:] if len(values) > 1 else []
            try:
                ws.clear()
                ws.append_row(expected)

                if body:
                    normalized = []
                    for r in body:
                        r = list(r)
                        if len(r) < len(expected):
                            r += [""] * (len(expected) - len(r))
                        normalized.append(r[: len(expected)])
                    ws.append_rows(normalized)
            except gspread.exceptions.APIError as e:
                raise RuntimeError(
                    f"ヘッダー修正に失敗しました: {name}。"
                    f" API制限または権限の問題の可能性があります。"
                ) from e

    # =========================
    # cache
    # =========================
    def clear_cache(self) -> None:
        st.session_state["gsheet_cache"] = {}


# END OF FILE
