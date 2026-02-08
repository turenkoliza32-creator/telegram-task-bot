import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
import logging
import sqlite3

# ========== НАСТРОЙКИ ==========
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения Render
API_TOKEN = os.getenv('API_TOKEN')

if not API_TOKEN:
    print("ОШИБКА: Не найден API_TOKEN!")
    print("Создайте переменную API_TOKEN в настройках Render")
    exit(1)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ========== БАЗА ДАННЫХ ==========
def init_db():
    try:
        conn = sqlite3.connect('/tmp/tasks.db')  # В Render нужно особое место
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_text TEXT NOT NULL,
            reminder_time TEXT,
            is_done BOOLEAN DEFAULT FALSE
        )''')
        conn.commit()
        conn.close()
        print("База данных инициализирована")
    except Exception as e:
        print(f"Ошибка БД: {e}")

def add_task(user_id, task_text, reminder_time=None):
    conn = sqlite3.connect('/tmp/tasks.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks (user_id, task_text, reminder_time) VALUES (?, ?, ?)", 
                (user_id, task_text, reminder_time))
    conn.commit()
    conn.close()
    return True

def get_user_tasks(user_id):
    conn = sqlite3.connect('/tmp/tasks.db')
    cur = conn.cursor()
    cur.execute("SELECT id, task_text, reminder_time FROM tasks WHERE user_id=? AND is_done=FALSE ORDER BY id", 
                (user_id,))
    tasks = cur.fetchall()
    conn.close()
    return tasks

def mark_task_done(task_id):
    conn = sqlite3.connect('/tmp/tasks.db')
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET is_done=TRUE WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return True

# Инициализация БД
init_db()

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "*Бот для задач запущен!*\n\n"
        "*Команды:*\n"
        "• /add задача - добавить задачу\n"
        "• /list - показать задачи\n"
        "• /done номер - отметить выполненной\n"
        "• /help - помощь\n\n"
        "_Размещено на Render.com_",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    help_text = (
        "*Как пользоваться:*\n\n"
        "1. *Добавить задачу:*\n"
        "   `/add Купить молоко`\n\n"
        "2. *Посмотреть задачи:*\n"
        "   `/list`\n\n"
        "3. *Завершить задачу:*\n"
        "   `/done 1`\n\n"
        "*Примеры:*\n"
        "`/add Сделать уроки`\n"
        "`/add Позвонить маме 18:00`\n"
        "`/list`\n"
        "`/done 2`"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("add"))
async def add_command(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажите задачу: `/add ваша задача`", parse_mode="Markdown")
        return
    
    task_text = args[1]
    # Проверяем, есть ли время в конце
    import re
    time_match = re.search(r'(\d{1,2}:\d{2})$', task_text)
    reminder_time = None
    
    if time_match:
        reminder_time = time_match.group(1)
        task_text = task_text.replace(reminder_time, '').strip()
    
    if add_task(message.from_user.id, task_text, reminder_time):
        response = f"*Задача добавлена!*\n\n {task_text}"
        if reminder_time:
            response += f"\n Напоминание: {reminder_time}"
        await message.answer(response, parse_mode="Markdown")
    else:
        await message.answer("Не удалось добавить задачу")

@dp.message(Command("list"))
async def list_command(message: types.Message):
    tasks = get_user_tasks(message.from_user.id)
    
    if not tasks:
        await message.answer("*Список задач пуст*\n\nИспользуйте `/add задача`", parse_mode="Markdown")
        return
    
    response = "*Ваши задачи:*\n\n"
    for i, task in enumerate(tasks, 1):
        task_id, task_text, reminder_time = task
        response += f"{i}. {task_text}"
        if reminder_time:
            response += f"{reminder_time}"
        response += "\n"
    
    response += "\n*Завершить:* `/done номер`"
    await message.answer(response, parse_mode="Markdown")

@dp.message(Command("done"))
async def done_command(message: types.Message):
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Укажите номер: `/done 1`", parse_mode="Markdown")
            return
        
        task_num = int(args[1])
        tasks = get_user_tasks(message.from_user.id)
        
        if 1 <= task_num <= len(tasks):
            task_id = tasks[task_num-1][0]
            mark_task_done(task_id)
            await message.answer(f"*Задача {task_num} выполнена!*", parse_mode="Markdown")
        else:
            await message.answer(f"*Задача {task_num} не найдена*", parse_mode="Markdown")
    except ValueError:
        await message.answer("*Используйте номер:* `/done 1`", parse_mode="Markdown")

# Обработка любого другого сообщения
@dp.message()
async def echo(message: types.Message):
    await message.answer(
        "*Я не понял*\n\n"
        "Используйте команды:\n"
        "• /start - начало работы\n"
        "• /help - помощь\n"
        "• /add - добавить задачу",
        parse_mode="Markdown"
    )

# ========== ЗАПУСК БОТА ==========
async def main():
    print("=" * 50)
    print("Telegram Task Bot")
    print("Hosted on Render.com")
    print("Bot Token:", API_TOKEN[:10] + "..." if API_TOKEN else "NOT SET")
    print("=" * 50)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
