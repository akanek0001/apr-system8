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

    def render(self, settings_df: pd.DataFrame, members_df: pd.DataFrame) -> None:
        st.subheader("💸 入金 / 出金（個別LINE通知）")
        projects = self.repo.active_projects(settings_df)
        if not projects:
            st.warning("有効なプロジェクトがありません。")
            return

        project = st.selectbox("プロジェクト", projects, key="cash_project")
        mem = self.repo.project_members_active(members_df, project)
        if mem.empty:
            st.warning("このプロジェクトに 🟢運用中 のメンバーがいません。")
            return

        person = st.selectbox("メンバー", mem["PersonName"].tolist())
        row = mem[mem["PersonName"] == person].iloc[0]
        current = float(row["Principal"])

        typ = st.selectbox("種別", [AppConfig.TYPE["DEPOSIT"], AppConfig.TYPE["WITHDRAW"]])
        amt = st.number_input("金額", min_value=0.0, value=0.0, step=100.0)
        note = st.text_input("メモ（任意）", value="")
        uploaded = st.file_uploader("エビデンス画像（任意）", type=["png", "jpg", "jpeg"], key="cash_img")

        if st.button("確定して保存＆個別にLINE通知"):
            try:
                if amt <= 0:
                    st.warning("金額が0です。")
                    return
                if typ == AppConfig.TYPE["WITHDRAW"] and float(amt) > current:
                    st.error("出金額が現在残高を超えています。")
                    return

                evidence_url = ExternalService.upload_imgbb(uploaded.getvalue()) if uploaded else None
                if uploaded and not evidence_url:
                    st.error("画像アップロードに失敗しました。")
                    return

                new_balance = current + float(amt) if typ == AppConfig.TYPE["DEPOSIT"] else current - float(amt)
                ts = U.fmt_dt(U.now_jst())

                for i in range(len(members_df)):
                    if members_df.loc[i, "Project_Name"] == str(project) and str(members_df.loc[i, "PersonName"]).strip() == str(person).strip():
                        members_df.loc[i, "Principal"] = float(new_balance)
                        members_df.loc[i, "UpdatedAt_JST"] = ts

                self.repo.append_ledger(ts, project, person, typ, float(amt), note, evidence_url or "", str(row["Line_User_ID"]).strip(), str(row["LINE_DisplayName"]).strip())
                self.repo.write_members(members_df)

                token = ExternalService.get_line_token(AdminAuth.current_namespace())
                uid = str(row["Line_User_ID"]).strip()
                msg = (
                    "💸【入出金通知】\n"
                    f"{person} 様\n"
                    f"日時: {U.now_jst().strftime('%Y/%m/%d %H:%M')}\n"
                    f"種別: {typ}\n"
                    f"金額: {U.fmt_usd(float(amt))}\n"
                    f"更新後残高: {U.fmt_usd(float(new_balance))}\n"
                )

                if uid:
                    code = ExternalService.send_line_push(token, uid, msg, evidence_url)
                    line_note = f"HTTP:{code}, Type:{typ}, Amount:{float(amt)}, NewBalance:{float(new_balance)}"
                else:
                    code, line_note = 0, "LINE未送信: Line_User_IDなし"

                self.repo.append_ledger(ts, project, person, AppConfig.TYPE["LINE"], 0, line_note, evidence_url or "", uid, str(row["LINE_DisplayName"]).strip())
                self.store.persist_and_refresh()

                if code == 200:
                    st.success("入出金保存＆LINE送信記録完了")
                else:
                    st.warning(f"入出金保存完了 / LINE送信または送信記録あり（HTTP {code}）")
                st.rerun()
            except Exception as e:
                st.error(f"入出金処理でエラー: {e}")
                st.stop()
