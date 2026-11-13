"""Link Audit — вежливый краулер внешних ссылок WordPress-сайта.

Один файл: краулер, Streamlit-интерфейс и bootstrap для запуска двойным
кликом. Запуск: ``python link_audit.py`` или ``Запустить_аудит.bat``.
"""

from __future__ import annotations

# Bootstrap: обязан быть ДО импорта streamlit.
import os, subprocess, sys, threading, time, webbrowser
from pathlib import Path

APP_PORT = int(os.environ.get("LINK_AUDIT_PORT", "8501"))
APP_URL = f"http://localhost:{APP_PORT}"
IS_FROZEN = bool(getattr(sys, "frozen", False))
# В EXE данные должны лежать рядом с самим файлом, а не во временной папке
# PyInstaller (_MEIPASS).
APP_BASE_DIR = (
    Path(sys.executable).resolve().parent
    if IS_FROZEN
    else Path(__file__).resolve().parent
)
BUNDLED_APP = Path(getattr(sys, "_MEIPASS", APP_BASE_DIR)) / "link_audit.py"
DESKTOP_MODE = (
    (IS_FROZEN and os.environ.get("LINK_AUDIT_BROWSER") != "1")
    or os.environ.get("LINK_AUDIT_DESKTOP") == "1"
)
SERVER_ONLY = (
    "--server-only" in sys.argv
    or os.environ.get("LINK_AUDIT_SERVER_ONLY") == "1"
)


def _say(message: str) -> None:
    """Печать без падения в windowed-сборке, где stdout может быть None."""
    if sys.stdout is None:
        return
    try:
        print(message, flush=True)
    except Exception:
        pass


def _ensure_std_streams() -> None:
    """В windowed EXE направить stdout/stderr в desktop.log."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        stream = open(APP_BASE_DIR / "desktop.log", "a", encoding="utf-8", buffering=1)
    except OSError:
        return
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def _running_in_streamlit() -> bool:
    """True, если код уже исполняется внутри Streamlit-рантайма."""
    try:
        from streamlit.runtime import exists

        return exists()
    except ImportError:
        return False


def _ensure_deps() -> None:
    """Проверить и при необходимости доустановить зависимости."""
    import importlib

    required = {
        "requests": "requests", "bs4": "beautifulsoup4", "lxml": "lxml",
        "pandas": "pandas", "openpyxl": "openpyxl", "streamlit": "streamlit",
        "rich": "rich", "tqdm": "tqdm",
    }
    if DESKTOP_MODE and not IS_FROZEN:
        required["webview"] = "pywebview"
    missing = []
    for mod, pkg in required.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Устанавливаю недостающие пакеты: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        except (subprocess.CalledProcessError, OSError) as exc:
            print(f"Не удалось установить зависимости: {exc}")
            print("Проверьте подключение к интернету и запустите файл снова.")
            raise SystemExit(1) from exc


def _port_is_busy(port: int = APP_PORT) -> bool:
    """Проверить, слушает ли кто-то localhost:port."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _launch_streamlit(server_only: bool = False) -> None:
    """Запустить Streamlit. В desktop-режиме это делает дочерний процесс."""
    os.chdir(APP_BASE_DIR)

    def open_browser() -> None:
        # Ждём, пока Streamlit реально начнёт слушать порт, иначе первый
        # запуск EXE может открыть пустую страницу.
        for _ in range(120):
            if _port_is_busy():
                break
            time.sleep(0.5)
        time.sleep(1.0)
        webbrowser.open(APP_URL)

    if not server_only and os.environ.get("LINK_AUDIT_NO_BROWSER") != "1":
        threading.Thread(target=open_browser, daemon=True).start()
    theme_env = {
        "STREAMLIT_THEME_BASE": "dark",
        "STREAMLIT_THEME_PRIMARY_COLOR": "#22d3ee",
        "STREAMLIT_THEME_BACKGROUND_COLOR": "#0b1220",
        "STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR": "#111827",
        "STREAMLIT_THEME_TEXT_COLOR": "#e5e7eb",
    }
    cli_args = [
        "streamlit", "run",
        str(BUNDLED_APP if IS_FROZEN else Path(__file__).resolve()),
        "--server.headless=true", "--browser.gatherUsageStats=false",
        f"--server.port={APP_PORT}", "--global.developmentMode=false",
        # Тёмная тема задаётся принудительно, чтобы интерфейс выглядел
        # одинаково независимо от системной темы Windows.
        "--theme.base=dark",
        "--theme.primaryColor=#22d3ee",
        "--theme.backgroundColor=#0b1220",
        "--theme.secondaryBackgroundColor=#111827",
        "--theme.textColor=#e5e7eb",
    ]

    if IS_FROZEN:
        # В одном файле EXE нельзя сделать `python -m streamlit`: запускаем
        # CLI внутри уже распакованного приложения.
        if not BUNDLED_APP.exists():
            _say(f"В сборке не найден файл приложения: {BUNDLED_APP}")
            raise SystemExit(1)
        os.environ.update(theme_env)
        sys.argv = cli_args
        from streamlit.web import cli as stcli

        stcli.main()
        return

    env = os.environ.copy()
    env.update(theme_env)
    subprocess.run(
        [sys.executable, "-m", "streamlit", *cli_args[1:]],
        check=False,
        env=env,
    )


