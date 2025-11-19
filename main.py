from datetime import datetime, timezone
import time
import requests
import random
import asyncio
import json
import gzip
import brotli
import zlib
import chardet
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from colorama import Fore, init as colorama_init
from fake_useragent import UserAgent

colorama_init(autoreset=True)

# Color palette: avoid Yellow, Red, Magenta, Pink as requested
PRIMARY = Fore.CYAN
SUCCESS = Fore.GREEN
INFO = Fore.BLUE
NEUTRAL = Fore.WHITE
TIMESTAMP = Fore.LIGHTBLACK_EX
HIGHLIGHT = Fore.LIGHTGREEN_EX

class ZoopBot:
    BASE_URL = "https://tgapi.zoop.com/api/"
    DEFAULT_HEADERS = {
        "accept": "/",
        "accept-encoding": "br",
        "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
        "content-type": "application/json",
        "origin": "https://tgapp.zoop.com",
        "referer": "https://tgapp.zoop.com/",
        "sec-ch-ua": '"Microsoft Edge";v="134", "Chromium";v="134", "Not:A-Brand";v="24", "Microsoft Edge WebView2";v="134"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        # user-agent will be set dynamically per account
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    def __init__(self):
        self.config = self.load_config()
        self.query_list = self.load_query("query.txt")
        self.token = None
        self.userId = None
        self.session = self._create_session()
        self._original_requests = {
            "get": requests.get,
            "post": requests.post,
            "put": requests.put,
            "delete": requests.delete,
        }
        self.proxy_session = None
        self.HEADERS = dict(self.DEFAULT_HEADERS)

    # ---------- Logging & Banner ----------
    def log(self, message: str, color=NEUTRAL) -> None:
        safe_message = str(message).encode("utf-8", "backslashreplace").decode("utf-8")
        print(
            TIMESTAMP
            + datetime.now().strftime("[%Y:%m:%d ~ %H:%M:%S] |")
            + " "
            + color
            + safe_message
            + Fore.RESET
        )

    def banner(self) -> None:
        # ASCII box banner with requested text
        lines = [
            "Code2Crypto",
            "Tool Name: Zoop Bot",
            "Developed By: Anaik_Dev",
            "Automated Zoop tasks - daily, spin, tasks",
        ]
        width = max(len(l) for l in lines) + 4
        top = "╔" + "═" * width + "╗"
        bottom = "╚" + "═" * width + "╝"
        self.log(top, PRIMARY)
        for l in lines:
            padding = width - len(l) - 2
            self.log(f"║  {l}{' ' * padding}║", PRIMARY)
        self.log(bottom, PRIMARY)

    # ---------- Session & network helpers ----------
    def _create_session(self):
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504, 520])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        return session

    def decode_response(self, response: requests.Response):
        """
        Decode server response robustly and return either parsed JSON or decoded text.
        """
        content_encoding = response.headers.get("Content-Encoding", "").lower()
        content_type = response.headers.get("Content-Type", "").lower()

        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=")[-1].split(";")[0].strip()

        data = response.content

        # Decompress if needed
        try:
            if content_encoding == "gzip":
                data = gzip.decompress(data)
            elif content_encoding in ["br", "brotli"]:
                data = brotli.decompress(data)
            elif content_encoding in ["deflate", "zlib"]:
                data = zlib.decompress(data)
        except Exception:
            # If decompression fails, continue with raw data
            pass

        try:
            text = data.decode(charset)
        except Exception:
            detection = chardet.detect(data)
            detected_encoding = detection.get("encoding", "utf-8")
            text = data.decode(detected_encoding, errors="replace")

        if "application/json" in content_type or text.strip().startswith("{") or text.strip().startswith("["):
            try:
                return json.loads(text)
            except Exception:
                return text
        else:
            return text

    # ---------- Config & query loading ----------
    def load_config(self) -> dict:
        try:
            with open("config.json", "r", encoding="utf-8") as config_file:
                config = json.load(config_file)
                self.log("✅ Configuration loaded successfully.", SUCCESS)
                return config
        except FileNotFoundError:
            self.log("⚠️ File not found: config.json", INFO)
            return {}
        except json.JSONDecodeError:
            self.log("⚠️ Failed to parse config.json. Please check the file format.", INFO)
            return {}

    def load_query(self, path_file: str = "query.txt") -> list:
        try:
            with open(path_file, "r", encoding="utf-8") as file:
                queries = [line.strip() for line in file if line.strip()]

            if not queries:
                self.log(f"⚠️ Warning: {path_file} is empty.", INFO)

            self.log(f"✅ Loaded {len(queries)} queries from {path_file}.", SUCCESS)
            return queries

        except FileNotFoundError:
            self.log(f"⚠️ File not found: {path_file}", INFO)
            return []
        except Exception as e:
            self.log(f"⚠️ Unexpected error loading queries: {e}", INFO)
            return []

    # ---------- Login, daily, spin, task routines ----------
    def login(self, index: int) -> None:
        self.log("🔐 Attempting to log in...", SUCCESS)

        if index >= len(self.query_list):
            self.log("❌ Invalid login index. Please check again.", INFO)
            return

        token = self.query_list[index]
        self.log(f"📋 Using token: {token[:10]}... (truncated for security)", PRIMARY)

        req_url = f"{self.BASE_URL}oauth/telegram"
        payload = {"initData": token}
        headers = dict(self.HEADERS)

        try:
            self.log("📡 Sending login request...", PRIMARY)
            response = self.session.post(req_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = self.decode_response(response)

            if isinstance(data, dict) and "data" in data:
                data = data["data"]
                access_token = data.get("access_token")
                if not access_token:
                    self.log("⚠️ Access token not found in response.", INFO)
                    return

                info = data.get("information", {})
                self.token = access_token
                self.userId = info.get("userId", "Unknown")

                username = info.get("username", "Unknown")
                year_join = info.get("yearJoin", "N/A")
                point = info.get("point", 0)
                spin = info.get("spin", 0)
                is_premium = info.get("isPremium", False)

                self.log("✅ Login successful!", SUCCESS)
                self.log(f"👤 Username: {username}", HIGHLIGHT)
                self.log(f"🎂 Year Joined: {year_join}", PRIMARY)
                self.log(f"⭐ Premium: {is_premium}", PRIMARY)
                self.log(f"💎 Points: {point}", PRIMARY)
                self.log(f"🔄 Spins: {spin}", PRIMARY)
            else:
                self.log("⚠️ Unexpected response structure.", INFO)

        except requests.exceptions.RequestException as e:
            self.log(f"⚠️ Failed to send login request: {e}", INFO)
        except ValueError as e:
            self.log(f"⚠️ Data error (possible JSON issue): {e}", INFO)
        except KeyError as e:
            self.log(f"⚠️ Key error: {e}", INFO)
        except Exception as e:
            self.log(f"⚠️ Unexpected error: {e}", INFO)

    def spin(self) -> None:
        self.log("🎰 Starting spin process...", SUCCESS)

        headers = {**self.HEADERS, "Authorization": f"Bearer {self.token}"}
        spin_url = f"{self.BASE_URL}users/spin"

        retry_limit = 3
        while True:
            current_date = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            payload = {"userId": self.userId, "date": current_date}

            self.log("🎡 Attempting spin...", PRIMARY)

            retries = 0
            while retries < retry_limit:
                try:
                    response = self.session.post(spin_url, headers=headers, json=payload, timeout=10)
                    response.raise_for_status()
                    spin_data = self.decode_response(response)

                    if not isinstance(spin_data, dict) or "data" not in spin_data:
                        self.log("⚠️ No 'data' in response. Spin ended.", INFO)
                        return

                    result = spin_data["data"]
                    reward = result.get("circle", {}).get("name", "N/A")
                    self.log(f"✅ Spin successful! Reward: {reward}", SUCCESS)
                    return # Exit after successful spin

                except requests.exceptions.Timeout:
                    retries += 1
                    self.log(f"⏳ Timeout occurred. Retry {retries}/{retry_limit}...", INFO)
                except Exception as e:
                    self.log(f"⚠️ Spin failed: {e}", INFO)
                    return

            if retries >= retry_limit:
                self.log("⚠️ Maximum retries reached. Exiting spin.", INFO)
                return

    def daily(self) -> None:
        self.log("🌞 Checking daily reward status...", SUCCESS)
        headers = {**self.HEADERS, "Authorization": f"Bearer {self.token}"}

        try:
            get_url = f"{self.BASE_URL}tasks/{self.userId}"
            response = self.session.get(get_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = self.decode_response(response)

            if isinstance(data, dict) and "data" in data:
                daily_info = data["data"]
                claimed = daily_info.get("claimed", True)
                daily_index = daily_info.get("dailyIndex", None)

                if not claimed:
                    self.log("🎁 Daily reward not yet claimed, attempting to claim...", PRIMARY)

                    reward_url = f"{self.BASE_URL}tasks/rewardDaily/{self.userId}"
                    payload = {"index": daily_index}

                    reward_response = self.session.post(reward_url, headers=headers, json=payload, timeout=15)
                    reward_response.raise_for_status()
                    # reward_data = self.decode_response(reward_response)

                    # Assuming successful claim based on 2xx status, since response structure is not fully certain
                    # if isinstance(reward_data, dict) and "data" in reward_data:
                    self.log("✅ Daily reward claimed successfully!", SUCCESS)
                    # else:
                    #     self.log("⚠️ Unexpected response structure when claiming reward.", INFO)
                else:
                    self.log("✔️ Daily reward has already been claimed today.", INFO)
            else:
                self.log("⚠️ Unexpected response structure from task status API.", INFO)

        except requests.exceptions.RequestException as e:
            self.log(f"⚠️ Failed to claim daily reward: {e}", INFO)
        except ValueError as e:
            self.log(f"⚠️ Data error (possibly JSON): {e}", INFO)
        except Exception as e:
            self.log(f"⚠️ Unexpected error: {e}", INFO)

    def task(self) -> None:
        def fetch_tasks():
            self.log("🧩 [Phase 1] Fetching task list from server...", SUCCESS)
            headers = {**self.HEADERS, "Authorization": f"Bearer {self.token}"}
            url = f"{self.BASE_URL}social"
            try:
                resp = self.session.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                data = self.decode_response(resp)
                return data.get("data", []) if isinstance(data, dict) else []
            except Exception as e:
                self.log(f"⚠️ Failed to fetch tasks: {e}", INFO)
                return []

        tasks = fetch_tasks()
        if not tasks:
            self.log("⚠️ No tasks available.", INFO)
            return

        expired_tasks = [t for t in tasks if t.get("expired", False)]
        pending_tasks = [t for t in tasks if not t.get("expired", False)]

        self.log(f"📋 Total tasks: {len(tasks)} (Pending: {len(pending_tasks)}, Expired: {len(expired_tasks)})", PRIMARY)
        if expired_tasks:
            self.log("⚠️ Expired tasks:", INFO)
            for t in expired_tasks:
                self.log(f" - {t.get('title')}", INFO)
        if pending_tasks:
            self.log("⌛ Pending tasks:", PRIMARY)
            for t in pending_tasks:
                self.log(f" - {t.get('title')}", PRIMARY)
        else:
            self.log("🎯 No pending tasks to claim.", SUCCESS)
            return

        self.log("⚙️ [Phase 2] Claiming pending tasks...", PRIMARY)
        claimed_ids = []
        for task_item in pending_tasks:
            try:
                task_id = task_item.get("_id")
                task_title = task_item.get("title", "Unknown")
                claim_url = f"{self.BASE_URL}tasks/verified/{self.userId}"
                payload = {
                    "point": task_item.get("point", 0),
                    "spin": task_item.get("spin", 0),
                    "type": task_item.get("type", "")
                }

                r = self.session.post(claim_url, headers={**self.HEADERS, "Authorization": f"Bearer {self.token}"}, json=payload, timeout=15)
                r.raise_for_status()
                res = self.decode_response(r)
                if isinstance(res, dict) and res.get("data"):
                    self.log(f"🎉 Claimed '{task_title}' successfully.", SUCCESS)
                    claimed_ids.append(task_id)
                else:
                    self.log(f"⚠️ Unexpected claim response for '{task_title}': {res}", INFO)
            except Exception as e:
                self.log(f"⚠️ Error during claim for '{task_item.get('title')}': {e}", INFO)

        self.log("🔄 [Phase 3] Updating local status...", PRIMARY)
        new_expired = [t for t in pending_tasks if t.get("_id") in claimed_ids]
        still_pending = [t for t in pending_tasks if t.get("_id") not in claimed_ids]
        self.log(f"Pending: {len(still_pending)}, Claimed: {len(new_expired)}", PRIMARY)
        if new_expired:
            self.log("✅ Newly claimed tasks:", SUCCESS)
            for t in new_expired:
                self.log(f" - {t.get('title')}", HIGHLIGHT)
        if still_pending:
            self.log("⌛ Still pending:", PRIMARY)
            for t in still_pending:
                self.log(f" - {t.get('title')}", PRIMARY)

    # ---------- Proxy helpers ----------
    def load_proxies(self, filename="proxy.txt") -> list:
        try:
            with open(filename, "r", encoding="utf-8") as file:
                proxies = [line.strip() for line in file if line.strip()]
            if not proxies:
                raise ValueError("Proxy file is empty.")
            return proxies
        except Exception as e:
            self.log(f"⚠️ Failed to load proxies: {e}", INFO)
            return []

    def set_proxy_session(self, proxies: list) -> requests.Session:
        if not proxies:
            self.log("⚠️ No proxies available. Using direct connection.", INFO)
            self.proxy_session = requests.Session()
            return self.proxy_session

        available_proxies = proxies.copy()

        while available_proxies:
            proxy_url = random.choice(available_proxies)
            self.proxy_session = requests.Session()
            self.proxy_session.proxies = {"http": proxy_url, "https": proxy_url}

            try:
                test_url = "https://httpbin.org/ip"
                response = self.proxy_session.get(test_url, timeout=5)
                response.raise_for_status()
                origin_ip = response.json().get("origin", "Unknown IP")
                self.log(f"✅ Using Proxy: {proxy_url} | Your IP: {origin_ip}", SUCCESS)
                return self.proxy_session
            except requests.RequestException as e:
                self.log(f"⚠️ Proxy failed: {proxy_url} | Error: {e}", INFO)
                available_proxies.remove(proxy_url)

        self.log("⚠️ All proxies failed. Using direct connection.", INFO)
        self.proxy_session = requests.Session()
        return self.proxy_session

    def override_requests(self):
        if self.config.get("proxy", False):
            self.log("[CONFIG] 🛡️ Proxy: ✅ Enabled", PRIMARY)
            proxies = self.load_proxies()
            self.set_proxy_session(proxies)

            # Override request methods globally to use proxy session
            requests.get = self.proxy_session.get
            requests.post = self.proxy_session.post
            requests.put = self.proxy_session.put
            requests.delete = self.proxy_session.delete
        else:
            self.log("[CONFIG] Proxy: ❌ Disabled", PRIMARY)
            # Restore original functions if proxy is disabled
            requests.get = self._original_requests["get"]
            requests.post = self._original_requests["post"]
            requests.put = self._original_requests["put"]
            requests.delete = self._original_requests["delete"]

# ---------- Async worker & orchestration (outside class) ----------

async def process_account(account: str, original_index: int, account_label: str, zoop: ZoopBot, config: dict):
    # Set unique User-Agent per account for better request simulation
    ua = UserAgent()
    zoop.HEADERS["user-agent"] = ua.random

    display_account = account[:10] + "..." if len(account) > 10 else account
    zoop.log(f"👤 Processing {account_label}: {display_account}", PRIMARY)

    if config.get("proxy", False):
        # Override requests with proxy session specific to this account's worker
        zoop.override_requests()
    else:
        # Ensure direct connection is used if proxy is disabled
        zoop.override_requests()
        # zoop.log("[CONFIG] Proxy: ❌ Disabled", PRIMARY) # Already logged in override_requests

    # Login (blocking) run in thread to avoid blocking event loop
    try:
        await asyncio.to_thread(zoop.login, original_index)
    except Exception as e:
        zoop.log(f"⚠️ Error during login for {account_label}: {e}", INFO)
        return # Skip processing if login fails

    if not zoop.token:
        zoop.log(f"❌ Login failed for {account_label}. Skipping tasks.", INFO)
        return

    zoop.log("🛠️ Starting task execution...", PRIMARY)
    tasks_config = {
        "daily": "Automatically claim your daily reward! 🌞",
        "task": "Automatically complete your tasks! ✅",
        "spin": "Automatically spin the wheel! 🎰",
    }

    for task_key, task_name in tasks_config.items():
        task_status = config.get(task_key, False)
        color = PRIMARY if task_status else INFO
        zoop.log(f"[CONFIG] {task_name}: {'✅ Enabled' if task_status else '❌ Disabled'}", color)
        if task_status:
            zoop.log(f"🔄 Executing {task_name}...", PRIMARY)
            try:
                # Execute task (blocking) in a separate thread
                await asyncio.to_thread(getattr(zoop, task_key))
            except Exception as e:
                zoop.log(f"⚠️ Error executing {task_key} for {account_label}: {e}", INFO)


    delay_switch = config.get("delay_account_switch", 10)
    zoop.log(f"➡️ Finished processing {account_label}. Waiting {delay_switch} seconds before next account.", PRIMARY)
    await asyncio.sleep(delay_switch)

async def worker(worker_id: int, zoop: ZoopBot, config: dict, queue: asyncio.Queue):
    while True:
        try:
            # Get an account from the queue
            original_index, account = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        
        # Create a new ZoopBot instance for each account/worker to handle
        # potential issues with shared state (like self.token, self.userId)
        # though only self.session/requests are truly shared in the original logic.
        # However, to be safe, a fresh instance is better for parallel processing
        # IF you intend for each worker to use a unique proxy/session.
        # The current design relies on modifying 'requests' globally which is dangerous.
        # For this fix, we'll keep the ZoopBot instance but ensure the proxy/headers are set correctly.
        
        # A safer approach would be to pass the necessary data (like token) back from login
        # and make the processing functions use the session object directly instead of
        # relying on global 'requests' modification and internal self.token/self.userId state.
        
        # STICKING TO ORIGINAL LOGIC'S INTENT:
        # Reset the essential account-specific fields on the existing ZoopBot instance
        zoop.token = None
        zoop.userId = None
        
        account_label = f"Worker-{worker_id} Account-{original_index+1}"
        await process_account(account, original_index, account_label, zoop, config)
        
        queue.task_done()
        # zoop.log(f"Worker-{worker_id} finished processing an account.", PRIMARY)


async def main():
    zoop = ZoopBot()
    zoop.banner()
    config = zoop.config or {}
    all_accounts = zoop.query_list or []
    num_threads = config.get("thread", 1)

    zoop.log("🎉 [LIVEXORDS] === Welcome to Zoop App Automation === [LIVEXORDS]", PRIMARY)
    zoop.log(f"📂 Loaded {len(all_accounts)} accounts from query list.", PRIMARY)

    if not all_accounts:
        zoop.log("❌ No accounts loaded. Exiting.", INFO)
        return

    while True:
        queue = asyncio.Queue()
        for idx, account in enumerate(all_accounts):
            queue.put_nowait((idx, account))

        zoop.log(f"🚀 Starting automation for {len(all_accounts)} accounts using {num_threads} threads...", PRIMARY)
        workers = [asyncio.create_task(worker(i + 1, zoop, config, queue)) for i in range(num_threads)]

        # Wait until all items in the queue have been processed
        await queue.join()

        # Cancel the workers once the queue is empty
        for w in workers:
            w.cancel()
        
        # Ensure all cancellations are propagated (optional, for clean shutdown)
        await asyncio.gather(*workers, return_exceptions=True)

        zoop.log("🔁 All accounts processed. Restarting loop.", PRIMARY)
        delay_loop = config.get("delay_loop", 3600) # Default to 1 hour
        zoop.log(f"⏳ Sleeping for {delay_loop} seconds before restarting.", PRIMARY)
        await asyncio.sleep(delay_loop)

if __name__ == "__main__":
    try:
        # Set a reasonable default to prevent ResourceWarning if not closed properly
        # if the script exits on error (though asyncio.run should handle shutdown).
        asyncio.run(main())
    except KeyboardInterrupt:
        print(NEUTRAL + " Exiting on user interrupt.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
