from __future__ import annotations

import pandas as pd
import streamlit as st

from repository.repository import Repository


class DashboardPage:
    def __init__(self, repo: Repository):
        self.repo = repo

    def _safe_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        out = df.copy().fillna("")
        out.columns = [str(c) for c in out.columns]
        for c in out.columns:
            out[c] = out[c].astype(str)
        return out.reset_index(drop=True)

    def render(self) -> None:
        st.subheader("ダッシュボード")

        settings_df = self.repo.load_settings()
        members_df = self.repo.load_members()
        ledger_df = self.repo.load_ledger()

        projects = self.repo.active_projects(settings_df)

        active_members = 0
        total_principal = 0.0
        total_apr = 0.0

        if members_df is not None and not members_df.empty:
            df = members_df.copy()
            if "IsActive" in df.columns:
                active_mask = df["IsActive"].astype(str).str.lower().isin(["true", "1", "yes", "on"])
                df = df[active_mask]
            active_members = len(df)
            if "Principal" in df.columns:
                total_principal = pd.to_numeric(df["Principal"], errors="coerce").fillna(0).sum()

        if ledger_df is not None and not ledger_df.empty:
            df = ledger_df.copy()
            if "Type" in df.columns:
                df = df[df["Type"].astype(str).str.strip() == "APR"]
            if "Amount" in df.columns:
                total_apr = pd.to_numeric(df["Amount"], errors="coerce").fillna(0).sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("有効プロジェクト数", len(projects))
        c2.metric("有効メンバー数", active_members)
        c3.metric("総元本", f"${float(total_principal):,.2f}")

        st.markdown("### APR累計")
        st.metric("Ledger上のAPR合計", f"${float(total_apr):,.6f}")

        st.markdown("### 最新Ledger")
        if ledger_df is None or ledger_df.empty:
            st.info("Ledger にデータがありません。")
        else:
            show = ledger_df.copy()
            if "Datetime_JST" in show.columns:
                show = show.sort_values("Datetime_JST", ascending=False)
            st.dataframe(self._safe_df(show.head(20)), use_container_width=True, hide_index=True)
