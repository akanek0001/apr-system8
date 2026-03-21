この版は、ユーザー提供の blank-app-main を基準に、
既知のエラー要因を先回りで修正したフルセットです。

主な反映:
- 元の分割版構成を維持
- UI / サイドバー / APR / Admin / Help 構成は元のまま
- Google Sheets secrets を [connections.gsheets.credentials] で読む
- 従来の [gcp_service_account] にも後方互換対応
- Settings シートが空でも PERSONAL を自動生成
- namespace 運用は元コード準拠

必要な Streamlit Secrets:
[connections.gsheets]
spreadsheet = "YOUR_SPREADSHEET_ID"

[connections.gsheets.credentials]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = """-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----"""
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[admin]
# 例
# pin = "1234"
# または users = [{name="A", pin="1234", namespace="A"}]

[ocrspace]
api_key = "..."

[line.tokens]
A = "..."
B = "..."
C = "..."
D = "..."
