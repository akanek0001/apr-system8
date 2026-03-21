from __future__ import annotations

import pandas as pd

from config import AppConfig
from services.gsheet_service import GSheetService


class Repository:
    def __init__(self, gs: GSheetService):
        self.gs = gs
        self._ensure_all_sheets()

    def _ensure_all_sheets(self) -> None:
        for key, sheet_name in AppConfig.SHEET.items():
            self.gs.ensure_sheet(sheet_name, AppConfig.HEADERS[key])

    def _ensure_columns(self, df: pd.DataFrame, headers: list[str]) -> pd.DataFrame:
        out = df.copy()
        for col in headers:
            if col not in out.columns:
                out[col] = ""
        return out[headers].copy()

    def load_settings(self) -> pd.DataFrame:
        df = self.gs.load_df(AppConfig.SHEET["SETTINGS"])
        if df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["SETTINGS"])
        return self._ensure_columns(df, AppConfig.HEADERS["SETTINGS"])

    def write_settings(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, AppConfig.HEADERS["SETTINGS"])
        self.gs.write_df(AppConfig.SHEET["SETTINGS"], out)

    def load_members(self) -> pd.DataFrame:
        df = self.gs.load_df(AppConfig.SHEET["MEMBERS"])
        if df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["MEMBERS"])
        return self._ensure_columns(df, AppConfig.HEADERS["MEMBERS"])

    def write_members(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, AppConfig.HEADERS["MEMBERS"])
        self.gs.write_df(AppConfig.SHEET["MEMBERS"], out)

    def load_ledger(self) -> pd.DataFrame:
        df = self.gs.load_df(AppConfig.SHEET["LEDGER"])
        if df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["LEDGER"])
        return self._ensure_columns(df, AppConfig.HEADERS["LEDGER"])

    def write_ledger(self, df: pd.DataFrame) -> None:
        out = self._ensure_columns(df, AppConfig.HEADERS["LEDGER"])
        self.gs.write_df(AppConfig.SHEET["LEDGER"], out)

    def append_ledger(
        self,
        ts: str,
        project: str,
        person: str,
        type_name: str,
        amount: float,
        memo: str,
        evidence: str,
        line_uid: str,
        line_name: str,
        source: str = "APP",
    ) -> None:
        row = [
            ts,
            project,
            person,
            type_name,
            amount,
            memo,
            evidence,
            line_uid,
            line_name,
            source,
        ]
        self.gs.append_row(AppConfig.SHEET["LEDGER"], row)

    def load_line_users(self) -> pd.DataFrame:
        df = self.gs.load_df(AppConfig.SHEET["LINEUSERS"])
        if df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["LINEUSERS"])
        return self._ensure_columns(df, AppConfig.HEADERS["LINEUSERS"])

    def active_projects(self, settings_df: pd.DataFrame) -> list[str]:
        if settings_df is None or settings_df.empty:
            return []

        df = settings_df.copy()
        if "Active" in df.columns:
            active_mask = df["Active"].astype(str).str.lower().isin(["true", "1", "yes", "on"])
            df = df[active_mask]

        if "Project_Name" not in df.columns:
            return []

        return (
            df["Project_Name"]
            .astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .tolist()
        )

    def existing_apr_keys_for_date(self, date_ymd: str) -> set[tuple[str, str]]:
        ledger_df = self.load_ledger()
        if ledger_df.empty:
            return set()

        df = ledger_df.copy()
        if "Datetime_JST" not in df.columns or "Type" not in df.columns:
            return set()

        df = df[df["Type"].astype(str).str.strip() == "APR"].copy()
        if df.empty:
            return set()

        df["DateOnly"] = df["Datetime_JST"].astype(str).str.slice(0, 10)
        df = df[df["DateOnly"] == str(date_ymd).strip()].copy()

        keys = set()
        for _, row in df.iterrows():
            keys.add(
                (
                    str(row.get("Project_Name", "")).strip(),
                    str(row.get("PersonName", "")).strip(),
                )
            )
        return keys

    def reset_today_apr_records(self, date_ymd: str, project: str) -> int:
        ledger_df = self.load_ledger()
        if ledger_df.empty:
            return 0

        before = len(ledger_df)

        mask = ~(
            (ledger_df["Type"].astype(str).str.strip() == "APR")
            & (ledger_df["Datetime_JST"].astype(str).str.slice(0, 10) == str(date_ymd).strip())
            & (ledger_df["Project_Name"].astype(str).str.strip() == str(project).strip())
        )
        new_df = ledger_df[mask].copy()
        deleted = before - len(new_df)

        if deleted > 0:
            self.write_ledger(new_df)

        return deleted
