from __future__ import annotations

import pandas as pd
import streamlit as st

from config import AppConfig
from repository.repository import Repository
from store.datastore import DataStore


class AdminPage:
    def __init__(self, repo: Repository, store: DataStore):
        self.repo = repo
        self.store = store

    def _safe_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        out = df.copy().fillna("")
        out.columns = [str(c) for c in out.columns]
        for c in out.columns:
            out[c] = out[c].astype(str)
        return out.reset_index(drop=True)

    def render(self, settings_df: pd.DataFrame, members_df: pd.DataFrame, line_users_df: pd.DataFrame) -> None:
        st.subheader("管理")

        tab1, tab2, tab3 = st.tabs(["Settings", "Members", "LineUsers"])

        with tab1:
            st.markdown("### Settings")
            if settings_df is None or settings_df.empty:
                st.info("Settings シートが空です。")
            else:
                st.dataframe(self._safe_df(settings_df), use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("### Members")
            if members_df is None or members_df.empty:
                st.info("Members シートが空です。")
            else:
                st.dataframe(self._safe_df(members_df), use_container_width=True, hide_index=True)

            st.markdown("### メンバー追加")
            projects = self.repo.active_projects(settings_df)
            if not projects:
                st.warning("有効なプロジェクトがありません。")
            else:
                with st.form("add_member_form", clear_on_submit=False):
                    project = st.selectbox("Project_Name", projects)
                    person_name = st.text_input("PersonName")
                    principal = st.number_input("Principal", min_value=0.0, step=100.0, value=0.0)
                    line_user_id = st.text_input("Line_User_ID")
                    line_display_name = st.text_input("LINE_DisplayName")
                    rank = st.selectbox("Rank", [AppConfig.RANK["MASTER"], AppConfig.RANK["ELITE"]])
                    is_active = st.selectbox("IsActive", ["TRUE", "FALSE"], index=0)
                    submitted = st.form_submit_button("Members に追加")

                if submitted:
                    if not str(person_name).strip():
                        st.warning("PersonName を入力してください。")
                    else:
                        current = self.repo.load_members().copy()
                        now_str = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d %H:%M:%S")
                        new_row = {
                            "Project_Name": str(project).strip(),
                            "PersonName": str(person_name).strip(),
                            "Principal": float(principal),
                            "Line_User_ID": str(line_user_id).strip(),
                            "LINE_DisplayName": str(line_display_name).strip(),
                            "Rank": str(rank).strip(),
                            "IsActive": str(is_active).strip(),
                            "CreatedAt_JST": now_str,
                            "UpdatedAt_JST": now_str,
                        }
                        current = pd.concat([current, pd.DataFrame([new_row])], ignore_index=True)
                        self.repo.write_members(current)
                        self.store.persist_and_refresh()
                        st.success("Members に追加しました。")
                        st.rerun()

        with tab3:
            st.markdown("### LineUsers")
            if line_users_df is None or line_users_df.empty:
                st.info("LineUsers シートが空です。")
            else:
                st.dataframe(self._safe_df(line_users_df), use_container_width=True, hide_index=True)
