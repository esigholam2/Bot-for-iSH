#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# BOTs_color_cli.py – نسخهٔ iSH (Alpine Linux on iOS) – دسامبر ۲۰۲۵
# ویژگی‌ها:
# - رنگ‌بندی ورودی/خروجی با colorama
# - منوی CLI شیک با کادر، میان‌بُرها و نمایش وضعیت کلیدها
# - استریم پاسخ‌ها بدون وابستگی‌های سنگین
# اجرا: python3 BOTs_color_cli.py
# نصب رنگ‌ها (در iSH): pip3 install colorama

import os
import re
import json
import sqlite3
import requests
from datetime import datetime
from pathlib import Path
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# رنگ‌ها
try:
    from colorama import init as colorama_init
    from colorama import Fore, Back, Style
    colorama_init(autoreset=True)
except Exception:
    class _Dummy:
        def __getattr__(self, _): return ""
    Fore = Back = Style = _Dummy()

# ==================== تنظیمات اولیه ====================
APP_NAME = "BOTs.py – iSH – رنگی و تمیز"
VERSION = "2025-12"
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

OPENAI_LOG = LOG_DIR / "openai.jsonl"
GROQ_LOG   = LOG_DIR / "groq.jsonl"
GEMINI_LOG = LOG_DIR / "gemini.jsonl"

USE_SQLITE = os.getenv("USE_SQLITE", "0") == "1"
SQLITE_DB = LOG_DIR / "chat.db"

# کلیدها از متغیر محیطی
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GROQ_KEY   = os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# حذف کاراکترهای خراب
RE_SURROGATE = re.compile(r'[\uD800-\uDFFF]')
def clean(s):
    return RE_SURROGATE.sub("", str(s))

# لاگ ساده
def log_line(path: Path, data: dict):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except:
        pass

# SQLite اختیاری
conn = None
if USE_SQLITE:
    try:
        conn = sqlite3.connect(str(SQLITE_DB))
        conn.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, ts TEXT, engine TEXT, role TEXT, msg TEXT)")
        conn.commit()
    except:
        conn = None

def sql_log(msg, engine="unknown", role="assistant"):
    if conn:
        try:
            conn.execute("INSERT INTO messages(ts,engine,role,msg) VALUES(datetime('now'),?,?,?)",
                        (engine, role, clean(msg)))
            conn.commit()
        except:
            pass

# چاپ استریم با رنگ
def stream_print(text, color=Fore.WHITE):
    print(f"{color}{text}{Style.RESET_ALL}", end="", flush=True)

def hr(char="─", width=52):
    return char * width

def clear_screen():
    try:
        os.system("clear")
    except:
        pass

def key_status(val):
    if val:
        return f"{Fore.GREEN}SET{Style.RESET_ALL}"
    return f"{Fore.RED}NOT SET{Style.RESET_ALL}"

def banner():
    print(f"{Fore.CYAN}{hr('═')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  {APP_NAME}  {Style.DIM}v{VERSION}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{hr('═')}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}کلیدها:{Style.RESET_ALL} OpenAI: {key_status(OPENAI_KEY)}  |  Groq: {key_status(GROQ_KEY)}  |  Gemini: {key_status(GEMINI_KEY)}")
    print(hr())

def menu():
    print(f"{Back.BLACK}{Fore.WHITE} منوی اصلی {Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}1{Style.RESET_ALL}) OpenAI   {Fore.MAGENTA}2{Style.RESET_ALL}) Groq   {Fore.MAGENTA}3{Style.RESET_ALL}) Gemini   {Fore.MAGENTA}0{Style.RESET_ALL}) خروج")
    print(hr())
    print(f"{Style.DIM}میان‌بُرها:  Ctrl+C خروج گفتگو  |  exit / quit / :q پایان{Style.RESET_ALL}")

def prompt_user(label="شما"):
    return input(f"\n{Fore.CYAN}{label}:{Style.RESET_ALL} ")

def print_assistant_header(name="دستیار"):
    print(f"{Fore.YELLOW}{name}:{Style.RESET_ALL} ", end="", flush=True)

def print_info(msg):
    print(f"{Fore.BLUE}ℹ{Style.RESET_ALL} {msg}")

def print_ok(msg):
    print(f"{Fore.GREEN}✓{Style.RESET_ALL} {msg}")

def print_err(msg):
    print(f"{Fore.RED}✗{Style.RESET_ALL} {msg}")

