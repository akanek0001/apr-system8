from __future__ import annotations

from typing import Optional

import streamlit as st

from config import AppConfig
from core.auth import AdminAuth
from core.utils import U
from engine.finance_engine import FinanceEngine
from repository.repository import Repository
from services.gsheet_service import GSheetService
from store.datastore import DataStore
from ui.admin import AdminPage
from ui.apr import APRPage
from ui.cash import CashPage
from ui.dashboard import DashboardPage
from ui.help import HelpPage


class AppController:
    def __init__(self):
        self.gs: Optional[GSheetService] = None
        self.repo: Optional[Repository] = None
        self.engine: Optional[FinanceEngine] = None
        self.store: Optional[DataStore] = None
        self.dashboard_page: Optional[DashboardPage] = None
        self.apr_page: Optional[APRPage] = None
        self.cash_page: Optional[CashPage] = None
        self.admin_page: Optional[AdminPage] = None
        self.help_page: Optional[HelpPage] = None

    def setup_page(self) -> None:
        st.set_page_config(page_title=AppConfig.APP_TITLE, layout=AppConfig.PAGE_LAYOUT, page_icon=AppConfig.APP_ICON)
        st.title(f"{AppConfig.APP_ICON} {AppConfig.APP_TITLE}")

    def setup_auth(self) -> None:
        AdminAuth.require_login()
        st.markdown("""
            <style>
              section[data-testid="stSidebar"] div[role="radiogroup"] > label { margin: 10px 0 !important; padding: 6px 8px !important; }
              section[data-testid="stSidebar"] div[role="radiogroup"] > label p { font-size: 16px !important; }
            </style>
            """, unsafe_allow_html=True)
        with st.sidebar:
            st.caption(f"👤 {AdminAuth.current_label()}")
            if st.button("🔓 ログアウト", use_container_width=True):
                st.session_state["admin_ok"] = False
                st.session_state["admin_name"] = ""
                st.session_state["admin_namespace"] = ""
                for key in AppConfig.SESSION_KEYS.values():
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    def setup_state(self) -> None:
        if "page" not in st.session_state:
            st.session_state["page"] = AppConfig.PAGE["DASHBOARD"]
        if "hide_line_history" not in st.session_state:
            st.session_state["hide_line_history"] = False

    def setup_services(self) -> None:
        con = st.secrets.get("connections", {}).get("gsheets", {})
        sid = U.extract_sheet_id(str(con.get("spreadsheet", "")).strip())
        if not sid:
            st.error("Secrets の [connections.gsheets].spreadsheet が未設定です。")
            st.stop()
        try:
            self.gs = GSheetService(spreadsheet_id=sid, namespace=AdminAuth.current_namespace())
        except Exception as e:
            msg = str(e)
            if "Quota exceeded" in msg or "429" in msg:
                st.error("Google Sheets API の読み取り上限に達しています。1〜2分待ってから再読み込みしてください。")
            else:
                st.error(f"Spreadsheet を開けません。: {e}")
            st.stop()
        self.repo = Repository(self.gs)
        self.engine = FinanceEngine()
        self.store = DataStore(self.repo, self.engine)
        self.dashboard_page = DashboardPage()
        self.apr_page = APRPage(self.repo, self.engine, self.store)
        self.cash_page = CashPage(self.repo, self.store)
        self.admin_page = AdminPage(self.repo, self.store)
        self.help_page = HelpPage(self.repo, self.store)

    def run(self) -> None:
        self.setup_page()
        self.setup_auth()
        self.setup_state()
        self.setup_services()
        data = self.store.load(force=False)
        menu = [AppConfig.PAGE["DASHBOARD"], AppConfig.PAGE["APR"], AppConfig.PAGE["CASH"], AppConfig.PAGE["ADMIN"], AppConfig.PAGE["HELP"]]
        page = st.sidebar.radio("メニュー", options=menu, index=menu.index(st.session_state["page"]) if st.session_state["page"] in menu else 0)
        st.session_state["page"] = page
        if page == AppConfig.PAGE["DASHBOARD"]:
            self.repo.write_apr_summary(data["apr_summary_df"])
            self.dashboard_page.render(data["members_df"], data["ledger_df"], data["apr_summary_df"])
        elif page == AppConfig.PAGE["APR"]:
            self.apr_page.render(data["settings_df"], data["members_df"])
        elif page == AppConfig.PAGE["CASH"]:
            self.cash_page.render(data["settings_df"], data["members_df"])
        elif page == AppConfig.PAGE["ADMIN"]:
            self.admin_page.render(data["settings_df"], data["members_df"], data["line_users_df"])
        else:
            self.help_page.render(self.gs, data["settings_df"])
