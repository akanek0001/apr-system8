from __future__ import annotations

from typing import Any, List, Optional, Set, Tuple

import pandas as pd
import streamlit as st

from config import AppConfig
from core.utils import U
from services.gsheet_service import GSheetService


class Repository:
    def __init__(self, gs: GSheetService):
        self.gs = gs

    def _ensure_setting_defaults(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for k, v in AppConfig.OCR_DEFAULTS_PC.items():
            if k not in out.columns:
                out[k] = v
            else:
                out[k] = out[k].replace("", v)
        for k, v in AppConfig.OCR_DEFAULTS_MOBILE.items():
            if k not in out.columns:
                out[k] = v
            else:
                out[k] = out[k].replace("", v)
        return out

    def load_settings(self) -> pd.DataFrame:
        try:
            df = self.gs.load_df("SETTINGS")
        except Exception as e:
            st.error(str(e))
            return pd.DataFrame(columns=AppConfig.HEADERS["SETTINGS"])

        if df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["SETTINGS"])

        for c in AppConfig.HEADERS["SETTINGS"]:
            if c not in df.columns:
                df[c] = ""

        df = df[AppConfig.HEADERS["SETTINGS"]].copy()
        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df = df[df["Project_Name"] != ""].copy()
        df["Net_Factor"] = U.to_num_series(df["Net_Factor"], AppConfig.FACTOR["MASTER"])
        df.loc[df["Net_Factor"] <= 0, "Net_Factor"] = AppConfig.FACTOR["MASTER"]
        df["IsCompound"] = U.truthy_series(df["IsCompound"])
        df["Compound_Timing"] = df["Compound_Timing"].apply(U.normalize_compound)
        df["Active"] = df["Active"].apply(lambda x: U.truthy(x) if str(x).strip() else True)
        df["UpdatedAt_JST"] = df["UpdatedAt_JST"].astype(str).str.strip()

        for k, v in AppConfig.OCR_DEFAULTS_PC.items():
            df[k] = df[k].apply(lambda x, default=v: U.to_ratio(x, default))
        for k, v in AppConfig.OCR_DEFAULTS_MOBILE.items():
            df[k] = df[k].apply(lambda x, default=v: U.to_ratio(x, default))

        personal_df = df[df["Project_Name"].str.upper() == AppConfig.PROJECT["PERSONAL"]].tail(1).copy()
        other_df = df[df["Project_Name"].str.upper() != AppConfig.PROJECT["PERSONAL"]].drop_duplicates(subset=["Project_Name"], keep="last")
        out = pd.concat([personal_df, other_df], ignore_index=True)

        if AppConfig.PROJECT["PERSONAL"] not in out["Project_Name"].astype(str).tolist():
            out = pd.concat(
                [
                    pd.DataFrame([
                        {
                            "Project_Name": AppConfig.PROJECT["PERSONAL"],
                            "Net_Factor": AppConfig.FACTOR["MASTER"],
                            "IsCompound": True,
                            "Compound_Timing": AppConfig.COMPOUND["DAILY"],
                            "Crop_Left_Ratio_PC": AppConfig.OCR_DEFAULTS_PC["Crop_Left_Ratio_PC"],
                            "Crop_Top_Ratio_PC": AppConfig.OCR_DEFAULTS_PC["Crop_Top_Ratio_PC"],
                            "Crop_Right_Ratio_PC": AppConfig.OCR_DEFAULTS_PC["Crop_Right_Ratio_PC"],
                            "Crop_Bottom_Ratio_PC": AppConfig.OCR_DEFAULTS_PC["Crop_Bottom_Ratio_PC"],
                            "Crop_Left_Ratio_Mobile": AppConfig.OCR_DEFAULTS_MOBILE["Crop_Left_Ratio_Mobile"],
                            "Crop_Top_Ratio_Mobile": AppConfig.OCR_DEFAULTS_MOBILE["Crop_Top_Ratio_Mobile"],
                            "Crop_Right_Ratio_Mobile": AppConfig.OCR_DEFAULTS_MOBILE["Crop_Right_Ratio_Mobile"],
                            "Crop_Bottom_Ratio_Mobile": AppConfig.OCR_DEFAULTS_MOBILE["Crop_Bottom_Ratio_Mobile"],
                            "UpdatedAt_JST": U.fmt_dt(U.now_jst()),
                            "Active": True,
                        }
                    ]),
                    out,
                ],
                ignore_index=True,
            )
        return self._ensure_setting_defaults(out)

    def write_settings(self, df: pd.DataFrame) -> None:
        out = df.copy()
        for c in AppConfig.HEADERS["SETTINGS"]:
            if c not in out.columns:
                out[c] = ""
        out = out[AppConfig.HEADERS["SETTINGS"]].copy()
        out["Project_Name"] = out["Project_Name"].astype(str).str.strip()
        out = out[out["Project_Name"] != ""].copy()
        out["Net_Factor"] = U.to_num_series(out["Net_Factor"], AppConfig.FACTOR["MASTER"]).map(lambda x: f"{float(x):.2f}")
        out["IsCompound"] = out["IsCompound"].apply(lambda x: "TRUE" if U.truthy(x) else "FALSE")
        out["Compound_Timing"] = out["Compound_Timing"].apply(U.normalize_compound)
        for k, v in AppConfig.OCR_DEFAULTS_PC.items():
            out[k] = out[k].apply(lambda x, default=v: f"{U.to_ratio(x, default):.3f}")
        for k, v in AppConfig.OCR_DEFAULTS_MOBILE.items():
            out[k] = out[k].apply(lambda x, default=v: f"{U.to_ratio(x, default):.3f}")
        out["Active"] = out["Active"].apply(lambda x: "TRUE" if U.truthy(x) else "FALSE")
        out["UpdatedAt_JST"] = out["UpdatedAt_JST"].astype(str)
        self.gs.write_df("SETTINGS", out)

    def repair_settings(self, settings_df: pd.DataFrame) -> pd.DataFrame:
        repaired = settings_df.copy()
        before_count = len(repaired)
        if repaired.empty:
            repaired = pd.DataFrame(columns=AppConfig.HEADERS["SETTINGS"])
        for c in AppConfig.HEADERS["SETTINGS"]:
            if c not in repaired.columns:
                repaired[c] = ""
        repaired = self._ensure_setting_defaults(repaired)
        repaired["Project_Name"] = repaired["Project_Name"].astype(str).str.strip()
        repaired = repaired[repaired["Project_Name"] != ""].copy()
        personal_df = repaired[repaired["Project_Name"].str.upper() == AppConfig.PROJECT["PERSONAL"]].tail(1).copy()
        other_df = repaired[repaired["Project_Name"].str.upper() != AppConfig.PROJECT["PERSONAL"]].drop_duplicates(subset=["Project_Name"], keep="last")
        repaired = pd.concat([personal_df, other_df], ignore_index=True)
        repaired["Net_Factor"] = U.to_num_series(repaired["Net_Factor"], AppConfig.FACTOR["MASTER"])
        repaired.loc[repaired["Net_Factor"] <= 0, "Net_Factor"] = AppConfig.FACTOR["MASTER"]
        repaired["IsCompound"] = repaired["IsCompound"].apply(U.truthy)
        repaired["Compound_Timing"] = repaired["Compound_Timing"].apply(U.normalize_compound)
        repaired["Active"] = repaired["Active"].apply(lambda x: U.truthy(x) if str(x).strip() else True)
        repaired["UpdatedAt_JST"] = repaired["UpdatedAt_JST"].astype(str) if "UpdatedAt_JST" in repaired.columns else ""
        for k, v in AppConfig.OCR_DEFAULTS_PC.items():
            repaired[k] = repaired[k].apply(lambda x, default=v: U.to_ratio(x, default))
        for k, v in AppConfig.OCR_DEFAULTS_MOBILE.items():
            repaired[k] = repaired[k].apply(lambda x, default=v: U.to_ratio(x, default))
        if AppConfig.PROJECT["PERSONAL"] not in repaired["Project_Name"].astype(str).tolist():
            repaired = pd.concat(
                [
                    pd.DataFrame([
                        {
                            "Project_Name": AppConfig.PROJECT["PERSONAL"],
                            "Net_Factor": AppConfig.FACTOR["MASTER"],
                            "IsCompound": True,
                            "Compound_Timing": AppConfig.COMPOUND["DAILY"],
                            "Crop_Left_Ratio_PC": AppConfig.OCR_DEFAULTS_PC["Crop_Left_Ratio_PC"],
                            "Crop_Top_Ratio_PC": AppConfig.OCR_DEFAULTS_PC["Crop_Top_Ratio_PC"],
                            "Crop_Right_Ratio_PC": AppConfig.OCR_DEFAULTS_PC["Crop_Right_Ratio_PC"],
                            "Crop_Bottom_Ratio_PC": AppConfig.OCR_DEFAULTS_PC["Crop_Bottom_Ratio_PC"],
                            "Crop_Left_Ratio_Mobile": AppConfig.OCR_DEFAULTS_MOBILE["Crop_Left_Ratio_Mobile"],
                            "Crop_Top_Ratio_Mobile": AppConfig.OCR_DEFAULTS_MOBILE["Crop_Top_Ratio_Mobile"],
                            "Crop_Right_Ratio_Mobile": AppConfig.OCR_DEFAULTS_MOBILE["Crop_Right_Ratio_Mobile"],
                            "Crop_Bottom_Ratio_Mobile": AppConfig.OCR_DEFAULTS_MOBILE["Crop_Bottom_Ratio_Mobile"],
                            "UpdatedAt_JST": U.fmt_dt(U.now_jst()),
                            "Active": True,
                        }
                    ]),
                    repaired,
                ],
                ignore_index=True,
            )
        need_write = len(repaired) != before_count or settings_df.empty
        try:
            left = repaired[AppConfig.HEADERS["SETTINGS"]].astype(str).reset_index(drop=True)
            right = settings_df.reindex(columns=AppConfig.HEADERS["SETTINGS"]).astype(str).reset_index(drop=True)
            if not left.equals(right):
                need_write = True
        except Exception:
            need_write = True
        if need_write:
            self.write_settings(repaired)
            self.gs.clear_cache()
            repaired = self.load_settings()
        return repaired

    def load_members(self) -> pd.DataFrame:
        try:
            df = self.gs.load_df("MEMBERS")
        except Exception as e:
            st.error(str(e))
            return pd.DataFrame(columns=AppConfig.HEADERS["MEMBERS"])
        if df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["MEMBERS"])
        for c in AppConfig.HEADERS["MEMBERS"]:
            if c not in df.columns:
                df[c] = ""
        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df["PersonName"] = df["PersonName"].astype(str).str.strip()
        df["Principal"] = U.to_num_series(df["Principal"])
        df["Line_User_ID"] = df["Line_User_ID"].astype(str).str.strip()
        df["LINE_DisplayName"] = df["LINE_DisplayName"].astype(str).str.strip()
        df["Rank"] = df["Rank"].apply(U.normalize_rank)
        df["IsActive"] = df["IsActive"].apply(U.truthy)
        return df

    def write_members(self, members_df: pd.DataFrame) -> None:
        out = members_df.copy()
        out["Principal"] = U.to_num_series(out["Principal"]).map(lambda x: f"{float(x):.6f}")
        out["IsActive"] = out["IsActive"].apply(lambda x: "TRUE" if U.truthy(x) else "FALSE")
        out["Rank"] = out["Rank"].apply(U.normalize_rank)
        self.gs.write_df("MEMBERS", out)

    def load_ledger(self) -> pd.DataFrame:
        try:
            df = self.gs.load_df("LEDGER")
        except Exception as e:
            st.error(str(e))
            return pd.DataFrame(columns=AppConfig.HEADERS["LEDGER"])
        if df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["LEDGER"])
        for c in AppConfig.HEADERS["LEDGER"]:
            if c not in df.columns:
                df[c] = ""
        df["Amount"] = U.to_num_series(df["Amount"])
        return df

    def load_line_users(self) -> pd.DataFrame:
        try:
            df = self.gs.load_df("LINEUSERS")
        except Exception as e:
            st.error(str(e))
            return pd.DataFrame(columns=AppConfig.HEADERS["LINEUSERS"])
        if df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["LINEUSERS"])
        if "Line_User_ID" not in df.columns and "LineID" in df.columns:
            df = df.rename(columns={"LineID": "Line_User_ID"})
        if "Line_User" not in df.columns and "LINE_DisplayName" in df.columns:
            df = df.rename(columns={"LINE_DisplayName": "Line_User"})
        if "Line_User_ID" not in df.columns:
            df["Line_User_ID"] = ""
        if "Line_User" not in df.columns:
            df["Line_User"] = ""
        df["Line_User_ID"] = df["Line_User_ID"].astype(str).str.strip()
        df["Line_User"] = df["Line_User"].astype(str).str.strip()
        return df

    def write_apr_summary(self, summary_df: pd.DataFrame) -> None:
        if summary_df.empty:
            return
        out = summary_df.copy()
        out["Date_JST"] = out["Date_JST"].astype(str)
        out["PersonName"] = out["PersonName"].astype(str)
        out["Total_APR"] = U.to_num_series(out["Total_APR"]).map(lambda x: f"{float(x):.6f}")
        out["APR_Count"] = U.to_num_series(out["APR_Count"]).astype(int).astype(str)
        out["Asset_Ratio"] = out["Asset_Ratio"].astype(str)
        out["LINE_DisplayName"] = out["LINE_DisplayName"].astype(str)
        self.gs.write_df("APR_SUMMARY", out)

    def append_ledger(self, dt_jst: str, project: str, person_name: str, typ: str, amount: float, note: str,
                      evidence_url: str = "", line_user_id: str = "", line_display_name: str = "",
                      source: str = AppConfig.SOURCE["APP"]) -> None:
        if not str(project).strip():
            raise ValueError("project が空です")
        if not str(person_name).strip():
            raise ValueError("person_name が空です")
        if not str(typ).strip():
            raise ValueError("typ が空です")
        self.gs.append_row(
            "LEDGER",
            [dt_jst, project, person_name, typ, float(amount), note, evidence_url or "", line_user_id or "", line_display_name or "", source],
        )

    def append_smartvault_history(self, dt_jst: str, project: str, liquidity: float, yesterday_profit: float, apr: float,
                                  source_mode: str, ocr_liquidity: Optional[float], ocr_yesterday_profit: Optional[float],
                                  ocr_apr: Optional[float], evidence_url: str, admin_name: str, admin_namespace: str,
                                  note: str = "") -> None:
        self.gs.append_row(
            "SMARTVAULT_HISTORY",
            [
                dt_jst, project, float(liquidity), float(yesterday_profit), float(apr), str(source_mode),
                "" if ocr_liquidity is None else float(ocr_liquidity),
                "" if ocr_yesterday_profit is None else float(ocr_yesterday_profit),
                "" if ocr_apr is None else float(ocr_apr), evidence_url or "", admin_name or "", admin_namespace or "", note or "",
            ],
        )

    def active_projects(self, settings_df: pd.DataFrame) -> List[str]:
        if settings_df.empty:
            return []
        return settings_df.loc[settings_df["Active"] == True, "Project_Name"].dropna().astype(str).unique().tolist()

    def project_members_active(self, members_df: pd.DataFrame, project: str) -> pd.DataFrame:
        if members_df.empty:
            return members_df.copy()
        return members_df[(members_df["Project_Name"] == str(project)) & (members_df["IsActive"] == True)].copy().reset_index(drop=True)

    def validate_no_dup_lineid(self, members_df: pd.DataFrame, project: str) -> Optional[str]:
        if members_df.empty:
            return None
        df = members_df[members_df["Project_Name"] == str(project)].copy()
        df["Line_User_ID"] = df["Line_User_ID"].astype(str).str.strip()
        df = df[df["Line_User_ID"] != ""]
        dup = df[df.duplicated(subset=["Line_User_ID"], keep=False)]
        return None if dup.empty else f"同一プロジェクト内で Line_User_ID が重複しています: {dup['Line_User_ID'].unique().tolist()}"

    def existing_apr_keys_for_date(self, date_jst: str) -> Set[Tuple[str, str]]:
        ledger_df = self.load_ledger()
        if ledger_df.empty:
            return set()
        df = ledger_df[(ledger_df["Type"].astype(str).str.strip() == AppConfig.TYPE["APR"]) & (ledger_df["Datetime_JST"].astype(str).str.startswith(date_jst))].copy()
        if df.empty:
            return set()
        return set(zip(df["Project_Name"].astype(str).str.strip(), df["PersonName"].astype(str).str.strip()))

    def reset_today_apr_records(self, date_jst: str, project: str) -> Tuple[int, int]:
        ws = self.gs.ws("LEDGER")
        values = ws.get_all_values()
        if not values:
            return 0, 0
        headers = values[0]
        if len(values) == 1:
            return 0, 0
        need_cols = ["Datetime_JST", "Project_Name", "Type", "Note"]
        if any(c not in headers for c in need_cols):
            return 0, 0
        idx_dt, idx_project, idx_type, idx_note = headers.index("Datetime_JST"), headers.index("Project_Name"), headers.index("Type"), headers.index("Note")
        kept_rows, deleted_apr, deleted_line = [headers], 0, 0
        for row in values[1:]:
            row = row + [""] * (len(headers) - len(row))
            dt_v, project_v, type_v, note_v = str(row[idx_dt]).strip(), str(row[idx_project]).strip(), str(row[idx_type]).strip(), str(row[idx_note]).strip()
            is_today = dt_v.startswith(date_jst)
            is_project = project_v == str(project).strip()
            delete_apr = is_today and is_project and type_v == AppConfig.TYPE["APR"]
            delete_line = is_today and is_project and type_v == AppConfig.TYPE["LINE"] and AppConfig.APR_LINE_NOTE_KEYWORD in note_v
            if delete_apr:
                deleted_apr += 1
                continue
            if delete_line:
                deleted_line += 1
                continue
            kept_rows.append(row[: len(headers)])
        if deleted_apr > 0 or deleted_line > 0:
            self.gs.overwrite_rows("LEDGER", kept_rows)
            self.gs.clear_cache()
        return deleted_apr, deleted_line
