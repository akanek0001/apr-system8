from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, List, Optional
import re

import pandas as pd
from PIL import Image, ImageDraw

from config import AppConfig
from services.external_service import ExternalService


@dataclass(frozen=True)
class OCRBox:
    left: float
    top: float
    right: float
    bottom: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "left": float(self.left),
            "top": float(self.top),
            "right": float(self.right),
            "bottom": float(self.bottom),
        }


class OCRProcessor:
    DEFAULT_TX_LAYOUT_MOBILE = {
        "base_top": 0.220,
        "step": 0.115,
        "max_rows": 12,
        "date_left": 0.050,
        "date_right": 0.450,
        "date_top_offset": 0.000,
        "date_bottom_offset": 0.030,
        "type_left": 0.180,
        "type_right": 0.700,
        "type_top_offset": 0.015,
        "type_bottom_offset": 0.055,
        "usd_left": 0.720,
        "usd_right": 0.960,
        "usd_top_offset": 0.010,
        "usd_bottom_offset": 0.055,
    }

    SMARTVAULT_FALLBACK_MOBILE = {
        "TOTAL_LIQUIDITY": {"left": 0.05, "top": 0.25, "right": 0.40, "bottom": 0.34},
        "YESTERDAY_PROFIT": {"left": 0.41, "top": 0.25, "right": 0.69, "bottom": 0.34},
        "APR": {"left": 0.70, "top": 0.25, "right": 0.93, "bottom": 0.34},
    }

    @staticmethod
    def detect_platform(file_bytes: Optional[bytes]) -> str:
        if not file_bytes:
            return "mobile"
        try:
            img = Image.open(BytesIO(file_bytes))
            w, h = img.size
            return "mobile" if w > 0 and (h / w) > 1.45 else "pc"
        except Exception:
            return "mobile"

    @staticmethod
    def normalize_text(text: str) -> str:
        t = str(text or "")
        t = t.replace("月 ", "月").replace(" 日", "日").replace(" at ", " ")
        t = t.replace("午前", "am").replace("午後", "pm")
        t = re.sub(r"[ \t\u3000]+", " ", t)
        return t.strip()

    @staticmethod
    def _to_ratio(value: Any, default: float) -> float:
        try:
            s = str(value).strip()
            if s == "":
                return float(default)
            v = float(s)
            if v < 0 or v > 1:
                return float(default)
            return float(v)
        except Exception:
            return float(default)

    @staticmethod
    def _to_int(value: Any, default: int) -> int:
        try:
            s = str(value).strip()
            if s == "":
                return int(default)
            v = int(float(s))
            return v if v > 0 else int(default)
        except Exception:
            return int(default)

    @staticmethod
    def _setting_row(settings_df: pd.DataFrame, project: str) -> Optional[pd.Series]:
        if settings_df is None or settings_df.empty:
            return None
        rows = settings_df[settings_df["Project_Name"].astype(str).str.strip() == str(project).strip()]
        if rows.empty:
            return None
        return rows.iloc[0]

    @staticmethod
    def extract_usd_candidates(text: str) -> List[float]:
        found = re.findall(r"\$?\s*(\d+(?:,\d{3})*(?:\.\d+)?)", str(text or ""))
        out = []
        for x in found:
            try:
                out.append(float(x.replace(",", "")))
            except Exception:
                pass
        return out

    @staticmethod
    def extract_percent_candidates(text: str) -> List[float]:
        found = re.findall(r"(\d+(?:\.\d+)?)\s*%", str(text or ""))
        out = []
        for x in found:
            try:
                out.append(float(x))
            except Exception:
                pass
        return out

    @staticmethod
    def draw_ocr_boxes(file_bytes: bytes, boxes: Dict[str, Dict[str, float]]) -> bytes:
        img = Image.open(BytesIO(file_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size

        for _, box in boxes.items():
            draw.rectangle(
                [
                    int(float(box["left"]) * w),
                    int(float(box["top"]) * h),
                    int(float(box["right"]) * w),
                    int(float(box["bottom"]) * h),
                ],
                outline="red",
                width=3,
            )

        out = BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()

    @staticmethod
    def ocr_crop_text(file_bytes: bytes, box: OCRBox) -> str:
        return ExternalService.ocr_space_extract_text_with_crop(
            file_bytes=file_bytes,
            crop_left_ratio=box.left,
            crop_top_ratio=box.top,
            crop_right_ratio=box.right,
            crop_bottom_ratio=box.bottom,
        )

    @classmethod
    def get_smartvault_boxes(cls, settings_df: pd.DataFrame, project: str, platform: str) -> Dict[str, OCRBox]:
        if platform != "mobile":
            raise ValueError("この版では SmartVault OCR は mobile のみ対応です。")

        row = cls._setting_row(settings_df, project)
        f = cls.SMARTVAULT_FALLBACK_MOBILE

        def box(prefix: str, fallback: Dict[str, float]) -> OCRBox:
            if row is None:
                return OCRBox(**fallback)
            return OCRBox(
                left=cls._to_ratio(row.get(f"{prefix}_Left_Mobile"), fallback["left"]),
                top=cls._to_ratio(row.get(f"{prefix}_Top_Mobile"), fallback["top"]),
                right=cls._to_ratio(row.get(f"{prefix}_Right_Mobile"), fallback["right"]),
                bottom=cls._to_ratio(row.get(f"{prefix}_Bottom_Mobile"), fallback["bottom"]),
            )

        return {
            "TOTAL_LIQUIDITY": box("SV_Total_Liquidity", f["TOTAL_LIQUIDITY"]),
            "YESTERDAY_PROFIT": box("SV_Yesterday_Profit", f["YESTERDAY_PROFIT"]),
            "APR": box("SV_APR", f["APR"]),
        }

    @classmethod
    def extract_metrics(cls, file_bytes: bytes, boxes: Dict[str, OCRBox]) -> Dict[str, Any]:
        total_text = cls.ocr_crop_text(file_bytes, boxes["TOTAL_LIQUIDITY"])
        profit_text = cls.ocr_crop_text(file_bytes, boxes["YESTERDAY_PROFIT"])
        apr_text = cls.ocr_crop_text(file_bytes, boxes["APR"])

        total_vals = cls.extract_usd_candidates(total_text)
        profit_vals = cls.extract_usd_candidates(profit_text)
        apr_vals = cls.extract_percent_candidates(apr_text)

        boxed_preview = cls.draw_ocr_boxes(file_bytes, {k: v.to_dict() for k, v in boxes.items()})
        return {
            "total_liquidity": max(total_vals) if total_vals else None,
            "yesterday_profit": max(profit_vals) if profit_vals else None,
            "apr_value": apr_vals[0] if apr_vals else None,
            "preview": boxed_preview,
            "total_text": total_text,
            "profit_text": profit_text,
            "apr_text": apr_text,
        }

    @classmethod
    def get_tx_layout(cls, settings_df: pd.DataFrame, project: str) -> Dict[str, float]:
        row = cls._setting_row(settings_df, project)
        d = cls.DEFAULT_TX_LAYOUT_MOBILE.copy()

        if row is None:
            return d

        return {
            "base_top": cls._to_ratio(row.get("TX_Scan_BaseTop_Ratio_Mobile"), d["base_top"]),
            "step": cls._to_ratio(row.get("TX_Scan_Step_Ratio_Mobile"), d["step"]),
            "max_rows": cls._to_int(row.get("TX_Scan_MaxRows_Mobile"), d["max_rows"]),
            "date_left": cls._to_ratio(row.get("TX_Date_Left_Ratio_Mobile"), d["date_left"]),
            "date_right": cls._to_ratio(row.get("TX_Date_Right_Ratio_Mobile"), d["date_right"]),
            "date_top_offset": cls._to_ratio(row.get("TX_Date_Top_Offset_Ratio_Mobile"), d["date_top_offset"]),
            "date_bottom_offset": cls._to_ratio(row.get("TX_Date_Bottom_Offset_Ratio_Mobile"), d["date_bottom_offset"]),
            "type_left": cls._to_ratio(row.get("TX_Type_Left_Ratio_Mobile"), d["type_left"]),
            "type_right": cls._to_ratio(row.get("TX_Type_Right_Ratio_Mobile"), d["type_right"]),
            "type_top_offset": cls._to_ratio(row.get("TX_Type_Top_Offset_Ratio_Mobile"), d["type_top_offset"]),
            "type_bottom_offset": cls._to_ratio(row.get("TX_Type_Bottom_Offset_Ratio_Mobile"), d["type_bottom_offset"]),
            "usd_left": cls._to_ratio(row.get("TX_USD_Left_Ratio_Mobile"), d["usd_left"]),
            "usd_right": cls._to_ratio(row.get("TX_USD_Right_Ratio_Mobile"), d["usd_right"]),
            "usd_top_offset": cls._to_ratio(row.get("TX_USD_Top_Offset_Ratio_Mobile"), d["usd_top_offset"]),
            "usd_bottom_offset": cls._to_ratio(row.get("TX_USD_Bottom_Offset_Ratio_Mobile"), d["usd_bottom_offset"]),
        }

    @staticmethod
    def build_region_box(row_top: float, left_ratio: float, right_ratio: float, top_offset_ratio: float, bottom_offset_ratio: float) -> OCRBox:
        return OCRBox(
            left=float(left_ratio),
            top=float(row_top + top_offset_ratio),
            right=float(right_ratio),
            bottom=float(row_top + bottom_offset_ratio),
        )

    @classmethod
    def extract_date(cls, text: str) -> str:
        t = cls.normalize_text(text)
        for p in [r"(\d{1,2}\s*月\s*\d{1,2}\s*日)", r"(\d{1,2}/\d{1,2})", r"(\d{1,2}-\d{1,2})"]:
            m = re.search(p, t)
            if m:
                return cls.normalize_text(m.group(1)).replace(" ", "")
        return ""

    @classmethod
    def extract_time(cls, text: str) -> str:
        t = cls.normalize_text(text)
        for p in [r"(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))", r"(\d{1,2}:\d{2})"]:
            m = re.search(p, t)
            if m:
                return cls.normalize_text(m.group(1)).lower()
        return ""

    @classmethod
    def extract_type_label(cls, text: str) -> str:
        t = cls.normalize_text(text)
        if "受け取ったUSDC" in t or "受け取った USDC" in t:
            return "受け取ったUSDC"
        if "USDC" in t:
            return "USDC"
        return ""

    @classmethod
    def extract_amount(cls, text: str) -> Optional[float]:
        t = cls.normalize_text(text)
        m = re.search(r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)", t)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except Exception:
                return None
        vals = cls.extract_usd_candidates(t)
        return max(vals) if vals else None

    @classmethod
    def extract_transaction_rows(cls, file_bytes: bytes, settings_df: pd.DataFrame, project: str) -> List[Dict[str, Any]]:
        layout = cls.get_tx_layout(settings_df, project)
        rows = []

        for i in range(int(layout["max_rows"])):
            row_top = float(layout["base_top"]) + float(layout["step"]) * i

            date_box = cls.build_region_box(row_top, layout["date_left"], layout["date_right"], layout["date_top_offset"], layout["date_bottom_offset"])
            type_box = cls.build_region_box(row_top, layout["type_left"], layout["type_right"], layout["type_top_offset"], layout["type_bottom_offset"])
            usd_box = cls.build_region_box(row_top, layout["usd_left"], layout["usd_right"], layout["usd_top_offset"], layout["usd_bottom_offset"])

            date_text = cls.normalize_text(cls.ocr_crop_text(file_bytes, date_box))
            type_text = cls.normalize_text(cls.ocr_crop_text(file_bytes, type_box))
            usd_text = cls.normalize_text(cls.ocr_crop_text(file_bytes, usd_box))

            joined = "\n".join([date_text, type_text, usd_text]).strip()
            if not joined:
                continue

            date_label = cls.extract_date(date_text or joined)
            time_label = cls.extract_time(date_text or joined)
            type_label = cls.extract_type_label(type_text or joined)
            amount_usd = cls.extract_amount(usd_text or joined)

            if not date_label or not time_label or not type_label or amount_usd is None or amount_usd <= 0:
                continue

            rows.append(
                {
                    "row_index": i + 1,
                    "date_label": date_label,
                    "time_label": time_label,
                    "type_label": type_label,
                    "amount_usd": float(amount_usd),
                    "unique_key": f"{date_label}|{time_label}|{type_label}|{float(amount_usd):.2f}",
                    "raw_text": joined,
                }
            )

        return rows

    @classmethod
    def build_preview_boxes(cls, settings_df: pd.DataFrame, project: str, rows_to_show: int = 3) -> Dict[str, Dict[str, float]]:
        layout = cls.get_tx_layout(settings_df, project)
        out: Dict[str, Dict[str, float]] = {}

        for i in range(max(1, min(rows_to_show, int(layout["max_rows"])))):
            row_top = float(layout["base_top"]) + float(layout["step"]) * i

            out[f"ROW{i+1}_DATE"] = cls.build_region_box(row_top, layout["date_left"], layout["date_right"], layout["date_top_offset"], layout["date_bottom_offset"]).to_dict()
            out[f"ROW{i+1}_TYPE"] = cls.build_region_box(row_top, layout["type_left"], layout["type_right"], layout["type_top_offset"], layout["type_bottom_offset"]).to_dict()
            out[f"ROW{i+1}_USD"] = cls.build_region_box(row_top, layout["usd_left"], layout["usd_right"], layout["usd_top_offset"], layout["usd_bottom_offset"]).to_dict()

        return out
