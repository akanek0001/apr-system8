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

        # キャッシュ
        if "gsheet_cache" not in st.session_state:
            st.session_state["gsheet_cache"] = {}

    # =========================
    # Secrets / 接続
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

        raise KeyError("Spreadsheet ID が見つかりません")

    def _read_credentials(self) -> dict[str, Any]:
        try:
            return dict(st.secrets["connections"]["gsheets"]["credentials"])
        except Exception:
            pass

        try:
            return dict(st.secrets["gcp_service_account"])
        except Exception:
            pass

        raise KeyError("Google Sheets 認証情報が見つかりません")

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
    # シート名
    # =========================
    def sheet(self, key: str) -> str:
        base = AppConfig.SHEET[key]
        return U.sheet_name(base, self.namespace)

    # =========================
    # ワークシート取得
    # =========================
    def worksheet(self, key: str):
        name = self.sheet(key)
        return self.sh.worksheet(name)

    # =========================
    # 読み込み
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

        # 🔥 重要：重複列除去
        df = df.loc[:, ~df.columns.duplicated()]

        cache[cache_key] = df.copy()
        return df.copy()

    # =========================
    # 書き込み
    # =========================
    def write_df(self, key: str, df: pd.DataFrame):
        ws = self.worksheet(key)

        if df is None or df.empty:
            ws.clear()
            return

        out = df.copy()
        out = out.loc[:, ~out.columns.duplicated()]

        data = [out.columns.tolist()] + out.fillna("").astype(str).values.tolist()

        ws.clear()
        ws.update(data)

    # =========================
    # 追加
    # =========================
    def append_row(self, key: str, row: list[Any]):
        ws = self.worksheet(key)
        ws.append_row([("" if x is None else x) for x in row], value_input_option="USER_ENTERED")

    # =========================
    # 初期化
    # =========================
    def ensure_sheet(self, key: str, headers: list[str]):
        name = self.sheet(key)

        try:
            ws = self.sh.worksheet(name)
        except gspread.exceptions.WorksheetNotFound:
            ws = self.sh.add_worksheet(title=name, rows=2000, cols=max(20, len(headers)))
            ws.append_row(headers)
            return

        values = ws.get_all_values()

        if not values:
            ws.append_row(headers)
            return

        current = values[0]

        if current != headers:
            body = values[1:] if len(values) > 1 else []
            ws.clear()
            ws.append_row(headers)

            if body:
                normalized = []
                for r in body:
                    r = list(r)
                    if len(r) < len(headers):
                        r += [""] * (len(headers) - len(r))
                    normalized.append(r[: len(headers)])
                ws.append_rows(normalized)

    # =========================
    # キャッシュ
    # =========================
    def clear_cache(self):
        st.session_state["gsheet_cache"] = {}
