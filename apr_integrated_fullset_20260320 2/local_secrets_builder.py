from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


class AppConfig:
    APP_TITLE = "secrets.toml 自動生成"
    APP_ICON = "🔐"
    DEFAULT_OUTPUT_DIR = ".streamlit"
    DEFAULT_OUTPUT_FILE = "secrets.toml"


class SecretsTomlBuilder:
    @staticmethod
    def _escape_toml_string(value: str) -> str:
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _normalize_private_key(value: str) -> str:
        text = str(value or "").strip()

        if not text:
            return ""

        # JSON由来で \\n になっている場合を本当の改行へ戻す
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\r\n", "\n")

        if not text.endswith("\n"):
            text += "\n"

        # secrets.toml 用に再度 \n 文字列へ変換
        return text.replace("\n", "\\n")

    @staticmethod
    def build_from_inputs(
        spreadsheet_id: str,
        service_account: dict,
        ocr_api_key: str,
        line_token_a: str,
    ) -> str:
        private_key = SecretsTomlBuilder._normalize_private_key(
            service_account.get("private_key", "")
        )

        lines = [
            "[gcp_service_account]",
            f'type = "{SecretsTomlBuilder._escape_toml_string(service_account.get("type", "service_account"))}"',
            f'project_id = "{SecretsTomlBuilder._escape_toml_string(service_account.get("project_id", ""))}"',
            f'private_key_id = "{SecretsTomlBuilder._escape_toml_string(service_account.get("private_key_id", ""))}"',
            f'private_key = "{SecretsTomlBuilder._escape_toml_string(private_key)}"',
            f'client_email = "{SecretsTomlBuilder._escape_toml_string(service_account.get("client_email", ""))}"',
            f'client_id = "{SecretsTomlBuilder._escape_toml_string(service_account.get("client_id", ""))}"',
            f'auth_uri = "{SecretsTomlBuilder._escape_toml_string(service_account.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"))}"',
            f'token_uri = "{SecretsTomlBuilder._escape_toml_string(service_account.get("token_uri", "https://oauth2.googleapis.com/token"))}"',
            f'auth_provider_x509_cert_url = "{SecretsTomlBuilder._escape_toml_string(service_account.get("auth_provider_x509_cert_url", "https://www.googleapis.com/oauth2/v1/certs"))}"',
            f'client_x509_cert_url = "{SecretsTomlBuilder._escape_toml_string(service_account.get("client_x509_cert_url", ""))}"',
            "",
            '[ocrspace]',
            f'api_key = "{SecretsTomlBuilder._escape_toml_string(ocr_api_key)}"',
            "",
            '[line.tokens]',
            f'A = "{SecretsTomlBuilder._escape_toml_string(line_token_a)}"',
            "",
            '[app]',
            f'spreadsheet_id = "{SecretsTomlBuilder._escape_toml_string(spreadsheet_id)}"',
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def parse_service_account_json(raw_text: str) -> dict:
        text = str(raw_text or "").strip()
        if not text:
            raise ValueError("サービスアカウントJSONが空です。")

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"サービスアカウントJSONの形式が不正です: {e}") from e

        required = [
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
        ]
        missing = [k for k in required if not str(data.get(k, "")).strip()]
        if missing:
            raise ValueError(
                "サービスアカウントJSONに不足があります: " + ", ".join(missing)
            )

        return data

    @staticmethod
    def write_file(project_root: str, toml_text: str) -> Path:
        root = Path(project_root).expanduser().resolve()
        out_dir = root / AppConfig.DEFAULT_OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        out_path = out_dir / AppConfig.DEFAULT_OUTPUT_FILE
        out_path.write_text(toml_text, encoding="utf-8")
        return out_path


def main() -> None:
    st.set_page_config(
        page_title=AppConfig.APP_TITLE,
        page_icon=AppConfig.APP_ICON,
        layout="wide",
    )

    st.title("🔐 secrets.toml 自動生成")
    st.caption("ローカルで値を貼り付けるだけで .streamlit/secrets.toml を作成します。")

    left, right = st.columns([1, 1])

    with left:
        project_root = st.text_input(
            "プロジェクトフォルダのパス",
            value=str(Path.cwd()),
            help="streamlit_app.py があるフォルダを指定します。",
        )

        spreadsheet_id = st.text_input(
            "Spreadsheet ID",
            value="",
        )

        ocr_api_key = st.text_input(
            "OCR.space API Key",
            value="",
            type="password",
        )

        line_token_a = st.text_input(
            "LINE Channel Access Token (A)",
            value="",
            type="password",
        )

    with right:
        service_account_raw = st.text_area(
            "GoogleサービスアカウントJSONをそのまま貼り付け",
            value="",
            height=420,
            placeholder='{"type":"service_account","project_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\\n..."}',
        )

    c1, c2 = st.columns([1, 1])

    if c1.button("secrets.toml を生成", use_container_width=True):
        try:
            sa = SecretsTomlBuilder.parse_service_account_json(service_account_raw)
            toml_text = SecretsTomlBuilder.build_from_inputs(
                spreadsheet_id=spreadsheet_id,
                service_account=sa,
                ocr_api_key=ocr_api_key,
                line_token_a=line_token_a,
            )

            st.session_state["generated_toml"] = toml_text
            st.success("生成しました。下の内容を確認してください。")
        except Exception as e:
            st.error(str(e))

    if c2.button("生成して .streamlit/secrets.toml に保存", use_container_width=True):
        try:
            sa = SecretsTomlBuilder.parse_service_account_json(service_account_raw)
            toml_text = SecretsTomlBuilder.build_from_inputs(
                spreadsheet_id=spreadsheet_id,
                service_account=sa,
                ocr_api_key=ocr_api_key,
                line_token_a=line_token_a,
            )
            out_path = SecretsTomlBuilder.write_file(project_root, toml_text)
            st.session_state["generated_toml"] = toml_text
            st.success(f"保存しました: {out_path}")
        except Exception as e:
            st.error(str(e))

    generated = st.session_state.get("generated_toml", "")
    if generated:
        st.markdown("### 生成結果")
        st.code(generated, language="toml")
        st.download_button(
            "secrets.toml をダウンロード",
            data=generated.encode("utf-8"),
            file_name="secrets.toml",
            mime="text/plain",
            use_container_width=True,
        )

    st.markdown("### 実行方法")
    st.code("streamlit run local_secrets_builder.py", language="bash")


if __name__ == "__main__":
    main()