_LOADING_HTML = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<style>
  html,body{height:100%;margin:0;background:#0b1220;color:#e5e7eb;
    font-family:Segoe UI,Arial,sans-serif;overflow:hidden}
  .wrap{height:100%;display:flex;align-items:center;justify-content:center}
  .card{width:420px;padding:34px 38px;border:1px solid #1e3a4a;border-radius:20px;
    background:linear-gradient(145deg,#111827,#0d1a2a);box-shadow:0 24px 70px #0008}
  .logo{font-size:38px}.title{font-size:30px;font-weight:700;margin:8px 0 4px}
  .sub{color:#94a3b8;font-size:14px;line-height:1.5}
  .bar{height:4px;background:#1e293b;border-radius:9px;overflow:hidden;margin-top:24px}
  .bar i{display:block;width:42%;height:100%;background:#22d3ee;border-radius:9px;
    animation:slide 1.15s ease-in-out infinite alternate}
  @keyframes slide{from{transform:translateX(-100%)}to{transform:translateX(240%)}}
</style></head>
<body><div class="wrap"><div class="card">
  <div class="logo">🔍</div><div class="title">Link Audit</div>
  <div class="sub">Запускаю локальный сервер и готовлю интерфейс…<br>
  Обычно это занимает 5–15 секунд.</div>
  <div class="bar"><i></i></div>
</div></div></body></html>"""

_ERROR_HTML = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<style>
  html,body{height:100%;margin:0;background:#0b1220;color:#e5e7eb;
    font-family:Segoe UI,Arial,sans-serif}
  .wrap{height:100%;display:flex;align-items:center;justify-content:center}
  .card{width:520px;padding:32px 36px;border:1px solid #7f1d1d;border-radius:18px;
    background:#111827;line-height:1.55}
  h1{font-size:22px;margin:0 0 12px;color:#fca5a5} code{color:#22d3ee}
</style></head><body><div class="wrap"><div class="card">
  <h1>Не удалось запустить интерфейс</h1>
  <p>Посмотрите <code>desktop.log</code> рядом с EXE. Также можно запустить
  с переменной <code>LINK_AUDIT_BROWSER=1</code> и открыть
  <code>http://localhost:8501</code> в браузере.</p>
</div></div></body></html>"""


def _stop_process(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
            return
        except Exception:
            pass
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _show_desktop_error(message: str) -> None:
    _say(message)
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "Link Audit", 0x10)
    except Exception:
        pass


def _run_desktop(existing: bool = False) -> None:
    """Открыть Streamlit в нативном окне WebView2, без браузера."""
    try:
        import webview
    except Exception as exc:
        _show_desktop_error(
            "Не удалось загрузить компонент окна pywebview.\n"
            f"{exc}\n\nЗапустите с LINK_AUDIT_BROWSER=1, чтобы открыть в браузере."
        )
        return

    proc = None
    log_handle = None
    try:
        if not existing:
            cmd = (
                [sys.executable, "--server-only"]
                if IS_FROZEN
                else [sys.executable, str(Path(__file__).resolve()), "--server-only"]
            )
            env = os.environ.copy()
            env["LINK_AUDIT_SERVER_ONLY"] = "1"
            env["LINK_AUDIT_NO_BROWSER"] = "1"
            env["LINK_AUDIT_PORT"] = str(APP_PORT)
            log_handle = open(APP_BASE_DIR / "desktop.log", "ab", buffering=0)
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
            proc = subprocess.Popen(
                cmd, cwd=APP_BASE_DIR, env=env,
                stdout=log_handle, stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )

        window = webview.create_window(
            "Link Audit",
            url=APP_URL if existing else None,
            html=None if existing else _LOADING_HTML,
            width=1500, height=950, min_size=(1000, 650),
            background_color="#0b1220", text_select=True,
        )

        if not existing:
            def wait_and_load() -> None:
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    if _port_is_busy():
                        time.sleep(1.0)
                        try:
                            window.load_url(APP_URL)
                        except Exception:
                            pass
                        return
                    if proc is not None and proc.poll() is not None:
                        try:
                            window.load_html(_ERROR_HTML)
                        except Exception:
                            pass
                        return
                    time.sleep(0.4)
                try:
                    window.load_html(_ERROR_HTML)
                except Exception:
                    pass

            threading.Thread(target=wait_and_load, daemon=True).start()

        webview.start()
    except Exception as exc:
        _show_desktop_error(f"Не удалось открыть окно Link Audit:\n{exc}")
    finally:
        _stop_process(proc)
        if log_handle is not None:
            try:
                log_handle.close()
            except Exception:
                pass


if __name__ == "__main__" and not _running_in_streamlit():
    if IS_FROZEN:
        _ensure_std_streams()

    if SERVER_ONLY:
        _launch_streamlit(server_only=True)
        sys.exit(0)

    # Повторный клик при работающем Streamlit не должен падать из-за порта.
    if _port_is_busy():
        if DESKTOP_MODE:
            _say(f"Интерфейс уже запущен: {APP_URL}")
            _run_desktop(existing=True)
        else:
            _say(f"Интерфейс уже запущен: {APP_URL}")
            _say("Открываю браузер. Это окно можно закрыть.")
            webbrowser.open(APP_URL)
        sys.exit(0)

    if not IS_FROZEN:
        _ensure_deps()

    if DESKTOP_MODE:
        _say("Запускаю окно Link Audit…")
        _run_desktop(existing=False)
    else:
        _say(f"Запускаю интерфейс: {APP_URL}")
        _say("Закройте это окно, чтобы остановить приложение.")
        _launch_streamlit(server_only=False)
    sys.exit(0)

# ---------------------------------------------------------------------------
# Обычные импорты — после bootstrap.
# ---------------------------------------------------------------------------
import csv, gzip, io, json, logging, re, warnings
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from http import HTTPStatus
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------
START_URL = "https://example.com"
DELAY = 1.5
TIMEOUT = 30
RETRIES = 3
USER_AGENT = "Mozilla/5.0 (compatible; LinkAuditBot/1.0)"
RESPECT_ROBOTS = True
SITEMAP_CANDIDATES = [
    "/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml",
    "/wp-sitemap.xml", "/sitemap.xml.gz", "/sitemap_index.xml.gz",
]
MAX_URL_LEN = 2000
MAX_PAGE_BYTES = 5 * 1024 * 1024
STATE_FILE = str(APP_BASE_DIR / "crawl_state.json")
CSV_FILE = str(APP_BASE_DIR / "external_links.csv")
LOG_FILE = str(APP_BASE_DIR / "crawl.log")
LINK_STATUS_FILE = str(APP_BASE_DIR / "link_status.json")

MAX_ANCHOR_LEN = 300
MAX_SITEMAPS = 200
MAX_FALLBACK_PAGES = 5000
MICRO_BATCH = 10
ERROR_STREAK_LIMIT = 20
LINK_CHECK_BATCH = 20
LINK_TIMEOUT = 20
LINK_DEFAULT_DELAY = 0.8
LINK_CHECK_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
LINK_STATUS_FIELDS = ("status_code", "status_label", "final_url", "error",
                      "checked_at", "ssl_verified")
EXCLUDED_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "svg", "webp", "pdf", "zip",
    "doc", "docx", "xls", "xlsx", "mp4", "mp3",
}
ROW_FIELDS = ("page_url", "page_title", "anchor", "href", "domain", "rel", "target", "context")
EXCEL_HEADERS = [
    "Страница (URL)", "Заголовок страницы", "Текст анкора", "Внешний URL",
    "Домен", "Статус", "rel", "target", "Контекст", "Финальный URL",
    "Ошибка проверки", "Проверено",
]
_LINK_COL_WIDTHS = [42, 34, 30, 52, 24, 20, 20, 10, 64, 52, 34, 22]
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.7",
}

# ---------------------------------------------------------------------------
# Логирование и общие утилиты
# ---------------------------------------------------------------------------
_LOG = logging.getLogger("link_audit")


def _setup_logging() -> None:
    if _LOG.handlers:
        return
    _LOG.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S")
    try:
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(formatter)
        _LOG.addHandler(handler)
    except OSError:
        pass
    stream = logging.StreamHandler(sys.stderr)
    stream.setFormatter(formatter)
    _LOG.addHandler(stream)


def _close_logging() -> None:
    # На Windows нельзя удалить crawl.log, пока его держит открытый handler.
    for handler in list(_LOG.handlers):
        _LOG.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass


_setup_logging()


def _tail(path: str, lines: int = 20) -> str:
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - 32768))
            data = handle.read()
    except OSError:
        return ""
    return "\n".join(data.decode("utf-8", errors="replace").splitlines()[-lines:])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _now_display() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def _squash(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    return session


def _origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _host_key(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _normalize_page_url(url: str) -> str:
    parsed = urlparse(str(url).strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return ""
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(),
                       parsed.path or "/", parsed.params, parsed.query, ""))


def _is_html_page(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    return Path(parsed.path).suffix.lower().lstrip(".") not in EXCLUDED_EXTENSIONS


def _dedupe(items: Iterable[str]) -> list[str]:
    result, seen = [], set()
    for item in items:
        key = _normalize_page_url(item)
        if key and key not in seen:
            seen.add(key)
            result.append(item.strip())
    return result


def _is_nofollow(rel_value: str) -> bool:
    return "nofollow" in rel_value.lower().replace(",", " ").split()


def _is_blank_anchor(anchor: str) -> bool:
    return not anchor.strip() or anchor.strip() == "[без текста]"


def _format_int(value: int | float) -> str:
    return f"{int(value):,}".replace(",", " ")


def _format_duration(seconds: float | None) -> str:
    if seconds is None or seconds < 0 or seconds == float("inf"):
        return "—"
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours} ч {minutes:02d} мин"
    return f"{minutes} мин {secs:02d} сек" if minutes else f"{secs} сек"


def _is_server_error(status: int | None) -> bool:
    """429/503, любой 5xx и сетевая ошибка считаются проблемой сайта."""
    return status is None or status in (429, 503) or status >= 500


class AdaptiveThrottle:
    """
    AIMD-троттлинг: Additive Increase / Multiplicative Decrease.
    Пока сайт здоров и быстр — плавно ускоряемся (уменьшаем DELAY).
    При ошибках/замедлении — резко тормозим (увеличиваем DELAY).

    Регулятор намеренно консервативен: ошибка стоит одного удвоения после
    двух подряд проблем, а ускорение — всего 10% после пяти быстрых ответов.
    """

    def __init__(self, initial_delay: float = 1.5, min_delay: float = 0.3,
                 max_delay: float = 10.0, window: int = 10) -> None:
        if min_delay <= 0 or max_delay <= min_delay:
            raise ValueError("min_delay должен быть больше 0 и меньше max_delay")
        self.min_delay = float(min_delay)
        self.max_delay = float(max_delay)
        self.window = max(3, int(window))
        self.delay = min(self.max_delay, max(self.min_delay, float(initial_delay)))
        self.history: list[tuple[float, int | None]] = []
        self.consecutive_ok = 0
        self.consecutive_err = 0

    @property
    def avg_response(self) -> float | None:
        """Среднее время ответа по окну history; None, если истории нет."""
        if not self.history:
            return None
        return sum(elapsed for elapsed, _ in self.history) / len(self.history)

    def record(self, elapsed: float, status: int | None) -> None:
        """Учесть один ответ и обновить DELAY по правилам AIMD."""
        elapsed = max(0.0, float(elapsed))
        self.history.append((elapsed, status))
        if len(self.history) > self.window:
            del self.history[:-self.window]
        avg = self.avg_response

        if _is_server_error(status):
            self.consecutive_err += 1
            self.consecutive_ok = 0
            # Две ошибки подряд — резкое удвоение паузы (multiplicative decrease).
            if self.consecutive_err >= 2:
                self.delay = min(self.delay * 2.0, self.max_delay)
                self.consecutive_err = 0
            return

        if status in (200, 301, 302, 304):
            self.consecutive_err = 0
            self.consecutive_ok += 1
            # Пять быстрых ответов подряд — осторожное ускорение на 10%.
            if (self.consecutive_ok >= 5 and avg is not None
                    and avg < 0.8 and self.delay > self.min_delay):
                self.delay = max(self.min_delay, self.delay * 0.9)
                self.consecutive_ok = 0
            # Сайт стал медленным — сразу притормаживаем.
            if avg is not None and avg > 3.0:
                self.delay = min(self.delay * 1.5, self.max_delay)
            return
        # Нейтральный статус (например, 404) не ускоряет и не тормозит,
        # но разрывает серии «быстрых успехов» и «подряд ошибок».
        self.consecutive_ok = 0
        self.consecutive_err = 0

    def emergency_brake(self) -> None:
        """Мгновенно уйти на максимальную паузу."""
        self.delay = self.max_delay
        self.consecutive_ok = 0
        self.consecutive_err = 0

    def snapshot(self) -> dict:
        """Сериализуемое состояние для crawl_state.json."""
        return {
            "delay": round(self.delay, 4),
            "avg_response": None if self.avg_response is None else round(self.avg_response, 4),
            "history": [[round(elapsed, 4), status] for elapsed, status in self.history],
        }

    def restore(self, snapshot: dict) -> None:
        """Восстановить DELAY и историю из state-файла."""
        if not isinstance(snapshot, dict):
            return
        try:
            self.delay = min(self.max_delay, max(self.min_delay,
                                                  float(snapshot.get("delay", self.delay))))
        except (TypeError, ValueError):
            pass
        history: list[tuple[float, int | None]] = []
        for item in snapshot.get("history", []) or []:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            try:
                elapsed = max(0.0, float(item[0]))
                status = None if item[1] is None else int(item[1])
            except (TypeError, ValueError):
                continue
            history.append((elapsed, status))
        self.history = history[-self.window:]
        self.consecutive_ok = 0
        self.consecutive_err = 0


# ---------------------------------------------------------------------------
# robots.txt
# ---------------------------------------------------------------------------
_ROBOTS_CACHE: dict[str, RobotFileParser | None] = {}


def _robots_for(start_url: str, session: requests.Session) -> RobotFileParser | None:
    root = _origin(start_url)
    if root in _ROBOTS_CACHE:
        return _ROBOTS_CACHE[root]
    parser, robots_url = None, urljoin(root, "/robots.txt")
    try:
        response = session.get(robots_url, timeout=TIMEOUT, allow_redirects=True)
        if response.status_code == 200:
            parser = RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.text.splitlines())
            _LOG.info("robots.txt загружен: %s", robots_url)
        else:
            _LOG.info("robots.txt недоступен (HTTP %s), ограничения не применяются",
                      response.status_code)
    except requests.RequestException as exc:
        _LOG.warning("Не удалось прочитать robots.txt: %s", exc)
    _ROBOTS_CACHE[root] = parser
    return parser


def _robots_allowed(url: str, session: requests.Session, start_url: str) -> bool:
    if not RESPECT_ROBOTS:
        return True
    parser = _robots_for(start_url, session)
    if parser is None:
        return True
    try:
        return parser.can_fetch(USER_AGENT, url)
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Sitemap
# ---------------------------------------------------------------------------
def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _parse_sitemap(content: bytes) -> tuple[str, list[str]] | None:
    # Некоторые плагины отдают .xml.gz без Content-Encoding: gzip.
    if content[:2] == b"\x1f\x8b":
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(content)) as gz:
                content = gz.read(MAX_PAGE_BYTES + 1)
        except (OSError, EOFError):
            return None
        if len(content) > MAX_PAGE_BYTES:
            return None
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return None
    kind = _local_name(root.tag)
    if kind not in ("sitemapindex", "urlset"):
        return None
    locs = [element.text.strip() for element in root.iter()
            if _local_name(element.tag) == "loc" and element.text and element.text.strip()]
    return kind, locs


def _fetch_sitemap(session: requests.Session, url: str) -> tuple[str, list[str]] | None:
    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as exc:
        _LOG.warning("Ошибка загрузки sitemap %s: %s", url, exc)
        return None
    if response.status_code != 200:
        _LOG.info("Sitemap %s вернул HTTP %s", url, response.status_code)
        return None
    length = response.headers.get("Content-Length")
    if (length and length.isdigit() and int(length) > MAX_PAGE_BYTES) or \
            len(response.content) > MAX_PAGE_BYTES:
        _LOG.warning("Sitemap %s слишком большой, пропуск", url)
        return None
    parsed = _parse_sitemap(response.content)
    if parsed is None:
        _LOG.warning("Sitemap %s не является корректным XML sitemap", url)
    return parsed


def _expand_sitemap(first_url: str, session: requests.Session, start_url: str,
                    preloaded: tuple[str, list[str]] | None = None) -> list[str]:
    pending, visited, pages = deque([first_url]), set(), []
    while pending and len(visited) < MAX_SITEMAPS:
        sitemap_url = pending.popleft()
        key = _normalize_page_url(sitemap_url)
        if not key or key in visited:
            continue
        visited.add(key)
        if not _robots_allowed(sitemap_url, session, start_url):
            _LOG.info("robots.txt запрещает sitemap %s", sitemap_url)
            continue
        parsed, preloaded = (preloaded if preloaded is not None
                             else _fetch_sitemap(session, sitemap_url)), None
        if parsed is not None:
            kind, locations = parsed
            if kind == "sitemapindex":
                pending.extend(urljoin(sitemap_url, loc) for loc in locations
                               if _normalize_page_url(urljoin(sitemap_url, loc)) not in visited)
                _LOG.info("Sitemap-индекс %s: дочерних карт %d", sitemap_url, len(locations))
            else:
                pages.extend(urljoin(sitemap_url, loc) for loc in locations)
                _LOG.info("Sitemap %s: URL %d", sitemap_url, len(locations))
        time.sleep(DELAY)  # пауза распространяется и на обход sitemap
    if len(visited) >= MAX_SITEMAPS:
        _LOG.warning("Достигнут лимит sitemap-файлов: %d", MAX_SITEMAPS)
    site_host = _host_key(start_url)
    return _dedupe(url for url in pages if _is_html_page(url)
                   and _host_key(url) == site_host and _robots_allowed(url, session, start_url))


