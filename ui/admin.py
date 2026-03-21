from __future__ import annotations

from typing import List, Tuple

import pandas as pd
import streamlit as st

from config import AppConfig
from core.auth import AdminAuth
from core.utils import U
from repository.repository import Repository
from services.external_service import ExternalService
from store.datastore import DataStore


class AdminPage:
    def __init__(self, repo: Repository, store: DataStore):
        self.repo = repo
        self.store = store

    # =========================
    # helper
    # =========================
    def _safe_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy()
        out = out.loc[:, ~out.columns.duplicated()]
        out.columns = [str(c).strip() for c in out.columns]
        out = out.fillna("")
        return out.reset_index(drop=True)

    def _line_user_options(self, line_users_df: pd.DataFrame) -> List[Tuple[str, str, str]]:
        if line_users_df is None or line_users_df.empty:
            return []

        df = self._safe_df(line_users_df)
        if "Line_User_ID" not in df.columns:
            return []

        df = df[df["Line_User_ID"].astype(str).str.startswith("U")].copy()
        df = df.drop_duplicates(subset=["Line_User_ID"], keep="last")

        options: List[Tuple[str, str, str]] = []
        for _, r in df.iterrows():
            uid = str(r.get("Line_User_ID", "")).strip()
            name = str(r.get("Line_User", "")).strip()
            label = f"{name} ({uid})" if name else uid
            options.append((label, uid, name))
        return options

    def _member_label(self, row: pd.Series) -> str:
        name = str(row.get("PersonName", "")).strip()
        disp = str(row.get("LINE_DisplayName", "")).strip()
        uid = str(row.get("Line_User_ID", "")).strip()
        stt = U.bool_to_status(row.get("IsActive", True))
        return f"{stt} {name} / {disp}" if disp else f"{stt} {name} / {uid}"

    # =========================
    # render
    # =========================
    def render(
        self,
        settings_df: pd.DataFrame,
        members_df: pd.DataFrame,
        line_users_df: pd.DataFrame,
    ) -> None:
        st.title("管理")
        st.caption(f"管理者: {AdminAuth.current_namespace()}")

        settings_df = self._safe_df(settings_df)
        members_df = self._safe_df(members_df)
        line_users_df = self._safe_df(line_users_df)

        projects = self.repo.active_projects(settings_df)
        if not projects:
            st.warning("有効なプロジェクトがありません。")
            return

        project = st.selectbox("対象プロジェクト", projects, key="admin_project")

        line_users = self._line_user_options(line_users_df)

        view_all = members_df[
            members_df["Project_Name"].astype(str).str.strip() == str(project).strip()
        ].copy()
        view_all = self._safe_df(view_all)
        view_all["_row_id"] = view_all.index

        # =========================
        # メンバー一覧
        # =========================
        if not view_all.empty:
            st.subheader("現在のメンバー一覧")

            show = view_all.copy()
            if "Principal" in show.columns:
                show["Principal"] = pd.to_numeric(show["Principal"], errors="coerce").fillna(0.0).apply(U.fmt_usd)
            if "IsActive" in show.columns:
                show["状態"] = show["IsActive"].apply(U.bool_to_status)

            st.dataframe(
                show.drop(columns=["_row_id"], errors="ignore"),
                use_container_width=True,
                hide_index=True,
            )

        # =========================
        # 個別LINE送信
        # =========================
        st.divider()
        st.subheader("メンバーへ個別LINE送信")

        if not view_all.empty:
            target_mode = st.radio(
                "対象",
                ["🟢運用中のみ", "全メンバー（停止含む）"],
                horizontal=True,
                key="admin_line_target_mode",
            )

            cand = (
                view_all.copy()
                if target_mode.startswith("全")
                else view_all[view_all["IsActive"].apply(U.truthy)].copy().reset_index(drop=True)
            )

            options = [self._member_label(cand.loc[i]) for i in range(len(cand))]
            selected = st.multiselect("送信先（複数可）", options=options, key="admin_line_targets")

            default_msg = (
                f"【ご連絡】\n"
                f"プロジェクト: {project}\n"
                f"日時: {U.now_jst().strftime('%Y/%m/%d %H:%M')}\n\n"
            )

            msg_common = st.text_area(
                "メッセージ本文（共通）※送信時に「〇〇 様」を自動挿入",
                value=st.session_state.get("direct_line_msg", default_msg),
                height=180,
                key="admin_line_msg",
            )
            st.session_state["direct_line_msg"] = msg_common

            img = st.file_uploader(
                "添付画像（任意・ImgBB）",
                type=["png", "jpg", "jpeg"],
                key="admin_line_img",
            )

            c1, c2 = st.columns([1, 1])
            do_send = c1.button("選択メンバーへ送信", use_container_width=True, key="admin_send_line")
            clear_msg = c2.button("本文を初期化", use_container_width=True, key="admin_clear_line_msg")

            if clear_msg:
                st.session_state["direct_line_msg"] = default_msg
                st.rerun()

            if do_send:
                if not selected:
                    st.warning("送信先を選択してください。")
                elif not str(msg_common).strip():
                    st.warning("メッセージが空です。")
                else:
                    evidence_url = ExternalService.upload_imgbb(img.getvalue()) if img else None
                    if img and not evidence_url:
                        st.error("画像アップロードに失敗しました。")
                        return

                    token = ExternalService.get_line_token(AdminAuth.current_namespace())
                    label_to_row = {self._member_label(cand.loc[i]): cand.loc[i] for i in range(len(cand))}

                    success = 0
                    fail = 0
                    failed_list: List[str] = []
                    ts = U.fmt_dt(U.now_jst())
                    line_log_count = 0

                    for lab in selected:
                        r = label_to_row.get(lab)
                        if r is None:
                            fail += 1
                            failed_list.append(lab)
                            continue

                        uid = str(r.get("Line_User_ID", "")).strip()
                        person_name = str(r.get("PersonName", "")).strip()
                        disp = str(r.get("LINE_DisplayName", "")).strip()
                        personalized = U.insert_person_name(msg_common, person_name)

                        if not U.is_line_uid(uid):
                            fail += 1
                            failed_list.append(f"{lab}（Line_User_ID不正）")
                            self.repo.append_ledger(
                                dt_jst=ts,
                                project=project,
                                person_name=person_name,
                                typ=AppConfig.TYPE["LINE"],
                                amount=0,
                                note="LINE未送信: Line_User_ID不正",
                                evidence_url=evidence_url or "",
                                line_user_id=uid,
                                line_display_name=disp,
                                source=AppConfig.SOURCE["APP"],
                            )
                            line_log_count += 1
                            continue

                        code = ExternalService.send_line_push(token, uid, personalized, evidence_url)
                        self.repo.append_ledger(
                            dt_jst=ts,
                            project=project,
                            person_name=person_name,
                            typ=AppConfig.TYPE["LINE"],
                            amount=0,
                            note=f"HTTP:{code}, DirectMessage",
                            evidence_url=evidence_url or "",
                            line_user_id=uid,
                            line_display_name=disp,
                            source=AppConfig.SOURCE["APP"],
                        )
                        line_log_count += 1

                        if code == 200:
                            success += 1
                        else:
                            fail += 1
                            failed_list.append(f"{lab}（HTTP {code}）")

                    self.store.persist_and_refresh()

                    if fail == 0:
                        st.success(f"送信完了（成功:{success} / 失敗:{fail} / Ledger記録:{line_log_count}）")
                    else:
                        st.warning(f"送信結果（成功:{success} / 失敗:{fail} / Ledger記録:{line_log_count}）")
                        with st.expander("失敗詳細", expanded=False):
                            st.write("\n".join(failed_list))

        # =========================
        # 状態切替
        # =========================
        st.divider()
        if not view_all.empty:
            st.subheader("状態切替")

            status_options = [
                f"{str(r['PersonName']).strip()} ｜ {U.bool_to_status(r['IsActive'])}"
                for _, r in view_all.iterrows()
            ]
            selected_label = st.selectbox("対象メンバー", status_options, key=f"status_target_{project}")
            selected_name = str(selected_label).split("｜")[0].strip()

            cur_row = view_all[view_all["PersonName"].astype(str).str.strip() == selected_name].iloc[0]
            current_status = U.bool_to_status(cur_row["IsActive"])
            next_status = AppConfig.STATUS["OFF"] if U.truthy(cur_row["IsActive"]) else AppConfig.STATUS["ON"]

            if st.button(f"{current_status} → {next_status}", use_container_width=True, key=f"toggle_status_{project}"):
                raw_members_df = self.repo.load_members()
                raw_members_df = self._safe_df(raw_members_df)

                mask = (
                    raw_members_df["Project_Name"].astype(str).str.strip() == str(project).strip()
                ) & (
                    raw_members_df["PersonName"].astype(str).str.strip() == str(selected_name).strip()
                )

                raw_members_df.loc[mask, "IsActive"] = not U.truthy(cur_row["IsActive"])
                raw_members_df.loc[mask, "UpdatedAt_JST"] = U.fmt_dt(U.now_jst())

                msg = self.repo.validate_no_dup_lineid(raw_members_df, project)
                if msg:
                    st.error(msg)
                    return

                self.repo.write_members(raw_members_df)
                self.store.persist_and_refresh()
                st.success(f"{selected_name} を {next_status} に更新しました。")
                st.rerun()

        # =========================
        # 一括編集
        # =========================
        st.divider()
        if not view_all.empty:
            st.subheader("一括編集")

            edit_src = view_all.copy()
            edit_src["状態"] = edit_src["IsActive"].apply(U.bool_to_status)

            edit_show = edit_src[
                ["PersonName", "Principal", "Rank", "状態", "Line_User_ID", "LINE_DisplayName"]
            ].copy()

            row_keys = (
                edit_src["Project_Name"].astype(str).str.strip()
                + "||"
                + edit_src["PersonName"].astype(str).str.strip()
            ).tolist()

            edited = st.data_editor(
                edit_show,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "Principal": st.column_config.NumberColumn("Principal", min_value=0.0, step=100.0),
                    "Rank": st.column_config.SelectboxColumn(
                        "Rank",
                        options=[AppConfig.RANK["MASTER"], AppConfig.RANK["ELITE"]],
                    ),
                    "状態": st.column_config.SelectboxColumn(
                        "状態",
                        options=[AppConfig.STATUS["ON"], AppConfig.STATUS["OFF"]],
                    ),
                },
                key=f"members_editor_{project}",
            )

            c1, c2 = st.columns([1, 1])
            save = c1.button("編集内容を保存", use_container_width=True, key=f"save_members_{project}")
            cancel = c2.button("編集を破棄（再読み込み）", use_container_width=True, key=f"cancel_members_{project}")

            if cancel:
                self.store.refresh()
                st.rerun()

            if save:
                raw_members_df = self.repo.load_members()
                raw_members_df = self._safe_df(raw_members_df)

                edited = edited.copy()
                edited["_row_key"] = row_keys
                ts = U.fmt_dt(U.now_jst())

                for _, r in edited.iterrows():
                    row_key = str(r["_row_key"]).strip()
                    p_name = row_key.split("||", 1)[1]

                    mask = (
                        raw_members_df["Project_Name"].astype(str).str.strip() == str(project).strip()
                    ) & (
                        raw_members_df["PersonName"].astype(str).str.strip() == str(p_name).strip()
                    )

                    raw_members_df.loc[mask, "Principal"] = float(U.to_f(r["Principal"]))
                    raw_members_df.loc[mask, "Rank"] = U.normalize_rank(r["Rank"])
                    raw_members_df.loc[mask, "IsActive"] = U.status_to_bool(r["状態"])
                    raw_members_df.loc[mask, "Line_User_ID"] = str(r["Line_User_ID"]).strip()
                    raw_members_df.loc[mask, "LINE_DisplayName"] = str(r["LINE_DisplayName"]).strip()
                    raw_members_df.loc[mask, "UpdatedAt_JST"] = ts

                msg = self.repo.validate_no_dup_lineid(raw_members_df, project)
                if msg:
                    st.error(msg)
                    return

                self.repo.write_members(raw_members_df)
                self.store.persist_and_refresh()
                st.success("保存しました。")
                st.rerun()

        # =========================
        # 追加
        # =========================
        st.divider()
        st.subheader("メンバー追加")

        add_mode = st.selectbox(
            "追加先",
            ["個人(PERSONAL)", "プロジェクト"],
            key="member_add_mode",
        )

        if add_mode == "個人(PERSONAL)":
            selected_project = AppConfig.PROJECT["PERSONAL"]
            st.info("登録先: PERSONAL")
        else:
            project_candidates = [
                p for p in projects if str(p).strip().upper() != AppConfig.PROJECT["PERSONAL"]
            ]
            if not project_candidates:
                st.warning("PERSONAL 以外のプロジェクトがありません。")
                return
            selected_project = st.selectbox(
                "登録するプロジェクト",
                project_candidates,
                key="member_add_target_project",
            )

        if line_users:
            labels = ["（選択しない）"] + [x[0] for x in line_users]
            picked = st.selectbox("登録済みLINEユーザーから選択", labels, index=0, key="member_add_lineuser_pick")

            if picked != "（選択しない）":
                idx = labels.index(picked) - 1
                _, uid, name = line_users[idx]
                st.session_state["prefill_line_uid"] = uid
                st.session_state["prefill_line_name"] = name

        pre_uid = st.session_state.get("prefill_line_uid", "")
        pre_name = st.session_state.get("prefill_line_name", "")

        with st.form("member_add_form", clear_on_submit=False):
            person = st.text_input("PersonName（個人名）")
            principal = st.number_input("Principal（残高）", min_value=0.0, value=0.0, step=100.0)
            line_uid = st.text_input("Line_User_ID（Uから始まる）", value=pre_uid)
            line_disp = st.text_input("LINE_DisplayName（任意）", value=pre_name)
            rank = st.selectbox("Rank", [AppConfig.RANK["MASTER"], AppConfig.RANK["ELITE"]], index=0)
            status = st.selectbox("ステータス", [AppConfig.STATUS["ON"], AppConfig.STATUS["OFF"]], index=0)
            submit = st.form_submit_button("保存（追加）")

        if submit:
            if not str(person).strip() or not str(line_uid).strip():
                st.error("PersonName と Line_User_ID は必須です。")
                return

            raw_members_df = self.repo.load_members()
            raw_members_df = self._safe_df(raw_members_df)

            exists = raw_members_df[
                (raw_members_df["Project_Name"].astype(str).str.strip() == str(selected_project).strip())
                & (raw_members_df["Line_User_ID"].astype(str).str.strip() == str(line_uid).strip())
            ]

            if not exists.empty:
                st.warning("このプロジェクト内に同じ Line_User_ID が既に存在します。")
                return

            ts = U.fmt_dt(U.now_jst())
            new_row = {
                "Project_Name": str(selected_project).strip(),
                "PersonName": str(person).strip(),
                "Principal": float(principal),
                "Line_User_ID": str(line_uid).strip(),
                "LINE_DisplayName": str(line_disp).strip(),
                "Rank": U.normalize_rank(rank),
                "IsActive": U.status_to_bool(status),
                "CreatedAt_JST": ts,
                "UpdatedAt_JST": ts,
            }

            raw_members_df = pd.concat([raw_members_df, pd.DataFrame([new_row])], ignore_index=True)

            msg = self.repo.validate_no_dup_lineid(raw_members_df, selected_project)
            if msg:
                st.error(msg)
                return

            self.repo.write_members(raw_members_df)
            self.store.persist_and_refresh()
            st.success(f"追加しました。登録先: {selected_project}")
            st.rerun()

        # =========================
        # Settings / LineUsers 表示
        # =========================
        st.divider()
        tab1, tab2 = st.tabs(["Settings", "LineUsers"])

        with tab1:
            st.subheader("Settings")
            show_settings = settings_df[
                settings_df["Project_Name"].astype(str).str.strip() == str(project).strip()
            ].copy()
            if show_settings.empty:
                st.info("Settings は空です。")
            else:
                st.dataframe(show_settings, use_container_width=True, hide_index=True)

        with tab2:
            st.subheader("LineUsers")
            if line_users_df.empty:
                st.info("LineUsers は空です。")
            else:
                st.dataframe(line_users_df, use_container_width=True, hide_index=True)


# END OF FILE
