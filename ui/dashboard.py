from __future__ import annotations

import pandas as pd
import streamlit as st

from repository.repository import Repository
from core.auth import AdminAuth


class DashboardPage:
    def __init__(self, repo: Repository):
        self.repo = repo

    def _safe_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy().fillna("")
        out = out.loc[:, ~out.columns.duplicated()]
        out.columns = [str(c) for c in out.columns]

        for c in out.columns:
            out[c] = out[c].astype(str)

        return out.reset_index(drop=True)

    def render(self) -> None:
        st.title("ダッシュボード")
        st.caption(f"管理者: {AdminAuth.current_namespace()}")

        settings_df = self.repo.load_settings()
        members_df = self.repo.load_members()
        ledger_df = self.repo.load_ledger()

        projects = self.repo.active_projects(settings_df)

        active_members = 0
        total_principal = 0.0
        total_apr = 0.0
        today_apr = 0.0

        if members_df is not None and not members_df.empty:
            df = members_df.copy()
            df = df.loc[:, ~df.columns.duplicated()]

            if "IsActive" in df.columns:
                active_mask = df["IsActive"].astype(str).str.lower().isin(["true", "1", "yes", "on"])
                df = df[active_mask]

            active_members = len(df)

            if "Principal" in df.columns:
                total_principal = pd.to_numeric(df["Principal"], errors="coerce").fillna(0).sum()

        if ledger_df is not None and not ledger_df.empty:
            df = ledger_df.copy()
            df = df.loc[:, ~df.columns.duplicated()]

            if "Type" in df.columns:
                apr_df = df[df["Type"].astype(str).str.strip() == "APR"].copy()
            else:
                apr_df = pd.DataFrame()

            if not apr_df.empty and "Amount" in apr_df.columns:
                apr_df["Amount"] = pd.to_numeric(apr_df["Amount"], errors="coerce").fillna(0)
                total_apr = apr_df["Amount"].sum()

                if "Datetime_JST" in apr_df.columns:
                    today_str = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d")
                    today_apr = apr_df[apr_df["Datetime_JST"].astype(str).str.startswith(today_str)]["Amount"].sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("有効プロジェクト数", len(projects))
        c2.metric("有効メンバー数", active_members)
        c3.metric("総元本", f"${float(total_principal):,.2f}")
        c4.metric("本日APR合計", f"${float(today_apr):,.6f}")

        st.divider()

        c5, c6 = st.columns([1, 2])
        with c5:
            st.metric("Ledger上のAPR累計", f"${float(total_apr):,.6f}")

        with c6:
            st.subheader("現在の対象プロジェクト")
            if projects:
                st.write(" / ".join(projects))
            else:
                st.info("有効プロジェクトがありません。")

        st.divider()

        st.subheader("メンバー一覧")
        if members_df is None or members_df.empty:
            st.info("Members にデータがありません。")
        else:
            show = members_df.copy()
            show = show.loc[:, ~show.columns.duplicated()]

            if "Principal" in show.columns:
                show["Principal"] = pd.to_numeric(show["Principal"], errors="coerce").fillna(0)

            st.dataframe(
                show,
                use_container_width=True,
                hide_index=True,
            )

        st.divider()

        st.subheader("最新Ledger")
        if ledger_df is None or ledger_df.empty:
            st.info("Ledger にデータがありません。")
        else:
            show = ledger_df.copy()
            show = show.loc[:, ~show.columns.duplicated()]

            if "Datetime_JST" in show.columns:
                show = show.sort_values("Datetime_JST", ascending=False)

            st.dataframe(
                self._safe_df(show.head(30)),
                use_container_width=True,
                hide_index=True,
            )

        st.divider()

        st.subheader("APR履歴")
        if ledger_df is None or ledger_df.empty:
            st.info("APR履歴がありません。")
        else:
            apr_df = ledger_df.copy()
            apr_df = apr_df.loc[:, ~apr_df.columns.duplicated()]

            if "Type" in apr_df.columns:
                apr_df = apr_df[apr_df["Type"].astype(str).str.strip() == "APR"].copy()

            if apr_df.empty:
                st.info("APR履歴がありません。")
            else:
                if "Amount" in apr_df.columns:
                    apr_df["Amount"] = pd.to_numeric(apr_df["Amount"], errors="coerce").fillna(0)

                if "Datetime_JST" in apr_df.columns:
                    apr_df = apr_df.sort_values("Datetime_JST", ascending=False)

                st.dataframe(
                    self._safe_df(apr_df.head(30)),
                    use_container_width=True,
                    hide_index=True,
                )
