import os
import sqlite3
import time
import threading
import tempfile
from datetime import datetime
from flask import Flask
import telebot
from telebot import types
import pdfkit

# 1. НАСТРОЙКИ
TOKEN = os.environ.get("TOKEN_REF", "СЮДА_ВСТАВЬТЕ_ТОКЕН")
MAIN_ADMIN = 8349263362
BOT_USERNAME = "GGKassa_bot"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
temp_data = {}

# --- БАЗА ДАННЫХ ---
def init_db():
    with sqlite3.connect('mbank_bot.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('PRAGMA journal_mode=WAL;')
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        chat_id INTEGER PRIMARY KEY, 
                        join_date TEXT, 
                        referrer_id INTEGER, 
                        balance REAL DEFAULT 0.0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES ("ref_percent", "5.0")')
        conn.commit()

def get_ref_percent():
    with sqlite3.connect('mbank_bot.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT value FROM settings WHERE key = "ref_percent"')
        row = c.fetchone()
        return float(row[0]) if row else 5.0

def set_ref_percent(val):
    with sqlite3.connect('mbank_bot.db', timeout=10) as conn:
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES ("ref_percent", ?)', (str(val),))
        conn.commit()

init_db()

# --- HTML ШАБЛОН КВИТАНЦИИ MBANK ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    
    body {
        font-family: 'Roboto', sans-serif;
        margin: 0;
        padding: 40px;
        color: #1c1c1e;
        background-color: #ffffff;
    }
    
    .header {
        margin-bottom: 40px;
    }
    
    .logo {
        font-size: 38px;
        font-weight: 700;
        color: #0d3880;
    }
    
    .logo span {
        color: #8cc63f;
    }
    
    .divider {
        height: 1px;
        background-color: #e5e5ea;
        margin: 25px 0;
    }
    
    .row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
        font-size: 16px;
    }
    
    .label {
        color: #2c2c2e;
    }
    
    .value {
        text-align: right;
        color: #1c1c1e;
        max-width: 60%;
    }
    
    .total-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 30px;
    }
    
    .total-title {
        font-size: 26px;
        font-weight: 700;
    }
    
    .total-amount {
        font-size: 26px;
        font-weight: 700;
    }
    
    .stamp-box {
        text-align: center;
        margin-top: 40px;
    }
    
    .stamp {
        width: 160px;
        height: 160px;
        border: 3px dashed #1a56b6;
        border-radius: 50%;
        display: inline-flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: #1a56b6;
        font-size: 11px;
        font-weight: 500;
        padding: 10px;
        box-sizing: border-box;
    }
    
    .footer-text {
        text-align: center;
        color: #8e8e93;
        font-size: 13px;
        margin-top: 50px;
        line-height: 1.4;
    }
</style>
</head>
<body>

<div class="header">
    <div class="logo"><span>m</span>bank</div>
</div>

<div class="divider"></div>

<div class="row">
    <div class="label">Детали операции</div>
    <div class="value">
        Перевод по номеру телефона.<br>
        <b>{{ phone }}/ {{ name }} /</b><br>
        Сумма {{ amount }} KGS
    </div>
</div>

<div class="row" style="margin-top: 30px;">
    <div class="label">Дата и время</div>
    <div class="value">{{ datetime_str }}</div>
</div>

<div class="divider"></div>

<div class="total-container">
    <div class="total-title">Итого</div>
    <div class="total-amount">{{ amount }} ~</div>
</div>

<div class="stamp-box">
    <div class="stamp">
        <div>Ачык акционердик коому</div>
        <div style="font-size: 16px; font-weight: 700; margin: 4px 0;">mbank</div>
        <div>Открытое акционерное общество</div>
    </div>
</div>

<div class="footer-text">
    Квитанция №{{ receipt_no }}<br><br>
    По вопросам зачисления обратитесь к отправителю<br>
    Телефон службы поддержки 3333
</div>