# ==================== OpenAI ====================
def chat_openai():
    if not OPENAI_KEY:
        print_err("OPENAI_API_KEY تنظیم نشده است.")
        return

    models = [
        "gpt-4o-mini", "gpt-4o", "o1-mini", "o1-preview", "gpt-4-turbo"
    ]
    print_info("مدل‌های OpenAI:")
    for i, m in enumerate(models, 1):
        print(f"  {Fore.MAGENTA}{i}{Style.RESET_ALL}) {m}")
    try:
        choice = int(input(f"{Fore.BLUE}شماره مدل (پیش‌فرض 1):{Style.RESET_ALL} ") or "1")
        model = models[choice - 1]
    except:
        model = models[0]

    print_ok(f"مدل انتخاب شد: {model}")
    messages = [{"role": "system", "content": "تو یک دستیار فارسی بسیار هوشمند و دقیق هستی."}]

    while True:
        try:
            q = prompt_user("شما")
            if q.lower().strip() in {"exit", "خروج", "quit", ":q", "bye"}:
                print_info("پایان گفتگو.")
                break

            messages.append({"role": "user", "content": q})
            log_line(OPENAI_LOG, {"t": datetime.utcnow().isoformat(), "role": "user", "msg": q})
            sql_log(q, "openai", "user")

            print_assistant_header("دستیار")
            full = ""

            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
            payload = {"model": model, "messages": messages, "stream": True, "temperature": 0.7}

            try:
                with requests.post(url, headers=headers, json=payload, stream=True, timeout=120, verify=False) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if not line: continue
                        s = line.decode("utf-8").strip()
                        if s.startswith("data: "): s = s[6:]
                        if s == "[DONE]": break
                        try:
                            data = json.loads(s)
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                delta = clean(delta)
                                full += delta
                                stream_print(delta, color=Fore.GREEN)
                        except:
                            continue
            except requests.exceptions.RequestException as e:
                print_err(str(e))
            except Exception as e:
                print_err(f"خطای ناشناخته: {e}")

            print()
            if full.strip():
                messages.append({"role": "assistant", "content": full})
                log_line(OPENAI_LOG, {"t": datetime.utcnow().isoformat(), "role": "assistant", "msg": full})
                sql_log(full, "openai", "assistant")

        except KeyboardInterrupt:
            print_info("خروج با Ctrl+C.")
            break

# ==================== Groq ====================
def chat_groq():
    if not GROQ_KEY:
        print_err("GROQ_API_KEY یا XAI_API_KEY تنظیم نشده است.")
        return

    models = ["llama-3.3-70b-versatile", "llama-3.3-8b-instant", "gemma2-9b-it", "mixtral-8x7b-32768"]
    print_info("مدل‌های Groq:")
    for i, m in enumerate(models, 1):
        print(f"  {Fore.MAGENTA}{i}{Style.RESET_ALL}) {m}")
    try:
        choice = int(input(f"{Fore.BLUE}شماره مدل (پیش‌فرض 1):{Style.RESET_ALL} ") or "1")
        model = models[choice - 1]
    except:
        model = models[0]

    print_ok(f"مدل انتخاب شد: {model}")
    history = [{"role": "system", "content": "تو یک دستیار فارسی فوق سریع هستی."}]

    while True:
        try:
            q = prompt_user("شما")
            if q.lower().strip() in {"exit", "خروج", "quit", ":q"}:
                print_info("پایان گفتگو.")
                break

            history.append({"role": "user", "content": q})
            log_line(GROQ_LOG, {"t": datetime.utcnow().isoformat(), "role": "user", "msg": q})
            sql_log(q, "groq", "user")

            print_assistant_header("دستیار")
            full = ""

            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_KEY}"}
            payload = {"model": model, "messages": history, "stream": True, "temperature": 0.7}

            try:
                with requests.post(url, headers=headers, json=payload, stream=True, timeout=90, verify=False) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if not line: continue
                        s = line.decode().strip()
                        if s.startswith("data: "): s = s[6:]
                        if s == "[DONE]": break
                        try:
                            data = json.loads(s)
                            delta = data["choices"][0]["delta"].get("content", "")
                            if delta:
                                delta = clean(delta)
                                full += delta
                                stream_print(delta, color=Fore.GREEN)
                        except:
                            continue
            except requests.exceptions.RequestException as e:
                print_err(str(e))
            except Exception as e:
                print_err(f"خطا: {e}")

            print()
            if full.strip():
                history.append({"role": "assistant", "content": full})
                log_line(GROQ_LOG, {"t": datetime.utcnow().isoformat(), "role": "assistant", "msg": full})
                sql_log(full, "groq", "assistant")

        except KeyboardInterrupt:
            print_info("خروج با Ctrl+C.")
            break

