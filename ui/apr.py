from __future__ import annotations

import pandas as pd
import streamlit as st

from config import AppConfig
from core.auth import AdminAuth
from core.utils import U
from engine.finance_engine import FinanceEngine
from repository.repository import Repository
from services.external_service import ExternalService
from store.datastore import DataStore


class APRPage:
    def __init__(self, repo: Repository, engine: FinanceEngine, store: DataStore):
        self.repo = repo
        self.engine = engine
        self.store = store

    def _safe_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        out = df.copy()
        out = out.loc[:, ~out.columns.duplicated()]
        return out.reset_index(drop=True)

    def _project_compound_mode(self, settings_df: pd.DataFrame, project: str) -> str:
        if settings_df is None or settings_df.empty:
            return AppConfig.COMPOUND["NONE"]

        sdf = settings_df.copy()
        sdf = sdf.loc[:, ~sdf.columns.duplicated()]
        sdf["Project_Name"] = sdf["Project_Name"].astype(str).str.strip()

        hit = sdf[sdf["Project_Name"] == str(project).strip()]
        if hit.empty:
            return AppConfig.COMPOUND["NONE"]

        return U.normalize_compound(hit.iloc[0].get("Compound_Timing", AppConfig.COMPOUND["NONE"]))

    def _project_is_compound(self, settings_df: pd.DataFrame, project: str) -> bool:
        if settings_df is None or settings_df.empty:
            return False

        sdf = settings_df.copy()
        sdf = sdf.loc[:, ~sdf.columns.duplicated()]
        sdf["Project_Name"] = sdf["Project_Name"].astype(str).str.strip()

        hit = sdf[sdf["Project_Name"] == str(project).strip()]
        if hit.empty:
            return False

        return U.truthy(hit.iloc[0].get("IsCompound", False))

    def _today_str(self) -> str:
        return U.fmt_date(U.now_jst())

    def _write_apr_ledger(
        self,
        apr_df: pd.DataFrame,
        project: str,
        apr_percent: float,
        note: str,
    ) -> int:
        if apr_df is None or apr_df.empty:
            return 0

        now_str = U.fmt_dt(U.now_jst())
        count = 0

        for _, r in apr_df.iterrows():
            self.repo.append_ledger(
                dt_jst=now_str,
                project=str(project).strip(),
                person_name=str(r["PersonName"]).strip(),
                typ=AppConfig.TYPE["APR"],
                amount=float(U.to_f(r["DailyAPR"], 0.0)),
                note=f"APR {float(apr_percent):.4f}% {str(note).strip()}".strip(),
                evidence_url="",
                line_user_id=str(r.get("Line_User_ID", "")).strip(),
                line_display_name=str(r.get("LINE_DisplayName", "")).strip(),
                source=AppConfig.SOURCE["APP"],
            )
            count += 1

        return count

    def _write_apr_summary(self, apr_df: pd.DataFrame) -> None:
        if apr_df is None or apr_df.empty:
            return

        date_jst = self._today_str()
        summary_df = self.engine.build_apr_summary(apr_df, date_jst)
        if summary_df is None or summary_df.empty:
            return

        existing = self.repo.load_apr_summary()
        existing = self._safe_df(existing)

        if existing.empty:
            merged = summary_df.copy()
        else:
            merged = existing[
                ~(
                    (existing["Date_JST"].astype(str).str.strip() == str(date_jst).strip())
                    & (existing["Project_Name"].astype(str).str.strip() == str(summary_df.iloc[0]["Project_Name"]).strip())
                )
            ].copy()
            merged = pd.concat([merged, summary_df], ignore_index=True)

        self.repo.write_apr_summary(merged)

    def _apply_compound_if_needed(
        self,
        settings_df: pd.DataFrame,
        members_df: pd.DataFrame,
        apr_df: pd.DataFrame,
        project: str,
    ) -> pd.DataFrame:
        if apr_df is None or apr_df.empty:
            return members_df.copy()

        is_compound = self._project_is_compound(settings_df, project)
        compound_mode = self._project_compound_mode(settings_df, project)

        if not is_compound:
            return members_df.copy()

        if compound_mode == AppConfig.COMPOUND["DAILY"]:
            return self.engine.apply_daily_compound(members_df, apr_df, project)

        return members_df.copy()

    def _send_line_if_needed(
        self,
        apr_df: pd.DataFrame,
        project: str,
        apr_percent: float,
        do_send: bool,
    ) -> tuple[int, int]:
        if not do_send or apr_df is None or apr_df.empty:
            return 0, 0

        token = ExternalService.get_line_token(AdminAuth.current_namespace())
        ok_count = 0
        ng_count = 0

        for _, r in apr_df.iterrows():
            uid = str(r.get("Line_User_ID", "")).strip()
            person = str(r.get("PersonName", "")).strip()
            daily_apr = float(U.to_f(r.get("DailyAPR", 0.0), 0.0))
            principal = float(U.to_f(r.get("Principal", 0.0), 0.0))

            if not U.is_line_uid(uid):
                ng_count += 1
                continue

            msg = (
                f"📈【APR通知】\n"
                f"{person} 様\n"
                f"プロジェクト: {project}\n"
                f"APR: {float(apr_percent):.4f}%\n"
                f"元本: {U.fmt_usd(principal)}\n"
                f"本日APR: {U.fmt_usd(daily_apr)}\n"
                f"日時: {U.now_jst().strftime('%Y/%m/%d %H:%M')}"
            )

            code = ExternalService.send_line_push(token, uid, msg)
            if code == 200:
                ok_count += 1
            else:
                ng_count += 1

            self.repo.append_ledger(
                dt_jst=U.fmt_dt(U.now_jst()),
                project=str(project).strip(),
                person_name=person,
                typ=AppConfig.TYPE["LINE"],
                amount=0,
                note=f"APR通知 HTTP:{code}",
                evidence_url="",
                line_user_id=uid,
                line_display_name=str(r.get("LINE_DisplayName", "")).strip(),
                source=AppConfig.SOURCE["APP"],
            )

        return ok_count, ng_count

    def render(self) -> None:
        st.title("APR設定 / 実行")
        st.caption(f"管理者: {AdminAuth.current_namespace()}")

        data = self.store.load(force=False)
        settings_df = self._safe_df(data["settings_df"])
        members_df = self._safe_df(data["members_df"])
        ledger_df = self._safe_df(data["ledger_df"])

        projects = self.repo.active_projects(settings_df)
        if not projects:
            st.warning("有効なプロジェクトがありません。")
            return

        project = st.selectbox("プロジェクト", projects, key="apr_project")

        compound_mode = self._project_compound_mode(settings_df, project)
        is_compound = self._project_is_compound(settings_df, project)

        c1, c2 = st.columns(2)
        with c1:
            st.info(f"Compound: {'ON' if is_compound else 'OFF'}")
        with c2:
            st.info(f"Compound_Timing: {compound_mode}")

        st.subheader("APR入力")
        c3, c4 = st.columns([2, 3])
        with c3:
            apr_percent = st.number_input("APR (%)", min_value=0.0, step=0.01, value=0.0)
        with c4:
            note = st.text_input("メモ", value="")

        do_send_line = st.checkbox("APR通知をLINE送信する", value=False)

        if apr_percent <= 0:
            st.info("APRを入力してください。")
            return

        st.divider()
        st.subheader("対象メンバー")

        apr_df = self.engine.build_apr_result(
            settings_df=settings_df,
            members_df=members_df,
            project=project,
            apr_percent=apr_percent,
        )

        apr_df = self._safe_df(apr_df)

        if apr_df.empty:
            st.warning("対象メンバーがいません。")
            return

        preview = apr_df.copy()
        preview["Principal"] = pd.to_numeric(preview["Principal"], errors="coerce").fillna(0.0)
        preview["DailyAPR"] = pd.to_numeric(preview["DailyAPR"], errors="coerce").fillna(0.0)

        show = preview[["PersonName", "Principal", "Rank", "DailyAPR"]].copy()
        st.dataframe(show, use_container_width=True, hide_index=True)

        total_apr = float(preview["DailyAPR"].sum())
        st.metric("合計APR", f"{total_apr:.6f}")

        st.divider()

        today = self._today_str()
        existing_keys = self.repo.existing_apr_keys_for_date(today)
        target_keys = set(
            zip(
                preview["Project_Name"].astype(str).str.strip(),
                preview["PersonName"].astype(str).str.strip(),
            )
        )
        already_done = len(target_keys & existing_keys)
        st.caption(f"本日既存APR件数: {already_done}")

        c5, c6 = st.columns(2)

        with c5:
            if st.button("APR実行", use_container_width=True):
                save_count = self._write_apr_ledger(
                    apr_df=preview,
                    project=project,
                    apr_percent=apr_percent,
                    note=note,
                )

                self._write_apr_summary(preview)

                new_members_df = self._apply_compound_if_needed(
                    settings_df=settings_df,
                    members_df=members_df,
                    apr_df=preview,
                    project=project,
                )
                if not new_members_df.equals(members_df):
                    self.repo.write_members(new_members_df)

                ok_count, ng_count = self._send_line_if_needed(
                    apr_df=preview,
                    project=project,
                    apr_percent=apr_percent,
                    do_send=do_send_line,
                )

                self.store.persist_and_refresh()

                if do_send_line:
                    st.success(f"APR保存: {save_count}件 / LINE成功: {ok_count}件 / LINE失敗: {ng_count}件")
                else:
                    st.success(f"APR保存: {save_count}件")

                st.rerun()

        with c6:
            if st.button("本日のAPRをリセット", use_container_width=True):
                deleted_apr, deleted_line = self.repo.reset_today_apr_records(today, project)
                self.store.persist_and_refresh()
                st.success(f"APR削除: {deleted_apr}件 / LINE削除: {deleted_line}件")
                st.rerun()

        st.divider()
        st.subheader("月次未反映APR")

        pending_df = self.engine.calc_monthly_pending_from_ledger(
            ledger_df=ledger_df,
            project=project,
        )
        pending_df = self._safe_df(pending_df)

        if pending_df.empty:
            st.info("未反映APRはありません。")
        else:
            st.dataframe(pending_df, use_container_width=True, hide_index=True)


# END OF FILE