</body>
</html>
"""

def make_pdf(data):
    from jinja2 import Template
    template = Template(HTML_TEMPLATE)
    rendered_html = template.render(**data)
    
    options = {
        'page-size': 'A5',
        'margin-top': '0mm',
        'margin-right': '0mm',
        'margin-bottom': '0mm',
        'margin-left': '0mm',
        'encoding': "UTF-8",
        'no-outline': None
    }
    
    # Явный путь к wkhtmltopdf в Linux
    config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
    
    output_path = tempfile.mktemp(suffix=".pdf")
    pdfkit.from_string(rendered_html, output_path, options=options, configuration=config)
    return output_path

# --- РЕНДЕР КНОПОК И МЕНЮ ---
def main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📄 Чеки / Балансы", "📄 PDF Квитанции")
    markup.add("💼 Баланс", "ℹ️ Инфо")
    markup.add("🤝 Партнерская программа")
    if user_id == MAIN_ADMIN:
        markup.add("⚙️ Админ панель")
    return markup

def back_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("‹ Назад")
    return markup

# --- ОБРАБОТКА КОМАНД И НАВИГАЦИИ ---
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(
        msg.chat.id, 
        "<b>Главное меню:</b>", 
        parse_mode='HTML', 
        reply_markup=main_keyboard(msg.from_user.id)
    )

@bot.message_handler(func=lambda m: m.text == "‹ Назад")
def back_btn(msg):
    start(msg)

@bot.message_handler(func=lambda m: m.text == "📄 PDF Квитанции")
def pdf_section(msg):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("MBank", callback_data="gen_mbank"))
    bot.send_message(msg.chat.id, "Выберите нужный банк для генерации PDF:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "gen_mbank")
def mbank_instruction(call):
    text = """📄 <b>MBank → отправь данные по инструкции:</b>

1️⃣ <b>Сумма перевода</b>
2️⃣ <b>Телефон получателя</b>
3️⃣ <b>Имя получателя</b>
4️⃣ <b>Дата и время перевода</b>
5️⃣ <b>Номер квитанции (необ.)</b>

👇 <b>Пример введенных данных:</b>

<code>5500.50
996700002434
Валентин Д
30.07.2026 15:26
P1000200030000</code>"""
    
    bot.send_message(call.message.chat.id, text, parse_mode='HTML', reply_markup=back_keyboard())
    bot.register_next_step_handler(call.message, process_mbank_input)

def process_mbank_input(msg):
    if msg.text == "‹ Назад":
        return start(msg)
    
    lines = [line.strip() for line in msg.text.strip().split('\n') if line.strip()]
    if len(lines) < 4:
        bot.send_message(msg.chat.id, "❌ Недостаточно строк! Отправьте данные строго по инструкции (минимум 4 строки).", reply_markup=back_keyboard())
        bot.register_next_step_handler(msg, process_mbank_input)
        return

    amount = lines[0]
    phone = lines[1]
    name = lines[2]
    datetime_str = lines[3]
    receipt_no = lines[4] if len(lines) >= 5 else f"P{int(time.time())}"

    bot.send_message(msg.chat.id, "⏳ <i>Генерация PDF квитанции MBank...</i>", parse_mode='HTML')

    try:
        data = {
            'amount': amount,
            'phone': phone,
            'name': name,
            'datetime_str': datetime_str,
            'receipt_no': receipt_no
        }
        
        pdf_file_path = make_pdf(data)
        
        with open(pdf_file_path, 'rb') as doc:
            bot.send_document(
                msg.chat.id, 
                doc, 
                visible_file_name=f"{receipt_no}.pdf",
                caption=f"✅ <b>Квитанция MBank успешно сформирована!</b>",
                parse_mode='HTML',
                reply_markup=main_keyboard(msg.from_user.id)
            )
        os.remove(pdf_file_path)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Ошибка при генерации PDF: {e}", reply_markup=main_keyboard(msg.from_user.id))

# --- УПРАВЛЕНИЕ РЕФЕРАЛЬНЫМ ПРОЦЕНТОМ ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Админ панель" and m.from_user.id == MAIN_ADMIN)
def admin_menu_handler(msg):
    ref_pct = get_ref_percent()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(f"🔗 Процент реф ({ref_pct:g}%)", "‹ Назад")
    bot.send_message(msg.chat.id, "⚙️ **Админ панель:**", parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text.startswith("🔗 Процент реф") and m.from_user.id == MAIN_ADMIN)
def change_pct_step(msg):
    bot.send_message(msg.chat.id, "Введите новый процент реферальной системы:", reply_markup=back_keyboard())
    bot.register_next_step_handler(msg, save_pct)

def save_pct(msg):
    if msg.text == "‹ Назад": return start(msg)
    try:
        val = float(msg.text.replace(',', '.').replace('%', ''))
        set_ref_percent(val)
        bot.send_message(msg.chat.id, f"✅ Установлен новый процент: {val:g}%", reply_markup=main_keyboard(msg.from_user.id))
    except ValueError:
        bot.send_message(msg.chat.id, "❌ Введите корректное число!")

# --- FLASK СЕРВЕР ---
@app.route('/')
def home():
    return {"status": "ok", "bot": "MBank Generator"}, 200

def run_bot():
    bot.remove_webhook()
    bot.polling(none_stop=True)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