def _bfs_collect(start_url: str, session: requests.Session) -> list[str]:
    start_key = _host_key(start_url)
    queue, seen, pages = deque([(start_url, 0)]), {_normalize_page_url(start_url)}, []
    while queue and len(pages) < MAX_FALLBACK_PAGES:
        url, depth = queue.popleft()
        if not _robots_allowed(url, session, start_url):
            _LOG.info("robots.txt запрещает страницу %s", url)
            continue
        started = time.perf_counter()
        try:
            response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        except requests.RequestException as exc:
            _LOG.warning("Ошибка BFS-запроса %s: %s", url, exc)
            continue
        ctype = response.headers.get("Content-Type", "").lower()
        length = response.headers.get("Content-Length")
        too_large = bool(length and length.isdigit() and int(length) > MAX_PAGE_BYTES)
        if response.status_code == 200 and "html" in ctype and not too_large \
                and len(response.content) <= MAX_PAGE_BYTES:
            pages.append(response.url)
            _LOG.info("BFS %s | глубина %d", response.url, depth)
            if depth < 10:
                encoding = response.encoding or response.apparent_encoding or "utf-8"
                try:
                    soup = BeautifulSoup(response.content.decode(encoding, errors="replace"), "lxml")
                    base_tag = soup.find("base", href=True)
                    base_href = (urljoin(response.url, str(base_tag.get("href")).strip())
                                 if base_tag is not None else response.url)
                    for raw, _tag, kind in _iter_link_targets(soup, base_href):
                        if kind == "form":
                            continue
                        candidate = _resolve_link(raw, base_href)
                        if not candidate:
                            continue
                        key = _normalize_page_url(candidate)
                        if _is_html_page(candidate) and _host_key(candidate) == start_key \
                                and key and key not in seen:
                            seen.add(key)
                            queue.append((candidate, depth + 1))
                except Exception as exc:
                    _LOG.warning("Битый HTML на %s: %s", url, exc)
        time.sleep(max(0, DELAY - (time.perf_counter() - started)))
    if len(pages) >= MAX_FALLBACK_PAGES:
        _LOG.warning("BFS остановлен на лимите %d страниц", MAX_FALLBACK_PAGES)
    return _dedupe(pages)


def collect_sitemap_urls(start_url: str, session: requests.Session) -> list[str]:
    """Найти sitemap, рекурсивно раскрыть его и вернуть HTML-URL сайта.

    Fallback при отсутствии sitemap — BFS внутренних ссылок до глубины 10.
    """
    if not start_url.startswith(("http://", "https://")):
        raise ValueError("Стартовый URL должен начинаться с http:// или https://")
    root = _origin(start_url)
    candidates = [urljoin(root, path) for path in SITEMAP_CANDIDATES]
    parser = _robots_for(start_url, session) if RESPECT_ROBOTS else None
    if parser is not None:
        try:
            candidates.extend(extra for extra in (parser.site_maps() or [])
                              if extra not in candidates)
        except Exception:
            pass

    first_url, preloaded = None, None
    for candidate in candidates:
        _LOG.info("Проверяю sitemap: %s", candidate)
        if not _robots_allowed(candidate, session, start_url):
            _LOG.info("robots.txt запрещает sitemap %s", candidate)
            continue
        parsed = _fetch_sitemap(session, candidate)
        if parsed is not None:
            first_url, preloaded = candidate, parsed
            break
        time.sleep(DELAY)
    if first_url:
        urls = _expand_sitemap(first_url, session, start_url, preloaded)
        if urls:
            _LOG.info("Sitemap собран: %d HTML-URL", len(urls))
            return urls
        _LOG.warning("Sitemap найден, но HTML-URL не обнаружены; перехожу к BFS")
    _LOG.warning("Sitemap не найден. Запускаю BFS-обход (глубина 10).")
    urls = _bfs_collect(start_url, session)
    _LOG.info("BFS завершён: %d HTML-URL", len(urls))
    return urls


# ---------------------------------------------------------------------------
# Сканирование страницы
# ---------------------------------------------------------------------------
_LINK_DATA_ATTRS = (
    "data-href", "data-url", "data-link", "data-target", "data-action",
    "data-path", "data-route",
)
_LINK_EVENT_ATTRS = (
    "onclick", "onmousedown", "onmouseup", "onchange", "onsubmit",
)
_JS_LINK_RE = re.compile(
    r"""(?:
      (?:window\.)?(?:document\.)?location(?:\.href)?\s*=\s*['"]([^'"]+)['"]
      |(?:window\.)?(?:document\.)?location\.(?:assign|replace)\s*\(\s*['"]([^'"]+)['"]
      |(?:window\.)?open\s*\(\s*['"]([^'"]+)['"]
      |['"](https?://[^'"\s]+)['"]
    )""",
    re.IGNORECASE | re.VERBOSE,
)
_META_REFRESH_RE = re.compile(r"(?:^|;)\s*url\s*=\s*([^;]+)", re.IGNORECASE)


def _clean_link_value(value: Any) -> str:
    raw = str(value or "").strip().strip("'\"")
    if not raw or raw[0] in "#{[":
        return ""
    if raw in ("_blank", "_self", "_top", "_parent"):
        return ""
    if raw.startswith(".") and not raw.startswith(("./", "../")):
        return ""
    if raw.lower().startswith((
        "mailto:", "tel:", "javascript:", "data:", "blob:", "about:", "file:",
    )):
        return ""
    return raw


def _resolve_link(value: Any, base_href: str) -> str:
    raw = _clean_link_value(value)
    if not raw:
        return ""
    if raw.startswith("//"):
        raw = "https:" + raw
    elif not raw.lower().startswith(("http://", "https://")):
        raw = urljoin(base_href, raw)
    if len(raw) > MAX_URL_LEN:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return ""
    return raw


def _iter_link_targets(soup: BeautifulSoup, base_href: str):
    """Все статические ссылки: a/area, кнопки, data-*, onclick, iframe/form."""
    for tag in soup.find_all(True):
        name = tag.name
        values: list[tuple[str, str]] = []

        if name in ("a", "area") and tag.has_attr("href"):
            values.append((str(tag.get("href")), name))
        if name == "form" and tag.has_attr("action"):
            values.append((str(tag.get("action")), "form"))
        if name in ("iframe", "frame", "embed") and tag.has_attr("src"):
            values.append((str(tag.get("src")), name))
        if name == "object" and tag.has_attr("data"):
            values.append((str(tag.get("data")), "object"))
        if name == "meta" and str(tag.get("http-equiv", "")).lower() == "refresh":
            match = _META_REFRESH_RE.search(str(tag.get("content", "")))
            if match:
                values.append((match.group(1).strip(), "meta refresh"))

        if tag.has_attr("formaction"):
            values.append((str(tag.get("formaction")), "formaction"))

        for attr in _LINK_DATA_ATTRS:
            if not tag.has_attr(attr):
                continue
            value = str(tag.get(attr)).strip()
            if attr in ("data-target", "data-action") and not value.startswith(
                    ("http://", "https://", "//", "/", "./", "../", "?")):
                continue
            values.append((value, "data"))
        for attr in _LINK_EVENT_ATTRS:
            if not tag.has_attr(attr):
                continue
            for match in _JS_LINK_RE.finditer(str(tag.get(attr))):
                value = next((part for part in match.groups() if part), "")
                if value:
                    values.append((value, "onclick"))

        for raw, kind in values:
            yield raw, tag, kind


def _extract_anchor(anchor_tag, kind: str = "") -> str:
    name = anchor_tag.name
    if name == "input":
        value = _squash(anchor_tag.get("value", ""))
        if value:
            return value[:MAX_ANCHOR_LEN]
    if name == "area":
        alt = _squash(anchor_tag.get("alt", ""))
        if alt:
            return alt[:MAX_ANCHOR_LEN]
    if name in ("iframe", "frame", "embed", "object"):
        title = _squash(anchor_tag.get("title") or anchor_tag.get("aria-label") or "")
        return f"[{name}: {title}]"[:MAX_ANCHOR_LEN] if title else f"[{name}]"
    if name == "meta":
        return "[meta refresh]"
    if name == "form":
        text = _squash(anchor_tag.get_text(" ", strip=True))
        return text[:MAX_ANCHOR_LEN] if text else "[form]"

    text = _squash(anchor_tag.get_text(" ", strip=True))
    if text:
        return text[:MAX_ANCHOR_LEN]
    image = anchor_tag.find("img")
    if image is not None and _squash(image.get("alt", "")):
        return f"[img: {_squash(image.get('alt'))}]"[:MAX_ANCHOR_LEN]
    aria = _squash(anchor_tag.get("aria-label", ""))
    if aria:
        return f"[aria: {aria}]"[:MAX_ANCHOR_LEN]
    title = _squash(anchor_tag.get("title", ""))
    if title:
        return f"[title: {title}]"[:MAX_ANCHOR_LEN]
    return f"[{kind}]" if kind else "[без текста]"


def _make_link_row(page_url: str, page_title: str, href: str, tag, kind: str) -> dict:
    rel_value = tag.get("rel") or []
    rel = _squash(rel_value) if isinstance(rel_value, str) else \
        " ".join(str(part) for part in rel_value)
    context = ""
    if tag.parent is not None:
        context = _squash(tag.parent.get_text(" ", strip=True))[:120]
    if kind not in ("a", "area") and context:
        context = f"[{kind}] {context}"[:120]
    return {
        "page_url": page_url, "page_title": page_title,
        "anchor": _extract_anchor(tag, kind),
        "href": href, "domain": _host_key(href), "rel": rel,
        "target": _squash(tag.get("target", "")),
        "context": context,
    }


def scan_page(url: str, session: requests.Session,
              start_url: str,
              internal_out: list[str] | None = None) -> tuple[list[dict], int | None]:
    """Просканировать страницу и вернуть (rows, status_code_or_None).

    Если передан internal_out, в него добавляются внутренние HTML-страницы,
    найденные на странице — чтобы подхватить страницы вне sitemap.

    status=None — сетевая ошибка после RETRIES. Для 429/503 и прочих HTTP-
    ошибок backoff не делается: этим управляет AdaptiveThrottle в батче.
    """
    if not _robots_allowed(url, session, start_url):
        _LOG.info("Пропуск %s: запрещено robots.txt", url)
        return [], 403
    started, response = time.perf_counter(), None
    try:
        for attempt in range(1, RETRIES + 1):
            try:
                response = session.get(url, timeout=TIMEOUT, allow_redirects=True)
            except requests.RequestException as exc:
                _LOG.warning("Сетевая ошибка %s (попытка %d/%d): %s",
                             url, attempt, RETRIES, exc)
                if attempt == RETRIES:
                    return [], None
                continue  # без backoff: паузу задаёт AdaptiveThrottle
            break

        if response is None:
            return [], None
        status = response.status_code
        if status >= 400:
            _LOG.warning("HTTP %s на %s, страница пропущена", status, url)
            return [], status

        ctype = response.headers.get("Content-Type", "").lower()
        if "html" not in ctype:
            _LOG.info("Пропуск %s: Content-Type=%s", response.url, ctype or "не указан")
            return [], status
        length = response.headers.get("Content-Length")
        if (length and length.isdigit() and int(length) > MAX_PAGE_BYTES) or \
                len(response.content) > MAX_PAGE_BYTES:
            _LOG.warning("Пропуск %s: размер больше %d байт", response.url, MAX_PAGE_BYTES)
            return [], status

        encoding = response.encoding
        if not encoding or encoding.lower() in ("iso-8859-1", "ascii"):
            encoding = response.apparent_encoding or encoding or "utf-8"
        try:
            html = response.content.decode(encoding, errors="replace")
        except (LookupError, TypeError):
            html = response.content.decode("utf-8", errors="replace")
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception as exc:
            _LOG.warning("Не удалось разобрать HTML %s: %s", response.url, exc)
            return [], status

        title_tag = soup.title
        page_title = _squash(title_tag.string or title_tag.get_text(" ", strip=True))[:200] \
            if title_tag is not None else ""
        base_tag = soup.find("base", href=True)
        base_href = (urljoin(response.url, str(base_tag.get("href")).strip())
                     if base_tag is not None else response.url)
        page_url, start_host = response.url, _host_key(start_url)
        rows, seen = [], set()
        internal_seen = set()
        for raw, tag, kind in _iter_link_targets(soup, base_href):
            href = _resolve_link(raw, base_href)
            if not href:
                continue
            if _host_key(href) == start_host:
                if internal_out is not None and kind != "form" and _is_html_page(href):
                    key = _normalize_page_url(href)
                    page_key = _normalize_page_url(page_url)
                    if key and key != page_key and key not in internal_seen:
                        internal_seen.add(key)
                        internal_out.append(href)
                continue
            anchor = _extract_anchor(tag, kind)
            if (href, anchor) in seen:
                continue
            seen.add((href, anchor))
            rows.append(_make_link_row(page_url, page_title, href, tag, kind))
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        _LOG.info("Страница %s | HTTP %s | внешних ссылок: %d | %.2f c",
                  page_url, status, len(rows), time.perf_counter() - started)
        return rows, status
    except Exception as exc:
        _LOG.exception("Ошибка обработки %s: %s", url, exc)
        return [], (response.status_code if response is not None else None)


