from __future__ import annotations

from datetime import timezone, timedelta


class AppConfig:
    APP_TITLE = "APR資産運用管理システム"
    APP_ICON = "🏦"
    PAGE_LAYOUT = "wide"
    JST = timezone(timedelta(hours=9), "JST")

    SPREADSHEET_ID = "YOUR_SPREADSHEET_ID"

    PAGE = {
        "DASHBOARD": "dashboard",
        "APR": "apr",
        "CASH": "cash",
        "ADMIN": "admin",
        "HELP": "help",
    }

    PROJECT = {
        "PERSONAL": "PERSONAL",
    }

    STATUS = {
        "ON": "🟢運用中",
        "OFF": "🔴停止",
    }

    RANK = {
        "MASTER": "Master",
        "ELITE": "Elite",
    }

    FACTOR = {
        "MASTER": 0.67,
        "ELITE": 0.60,
    }

    COMPOUND = {
        "DAILY": "daily",
        "MONTHLY": "monthly",
        "NONE": "none",
    }

    TYPE = {
        "APR": "APR",
        "DEPOSIT": "DEPOSIT",
        "WITHDRAW": "WITHDRAW",
        "LINE": "LINE",
    }

    SOURCE = {
        "APP": "APP",
        "OCR": "OCR",
        "MANUAL": "MANUAL",
    }

    SHEET = {
        "SETTINGS": "Settings",
        "MEMBERS": "Members",
        "LEDGER": "Ledger",
        "LINEUSERS": "LineUsers",
        "APR_SUMMARY": "APR_Summary",
        "SMARTVAULT_HISTORY": "SmartVault_History",
        "OCR_TRANSACTION": "OCR_Transaction",
        "OCR_TRANSACTION_HISTORY": "OCR_Transaction_History",
        "APR_AUTO_QUEUE": "APR_Auto_Queue",
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
            "SV_Total_Liquidity_Left_Mobile",
            "SV_Total_Liquidity_Top_Mobile",
            "SV_Total_Liquidity_Right_Mobile",
            "SV_Total_Liquidity_Bottom_Mobile",
            "SV_Yesterday_Profit_Left_Mobile",
            "SV_Yesterday_Profit_Top_Mobile",
            "SV_Yesterday_Profit_Right_Mobile",
            "SV_Yesterday_Profit_Bottom_Mobile",
            "SV_APR_Left_Mobile",
            "SV_APR_Top_Mobile",
            "SV_APR_Right_Mobile",
            "SV_APR_Bottom_Mobile",
            "TX_Scan_BaseTop_Ratio_Mobile",
            "TX_Scan_Step_Ratio_Mobile",
            "TX_Scan_MaxRows_Mobile",
            "TX_Date_Left_Ratio_Mobile",
            "TX_Date_Right_Ratio_Mobile",
            "TX_Date_Top_Offset_Ratio_Mobile",
            "TX_Date_Bottom_Offset_Ratio_Mobile",
            "TX_Type_Left_Ratio_Mobile",
            "TX_Type_Right_Ratio_Mobile",
            "TX_Type_Top_Offset_Ratio_Mobile",
            "TX_Type_Bottom_Offset_Ratio_Mobile",
            "TX_USD_Left_Ratio_Mobile",
            "TX_USD_Right_Ratio_Mobile",
            "TX_USD_Top_Offset_Ratio_Mobile",
            "TX_USD_Bottom_Offset_Ratio_Mobile",
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
        "LINEUSERS": [
            "Line_User_ID",
            "Line_User",
        ],
        "APR_SUMMARY": [
            "Date_JST",
            "Project_Name",
            "PersonName",
            "Total_APR",
            "APR_Count",
            "Asset_Ratio",
            "LINE_DisplayName",
        ],
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
        "OCR_TRANSACTION": [
            "Datetime_JST",
            "Project_Name",
            "Row_No",
            "Date_Label",
            "Time_Label",
            "Type_Label",
            "Amount_USD",
            "Raw_Text",
            "CreatedAt_JST",
        ],
        "OCR_TRANSACTION_HISTORY": [
            "Unique_Key",
            "Date_Label",
            "Time_Label",
            "Type_Label",
            "Amount_USD",
            "Token_Amount",
            "Token_Symbol",
            "Source_Image",
            "Source_Project",
            "OCR_Raw_Text",
            "CreatedAt_JST",
        ],
        "APR_AUTO_QUEUE": [
            "CreatedAt_JST",
            "Project_Name",
            "PersonName",
            "Line_User_ID",
            "LINE_DisplayName",
            "APR",
            "DailyAPR",
            "Status",
            "Note",
        ],
    }

    OCR_DEFAULTS_PC = {
        "Crop_Left_Ratio_PC": 0.00,
        "Crop_Top_Ratio_PC": 0.00,
        "Crop_Right_Ratio_PC": 1.00,
        "Crop_Bottom_Ratio_PC": 1.00,
    }

    OCR_DEFAULTS_MOBILE = {
        "Crop_Left_Ratio_Mobile": 0.00,
        "Crop_Top_Ratio_Mobile": 0.00,
        "Crop_Right_Ratio_Mobile": 1.00,
        "Crop_Bottom_Ratio_Mobile": 1.00,
    }

    SMARTVAULT_BOXES_MOBILE = {
        "TOTAL_LIQUIDITY": {"left": 0.05, "top": 0.25, "right": 0.40, "bottom": 0.34},
        "YESTERDAY_PROFIT": {"left": 0.40, "top": 0.25, "right": 0.70, "bottom": 0.34},
        "APR": {"left": 0.70, "top": 0.25, "right": 0.95, "bottom": 0.34},
    }

    SESSION_KEYS = {
        "SETTINGS": "settings_df",
        "MEMBERS": "members_df",
        "LEDGER": "ledger_df",
        "LINEUSERS": "line_users_df",
        "APR_SUMMARY": "apr_summary_df",
        "SMARTVAULT_HISTORY": "smartvault_history_df",
        "OCR_TRANSACTION": "ocr_transaction_df",
        "OCR_TRANSACTION_HISTORY": "ocr_transaction_history_df",
        "APR_AUTO_QUEUE": "apr_auto_queue_df",
    }

    DEFAULT_NAMESPACE = "A"
