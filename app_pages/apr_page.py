from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from config import AppConfig
from repository.repository import Repository
from services.external_service import ExternalService
from services.ocr_processor import OCRProcessor


class APRPage:
    OCR_TX_HISTORY_SHEET = "OCR_Transaction_History"
    OCR_TX_HISTORY_HEADERS = [
        "Unique_Key",
        "Date_Label",
        "Time_Label",
        "Type_Label",
        "Amount_USD",
        "Token_Amount",
        "Token_Symbol",
        "Source_Image",
        "Source_Project",
        "OCR_Raw_Text",
        "CreatedAt_JST",
    ]

    def __init__(self, repo: Repository):
        self.repo = repo

    def _to_float(self, value) -> float:
        try:
            s = str(value).replace(",", "").replace("$", "").replace("%", "").strip()
            return float(s)
        except Exception:
            return 0.0

    def _truthy(self, value) -> bool:
        return str(value).strip().lower() in {"true", "1", "yes", "on", "🟢運用中"}

    def _normalize_rank(self, value: object) -> str:
        s = str(value).strip().lower()
        if s == "elite":
            return AppConfig.RANK["ELITE"]
        return AppConfig.RANK["MASTER"]

    def _rank_factor(self, rank: str) -> float:
        if self._normalize_rank(rank) == AppConfig.RANK["ELITE"]:
            return float(AppConfig.FACTOR["ELITE"])
        return float(AppConfig.FACTOR["MASTER"])

    def _safe_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        out = df.copy().fillna("")
        out.columns = [str(c) for c in out.columns]
        for c in out.columns:
            out[c] = out[c].astype(str)
        return out.reset_index(drop=True)

    def _folder_image_files(self, folder_path: str) -> List[Path]:
        path = Path(folder_path).expanduser()
        if not path.exists() or not path.is_dir():
            return []
        exts = {".png", ".jpg", ".jpeg", ".webp"}
        files = [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in exts]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def _get_default_watch_folder(self) -> str:
        try:
            return str(st.secrets.get("local_paths", {}).get("apr_watch_folder", "")).strip()
        except Exception:
            return ""

    def _ensure_ocr_tx_history_sheet(self) -> None:
        try:
            self.repo.gs.ensure_sheet(self.OCR_TX_HISTORY_SHEET, self.OCR_TX_HISTORY_HEADERS)
        except Exception:
            pass

    def _load_existing_ocr_tx_keys(self) -> set[str]:
        self._ensure_ocr_tx_history_sheet()
        try:
            df = self.repo.gs.load_df(self.OCR_TX_HISTORY_SHEET)
        except Exception:
            return set()
        if df is None or df.empty or "Unique_Key" not in df.columns:
            return set()
        return set(df["Unique_Key"].astype(str).str.strip().replace("", pd.NA).dropna().tolist())

    def _append_ocr_tx_rows(self, rows: List[List[Any]]) -> None:
        if not rows:
            return
        self._ensure_ocr_tx_history_sheet()
        current = self.repo.gs.load_df(self.OCR_TX_HISTORY_SHEET)
        new_df = pd.DataFrame(rows, columns=self.OCR_TX_HISTORY_HEADERS)
        if current is None or current.empty:
            out = new_df
        else:
            out = pd.concat([current, new_df], ignore_index=True)
        self.repo.gs.write_df(self.OCR_TX_HISTORY_SHEET, out)

    def _apply_ocr_result(self, file_bytes: bytes, settings_df: pd.DataFrame, project: str) -> None:
        platform = OCRProcessor.detect_platform(file_bytes)
        if platform != "mobile":
            st.warning("この版では SmartVault OCR は mobile 画像のみ対応です。")
            return

        boxes = OCRProcessor.get_smartvault_boxes(settings_df, project, platform)
        smart = OCRProcessor.extract_metrics(file_bytes, boxes)

        st.image(smart["preview"], caption="SmartVault OCR対象範囲", width=500)

        c1, c2, c3 = st.columns(3)
        c1.metric("流動性", "-" if smart["total_liquidity"] is None else f"${float(smart['total_liquidity']):,.2f}")
        c2.metric("昨日の収益", "-" if smart["yesterday_profit"] is None else f"${float(smart['yesterday_profit']):,.2f}")
        c3.metric("APR", "-" if smart["apr_value"] is None else f"{float(smart['apr_value']):.2f}%")

        if smart["total_liquidity"] is not None:
            st.session_state["sv_total_liquidity"] = f"{float(smart['total_liquidity']):,.2f}"
        if smart["yesterday_profit"] is not None:
            st.session_state["sv_yesterday_profit"] = f"{float(smart['yesterday_profit']):,.2f}"
        if smart["apr_value"] is not None:
            st.session_state["sv_apr"] = f"{float(smart['apr_value']):.4f}"

        with st.expander("OCR生テキスト", expanded=False):
            st.write("TOTAL_LIQUIDITY")
            st.text(smart["total_text"])
            st.write("YESTERDAY_PROFIT")
            st.text(smart["profit_text"])
            st.write("APR")
            st.text(smart["apr_text"])

    def _process_transaction_ocr(self, file_bytes: bytes, source_image: str, source_project: str, settings_df: pd.DataFrame, project: str) -> None:
        tx_rows = OCRProcessor.extract_transaction_rows(file_bytes, settings_df, project)
        if not tx_rows:
            st.warning("受け取ったUSDCの取引明細を抽出できませんでした。")
            return

        existing_keys = self._load_existing_ocr_tx_keys()
        created_at = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d %H:%M:%S")

        new_sheet_rows: List[List[Any]] = []
        view_rows: List[Dict[str, Any]] = []
        total_detected = 0.0
        total_new = 0.0
        duplicate_count = 0

        for row in tx_rows:
            unique_key = str(row["unique_key"]).strip()
            amount_usd = float(row["amount_usd"])
            is_duplicate = unique_key in existing_keys
            total_detected += amount_usd

            if is_duplicate:
                duplicate_count += 1
            else:
                existing_keys.add(unique_key)
                total_new += amount_usd
                new_sheet_rows.append(
                    [
                        unique_key,
                        row["date_label"],
                        row["time_label"],
                        row["type_label"],
                        amount_usd,
                        "",
                        "",
                        source_image,
                        source_project,
                        row["raw_text"],
                        created_at,
                    ]
                )

            view_rows.append(
                {
                    "Row": row["row_index"],
                    "Date_Label": row["date_label"],
                    "Time_Label": row["time_label"],
                    "Type_Label": row["type_label"],
                    "Amount_USD": f"{amount_usd:.2f}",
                    "Unique_Key": unique_key,
                    "Status": "重複" if is_duplicate else "新規",
                }
            )

        if new_sheet_rows:
            self._append_ocr_tx_rows(new_sheet_rows)

        st.dataframe(self._safe_df(pd.DataFrame(view_rows)), use_container_width=True, hide_index=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("検出合計USD", f"${total_detected:,.2f}")
        c2.metric("新規追加USD", f"${total_new:,.2f}")
        c3.metric("重複件数", duplicate_count)

    def _build_calc_df(self, members_df: pd.DataFrame, project: str, apr_percent: float) -> pd.DataFrame:
        if members_df is None or members_df.empty:
            return pd.DataFrame()

        df = members_df.copy()
        df = df[df["Project_Name"].astype(str).str.strip() == str(project).strip()].copy()

        if "IsActive" in df.columns:
            df = df[df["IsActive"].apply(self._truthy)].copy()

        if df.empty:
            return pd.DataFrame()

        if "Principal" not in df.columns:
            df["Principal"] = 0.0
        if "Rank" not in df.columns:
            df["Rank"] = AppConfig.RANK["MASTER"]
        if "Line_User_ID" not in df.columns:
            df["Line_User_ID"] = ""
        if "LINE_DisplayName" not in df.columns:
            df["LINE_DisplayName"] = ""

        df["Principal"] = pd.to_numeric(df["Principal"], errors="coerce").fillna(0.0)
        df["Rank"] = df["Rank"].apply(self._normalize_rank)

        if str(project).strip().upper() == "PERSONAL":
            df["DailyAPR"] = (
                df["Principal"]
                * (float(apr_percent) / 100.0)
                * df["Rank"].apply(self._rank_factor)
                / 365.0
            )
        else:
            total_principal = float(df["Principal"].sum())
            member_count = int(len(df))
            if total_principal <= 0 or member_count <= 0:
                df["DailyAPR"] = 0.0
            else:
                total_group_reward = total_principal * (float(apr_percent) / 100.0) * float(AppConfig.FACTOR["MASTER"]) / 365.0
                df["DailyAPR"] = float(total_group_reward / member_count)

        return df.reset_index(drop=True)

    def _calc_preview(self, members_df: pd.DataFrame, project: str, apr_percent: float) -> pd.DataFrame:
        df = self._build_calc_df(members_df, project, apr_percent)
        if df.empty:
            return pd.DataFrame()

        out = df[["Project_Name", "PersonName", "Principal", "Rank", "DailyAPR", "Line_User_ID", "LINE_DisplayName"]].copy()
        out["Principal"] = out["Principal"].map(lambda x: f"{float(x):,.2f}")
        out["DailyAPR"] = out["DailyAPR"].map(lambda x: f"{float(x):,.6f}")
        return out.reset_index(drop=True)

    def render(self) -> None:
        st.subheader("APR設定")

        settings_df = self.repo.load_settings()
        members_df = self.repo.load_members()

        projects = self.repo.active_projects(settings_df)
        if not projects:
            st.warning("有効なプロジェクトがありません。")
            return

        project = st.selectbox("対象プロジェクト", projects, key="apr_project")

        c1, c2, c3 = st.columns(3)
        with c1:
            apr_raw = st.text_input("APR（%）", value=st.session_state.get("apr_value", st.session_state.get("sv_apr", "")), key="apr_value")
        with c2:
            memo = st.text_input("メモ", value="", key="apr_note")
        with c3:
            send_line = st.checkbox("LINE送信も行う", value=False, key="apr_send_line")

        apr_percent = self._to_float(apr_raw)
        st.info(f"現在のAPR: {apr_percent:.4f}%")

        default_watch_folder = self._get_default_watch_folder()
        folder_path = st.text_input("監視フォルダパス", value=default_watch_folder, key="apr_watch_folder")

        image_files = self._folder_image_files(folder_path) if folder_path else []
        selected_folder_file: Optional[Path] = None

        if image_files:
            labels = [p.name for p in image_files]
            selected_label = st.selectbox("フォルダ内画像", labels, index=0, key="apr_folder_file_select")
            selected_folder_file = image_files[labels.index(selected_label)]

        uploaded = st.file_uploader("手動アップロード", type=["png", "jpg", "jpeg"], key="apr_img")

        c_ocr1, c_ocr2 = st.columns(2)
        with c_ocr1:
            if st.button("選択画像でOCR", use_container_width=True, key="apr_ocr_selected"):
                if selected_folder_file is not None:
                    file_bytes = selected_folder_file.read_bytes()
                    st.session_state["apr_folder_selected_name"] = selected_folder_file.name
                    st.session_state["apr_folder_selected_bytes"] = file_bytes
                    self._apply_ocr_result(file_bytes, settings_df, project)
                    st.rerun()

        with c_ocr2:
            if st.button("アップロード画像をOCR", use_container_width=True, key="apr_ocr_upload"):
                if uploaded is not None:
                    file_bytes = uploaded.getvalue()
                    st.session_state["apr_folder_selected_name"] = uploaded.name
                    st.session_state["apr_folder_selected_bytes"] = file_bytes
                    self._apply_ocr_result(file_bytes, settings_df, project)
                    st.rerun()

        selected_evidence_name = st.session_state.get("apr_folder_selected_name", "")
        selected_evidence_bytes = st.session_state.get("apr_folder_selected_bytes")

        if selected_evidence_name:
            st.caption(f"現在のエビデンス画像: {selected_evidence_name}")

        if selected_evidence_bytes:
            preview_boxes = OCRProcessor.build_preview_boxes(settings_df, project, rows_to_show=3)
            st.image(OCRProcessor.draw_ocr_boxes(selected_evidence_bytes, preview_boxes), caption="3領域OCR赤枠", width=500)

        st.markdown("### 受け取ったUSDC OCR集計（重複防止）")
        c_tx1, c_tx2 = st.columns(2)
        with c_tx1:
            if st.button("現在の画像から3領域OCR集計", use_container_width=True, key="ocr_tx_current"):
                if selected_evidence_bytes:
                    self._process_transaction_ocr(selected_evidence_bytes, selected_evidence_name or "selected_image", project, settings_df, project)
                else:
                    st.warning("先に画像を選択してください。")

        with c_tx2:
            if st.button("最新画像から3領域OCR集計", use_container_width=True, key="ocr_tx_latest"):
                if image_files:
                    latest_file = image_files[0]
                    self._process_transaction_ocr(latest_file.read_bytes(), latest_file.name, project, settings_df, project)
                else:
                    st.warning("監視フォルダに画像がありません。")

        st.markdown("### 試算結果")
        preview_df = self._calc_preview(members_df, project, apr_percent)
        if preview_df.empty:
            st.info("対象メンバーがいません。")
        else:
            st.dataframe(self._safe_df(preview_df), use_container_width=True, hide_index=True)

        today_ymd = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d")
        existing_keys = self.repo.existing_apr_keys_for_date(today_ymd)
        raw_df = self._build_calc_df(members_df, project, apr_percent)

        if not raw_df.empty:
            target_count = 0
            skipped_count = 0
            for _, row in raw_df.iterrows():
                key = (str(project).strip(), str(row.get("PersonName", "")).strip())
                if key in existing_keys:
                    skipped_count += 1
                else:
                    target_count += 1
            st.caption(f"本日未記録: {target_count}名 / 本日記録済み: {skipped_count}名")

        c_save1, c_save2 = st.columns(2)
        with c_save1:
            save_clicked = st.button("APRを記録", use_container_width=True, key="save_apr")
        with c_save2:
            reset_clicked = st.button("本日のAPR記録をリセット", use_container_width=True, key="reset_apr")

        if reset_clicked:
            deleted = self.repo.reset_today_apr_records(today_ymd, project)
            try:
                self.repo.gs.clear_cache()
            except Exception:
                pass
            if deleted > 0:
                st.success(f"本日分APRを {deleted} 件削除しました。")
            else:
                st.info("削除対象はありません。")
            st.rerun()

        if save_clicked:
            if raw_df.empty:
                st.warning("記録対象がありません。")
                return

            ts = pd.Timestamp.now(tz="Asia/Tokyo").strftime("%Y-%m-%d %H:%M:%S")
            token = ExternalService.get_line_token("A")
            saved_count = 0
            skipped_count = 0
            line_ok = 0
            line_ng = 0

            for _, row in raw_df.iterrows():
                person = str(row.get("PersonName", "")).strip()
                ledger_key = (str(project).strip(), person)

                if ledger_key in existing_keys:
                    skipped_count += 1
                    continue

                amount = float(row.get("DailyAPR", 0.0))
                uid = str(row.get("Line_User_ID", "")).strip()
                line_name = str(row.get("LINE_DisplayName", "")).strip()

                self.repo.append_ledger(
                    ts=ts,
                    project=str(project).strip(),
                    person=person,
                    type_name="APR",
                    amount=amount,
                    memo=str(memo).strip(),
                    evidence=selected_evidence_name,
                    line_uid=uid,
                    line_name=line_name,
                    source="APP",
                )
                saved_count += 1

                if send_line and uid:
                    msg = (
                        f"{person} 様\n"
                        f"本日のAPR配当を記録しました。\n"
                        f"Project: {project}\n"
                        f"APR: {apr_percent:.4f}%\n"
                        f"DailyAPR: ${amount:,.6f}"
                    )
                    code = ExternalService.send_line_push(token, uid, msg)
                    if code == 200:
                        line_ok += 1
                    else:
                        line_ng += 1

            try:
                self.repo.gs.clear_cache()
            except Exception:
                pass

            if send_line:
                st.success(f"APR記録: {saved_count}件 / スキップ: {skipped_count}件 / LINE成功: {line_ok} / LINE失敗: {line_ng}")
            else:
                st.success(f"APR記録: {saved_count}件 / スキップ: {skipped_count}件")
            st.rerun()
