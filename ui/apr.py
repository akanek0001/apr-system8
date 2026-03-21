from __future__ import annotations

from typing import Any, Dict, List, Tuple

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

    def _ocr_crop_text(self, file_bytes: bytes, box: Dict[str, float]) -> str:
        return ExternalService.ocr_space_extract_text_with_crop(
            file_bytes=file_bytes,
            crop_left_ratio=box["left"],
            crop_top_ratio=box["top"],
            crop_right_ratio=box["right"],
            crop_bottom_ratio=box["bottom"],
        )

    def _ocr_smartvault_mobile_metrics(self, file_bytes: bytes) -> Dict[str, Any]:
        boxes = AppConfig.SMARTVAULT_BOXES_MOBILE
        total_text = self._ocr_crop_text(file_bytes, boxes["TOTAL_LIQUIDITY"])
        profit_text = self._ocr_crop_text(file_bytes, boxes["YESTERDAY_PROFIT"])
        apr_text = self._ocr_crop_text(file_bytes, boxes["APR"])
        total_vals = U.extract_usd_candidates(total_text)
        profit_vals = U.extract_usd_candidates(profit_text)
        apr_vals = U.extract_percent_candidates(apr_text)
        total_liquidity = U.pick_total_liquidity(total_vals)
        yesterday_profit = U.pick_yesterday_profit(profit_vals)
        apr_value = apr_vals[0] if apr_vals else None
        boxed_preview = U.draw_ocr_boxes(file_bytes, boxes)
        return {
            "boxes": boxes,
            "total_text": total_text,
            "profit_text": profit_text,
            "apr_text": apr_text,
            "total_vals": total_vals,
            "profit_vals": profit_vals,
            "apr_vals": apr_vals,
            "total_liquidity": total_liquidity,
            "yesterday_profit": yesterday_profit,
            "apr_value": apr_value,
            "boxed_preview": boxed_preview,
        }

    def render(self, settings_df: pd.DataFrame, members_df: pd.DataFrame) -> None:
        st.subheader("📈 APR 確定")
        st.caption(f"{AppConfig.RANK_LABEL} / PERSONAL=個別計算 / GROUP=総額均等割 / 管理者: {AdminAuth.current_label()}")

        projects = self.repo.active_projects(settings_df)
        if not projects:
            st.warning("有効（Active=TRUE）のプロジェクトがありません。")
            return

        project = st.selectbox("基準プロジェクト", projects)
        send_scope = st.radio("送信対象", ["選択中プロジェクトのみ", "全有効プロジェクト"], horizontal=True)

        st.markdown("#### 流動性 / 昨日の収益 / APR（別取得・手動設定可）")
        c1, c2, c3 = st.columns(3)
        with c1:
            total_liquidity_raw = st.text_input("流動性（手動設定可）", value=st.session_state.get("sv_total_liquidity", ""), key="sv_total_liquidity", placeholder="$78,354.35")
        with c2:
            yesterday_profit_raw = st.text_input("昨日の収益（手動設定可）", value=st.session_state.get("sv_yesterday_profit", ""), key="sv_yesterday_profit", placeholder="$90.87")
        with c3:
            apr_raw = st.text_input("APR（%・手動設定可）", value=st.session_state.get("sv_apr", ""), key="sv_apr", placeholder="42.33")

        total_liquidity = U.to_f(total_liquidity_raw)
        yesterday_profit = U.to_f(yesterday_profit_raw)
        apr = U.apr_val(apr_raw)

        st.info(f"流動性 = {U.fmt_usd(total_liquidity)} / 昨日の収益 = {U.fmt_usd(yesterday_profit)} / 最終APR = {apr:.4f}%")
        uploaded = st.file_uploader("エビデンス画像（任意）", type=["png", "jpg", "jpeg"], key="apr_img")

        if uploaded is not None and st.button("OCRで別取得"):
            file_bytes = uploaded.getvalue()
            crop_left_ratio = AppConfig.OCR_DEFAULTS_PC["Crop_Left_Ratio_PC"]
            crop_top_ratio = AppConfig.OCR_DEFAULTS_PC["Crop_Top_Ratio_PC"]
            crop_right_ratio = AppConfig.OCR_DEFAULTS_PC["Crop_Right_Ratio_PC"]
            crop_bottom_ratio = AppConfig.OCR_DEFAULTS_PC["Crop_Bottom_Ratio_PC"]
            try:
                srow = settings_df[settings_df["Project_Name"] == str(project)].iloc[0]
                if U.is_mobile_tall_image(file_bytes):
                    crop_left_ratio = U.to_ratio(srow.get("Crop_Left_Ratio_Mobile", AppConfig.OCR_DEFAULTS_MOBILE["Crop_Left_Ratio_Mobile"]), AppConfig.OCR_DEFAULTS_MOBILE["Crop_Left_Ratio_Mobile"])
                    crop_top_ratio = U.to_ratio(srow.get("Crop_Top_Ratio_Mobile", AppConfig.OCR_DEFAULTS_MOBILE["Crop_Top_Ratio_Mobile"]), AppConfig.OCR_DEFAULTS_MOBILE["Crop_Top_Ratio_Mobile"])
                    crop_right_ratio = U.to_ratio(srow.get("Crop_Right_Ratio_Mobile", AppConfig.OCR_DEFAULTS_MOBILE["Crop_Right_Ratio_Mobile"]), AppConfig.OCR_DEFAULTS_MOBILE["Crop_Right_Ratio_Mobile"])
                    crop_bottom_ratio = U.to_ratio(srow.get("Crop_Bottom_Ratio_Mobile", AppConfig.OCR_DEFAULTS_MOBILE["Crop_Bottom_Ratio_Mobile"]), AppConfig.OCR_DEFAULTS_MOBILE["Crop_Bottom_Ratio_Mobile"])
                else:
                    crop_left_ratio = U.to_ratio(srow.get("Crop_Left_Ratio_PC", AppConfig.OCR_DEFAULTS_PC["Crop_Left_Ratio_PC"]), AppConfig.OCR_DEFAULTS_PC["Crop_Left_Ratio_PC"])
                    crop_top_ratio = U.to_ratio(srow.get("Crop_Top_Ratio_PC", AppConfig.OCR_DEFAULTS_PC["Crop_Top_Ratio_PC"]), AppConfig.OCR_DEFAULTS_PC["Crop_Top_Ratio_PC"])
                    crop_right_ratio = U.to_ratio(srow.get("Crop_Right_Ratio_PC", AppConfig.OCR_DEFAULTS_PC["Crop_Right_Ratio_PC"]), AppConfig.OCR_DEFAULTS_PC["Crop_Right_Ratio_PC"])
                    crop_bottom_ratio = U.to_ratio(srow.get("Crop_Bottom_Ratio_PC", AppConfig.OCR_DEFAULTS_PC["Crop_Bottom_Ratio_PC"]), AppConfig.OCR_DEFAULTS_PC["Crop_Bottom_Ratio_PC"])
            except Exception:
                pass

            raw_text = ExternalService.ocr_space_extract_text_with_crop(file_bytes, crop_left_ratio, crop_top_ratio, crop_right_ratio, crop_bottom_ratio)
            if raw_text:
                with st.expander("OCR生テキスト（通常範囲）", expanded=False):
                    st.text(raw_text)
            st.info(f"OCR切り抜き範囲: left={crop_left_ratio:.3f}, top={crop_top_ratio:.3f}, right={crop_right_ratio:.3f}, bottom={crop_bottom_ratio:.3f}")

            if U.is_mobile_tall_image(file_bytes):
                smart = self._ocr_smartvault_mobile_metrics(file_bytes)
                st.markdown("#### SmartVaultモバイル専用OCR結果")
                st.image(smart["boxed_preview"], caption="赤枠 = OCR対象範囲", use_container_width=True)
                c_a, c_b, c_c = st.columns(3)
                with c_a:
                    st.success(f"流動性: {U.fmt_usd(float(smart['total_liquidity']))}") if smart["total_liquidity"] is not None else st.warning("流動性: 未検出")
                with c_b:
                    st.success(f"昨日の収益: {U.fmt_usd(float(smart['yesterday_profit']))}") if smart["yesterday_profit"] is not None else st.warning("昨日の収益: 未検出")
                with c_c:
                    st.success(f"APR: {float(smart['apr_value']):.2f}%") if smart["apr_value"] is not None else st.warning("APR: 未検出")
                if smart["total_liquidity"] is not None:
                    st.session_state["sv_total_liquidity"] = f"{float(smart['total_liquidity']):,.2f}"
                    st.session_state["ocr_total_liquidity"] = float(smart["total_liquidity"])
                if smart["yesterday_profit"] is not None:
                    st.session_state["sv_yesterday_profit"] = f"{float(smart['yesterday_profit']):,.2f}"
                    st.session_state["ocr_yesterday_profit"] = float(smart["yesterday_profit"])
                if smart["apr_value"] is not None:
                    st.session_state["sv_apr"] = f"{float(smart['apr_value']):.4f}"
                    st.session_state["ocr_apr"] = float(smart["apr_value"])
                st.rerun()
            else:
                apr_candidates = U.extract_percent_candidates(raw_text)
                if apr_candidates:
                    best = apr_candidates[0]
                    st.success(f"通常OCRからAPR候補を検出: {best}%")
                    st.session_state["sv_apr"] = f"{float(best):.4f}"
                    st.session_state["ocr_apr"] = float(best)
                    st.rerun()
                else:
                    st.warning("APR候補は見つかりませんでした。")

        target_projects = projects if send_scope == "全有効プロジェクト" else [project]
        today_key = U.fmt_date(U.now_jst())
        existing_apr_keys = self.repo.existing_apr_keys_for_date(today_key)
        preview_rows: List[dict] = []
        total_members, total_principal, total_reward, skipped_members = 0, 0.0, 0.0, 0

        for p in target_projects:
            row = settings_df[settings_df["Project_Name"] == str(p)].iloc[0]
            project_net_factor = float(row.get("Net_Factor", AppConfig.FACTOR["MASTER"]))
            compound_timing = U.normalize_compound(row.get("Compound_Timing", AppConfig.COMPOUND["NONE"]))
            mem = self.repo.project_members_active(members_df, p)
            if mem.empty:
                continue
            mem_calc = self.engine.calc_project_apr(mem, float(apr), project_net_factor, p)
            for _, r in mem_calc.iterrows():
                person = str(r["PersonName"]).strip()
                is_done = (str(p).strip(), person) in existing_apr_keys
                if is_done:
                    skipped_members += 1
                else:
                    total_members += 1
                    total_principal += float(r["Principal"])
                    total_reward += float(r["DailyAPR"])
                preview_rows.append({
                    "Project_Name": p,
                    "PersonName": person,
                    "Rank": str(r["Rank"]).strip(),
                    "Compound_Timing": U.compound_label(compound_timing),
                    "Principal": U.fmt_usd(float(r["Principal"])),
                    "DailyAPR": U.fmt_usd(float(r["DailyAPR"])),
                    "Line_User_ID": str(r["Line_User_ID"]).strip(),
                    "LINE_DisplayName": str(r["LINE_DisplayName"]).strip(),
                    "流動性": U.fmt_usd(float(total_liquidity)),
                    "昨日の収益": U.fmt_usd(float(yesterday_profit)),
                    "APR": f"{apr:.4f}%",
                    "本日APR状態": "本日記録済み" if is_done else "未記録",
                })

        if total_members == 0 and skipped_members == 0:
            st.warning("送信対象に 🟢運用中 のメンバーがいません。")
            return

        st.markdown(f"送信対象プロジェクト数: {len(target_projects)} / 本日未記録の対象人数: {total_members} / 本日記録済み人数: {skipped_members}")
        apr_percent_display = (total_reward / total_principal * 100.0) if total_principal > 0 else 0.0

        csum1, csum2 = st.columns([1.2, 2.8])
        with csum1:
            if send_scope == "選択中プロジェクトのみ":
                if st.button("本日のAPR記録をリセット", key="reset_today_apr_top", use_container_width=True):
                    try:
                        deleted_apr, deleted_line = self.repo.reset_today_apr_records(today_key, project)
                        self.store.persist_and_refresh()
                        st.info("削除対象はありません。") if deleted_apr == 0 and deleted_line == 0 else st.success(f"本日分をリセットしました。APR削除:{deleted_apr}件 / LINE削除:{deleted_line}件")
                        st.rerun()
                    except Exception as e:
                        st.error(f"APRリセットでエラー: {e}")
                        st.stop()

        with csum2:
            st.markdown(f"""
**本日対象サマリー**  
流動性: **{U.fmt_usd(total_liquidity)}**　/　昨日の収益: **{U.fmt_usd(yesterday_profit)}**　/　最終APR: **{apr:.4f}%**  
総投資額: **{U.fmt_usd(total_principal)}**　/　APR合計: **{U.fmt_usd(total_reward)}**　/　実効APR: **{apr_percent_display:.4f}%**
""")

        with st.expander("個人別の本日配当（確認）", expanded=False):
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

        if st.button("APRを確定して対象全員にLINE送信"):
            try:
                if apr <= 0:
                    st.warning("APRが0以下です。")
                    return
                evidence_url = None
                if uploaded:
                    evidence_url = ExternalService.upload_imgbb(uploaded.getvalue())
                    if not evidence_url:
                        st.error("画像アップロードに失敗しました。")
                        return
                source_mode = U.detect_source_mode(float(total_liquidity), float(yesterday_profit), float(apr), st.session_state.get("ocr_total_liquidity"), st.session_state.get("ocr_yesterday_profit"), st.session_state.get("ocr_apr"))
                ts = U.fmt_dt(U.now_jst())
                apr_ledger_count, line_log_count, success, fail, skip_count = 0, 0, 0, 0, 0
                existing_apr_keys = self.repo.existing_apr_keys_for_date(today_key)
                token = ExternalService.get_line_token(AdminAuth.current_namespace())
                daily_add_map: Dict[Tuple[str, str], float] = {}

                self.repo.append_smartvault_history(ts, project, float(total_liquidity), float(yesterday_profit), float(apr), source_mode, st.session_state.get("ocr_total_liquidity"), st.session_state.get("ocr_yesterday_profit"), st.session_state.get("ocr_apr"), evidence_url or "", AdminAuth.current_name(), AdminAuth.current_namespace(), "APR確定時に保存")

                for p in target_projects:
                    row = settings_df[settings_df["Project_Name"] == str(p)].iloc[0]
                    project_net_factor = float(row.get("Net_Factor", AppConfig.FACTOR["MASTER"]))
                    compound_timing = U.normalize_compound(row.get("Compound_Timing", AppConfig.COMPOUND["NONE"]))
                    mem = self.repo.project_members_active(members_df, p)
                    if mem.empty:
                        continue
                    mem_calc = self.engine.calc_project_apr(mem, float(apr), project_net_factor, p)
                    for _, r in mem_calc.iterrows():
                        person = str(r["PersonName"]).strip()
                        uid = str(r["Line_User_ID"]).strip()
                        disp = str(r["LINE_DisplayName"]).strip()
                        daily_apr = float(r["DailyAPR"])
                        current_principal = float(r["Principal"])
                        apr_key = (str(p).strip(), person)
                        if apr_key in existing_apr_keys:
                            skip_count += 1
                            continue
                        note = f"APR:{apr}%, Liquidity:{total_liquidity}, YesterdayProfit:{yesterday_profit}, SourceMode:{source_mode}, Mode:{r['CalcMode']}, Rank:{r['Rank']}, Factor:{r['Factor']}, CompoundTiming:{compound_timing}"
                        self.repo.append_ledger(ts, p, person, AppConfig.TYPE["APR"], daily_apr, note, evidence_url or "", uid, disp)
                        existing_apr_keys.add(apr_key)
                        apr_ledger_count += 1
                        if compound_timing == AppConfig.COMPOUND["DAILY"]:
                            daily_add_map[(str(p).strip(), person)] = daily_add_map.get((str(p).strip(), person), 0.0) + daily_apr
                            person_after_amount = current_principal + daily_apr
                        else:
                            person_after_amount = current_principal
                        personalized_msg = (
                            "🏦【APR収益報告】\n"
                            f"{person} 様\n"
                            f"報告日時: {U.now_jst().strftime('%Y/%m/%d %H:%M')}\n"
                            f"流動性: {U.fmt_usd(total_liquidity)}\n"
                            f"昨日の収益: {U.fmt_usd(yesterday_profit)}\n"
                            f"APR: {apr:.4f}%\n"
                            f"本日配当: {U.fmt_usd(daily_apr)}\n"
                            f"現在運用額: {U.fmt_usd(current_principal)}\n"
                            f"複利タイプ: {U.compound_label(compound_timing)}\n"
                        )
                        if compound_timing == AppConfig.COMPOUND["DAILY"]:
                            personalized_msg += f"複利反映後運用額: {U.fmt_usd(person_after_amount)}\n"
                        if not uid:
                            code, line_note = 0, "LINE未送信: Line_User_IDなし"
                        else:
                            code = ExternalService.send_line_push(token, uid, personalized_msg, evidence_url)
                            line_note = f"HTTP:{code}, Liquidity:{total_liquidity}, YesterdayProfit:{yesterday_profit}, APR:{apr}%, SourceMode:{source_mode}, CompoundTiming:{compound_timing}"
                        self.repo.append_ledger(ts, p, person, AppConfig.TYPE["LINE"], 0, line_note, evidence_url or "", uid, disp)
                        line_log_count += 1
                        if code == 200:
                            success += 1
                        else:
                            fail += 1

                if daily_add_map:
                    for i in range(len(members_df)):
                        p = str(members_df.loc[i, "Project_Name"]).strip()
                        pn = str(members_df.loc[i, "PersonName"]).strip()
                        addv = float(daily_add_map.get((p, pn), 0.0))
                        if addv != 0.0 and U.truthy(members_df.loc[i, "IsActive"]):
                            members_df.loc[i, "Principal"] = float(members_df.loc[i, "Principal"]) + addv
                            members_df.loc[i, "UpdatedAt_JST"] = ts
                    self.repo.write_members(members_df)

                self.store.persist_and_refresh()
                st.success(f"APR記録:{apr_ledger_count}件 / LINE履歴記録:{line_log_count}件 / 送信成功:{success} / 送信失敗:{fail} / 重複スキップ:{skip_count}件")
                st.rerun()
            except Exception as e:
                st.error(f"APR確定処理でエラー: {e}")
                st.stop()

        if send_scope == "選択中プロジェクトのみ":
            row = settings_df[settings_df["Project_Name"] == str(project)].iloc[0]
            compound_timing = U.normalize_compound(row.get("Compound_Timing", AppConfig.COMPOUND["NONE"]))
            if compound_timing == AppConfig.COMPOUND["MONTHLY"]:
                st.divider()
                st.markdown("#### 月次複利反映")
                if st.button("未反映APRを元本へ反映"):
                    try:
                        count, total_added = self.engine.apply_monthly_compound(self.repo, members_df, project)
                        self.store.persist_and_refresh()
                        st.info("未反映のAPRはありません。") if count == 0 else st.success(f"{count}名に反映しました。合計反映額: {U.fmt_usd(total_added)}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"月次複利反映でエラー: {e}")
                        st.stop()
