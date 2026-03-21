from datetime import timezone, timedelta


class AppConfig:
    APP_TITLE = "APR資産運用管理システム"
    APP_ICON = "🏦"
    PAGE_LAYOUT = "wide"
    JST = timezone(timedelta(hours=9), "JST")

    STATUS = {"ON": "🟢運用中", "OFF": "🔴停止"}
    RANK = {"MASTER": "Master", "ELITE": "Elite"}
    FACTOR = {"MASTER": 0.67, "ELITE": 0.60}
    RANK_LABEL = "👑Master=67% / 🥈Elite=60%"

    PROJECT = {"PERSONAL": "PERSONAL"}
    COMPOUND = {"DAILY": "daily", "MONTHLY": "monthly", "NONE": "none"}
    COMPOUND_LABEL = {"daily": "日次複利", "monthly": "月次複利", "none": "単利"}

    TYPE = {"APR": "APR", "LINE": "LINE", "DEPOSIT": "Deposit", "WITHDRAW": "Withdraw"}
    SOURCE = {"APP": "app"}

    SHEET = {
        "SETTINGS": "Settings",
        "MEMBERS": "Members",
        "LEDGER": "Ledger",
        "LINEUSERS": "LineUsers",
        "APR_SUMMARY": "APR_Summary",
        "SMARTVAULT_HISTORY": "SmartVault_History",
    }

    HEADERS = {
        "SETTINGS": [
            "Project_Name",
            "Net_Factor",
            "IsCompound",
            "Compound_Timing",
            "Crop_Left_Ratio_PC",
            "Crop_Top_Ratio_PC",
            "Crop_Right_Ratio_PC",
            "Crop_Bottom_Ratio_PC",
            "Crop_Left_Ratio_Mobile",
            "Crop_Top_Ratio_Mobile",
            "Crop_Right_Ratio_Mobile",
            "Crop_Bottom_Ratio_Mobile",
            "UpdatedAt_JST",
            "Active",
        ],
        "MEMBERS": [
            "Project_Name",
            "PersonName",
            "Principal",
            "Line_User_ID",
            "LINE_DisplayName",
            "Rank",
            "IsActive",
            "CreatedAt_JST",
            "UpdatedAt_JST",
        ],
        "LEDGER": [
            "Datetime_JST",
            "Project_Name",
            "PersonName",
            "Type",
            "Amount",
            "Note",
            "Evidence_URL",
            "Line_User_ID",
            "LINE_DisplayName",
            "Source",
        ],
        "LINEUSERS": ["Date", "Time", "Type", "Line_User_ID", "Line_User"],
        "APR_SUMMARY": ["Date_JST", "PersonName", "Total_APR", "APR_Count", "Asset_Ratio", "LINE_DisplayName"],
        "SMARTVAULT_HISTORY": [
            "Datetime_JST",
            "Project_Name",
            "Liquidity",
            "Yesterday_Profit",
            "APR",
            "Source_Mode",
            "OCR_Liquidity",
            "OCR_Yesterday_Profit",
            "OCR_APR",
            "Evidence_URL",
            "Admin_Name",
            "Admin_Namespace",
            "Note",
        ],
    }

    PAGE = {
        "DASHBOARD": "📊 ダッシュボード",
        "APR": "📈 APR",
        "CASH": "💸 入金/出金",
        "ADMIN": "⚙️ 管理",
        "HELP": "❓ ヘルプ",
    }

    SESSION_KEYS = {
        "SETTINGS": "settings_df",
        "MEMBERS": "members_df",
        "LEDGER": "ledger_df",
        "LINEUSERS": "line_users_df",
        "APR_SUMMARY": "apr_summary_df",
    }

    APR_LINE_NOTE_KEYWORD = "APR:"

    OCR_DEFAULTS_PC = {
        "Crop_Left_Ratio_PC": 0.70,
        "Crop_Top_Ratio_PC": 0.20,
        "Crop_Right_Ratio_PC": 0.90,
        "Crop_Bottom_Ratio_PC": 0.285,
    }

    OCR_DEFAULTS_MOBILE = {
        "Crop_Left_Ratio_Mobile": 0.68,
        "Crop_Top_Ratio_Mobile": 0.23,
        "Crop_Right_Ratio_Mobile": 0.92,
        "Crop_Bottom_Ratio_Mobile": 0.355,
    }

    SMARTVAULT_BOXES_MOBILE = {
        "TOTAL_LIQUIDITY": {"left": 0.05, "top": 0.25, "right": 0.40, "bottom": 0.34},
        "YESTERDAY_PROFIT": {"left": 0.41, "top": 0.25, "right": 0.69, "bottom": 0.34},
        "APR": {"left": 0.70, "top": 0.25, "right": 0.93, "bottom": 0.34},
    }
