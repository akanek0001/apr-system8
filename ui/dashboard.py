from __future__ import annotations

import pandas as pd
import streamlit as st

from repository.repository import Repository
from core.auth import AdminAuth
from core.utils import U


class DashboardPage:
    def __init__(self, repo: Repository):
        self.repo = repo

    # =========================
    # helper
    # =========================
    def _safe_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy()
        out = out.loc[:, ~out.columns.duplicated()]
        out.columns = [str(c).strip() for c in out.columns]
        return out.reset_index(drop=True)

    def _today_str(self) -> str:
        return U.fmt_date(U.now_jst())

    # =========================
    # render
    # =========================
    def render(self) -> None:
        st.title("ダッシュボード")
        st.caption(f"管理者: {AdminAuth.current_namespace()}")

        settings_df = self._safe_df(self.repo.load_settings())
        members_df = self._safe_df(self.repo.load_members())
        ledger_df = self._safe_df(self.repo.load_ledger())
        apr_summary_df = self._safe_df(self.repo.load_apr_summary())
        smartvault_df = self._safe_df(self.repo.load_smartvault_history())

        projects = self.repo.active_projects(settings_df)

        active_members = 0
        total_principal = 0.0
        total_apr = 0.0
        today_apr = 0.0

        # =========================
        # Members 集計
        # =========================
        if not members_df.empty:
            mdf = members_df.copy()
            mdf["IsActive"] = mdf["IsActive"].apply(U.truthy)
            mdf["Principal"] = pd.to_numeric(mdf["Principal"], errors="coerce").fillna(0.0)

            active_members = int(mdf[mdf["IsActive"] == True].shape[0])
            total_principal = float(mdf[mdf["IsActive"] == True]["Principal"].sum())

        # =========================
        # Ledger 集計
        # =========================
        if not ledger_df.empty:
            ldf = ledger_df.copy()
            ldf["Type"] = ldf["Type"].astype(str).str.strip()
            ldf["Amount"] = pd.to_numeric(ldf["Amount"], errors="coerce").fillna(0.0)

            apr_df = ldf[ldf["Type"] == "APR"].copy()
            total_apr = float(apr_df["Amount"].sum())

            if "Datetime_JST" in apr_df.columns:
                today = self._today_str()
                today_apr = float(
                    apr_df[apr_df["Datetime_JST"].astype(str).str.startswith(today)]["Amount"].sum()
                )

        # =========================
        # Header metrics
        # =========================
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("有効プロジェクト数", len(projects))
        c2.metric("有効メンバー数", active_members)
        c3.metric("総元本", f"${total_principal:,.2f}")
        c4.metric("本日APR合計", f"${today_apr:,.6f}")

        st.divider()

        c5, c6 = st.columns([1, 2])
        with c5:
            st.metric("Ledger上のAPR累計", f"${total_apr:,.6f}")

        with c6:
            st.subheader("現在の対象プロジェクト")
            if projects:
                st.write(" / ".join(projects))
            else:
                st.info("有効プロジェクトがありません。")

        # =========================
        # SmartVault 最新値
        # =========================
        st.divider()
        st.subheader("SmartVault 最新状況")

        if smartvault_df.empty:
            st.info("SmartVault_History にデータがありません。")
        else:
            sdf = smartvault_df.copy()
            if "Datetime_JST" in sdf.columns:
                sdf = sdf.sort_values("Datetime_JST", ascending=False)

            latest = sdf.iloc[0]

            c7, c8, c9 = st.columns(3)
            c7.metric("Liquidity", f"${float(pd.to_numeric(pd.Series([latest.get('Liquidity', 0)]), errors='coerce').fillna(0).iloc[0]):,.2f}")
            c8.metric("Yesterday Profit", f"${float(pd.to_numeric(pd.Series([latest.get('Yesterday_Profit', 0)]), errors='coerce').fillna(0).iloc[0]):,.2f}")
            c9.metric("APR", f"{float(pd.to_numeric(pd.Series([latest.get('APR', 0)]), errors='coerce').fillna(0).iloc[0]):,.4f}%")

            with st.expander("SmartVault 履歴（先頭30件）", expanded=False):
                st.dataframe(self._safe_df(sdf.head(30)), use_container_width=True, hide_index=True)

        # =========================
        # APR Summary
        # =========================
        st.divider()
        st.subheader("APR Summary")

        if apr_summary_df.empty:
            st.info("APR_Summary にデータがありません。")
        else:
            sdf = apr_summary_df.copy()
            if "Date_JST" in sdf.columns:
                sdf = sdf.sort_values("Date_JST", ascending=False)

            st.dataframe(self._safe_df(sdf.head(30)), use_container_width=True, hide_index=True)

        # =========================
        # Members 一覧
        # =========================
        st.divider()
        st.subheader("メンバー一覧")

        if members_df.empty:
            st.info("Members にデータがありません。")
        else:
            mshow = members_df.copy()
            if "Principal" in mshow.columns:
                mshow["Principal"] = pd.to_numeric(mshow["Principal"], errors="coerce").fillna(0.0)
            if "IsActive" in mshow.columns:
                mshow["状態"] = mshow["IsActive"].apply(U.bool_to_status)

            st.dataframe(
                self._safe_df(mshow),
                use_container_width=True,
                hide_index=True,
            )

        # =========================
        # 最新 Ledger
        # =========================
        st.divider()
        st.subheader("最新 Ledger")

        if ledger_df.empty:
            st.info("Ledger にデータがありません。")
        else:
            lshow = ledger_df.copy()
            if "Datetime_JST" in lshow.columns:
                lshow = lshow.sort_values("Datetime_JST", ascending=False)

            st.dataframe(
                self._safe_df(lshow.head(30)),
                use_container_width=True,
                hide_index=True,
            )

        # =========================
        # APR履歴
        # =========================
        st.divider()
        st.subheader("APR履歴")

        if ledger_df.empty:
            st.info("APR履歴がありません。")
        else:
            apr_hist = ledger_df.copy()
            apr_hist["Type"] = apr_hist["Type"].astype(str).str.strip()
            apr_hist = apr_hist[apr_hist["Type"] == "APR"].copy()

            if apr_hist.empty:
                st.info("APR履歴がありません。")
            else:
                if "Amount" in apr_hist.columns:
                    apr_hist["Amount"] = pd.to_numeric(apr_hist["Amount"], errors="coerce").fillna(0.0)
                if "Datetime_JST" in apr_hist.columns:
                    apr_hist = apr_hist.sort_values("Datetime_JST", ascending=False)

                st.dataframe(
                    self._safe_df(apr_hist.head(30)),
                    use_container_width=True,
                    hide_index=True,
                )


# END OF FILE
