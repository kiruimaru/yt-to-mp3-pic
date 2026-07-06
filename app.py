#!/usr/bin/env python3
"""
YouTube -> MP3 + обложка. Простой графический интерфейс.

Окно на tkinter (входит в стандартную поставку Python):
  - поле для вставки URL видео
  - кнопка выбора папки для сохранения
  - выбор битрейта MP3
  - кнопка "Скачать" и индикатор прогресса
  - лог того, что происходит

Скачивание идёт в отдельном потоке, поэтому окно не зависает.

Требования:
    pip install -r requirements.txt
    (ffmpeg подтягивается автоматически через пакет imageio-ffmpeg)

Запуск:
    python app.py
"""

import queue
import tempfile
import shutil
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import yt_dlp
except ImportError:
    raise SystemExit(
        "Не найден модуль yt-dlp. Установите его командой:\n"
        "    pip install yt-dlp"
    )


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


class DownloaderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("YouTube -> MP3")
        self.root.geometry("640x460")
        self.root.minsize(560, 420)

        # Очередь для сообщений из рабочего потока в интерфейс.
        self.msg_queue = queue.Queue()
        self.is_downloading = False

        self._build_ui()
        self._poll_queue()

    # ---------- построение интерфейса ----------
    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}
        frm = ttk.Frame(self.root, padding=16)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        # URL
        ttk.Label(frm, text="Ссылка на видео:").grid(row=0, column=0, sticky="w", **pad)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(frm, textvariable=self.url_var)
        url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", **pad)
        url_entry.focus()

        # Папка
        ttk.Label(frm, text="Папка для сохранения:").grid(row=1, column=0, sticky="w", **pad)
        self.dir_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        ttk.Entry(frm, textvariable=self.dir_var).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(frm, text="Обзор...", command=self._choose_dir).grid(row=1, column=2, **pad)

        # Битрейт
        ttk.Label(frm, text="Качество (kbps):").grid(row=2, column=0, sticky="w", **pad)
        self.quality_var = tk.StringVar(value="192")
        ttk.Combobox(
            frm,
            textvariable=self.quality_var,
            values=["128", "192", "256", "320"],
            state="readonly",
            width=8,
        ).grid(row=2, column=1, sticky="w", **pad)

        # Кнопка скачивания
        self.download_btn = ttk.Button(frm, text="Скачать", command=self._start_download)
        self.download_btn.grid(row=3, column=0, columnspan=3, sticky="ew", **pad)

        # Прогресс
        self.progress = ttk.Progressbar(frm, mode="determinate", maximum=100)
        self.progress.grid(row=4, column=0, columnspan=3, sticky="ew", **pad)

        # Лог
        ttk.Label(frm, text="Ход выполнения:").grid(row=5, column=0, sticky="w", **pad)
        self.log = tk.Text(frm, height=10, wrap="word", state="disabled")
        self.log.grid(row=6, column=0, columnspan=3, sticky="nsew", **pad)
        frm.rowconfigure(6, weight=1)

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
            messagebox.showwarning("Нет ссылки", "Вставьте ссылку на видео.")
            return
        if not out_dir:
            messagebox.showwarning("Нет папки", "Выберите папку для сохранения.")
            return

        ffmpeg_dir = find_ffmpeg()
        if ffmpeg_dir is None:
            messagebox.showerror(
                "Нет ffmpeg",
                "Не найден ffmpeg — он нужен для конвертации в MP3.\n\n"
                "Проще всего установить его вместе с зависимостями:\n"
                "    pip install -r requirements.txt\n\n"
                "Либо вручную:\n"
                "Windows: скачайте с gyan.dev/ffmpeg и добавьте в PATH.\n"
                "macOS: brew install ffmpeg\n"
                "Linux: sudo apt install ffmpeg",
            )
            return

        Path(out_dir).mkdir(parents=True, exist_ok=True)

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="Скачивание...")
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
                self.msg_queue.put(("log", "Загрузка завершена, конвертирую в MP3..."))
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
                title = info.get("title", "видео")
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
                    self._log(f"Готово: {title}")
                    self._log(f"Файлы сохранены в: {out_dir}")
                    self._finish()
                    messagebox.showinfo("Готово", f"Скачано и сохранено:\n{title}")
                elif kind == "error":
                    self._log(f"Ошибка: {msg[1]}")
                    self._finish()
                    messagebox.showerror("Ошибка", msg[1])
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_queue)

    def _finish(self) -> None:
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="Скачать")


def main() -> None:
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
