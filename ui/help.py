from __future__ import annotations

import io
import re
from typing import Dict

import requests
import streamlit as st
from PIL import Image, ImageDraw

from config import AppConfig
from repository.repository import Repository
from core.auth import AdminAuth


class HelpPage:
    def __init__(self, repo: Repository):
        self.repo = repo

    # =========================
    # OCR API
    # =========================
    def _ocr_request(self, img_bytes: bytes) -> str:
        api_key = st.secrets["ocrspace"]["api_key"]

        res = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("img.png", img_bytes)},
            data={
                "apikey": api_key,
                "language": "eng",
                "isOverlayRequired": False,
            },
            timeout=30,
        )

        data = res.json()
        if "ParsedResults" not in data or not data["ParsedResults"]:
            return ""
        return str(data["ParsedResults"][0].get("ParsedText", "")).strip()

    # =========================
    # 画像切り抜き
    # =========================
    def _crop(self, img: Image.Image, box: Dict[str, float]) -> Image.Image:
        w, h = img.size
        return img.crop(
            (
                int(box["left"] * w),
                int(box["top"] * h),
                int(box["right"] * w),
                int(box["bottom"] * h),
            )
        )

    # =========================
    # 数値抽出
    # =========================
    def _num(self, text: str) -> float:
        m = re.findall(r"[-+]?\d*\.\d+|\d+", str(text).replace(",", ""))
        return float(m[0]) if m else 0.0

    # =========================
    # 枠描画
    # =========================
    def _draw(self, img: Image.Image, boxes: Dict[str, Dict[str, float]]) -> Image.Image:
        d = ImageDraw.Draw(img)
        w, h = img.size

        for b in boxes.values():
            d.rectangle(
                [
                    (b["left"] * w, b["top"] * h),
                    (b["right"] * w, b["bottom"] * h),
                ],
                outline="red",
                width=3,
            )
        return img

    # =========================
    # メイン
    # =========================
    def render(self) -> None:
        st.title("ヘルプ / OCR設定")
        st.caption(f"管理者: {AdminAuth.current_namespace()}")

        settings_df = self.repo.load_settings()
        projects = self.repo.active_projects(settings_df)

        st.markdown(
            """
## 使用シート一覧

### シート命名ルール
すべてのシートは次の形式で統一します。

`<BaseName>__<Namespace>`

例:
- Settings__A
- Members__A
- Ledger__A
- LineUsers__A
- APR_Summary__A
- SmartVault_History__A
- OCR_Transaction__A
- OCR_Transaction_History__A
- APR_Auto_Queue__A

`_A` ではなく、必ず `__A` を使います。  
無印シートは使いません。

---

### A環境の使用シート
- Settings__A
- Members__A
- Ledger__A
- LineUsers__A
- APR_Summary__A
- SmartVault_History__A
- OCR_Transaction__A
- OCR_Transaction_History__A
- APR_Auto_Queue__A

---

## シート役割

### Settings__A
APR設定、OCR座標、Compound_Timing、Active管理

### Members__A
メンバー管理（元本、LINE ID、Rank、状態）

### Ledger__A
APR、入出金、LINE送信など全履歴

### LineUsers__A
LINEユーザー情報

### APR_Summary__A
日次APR集計

### SmartVault_History__A
Liquidity、Yesterday Profit、APR の履歴

### OCR_Transaction__A
OCR解析の作業データ

### OCR_Transaction_History__A
OCR履歴、重複防止

### APR_Auto_Queue__A
APR自動処理キュー

---

## 計算ロジック

### Rank係数
- Master = 0.67
- Elite = 0.60

### Compound_Timing
- daily = 日次複利
- monthly = 月次複利
- none = 複利なし

### PERSONAL
DailyAPR = Principal × APR ÷ 100 × Rank係数 ÷ 365

### GROUP
TotalAPR = 総元本 × APR ÷ 100 × Net_Factor ÷ 365  
DailyAPR = TotalAPR ÷ 対象人数

### 挙動
- daily: 元本へ即時反映
- monthly: 月次反映
- none: Ledger記録のみ

---

## OCR仕様

### SmartVault OCR
- Total Liquidity
- Yesterday Profit
- APR

### Transaction OCR
- Date
- Type
- USD

OCR座標は Settings__A で管理します。
"""
        )

        if not projects:
            st.warning("有効なプロジェクトがありません。")
            return

        project = st.selectbox("OCR設定対象プロジェクト", projects, key="help_project")
        row = settings_df[settings_df["Project_Name"].astype(str).str.strip() == str(project).strip()].iloc[0]

        def g(key: str, default: float) -> float:
            try:
                value = row.get(key, default)
                if str(value).strip() == "":
                    return float(default)
                return float(value)
            except Exception:
                return float(default)

        st.subheader("OCRテスト")

        boxes = {
            "LIQ": {
                "left": g("SV_Total_Liquidity_Left_Mobile", 0.05),
                "top": g("SV_Total_Liquidity_Top_Mobile", 0.25),
                "right": g("SV_Total_Liquidity_Right_Mobile", 0.40),
                "bottom": g("SV_Total_Liquidity_Bottom_Mobile", 0.34),
            },
            "PROFIT": {
                "left": g("SV_Yesterday_Profit_Left_Mobile", 0.40),
                "top": g("SV_Yesterday_Profit_Top_Mobile", 0.25),
                "right": g("SV_Yesterday_Profit_Right_Mobile", 0.70),
                "bottom": g("SV_Yesterday_Profit_Bottom_Mobile", 0.34),
            },
            "APR": {
                "left": g("SV_APR_Left_Mobile", 0.70),
                "top": g("SV_APR_Top_Mobile", 0.25),
                "right": g("SV_APR_Right_Mobile", 0.95),
                "bottom": g("SV_APR_Bottom_Mobile", 0.34),
            },
        }

        f = st.file_uploader("画像", type=["png", "jpg", "jpeg"], key="help_ocr_file")

        if not f:
            return

        img = Image.open(f).convert("RGB")
        st.image(self._draw(img.copy(), boxes), caption="OCR範囲")

        results = {}

        for k, b in boxes.items():
            crop = self._crop(img, b)
            buf = io.BytesIO()
            crop.save(buf, format="PNG")

            txt = self._ocr_request(buf.getvalue())
            results[k] = {
                "text": txt,
                "value": self._num(txt),
            }

        c1, c2, c3 = st.columns(3)
        c1.metric("Liquidity", f"{results['LIQ']['value']}")
        c2.metric("Yesterday Profit", f"{results['PROFIT']['value']}")
        c3.metric("APR", f"{results['APR']['value']}")

        st.text_area("RAW", str(results), height=220)
