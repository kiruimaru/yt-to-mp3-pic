![YouTube to MP3 Banner](https://capsule-render.vercel.app/api?type=waving&height=250&color=0:0d1117,100:161b22&text=YouTube%20→%20MP3&fontSize=75&fontColor=58a6ff&animation=fadeIn&desc=Download%20music%20with%20cover%20art%20|%20Cross-platform&descSize=18&descAlignY=70)

<img width="642" height="572" alt="image" src="https://github.com/user-attachments/assets/331114e5-b624-4d9d-b771-dfba6453fbe4" />


# YouTube → MP3

Скачивает аудио с **YouTube** и **SoundCloud**, конвертирует в MP3 и сохраняет обложку.
Обложка и метаданные (название, автор) встраиваются прямо в MP3.
Интерфейс — в тёмной теме, с переключателем языка RU / EN и выбором источника.

**Кроссплатформенно:** Windows, Linux, macOS

## ⚡ Для обычного пользователя

### Windows
Скачайте `YouTube-to-MP3.exe` из [Releases](../../releases) и запустите двойным кликом.
Всё включено: Python, ffmpeg, зависимости — ничего устанавливать не нужно.

### Linux / macOS
```bash
./run.sh
```
Первый запуск установит зависимости автоматически.

## 🔧 Для разработчика

### Что внутри

- `app.py` — графическое приложение (тёмная тема, поле URL, выбор папки и битрейта)
- `youtube_to_mp3.py` — версия для командной строки
- **Windows:** `Запустить.bat`, `Собрать-EXE.bat`
- **Linux/macOS:** `run.sh`, `run_cli.sh`

### Запуск из исходников

Нужен только **Python 3.8+**. Зависимости устанавливаются автоматически.

**Windows:**
```cmd
Запустить.bat
```
или
```cmd
python app.py
```

**Linux / macOS:**
```bash
./run.sh
```
или
```bash
python3 app.py
```

### CLI версия

**Windows:**
```cmd
python youtube_to_mp3.py "https://youtu.be/XXXX" -o ./музыка -q 320
```

**Linux / macOS:**
```bash
./run_cli.sh "https://youtu.be/XXXX" -o ./музыка -q 320
```

### Сборка исполняемых файлов

**Windows (.exe):**
```cmd
Собрать-EXE.bat
```
Готовый `YouTube-to-MP3.exe` появится в папке `dist/`.

**Linux (AppImage, coming soon):**
Планируется добавить сборку AppImage для Linux.

## 🆕 Что нового в v2.0

- ✅ **Исправлена ошибка 403** — обновлен yt-dlp и добавлен обход блокировок YouTube
- ✅ **Поддержка Linux/macOS** — добавлены shell скрипты для запуска
- ✅ **Улучшенный дизайн** — современная тёмная тема (GitHub Dark inspired)
- ✅ **Кроссплатформенность** — работает на Windows, Linux, macOS
- ✅ **Автоматическая установка зависимостей** — просто запустите скрипт

## 📋 Требования

- Python 3.8+ (для запуска из исходников)
- Linux: `sudo apt install python3-tk ffmpeg` (опционально, для системного ffmpeg)
- macOS: `brew install ffmpeg` (опционально)

## 📝 Лицензия

MIT — пользуйтесь свободно, в том числе в коммерческих целях.

## ⚠️ Замечание

Скачивайте только тот контент, на который у вас есть права или разрешение автора.
