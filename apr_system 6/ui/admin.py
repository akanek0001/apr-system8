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

    def render(self, settings_df: pd.DataFrame, members_df: pd.DataFrame, line_users_df: pd.DataFrame) -> None:
        st.subheader("⚙️ 管理")
        projects = self.repo.active_projects(settings_df)
        if not projects:
            st.warning("有効なプロジェクトがありません。")
            return

        project = st.selectbox("対象プロジェクト", projects, key="admin_project")
        line_users: List[Tuple[str, str, str]] = []
        if not line_users_df.empty:
            tmp = line_users_df[line_users_df["Line_User_ID"].astype(str).str.startswith("U")].drop_duplicates(subset=["Line_User_ID"], keep="last")
            for _, r in tmp.iterrows():
                uid = str(r["Line_User_ID"]).strip()
                name = str(r.get("Line_User", "")).strip()
                line_users.append((f"{name} ({uid})" if name else uid, uid, name))

        view_all = members_df[members_df["Project_Name"] == str(project)].copy()
        view_all["_row_id"] = view_all.index

        if not view_all.empty:
            st.markdown("#### 現在のメンバー一覧")
            show = view_all.copy()
            show["Principal"] = show["Principal"].apply(U.fmt_usd)
            show["状態"] = show["IsActive"].apply(U.bool_to_status)
            st.dataframe(show.drop(columns=["_row_id"], errors="ignore"), use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### 📨 メンバーから選択して個別にLINE送信（個人名 自動挿入）")
        if not view_all.empty:
            target_mode = st.radio("対象", ["🟢運用中のみ", "全メンバー（停止含む）"], horizontal=True)
            cand = view_all.copy() if target_mode.startswith("全") else view_all[view_all["IsActive"] == True].copy().reset_index(drop=True)

            def label_row(r: pd.Series) -> str:
                name = str(r.get("PersonName", "")).strip()
                disp = str(r.get("LINE_DisplayName", "")).strip()
                uid = str(r.get("Line_User_ID", "")).strip()
                stt = U.bool_to_status(r.get("IsActive", True))
                return f"{stt} {name} / {disp}" if disp else f"{stt} {name} / {uid}"

            options = [label_row(cand.loc[i]) for i in range(len(cand))]
            selected = st.multiselect("送信先（複数可）", options=options)
            default_msg = f"【ご連絡】\nプロジェクト: {project}\n日時: {U.now_jst().strftime('%Y/%m/%d %H:%M')}\n\n"
            msg_common = st.text_area("メッセージ本文（共通）※送信時に「〇〇 様」を自動挿入します", value=st.session_state.get("direct_line_msg", default_msg), height=180)
            st.session_state["direct_line_msg"] = msg_common
            img = st.file_uploader("添付画像（任意・ImgBB）", type=["png", "jpg", "jpeg"], key="direct_line_img")
            c1, c2 = st.columns([1, 1])
            do_send = c1.button("選択メンバーへ送信", use_container_width=True)
            clear_msg = c2.button("本文を初期化", use_container_width=True)
            if clear_msg:
                st.session_state["direct_line_msg"] = default_msg
                st.rerun()
            if do_send:
                if not selected:
                    st.warning("送信先を選択してください。")
                elif not msg_common.strip():
                    st.warning("メッセージが空です。")
                else:
                    evidence_url = ExternalService.upload_imgbb(img.getvalue()) if img else None
                    if img and not evidence_url:
                        st.error("画像アップロードに失敗しました。")
                        return
                    token = ExternalService.get_line_token(AdminAuth.current_namespace())
                    label_to_row = {label_row(cand.loc[i]): cand.loc[i] for i in range(len(cand))}
                    success, fail, failed_list, ts, line_log_count = 0, 0, [], U.fmt_dt(U.now_jst()), 0
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
                            self.repo.append_ledger(ts, project, person_name, AppConfig.TYPE["LINE"], 0, "LINE未送信: Line_User_ID不正", evidence_url or "", uid, disp)
                            line_log_count += 1
                            continue
                        code = ExternalService.send_line_push(token, uid, personalized, evidence_url)
                        self.repo.append_ledger(ts, project, person_name, AppConfig.TYPE["LINE"], 0, f"HTTP:{code}, DirectMessage", evidence_url or "", uid, disp)
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

        st.divider()
        if not view_all.empty:
            st.markdown("#### 状態切替")
            status_options = [f"{str(r['PersonName']).strip()} ｜ {U.bool_to_status(r['IsActive'])}" for _, r in view_all.iterrows()]
            selected_label = st.selectbox("対象メンバー", status_options, key=f"status_target_{project}")
            selected_name = str(selected_label).split("｜")[0].strip()
            cur_row = view_all[view_all["PersonName"].astype(str).str.strip() == selected_name].iloc[0]
            current_status = U.bool_to_status(cur_row["IsActive"])
            next_status = AppConfig.STATUS["OFF"] if U.truthy(cur_row["IsActive"]) else AppConfig.STATUS["ON"]
            if st.button(f"{current_status} → {next_status}", use_container_width=True, key=f"toggle_status_{project}"):
                row_id = int(cur_row["_row_id"])
                ts = U.fmt_dt(U.now_jst())
                members_df.loc[row_id, "IsActive"] = not U.truthy(members_df.loc[row_id, "IsActive"])
                members_df.loc[row_id, "UpdatedAt_JST"] = ts
                msg = self.repo.validate_no_dup_lineid(members_df, project)
                if msg:
                    st.error(msg)
                    return
                self.repo.write_members(members_df)
                self.store.persist_and_refresh()
                st.success(f"{selected_name} を {next_status} に更新しました。")
                st.rerun()

        st.divider()
        if not view_all.empty:
            st.markdown("#### 一括編集（保存ボタンで確定）")
            edit_src = view_all.copy()
            edit_src["状態"] = edit_src["IsActive"].apply(U.bool_to_status)
            edit_show = edit_src[["PersonName", "Principal", "Rank", "状態", "Line_User_ID", "LINE_DisplayName"]].copy()
            row_ids = edit_src["_row_id"].tolist()
            edited = st.data_editor(edit_show, use_container_width=True, hide_index=True, num_rows="fixed", column_config={
                "Principal": st.column_config.NumberColumn("Principal", min_value=0.0, step=100.0),
                "Rank": st.column_config.SelectboxColumn("Rank", options=[AppConfig.RANK["MASTER"], AppConfig.RANK["ELITE"]]),
                "状態": st.column_config.SelectboxColumn("状態", options=[AppConfig.STATUS["ON"], AppConfig.STATUS["OFF"]]),
            }, key=f"members_editor_{project}")
            c1, c2 = st.columns([1, 1])
            save = c1.button("編集内容を保存", use_container_width=True, key=f"save_members_{project}")
            cancel = c2.button("編集を破棄（再読み込み）", use_container_width=True, key=f"cancel_members_{project}")
            if cancel:
                self.store.refresh()
                st.rerun()
            if save:
                ts = U.fmt_dt(U.now_jst())
                edited = edited.copy()
                edited["_row_id"] = row_ids
                for _, r in edited.iterrows():
                    row_id = int(r["_row_id"])
                    members_df.loc[row_id, "Principal"] = float(U.to_f(r["Principal"]))
                    members_df.loc[row_id, "Rank"] = U.normalize_rank(r["Rank"])
                    members_df.loc[row_id, "IsActive"] = U.status_to_bool(r["状態"])
                    members_df.loc[row_id, "Line_User_ID"] = str(r["Line_User_ID"]).strip()
                    members_df.loc[row_id, "LINE_DisplayName"] = str(r["LINE_DisplayName"]).strip()
                    members_df.loc[row_id, "UpdatedAt_JST"] = ts
                msg = self.repo.validate_no_dup_lineid(members_df, project)
                if msg:
                    st.error(msg)
                    return
                self.repo.write_members(members_df)
                self.store.persist_and_refresh()
                st.success("保存しました。")
                st.rerun()

        st.divider()
        st.markdown("#### 追加（同一プロジェクト内で Line_User_ID が一致したら追加しない）")
        add_mode = st.selectbox("追加先", ["個人(PERSONAL)", "プロジェクト"], key="member_add_mode")
        all_projects = self.repo.active_projects(settings_df)
        if add_mode == "個人(PERSONAL)":
            selected_project = AppConfig.PROJECT["PERSONAL"]
            st.info("登録先: PERSONAL")
        else:
            project_candidates = [p for p in all_projects if str(p).strip().upper() != AppConfig.PROJECT["PERSONAL"]]
            if not project_candidates:
                st.warning("PERSONAL以外のプロジェクトがありません。")
                return
            selected_project = st.selectbox("登録するプロジェクト", project_candidates, key="member_add_target_project")
        if line_users:
            labels = ["（選択しない）"] + [x[0] for x in line_users]
            picked = st.selectbox("登録済みLINEユーザーから選択", labels, index=0)
            if picked != "（選択しない）":
                idx = labels.index(picked) - 1
                _, uid, name = line_users[idx]
                st.session_state["prefill_line_uid"] = uid
                st.session_state["prefill_line_name"] = name
        pre_uid = st.session_state.get("prefill_line_uid", "")
        pre_name = st.session_state.get("prefill_line_name", "")
        with st.form("member_add", clear_on_submit=False):
            person = st.text_input("PersonName（個人名）")
            principal = st.number_input("Principal（残高）", min_value=0.0, value=0.0, step=100.0)
            line_uid = st.text_input("Line_User_ID（Uから始まる）", value=pre_uid)
            line_disp = st.text_input("LINE_DisplayName（任意）", value=pre_name)
            rank = st.selectbox("Rank", [AppConfig.RANK["MASTER"], AppConfig.RANK["ELITE"]], index=0)
            status = st.selectbox("ステータス", [AppConfig.STATUS["ON"], AppConfig.STATUS["OFF"]], index=0)
            submit = st.form_submit_button("保存（追加）")
        if submit:
            if not person or not line_uid:
                st.error("PersonName と Line_User_ID は必須です。")
                return
            exists = members_df[(members_df["Project_Name"] == str(selected_project)) & (members_df["Line_User_ID"].astype(str).str.strip() == str(line_uid).strip())]
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
            members_df = pd.concat([members_df, pd.DataFrame([new_row])], ignore_index=True)
            msg = self.repo.validate_no_dup_lineid(members_df, selected_project)
            if msg:
                st.error(msg)
                return
            self.repo.write_members(members_df)
            self.store.persist_and_refresh()
            st.success(f"追加しました。登録先: {selected_project}")
            st.rerun()
