from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from config import AppConfig
from engine.finance_engine import FinanceEngine
from repository.repository import Repository


class DataStore:
    def __init__(self, repo: Repository, engine: FinanceEngine):
        self.repo = repo
        self.engine = engine

    def clear(self) -> None:
        for key in AppConfig.SESSION_KEYS.values():
            if key in st.session_state:
                del st.session_state[key]

    def load(self, force: bool = False) -> Dict[str, pd.DataFrame]:
        if force or AppConfig.SESSION_KEYS["SETTINGS"] not in st.session_state:
            st.session_state[AppConfig.SESSION_KEYS["SETTINGS"]] = self.repo.repair_settings(self.repo.load_settings())
        if force or AppConfig.SESSION_KEYS["MEMBERS"] not in st.session_state:
            st.session_state[AppConfig.SESSION_KEYS["MEMBERS"]] = self.repo.load_members()
        if force or AppConfig.SESSION_KEYS["LEDGER"] not in st.session_state:
            st.session_state[AppConfig.SESSION_KEYS["LEDGER"]] = self.repo.load_ledger()
        if force or AppConfig.SESSION_KEYS["LINEUSERS"] not in st.session_state:
            st.session_state[AppConfig.SESSION_KEYS["LINEUSERS"]] = self.repo.load_line_users()

        settings_df = st.session_state[AppConfig.SESSION_KEYS["SETTINGS"]]
        members_df = st.session_state[AppConfig.SESSION_KEYS["MEMBERS"]]
        ledger_df = st.session_state[AppConfig.SESSION_KEYS["LEDGER"]]
        line_users_df = st.session_state[AppConfig.SESSION_KEYS["LINEUSERS"]]
        apr_summary_df = self.engine.build_apr_summary(ledger_df, members_df)
        st.session_state[AppConfig.SESSION_KEYS["APR_SUMMARY"]] = apr_summary_df

        return {
            "settings_df": settings_df,
            "members_df": members_df,
            "ledger_df": ledger_df,
            "line_users_df": line_users_df,
            "apr_summary_df": apr_summary_df,
        }

    def refresh(self) -> Dict[str, pd.DataFrame]:
        self.repo.gs.clear_cache()
        self.clear()
        return self.load(force=True)

    def persist_and_refresh(self) -> Dict[str, pd.DataFrame]:
        data = self.refresh()
        self.repo.write_apr_summary(data["apr_summary_df"])
        return self.refresh()
