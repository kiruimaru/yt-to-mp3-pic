#!/usr/bin/env python3
"""
YouTube -> MP3 + обложка. Простой графический интерфейс (тёмная тема).

Окно на tkinter (входит в стандартную поставку Python):
  - поле для вставки URL видео
  - кнопка выбора папки для сохранения
  - выбор битрейта MP3
  - переключатель языка интерфейса (RU / EN)
  - кнопка "Скачать" и индикатор прогресса
  - лог того, что происходит

Скачивание идёт в отдельном потоке, поэтому окно не зависает.

Зависимости (yt-dlp, imageio-ffmpeg) при первом запуске
доустанавливаются автоматически — вручную ничего делать не нужно.

Запуск:
    python app.py
"""

import importlib
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ---------- автоматическая установка зависимостей ----------
def ensure_deps() -> None:
    """
    Проверяем, что нужные пакеты установлены. Чего нет — ставим через pip
    в текущее окружение. Так пользователю не нужно вручную ничего докачивать.
    Пары (имя пакета для pip, имя модуля для импорта).
    """
    required = [
        ("yt-dlp", "yt_dlp"),
        ("imageio-ffmpeg", "imageio_ffmpeg"),
    ]
    missing = []
    for pip_name, module_name in required:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return

    print(f"Устанавливаю недостающие пакеты: {', '.join(missing)} ...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", *missing]
        )
    except subprocess.CalledProcessError as e:
        raise SystemExit(
            "Не удалось установить зависимости автоматически.\n"
            f"Попробуйте вручную:\n    {sys.executable} -m pip install "
            + " ".join(missing)
            + f"\n\nОшибка: {e}"
        )
    # Сбрасываем кэш импортов, чтобы свежеустановленные пакеты стали видны.
    importlib.invalidate_caches()


# Внутри собранного .exe зависимости уже упакованы, а pip недоступен —
# поэтому авто-установку запускаем только при обычном запуске из исходников.
if not getattr(sys, "frozen", False):
    ensure_deps()

import yt_dlp  # noqa: E402 — импортируем уже после установки


def find_ffmpeg():
    """
    Возвращаем путь к папке, где лежит ffmpeg с именем, понятным yt-dlp.
    Порядок поиска:
      1. Системный ffmpeg из PATH.
      2. Бинарник из пакета imageio-ffmpeg. Он называется не "ffmpeg",
         поэтому копируем его под именем ffmpeg.exe в отдельную папку —
         иначе yt-dlp его не находит.
    None — если ffmpeg найти не удалось.
    """
    exe = shutil.which("ffmpeg")
    if exe:
        return str(Path(exe).parent)
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    src = Path(imageio_ffmpeg.get_ffmpeg_exe())
    if not src.exists():
        return None
    target_name = "ffmpeg.exe" if src.suffix.lower() == ".exe" else "ffmpeg"
    dest_dir = Path(tempfile.gettempdir()) / "yt2mp3_ffmpeg"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / target_name
    if not dest.exists():
        shutil.copy2(src, dest)
    return str(dest_dir)


# ---------- палитра тёмной темы ----------
DARK = {
    "bg": "#1e1e2e",        # фон окна
    "surface": "#282a3a",   # фон полей ввода
    "fg": "#e4e4ef",        # основной текст
    "muted": "#a6adc8",     # приглушённый текст
    "accent": "#89b4fa",    # акцент (кнопка, прогресс)
    "accent_hi": "#a6c8ff", # акцент при наведении
    "border": "#45475a",    # рамки
}


