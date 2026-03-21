from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from repository.repository import Repository


class DataStore:
    def __init__(self, repo: Repository):
        self.repo = repo

    def clear(self) -> None:
        for key in ["settings_df", "members_df", "ledger_df", "line_users_df"]:
            if key in st.session_state:
                del st.session_state[key]

    def load(self, force: bool = False) -> Dict[str, pd.DataFrame]:
        if force or "settings_df" not in st.session_state:
            st.session_state["settings_df"] = self.repo.load_settings()

        if force or "members_df" not in st.session_state:
            st.session_state["members_df"] = self.repo.load_members()

        if force or "ledger_df" not in st.session_state:
            st.session_state["ledger_df"] = self.repo.load_ledger()

        if force or "line_users_df" not in st.session_state:
            st.session_state["line_users_df"] = self.repo.load_line_users()

        return {
            "settings_df": st.session_state["settings_df"],
            "members_df": st.session_state["members_df"],
            "ledger_df": st.session_state["ledger_df"],
            "line_users_df": st.session_state["line_users_df"],
        }

    def refresh(self) -> Dict[str, pd.DataFrame]:
        self.repo.gs.clear_cache()
        self.clear()
        return self.load(force=True)

    def persist_and_refresh(self) -> Dict[str, pd.DataFrame]:
        return self.refresh()
