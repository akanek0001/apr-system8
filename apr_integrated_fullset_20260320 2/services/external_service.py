from __future__ import annotations

from io import BytesIO
from typing import Optional

import requests
import streamlit as st
from PIL import Image


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
    def get_line_token(namespace: str = "A") -> str:
        return ExternalService._get_secret(f"line.tokens.{namespace}", default="")

    @staticmethod
    def ocr_space_extract_text_with_crop(
        file_bytes: bytes,
        crop_left_ratio: float,
        crop_top_ratio: float,
        crop_right_ratio: float,
        crop_bottom_ratio: float,
    ) -> str:
        api_key = ExternalService._get_secret("ocrspace.api_key", "ocr.api_key", default="")
        if not api_key:
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
                files={"filename": ("crop.png", buf.getvalue(), "image/png")},
                data={
                    "apikey": api_key,
                    "language": "eng",
                    "isOverlayRequired": "false",
                    "OCREngine": "2",
                    "scale": "true",
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()

            parsed = data.get("ParsedResults", [])
            if not parsed:
                return ""

            texts = [str(item.get("ParsedText", "")).strip() for item in parsed]
            return "\n".join([t for t in texts if t]).strip()

        except Exception:
            return ""

    @staticmethod
    def send_line_push(token: str, uid: str, text: str, image_url: Optional[str] = None) -> int:
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
                    "originalContentUrl": image_url,
                    "previewImageUrl": image_url,
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
