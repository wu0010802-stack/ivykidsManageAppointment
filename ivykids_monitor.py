import re
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

import config

TZ = ZoneInfo("Asia/Taipei")


def log(msg):
    print(f"[{datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def send_line_message(token, user_id, message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": message}],
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            log("LINE 訊息發送成功")
        else:
            log(f"LINE 訊息失敗：{resp.status_code} {resp.text}")
    except Exception as e:
        log(f"LINE 訊息例外：{e}")


class IvykidsMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        self.seen_ids = self._load_seen_ids()

    def _load_seen_ids(self):
        seen = set()
        try:
            with open(config.LAST_DATA_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        seen.add(line)
            log(f"載入歷史記錄 {len(seen)} 筆")
        except FileNotFoundError:
            log("尚無歷史記錄檔，從零開始")
        return seen

    def _save_seen_ids(self):
        with open(config.LAST_DATA_FILE, "w", encoding="utf-8") as f:
            for rid in self.seen_ids:
                f.write(rid + "\n")

    def login(self):
        log("嘗試登入...")
        try:
            self.session.post(
                config.LOGIN_URL,
                data={"account": config.USERNAME, "password": config.PASSWORD},
                timeout=15,
            )
            if self._is_logged_in():
                log("登入成功")
                return True
            log("登入失敗，請確認帳密")
            return False
        except Exception as e:
            log(f"登入例外：{e}")
            return False

    def _is_logged_in(self):
        try:
            r = self.session.get(config.DATA_URL, timeout=15)
            return "sortable" in r.text
        except Exception:
            return False

    def get_latest_records(self, n=5):
        try:
            r = self.session.get(config.DATA_URL, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            rows = soup.select("#sortable tr")
            records = []
            for row in rows[:n + 1]:
                cols = row.find_all("td")
                if len(cols) < 7:
                    continue
                # 從編輯連結抓真實資料庫 ID（form.php?id=158 → "158"）
                edit_link = row.select_one('a[href*="form.php?id="]')
                if not edit_link:
                    continue
                match = re.search(r"id=(\d+)", edit_link["href"])
                if not match:
                    continue
                db_id = match.group(1)

                record = {
                    "id": db_id,
                    "status": cols[0].get_text(strip=True),
                    "date": cols[1].get_text(strip=True),
                    "name": cols[2].get_text(strip=True),
                    "phone": cols[4].get_text(strip=True),
                    "created_at": cols[6].get_text(strip=True),
                }
                records.append(record)
            log(f"讀取到 {len(records)} 筆預約資料")
            return records
        except Exception as e:
            log(f"讀取資料例外：{e}")
            return []

    def check_and_notify(self, init=False):
        if not self._is_logged_in():
            log("Session 已失效，重新登入...")
            if not self.login():
                return

        records = self.get_latest_records(n=5)
        if not records:
            log("本次未取得任何資料，跳過比對")
            return

        if init:
            # 初次啟動：只記錄現有資料，不發通知，避免舊資料洗版
            for r in records:
                self.seen_ids.add(r["id"])
            self._save_seen_ids()
            log(f"初始化完成，已記錄 {len(records)} 筆現有資料（不發通知）")
            return

        new_items = [r for r in records if r["id"] not in self.seen_ids]

        if new_items:
            log(f"發現 {len(new_items)} 筆新預約！")
            for item in new_items:
                msg = (
                    f"\n【新預約通知】\n"
                    f"狀態：{item['status']}\n"
                    f"預約時間：{item['date']}\n"
                    f"姓名：{item['name']}\n"
                    f"電話：{item['phone']}\n"
                    f"建立時間：{item['created_at']}"
                )
                send_line_message(config.LINE_CHANNEL_ACCESS_TOKEN, config.LINE_USER_ID, msg)
                self.seen_ids.add(item["id"])
            self._save_seen_ids()
        else:
            log("無新預約")

    def run(self):
        log("=== ivykids 預約監控啟動 ===")
        log(f"檢查間隔：{config.CHECK_INTERVAL} 分鐘")

        if not self.login():
            log("初始登入失敗，請確認設定後重試")
            return

        # 第一次執行：若無歷史記錄則初始化（避免把所有舊資料都當新預約通知）
        if not self.seen_ids:
            self.check_and_notify(init=True)

        while True:
            try:
                self.check_and_notify()
            except Exception as e:
                log(f"check_and_notify 發生未預期例外：{e}")

            log(f"等待 {config.CHECK_INTERVAL} 分鐘後再次檢查...")
            time.sleep(config.CHECK_INTERVAL * 60)


if __name__ == "__main__":
    monitor = IvykidsMonitor()
    try:
        monitor.run()
    except KeyboardInterrupt:
        log("使用者中斷，程式結束")