# ==================== Gemini (به‌روزشده ۲۰۲۵) ====================
def chat_gemini():
    if not GEMINI_KEY:
        print_err("GEMINI_API_KEY تنظیم نشده است.")
        return

    models = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
        "gemini-2.0-flash-thinking",
        "gemini-2.0-pro-exp-1219"
    ]
    print_info("مدل‌های Gemini:")
    for i, m in enumerate(models, 1):
        print(f"  {Fore.MAGENTA}{i}{Style.RESET_ALL}) {m}")
    try:
        choice = int(input(f"{Fore.BLUE}شماره مدل (پیش‌فرض 1):{Style.RESET_ALL} ") or "1")
        model = models[choice - 1]
    except:
        model = models[0]

    print_ok(f"مدل انتخاب شد: {model}")

    # تاریخچه به فرمت Gemini
    history = []
    system = "تو یک دستیار فارسی بسیار هوشمند، دقیق و سریع هستی. همیشه به فارسی پاسخ بده مگر کاربر بخواهد."
    history.append({"role": "user", "parts": [{"text": system}]})
    history.append({"role": "model", "parts": [{"text": "سلام! چطور می‌توانم کمک کنم؟"}]})

    while True:
        try:
            q = prompt_user("شما")
            if q.lower().strip() in {"exit", "خروج", "quit", ":q", "bye"}:
                print_info("پایان گفتگو.")
                break

            history.append({"role": "user", "parts": [{"text": q}]})
            log_line(GEMINI_LOG, {"t": datetime.utcnow().isoformat(), "role": "user", "msg": q})
            sql_log(q, "gemini", "user")

            print_assistant_header("Gemini")
            full = ""

            url = f"https://generativelanguage.googleapis.com/v1/models/{model}:streamGenerateContent"
            params = {"key": GEMINI_KEY, "alt": "sse"}
            payload = {
                "contents": history,
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192},
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            }

            try:
                with requests.post(url, params=params, json=payload, stream=True, timeout=180, verify=False) as r:
                    if r.status_code != 200:
                        print_err(f"خطا {r.status_code}: {r.text[:200]}")
                        break
                    for line in r.iter_lines():
                        if not line: continue
                        text = line.decode("utf-8").strip()
                        if not text.startswith("data: "): continue
                        data_str = text[6:]
                        if data_str == "[DONE]": break
                        try:
                            data = json.loads(data_str)
                            part = data.get("candidates", [{}])[0] \
                                     .get("content", {}) \
                                     .get("parts", [{}])[0] \
                                     .get("text", "")
                            if part:
                                part = clean(part)
                                full += part
                                stream_print(part, color=Fore.GREEN)
                        except:
                            continue
            except requests.exceptions.RequestException as e:
                print_err(str(e))
            except Exception as e:
                print_err(f"خطا: {e}")

            print()
            if full.strip():
                history.append({"role": "model", "parts": [{"text": full}]})
                log_line(GEMINI_LOG, {"t": datetime.utcnow().isoformat(), "role": "assistant", "msg": full})
                sql_log(full, "gemini", "assistant")

        except KeyboardInterrupt:
            print_info("خروج با Ctrl+C.")
            break

# ==================== منوی اصلی ====================
def main():
    clear_screen()
    banner()
    menu()

    while True:
        try:
            choice = input(f"\n{Fore.YELLOW}انتخاب کنید:{Style.RESET_ALL} ").strip()
            if choice == "1":
                clear_screen(); banner(); print_info("OpenAI فعال شد."); chat_openai(); clear_screen(); banner(); menu()
            elif choice == "2":
                clear_screen(); banner(); print_info("Groq فعال شد.");   chat_groq();   clear_screen(); banner(); menu()
            elif choice == "3":
                clear_screen(); banner(); print_info("Gemini فعال شد.");  chat_gemini(); clear_screen(); banner(); menu()
            elif choice in {"0", "exit", "quit"}:
                print_ok("خداحافظ!")
                break
            else:
                print_err("لطفاً 1، 2، 3 یا 0 را وارد کنید.")
        except KeyboardInterrupt:
            print_info("\nخروج.")
            break

    if conn:
        conn.close()

if __name__ == "__main__":
    main()
