from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import streamlit as st

from config import AppConfig


@dataclass
class AdminUser:
    name: str
    pin: str
    namespace: str


class AdminAuth:
    @staticmethod
    def _default_users() -> List[AdminUser]:
        return [
            AdminUser(name="管理者A", pin="1111", namespace="A"),
            AdminUser(name="管理者B", pin="2222", namespace="B"),
            AdminUser(name="管理者C", pin="3333", namespace="C"),
            AdminUser(name="管理者D", pin="4444", namespace="D"),
        ]

    @staticmethod
    def load_users() -> List[AdminUser]:
        users_raw = st.secrets.get("admin", {}).get("users")

        if users_raw:
            users: List[AdminUser] = []
            for u in users_raw:
                users.append(
                    AdminUser(
                        name=str(u.get("name", "")).strip(),
                        pin=str(u.get("pin", "")).strip(),
                        namespace=str(u.get("namespace", AppConfig.DEFAULT_NAMESPACE)).strip() or AppConfig.DEFAULT_NAMESPACE,
                    )
                )
            return users

        single_pin = str(st.secrets.get("admin", {}).get("pin", "")).strip()
        if single_pin:
            return [AdminUser(name="管理者A", pin=single_pin, namespace="A")]

        return AdminAuth._default_users()

    @staticmethod
    def init_session() -> None:
        if "admin_ok" not in st.session_state:
            st.session_state["admin_ok"] = False
        if "admin_name" not in st.session_state:
            st.session_state["admin_name"] = ""
        if "admin_namespace" not in st.session_state:
            st.session_state["admin_namespace"] = AppConfig.DEFAULT_NAMESPACE

    @staticmethod
    def current_namespace() -> str:
        return str(st.session_state.get("admin_namespace", AppConfig.DEFAULT_NAMESPACE)).strip() or AppConfig.DEFAULT_NAMESPACE

    @staticmethod
    def current_name() -> str:
        return str(st.session_state.get("admin_name", "")).strip()

    @staticmethod
    def current_label() -> str:
        name = AdminAuth.current_name()
        ns = AdminAuth.current_namespace()
        return f"{name} / {ns}" if name else f"管理者 / {ns}"

    @staticmethod
    def _find_user(name: str, pin: str) -> Optional[AdminUser]:
        for user in AdminAuth.load_users():
            if user.name == str(name).strip() and user.pin == str(pin).strip():
                return user
        return None

    @staticmethod
    def login_form() -> None:
        st.markdown("### 管理者ログイン")

        users = AdminAuth.load_users()
        names = [u.name for u in users]

        with st.form("admin_login_form", clear_on_submit=False):
            picked_name = st.selectbox("管理者", names, index=0 if names else None)
            pin = st.text_input("PIN", type="password")
            submitted = st.form_submit_button("ログイン", use_container_width=True)

        if submitted:
            user = AdminAuth._find_user(picked_name, pin)
            if user is None:
                st.error("管理者名またはPINが違います。")
                st.stop()

            st.session_state["admin_ok"] = True
            st.session_state["admin_name"] = user.name
            st.session_state["admin_namespace"] = user.namespace
            st.rerun()

    @staticmethod
    def require_login() -> None:
        AdminAuth.init_session()

        if st.session_state.get("admin_ok", False):
            return

        AdminAuth.login_form()
        st.stop()

    @staticmethod
    def logout() -> None:
        st.session_state["admin_ok"] = False
        st.session_state["admin_name"] = ""
        st.session_state["admin_namespace"] = AppConfig.DEFAULT_NAMESPACE


# END OF FILE