# ---------- тексты интерфейса на двух языках ----------
TEXTS = {
    "ru": {
        "title": "YouTube -> MP3",
        "lang_label": "Язык:",
        "source_label": "Источник:",
        "url_label": "Ссылка на видео:",
        "url_hint_youtube": "Вставьте ссылку на видео YouTube",
        "url_hint_soundcloud": "Вставьте ссылку на трек SoundCloud",
        "dir_label": "Папка для сохранения:",
        "browse": "Обзор...",
        "quality_label": "Качество (kbps):",
        "download": "Скачать",
        "downloading": "Скачивание...",
        "progress_label": "Ход выполнения:",
        "no_url_title": "Нет ссылки",
        "no_url_msg": "Вставьте ссылку на видео.",
        "wrong_source_title": "Проверьте источник",
        "wrong_source_msg": "Похоже, ссылка не от {source}. Всё равно попробовать скачать?",
        "no_dir_title": "Нет папки",
        "no_dir_msg": "Выберите папку для сохранения.",
        "no_ffmpeg_title": "Нет ffmpeg",
        "no_ffmpeg_msg": (
            "Не найден ffmpeg — он нужен для конвертации в MP3.\n\n"
            "Обычно он ставится автоматически вместе с зависимостями.\n"
            "Если нет — установите вручную:\n"
            "    pip install imageio-ffmpeg\n\n"
            "Либо системный ffmpeg:\n"
            "Windows: скачайте с gyan.dev/ffmpeg и добавьте в PATH.\n"
            "macOS: brew install ffmpeg\n"
            "Linux: sudo apt install ffmpeg"
        ),
        "converting": "Загрузка завершена, конвертирую в MP3...",
        "done_log": "Готово: {title}",
        "saved_to": "Файлы сохранены в: {dir}",
        "done_title": "Готово",
        "done_msg": "Скачано и сохранено:\n{title}",
        "error_log": "Ошибка: {msg}",
        "error_title": "Ошибка",
        "video_word": "видео",
    },
    "en": {
        "title": "YouTube -> MP3",
        "lang_label": "Language:",
        "source_label": "Source:",
        "url_label": "Video URL:",
        "url_hint_youtube": "Paste a YouTube video URL",
        "url_hint_soundcloud": "Paste a SoundCloud track URL",
        "dir_label": "Save to folder:",
        "browse": "Browse...",
        "quality_label": "Quality (kbps):",
        "download": "Download",
        "downloading": "Downloading...",
        "progress_label": "Progress:",
        "no_url_title": "No link",
        "no_url_msg": "Paste a video URL.",
        "wrong_source_title": "Check the source",
        "wrong_source_msg": "This link does not look like a {source} link. Try downloading anyway?",
        "no_dir_title": "No folder",
        "no_dir_msg": "Choose a folder to save to.",
        "no_ffmpeg_title": "ffmpeg not found",
        "no_ffmpeg_msg": (
            "ffmpeg was not found — it is required to convert to MP3.\n\n"
            "It normally installs automatically with the dependencies.\n"
            "If not, install it manually:\n"
            "    pip install imageio-ffmpeg\n\n"
            "Or a system ffmpeg:\n"
            "Windows: download from gyan.dev/ffmpeg and add it to PATH.\n"
            "macOS: brew install ffmpeg\n"
            "Linux: sudo apt install ffmpeg"
        ),
        "converting": "Download finished, converting to MP3...",
        "done_log": "Done: {title}",
        "saved_to": "Files saved to: {dir}",
        "done_title": "Done",
        "done_msg": "Downloaded and saved:\n{title}",
        "error_log": "Error: {msg}",
        "error_title": "Error",
        "video_word": "video",
    },
}