def scan_page_legacy(url: str, session: requests.Session, start_url: str) -> list[dict]:
    """Старый контракт scan_page -> list[dict] для обратной совместимости."""
    return scan_page(url, session, start_url)[0]


# ---------------------------------------------------------------------------
# Состояние и CSV
# ---------------------------------------------------------------------------
def _new_stats() -> dict:
    return {"pages_scanned": 0, "links_found": 0, "unique_domains": 0,
            "nofollow": 0, "no_anchor": 0, "domain_counts": {}, "last_page": ""}


@dataclass
class CrawlState:
    """Состояние краулера, полностью сериализуемое в JSON."""
    queue: list[str] = field(default_factory=list)
    done: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=_new_stats)
    started_at: str = ""
    params: dict = field(default_factory=dict)
    throttle: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.queue = [str(url) for url in self.queue if str(url).strip()]
        self.done = [str(url) for url in self.done if str(url).strip()]
        self.rows = [row for row in self.rows if isinstance(row, dict)]
        if not isinstance(self.stats, dict):
            self.stats = {}
        for key, value in _new_stats().items():
            self.stats.setdefault(key, value)
        if not isinstance(self.stats["domain_counts"], dict):
            self.stats["domain_counts"] = {}
        if not isinstance(self.throttle, dict):
            self.throttle = {}
        self.stats["pages_scanned"] = len(self.done)

    @property
    def remaining(self) -> list[str]:
        done = set(self.done)
        return [url for url in self.queue if url not in done]

    @classmethod
    def load(cls, path: str) -> "CrawlState":
        """Загрузить состояние; при отсутствии/поломке вернуть пустое."""
        file = Path(path)
        if not file.exists():
            return cls()
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _LOG.error("Не удалось прочитать состояние %s: %s", path, exc)
            return cls()
        if not isinstance(payload, dict):
            return cls()
        def as_list(value: Any) -> list:
            return value if isinstance(value, list) else []
        return cls(queue=as_list(payload.get("queue")), done=as_list(payload.get("done")),
                   rows=as_list(payload.get("rows")),
                   stats=payload.get("stats") if isinstance(payload.get("stats"), dict) else {},
                   started_at=str(payload.get("started_at") or ""),
                   params=payload.get("params") if isinstance(payload.get("params"), dict) else {},
                   throttle=payload.get("throttle") if isinstance(payload.get("throttle"), dict) else {})

    def save(self, path: str) -> None:
        """Атомарно сохранить состояние: временный файл + os.replace."""
        file = Path(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        tmp = file.with_suffix(file.suffix + ".tmp")
        payload = {"queue": self.queue, "done": self.done, "rows": self.rows,
                   "stats": self.stats, "started_at": self.started_at,
                   "params": self.params, "throttle": self.throttle}
        try:
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, file)
        except OSError as exc:
            _LOG.error("Не удалось сохранить состояние %s: %s", path, exc)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise


def init_csv(path: str) -> None:
    """Создать CSV с заголовком, перезаписав существующий."""
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        csv.DictWriter(handle, fieldnames=ROW_FIELDS, extrasaction="ignore").writeheader()


def append_rows(path: str, rows: list[dict]) -> None:
    if not rows:
        return
    file = Path(path)
    if not file.exists() or file.stat().st_size == 0:
        init_csv(path)
    with open(path, "a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROW_FIELDS, extrasaction="ignore")
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in ROW_FIELDS})
        handle.flush()
        os.fsync(handle.fileno())


def read_csv(path: str, limit: int | None = None) -> list[dict]:
    """Прочитать CSV в список словарей; limit ограничивает число строк."""
    if not Path(path).exists():
        return []
    result = []
    try:
        with open(path, "r", encoding="utf-8-sig", newline="", errors="replace") as handle:
            for row in csv.DictReader(handle):
                result.append({key: str(row.get(key, "") or "") for key in ROW_FIELDS})
                if limit is not None and len(result) >= limit:
                    break
    except (OSError, csv.Error) as exc:
        _LOG.error("Не удалось прочитать CSV %s: %s", path, exc)
    return result


@st.cache_data(ttl=5, show_spinner=False)
def _read_csv_cached(path: str, mtime_ns: int, limit: int | None) -> list[dict]:
    # mtime_ns — ключ кэша, чтобы не читать файл на каждом rerun.
    return read_csv(path, limit=limit)


def _status_key(url: str) -> str:
    """Ключ кэша статусов: URL без fragment."""
    return _normalize_page_url(url) or str(url).strip()


def load_link_statuses(path: str = LINK_STATUS_FILE) -> dict[str, dict]:
    """Загрузить кэш HTTP-статусов внешних ссылок."""
    file = Path(path)
    if not file.exists():
        return {}
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _LOG.error("Не удалось прочитать кэш статусов %s: %s", path, exc)
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def save_link_statuses(statuses: dict[str, dict], path: str = LINK_STATUS_FILE) -> None:
    """Атомарно сохранить кэш статусов."""
    file = Path(path)
    tmp = file.with_suffix(file.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(statuses, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, file)
    except OSError as exc:
        _LOG.error("Не удалось сохранить кэш статусов %s: %s", path, exc)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _status_phrase(code: int | None) -> str:
    if code is None:
        return "Сетевая ошибка"
    try:
        return HTTPStatus(int(code)).phrase
    except (TypeError, ValueError):
        return ""


def _status_label(entry: dict | None) -> str:
    if not entry:
        return "— Не проверено"
    code = entry.get("status")
    if code is None:
        return "⛔ Ошибка сети"
    code = int(code)
    if entry.get("ssl_verified") is False:
        phrase = _status_phrase(code)
        return f"🔓 {code} {phrase} (SSL не проверен)".strip()
    if 200 <= code < 300:
        icon = "✅"
    elif 300 <= code < 400:
        icon = "↪️"
    elif 400 <= code < 500:
        icon = "⚠️"
    else:
        icon = "❌"
    phrase = _status_phrase(code)
    return f"{icon} {code} {phrase}".strip()


def _status_short(entry: dict | None) -> str:
    """Короткая подпись для таблицы и фильтров."""
    if not entry:
        return "Не проверено"
    code = entry.get("status")
    if code is None:
        return "⛔ Сеть"
    code = int(code)
    if entry.get("ssl_verified") is False:
        return f"🔓 {code}"
    if 200 <= code < 300:
        icon = "✅"
    elif 300 <= code < 400:
        icon = "↪️"
    elif 400 <= code < 500:
        icon = "⚠️"
    else:
        icon = "❌"
    return f"{icon} {code}"


def _status_group(entry: dict | None) -> str:
    if not entry:
        return "unchecked"
    code = entry.get("status")
    if code is not None and int(code) < 400 and entry.get("ssl_verified") is False:
        return "ssl"
    if code is None:
        return "problem"
    return "problem" if int(code) >= 400 else "ok"


def _unique_external_links(rows: Iterable[dict]) -> dict[str, str]:
    """Уникальные внешние URL: ключ проверки -> исходный href."""
    links: dict[str, str] = {}
    for row in rows:
        href = str(row.get("href", "")).strip()
        key = _status_key(href)
        if href and key:
            links.setdefault(key, href)
    return links


def _status_values(href: str, statuses: dict[str, dict]) -> dict:
    entry = statuses.get(_status_key(href))
    return {
        "status_code": "" if not entry or entry.get("status") is None else entry.get("status"),
        "status_label": _status_label(entry),
        "final_url": str(entry.get("final_url") or "") if entry else "",
        "error": str(entry.get("error") or "") if entry else "",
        "checked_at": str(entry.get("checked_at") or "") if entry else "",
        "ssl_verified": "" if not entry else (
            "Да" if entry.get("ssl_verified", True) else "Нет"
        ),
    }


def check_external_link(url: str, session: requests.Session) -> dict:
    """Проверить внешнюю ссылку: HEAD, при необходимости GET.

    Тело GET не читается. Проверка не идёт по контенту и не выполняет JS.
    """
    target = _status_key(url)
    checked_at = _now_iso()
    error = ""
    ssl_error = ""
    # Для внешних проверок используем браузерный User-Agent: часть сайтов
    # (например, некоторые CMS) отдаёт 418/403 ботам, хотя обычному посетителю
    # страница доступна. Тело ответа всё равно не читается.
    headers = {
        "User-Agent": LINK_CHECK_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.7",
    }
    try:
        response = session.get(
            target, timeout=LINK_TIMEOUT, allow_redirects=True,
            headers=headers, stream=True,
        )
    except requests.RequestException as exc:
        if isinstance(exc, requests.exceptions.SSLError):
            ssl_error = _squash(exc)[:300]
        error = _squash(exc)[:300]
    else:
        status = response.status_code
        final_url = response.url
        try:
            response.close()
        except Exception:
            pass
        return {
            "status": status,
            "final_url": final_url,
            "error": "",
            "checked_at": checked_at,
            "method": "GET",
            "ssl_verified": True,
        }

    # Сертификат может быть валиден для браузера, но не собираться в цепочку
    # в Python. Для аудита доступности делаем один запрос без проверки SSL,
    # но явно помечаем результат как «SSL не проверен».
    if ssl_error:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                response = session.get(
                    target, timeout=LINK_TIMEOUT, allow_redirects=True,
                    headers=headers, stream=True, verify=False,
                )
        except requests.RequestException as exc:
            return {
                "status": None,
                "final_url": target,
                "error": (_squash(exc) or ssl_error)[:300],
                "checked_at": checked_at,
                "method": "GET",
                "ssl_verified": False,
            }
        status = response.status_code
        final_url = response.url
        try:
            response.close()
        except Exception:
            pass
        return {
            "status": status,
            "final_url": final_url,
            "error": f"SSL: {ssl_error}"[:300],
            "checked_at": checked_at,
            "method": "GET",
            "ssl_verified": False,
        }

    return {
        "status": None,
        "final_url": target,
        "error": error or "Не удалось выполнить запрос",
        "checked_at": checked_at,
        "method": "HEAD/GET",
        "ssl_verified": True,
    }


def build_csv_bytes(rows: list[dict], statuses: dict[str, dict]) -> bytes:
    """CSV со статусами внешних ссылок (в памяти)."""
    output = io.StringIO(newline="")
    fieldnames = list(ROW_FIELDS) + list(LINK_STATUS_FIELDS)
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        values = {key: row.get(key, "") for key in ROW_FIELDS}
        values.update(_status_values(row.get("href", ""), statuses))
        writer.writerow(values)
    return output.getvalue().encode("utf-8-sig")


@st.cache_resource(show_spinner=False)
def _crawler_session() -> requests.Session:
    # Одна Session на батч; живёт между rerun-ами, пока батч активен.
    return _make_session()


@st.cache_resource(show_spinner=False)
def _link_check_session() -> requests.Session:
    return _make_session()


def _apply_rows_to_stats(state: CrawlState, rows: list[dict]) -> None:
    counts = state.stats.get("domain_counts")
    if not isinstance(counts, dict):
        counts = {}
        state.stats["domain_counts"] = counts
    for row in rows:
        if row.get("domain"):
            counts[row["domain"]] = int(counts.get(row["domain"], 0)) + 1
        state.stats["nofollow"] += int(_is_nofollow(row.get("rel", "")))
        state.stats["no_anchor"] += int(_is_blank_anchor(row.get("anchor", "")))
    state.stats["links_found"] += len(rows)
    state.stats["unique_domains"] = len(counts)
    state.stats["pages_scanned"] = len(state.done)


def _recalculate_stats(state: CrawlState) -> None:
    last_page = state.stats.get("last_page", "") if isinstance(state.stats, dict) else ""
    state.stats = _new_stats()
    state.stats["last_page"] = last_page
    _apply_rows_to_stats(state, state.rows)


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
_ILLEGAL_XLSX = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_TOP10_FILL = PatternFill("solid", fgColor="FFF2CC")
_LINK_FONT = Font(color="0563C1", underline="single")


def _cell(value: Any) -> Any:
    if value is None or isinstance(value, (int, float)):
        return value if value is not None else ""
    return _ILLEGAL_XLSX.sub("", str(value))[:32767]


def _header(ws, row: int = 1) -> None:
    for cell in ws[row]:
        cell.font, cell.fill = _HEADER_FONT, _HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)


