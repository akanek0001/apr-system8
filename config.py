from datetime import timezone, timedelta


class AppConfig:
    APP_TITLE = "APR資産運用管理システム"
    APP_ICON = "🏦"
    JST = timezone(timedelta(hours=9))

    SPREADSHEET_ID = "YOUR_SPREADSHEET_ID"

    PAGE = {
        "DASHBOARD": "dashboard",
        "APR": "apr",
        "CASH": "cash",
        "ADMIN": "admin",
        "HELP": "help",
    }

    RANK = {
        "MASTER": "Master",
        "ELITE": "Elite",
    }

    FACTOR = {
        "MASTER": 0.67,
        "ELITE": 0.60,
    }

    STATUS = {
        "ON": "🟢運用中",
        "OFF": "🔴停止",
    }

    SHEET = {
        "SETTINGS": "Settings",
        "MEMBERS": "Members",
        "LEDGER": "Ledger",
        "LINEUSERS": "LineUsers",
    }

    HEADERS = {
        "SETTINGS": [
            "Project_Name",
            "Net_Factor",
            "IsCompound",
            "Compound_Timing",
            "Active",
            "UpdatedAt_JST",
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
        "YESTERDAY_PROFIT": {"left": 0.41, "top": 0.25, "right": 0.69, "bottom": 0.34},
        "APR": {"left": 0.70, "top": 0.25, "right": 0.93, "bottom": 0.34},
    }
