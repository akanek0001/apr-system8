from __future__ import annotations

from typing import Optional, Set, Tuple

import pandas as pd

from config import AppConfig
from core.utils import U
from services.gsheet_service import GSheetService


class Repository:
    def __init__(self, gs: GSheetService):
        self.gs = gs

    # =========================
    # 共通
    # =========================
    def _empty_df(self, key: str) -> pd.DataFrame:
        return pd.DataFrame(columns=AppConfig.HEADERS[key])

    def _ensure_columns(self, df: pd.DataFrame, key: str) -> pd.DataFrame:
        out = df.copy()
        out = out.loc[:, ~out.columns.duplicated()]

        for col in AppConfig.HEADERS[key]:
            if col not in out.columns:
                out[col] = ""

        return out[AppConfig.HEADERS[key]].copy()

    # =========================
    # 初期シート作成
    # =========================
    def ensure_all_sheets(self) -> None:
        for key, headers in AppConfig.HEADERS.items():
            self.gs.ensure_sheet(key, headers)

    # =========================
    # Settings
    # =========================
    def _bootstrap_settings_if_empty(self) -> None:
        df = self.gs.load_df("SETTINGS")
        df = df.loc[:, ~df.columns.duplicated()]

        if not df.empty:
            return

        row = {c: "" for c in AppConfig.HEADERS["SETTINGS"]}
        row["Project_Name"] = AppConfig.PROJECT["PERSONAL"]
        row["Net_Factor"] = AppConfig.FACTOR["MASTER"]
        row["IsCompound"] = "TRUE"
        row["Compound_Timing"] = AppConfig.COMPOUND["NONE"]
        row["UpdatedAt_JST"] = U.fmt_dt(U.now_jst())
        row["Active"] = "TRUE"

        for k, v in AppConfig.OCR_DEFAULTS_PC.items():
            row[k] = v
        for k, v in AppConfig.OCR_DEFAULTS_MOBILE.items():
            row[k] = v

        self.gs.write_df("SETTINGS", pd.DataFrame([row]))
        self.gs.clear_cache()

    def load_settings(self) -> pd.DataFrame:
        self._bootstrap_settings_if_empty()

        df = self.gs.load_df("SETTINGS")
        if df.empty:
            return self._empty_df("SETTINGS")

        df = self._ensure_columns(df, "SETTINGS")

        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df = df[df["Project_Name"] != ""].copy()

        df["Net_Factor"] = U.to_num_series(df["Net_Factor"], AppConfig.FACTOR["MASTER"])
        df["IsCompound"] = U.truthy_series(df["IsCompound"])
        df["Compound_Timing"] = df["Compound_Timing"].apply(U.normalize_compound)
        df["UpdatedAt_JST"] = df["UpdatedAt_JST"].astype(str).str.strip()
        df["Active"] = U.truthy_series(df["Active"])

        return df.reset_index(drop=True)

    def write_settings(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, "SETTINGS")

        out["Project_Name"] = out["Project_Name"].astype(str).str.strip()
        out = out[out["Project_Name"] != ""].copy()

        out["Net_Factor"] = U.to_num_series(out["Net_Factor"], AppConfig.FACTOR["MASTER"])
        out["IsCompound"] = out["IsCompound"].apply(lambda x: "TRUE" if U.truthy(x) else "FALSE")
        out["Compound_Timing"] = out["Compound_Timing"].apply(U.normalize_compound)
        out["UpdatedAt_JST"] = out["UpdatedAt_JST"].astype(str)
        out["Active"] = out["Active"].apply(lambda x: "TRUE" if U.truthy(x) else "FALSE")

        self.gs.write_df("SETTINGS", out)
        self.gs.clear_cache()

    # =========================
    # Members
    # =========================
    def load_members(self) -> pd.DataFrame:
        df = self.gs.load_df("MEMBERS")
        if df.empty:
            return self._empty_df("MEMBERS")

        df = self._ensure_columns(df, "MEMBERS")

        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df["PersonName"] = df["PersonName"].astype(str).str.strip()
        df["Principal"] = U.to_num_series(df["Principal"], 0.0)
        df["Line_User_ID"] = df["Line_User_ID"].astype(str).str.strip()
        df["LINE_DisplayName"] = df["LINE_DisplayName"].astype(str).str.strip()
        df["Rank"] = df["Rank"].apply(U.normalize_rank)
        df["IsActive"] = U.truthy_series(df["IsActive"])
        df["CreatedAt_JST"] = df["CreatedAt_JST"].astype(str).str.strip()
        df["UpdatedAt_JST"] = df["UpdatedAt_JST"].astype(str).str.strip()

        return df.reset_index(drop=True)

    def write_members(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, "MEMBERS")

        out["Project_Name"] = out["Project_Name"].astype(str).str.strip()
        out["PersonName"] = out["PersonName"].astype(str).str.strip()
        out["Principal"] = U.to_num_series(out["Principal"], 0.0)
        out["Line_User_ID"] = out["Line_User_ID"].astype(str).str.strip()
        out["LINE_DisplayName"] = out["LINE_DisplayName"].astype(str).str.strip()
        out["Rank"] = out["Rank"].apply(U.normalize_rank)
        out["IsActive"] = out["IsActive"].apply(lambda x: "TRUE" if U.truthy(x) else "FALSE")
        out["CreatedAt_JST"] = out["CreatedAt_JST"].astype(str)
        out["UpdatedAt_JST"] = out["UpdatedAt_JST"].astype(str)

        self.gs.write_df("MEMBERS", out)
        self.gs.clear_cache()

    # =========================
    # Ledger
    # =========================
    def load_ledger(self) -> pd.DataFrame:
        df = self.gs.load_df("LEDGER")
        if df.empty:
            return self._empty_df("LEDGER")

        df = self._ensure_columns(df, "LEDGER")

        df["Datetime_JST"] = df["Datetime_JST"].astype(str).str.strip()
        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df["PersonName"] = df["PersonName"].astype(str).str.strip()
        df["Type"] = df["Type"].astype(str).str.strip()
        df["Amount"] = U.to_num_series(df["Amount"], 0.0)
        df["Note"] = df["Note"].astype(str).str.strip()
        df["Evidence_URL"] = df["Evidence_URL"].astype(str).str.strip()
        df["Line_User_ID"] = df["Line_User_ID"].astype(str).str.strip()
        df["LINE_DisplayName"] = df["LINE_DisplayName"].astype(str).str.strip()
        df["Source"] = df["Source"].astype(str).str.strip()

        return df.reset_index(drop=True)

    def write_ledger(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, "LEDGER")

        out["Datetime_JST"] = out["Datetime_JST"].astype(str)
        out["Project_Name"] = out["Project_Name"].astype(str).str.strip()
        out["PersonName"] = out["PersonName"].astype(str).str.strip()
        out["Type"] = out["Type"].astype(str).str.strip()
        out["Amount"] = U.to_num_series(out["Amount"], 0.0)
        out["Note"] = out["Note"].astype(str)
        out["Evidence_URL"] = out["Evidence_URL"].astype(str)
        out["Line_User_ID"] = out["Line_User_ID"].astype(str)
        out["LINE_DisplayName"] = out["LINE_DisplayName"].astype(str)
        out["Source"] = out["Source"].astype(str)

        self.gs.write_df("LEDGER", out)
        self.gs.clear_cache()

    def append_ledger(
        self,
        dt_jst: str,
        project: str,
        person_name: str,
        typ: str,
        amount: float,
        note: str,
        evidence_url: str = "",
        line_user_id: str = "",
        line_display_name: str = "",
        source: str = AppConfig.SOURCE["APP"],
    ) -> None:
        self.gs.append_row(
            "LEDGER",
            [
                str(dt_jst).strip(),
                str(project).strip(),
                str(person_name).strip(),
                str(typ).strip(),
                float(amount),
                str(note).strip(),
                str(evidence_url).strip(),
                str(line_user_id).strip(),
                str(line_display_name).strip(),
                str(source).strip(),
            ],
        )
        self.gs.clear_cache()

    # =========================
    # LineUsers
    # =========================
    def load_line_users(self) -> pd.DataFrame:
        df = self.gs.load_df("LINEUSERS")
        if df.empty:
            return self._empty_df("LINEUSERS")

        df = self._ensure_columns(df, "LINEUSERS")

        df["Line_User_ID"] = df["Line_User_ID"].astype(str).str.strip()
        df["Line_User"] = df["Line_User"].astype(str).str.strip()

        return df.reset_index(drop=True)

    def write_line_users(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, "LINEUSERS")

        out["Line_User_ID"] = out["Line_User_ID"].astype(str).str.strip()
        out["Line_User"] = out["Line_User"].astype(str).str.strip()

        self.gs.write_df("LINEUSERS", out)
        self.gs.clear_cache()

    # =========================
    # APR Summary
    # =========================
    def load_apr_summary(self) -> pd.DataFrame:
        df = self.gs.load_df("APR_SUMMARY")
        if df.empty:
            return self._empty_df("APR_SUMMARY")

        df = self._ensure_columns(df, "APR_SUMMARY")

        df["Date_JST"] = df["Date_JST"].astype(str).str.strip()
        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df["PersonName"] = df["PersonName"].astype(str).str.strip()
        df["Total_APR"] = U.to_num_series(df["Total_APR"], 0.0)
        df["APR_Count"] = U.to_num_series(df["APR_Count"], 0.0).astype(int)
        df["Asset_Ratio"] = df["Asset_Ratio"].astype(str).str.strip()
        df["LINE_DisplayName"] = df["LINE_DisplayName"].astype(str).str.strip()

        return df.reset_index(drop=True)

    def write_apr_summary(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, "APR_SUMMARY")

        out["Date_JST"] = out["Date_JST"].astype(str)
        out["Project_Name"] = out["Project_Name"].astype(str).str.strip()
        out["PersonName"] = out["PersonName"].astype(str).str.strip()
        out["Total_APR"] = U.to_num_series(out["Total_APR"], 0.0)
        out["APR_Count"] = U.to_num_series(out["APR_Count"], 0.0).astype(int)
        out["Asset_Ratio"] = out["Asset_Ratio"].astype(str)
        out["LINE_DisplayName"] = out["LINE_DisplayName"].astype(str)

        self.gs.write_df("APR_SUMMARY", out)
        self.gs.clear_cache()

    # =========================
    # SmartVault History
    # =========================
    def load_smartvault_history(self) -> pd.DataFrame:
        df = self.gs.load_df("SMARTVAULT_HISTORY")
        if df.empty:
            return self._empty_df("SMARTVAULT_HISTORY")

        df = self._ensure_columns(df, "SMARTVAULT_HISTORY")

        df["Datetime_JST"] = df["Datetime_JST"].astype(str).str.strip()
        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df["Liquidity"] = U.to_num_series(df["Liquidity"], 0.0)
        df["Yesterday_Profit"] = U.to_num_series(df["Yesterday_Profit"], 0.0)
        df["APR"] = U.to_num_series(df["APR"], 0.0)
        df["Source_Mode"] = df["Source_Mode"].astype(str).str.strip()
        df["OCR_Liquidity"] = U.to_num_series(df["OCR_Liquidity"], 0.0)
        df["OCR_Yesterday_Profit"] = U.to_num_series(df["OCR_Yesterday_Profit"], 0.0)
        df["OCR_APR"] = U.to_num_series(df["OCR_APR"], 0.0)
        df["Evidence_URL"] = df["Evidence_URL"].astype(str).str.strip()
        df["Admin_Name"] = df["Admin_Name"].astype(str).str.strip()
        df["Admin_Namespace"] = df["Admin_Namespace"].astype(str).str.strip()
        df["Note"] = df["Note"].astype(str).str.strip()

        return df.reset_index(drop=True)

    def append_smartvault_history(
        self,
        dt_jst: str,
        project: str,
        liquidity: float,
        yesterday_profit: float,
        apr: float,
        source_mode: str,
        ocr_liquidity: Optional[float],
        ocr_yesterday_profit: Optional[float],
        ocr_apr: Optional[float],
        evidence_url: str,
        admin_name: str,
        admin_namespace: str,
        note: str = "",
    ) -> None:
        self.gs.append_row(
            "SMARTVAULT_HISTORY",
            [
                str(dt_jst).strip(),
                str(project).strip(),
                float(liquidity),
                float(yesterday_profit),
                float(apr),
                str(source_mode).strip(),
                "" if ocr_liquidity is None else float(ocr_liquidity),
                "" if ocr_yesterday_profit is None else float(ocr_yesterday_profit),
                "" if ocr_apr is None else float(ocr_apr),
                str(evidence_url).strip(),
                str(admin_name).strip(),
                str(admin_namespace).strip(),
                str(note).strip(),
            ],
        )
        self.gs.clear_cache()

    # =========================
    # OCR Transaction
    # =========================
    def load_ocr_transaction(self) -> pd.DataFrame:
        df = self.gs.load_df("OCR_TRANSACTION")
        if df.empty:
            return self._empty_df("OCR_TRANSACTION")

        df = self._ensure_columns(df, "OCR_TRANSACTION")

        df["Datetime_JST"] = df["Datetime_JST"].astype(str).str.strip()
        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df["Row_No"] = U.to_num_series(df["Row_No"], 0.0).astype(int)
        df["Date_Label"] = df["Date_Label"].astype(str).str.strip()
        df["Time_Label"] = df["Time_Label"].astype(str).str.strip()
        df["Type_Label"] = df["Type_Label"].astype(str).str.strip()
        df["Amount_USD"] = U.to_num_series(df["Amount_USD"], 0.0)
        df["Raw_Text"] = df["Raw_Text"].astype(str).str.strip()
        df["CreatedAt_JST"] = df["CreatedAt_JST"].astype(str).str.strip()

        return df.reset_index(drop=True)

    def write_ocr_transaction(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, "OCR_TRANSACTION")

        out["Datetime_JST"] = out["Datetime_JST"].astype(str)
        out["Project_Name"] = out["Project_Name"].astype(str).str.strip()
        out["Row_No"] = U.to_num_series(out["Row_No"], 0.0).astype(int)
        out["Date_Label"] = out["Date_Label"].astype(str)
        out["Time_Label"] = out["Time_Label"].astype(str)
        out["Type_Label"] = out["Type_Label"].astype(str)
        out["Amount_USD"] = U.to_num_series(out["Amount_USD"], 0.0)
        out["Raw_Text"] = out["Raw_Text"].astype(str)
        out["CreatedAt_JST"] = out["CreatedAt_JST"].astype(str)

        self.gs.write_df("OCR_TRANSACTION", out)
        self.gs.clear_cache()

    # =========================
    # OCR Transaction History
    # =========================
    def load_ocr_transaction_history(self) -> pd.DataFrame:
        df = self.gs.load_df("OCR_TRANSACTION_HISTORY")
        if df.empty:
            return self._empty_df("OCR_TRANSACTION_HISTORY")

        df = self._ensure_columns(df, "OCR_TRANSACTION_HISTORY")

        df["Unique_Key"] = df["Unique_Key"].astype(str).str.strip()
        df["Date_Label"] = df["Date_Label"].astype(str).str.strip()
        df["Time_Label"] = df["Time_Label"].astype(str).str.strip()
        df["Type_Label"] = df["Type_Label"].astype(str).str.strip()
        df["Amount_USD"] = U.to_num_series(df["Amount_USD"], 0.0)
        df["Token_Amount"] = df["Token_Amount"].astype(str).str.strip()
        df["Token_Symbol"] = df["Token_Symbol"].astype(str).str.strip()
        df["Source_Image"] = df["Source_Image"].astype(str).str.strip()
        df["Source_Project"] = df["Source_Project"].astype(str).str.strip()
        df["OCR_Raw_Text"] = df["OCR_Raw_Text"].astype(str).str.strip()
        df["CreatedAt_JST"] = df["CreatedAt_JST"].astype(str).str.strip()

        return df.reset_index(drop=True)

    def write_ocr_transaction_history(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, "OCR_TRANSACTION_HISTORY")

        out["Unique_Key"] = out["Unique_Key"].astype(str)
        out["Date_Label"] = out["Date_Label"].astype(str)
        out["Time_Label"] = out["Time_Label"].astype(str)
        out["Type_Label"] = out["Type_Label"].astype(str)
        out["Amount_USD"] = U.to_num_series(out["Amount_USD"], 0.0)
        out["Token_Amount"] = out["Token_Amount"].astype(str)
        out["Token_Symbol"] = out["Token_Symbol"].astype(str)
        out["Source_Image"] = out["Source_Image"].astype(str)
        out["Source_Project"] = out["Source_Project"].astype(str)
        out["OCR_Raw_Text"] = out["OCR_Raw_Text"].astype(str)
        out["CreatedAt_JST"] = out["CreatedAt_JST"].astype(str)

        self.gs.write_df("OCR_TRANSACTION_HISTORY", out)
        self.gs.clear_cache()

    # =========================
    # APR Auto Queue
    # =========================
    def load_apr_auto_queue(self) -> pd.DataFrame:
        df = self.gs.load_df("APR_AUTO_QUEUE")
        if df.empty:
            return self._empty_df("APR_AUTO_QUEUE")

        df = self._ensure_columns(df, "APR_AUTO_QUEUE")

        df["CreatedAt_JST"] = df["CreatedAt_JST"].astype(str).str.strip()
        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df["PersonName"] = df["PersonName"].astype(str).str.strip()
        df["Line_User_ID"] = df["Line_User_ID"].astype(str).str.strip()
        df["LINE_DisplayName"] = df["LINE_DisplayName"].astype(str).str.strip()
        df["APR"] = U.to_num_series(df["APR"], 0.0)
        df["DailyAPR"] = U.to_num_series(df["DailyAPR"], 0.0)
        df["Status"] = df["Status"].astype(str).str.strip()
        df["Note"] = df["Note"].astype(str).str.strip()

        return df.reset_index(drop=True)

    def write_apr_auto_queue(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, "APR_AUTO_QUEUE")

        out["CreatedAt_JST"] = out["CreatedAt_JST"].astype(str)
        out["Project_Name"] = out["Project_Name"].astype(str)
        out["PersonName"] = out["PersonName"].astype(str)
        out["Line_User_ID"] = out["Line_User_ID"].astype(str)
        out["LINE_DisplayName"] = out["LINE_DisplayName"].astype(str)
        out["APR"] = U.to_num_series(out["APR"], 0.0)
        out["DailyAPR"] = U.to_num_series(out["DailyAPR"], 0.0)
        out["Status"] = out["Status"].astype(str)
        out["Note"] = out["Note"].astype(str)

        self.gs.write_df("APR_AUTO_QUEUE", out)
        self.gs.clear_cache()

    # =========================
    # 補助
    # =========================
    def active_projects(self, settings_df: pd.DataFrame) -> list[str]:
        if settings_df.empty:
            return []

        df = settings_df.copy()
        df = df[df["Active"] == True].copy()

        return (
            df["Project_Name"]
            .dropna()
            .astype(str)
            .str.strip()
            .tolist()
        )

    def project_members_active(self, members_df: pd.DataFrame, project: str) -> pd.DataFrame:
        if members_df.empty:
            return self._empty_df("MEMBERS")

        df = members_df.copy()
        df = df[df["Project_Name"].astype(str).str.strip() == str(project).strip()].copy()
        df = df[df["IsActive"] == True].copy()

        return df.reset_index(drop=True)

    def validate_no_dup_lineid(self, members_df: pd.DataFrame, project: str) -> Optional[str]:
        if members_df.empty:
            return None

        df = members_df.copy()
        df = df[df["Project_Name"].astype(str).str.strip() == str(project).strip()].copy()
        df["Line_User_ID"] = df["Line_User_ID"].astype(str).str.strip()
        df = df[df["Line_User_ID"] != ""].copy()

        dup = df[df.duplicated(subset=["Line_User_ID"], keep=False)]
        if dup.empty:
            return None

        ids = sorted(dup["Line_User_ID"].astype(str).unique().tolist())
        return f"同一プロジェクト内で Line_User_ID が重複しています: {', '.join(ids)}"

    def existing_apr_keys_for_date(self, date_jst: str) -> Set[Tuple[str, str]]:
        ledger_df = self.load_ledger()
        if ledger_df.empty:
            return set()

        df = ledger_df.copy()
        df = df[df["Type"].astype(str).str.strip() == AppConfig.TYPE["APR"]].copy()
        df = df[df["Datetime_JST"].astype(str).str.startswith(str(date_jst).strip())].copy()

        if df.empty:
            return set()

        return set(
            zip(
                df["Project_Name"].astype(str).str.strip(),
                df["PersonName"].astype(str).str.strip(),
            )
        )

    def reset_today_apr_records(self, date_jst: str, project: str) -> tuple[int, int]:
        ledger_df = self.load_ledger()
        if ledger_df.empty:
            return 0, 0

        df = ledger_df.copy()

        apr_mask = (
            df["Datetime_JST"].astype(str).str.startswith(str(date_jst).strip())
            & (df["Project_Name"].astype(str).str.strip() == str(project).strip())
            & (df["Type"].astype(str).str.strip() == AppConfig.TYPE["APR"])
        )

        line_mask = (
            df["Datetime_JST"].astype(str).str.startswith(str(date_jst).strip())
            & (df["Project_Name"].astype(str).str.strip() == str(project).strip())
            & (df["Type"].astype(str).str.strip() == AppConfig.TYPE["LINE"])
        )

        deleted_apr = int(apr_mask.sum())
        deleted_line = int(line_mask.sum())

        kept = df[~(apr_mask | line_mask)].copy()
        self.write_ledger(kept)

        return deleted_apr, deleted_line