def _link_headers(ws, row: int) -> None:
    for column, title in enumerate(EXCEL_HEADERS, 1):
        ws.cell(row=row, column=column, value=title)
    _header(ws, row)


def _linkify(ws, first: int, last: int) -> None:
    for row in range(first, last + 1):
        for column in (1, 4, 10):
            cell = ws.cell(row=row, column=column)
            if cell.value:
                cell.hyperlink, cell.font = str(cell.value), _LINK_FONT


def _excel_values(data: dict, statuses: dict[str, dict]) -> list:
    status = _status_values(data.get("href", ""), statuses)
    return [
        data.get("page_url", ""), data.get("page_title", ""), data.get("anchor", ""),
        data.get("href", ""), data.get("domain", ""), status["status_label"],
        data.get("rel", ""), data.get("target", ""), data.get("context", ""),
        status["final_url"], status["error"], status["checked_at"],
    ]


def _link_table(ws, rows: list[dict], start: int,
                statuses: dict[str, dict] | None = None) -> int:
    statuses = statuses or {}
    _link_headers(ws, start)
    row = start
    for data in rows:
        row += 1
        values = _excel_values(data, statuses)
        for column, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=column, value=_cell(value))
            cell.alignment = Alignment(vertical="top", wrap_text=(column in (9, 11)))
    _linkify(ws, start + 1, row)
    return row


