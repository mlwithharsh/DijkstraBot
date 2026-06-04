import os
import pandas as pd
from datetime import datetime
from typing import List
from dijkstrabot.models import EnrichedProfile
from dijkstrabot.utils.logger import logger

EXPORT_COLUMNS = [
    "username",
    "profile_url",
    "follower_count",
    "following_count",
    "media_count",
    "engagement_rate",
    "est_avg_reach",
    "location",
    "category",
    "primary_hashtags",
    "gender",
    "bio_keywords_matched",
    "profile_pic_url",
    "external_url",
    "is_verified",
    "source_api",
    "dijkstra_score",
    "last_scraped_at",
]


def profiles_to_dataframe(profiles: List[EnrichedProfile]) -> pd.DataFrame:
    rows = []
    for profile in profiles:
        row = profile.model_dump()
        for key, value in list(row.items()):
            if isinstance(value, list):
                row[key] = ", ".join(value)
            elif isinstance(value, datetime):
                row[key] = value.isoformat()
        rows.append({column: row.get(column) for column in EXPORT_COLUMNS})
    return pd.DataFrame(rows, columns=EXPORT_COLUMNS)


class SheetsExporter:
    COLUMNS = EXPORT_COLUMNS

    def __init__(self, service_account_json: str, folder_id: str):
        self.service_account_json = service_account_json
        self.folder_id = folder_id

    async def export(self, profiles: List[EnrichedProfile], stats: dict):
        if not os.path.exists(self.service_account_json):
            logger.warning("sheets_export_skipped", reason="service_account_json_missing")
            return
            
        import gspread
        from google.oauth2.service_account import Credentials
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(self.service_account_json, scopes=scopes)
            client = gspread.authorize(creds)
            sheet_name = f"DijkstraBot Export — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            spreadsheet = client.create(sheet_name, folder_id=self.folder_id)
            worksheet = spreadsheet.get_worksheet(0)
            worksheet.update_title("Profiles")
            df = profiles_to_dataframe(profiles)
            data = [list(df.columns)] + df.astype(str).values.tolist()
            for i in range(0, len(data), 1000):
                worksheet.append_rows(data[i:i+1000])
            stats_ws = spreadsheet.add_worksheet(title="Run Stats", rows=10, cols=2)
            stats_ws.update("A1", [[k, str(v)] for k, v in stats.items()])
            logger.info("sheets_export_completed", url=spreadsheet.url)
        except Exception as e:
            logger.error("sheets_export_failed", error=str(e))

class CSVExporter:
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def export(self, profiles: List[EnrichedProfile]):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dijkstrabot_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        df = profiles_to_dataframe(profiles)
        df.to_csv(filepath, index=False, encoding="utf-8")
        logger.info("csv_export_completed", path=filepath, rows=len(df))
        return filepath

class XLSXExporter:
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir): os.makedirs(output_dir)

    def export(self, profiles: List[EnrichedProfile]):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dijkstrabot_{timestamp}.xlsx"
        filepath = os.path.join(self.output_dir, filename)
        df = profiles_to_dataframe(profiles)
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Profiles")
        logger.info("xlsx_export_completed", path=filepath)
        return filepath
