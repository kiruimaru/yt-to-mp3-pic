#!/bin/bash
# Скрипт запуска CLI версии для Linux/macOS

# Определяем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "Ошибка: Python 3 не найден!"
    echo "Установите Python 3: sudo apt install python3 python3-pip"
    exit 1
fi

# Создаем виртуальное окружение если его нет
if [ ! -d "venv" ]; then
    echo "Создаю виртуальное окружение..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
source venv/bin/activate

# Устанавливаем зависимости
echo "Проверяю зависимости..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Запускаем CLI версию
echo "Запускаю CLI версию..."
python3 youtube_to_mp3.py "$@"

# Деактивируем окружение при выходе
deactivate