def apply_dark_theme(root: tk.Tk) -> None:
    """Настраиваем тёмную тему для ttk-виджетов на основе темы 'clam'."""
    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=DARK["bg"])

    style.configure(".", background=DARK["bg"], foreground=DARK["fg"],
                    fieldbackground=DARK["surface"], bordercolor=DARK["border"])
    style.configure("TFrame", background=DARK["bg"])
    style.configure("TLabel", background=DARK["bg"], foreground=DARK["fg"])

    # Поля ввода
    style.configure("TEntry", fieldbackground=DARK["surface"],
                    foreground=DARK["fg"], insertcolor=DARK["fg"],
                    bordercolor=DARK["border"], lightcolor=DARK["border"],
                    darkcolor=DARK["border"])

    # Выпадающий список
    style.configure("TCombobox", fieldbackground=DARK["surface"],
                    background=DARK["surface"], foreground=DARK["fg"],
                    arrowcolor=DARK["fg"], bordercolor=DARK["border"])
    style.map("TCombobox",
              fieldbackground=[("readonly", DARK["surface"])],
              foreground=[("readonly", DARK["fg"])])
    root.option_add("*TCombobox*Listbox.background", DARK["surface"])
    root.option_add("*TCombobox*Listbox.foreground", DARK["fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", DARK["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", DARK["bg"])

    # Кнопки
    style.configure("TButton", background=DARK["surface"],
                    foreground=DARK["fg"], bordercolor=DARK["border"],
                    focuscolor=DARK["bg"], padding=6)
    style.map("TButton",
              background=[("active", DARK["border"]),
                          ("disabled", DARK["bg"])],
              foreground=[("disabled", DARK["muted"])])

    # Акцентная кнопка "Скачать"
    style.configure("Accent.TButton", background=DARK["accent"],
                    foreground=DARK["bg"], padding=8)
    style.map("Accent.TButton",
              background=[("active", DARK["accent_hi"]),
                          ("disabled", DARK["border"])],
              foreground=[("disabled", DARK["muted"])])

    # Прогресс-бар
    style.configure("Horizontal.TProgressbar",
                    background=DARK["accent"], troughcolor=DARK["surface"],
                    bordercolor=DARK["border"], lightcolor=DARK["accent"],
                    darkcolor=DARK["accent"])


class DownloaderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.lang = "ru"  # язык по умолчанию

        self.root.geometry("640x540")
        self.root.minsize(560, 500)

        apply_dark_theme(self.root)

        # Очередь для сообщений из рабочего потока в интерфейс.
        self.msg_queue = queue.Queue()
        self.is_downloading = False

        self._build_ui()
        self._apply_language()
        self._poll_queue()

    def t(self, key: str) -> str:
        """Короткий доступ к тексту на текущем языке."""
        return TEXTS[self.lang][key]

    # ---------- построение интерфейса ----------
    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}
        frm = ttk.Frame(self.root, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        # Переключатель языка (верхний правый угол)
        self.lang_label = ttk.Label(frm)
        self.lang_label.grid(row=0, column=0, sticky="w", **pad)
        self.lang_var = tk.StringVar(value="Русский")
        self.lang_combo = ttk.Combobox(
            frm,
            textvariable=self.lang_var,
            values=["Русский", "English"],
            state="readonly",
            width=12,
        )
        self.lang_combo.grid(row=0, column=2, sticky="e", **pad)
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_language_change)

        # Источник (YouTube / SoundCloud)
        self.source_label = ttk.Label(frm)
        self.source_label.grid(row=1, column=0, sticky="w", **pad)
        self.source_var = tk.StringVar(value="YouTube")
        self.source_combo = ttk.Combobox(
            frm,
            textvariable=self.source_var,
            values=["YouTube", "SoundCloud"],
            state="readonly",
            width=14,
        )
        self.source_combo.grid(row=1, column=1, sticky="w", **pad)
        self.source_combo.bind("<<ComboboxSelected>>", self._on_source_change)

        # URL
        self.url_label = ttk.Label(frm)
        self.url_label.grid(row=2, column=0, sticky="w", **pad)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(frm, textvariable=self.url_var)
        url_entry.grid(row=2, column=1, columnspan=2, sticky="ew", **pad)
        url_entry.focus()

        # Папка
        self.dir_label = ttk.Label(frm)
        self.dir_label.grid(row=3, column=0, sticky="w", **pad)
        self.dir_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        ttk.Entry(frm, textvariable=self.dir_var).grid(row=3, column=1, sticky="ew", **pad)
        self.browse_btn = ttk.Button(frm, command=self._choose_dir)
        self.browse_btn.grid(row=3, column=2, **pad)

        # Битрейт
        self.quality_label = ttk.Label(frm)
        self.quality_label.grid(row=4, column=0, sticky="w", **pad)
        self.quality_var = tk.StringVar(value="192")
        ttk.Combobox(
            frm,
            textvariable=self.quality_var,
            values=["128", "192", "256", "320"],
            state="readonly",
            width=8,
        ).grid(row=4, column=1, sticky="w", **pad)

        # Кнопка скачивания
        self.download_btn = ttk.Button(
            frm, style="Accent.TButton", command=self._start_download
        )
        self.download_btn.grid(row=5, column=0, columnspan=3, sticky="ew", **pad)

        # Прогресс
        self.progress = ttk.Progressbar(frm, mode="determinate", maximum=100)
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", **pad)

        # Лог
        self.progress_label = ttk.Label(frm)
        self.progress_label.grid(row=7, column=0, sticky="w", **pad)
        self.log = tk.Text(
            frm, height=10, wrap="word", state="disabled",
            bg=DARK["surface"], fg=DARK["fg"], insertbackground=DARK["fg"],
            relief="flat", borderwidth=8, highlightthickness=1,
            highlightbackground=DARK["border"], highlightcolor=DARK["border"],
        )
        self.log.grid(row=8, column=0, columnspan=3, sticky="nsew", **pad)
        frm.rowconfigure(8, weight=1)

    # ---------- переключение языка ----------
    def _on_language_change(self, event=None) -> None:
        self.lang = "en" if self.lang_var.get() == "English" else "ru"
        self._apply_language()

    def _on_source_change(self, event=None) -> None:
        """Меняем подсказку в поле URL под выбранный источник."""
        self._apply_language()

    def _apply_language(self) -> None:
        """Обновляем все подписи под текущий язык."""
        self.root.title(self.t("title"))
        self.lang_label.configure(text=self.t("lang_label"))
        self.source_label.configure(text=self.t("source_label"))
        # Подпись поля URL зависит от выбранного источника.
        if self.source_var.get() == "SoundCloud":
            self.url_label.configure(text=self.t("url_hint_soundcloud"))
        else:
            self.url_label.configure(text=self.t("url_hint_youtube"))
        self.dir_label.configure(text=self.t("dir_label"))
        self.browse_btn.configure(text=self.t("browse"))
        self.quality_label.configure(text=self.t("quality_label"))
        self.progress_label.configure(text=self.t("progress_label"))
        # Кнопку скачивания не трогаем во время загрузки, чтобы не сбить статус.
        if not self.is_downloading:
            self.download_btn.configure(text=self.t("download"))

    # ---------- вспомогательные действия ----------
    def _choose_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.dir_var.get() or str(Path.home()))
        if chosen:
            self.dir_var.set(chosen)

    def _log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # ---------- запуск скачивания ----------
    def _start_download(self) -> None:
        if self.is_downloading:
            return

        url = self.url_var.get().strip()
        out_dir = self.dir_var.get().strip()

        if not url:
            messagebox.showwarning(self.t("no_url_title"), self.t("no_url_msg"))
            return
        if not out_dir:
            messagebox.showwarning(self.t("no_dir_title"), self.t("no_dir_msg"))
            return

        # Мягкая проверка: ссылка похожа на выбранный источник?
        source = self.source_var.get()
        low = url.lower()
        looks_ok = (
            (source == "YouTube" and ("youtube.com" in low or "youtu.be" in low))
            or (source == "SoundCloud" and "soundcloud.com" in low)
        )
        if not looks_ok:
            proceed = messagebox.askyesno(
                self.t("wrong_source_title"),
                self.t("wrong_source_msg").format(source=source),
            )
            if not proceed:
                return

        ffmpeg_dir = find_ffmpeg()
        if ffmpeg_dir is None:
            messagebox.showerror(self.t("no_ffmpeg_title"), self.t("no_ffmpeg_msg"))
            return

        Path(out_dir).mkdir(parents=True, exist_ok=True)

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text=self.t("downloading"))
        self.progress["value"] = 0

        worker = threading.Thread(
            target=self._download_worker,
            args=(url, out_dir, self.quality_var.get(), ffmpeg_dir),
            daemon=True,
        )
        worker.start()

    def _download_worker(self, url: str, out_dir: str, quality: str, ffmpeg_dir: str) -> None:
        """Выполняется в отдельном потоке. Общение с интерфейсом — через очередь."""

        def hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    pct = downloaded / total * 100
                    self.msg_queue.put(("progress", pct))
            elif d["status"] == "finished":
                self.msg_queue.put(("log", self.t("converting")))
                self.msg_queue.put(("progress", 100))

        opts = {
            "format": "bestaudio/best",
            "outtmpl": str(Path(out_dir) / "%(title)s.%(ext)s"),
            "writethumbnail": True,
            "progress_hooks": [hook],
            "quiet": True,
            "no_warnings": True,
            "ffmpeg_location": ffmpeg_dir,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                },
                {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
                {"key": "EmbedThumbnail"},
                {"key": "FFmpegMetadata"},
            ],
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", self.t("video_word"))
            self.msg_queue.put(("done", title, out_dir))
        except Exception as e:  # noqa: BLE001 — показываем любую ошибку пользователю
            self.msg_queue.put(("error", str(e)))

    # ---------- обработка сообщений из потока ----------
    def _poll_queue(self) -> None:
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    self.progress["value"] = msg[1]
                elif kind == "log":
                    self._log(msg[1])
                elif kind == "done":
                    _, title, out_dir = msg
                    self._log(self.t("done_log").format(title=title))
                    self._log(self.t("saved_to").format(dir=out_dir))
                    self._finish()
                    messagebox.showinfo(
                        self.t("done_title"),
                        self.t("done_msg").format(title=title),
                    )
                elif kind == "error":
                    self._log(self.t("error_log").format(msg=msg[1]))
                    self._finish()
                    messagebox.showerror(self.t("error_title"), msg[1])
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_queue)

    def _finish(self) -> None:
        self.is_downloading = False
        self.download_btn.configure(state="normal", text=self.t("download"))


def main() -> None:
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
