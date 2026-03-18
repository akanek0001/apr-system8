from __future__ import annotations

import pandas as pd
import streamlit as st

from config import AppConfig
from core.utils import U


class DashboardPage:
    def render(self, members_df: pd.DataFrame, ledger_df: pd.DataFrame, apr_summary_df: pd.DataFrame) -> None:
        st.subheader("📊 管理画面ダッシュボード")
        st.caption("総資産 / 本日APR / グループ別残高 / 個人残高 / 個人別累計APR / LINE通知履歴")

        active_mem = members_df[members_df["IsActive"] == True].copy() if not members_df.empty else members_df.copy()
        total_assets = float(active_mem["Principal"].sum()) if not active_mem.empty else 0.0

        today_prefix, today_apr = U.fmt_date(U.now_jst()), 0.0
        if not ledger_df.empty and "Datetime_JST" in ledger_df.columns:
            today_rows = ledger_df[ledger_df["Datetime_JST"].astype(str).str.startswith(today_prefix)].copy()
            today_apr = float(today_rows[today_rows["Type"].astype(str).str.strip() == AppConfig.TYPE["APR"]]["Amount"].sum())

        c1, c2 = st.columns(2)
        c1.metric("総資産", U.fmt_usd(total_assets))
        c2.metric("本日APR", U.fmt_usd(today_apr))

        st.divider()
        c3, c4 = st.columns(2)

        with c3:
            st.markdown("#### グループ別残高")
            group_df = active_mem[active_mem["Project_Name"].astype(str).str.upper() != AppConfig.PROJECT["PERSONAL"]].copy() if not active_mem.empty else pd.DataFrame()
            if group_df.empty:
                st.info("グループデータがありません。")
            else:
                group_summary = group_df.groupby("Project_Name", as_index=False).agg(人数=("PersonName", "count"), 総残高=("Principal", "sum")).sort_values("総残高", ascending=False)
                group_summary["総残高"] = group_summary["総残高"].apply(U.fmt_usd)
                st.dataframe(group_summary, use_container_width=True, hide_index=True)

        with c4:
            st.markdown("#### 個人残高")
            personal_df = active_mem[active_mem["Project_Name"].astype(str).str.upper() == AppConfig.PROJECT["PERSONAL"]].copy() if not active_mem.empty else pd.DataFrame()
            if personal_df.empty:
                st.info("PERSONAL データがありません。")
            else:
                p = personal_df[["PersonName", "Principal", "LINE_DisplayName"]].copy()
                p["資産割合"] = p["Principal"].map(lambda x: f"{(float(x) / total_assets) * 100:.2f}%" if total_assets > 0 else "0.00%")
                p["Principal_num"] = p["Principal"].astype(float)
                p["Principal"] = p["Principal"].apply(U.fmt_usd)
                p = p.sort_values("Principal_num", ascending=False)[["PersonName", "Principal", "資産割合", "LINE_DisplayName"]]
                st.dataframe(p, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### 個人別 累計APR")
        if apr_summary_df.empty:
            st.info("APR履歴がありません。")
        else:
            view = apr_summary_df.copy()
            view["Total_APR_num"] = U.to_num_series(view["Total_APR"])
            view["Total_APR"] = view["Total_APR_num"].apply(U.fmt_usd)
            view = view.sort_values("Total_APR_num", ascending=False)[["PersonName", "Total_APR", "APR_Count", "Asset_Ratio", "LINE_DisplayName"]]
            view = view.rename(columns={"Total_APR": "累計APR", "APR_Count": "件数", "Asset_Ratio": "総資産比"})
            st.dataframe(view, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### LINE通知履歴")
        c_hist1, c_hist2 = st.columns([1, 1])
        with c_hist1:
            if st.button("LINE送信履歴をリセット表示", use_container_width=True):
                st.session_state["hide_line_history"] = True
                st.rerun()
        with c_hist2:
            if st.button("LINE送信履歴を再表示", use_container_width=True):
                st.session_state["hide_line_history"] = False
                st.rerun()

        if st.session_state.get("hide_line_history", False):
            st.info("LINE通知履歴はリセット表示中です。シートの記録は削除していません。")
        else:
            if ledger_df.empty:
                st.info("通知履歴がありません。")
            else:
                line_hist = ledger_df[ledger_df["Type"].astype(str).str.strip() == AppConfig.TYPE["LINE"]].copy()
                if line_hist.empty:
                    st.info("LINE通知履歴はまだありません。")
                else:
                    cols = [c for c in ["Datetime_JST", "Project_Name", "PersonName", "Type", "Line_User_ID", "LINE_DisplayName", "Note", "Source"] if c in line_hist.columns]
                    st.dataframe(line_hist.sort_values("Datetime_JST", ascending=False)[cols].head(100), use_container_width=True, hide_index=True)
