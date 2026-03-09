import os

LOGIN_URL = "https://www.ivykids.tw/manage/"
DATA_URL = "https://www.ivykids.tw/manage/make_an_appointment/"

USERNAME = os.environ.get("IVYKIDS_USERNAME", "")
PASSWORD = os.environ.get("IVYKIDS_PASSWORD", "")

# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "")

CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "10"))  # 幾分鐘檢查一次
LAST_DATA_FILE = "last_record.txt"
