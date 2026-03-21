from __future__ import annotations

import pandas as pd
import streamlit as st

from repository.repository import Repository
from store.datastore import DataStore


class CashPage:
    def __init__(self, repo: Repository, store: DataStore):
        self.repo = repo
        self.store = store

    def _truthy(self, value) -> bool:
        return str(value).strip().lower() in {"true", "1", "yes", "on", "🟢運用中"}

    def _safe_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        out = df.copy().fillna("")
        out.columns = [str(c) for c in out.columns]
        for c in out.columns:
            out[c] = out[c].astype(str)
        return out.reset_index(drop=True)

    def render(self, settings_df: pd.DataFrame, members_df: pd.DataFrame, ledger_df: pd.DataFrame) -> None:
        st.subheader("入出金")

        projects = self.repo.active_projects(settings_df)
        if not projects:
            st.warning("有効なプロジェクトがありません。")
            return

        project = st.selectbox("対象プロジェクト", projects, key="cash_project")

        sub = members_df.copy()
        sub = sub[sub["Project_Name"].astype(str).str.strip() == str(project).strip()].copy()
        if "IsActive" in sub.columns:
            sub = sub[sub["IsActive"].apply(self._truthy)].copy()

        if sub.empty:
            st.info("対象メンバーがいません。")
            return

        member_names = sub["PersonName"].astype(str).str.strip().tolist()
        person = st.selectbox("対象メンバー", member_names, key="cash_person")

        c1, c2 = st.columns(2)
        with c1:
            cash_type = st.selectbox("種別", ["DEPOSIT", "WITHDRAW"], key="cash_type")
        with c2:
            amount = st.number_input("金額", min_value=0.0, step=100.0, value=0.0, key="cash_amount")

        note = st.text_input("メモ", key="cash_note")

        if st.button("記録", use_container_width=True, key="cash_save"):
            if amount <= 0:
                st.warning("金額を入力してください。")
                return

            target = sub[sub["PersonName"].astype(str).str.strip() == str(person).strip()].iloc[0]
            ts = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d %H:%M:%S")
            signed_amount = float(amount) if cash_type == "DEPOSIT" else -float(amount)

            self.repo.append_ledger(
                ts=ts,
                project=str(project).strip(),
                person=str(person).strip(),
                type_name=cash_type,
                amount=signed_amount,
                memo=str(note).strip(),
                evidence="",
                line_uid=str(target.get("Line_User_ID", "")).strip(),
                line_name=str(target.get("LINE_DisplayName", "")).strip(),
                source="APP",
            )

            self.store.persist_and_refresh()
            st.success("Ledger に記録しました。")
            st.rerun()

        st.markdown("### 最近の入出金")
        if ledger_df is None or ledger_df.empty:
            st.info("Ledger にデータがありません。")
            return

        show = ledger_df.copy()
        show = show[show["Project_Name"].astype(str).str.strip() == str(project).strip()].copy()
        if "Type" in show.columns:
            show = show[show["Type"].astype(str).isin(["DEPOSIT", "WITHDRAW"])].copy()
        if "Datetime_JST" in show.columns:
            show = show.sort_values("Datetime_JST", ascending=False)

        if show.empty:
            st.info("このプロジェクトの入出金履歴はありません。")
        else:
            st.dataframe(self._safe_df(show.head(50)), use_container_width=True, hide_index=True)
