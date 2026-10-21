#!/usr/bin/env python3
"""
YouTube -> MP3 + обложка (версия для командной строки).

Пользователь вводит URL видео (или передаёт его аргументом), а программа:
  1. Скачивает лучший доступный звук с YouTube.
  2. Конвертирует его в MP3 (через ffmpeg).
  3. Сохраняет обложку видео в отдельный файл.
  4. Встраивает обложку и метаданные (название, автор) в сам MP3.

Требования:
    pip install -r requirements.txt
    (ffmpeg подтягивается автоматически через пакет imageio-ffmpeg)

Примеры запуска:
    python youtube_to_mp3.py
    python youtube_to_mp3.py "https://www.youtube.com/watch?v=XXXX"
    python youtube_to_mp3.py "https://youtu.be/XXXX" -o ./музыка -q 320
"""

import argparse
import importlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def ensure_deps() -> None:
    """
    Проверяем, что нужные пакеты установлены. Чего нет — ставим через pip
    в текущее окружение. Так вручную ничего докачивать не нужно.
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
        sys.exit(
            "Не удалось установить зависимости автоматически.\n"
            f"Попробуйте вручную:\n    {sys.executable} -m pip install "
            + " ".join(missing)
            + f"\n\nОшибка: {e}"
        )
    importlib.invalidate_caches()


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
    Если ffmpeg найти не удалось — завершаем работу с подсказкой.
    """
    exe = shutil.which("ffmpeg")
    if exe:
        return str(Path(exe).parent)
    try:
        import imageio_ffmpeg

        src = Path(imageio_ffmpeg.get_ffmpeg_exe())
        target_name = "ffmpeg.exe" if src.suffix.lower() == ".exe" else "ffmpeg"
        dest_dir = Path(tempfile.gettempdir()) / "yt2mp3_ffmpeg"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / target_name
        if not dest.exists():
            shutil.copy2(src, dest)
        return str(dest_dir)
    except Exception:  # noqa: BLE001
        sys.exit(
            "Не найден ffmpeg. Он нужен для конвертации в MP3.\n"
            "Проще всего: pip install -r requirements.txt\n"
            "  - Windows: скачайте с https://www.gyan.dev/ffmpeg/builds/ и добавьте в PATH\n"
            "  - macOS:   brew install ffmpeg\n"
            "  - Linux:   sudo apt install ffmpeg"
        )


def build_options(output_dir: Path, quality: str, ffmpeg_dir: str) -> dict:
    """Формируем настройки yt-dlp с обходом блокировок YouTube."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return {
        # Берём лучший звук.
        "format": "bestaudio/best",
        # Шаблон имени: название видео.
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        # Путь к ffmpeg (найден автоматически).
        "ffmpeg_location": ffmpeg_dir,
        # Скачиваем обложку отдельным файлом.
        "writethumbnail": True,
        # Обход блокировок 403
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
                "player_skip": ["webpage", "configs"],
            }
        },
        # User-Agent для обхода блокировок
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        "postprocessors": [
            # 1. Конвертируем звук в MP3.
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            },
            # 2. Готовим обложку (jpg) для встраивания.
            {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
            # 3. Встраиваем обложку в MP3.
            {"key": "EmbedThumbnail"},
            # 4. Добавляем метаданные (название, автор и т.д.).
            {"key": "FFmpegMetadata"},
        ],
        "quiet": False,
        "no_warnings": False,
    }


def download(url: str, output_dir: Path, quality: str, ffmpeg_dir: str) -> None:
    """Скачиваем видео, конвертируем в MP3 и сохраняем обложку."""
    opts = build_options(output_dir, quality, ffmpeg_dir)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "видео")

    # Ищем итоговые файлы, чтобы показать их пользователю.
    mp3_files = sorted(output_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
    thumbs = sorted(
        [p for ext in ("*.jpg", "*.png", "*.webp") for p in output_dir.glob(ext)],
        key=lambda p: p.stat().st_mtime,
    )

    print("\n" + "=" * 50)
    print(f"Готово: {title}")
    if mp3_files:
        print(f"  MP3:     {mp3_files[-1]}")
    if thumbs:
        print(f"  Обложка: {thumbs[-1]}")
    print("=" * 50)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Скачивает видео с YouTube, делает MP3 и сохраняет обложку."
    )
    parser.add_argument("url", nargs="?", help="URL видео на YouTube")
    parser.add_argument(
        "-o",
        "--output",
        default="downloads",
        help="Папка для сохранения (по умолчанию: ./downloads)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        default="192",
        help="Битрейт MP3 в kbps (по умолчанию: 192)",
    )
    args = parser.parse_args()

    ffmpeg_dir = find_ffmpeg()

    url = args.url or input("Введите URL видео с YouTube: ").strip()
    if not url:
        sys.exit("URL не введён. Выход.")

    output_dir = Path(args.output).expanduser().resolve()

    try:
        download(url, output_dir, args.quality, ffmpeg_dir)
    except yt_dlp.utils.DownloadError as e:
        sys.exit(f"Ошибка скачивания: {e}")
    except KeyboardInterrupt:
        sys.exit("\nПрервано пользователем.")


if __name__ == "__main__":
    main()
