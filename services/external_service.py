from __future__ import annotations

from typing import List, Optional
import json

import requests
import streamlit as st

from core.utils import U


class ExternalService:
    @staticmethod
    def get_line_token(ns: str) -> str:
        line = st.secrets.get("line", {}) or {}
        tokens = line.get("tokens")
        if tokens:
            tok = str(tokens.get(ns, "")).strip()
            if tok:
                return tok
        legacy = str(line.get("channel_access_token", "")).strip()
        if legacy:
            return legacy
        st.error("LINEトークンが未設定です。")
        st.stop()

    @staticmethod
    def send_line_push(token: str, user_id: str, text: str, image_url: Optional[str] = None) -> int:
        if not user_id:
            return 400
        url = "https://api.line.me/v2/bot/message/push"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
        messages = [{"type": "text", "text": text}]
        if image_url:
            messages.append({"type": "image", "originalContentUrl": image_url, "previewImageUrl": image_url})
        try:
            r = requests.post(url, headers=headers, data=json.dumps({"to": str(user_id), "messages": messages}), timeout=25)
            return r.status_code
        except Exception:
            return 500

    @staticmethod
    def upload_imgbb(file_bytes: bytes) -> Optional[str]:
        try:
            key = st.secrets["imgbb"]["api_key"]
        except Exception:
            return None
        try:
            res = requests.post("https://api.imgbb.com/1/upload", params={"key": key}, files={"image": file_bytes}, timeout=30)
            return res.json()["data"]["url"]
        except Exception:
            return None

    @staticmethod
    def ocr_space_extract_text_with_crop(
        file_bytes: bytes,
        crop_left_ratio: float,
        crop_top_ratio: float,
        crop_right_ratio: float,
        crop_bottom_ratio: float,
    ) -> str:
        try:
            api_key = st.secrets["ocrspace"]["api_key"]
        except Exception:
            return ""

        texts: List[str] = []
        try:
            cropped_bytes = U.crop_image_by_ratio(
                file_bytes=file_bytes,
                left_ratio=crop_left_ratio,
                top_ratio=crop_top_ratio,
                right_ratio=crop_right_ratio,
                bottom_ratio=crop_bottom_ratio,
            )
            processed_list = U.preprocess_ocr_image(cropped_bytes)
            targets = [("cropped.png", cropped_bytes)] + [(f"processed_{i}.png", b) for i, b in enumerate(processed_list, start=1)]
            for target_name, target_bytes in targets:
                for engine in (2, 1):
                    try:
                        res = requests.post(
                            "https://api.ocr.space/parse/image",
                            files={"filename": (target_name, target_bytes)},
                            data={
                                "apikey": api_key,
                                "language": "eng",
                                "isOverlayRequired": False,
                                "OCREngine": engine,
                                "scale": True,
                                "detectOrientation": True,
                                "isTable": False,
                            },
                            timeout=60,
                        )
                        data = res.json()
                        for p in data.get("ParsedResults", []):
                            txt = str(p.get("ParsedText", "")).strip()
                            if txt:
                                texts.append(txt)
                    except Exception:
                        continue
            uniq, seen = [], set()
            for t in texts:
                key = t.strip()
                if key and key not in seen:
                    seen.add(key)
                    uniq.append(key)
            return "\n\n".join(uniq)
        except Exception:
            return ""
