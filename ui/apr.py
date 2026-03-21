from __future__ import annotations

import pandas as pd
import streamlit as st

from config import AppConfig
from repository.repository import Repository
from core.utils import U
from core.auth import AdminAuth


class APRPage:
    def __init__(self, repo: Repository):
        self.repo = repo

    # =========================
    # APR計算
    # =========================
    def _calc_daily_apr(self, principal: float, apr: float, rank: str) -> float:
        factor = AppConfig.FACTOR.get(str(rank).upper(), AppConfig.FACTOR["MASTER"])
        return principal * (apr / 100.0) * factor / 365.0

    # =========================
    # メイン
    # =========================
    def render(self):
        st.title("APR設定 / 実行")
        st.caption(f"管理者: {AdminAuth.current_namespace()}")

        settings_df = self.repo.load_settings()
        members_df = self.repo.load_members()
        ledger_df = self.repo.load_ledger()

        projects = self.repo.active_projects(settings_df)

        if not projects:
            st.warning("有効プロジェクトなし")
            return

        project = st.selectbox("プロジェクト", projects)

        st.subheader("APR入力")

        apr = st.number_input("APR (%)", min_value=0.0, step=1.0, value=0.0)

        if apr <= 0:
            st.info("APRを入力してください")
            return

        st.divider()

        st.subheader("対象メンバー")

        members = members_df[
            (members_df["Project_Name"] == project)
            & (members_df["IsActive"] == True)
        ].copy()

        if members.empty:
            st.warning("対象メンバーなし")
            return

        # 数値整形
        members["Principal"] = pd.to_numeric(members["Principal"], errors="coerce").fillna(0)

        results = []

        for _, row in members.iterrows():
            daily = self._calc_daily_apr(
                row["Principal"],
                apr,
                row["Rank"]
            )

            results.append({
                "PersonName": row["PersonName"],
                "Principal": row["Principal"],
                "Rank": row["Rank"],
                "DailyAPR": daily,
                "Line_User_ID": row["Line_User_ID"],
                "LINE_DisplayName": row["LINE_DisplayName"],
            })

        df = pd.DataFrame(results)

        st.dataframe(
            df[["PersonName", "Principal", "Rank", "DailyAPR"]],
            use_container_width=True,
            hide_index=True
        )

        total = df["DailyAPR"].sum()
        st.metric("合計APR", f"{total:.6f}")

        st.divider()

        # =========================
        # 実行
        # =========================
        if st.button("APR実行", use_container_width=True):

            now = U.fmt_dt(U.now_jst())

            for _, r in df.iterrows():
                self.repo.append_ledger(
                    dt_jst=now,
                    project=project,
                    person_name=r["PersonName"],
                    typ="APR",
                    amount=float(r["DailyAPR"]),
                    note=f"APR {apr}%",
                    evidence_url="",
                    line_user_id=r["Line_User_ID"],
                    line_display_name=r["LINE_DisplayName"],
                    source="APP",
                )

            st.success("APRをLedgerに記録しました")

            st.rerun()
