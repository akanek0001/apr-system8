from __future__ import annotations

import pandas as pd

from config import AppConfig
from core.utils import U


class FinanceEngine:
    def rank_factor(self, rank: str) -> float:
        r = U.normalize_rank(rank)
        if r == AppConfig.RANK["ELITE"]:
            return float(AppConfig.FACTOR["ELITE"])
        return float(AppConfig.FACTOR["MASTER"])

    def compound_mode(self, value: str) -> str:
        return U.normalize_compound(value)

    def calc_personal_daily_apr(
        self,
        principal: float,
        apr_percent: float,
        rank: str,
    ) -> float:
        principal = float(U.to_f(principal, 0.0))
        apr_percent = float(U.to_f(apr_percent, 0.0))
        factor = self.rank_factor(rank)
        return principal * (apr_percent / 100.0) * factor / 365.0

    def calc_group_total_daily_apr(
        self,
        total_principal: float,
        apr_percent: float,
        net_factor: float,
    ) -> float:
        total_principal = float(U.to_f(total_principal, 0.0))
        apr_percent = float(U.to_f(apr_percent, 0.0))
        net_factor = float(U.to_f(net_factor, AppConfig.FACTOR["MASTER"]))
        return total_principal * (apr_percent / 100.0) * net_factor / 365.0

    def calc_group_member_daily_apr(
        self,
        total_principal: float,
        apr_percent: float,
        net_factor: float,
        member_count: int,
    ) -> float:
        member_count = int(member_count or 0)
        if member_count <= 0:
            return 0.0

        total_apr = self.calc_group_total_daily_apr(
            total_principal,
            apr_percent,
            net_factor,
        )
        return total_apr / member_count

    def build_apr_result(
        self,
        settings_df: pd.DataFrame,
        members_df: pd.DataFrame,
        project: str,
        apr_percent: float,
    ) -> pd.DataFrame:
        if members_df is None or members_df.empty:
            return pd.DataFrame()

        project = str(project).strip()
        apr_percent = float(U.to_f(apr_percent, 0.0))

        mdf = members_df.copy()
        mdf = mdf.loc[:, ~mdf.columns.duplicated()]
        mdf["Project_Name"] = mdf["Project_Name"].astype(str).str.strip()
        mdf["PersonName"] = mdf["PersonName"].astype(str).str.strip()
        mdf["Principal"] = U.to_num_series(mdf["Principal"], 0.0)
        mdf["Rank"] = mdf["Rank"].apply(U.normalize_rank)
        mdf["IsActive"] = mdf["IsActive"].apply(U.truthy)

        mdf = mdf[
            (mdf["Project_Name"] == project) &
            (mdf["IsActive"] == True)
        ].copy()

        if mdf.empty:
            return pd.DataFrame()

        if project.upper() == AppConfig.PROJECT["PERSONAL"]:
            mdf["DailyAPR"] = mdf.apply(
                lambda r: self.calc_personal_daily_apr(
                    r["Principal"],
                    apr_percent,
                    r["Rank"],
                ),
                axis=1,
            )
            return mdf.reset_index(drop=True)

        net_factor = float(AppConfig.FACTOR["MASTER"])

        if settings_df is not None and not settings_df.empty:
            sdf = settings_df.copy()
            sdf = sdf.loc[:, ~sdf.columns.duplicated()]
            sdf["Project_Name"] = sdf["Project_Name"].astype(str).str.strip()

            hit = sdf[sdf["Project_Name"] == project]
            if not hit.empty:
                net_factor = float(
                    U.to_f(
                        hit.iloc[0].get("Net_Factor", net_factor),
                        net_factor,
                    )
                )

        total_principal = float(mdf["Principal"].sum())
        member_count = int(len(mdf))

        member_apr = self.calc_group_member_daily_apr(
            total_principal,
            apr_percent,
            net_factor,
            member_count,
        )

        mdf["DailyAPR"] = float(member_apr)
        return mdf.reset_index(drop=True)

    def apply_daily_compound(
        self,
        members_df: pd.DataFrame,
        apr_df: pd.DataFrame,
        project: str,
    ) -> pd.DataFrame:
        if members_df is None or members_df.empty:
            return members_df.copy()

        if apr_df is None or apr_df.empty:
            return members_df.copy()

        out = members_df.copy()
        out = out.loc[:, ~out.columns.duplicated()]
        out["Project_Name"] = out["Project_Name"].astype(str).str.strip()
        out["PersonName"] = out["PersonName"].astype(str).str.strip()
        out["Principal"] = U.to_num_series(out["Principal"], 0.0)

        tmp = apr_df.copy()
        tmp["Project_Name"] = tmp["Project_Name"].astype(str).str.strip()
        tmp["PersonName"] = tmp["PersonName"].astype(str).str.strip()
        tmp["DailyAPR"] = U.to_num_series(tmp["DailyAPR"], 0.0)

        for _, r in tmp.iterrows():
            mask = (
                (out["Project_Name"] == project) &
                (out["PersonName"] == r["PersonName"])
            )

            if mask.any():
                out.loc[mask, "Principal"] += float(r["DailyAPR"])
                out.loc[mask, "UpdatedAt_JST"] = U.fmt_dt(U.now_jst())

        return out

    def calc_monthly_pending_from_ledger(
        self,
        ledger_df: pd.DataFrame,
        project: str,
    ) -> pd.DataFrame:
        if ledger_df is None or ledger_df.empty:
            return pd.DataFrame(columns=["PersonName", "PendingAPR"])

        df = ledger_df.copy()
        df = df.loc[:, ~df.columns.duplicated()]
        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df["PersonName"] = df["PersonName"].astype(str).str.strip()
        df["Type"] = df["Type"].astype(str).str.strip()
        df["Amount"] = U.to_num_series(df["Amount"], 0.0)

        df = df[df["Project_Name"] == project]

        apr_df = df[df["Type"] == AppConfig.TYPE["APR"]]
        applied_df = df[df["Type"] == "APR_MONTHLY_APPLIED"]

        apr_sum = apr_df.groupby("PersonName")["Amount"].sum()
        applied_sum = applied_df.groupby("PersonName")["Amount"].sum()

        result = pd.DataFrame({
            "PersonName": apr_sum.index,
            "PendingAPR": apr_sum.values - applied_sum.reindex(apr_sum.index, fill_value=0).values,
        })

        return result.reset_index(drop=True)

    def build_apr_summary(
        self,
        apr_df: pd.DataFrame,
        date_jst: str,
    ) -> pd.DataFrame:
        if apr_df is None or apr_df.empty:
            return pd.DataFrame(columns=AppConfig.HEADERS["APR_SUMMARY"])

        df = apr_df.copy()
        df = df.loc[:, ~df.columns.duplicated()]
        df["Project_Name"] = df["Project_Name"].astype(str).str.strip()
        df["PersonName"] = df["PersonName"].astype(str).str.strip()
        df["DailyAPR"] = U.to_num_series(df["DailyAPR"], 0.0)
        df["Principal"] = U.to_num_series(df["Principal"], 0.0)

        if "LINE_DisplayName" not in df.columns:
            df["LINE_DisplayName"] = ""

        total_principal = float(df["Principal"].sum())

        grouped = df.groupby(
            ["Project_Name", "PersonName", "LINE_DisplayName"],
            as_index=False,
        ).agg(
            Total_APR=("DailyAPR", "sum"),
            APR_Count=("DailyAPR", "count"),
            Principal=("Principal", "sum"),
        )

        if total_principal > 0:
            grouped["Asset_Ratio"] = grouped["Principal"].apply(
                lambda x: f"{(float(x) / total_principal):.6f}"
            )
        else:
            grouped["Asset_Ratio"] = "0.000000"

        grouped["Date_JST"] = str(date_jst)

        return grouped[
            [
                "Date_JST",
                "Project_Name",
                "PersonName",
                "Total_APR",
                "APR_Count",
                "Asset_Ratio",
                "LINE_DisplayName",
            ]
        ].reset_index(drop=True)


# END OF FILE
