from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from config import AppConfig


class U:
    @staticmethod
    def now_jst() -> datetime:
        return datetime.now(AppConfig.JST)

    @staticmethod
    def fmt_dt(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def fmt_date(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d")

    @staticmethod
    def fmt_usd(x: Any) -> str:
        try:
            return f"${float(x):,.2f}"
        except Exception:
            return "$0.00"

    @staticmethod
    def sheet_name(base: str, namespace: str) -> str:
        return f"{str(base).strip()}__{str(namespace).strip()}"

    @staticmethod
    def extract_sheet_id(value: str) -> str:
        s = str(value or "").strip()
        if "/d/" in s:
            try:
                return s.split("/d/")[1].split("/")[0]
            except Exception:
                return s
        return s

    @staticmethod
    def truthy(x: Any) -> bool:
        return str(x).strip().lower() in {"true", "1", "yes", "on", "🟢運用中"}

    @staticmethod
    def truthy_series(s: pd.Series) -> pd.Series:
        return s.apply(U.truthy)

    @staticmethod
    def to_f(x: Any, default: float = 0.0) -> float:
        try:
            return float(str(x).replace(",", "").replace("$", "").replace("%", "").strip())
        except Exception:
            return float(default)

    @staticmethod
    def to_num_series(s: pd.Series, default: float = 0.0) -> pd.Series:
        return pd.to_numeric(
            s.astype(str).str.replace(",", "", regex=False).str.replace("$", "", regex=False),
            errors="coerce",
        ).fillna(default)

    @staticmethod
    def to_ratio(x: Any, default: float = 0.0) -> float:
        try:
            v = float(x)
            if 0.0 <= v <= 1.0:
                return v
            return default
        except Exception:
            return default

    @staticmethod
    def normalize_rank(x: Any) -> str:
        s = str(x).strip().lower()
        if s == "elite":
            return AppConfig.RANK["ELITE"]
        return AppConfig.RANK["MASTER"]

    @staticmethod
    def normalize_compound(x: Any) -> str:
        s = str(x).strip().lower()
        if s in {
            AppConfig.COMPOUND["DAILY"],
            AppConfig.COMPOUND["MONTHLY"],
            AppConfig.COMPOUND["NONE"],
        }:
            return s
        return AppConfig.COMPOUND["NONE"]

    @staticmethod
    def bool_to_status(x: Any) -> str:
        return AppConfig.STATUS["ON"] if U.truthy(x) else AppConfig.STATUS["OFF"]

    @staticmethod
    def status_to_bool(x: Any) -> bool:
        s = str(x).strip()
        return s == AppConfig.STATUS["ON"] or U.truthy(x)

    @staticmethod
    def is_line_uid(x: Any) -> bool:
        s = str(x).strip()
        return s.startswith("U") and len(s) >= 10

    @staticmethod
    def insert_person_name(text: str, person_name: str) -> str:
        name = str(person_name).strip()
        body = str(text or "").strip()
        if not name:
            return body
        return f"{name} 様\n{body}"

    @staticmethod
    def clean_cols(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out.columns = [str(c).strip() for c in out.columns]
        out = out.loc[:, ~out.columns.duplicated()]
        return out
