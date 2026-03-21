from __future__ import annotations

import streamlit as st


class AdminAuth:
    @staticmethod
    def init() -> None:
        if "admin_namespace" not in st.session_state:
            st.session_state["admin_namespace"] = "A"

    @staticmethod
    def current_namespace() -> str:
        return str(st.session_state.get("admin_namespace", "A")).strip() or "A"
