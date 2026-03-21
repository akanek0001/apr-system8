from __future__ import annotations

import streamlit as st

from config import AppConfig
from repository.repository import Repository
from services.gsheet_service import GSheetService
from store.datastore import DataStore

from app_pages.dashboard_page import DashboardPage
from app_pages.apr_page import APRPage
from app_pages.cash_page import CashPage
from app_pages.admin_page import AdminPage
from app_pages.help_page import HelpPage

from ui.sidebar import Sidebar


class AppController:
    def __init__(self):
        self.gs: GSheetService | None = None
        self.repo: Repository | None = None
        self.store: DataStore | None = None

        self.dashboard: DashboardPage | None = None
        self.apr: APRPage | None = None
        self.cash: CashPage | None = None
        self.admin: AdminPage | None = None
        self.help: HelpPage | None = None
        self.sidebar: Sidebar | None = None

    def setup_services(self) -> None:
        self.gs = GSheetService(AppConfig.SPREADSHEET_ID)
        self.repo = Repository(self.gs)
        self.store = DataStore(self.repo)

        self.dashboard = DashboardPage(self.repo)
        self.apr = APRPage(self.repo)
        self.cash = CashPage(self.repo, self.store)
        self.admin = AdminPage(self.repo, self.store)
        self.help = HelpPage(self.repo)
        self.sidebar = Sidebar()

    def setup_state(self) -> None:
        if "page" not in st.session_state:
            st.session_state["page"] = AppConfig.PAGE["DASHBOARD"]

    def run(self) -> None:
        st.set_page_config(
            page_title=AppConfig.APP_TITLE,
            page_icon=AppConfig.APP_ICON,
            layout="wide",
        )

        self.setup_services()
        self.setup_state()
        self.sidebar.render()

        page = st.session_state["page"]

        if page == AppConfig.PAGE["DASHBOARD"]:
            self.dashboard.render()
        elif page == AppConfig.PAGE["APR"]:
            self.apr.render()
        elif page == AppConfig.PAGE["CASH"]:
            data = self.store.load()
            self.cash.render(
                data["settings_df"],
                data["members_df"],
                data["ledger_df"],
            )
        elif page == AppConfig.PAGE["ADMIN"]:
            data = self.store.load()
            self.admin.render(
                data["settings_df"],
                data["members_df"],
                data["line_users_df"],
            )
        elif page == AppConfig.PAGE["HELP"]:
            self.help.render()