def build_excel(rows: list[dict], state: CrawlState,
                statuses: dict[str, dict] | None = None) -> bytes:
    """Собрать Excel в памяти: 5 листов, гиперссылки, автофильтр, статусы."""
    statuses = statuses or {}
    workbook = Workbook()
    ws = workbook.active
    ws.title = "Все ссылки"
    last = _link_table(ws, rows, 1, statuses)
    ws.freeze_panes, ws.auto_filter.ref = "A2", f"A1:L{max(last, 1)}"
    for column, width in enumerate(_LINK_COL_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(column)].width = width
    _linkify(ws, 2, last)

    counts, sources, broken, ssl_counts = Counter(), {}, Counter(), Counter()
    for row in rows:
        domain = row.get("domain", "")
        if domain:
            counts[domain] += 1
            sources.setdefault(domain, set()).add(row.get("page_url", ""))
            group = _status_group(statuses.get(_status_key(row.get("href", ""))))
            if group == "problem":
                broken[domain] += 1
            elif group == "ssl":
                ssl_counts[domain] += 1
    ws = workbook.create_sheet("Сводка по доменам")
    for column, title in enumerate(["Домен", "Кол-во ссылок",
                                    "Уникальных страниц-источников",
                                    "Битых ссылок", "SSL-предупреждений"], 1):
        ws.cell(row=1, column=column, value=title)
    _header(ws)
    for index, (domain, count) in enumerate(sorted(counts.items(),
                                                    key=lambda item: (-item[1], item[0])), 2):
        ws.cell(row=index, column=1, value=_cell(domain))
        ws.cell(row=index, column=2, value=count)
        ws.cell(row=index, column=3, value=len(sources[domain]))
        ws.cell(row=index, column=4, value=broken[domain])
        ws.cell(row=index, column=5, value=ssl_counts[domain])
        if index <= 11:
            for column in range(1, 6):
                ws.cell(row=index, column=column).fill = _TOP10_FILL
    ws.freeze_panes, ws.auto_filter.ref = "A2", f"A1:E{max(ws.max_row, 1)}"
    for column, width in enumerate([34, 18, 30, 16, 20], 1):
        ws.column_dimensions[get_column_letter(column)].width = width

    ws = workbook.create_sheet("Проблемные")
    broken_rows = [
        row for row in rows
        if _status_group(statuses.get(_status_key(row.get("href", "")))) == "problem"
        and statuses.get(_status_key(row.get("href", ""))) is not None
    ]
    ssl_rows = [
        row for row in rows
        if _status_group(statuses.get(_status_key(row.get("href", "")))) == "ssl"
    ]
    sections = [
        ("Битые внешние ссылки (4xx/5xx/сеть)", broken_rows),
        ("SSL-предупреждения", ssl_rows),
        ("Без анкора", [row for row in rows if _is_blank_anchor(row.get("anchor", ""))]),
        ("nofollow", [row for row in rows if _is_nofollow(row.get("rel", ""))]),
        ("HTTP-ссылки (не HTTPS)", [row for row in rows
                                    if row.get("href", "").lower().startswith("http://")]),
    ]
    current = 1
    for title, section_rows in sections:
        cell = ws.cell(row=current, column=1, value=title)
        cell.font = Font(bold=True, size=12, color="1F4E78")
        current += 1
        if section_rows:
            current = _link_table(ws, section_rows, current, statuses) + 2
        else:
            ws.cell(row=current, column=1, value="Нет")
            current += 2
    for column, width in enumerate(_LINK_COL_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(column)].width = width

    # ---- Отдельный лист по уникальным внешним ссылкам ----
    ws = workbook.create_sheet("Статусы ссылок")
    status_headers = ["Внешний URL", "Домен", "Статус", "Код", "Финальный URL",
                      "Ошибка", "Проверено", "Вхождений", "Страниц-источников"]
    for column, title in enumerate(status_headers, 1):
        ws.cell(row=1, column=column, value=title)
    _header(ws)
    unique = _unique_external_links(rows)
    occurrences: Counter[str] = Counter()
    unique_pages: dict[str, set[str]] = {}
    for row in rows:
        key = _status_key(row.get("href", ""))
        if key:
            occurrences[key] += 1
            unique_pages.setdefault(key, set()).add(row.get("page_url", ""))
    for index, (key, href) in enumerate(unique.items(), 2):
        entry = statuses.get(key)
        values = _status_values(href, statuses)
        ws.cell(row=index, column=1, value=_cell(href))
        ws.cell(row=index, column=2, value=_cell(_host_key(href)))
        ws.cell(row=index, column=3, value=_cell(values["status_label"]))
        ws.cell(row=index, column=4, value=values["status_code"])
        ws.cell(row=index, column=5, value=_cell(values["final_url"]))
        ws.cell(row=index, column=6, value=_cell(values["error"]))
        ws.cell(row=index, column=7, value=_cell(values["checked_at"]))
        ws.cell(row=index, column=8, value=occurrences[key])
        ws.cell(row=index, column=9, value=len(unique_pages.get(key, set())))
    for row in range(2, ws.max_row + 1):
        for column in (1, 5):
            cell = ws.cell(row=row, column=column)
            if cell.value:
                cell.hyperlink, cell.font = str(cell.value), _LINK_FONT
    ws.freeze_panes, ws.auto_filter.ref = "A2", f"A1:I{max(ws.max_row, 1)}"
    for column, width in enumerate([55, 24, 26, 10, 55, 40, 22, 12, 20], 1):
        ws.column_dimensions[get_column_letter(column)].width = width

    ws = workbook.create_sheet("Метаданные")
    try:
        started = datetime.fromisoformat(state.started_at)
        if started.tzinfo is not None:
            started = started.astimezone().replace(tzinfo=None)
        duration = max(0.0, (datetime.now() - started).total_seconds())
    except (TypeError, ValueError):
        duration = 0.0
    params = state.params or {}
    speed = len(state.done) / duration if duration > 0 else 0.0
    checked_links = sum(1 for key in unique if key in statuses)
    broken_links = sum(1 for key in unique
                       if _status_group(statuses.get(key)) == "problem")
    ssl_links = sum(1 for key in unique
                    if _status_group(statuses.get(key)) == "ssl")
    meta = [
        ("Дата формирования", _now_display()), ("Начало сканирования", state.started_at or "—"),
        ("Длительность", _format_duration(duration)), ("Стартовый URL", params.get("start_url", "")),
        ("Пауза между запросами, сек", params.get("delay", DELAY)),
        ("Режим скорости", "Авто" if params.get("speed_mode") == "auto" else "Ручной"),
        ("Мин. пауза, сек", params.get("min_delay", "")),
        ("Макс. пауза, сек", params.get("max_delay", "")),
        ("Размер батча", params.get("batch_size", "")),
        ("Уважать robots.txt", "Да" if params.get("respect_robots", RESPECT_ROBOTS) else "Нет"),
        ("Просканировано страниц", len(state.done)), ("Найдено внешних ссылок", len(rows)),
        ("Уникальных внешних ссылок", len(unique)),
        ("Проверено внешних ссылок", checked_links),
        ("Битых внешних ссылок", broken_links),
        ("SSL-предупреждений", ssl_links),
        ("Уникальных доменов", len(counts)), ("Скорость, страниц/сек", round(speed, 4)),
    ]
    ws.cell(row=1, column=1, value="Параметр")
    ws.cell(row=1, column=2, value="Значение")
    _header(ws)
    for index, (key, value) in enumerate(meta, 2):
        ws.cell(row=index, column=1, value=_cell(key))
        ws.cell(row=index, column=2, value=_cell(value))
    ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 34, 60
    ws.freeze_panes = "A2"
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@st.cache_data(ttl=30, show_spinner=False)
def _excel_cached(csv_path: str, csv_mtime_ns: int, state_mtime_ns: int,
                  status_mtime_ns: int) -> bytes:
    # mtime state/status входят в ключ, чтобы отчёт обновлялся после проверки.
    state = CrawlState.load(STATE_FILE)
    statuses = load_link_statuses()
    return build_excel(read_csv(csv_path) or state.rows, state, statuses)


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Link Audit", page_icon="🔍", layout="wide")
st.markdown(
    """
    <style>
    .stApp {
        color-scheme: dark;
        color: #e5e7eb;
        overflow-x: hidden;
        background:
            radial-gradient(1100px 520px at 8% -12%, rgba(34, 211, 238, .12), transparent 62%),
            radial-gradient(900px 460px at 96% 0%, rgba(99, 102, 241, .14), transparent 58%),
            #0b1220;
    }
    .block-container {
        width: 100% !important;
        max-width: 1240px !important;
        margin: 0 auto !important;
        padding: 1.4rem 2rem 3rem 2rem !important;
        box-sizing: border-box;
    }
    .la-hero {
        border-radius: 22px;
        padding: 24px 28px;
        margin-bottom: 18px;
        color: #f8fafc;
        background: linear-gradient(120deg, #0a101c 0%, #102a43 55%, #083344 100%);
        border: 1px solid rgba(34, 211, 238, .20);
        box-shadow: 0 22px 55px rgba(0, 0, 0, .36);
    }
    .la-hero h1 { margin: 2px 0 6px 0; font-size: 2.15rem; letter-spacing: -.03em; color: #ffffff; }
    .la-hero p { margin: 0; color: #cbd5e1; max-width: 900px; }
    .la-kicker { font-size: .76rem; letter-spacing: .18em; text-transform: uppercase; color: #67e8f9; font-weight: 700; }
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(17, 24, 39, .98), rgba(15, 23, 42, .92));
        border: 1px solid rgba(148, 163, 184, .16);
        padding: 14px 16px;
        border-radius: 16px;
        box-shadow: 0 10px 28px rgba(0, 0, 0, .18);
    }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; }
    div[data-testid="stMetricValue"] { color: #f8fafc !important; }
    .stApp [data-testid="stWidgetLabel"] p, .stApp label { color: #cbd5e1; }
    [data-testid="stCaptionContainer"] p { color: #94a3b8; }
    div.stButton > button {
        border-radius: 11px;
        font-weight: 600;
        border: 1px solid rgba(148, 163, 184, .28);
        transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
        background: #111827;
        color: #e5e7eb;
    }
    div.stButton > button:hover {
        background: #1e293b;
        border-color: rgba(34, 211, 238, .45);
        transform: translateY(-1px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, .24);
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(120deg, #0891b2, #0e7490);
        border-color: transparent;
        color: #ecfeff;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(120deg, #06b6d4, #0891b2);
    }
    div.stButton > button:disabled { opacity: .45; }
    div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, .18);
        background: #0f172a;
    }
    div[data-testid="stExpander"] {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, .16);
        background: rgba(17, 24, 39, .72);
    }
    div[data-testid="stAlert"] { border-radius: 14px; }
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    div[data-baseweb="base-input"] {
        background-color: #0f172a !important;
        border-color: #334155 !important;
        color: #e5e7eb !important;
    }
    input, textarea { color: #e5e7eb !important; }
    a { color: #67e8f9; }
    h2, h3 { letter-spacing: -.02em; color: #f1f5f9; }
    header[data-testid="stHeader"] { display: none; }
    div[data-testid="stToolbar"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="la-hero">
        <div class="la-kicker">SEO · External Link Audit</div>
        <h1>🔍 Link Audit</h1>
        <p>Аудит внешних ссылок, проверка HTTP-статусов и отчётность.
        Один поток, вежливые паузы, прогресс сохраняется между запусками.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

state = CrawlState.load(STATE_FILE)
_recalculate_stats(state)
statuses = load_link_statuses()
flash = st.session_state.pop("_flash", None)
if flash:
    getattr(st, flash[0], st.info)(flash[1])

# Троттлер живёт в session_state, но его снимок сохраняется в crawl_state.json.
if "throttle" not in st.session_state:
    restored_throttle = AdaptiveThrottle(
        initial_delay=1.5, min_delay=0.3, max_delay=10.0, window=10
    )
    if state.throttle:
        restored_throttle.restore(state.throttle)
    st.session_state["throttle"] = restored_throttle
throttle: AdaptiveThrottle = st.session_state["throttle"]
st.session_state.setdefault("throttle_snapshot", throttle.snapshot())

_default_mode = state.params.get("speed_mode", "auto")
if _default_mode not in ("manual", "auto"):
    _default_mode = "auto"
for key, default in (("stop_requested", False), ("batch_running", False),
                     ("pages_done_in_batch", 0), ("batch_target", 0),
                     ("site_error_streak", 0), ("confirm_sitemap", False),
                     ("confirm_reset", False), ("confirm_rescan", False),
                     ("table_page", 0),
                     ("speed_mode", _default_mode), ("manual_delay", float(DELAY)),
                     ("auto_min_delay", 0.3), ("auto_max_delay", 10.0),
                     ("link_check_running", False), ("link_check_stop", False),
                     ("link_check_queue", []), ("link_check_total", 0),
                     ("link_check_processed", 0), ("link_check_mode", "missing"),
                     ("link_batch_size", LINK_CHECK_BATCH),
                     ("link_check_delay", LINK_DEFAULT_DELAY)):
    st.session_state.setdefault(key, default)

st.subheader("⚙️ Параметры")
start_url = st.text_input("Стартовый URL", value=START_URL).strip()
base_cols = st.columns(2)
batch_size = base_cols[0].number_input("Размер батча", 10, 500, 50, 10)
respect = base_cols[1].checkbox("Уважать robots.txt", value=RESPECT_ROBOTS)

mode = st.radio(
    "Режим скорости",
    ["manual", "auto"],
    format_func=lambda value: (
        "Ручной — фиксированный DELAY" if value == "manual"
        else "Авто — адаптация под сайт"
    ),
    horizontal=True,
    key="speed_mode",
)
speed_valid = True
delay_metric_slot = None
avg_metric_slot = None
if mode == "manual":
    manual_delay = st.slider("Пауза между запросами, сек", 0.3, 10.0,
                             step=0.1, key="manual_delay")
    speed_delay = float(manual_delay)
else:
    auto_cols = st.columns(2)
    auto_min = auto_cols[0].slider("Мин. пауза, сек", 0.2, 3.0,
                                   step=0.1, key="auto_min_delay")
    auto_max = auto_cols[1].slider("Макс. пауза, сек", 2.0, 15.0,
                                   step=0.5, key="auto_max_delay")
    if float(auto_min) >= float(auto_max):
        speed_valid = False
        st.error("min_delay должен быть меньше max_delay")
    else:
        throttle.min_delay = float(auto_min)
        throttle.max_delay = float(auto_max)
        throttle.delay = min(throttle.max_delay, max(throttle.min_delay, throttle.delay))
    speed_metrics = st.columns(2)
    delay_metric_slot = speed_metrics[0].empty()
    avg_metric_slot = speed_metrics[1].empty()
    delay_metric_slot.metric("Текущий DELAY", f"{throttle.delay:.2f} сек")
    avg = throttle.avg_response
    avg_metric_slot.metric("Среднее время ответа",
                           f"{avg * 1000:.0f} ms" if avg is not None else "—")
    speed_delay = throttle.delay

DELAY = float(speed_delay)
RESPECT_ROBOTS = bool(respect)
params = {
    "start_url": start_url,
    "delay": DELAY,
    "batch_size": int(batch_size),
    "respect_robots": RESPECT_ROBOTS,
    "speed_mode": mode,
    "min_delay": throttle.min_delay,
    "max_delay": throttle.max_delay,
}


def _collect_sitemap() -> None:
    if not start_url.startswith(("http://", "https://")):
        st.error("Стартовый URL должен начинаться с http:// или https://")
        return
    session = _make_session()
    try:
        with st.spinner("Собираю sitemap. Это может занять несколько минут…"):
            urls = collect_sitemap_urls(start_url, session)
    except Exception as exc:
        _LOG.exception("Ошибка сбора sitemap: %s", exc)
        st.error(f"Не удалось собрать sitemap: {exc}")
        return
    finally:
        session.close()
    if not urls:
        st.error("Sitemap не найден, и BFS не нашёл доступных HTML-страниц. "
                 "Проверьте URL и robots.txt.")
        return
    new_state = CrawlState(queue=urls, stats=_new_stats(), started_at=_now_iso(),
                           params=params, throttle=throttle.snapshot())
    st.session_state.update(batch_running=False, stop_requested=False,
                            pages_done_in_batch=0, batch_target=0,
                            site_error_streak=0, link_check_running=False,
                            link_check_stop=False, link_check_queue=[],
                            link_check_total=0, link_check_processed=0)
    _crawler_session.clear()
    _link_check_session.clear()
    try:
        init_csv(CSV_FILE)
        new_state.save(STATE_FILE)
    except OSError as exc:
        st.error(f"Не удалось сохранить состояние: {exc}")
        return
    _LOG.info("Sitemap сохранён: %d URL; прежний прогресс сброшен", len(urls))
    st.session_state.update(confirm_sitemap=False, table_page=0,
                            **{"_flash": ("success", f"Найдено {_format_int(len(urls))} URL. Sitemap сохранён.")})
    st.rerun()


def _start_link_check(mode: str) -> None:
    """Сформировать очередь проверки внешних ссылок и запустить микробатчи."""
    links = _unique_external_links(
        state.rows or (read_csv(CSV_FILE) if Path(CSV_FILE).exists() else [])
    )
    cache = load_link_statuses()
    if mode == "missing":
        queue = [key for key in links if key not in cache]
    elif mode == "errors":
        queue = [key for key in links
                 if _status_group(cache.get(key)) in ("problem", "ssl")]
    else:
        queue = list(links)
    if not queue:
        st.info("Нет ссылок для проверки в выбранном режиме.")
        return
    _link_check_session.clear()
    st.session_state.update(
        link_check_running=True, link_check_stop=False,
        link_check_queue=queue, link_check_total=len(queue),
        link_check_processed=0, link_check_mode=mode,
    )
    st.rerun()


def _reset_all() -> None:
    _close_logging()
    for path in (STATE_FILE, CSV_FILE, LOG_FILE, LINK_STATUS_FILE,
                 STATE_FILE + ".tmp", LINK_STATUS_FILE + ".tmp"):
        try:
            Path(path).unlink(missing_ok=True)
        except OSError as exc:
            st.error(f"Не удалось удалить {path}: {exc}")
            _setup_logging()
            return
    _setup_logging()
    _LOG.info("Прогресс и статусы ссылок сброшены пользователем")
    st.cache_data.clear()
    _crawler_session.clear()
    _link_check_session.clear()
    for key in ("stop_requested", "batch_running", "confirm_sitemap", "confirm_reset",
                "confirm_rescan", "table_page", "pages_done_in_batch", "batch_target",
                "site_error_streak", "link_check_running", "link_check_stop",
                "link_check_total", "link_check_processed"):
        st.session_state[key] = False if key not in (
            "table_page", "pages_done_in_batch", "batch_target", "site_error_streak",
            "link_check_total", "link_check_processed"
        ) else 0
    st.session_state["link_check_queue"] = []
    st.session_state.pop("throttle", None)
    st.session_state.pop("throttle_snapshot", None)
    st.session_state["_flash"] = ("success", "Прогресс, CSV, лог и статусы ссылок удалены.")
    st.rerun()


st.subheader("🎛 Управление")
total, done_count = len(state.queue), len(state.done)
has_pending = done_count < total
controls = st.columns(3)
collect_clicked = controls[0].button("▶ Собрать sitemap", width="stretch")
scan_clicked = controls[1].button("▶ Сканировать батч", type="primary",
                                  width="stretch",
                                  disabled=not state.queue or not has_pending
                                  or not speed_valid or st.session_state["batch_running"]
                                  or st.session_state.get("link_check_running", False))
pause_clicked = controls[2].button("⏸ Пауза", width="stretch",
                                   disabled=not st.session_state["batch_running"])
extra_controls = st.columns([1, 1, 2])
emergency_clicked = extra_controls[0].button(
    "🚨 Экстренный тормоз", width="stretch", disabled=(mode != "auto")
)
reset_clicked = extra_controls[1].button("🗑 Сброс", width="stretch")
extra_controls[2].caption("Сброс удалит прогресс, CSV, лог и статусы ссылок.")
rescan_cols = st.columns([1.2, 2.8])
rescan_clicked = rescan_cols[0].button(
    "🔄 Пересканировать страницы", width="stretch",
    disabled=not state.queue or st.session_state["batch_running"],
)
rescan_cols[1].caption(
    "Повторно обойти все страницы и найти новые ссылки — включая кнопки, "
    "data-атрибуты и onclick. Статусы ссылок сохранятся."
)

if emergency_clicked:
    if mode != "auto":
        st.toast("В ручном режиме экстренный тормоз не действует")
    else:
        throttle.emergency_brake()
        st.session_state["throttle_snapshot"] = throttle.snapshot()
        if delay_metric_slot is not None:
            delay_metric_slot.metric("Текущий DELAY", f"{throttle.delay:.2f} сек")
        if avg_metric_slot is not None:
            avg = throttle.avg_response
            avg_metric_slot.metric("Среднее время ответа",
                                   f"{avg * 1000:.0f} ms" if avg is not None else "—")
        if state.queue:
            state.throttle = throttle.snapshot()
            try:
                state.save(STATE_FILE)
            except OSError as exc:
                st.error(f"Не удалось сохранить состояние: {exc}")
        st.toast("Скорость сброшена до минимума (max_delay)")

if not state.queue:
    st.info("Sitemap ещё не собран. Нажмите «▶ Собрать sitemap».")
elif not has_pending:
    st.success("Все страницы из очереди просканированы. Можно скачать отчёт или сбросить прогресс.")
else:
    st.caption(f"В очереди: {_format_int(total - done_count)} из {_format_int(total)} URL.")

if collect_clicked:
    if state.queue:
        st.session_state["confirm_sitemap"] = True
    else:
        _collect_sitemap()
if st.session_state["confirm_sitemap"]:
    st.warning("Sitemap уже собран. Пересборка сбросит текущий прогресс и таблицу, "
               "а CSV будет перезаписан. Продолжить?")
    confirm = st.columns([1, 1, 4])
    if confirm[0].button("Да, пересобрать", type="primary", width="stretch"):
        _collect_sitemap()
    if confirm[1].button("Отмена", width="stretch"):
        st.session_state["confirm_sitemap"] = False
        st.rerun()

if reset_clicked:
    st.session_state["confirm_reset"] = True
if st.session_state["confirm_reset"]:
    st.warning("Удалить crawl_state.json, external_links.csv, link_status.json "
               "и crawl.log? Это действие нельзя отменить.")
    reset = st.columns([1, 1, 4])
    if reset[0].button("Да, удалить", type="primary", width="stretch"):
        _reset_all()
    if reset[1].button("Отмена", key="cancel_reset", width="stretch"):
        st.session_state["confirm_reset"] = False
        st.rerun()
if rescan_clicked:
    st.session_state["confirm_rescan"] = True
if st.session_state["confirm_rescan"]:
    st.warning("Пересканировать все страницы заново? Найденные строки и прогресс "
               "страниц будут очищены, а CSV перезаписан. Кэш HTTP-статусов "
               "сохранится.")
    rescan = st.columns([1, 1, 4])
    if rescan[0].button("Да, пересканировать", type="primary", width="stretch"):
        try:
            state.done = []
            state.rows = []
            state.stats = _new_stats()
            state.started_at = _now_iso()
            state.params = params
            state.throttle = throttle.snapshot()
            state.save(STATE_FILE)
            init_csv(CSV_FILE)
        except OSError as exc:
            st.error(f"Не удалось подготовить пересканирование: {exc}")
        else:
            st.session_state["confirm_rescan"] = False
            st.session_state["table_page"] = 0
            st.session_state["pages_done_in_batch"] = 0
            st.session_state["batch_target"] = 0
            st.cache_data.clear()
            st.session_state["_flash"] = (
                "success",
                "Страницы очищены для повторного обхода. Статусы ссылок сохранены.",
            )
            _LOG.info("Пользователь запустил пересканирование страниц")
            st.rerun()
    if rescan[1].button("Отмена", key="cancel_rescan", width="stretch"):
        st.session_state["confirm_rescan"] = False
        st.rerun()
if pause_clicked:
    st.session_state["stop_requested"] = True
    st.info("Запрошена пауза. Батч остановится после текущей страницы.")

# ---------------------------------------------------------------------------
# Прогресс
# ---------------------------------------------------------------------------
st.subheader("📈 Прогресс")


def _elapsed() -> float:
    if not state.started_at:
        return 0.0
    try:
        started = datetime.fromisoformat(state.started_at)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - started).total_seconds())
    except (TypeError, ValueError):
        return 0.0


progress = st.progress(0.0)
progress_text = st.empty()
progress_cols = st.columns(4)
speed_metric, eta_metric = progress_cols[0].empty(), progress_cols[1].empty()
elapsed_metric, left_metric = progress_cols[2].empty(), progress_cols[3].empty()
last_page_caption = st.empty()


def _paint_progress() -> None:
    total_now, done_now = len(state.queue), len(state.done)
    fraction = min(1.0, done_now / total_now) if total_now else 0.0
    progress.progress(fraction)
    progress_text.markdown(f"**{_format_int(done_now)} / {_format_int(total_now)} "
                           f"({fraction * 100:.1f}%)**")
    elapsed = _elapsed()
    speed = done_now / elapsed if elapsed > 0 else 0.0
    eta = (total_now - done_now) / speed if speed > 0 else None
    speed_metric.metric("Скорость (URL/сек)", f"{speed:.2f}")
    eta_metric.metric("ETA", _format_duration(eta))
    elapsed_metric.metric("Прошло", _format_duration(elapsed))
    left_metric.metric("Осталось", _format_duration(eta))
    last_page_caption.caption(f"Последняя страница: {state.stats.get('last_page') or '—'}")


_paint_progress()

st.subheader("⏱ Отзывчивость сайта")
history = list(throttle.history)
if len(history) < 3:
    st.info("График появится после 3 запросов")
else:
    response_frame = pd.DataFrame({
        "request": list(range(1, len(history) + 1)),
        "response_time_sec": [round(elapsed, 4) for elapsed, _ in history],
        "status": [status for _, status in history],
    })
    st.line_chart(response_frame, x="request", y="response_time_sec", height=220)
st.caption("Время ответа по последним N запросам. Рост → сайт замедляется, "
           "тормозим. Падение → ускоряемся.")

# ---------------------------------------------------------------------------
# Батч: микробатчи по MICRO_BATCH страниц, между ними — st.rerun().
# ---------------------------------------------------------------------------
if scan_clicked:
    _crawler_session.clear()
    st.session_state.update(
        batch_running=True, stop_requested=False, pages_done_in_batch=0,
        batch_target=int(batch_size), site_error_streak=0,
    )
    state.params = params
    state.throttle = throttle.snapshot()
    try:
        state.save(STATE_FILE)
    except OSError as exc:
        st.session_state["batch_running"] = False
        st.error(f"Не удалось сохранить состояние: {exc}")
    else:
        st.rerun()

if st.session_state["batch_running"]:
    target_total = int(st.session_state.get("batch_target", int(batch_size)))
    done_in_batch = int(st.session_state.get("pages_done_in_batch", 0))
    remaining_in_batch = max(0, target_total - done_in_batch)
    target_pages = min(MICRO_BATCH, remaining_in_batch)
    batch_error = ""
    stopped_by_user = False
    processed = 0
    progress_bar = st.progress(0.0)
    status_line = st.empty()

    def _finish_batch(kind: str, message: str) -> None:
        st.session_state.update(
            batch_running=False, stop_requested=False, pages_done_in_batch=0,
            batch_target=0, site_error_streak=0,
        )
        _crawler_session.clear()
        state.throttle = throttle.snapshot()
        state.stats["pages_scanned"] = len(state.done)
        try:
            state.save(STATE_FILE)
        except OSError:
            pass
        st.session_state["_flash"] = (kind, message)
        st.rerun()

    if not speed_valid:
        _finish_batch("error", "min_delay должен быть меньше max_delay")
    if target_pages <= 0:
        _finish_batch("success", f"Батч завершён: обработано страниц — {done_in_batch}. "
                                 "Прогресс сохранён.")

    session = _crawler_session()
    done_set = set(state.done)
    known_pages = {
        _normalize_page_url(u) for u in list(state.queue) + list(state.done)
        if _normalize_page_url(u)
    }
    frozen_start_url = str(state.params.get("start_url") or start_url)

    for i in range(target_pages):
        if st.session_state.get("stop_requested"):
            stopped_by_user = True
            break

        # Настройки читаются заново на каждой странице: смена режима/слайдера
        # подхватывается после ближайшего rerun между микробатчами.
        current_mode = st.session_state.get("speed_mode", "manual")
        if current_mode == "auto":
            min_delay = float(st.session_state.get("auto_min_delay", 0.3))
            max_delay = float(st.session_state.get("auto_max_delay", 10.0))
            if min_delay >= max_delay:
                batch_error = "min_delay должен быть меньше max_delay"
                break
            throttle.min_delay, throttle.max_delay = min_delay, max_delay
            throttle.delay = min(max_delay, max(throttle.min_delay, throttle.delay))
            delay = throttle.delay
        else:
            delay = float(st.session_state.get("manual_delay", 1.5))

        page_url = next((url for url in state.queue if url not in done_set), None)
        if page_url is None:
            break

        page_started = time.perf_counter()
        internal_pages: list[str] = []
        try:
            found, status = scan_page(page_url, session, frozen_start_url,
                                      internal_out=internal_pages)
        except Exception as exc:
            batch_error = f"Ошибка на {page_url}: {exc}"
            _LOG.exception(batch_error)
            break
        elapsed = time.perf_counter() - page_started

        if internal_pages:
            added = 0
            for candidate in internal_pages:
                key = _normalize_page_url(candidate)
                if not key or key in known_pages:
                    continue
                if len(state.queue) >= MAX_FALLBACK_PAGES:
                    break
                state.queue.append(candidate)
                known_pages.add(key)
                added += 1
            if added:
                _LOG.info("Добавлено внутренних страниц вне sitemap: %d", added)

        if current_mode == "auto":
            throttle.record(elapsed, status)
            delay = throttle.delay
            st.session_state["throttle_snapshot"] = throttle.snapshot()

        try:
            append_rows(CSV_FILE, found)
            state.rows.extend(found)
            state.done.append(page_url)
            done_set.add(page_url)
            _apply_rows_to_stats(state, found)
            state.stats["last_page"] = page_url
            state.throttle = throttle.snapshot()
            state.save(STATE_FILE)
        except Exception as exc:
            batch_error = f"Ошибка сохранения после {page_url}: {exc}"
            _LOG.exception(batch_error)
            break

        if _is_server_error(status):
            st.session_state["site_error_streak"] = int(
                st.session_state.get("site_error_streak", 0)
            ) + 1
        else:
            st.session_state["site_error_streak"] = 0

        processed += 1
        _paint_progress()
        progress_bar.progress((i + 1) / target_pages)
        status_line.caption(
            f"Обработано: {i + 1}/{target_pages} | delay={delay:.2f}s | последняя: {page_url}"
        )

        if int(st.session_state.get("site_error_streak", 0)) > ERROR_STREAK_LIMIT:
            st.session_state["stop_requested"] = True
            batch_error = "Сайт не отвечает, остановите батч"
            break

        # В авто режиме delay мог вырасти после record — спим уже по новому.
        time.sleep(max(0, delay - elapsed))

    total_processed = done_in_batch + processed
    st.session_state["pages_done_in_batch"] = total_processed
    if batch_error:
        _finish_batch("error", batch_error)
    if stopped_by_user:
        _finish_batch("warning", f"Пауза: в батче обработано страниц — {total_processed}. "
                                 "Прогресс сохранён.")
    if total_processed >= target_total:
        _finish_batch("success", f"Батч завершён: обработано страниц — {total_processed}. "
                                 "Прогресс сохранён.")
    if not any(url not in done_set for url in state.queue):
        _finish_batch("success", "Все страницы из очереди просканированы. Прогресс сохранён.")

    # Микробатч закончился: перерисовать UI и забрать новые настройки.
    st.rerun()

# ---------------------------------------------------------------------------
# Проверка HTTP-статусов внешних ссылок
# ---------------------------------------------------------------------------
st.subheader("🌐 Статусы внешних ссылок")
st.caption("GET без чтения тела ответа, JS не выполняется. Проверяются только "
           "уникальные внешние URL, с паузой между запросами.")

all_links = _unique_external_links(
    state.rows or (read_csv(CSV_FILE) if Path(CSV_FILE).exists() else [])
)
checked_entries = [statuses.get(key) for key in all_links]
checked_count = sum(1 for entry in checked_entries if entry is not None)
problem_count = sum(1 for entry in checked_entries
                    if entry is not None and _status_group(entry) == "problem")
ssl_count = sum(1 for entry in checked_entries
                if entry is not None and _status_group(entry) == "ssl")
ok_count = sum(1 for entry in checked_entries
               if entry is not None and _status_group(entry) == "ok")
not_checked = max(0, len(all_links) - checked_count)

status_metrics_top = st.columns(2)
status_metrics_bottom = st.columns(2)
status_metrics_top[0].metric("Уникальных ссылок", _format_int(len(all_links)))
status_metrics_top[1].metric("Проверено", _format_int(checked_count))
status_metrics_bottom[0].metric("OK (2xx/3xx)", _format_int(ok_count))
status_metrics_bottom[1].metric("Проблемных", _format_int(problem_count))
if ssl_count:
    st.caption(f"🔓 SSL-предупреждений: {_format_int(ssl_count)} — "
               "страница доступна, но сертификат не удалось проверить.")
if all_links and checked_count == 0:
    st.info("Статусы ещё не проверялись. Нажмите «🔎 Проверить непроверенные».")
elif not_checked:
    st.caption(f"Осталось проверить: {_format_int(not_checked)}.")
legacy_blocked = sum(1 for entry in checked_entries
                     if entry and entry.get("status") in (403, 418))
if legacy_blocked:
    st.info(f"Найдено статусов 403/418: {_format_int(legacy_blocked)}. "
            "Это часто защита от ботов. Нажмите «♻️ Перепроверить ошибки» — "
            "проверка теперь использует браузерный User-Agent и GET-fallback.")
legacy_ssl = sum(
    1 for entry in checked_entries
    if entry and entry.get("status") is None
    and "certificate" in str(entry.get("error", "")).lower()
)
if legacy_ssl:
    st.info(f"Найдено сетевых ошибок с сертификатом: {_format_int(legacy_ssl)}. "
            "Нажмите «♻️ Перепроверить ошибки» — такие сайты будут проверены "
            "повторно без валидации SSL и помечены значком 🔓.")
legacy_404 = sum(
    1 for entry in checked_entries
    if entry and entry.get("status") == 404 and entry.get("method") == "HEAD"
)
if legacy_404:
    st.info(f"Найдено 404, полученных через HEAD: {_format_int(legacy_404)}. "
            "Если страница открывается в браузере, нажмите "
            "«♻️ Перепроверить ошибки» — теперь используется GET.")

link_settings = st.columns([1, 1, 2])
link_batch_size = link_settings[0].number_input(
    "Ссылок за микробатч", min_value=5, max_value=100, step=5,
    key="link_batch_size"
)
link_check_delay = link_settings[1].slider(
    "Пауза проверки, сек", 0.2, 5.0, step=0.1, key="link_check_delay"
)
link_settings[2].caption(
    f"Осталось непроверенных: **{_format_int(not_checked)}**. "
    "Кнопки ниже запускают автоматическую проверку микробатчами."
)
link_buttons_top = st.columns(2)
link_buttons_bottom = st.columns(2)
missing_clicked = link_buttons_top[0].button(
    "🔎 Проверить непроверенные", type="primary", width="stretch",
    disabled=st.session_state["link_check_running"] or not_checked == 0
    or st.session_state["batch_running"],
)
errors_clicked = link_buttons_top[1].button(
    "♻️ Перепроверить ошибки", width="stretch",
    disabled=st.session_state["link_check_running"] or (problem_count + ssl_count) == 0
    or st.session_state["batch_running"],
)
all_clicked = link_buttons_bottom[0].button(
    "🔁 Перепроверить все", width="stretch",
    disabled=st.session_state["link_check_running"] or not all_links
    or st.session_state["batch_running"],
)
pause_links_clicked = link_buttons_bottom[1].button(
    "⏸ Пауза проверки", width="stretch",
    disabled=not st.session_state["link_check_running"],
)
if missing_clicked:
    _start_link_check("missing")
if errors_clicked:
    _start_link_check("errors")
if all_clicked:
    _start_link_check("all")
if pause_links_clicked:
    st.session_state["link_check_stop"] = True
    st.info("Проверка остановится после текущего микробатча.")

if st.session_state.get("link_check_running"):
    link_queue = list(st.session_state.get("link_check_queue", []))
    link_total = max(1, int(st.session_state.get("link_check_total", 0)))
    link_done = int(st.session_state.get("link_check_processed", 0))
    link_progress = st.progress(min(1.0, link_done / link_total))
    link_status_line = st.empty()

    def _finish_link_check(kind: str, message: str) -> None:
        st.session_state.update(
            link_check_running=False, link_check_stop=False,
            link_check_queue=[], link_check_total=0, link_check_processed=0,
        )
        _link_check_session.clear()
        st.session_state["_flash"] = (kind, message)
        st.rerun()

    if st.session_state.get("link_check_stop"):
        _finish_link_check("warning", "Проверка статусов остановлена. "
                                      f"Обработано: {link_done}.")
    if not link_queue:
        _finish_link_check("success", f"Проверка завершена. Обработано ссылок: {link_done}.")

    target_links = min(int(link_batch_size), len(link_queue))
    check_session = _link_check_session()
    run_processed = 0
    save_error = ""
    for index in range(target_links):
        if st.session_state.get("link_check_stop"):
            break
        key = link_queue[index]
        started_link = time.perf_counter()
        try:
            entry = check_external_link(key, check_session)
        except Exception as exc:
            _LOG.exception("Ошибка проверки %s: %s", key, exc)
            entry = {
                "status": None, "final_url": key, "error": _squash(exc)[:300],
                "checked_at": _now_iso(), "method": "HEAD/GET",
            }
        statuses[key] = entry
        try:
            save_link_statuses(statuses)
        except OSError as exc:
            save_error = str(exc)
            break
        _LOG.info("Проверка %s | HTTP %s | SSL=%s | %.2f c",
                  key, entry.get("status"), entry.get("ssl_verified", True),
                  time.perf_counter() - started_link)
        run_processed += 1
        current_done = link_done + run_processed
        link_progress.progress(min(1.0, current_done / link_total))
        link_status_line.caption(
            f"Проверено: {current_done}/{link_total} | {_status_label(entry)} | {key}"
        )
        wait = float(st.session_state.get("link_check_delay", LINK_DEFAULT_DELAY))
        if entry.get("status") in (429, 503):
            wait = max(wait, 2.0)
        time.sleep(max(0, wait - (time.perf_counter() - started_link)))

    st.session_state["link_check_queue"] = link_queue[run_processed:]
    st.session_state["link_check_processed"] = link_done + run_processed
    if save_error:
        _finish_link_check("error", f"Не удалось сохранить статусы: {save_error}")
    if st.session_state.get("link_check_stop"):
        _finish_link_check("warning", "Проверка статусов остановлена. "
                                      f"Обработано: {link_done + run_processed}.")
    if not st.session_state["link_check_queue"]:
        _finish_link_check("success", "Проверка статусов завершена. "
                                      f"Обработано ссылок: {link_done + run_processed}.")
    st.rerun()

# ---------------------------------------------------------------------------
# Статистика и таблица
# ---------------------------------------------------------------------------
st.subheader("📊 Статистика")
stats = state.stats
metric_top = st.columns(2)
metric_bottom = st.columns(2)
metric_top[0].metric("Внешних ссылок", _format_int(stats.get("links_found", 0)))
metric_top[1].metric("Уникальных доменов", _format_int(stats.get("unique_domains", 0)))
metric_bottom[0].metric("nofollow", _format_int(stats.get("nofollow", 0)))
metric_bottom[1].metric("Без анкора", _format_int(stats.get("no_anchor", 0)))

st.subheader("📋 Таблица внешних ссылок")
csv_path = Path(CSV_FILE)
csv_exists = csv_path.exists()
csv_size = csv_path.stat().st_size if csv_exists else 0
limit = 1000 if csv_size > 50 * 1024 * 1024 else None
if limit:
    st.warning("CSV больше 50 МБ. Для скорости показаны только первые 1000 строк; "
               "полные данные доступны в Excel и CSV.")
csv_mtime = csv_path.stat().st_mtime_ns if csv_exists else 0
table_rows = _read_csv_cached(str(csv_path), csv_mtime, limit) if csv_exists else []

if not table_rows:
    st.info("Данных пока нет. Соберите sitemap и просканируйте один или несколько батчей.")
    filtered = []
else:
    enriched_rows = []
    for row in table_rows:
        entry = statuses.get(_status_key(row.get("href", "")))
        enriched = dict(row)
        enriched.update(_status_values(row.get("href", ""), statuses))
        enriched["_status_entry"] = entry
        enriched["status_short"] = _status_short(entry)
        enriched_rows.append(enriched)

    domains = sorted({row["domain"] for row in enriched_rows if row.get("domain")})
    rels = sorted({row["rel"] for row in enriched_rows if row.get("rel")})
    status_options = sorted({row["status_short"] for row in enriched_rows})
    filter_top = st.columns(2)
    filter_bottom = st.columns(2)
    selected_domains = filter_top[0].multiselect(
        "Домен", options=domains, placeholder="Все домены"
    )
    selected_rels = filter_top[1].multiselect(
        "rel", options=rels, placeholder="Все rel"
    )
    selected_statuses = filter_bottom[0].multiselect(
        "HTTP-статус", options=status_options, placeholder="Все статусы"
    )
    query = filter_bottom[1].text_input(
        "Поиск по анкору, URL или ошибке",
        placeholder="Анкор, URL, финальный URL или ошибка",
    ).strip().casefold()
    problem_only = st.checkbox("Показывать только проблемные (4xx/5xx/сеть)",
                               value=False)
    filtered = []
    for row in enriched_rows:
        if selected_domains and row.get("domain") not in selected_domains:
            continue
        if selected_rels and row.get("rel") not in selected_rels:
            continue
        if selected_statuses and row.get("status_short") not in selected_statuses:
            continue
        if problem_only:
            entry = row.get("_status_entry")
            if entry is None or _status_group(entry) != "problem":
                continue
        if query and query not in " ".join((
            row.get("anchor", ""), row.get("href", ""), row.get("page_url", ""),
            row.get("page_title", ""), row.get("status_label", ""),
            row.get("final_url", ""), row.get("error", ""),
        )).casefold():
            continue
        filtered.append(row)
    page_size = st.number_input("Строк на странице", 25, 500, 100, 25)
    max_page = max(0, (len(filtered) - 1) // int(page_size)) if filtered else 0
    current_page = min(int(st.session_state.get("table_page", 0)), max_page)
    st.session_state["table_page"] = current_page
    nav = st.columns([1, 1, 4])
    if nav[0].button("← Назад", disabled=current_page <= 0, width="stretch"):
        st.session_state["table_page"] = current_page - 1
        st.rerun()
    if nav[1].button("Вперёд →", disabled=current_page >= max_page, width="stretch"):
        st.session_state["table_page"] = current_page + 1
        st.rerun()
    nav[2].caption(f"Страница {current_page + 1} из {max_page + 1} · "
                   f"найдено строк: {_format_int(len(filtered))}")
    page_rows = filtered[current_page * int(page_size):(current_page + 1) * int(page_size)]
    if page_rows:
        columns = ["page_url", "status_short", "href", "domain",
                   "anchor", "page_title"]
        frame = pd.DataFrame(page_rows).reindex(columns=columns, fill_value="")
        frame = frame.rename(columns={
            "page_url": "Страница (URL)", "page_title": "Заголовок страницы",
            "anchor": "Текст анкора", "href": "Внешний URL", "domain": "Домен",
            "status_short": "Статус",
        })
        st.dataframe(
            frame, width="stretch", hide_index=True, column_config={
                "Страница (URL)": st.column_config.LinkColumn("Страница (URL)"),
                "Статус": st.column_config.TextColumn("Статус", width="medium"),
                "Внешний URL": st.column_config.LinkColumn("Внешний URL"),
                "Домен": st.column_config.TextColumn("Домен", width="small"),
            }
        )
        st.caption("Финальный URL, rel, target, контекст и текст ошибки "
                   "доступны в Excel и CSV.")
    else:
        st.info("По выбранным фильтрам ничего не найдено. Измените условия поиска.")

# ---------------------------------------------------------------------------
# Скачивание
# ---------------------------------------------------------------------------
st.subheader("📥 Отчёты")
download_cols = st.columns(2)
csv_mtime = csv_path.stat().st_mtime_ns if csv_path.exists() else 0
state_path = Path(STATE_FILE)
state_mtime = state_path.stat().st_mtime_ns if state_path.exists() else 0
status_path = Path(LINK_STATUS_FILE)
status_mtime = status_path.stat().st_mtime_ns if status_path.exists() else 0
report_rows = state.rows or (read_csv(str(csv_path)) if csv_path.exists() else [])
with download_cols[0]:
    if csv_path.exists() and csv_path.stat().st_size > 0:
        try:
            excel_bytes = _excel_cached(str(csv_path), csv_mtime, state_mtime, status_mtime)
        except Exception as exc:
            _LOG.exception("Ошибка формирования Excel: %s", exc)
            st.error(f"Не удалось сформировать Excel: {exc}")
        else:
            st.download_button("💾 Скачать Excel", data=excel_bytes,
                               file_name="external_links.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               width="stretch")
    else:
        st.button("💾 Скачать Excel", disabled=True, width="stretch")
with download_cols[1]:
    if report_rows:
        try:
            csv_bytes = build_csv_bytes(report_rows, statuses)
        except Exception as exc:
            st.error(f"Не удалось сформировать CSV: {exc}")
        else:
            st.download_button("💾 Скачать CSV со статусами", data=csv_bytes,
                               file_name="external_links.csv", mime="text/csv",
                               width="stretch")
    else:
        st.button("💾 Скачать CSV со статусами", disabled=True, width="stretch")
st.caption("В Excel 5 листов: все ссылки, сводка по доменам, проблемные, "
           "статусы ссылок и метаданные. CSV также содержит статусы.")

# ---------------------------------------------------------------------------
# Лог
# ---------------------------------------------------------------------------
with st.expander("📜 Лог (последние 20 строк)"):
    st.code(_tail(LOG_FILE, 20) or "Лог пока пуст.", language=None)

