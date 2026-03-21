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
from ui.dashboard import DashboardPage
from ui.apr import APRPage
from ui.cash import CashPage
from ui.admin import AdminPage
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
        st.set_page_config(
            page_title=AppConfig.APP_TITLE,
            page_icon=AppConfig.APP_ICON,
            layout=AppConfig.PAGE_LAYOUT,
        )
        st.title(f"{AppConfig.APP_ICON} {AppConfig.APP_TITLE}")

    def setup_auth(self) -> None:
        AdminAuth.require_login()

        with st.sidebar:
            st.caption(f"👤 {AdminAuth.current_label()}")
            if st.button("🔓 ログアウト", use_container_width=True):
                AdminAuth.logout()

                for key in AppConfig.SESSION_KEYS.values():
                    if key in st.session_state:
                        del st.session_state[key]

                if "gsheet_cache" in st.session_state:
                    del st.session_state["gsheet_cache"]

                if "page" in st.session_state:
                    del st.session_state["page"]

                st.rerun()

    def setup_state(self) -> None:
        if "page" not in st.session_state:
            st.session_state["page"] = AppConfig.PAGE["DASHBOARD"]

        if "hide_line_history" not in st.session_state:
            st.session_state["hide_line_history"] = False

    def setup_services(self) -> None:
        sid = U.extract_sheet_id(str(AppConfig.SPREADSHEET_ID).strip())

        try:
            self.gs = GSheetService(
                spreadsheet_id=sid,
                namespace=AdminAuth.current_namespace(),
            )
        except Exception as e:
            st.error(f"Spreadsheet を開けません。: {e}")
            st.stop()

        self.repo = Repository(self.gs)
        self.engine = FinanceEngine()
        self.store = DataStore(self.repo, self.engine)

        self.dashboard_page = DashboardPage(self.repo)
        self.apr_page = APRPage(self.repo, self.engine, self.store)
        self.cash_page = CashPage(self.repo, self.store)
        self.admin_page = AdminPage(self.repo, self.store)
        self.help_page = HelpPage(self.repo)

    def render_sidebar_menu(self) -> None:
        with st.sidebar:
            st.markdown("### メニュー")

            pages = [
                AppConfig.PAGE["DASHBOARD"],
                AppConfig.PAGE["APR"],
                AppConfig.PAGE["CASH"],
                AppConfig.PAGE["ADMIN"],
                AppConfig.PAGE["HELP"],
            ]

            labels = {
                AppConfig.PAGE["DASHBOARD"]: "📊 ダッシュボード",
                AppConfig.PAGE["APR"]: "📈 APR",
                AppConfig.PAGE["CASH"]: "💸 入金 / 出金",
                AppConfig.PAGE["ADMIN"]: "⚙️ 管理",
                AppConfig.PAGE["HELP"]: "❓ ヘルプ",
            }

            current_page = st.session_state["page"]
            if current_page not in pages:
                current_page = AppConfig.PAGE["DASHBOARD"]

            selected = st.radio(
                "ページ",
                pages,
                index=pages.index(current_page),
                format_func=lambda x: labels[x],
            )

            st.session_state["page"] = selected

    def run(self) -> None:
        self.setup_page()
        self.setup_auth()
        self.setup_state()
        self.setup_services()
        self.render_sidebar_menu()

        data = self.store.load(force=False)
        page = st.session_state["page"]

        if page == AppConfig.PAGE["DASHBOARD"]:
            self.dashboard_page.render()

        elif page == AppConfig.PAGE["APR"]:
            self.apr_page.render()

        elif page == AppConfig.PAGE["CASH"]:
            self.cash_page.render(
                data["settings_df"],
                data["members_df"],
            )

        elif page == AppConfig.PAGE["ADMIN"]:
            self.admin_page.render(
                data["settings_df"],
                data["members_df"],
                data["line_users_df"],
            )

        elif page == AppConfig.PAGE["HELP"]:
            self.help_page.render()

        else:
            st.warning("ページが見つかりません。")


# END OF FILE
