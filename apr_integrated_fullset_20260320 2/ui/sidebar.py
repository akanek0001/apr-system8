from __future__ import annotations

import streamlit as st

from config import AppConfig


class Sidebar:
    def render(self) -> None:
        st.sidebar.title("MENU")

        current = st.session_state.get("page", AppConfig.PAGE["DASHBOARD"])

        options = [
            AppConfig.PAGE["DASHBOARD"],
            AppConfig.PAGE["APR"],
            AppConfig.PAGE["CASH"],
            AppConfig.PAGE["ADMIN"],
            AppConfig.PAGE["HELP"],
        ]

        labels = {
            AppConfig.PAGE["DASHBOARD"]: "Dashboard",
            AppConfig.PAGE["APR"]: "APR",
            AppConfig.PAGE["CASH"]: "Cash",
            AppConfig.PAGE["ADMIN"]: "Admin",
            AppConfig.PAGE["HELP"]: "Help",
        }

        page = st.sidebar.radio(
            "ページ",
            options,
            index=options.index(current) if current in options else 0,
            format_func=lambda x: labels.get(x, x),
        )

        st.session_state["page"] = page
