from __future__ import annotations

import io
import re
from typing import Dict

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw

from config import AppConfig
from repository.repository import Repository
from services.external_service import ExternalService
from core.auth import AdminAuth


class HelpPage:
    def __init__(self, repo: Repository):
        self.repo = repo

    # =========================
    # OCR helper
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

    def _draw(self, img: Image.Image, boxes: Dict[str, Dict[str, float]]) -> Image.Image:
        d = ImageDraw.Draw(img)
        w, h = img.size

        for _, b in boxes.items():
            d.rectangle(
                [
                    (b["left"] * w, b["top"] * h),
                    (b["right"] * w, b["bottom"] * h),
                ],
                outline="red",
                width=3,
            )
        return img

    def _num(self, text: str) -> float:
        m = re.findall(r"[-+]?\d*\.\d+|\d+", str(text).replace(",", ""))
        return float(m[0]) if m else 0.0

    def _safe_float(self, value, default: float) -> float:
        try:
            if str(value).strip() == "":
                return float(default)
            return float(value)
        except Exception:
            return float(default)

    # =========================
    # render
    # =========================
    def render(self) -> None:
        st.title("ヘルプ / OCR設定")
        st.caption(f"管理者: {AdminAuth.current_namespace()}")

        settings_df = self.repo.load_settings()
        projects = self.repo.active_projects(settings_df)

        st.markdown(
            """
## 全体アーキテクチャ（固定）

UI  
↓  
Controller  
↓  
Repository  
↓  
Service  
↓  
External（Sheets / LINE / OCR）

---

## データフロー（実際に動く流れ）

Help で設定確認 / OCRテスト  
↓  
APRページでAPR入力  
↓  
FinanceEngineで計算  
↓  
RepositoryでLedger保存  
↓  
Dashboardで表示  
↓  
必要に応じてLINE送信

---

## シート構造（完全固定）

- Settings__A
- Members__A
- Ledger__A
- LineUsers__A
- APR_Summary__A
- SmartVault_History__A
- OCR_Transaction__A
- OCR_Transaction_History__A
- APR_Auto_Queue__A

※ `_A` ではなく、必ず `__A` を使います  
※ 無印シートは使いません

---

## コア責務（重要）

### UI
- 表示と入力のみ
- 計算しない
- データ保存ロジックを持たない

### Controller
- 全体の接続
- ページ切替
- UI / Repository / Engine / Service の橋渡し

### Repository
- データの読み書き
- DataFrame整形
- シートI/O管理
- 計算しない

### Engine
- APR計算だけ担当
- 外部接続しない

### Service
- OCR / LINE / Sheets など外部接続だけ
- 計算しない

---

## 正しい実装ルール（これ守る）

1. UIは計算しない  
2. Repositoryはロジックを持たない  
3. Engineだけが計算する  
4. Serviceは外部接続だけ  
5. Controllerが全部をつなぐ  

---

## 使用シート役割

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

        st.divider()
        st.subheader("OCRテスト")

        project = st.selectbox("OCR設定対象プロジェクト", projects, key="help_project")
        row = settings_df[settings_df["Project_Name"].astype(str).str.strip() == str(project).strip()].iloc[0]

        boxes = {
            "LIQ": {
                "left": self._safe_float(row.get("SV_Total_Liquidity_Left_Mobile", 0.05), 0.05),
                "top": self._safe_float(row.get("SV_Total_Liquidity_Top_Mobile", 0.25), 0.25),
                "right": self._safe_float(row.get("SV_Total_Liquidity_Right_Mobile", 0.40), 0.40),
                "bottom": self._safe_float(row.get("SV_Total_Liquidity_Bottom_Mobile", 0.34), 0.34),
            },
            "PROFIT": {
                "left": self._safe_float(row.get("SV_Yesterday_Profit_Left_Mobile", 0.40), 0.40),
                "top": self._safe_float(row.get("SV_Yesterday_Profit_Top_Mobile", 0.25), 0.25),
                "right": self._safe_float(row.get("SV_Yesterday_Profit_Right_Mobile", 0.70), 0.70),
                "bottom": self._safe_float(row.get("SV_Yesterday_Profit_Bottom_Mobile", 0.34), 0.34),
            },
            "APR": {
                "left": self._safe_float(row.get("SV_APR_Left_Mobile", 0.70), 0.70),
                "top": self._safe_float(row.get("SV_APR_Top_Mobile", 0.25), 0.25),
                "right": self._safe_float(row.get("SV_APR_Right_Mobile", 0.95), 0.95),
                "bottom": self._safe_float(row.get("SV_APR_Bottom_Mobile", 0.34), 0.34),
            },
        }

        uploaded = st.file_uploader("画像", type=["png", "jpg", "jpeg"], key="help_ocr_file")
        if not uploaded:
            return

        img = Image.open(uploaded).convert("RGB")
        st.image(self._draw(img.copy(), boxes), caption="OCR範囲", use_container_width=True)

        results = {}
        for key, b in boxes.items():
            crop = self._crop(img, b)
            buf = io.BytesIO()
            crop.save(buf, format="PNG")

            txt = ExternalService.ocr_space_extract_text(buf.getvalue())
            results[key] = {
                "text": txt,
                "value": self._num(txt),
            }

        c1, c2, c3 = st.columns(3)
        c1.metric("Liquidity", f"{results['LIQ']['value']}")
        c2.metric("Yesterday Profit", f"{results['PROFIT']['value']}")
        c3.metric("APR", f"{results['APR']['value']}")

        st.text_area("RAW", str(results), height=220)

        # 参考: OCR取引履歴
        st.divider()
        st.subheader("OCR Transaction History（先頭30件）")
        ocr_hist = self.repo.load_ocr_transaction_history()
        if ocr_hist.empty:
            st.info("OCR_Transaction_History は空です。")
        else:
            show = ocr_hist.loc[:, ~ocr_hist.columns.duplicated()].copy()
            st.dataframe(show.head(30), use_container_width=True, hide_index=True)


# END OF FILE
