#!/bin/bash
# Скрипт запуска графического интерфейса для Linux/macOS

# Определяем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "Ошибка: Python 3 не найден!"
    echo "Установите Python 3: sudo apt install python3 python3-pip python3-tk"
    exit 1
fi

# Проверяем наличие tk (tkinter)
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "Ошибка: tkinter не найден!"
    echo "Установите tkinter: sudo apt install python3-tk"
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

# Запускаем приложение
echo "Запускаю приложение..."
python3 app.py

# Деактивируем окружение при выходе
deactivate
