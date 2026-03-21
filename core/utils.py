from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional
import re

import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw

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
    def fmt_usd(x: float) -> str:
        return f"${x:,.2f}"

    @staticmethod
    def to_f(v: Any) -> float:
        try:
            s = str(v).replace(",", "").replace("$", "").replace("%", "").strip()
            return float(s) if s else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def to_num_series(s: pd.Series, default: float = 0.0) -> pd.Series:
        out = pd.to_numeric(
            s.astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("$", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.strip(),
            errors="coerce",
        )
        return out.fillna(default)

    @staticmethod
    def truthy(v: Any) -> bool:
        if isinstance(v, bool):
            return v
        return str(v).strip().lower() in ("1", "true", "yes", "y", "on", "はい", "t")

    @staticmethod
    def truthy_series(s: pd.Series) -> pd.Series:
        return s.astype(str).str.strip().str.lower().isin(["1", "true", "yes", "y", "on", "はい", "t"])

    @staticmethod
    def clean_cols(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out.columns = out.columns.astype(str).str.replace("\u3000", " ", regex=False).str.strip()
        return out

    @staticmethod
    def extract_sheet_id(value: str) -> str:
        sid = (value or "").strip()
        if "/spreadsheets/d/" in sid:
            try:
                sid = sid.split("/spreadsheets/d/")[1].split("/")[0]
            except Exception:
                pass
        return sid

    @staticmethod
    def normalize_rank(rank: Any) -> str:
        return AppConfig.RANK["ELITE"] if str(rank).strip().lower() == "elite" else AppConfig.RANK["MASTER"]

    @staticmethod
    def rank_factor(rank: Any) -> float:
        return AppConfig.FACTOR["ELITE"] if str(rank).strip().lower() == "elite" else AppConfig.FACTOR["MASTER"]

    @staticmethod
    def bool_to_status(v: Any) -> str:
        return AppConfig.STATUS["ON"] if U.truthy(v) else AppConfig.STATUS["OFF"]

    @staticmethod
    def status_to_bool(v: Any) -> bool:
        return str(v).strip() == AppConfig.STATUS["ON"]

    @staticmethod
    def normalize_compound(v: Any) -> str:
        s = str(v).strip().lower()
        return s if s in AppConfig.COMPOUND.values() else AppConfig.COMPOUND["NONE"]

    @staticmethod
    def compound_label(v: Any) -> str:
        return AppConfig.COMPOUND_LABEL[U.normalize_compound(v)]

    @staticmethod
    def is_line_uid(v: Any) -> bool:
        s = str(v).strip()
        return s.startswith("U") and len(s) >= 10

    @staticmethod
    def sheet_name(base: str, ns: str) -> str:
        ns = str(ns or "").strip()
        return base if not ns or ns == "default" else f"{base}__{ns}"

    @staticmethod
    def insert_person_name(msg_common: str, person_name: str) -> str:
        name_line = f"{person_name} 様"
        lines = msg_common.splitlines()
        if name_line in lines:
            return msg_common
        if lines and lines[0].strip() == "【ご連絡】":
            return "\n".join([lines[0], name_line] + lines[1:])
        return "\n".join([name_line] + lines)

    @staticmethod
    def apr_val(x: str) -> float:
        s = str(x).replace("%", "").replace(",", "").strip()
        if not s:
            return 0.0
        try:
            return float(s)
        except Exception:
            return 0.0

    @staticmethod
    def to_ratio(v: Any, default: float) -> float:
        try:
            x = float(str(v).strip())
            if 0.0 <= x <= 1.0:
                return x
            return default
        except Exception:
            return default

    @staticmethod
    def crop_image_by_ratio(
        file_bytes: bytes,
        left_ratio: float,
        top_ratio: float,
        right_ratio: float,
        bottom_ratio: float,
    ) -> bytes:
        try:
            img = Image.open(BytesIO(file_bytes)).convert("RGB")
            w, h = img.size

            left = max(0, min(int(w * left_ratio), w - 1))
            top = max(0, min(int(h * top_ratio), h - 1))
            right = max(left + 1, min(int(w * right_ratio), w))
            bottom = max(top + 1, min(int(h * bottom_ratio), h))

            cropped = img.crop((left, top, right, bottom))
            buf = BytesIO()
            cropped.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            return file_bytes

    @staticmethod
    def is_mobile_tall_image(file_bytes: bytes) -> bool:
        try:
            img = Image.open(BytesIO(file_bytes))
            w, h = img.size
            return h / max(w, 1) > 1.45
        except Exception:
            return False

    @staticmethod
    def preprocess_ocr_image(file_bytes: bytes) -> List[bytes]:
        outputs: List[bytes] = []
        try:
            base = Image.open(BytesIO(file_bytes)).convert("L")
            variants: List[Image.Image] = []

            img1 = ImageOps.autocontrast(base)
            img1 = ImageEnhance.Contrast(img1).enhance(3.0)
            img1 = ImageEnhance.Sharpness(img1).enhance(2.5)
            img1 = img1.resize((base.width * 4, base.height * 4))
            variants.append(img1)

            img2 = ImageOps.autocontrast(base)
            img2 = ImageEnhance.Contrast(img2).enhance(3.5)
            img2 = img2.resize((base.width * 5, base.height * 5))
            img2 = img2.point(lambda x: 255 if x > 165 else 0)
            variants.append(img2)

            img3 = ImageOps.autocontrast(base)
            img3 = ImageEnhance.Contrast(img3).enhance(3.2)
            img3 = img3.resize((base.width * 5, base.height * 5))
            img3 = img3.point(lambda x: 255 if x > 145 else 0)
            variants.append(img3)

            img4 = ImageOps.autocontrast(base)
            img4 = img4.filter(ImageFilter.MedianFilter(size=3))
            img4 = ImageEnhance.Contrast(img4).enhance(2.8)
            img4 = ImageEnhance.Sharpness(img4).enhance(3.2)
            img4 = img4.resize((base.width * 4, base.height * 4))
            variants.append(img4)

            for img in variants:
                buf = BytesIO()
                img.save(buf, format="PNG")
                outputs.append(buf.getvalue())
        except Exception:
            return [file_bytes]
        return outputs if outputs else [file_bytes]

    @staticmethod
    def extract_percent_candidates(text: str) -> List[float]:
        if not text:
            return []
        norm = str(text)
        replace_map = {
            "％": "%", "O": "0", "o": "0", "Q": "0", "D": "0", "I": "1", "l": "1", "|": "1", "S": "5", "s": "5", ",": ".",
        }
        for k, v in replace_map.items():
            norm = norm.replace(k, v)
        norm = re.sub(r"[ \t\u3000]+", " ", norm)
        patterns = [
            r"(?i)apr\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%",
            r"(?i)apr\s*[:：]?\s*(\d+(?:\.\d+)?)",
            r"(?i)apy\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%",
            r"(?i)rate\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%",
            r"(\d{1,3}\.\d{1,4})",
        ]
        vals: List[float] = []
        seen = set()
        for pat in patterns:
            for v in re.findall(pat, norm):
                try:
                    f = float(v)
                    if 0 <= f <= 300:
                        key = round(f, 6)
                        if key not in seen:
                            seen.add(key)
                            vals.append(f)
                except Exception:
                    pass
        def score(x: float) -> tuple:
            if 1 <= x <= 80:
                return (0, abs(x - 40))
            if 80 < x <= 150:
                return (1, abs(x - 100))
            return (2, x)
        return sorted(vals, key=score)

    @staticmethod
    def extract_usd_candidates(text: str) -> List[float]:
        if not text:
            return []
        norm = str(text)
        replace_map = {
            "＄": "$", "，": ",", "。": ".", "O": "0", "o": "0", "Q": "0", "D": "0", "I": "1", "l": "1", "|": "1", "S": "5", "s": "5",
        }
        for k, v in replace_map.items():
            norm = norm.replace(k, v)
        norm = re.sub(r"[ \t\u3000]+", " ", norm)
        patterns = [r"\$?\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?)", r"\$?\s*(\d+\.\d+)"]
        vals: List[float] = []
        seen = set()
        for pat in patterns:
            for v in re.findall(pat, norm):
                try:
                    f = float(str(v).replace(",", ""))
                    if 0 <= f <= 1000000000:
                        key = round(f, 6)
                        if key not in seen:
                            seen.add(key)
                            vals.append(f)
                except Exception:
                    pass
        return vals

    @staticmethod
    def pick_total_liquidity(vals: List[float]) -> Optional[float]:
        if not vals:
            return None
        positives = [float(v) for v in vals if float(v) > 0]
        if not positives:
            return None
        return max(positives)

    @staticmethod
    def pick_yesterday_profit(vals: List[float]) -> Optional[float]:
        if not vals:
            return None
        candidates = [float(v) for v in vals if float(v) >= 0]
        if not candidates:
            return None
        small_first = [v for v in candidates if v <= 1000000]
        if small_first:
            return sorted(small_first)[0] if len(small_first) == 1 else min(small_first, key=lambda x: len(str(int(x))))
        return min(candidates)

    @staticmethod
    def draw_ocr_boxes(file_bytes: bytes, boxes: Dict[str, Dict[str, float]]) -> bytes:
        try:
            img = Image.open(BytesIO(file_bytes)).convert("RGB")
            draw = ImageDraw.Draw(img)
            w, h = img.size
            for label, box in boxes.items():
                left = int(w * box["left"])
                top = int(h * box["top"])
                right = int(w * box["right"])
                bottom = int(h * box["bottom"])
                draw.rectangle((left, top, right, bottom), outline="red", width=4)
                draw.text((left, max(0, top - 20)), label, fill="red")
            buf = BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception:
            return file_bytes

    @staticmethod
    def detect_source_mode(
        final_liquidity: float,
        final_profit: float,
        final_apr: float,
        ocr_liquidity: Optional[float],
        ocr_profit: Optional[float],
        ocr_apr: Optional[float],
    ) -> str:
        has_ocr = any(v is not None for v in [ocr_liquidity, ocr_profit, ocr_apr])
        if not has_ocr:
            return "manual"
        def same(a: Optional[float], b: float) -> bool:
            if a is None:
                return False
            return abs(float(a) - float(b)) < 1e-9
        if same(ocr_liquidity, final_liquidity) and same(ocr_profit, final_profit) and same(ocr_apr, final_apr):
            return "ocr"
        return "ocr+manual"
