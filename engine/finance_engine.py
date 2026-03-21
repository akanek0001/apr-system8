from __future__ import annotations

from typing import Tuple

import pandas as pd

from config import AppConfig
from core.utils import U
from repository.repository import Repository


class FinanceEngine:
    def calc_project_apr(self, mem: pd.DataFrame, apr_percent: float, project_net_factor: float, project_name: str) -> pd.DataFrame:
        out = mem.copy()
        if str(project_name).strip().upper() == AppConfig.PROJECT["PERSONAL"]:
            out["Factor"] = out["Rank"].map(U.rank_factor)
            out["DailyAPR"] = (out["Principal"] * (apr_percent / 100.0) * out["Factor"]) / 365.0
            out["CalcMode"] = "PERSONAL"
            return out
        total_principal = float(out["Principal"].sum())
        count = len(out)
        factor = float(project_net_factor if project_net_factor > 0 else AppConfig.FACTOR["MASTER"])
        total_group_reward = (total_principal * (apr_percent / 100.0) * factor) / 365.0
        out["Factor"] = factor
        out["DailyAPR"] = (total_group_reward / count) if count > 0 else 0.0
        out["CalcMode"] = "GROUP_EQUAL"
        return out

    def build_apr_summary(self, ledger_df: pd.DataFrame, members_df: pd.DataFrame) -> pd.DataFrame:
        if ledger_df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["APR_SUMMARY"])
        apr_df = ledger_df[ledger_df["Type"].astype(str).str.strip() == AppConfig.TYPE["APR"]].copy()
        if apr_df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["APR_SUMMARY"])
        apr_df["PersonName"] = apr_df["PersonName"].astype(str).str.strip()
        apr_df["LINE_DisplayName"] = apr_df["LINE_DisplayName"].astype(str).str.strip()
        apr_df["Amount"] = U.to_num_series(apr_df["Amount"])
        active_mem = members_df[members_df["IsActive"] == True].copy() if not members_df.empty and "IsActive" in members_df.columns else members_df.copy()
        total_assets = float(active_mem["Principal"].sum()) if not active_mem.empty else 0.0
        summary = apr_df.groupby("PersonName", as_index=False).agg(Total_APR=("Amount", "sum"), APR_Count=("Amount", "count"))
        disp_map = apr_df.sort_values("Datetime_JST", ascending=False).drop_duplicates(subset=["PersonName"])[["PersonName", "LINE_DisplayName"]].copy()
        summary = summary.merge(disp_map, on="PersonName", how="left")
        summary["Date_JST"] = U.fmt_date(U.now_jst())
        summary["Asset_Ratio"] = summary["Total_APR"].map(lambda x: f"{(float(x) / total_assets) * 100:.2f}%" if total_assets > 0 else "0.00%")
        return summary[["Date_JST", "PersonName", "Total_APR", "APR_Count", "Asset_Ratio", "LINE_DisplayName"]].copy()

    def apply_monthly_compound(self, repo: Repository, members_df: pd.DataFrame, project: str) -> Tuple[int, float]:
        ledger_df = repo.load_ledger()
        if ledger_df.empty:
            return 0, 0.0
        target = ledger_df[
            (ledger_df["Project_Name"].astype(str).str.strip() == str(project).strip())
            & (ledger_df["Type"].astype(str).str.strip() == AppConfig.TYPE["APR"])
            & (~ledger_df["Note"].astype(str).str.contains("COMPOUNDED", na=False))
        ].copy()
        if target.empty:
            return 0, 0.0
        sums = target.groupby("PersonName", as_index=False)["Amount"].sum()
        if sums.empty:
            return 0, 0.0
        ts = U.fmt_dt(U.now_jst())
        updated_count, total_added = 0, 0.0
        add_map = dict(zip(sums["PersonName"].astype(str).str.strip(), U.to_num_series(sums["Amount"])))
        mask = (members_df["Project_Name"].astype(str).str.strip() == str(project).strip()) & (members_df["PersonName"].astype(str).str.strip().isin(add_map.keys()))
        if mask.any():
            for idx in members_df[mask].index.tolist():
                person = str(members_df.loc[idx, "PersonName"]).strip()
                addv = float(add_map.get(person, 0.0))
                if addv == 0:
                    continue
                members_df.loc[idx, "Principal"] = float(members_df.loc[idx, "Principal"]) + addv
                members_df.loc[idx, "UpdatedAt_JST"] = ts
                updated_count += 1
                total_added += addv
        if updated_count > 0:
            repo.write_members(members_df)
            ws = repo.gs.ws("LEDGER")
            values = ws.get_all_values()
            if values and len(values) >= 2:
                headers = values[0]
                note_idx = headers.index("Note") + 1 if "Note" in headers else None
                if note_idx:
                    for row_no in range(2, len(values) + 1):
                        row = values[row_no - 1]
                        if len(row) < len(headers):
                            row = row + [""] * (len(headers) - len(row))
                        r_project = str(row[headers.index("Project_Name")]).strip()
                        r_type = str(row[headers.index("Type")]).strip()
                        r_note = str(row[headers.index("Note")]).strip()
                        if r_project == str(project).strip() and r_type == AppConfig.TYPE["APR"] and "COMPOUNDED" not in r_note:
                            ws.update_cell(row_no, note_idx, (r_note + " | " if r_note else "") + f"COMPOUNDED:{ts}")
            repo.gs.clear_cache()
        return updated_count, total_added
