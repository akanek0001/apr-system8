from __future__ import annotations

import pandas as pd
import streamlit as st

from config import AppConfig
from core.auth import AdminAuth
from core.utils import U
from repository.repository import Repository
from services.external_service import ExternalService
from store.datastore import DataStore


class CashPage:
    def __init__(self, repo: Repository, store: DataStore):
        self.repo = repo
        self.store = store

    def _safe_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy()
        out = out.loc[:, ~out.columns.duplicated()]
        out.columns = [str(c).strip() for c in out.columns]
        return out.reset_index(drop=True)

    def _active_members(self, members_df: pd.DataFrame, project: str) -> pd.DataFrame:
        if members_df is None or members_df.empty:
            return pd.DataFrame()

        df = members_df.copy()
        df = df.loc[:, ~df.columns.duplicated()]
        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df["IsActive"] = df["IsActive"].apply(U.truthy)
        df["Principal"] = pd.to_numeric(df["Principal"], errors="coerce").fillna(0.0)

        df = df[
            (df["Project_Name"] == str(project).strip()) &
            (df["IsActive"] == True)
        ].copy()

        return df.reset_index(drop=True)

    def _write_member_balance(
        self,
        members_df: pd.DataFrame,
        project: str,
        person: str,
        new_balance: float,
    ) -> pd.DataFrame:
        out = members_df.copy()
        out = out.loc[:, ~out.columns.duplicated()]

        mask = (
            out["Project_Name"].astype(str).str.strip() == str(project).strip()
        ) & (
            out["PersonName"].astype(str).str.strip() == str(person).strip()
        )

        out.loc[mask, "Principal"] = float(new_balance)
        out.loc[mask, "UpdatedAt_JST"] = U.fmt_dt(U.now_jst())

        return out

    def render(self, settings_df: pd.DataFrame, members_df: pd.DataFrame) -> None:
        st.title("入金 / 出金")
        st.caption(f"管理者: {AdminAuth.current_namespace()}")

        settings_df = self._safe_df(settings_df)
        members_df = self._safe_df(members_df)

        projects = self.repo.active_projects(settings_df)
        if not projects:
            st.warning("有効なプロジェクトがありません。")
            return

        project = st.selectbox("プロジェクト", projects, key="cash_project")
        active_members = self._active_members(members_df, project)

        if active_members.empty:
            st.warning("このプロジェクトに有効メンバーがいません。")
            return

        st.subheader("入出金入力")

        person = st.selectbox("メンバー", active_members["PersonName"].astype(str).tolist(), key="cash_person")
        row = active_members[active_members["PersonName"].astype(str) == str(person)].iloc[0]

        current_balance = float(pd.to_numeric(pd.Series([row.get("Principal", 0)]), errors="coerce").fillna(0).iloc[0])

        c1, c2 = st.columns(2)
        with c1:
            typ = st.selectbox("種別", [AppConfig.TYPE["DEPOSIT"], AppConfig.TYPE["WITHDRAW"]], key="cash_type")
        with c2:
            amount = st.number_input("金額", min_value=0.0, value=0.0, step=100.0, key="cash_amount")

        note = st.text_input("メモ", value="", key="cash_note")
        uploaded = st.file_uploader("エビデンス画像（任意）", type=["png", "jpg", "jpeg"], key="cash_img")

        st.info(f"現在残高: {U.fmt_usd(current_balance)}")

        if st.button("保存", use_container_width=True, key="cash_save"):
            if amount <= 0:
                st.warning("金額を入力してください。")
                return

            if typ == AppConfig.TYPE["WITHDRAW"] and float(amount) > float(current_balance):
                st.error("出金額が現在残高を超えています。")
                return

            evidence_url = ExternalService.upload_imgbb(uploaded.getvalue()) if uploaded else ""
            if uploaded and not evidence_url:
                st.error("画像アップロードに失敗しました。")
                return

            new_balance = (
                float(current_balance) + float(amount)
                if typ == AppConfig.TYPE["DEPOSIT"]
                else float(current_balance) - float(amount)
            )

            now_str = U.fmt_dt(U.now_jst())
            uid = str(row.get("Line_User_ID", "")).strip()
            display_name = str(row.get("LINE_DisplayName", "")).strip()

            self.repo.append_ledger(
                dt_jst=now_str,
                project=str(project).strip(),
                person_name=str(person).strip(),
                typ=str(typ).strip(),
                amount=float(amount),
                note=str(note).strip(),
                evidence_url=str(evidence_url).strip(),
                line_user_id=uid,
                line_display_name=display_name,
                source=AppConfig.SOURCE["APP"],
            )

            new_members_df = self._write_member_balance(
                members_df=members_df,
                project=project,
                person=person,
                new_balance=new_balance,
            )
            self.repo.write_members(new_members_df)

            token = ExternalService.get_line_token(AdminAuth.current_namespace())

            if uid:
                line_text = (
                    f"💸【入出金通知】\n"
                    f"{person} 様\n"
                    f"プロジェクト: {project}\n"
                    f"種別: {typ}\n"
                    f"金額: {U.fmt_usd(amount)}\n"
                    f"更新後残高: {U.fmt_usd(new_balance)}\n"
                    f"日時: {U.now_jst().strftime('%Y/%m/%d %H:%M')}"
                )

                code = ExternalService.send_line_push(token, uid, line_text, evidence_url or None)

                self.repo.append_ledger(
                    dt_jst=now_str,
                    project=str(project).strip(),
                    person_name=str(person).strip(),
                    typ=AppConfig.TYPE["LINE"],
                    amount=0,
                    note=f"Cash通知 HTTP:{code}",
                    evidence_url=str(evidence_url).strip(),
                    line_user_id=uid,
                    line_display_name=display_name,
                    source=AppConfig.SOURCE["APP"],
                )

            self.store.persist_and_refresh()
            st.success("入出金を保存しました。")
            st.rerun()

        st.divider()
        st.subheader("最近の入出金")

        ledger_df = self._safe_df(self.repo.load_ledger())
        if ledger_df.empty:
            st.info("Ledger にデータがありません。")
            return

        show = ledger_df.copy()
        show["Project_Name"] = show["Project_Name"].astype(str).str.strip()
        show["Type"] = show["Type"].astype(str).str.strip()

        show = show[
            (show["Project_Name"] == str(project).strip()) &
            (show["Type"].isin([AppConfig.TYPE["DEPOSIT"], AppConfig.TYPE["WITHDRAW"]]))
        ].copy()

        if show.empty:
            st.info("このプロジェクトの入出金履歴はありません。")
            return

        if "Amount" in show.columns:
            show["Amount"] = pd.to_numeric(show["Amount"], errors="coerce").fillna(0.0)

        if "Datetime_JST" in show.columns:
            show = show.sort_values("Datetime_JST", ascending=False)

        st.dataframe(
            self._safe_df(show.head(50)),
            use_container_width=True,
            hide_index=True,
        )


# END OF FILE
