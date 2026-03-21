from __future__ import annotations

from io import BytesIO
from typing import Optional

import requests
import streamlit as st
from PIL import Image

from core.auth import AdminAuth


class ExternalService:
    @staticmethod
    def _get_secret(*keys: str, default: str = "") -> str:
        for path in keys:
            try:
                cur = st.secrets
                for k in path.split("."):
                    cur = cur[k]
                return str(cur).strip()
            except Exception:
                pass
        return default

    @staticmethod
    def get_line_token(namespace: str | None = None) -> str:
        ns = str(namespace or AdminAuth.current_namespace()).strip() or "A"
        return ExternalService._get_secret(f"line.tokens.{ns}", default="")

    @staticmethod
    def send_line_push(
        token: str,
        uid: str,
        text: str,
        image_url: Optional[str] = None,
    ) -> int:
        if not token or not uid:
            return 0

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        messages = [{"type": "text", "text": str(text)}]

        if image_url:
            messages.append(
                {
                    "type": "image",
                    "originalContentUrl": str(image_url),
                    "previewImageUrl": str(image_url),
                }
            )

        try:
            resp = requests.post(
                "https://api.line.me/v2/bot/message/push",
                headers=headers,
                json={"to": uid, "messages": messages},
                timeout=30,
            )
            return int(resp.status_code)
        except Exception:
            return 0

    @staticmethod
    def upload_imgbb(file_bytes: bytes | None) -> Optional[str]:
        if not file_bytes:
            return None

        api_key = ExternalService._get_secret("imgbb.api_key", default="")
        if not api_key:
            return None

        try:
            payload = {"key": api_key}
            files = {"image": file_bytes}

            resp = requests.post(
                "https://api.imgbb.com/1/upload",
                data=payload,
                files=files,
                timeout=60,
            )
            data = resp.json()

            if not data.get("success"):
                return None

            return str(data["data"]["url"]).strip()
        except Exception:
            return None

    @staticmethod
    def _ocr_api_key() -> str:
        return ExternalService._get_secret("ocrspace.api_key", "ocr.api_key", default="")

    @staticmethod
    def ocr_space_extract_text(image_bytes: bytes) -> str:
        api_key = ExternalService._ocr_api_key()
        if not api_key or not image_bytes:
            return ""

        try:
            resp = requests.post(
                "https://api.ocr.space/parse/image",
                files={"file": ("image.png", image_bytes)},
                data={
                    "apikey": api_key,
                    "language": "eng",
                    "isOverlayRequired": "false",
                    "OCREngine": "2",
                    "scale": "true",
                },
                timeout=60,
            )
            data = resp.json()

            parsed = data.get("ParsedResults", [])
            if not parsed:
                return ""

            texts = [str(item.get("ParsedText", "")).strip() for item in parsed]
            return "\n".join([t for t in texts if t]).strip()
        except Exception:
            return ""

    @staticmethod
    def ocr_space_extract_text_with_crop(
        file_bytes: bytes,
        crop_left_ratio: float,
        crop_top_ratio: float,
        crop_right_ratio: float,
        crop_bottom_ratio: float,
    ) -> str:
        api_key = ExternalService._ocr_api_key()
        if not api_key or not file_bytes:
            return ""

        try:
            image = Image.open(BytesIO(file_bytes)).convert("RGB")
            w, h = image.size

            left = max(0, min(w, int(w * float(crop_left_ratio))))
            top = max(0, min(h, int(h * float(crop_top_ratio))))
            right = max(0, min(w, int(w * float(crop_right_ratio))))
            bottom = max(0, min(h, int(h * float(crop_bottom_ratio))))

            if right <= left or bottom <= top:
                return ""

            cropped = image.crop((left, top, right, bottom))

            buf = BytesIO()
            cropped.save(buf, format="PNG")
            buf.seek(0)

            resp = requests.post(
                "https://api.ocr.space/parse/image",
                files={"file": ("crop.png", buf.getvalue())},
                data={
                    "apikey": api_key,
                    "language": "eng",
                    "isOverlayRequired": "false",
                    "OCREngine": "2",
                    "scale": "true",
                },
                timeout=60,
            )
            data = resp.json()

            parsed = data.get("ParsedResults", [])
            if not parsed:
                return ""

            texts = [str(item.get("ParsedText", "")).strip() for item in parsed]
            return "\n".join([t for t in texts if t]).strip()
        except Exception:
            return ""

    @staticmethod
    def extract_number_candidates(text: str) -> list[float]:
        import re

        if not text:
            return []

        found = re.findall(r"[-+]?\d[\d,]*\.?\d*", str(text))
        out: list[float] = []

        for x in found:
            xs = str(x).replace(",", "").strip()
            if xs in {"", "-", "+", ".", "-.", "+."}:
                continue
            try:
                out.append(float(xs))
            except Exception:
                pass

        return out

    @staticmethod
    def extract_first_number(text: str, default: float = 0.0) -> float:
        vals = ExternalService.extract_number_candidates(text)
        if not vals:
            return float(default)
        return float(vals[0])

    @staticmethod
    def extract_max_number(text: str, default: float = 0.0) -> float:
        vals = ExternalService.extract_number_candidates(text)
        if not vals:
            return float(default)
        return float(max(vals))


# END OF FILE
