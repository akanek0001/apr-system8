from __future__ import annotations

import io
import re
from typing import Dict

import streamlit as st
from PIL import Image, ImageDraw

from core.auth import AdminAuth
from repository.repository import Repository
from services.external_service import ExternalService


class HelpPage:
    def __init__(self, repo: Repository):
        self.repo = repo

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

---

## Secrets 形式

```toml
[connections.gsheets]
spreadsheet = "YOUR_SPREADSHEET_ID"

[connections.gsheets.credentials]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = \"\"\"-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----\"\"\"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[ocrspace]
api_key = "..."

[line.tokens]
A = "..."
B = "..."
C = "..."
D = "..."
