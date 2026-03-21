from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from config import AppConfig
from repository.repository import Repository
from engine.finance_engine import FinanceEngine


class DataStore:
    def __init__(self, repo: Repository, engine: FinanceEngine):
        self.repo = repo
        self.engine = engine

    def _key(self, name: str) -> str:
        return AppConfig.SESSION_KEYS[name]

    def clear(self) -> None:
        for key in AppConfig.SESSION_KEYS.values():
            if key in st.session_state:
                del st.session_state[key]

    def load_settings(self, force: bool = False) -> pd.DataFrame:
        key = self._key("SETTINGS")
        if force or key not in st.session_state:
            st.session_state[key] = self.repo.load_settings()
        return st.session_state[key]

    def load_members(self, force: bool = False) -> pd.DataFrame:
        key = self._key("MEMBERS")
        if force or key not in st.session_state:
            st.session_state[key] = self.repo.load_members()
        return st.session_state[key]

    def load_ledger(self, force: bool = False) -> pd.DataFrame:
        key = self._key("LEDGER")
        if force or key not in st.session_state:
            st.session_state[key] = self.repo.load_ledger()
        return st.session_state[key]

    def load_line_users(self, force: bool = False) -> pd.DataFrame:
        key = self._key("LINEUSERS")
        if force or key not in st.session_state:
            st.session_state[key] = self.repo.load_line_users()
        return st.session_state[key]

    def load_apr_summary(self, force: bool = False) -> pd.DataFrame:
        key = self._key("APR_SUMMARY")
        if force or key not in st.session_state:
            st.session_state[key] = self.repo.load_apr_summary()
        return st.session_state[key]

    def load_smartvault_history(self, force: bool = False) -> pd.DataFrame:
        key = self._key("SMARTVAULT_HISTORY")
        if force or key not in st.session_state:
            st.session_state[key] = self.repo.load_smartvault_history()
        return st.session_state[key]

    def load_ocr_transaction(self, force: bool = False) -> pd.DataFrame:
        key = self._key("OCR_TRANSACTION")
        if force or key not in st.session_state:
            st.session_state[key] = self.repo.load_ocr_transaction()
        return st.session_state[key]

    def load_ocr_transaction_history(self, force: bool = False) -> pd.DataFrame:
        key = self._key("OCR_TRANSACTION_HISTORY")
        if force or key not in st.session_state:
            st.session_state[key] = self.repo.load_ocr_transaction_history()
        return st.session_state[key]

    def load_apr_auto_queue(self, force: bool = False) -> pd.DataFrame:
        key = self._key("APR_AUTO_QUEUE")
        if force or key not in st.session_state:
            st.session_state[key] = self.repo.load_apr_auto_queue()
        return st.session_state[key]

    def load(self, force: bool = False) -> Dict[str, pd.DataFrame]:
        settings_df = self.load_settings(force=force)
        members_df = self.load_members(force=force)
        ledger_df = self.load_ledger(force=force)
        line_users_df = self.load_line_users(force=force)
        apr_summary_df = self.load_apr_summary(force=force)
        smartvault_history_df = self.load_smartvault_history(force=force)
        ocr_transaction_df = self.load_ocr_transaction(force=force)
        ocr_transaction_history_df = self.load_ocr_transaction_history(force=force)
        apr_auto_queue_df = self.load_apr_auto_queue(force=force)

        return {
            "settings_df": settings_df,
            "members_df": members_df,
            "ledger_df": ledger_df,
            "line_users_df": line_users_df,
            "apr_summary_df": apr_summary_df,
            "smartvault_history_df": smartvault_history_df,
            "ocr_transaction_df": ocr_transaction_df,
            "ocr_transaction_history_df": ocr_transaction_history_df,
            "apr_auto_queue_df": apr_auto_queue_df,
        }

    def refresh(self) -> Dict[str, pd.DataFrame]:
        self.repo.gs.clear_cache()
        self.clear()
        return self.load(force=True)

    def persist_and_refresh(self) -> Dict[str, pd.DataFrame]:
        return self.refresh()

    def build_apr_preview(
        self,
        project: str,
        apr_percent: float,
    ) -> pd.DataFrame:
        data = self.load(force=False)

        result_df = self.engine.build_apr_result(
            settings_df=data["settings_df"],
            members_df=data["members_df"],
            project=project,
            apr_percent=apr_percent,
        )

        return result_df

    def build_today_apr_summary(
        self,
        project: str,
        apr_percent: float,
        date_jst: str,
    ) -> pd.DataFrame:
        data = self.load(force=False)

        apr_df = self.engine.build_apr_result(
            settings_df=data["settings_df"],
            members_df=data["members_df"],
            project=project,
            apr_percent=apr_percent,
        )

        if apr_df is None or apr_df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["APR_SUMMARY"])

        return self.engine.build_apr_summary(
            apr_df=apr_df,
            date_jst=date_jst,
        )

    def build_monthly_pending(
        self,
        project: str,
    ) -> pd.DataFrame:
        data = self.load(force=False)

        return self.engine.calc_monthly_pending_from_ledger(
            ledger_df=data["ledger_df"],
            project=project,
        )


# END OF FILE
