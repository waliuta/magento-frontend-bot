import telebot
import json
import random
import httpx
import asyncio
import os
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# УСІ СЕКРЕТИ — у змінних середовища Render!
TOKEN = os.getenv("BOT_TOKEN")
TEACHER_CHAT_ID = int(os.getenv("TEACHER_CHAT_ID"))
GROQ_KEY = os.getenv("GROQ_KEY")

bot = telebot.TeleBot(TOKEN)
user_data = {}

THEMES = {
    "Themes": "Теми, theme.xml, спадкування",
    "Layouts": "Layout XML, handles, referenceBlock",
    "Templates": "phtml-шаблони, блоки",
    "Cascading style sheets (CSS)": "LESS, _extend.less",
    "Responsive web design": "Брейкпоінти, медіа-запити",
    "Translations": "i18n, csv, inline",
    "Form validation": "валідація форм"
}

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for t in THEMES:
        kb.add(KeyboardButton(t))
    return kb

def numbers_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=5)
    for i in range(1, 11):
        kb.add(KeyboardButton(str(i)))
    kb.add(KeyboardButton("Назад"))
    return kb

async def generate_questions(theme, count):
    prompt = f"""Ти — експерт Adobe Commerce Frontend Developer.
Створи рівно {count} унікальних питань УКРАЇНСЬКОЮ по темі «{theme}».
Тільки офіційний гайд: https://developer.adobe.com/commerce/frontend-core/guide/

Повертай ТІЛЬКИ чистий JSON-масив без ```json і без зайвого тексту.
Приклад структури (не копіюй його, просто дотримуйся формату):
[{{"question":"Питання тут","options":["A","B","C","D"],"correct":1,"explanation":"Пояснення тут"}}]
""".strip()
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={
                    "model": "llama-3.1-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 4000
                }
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
            text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(text)
    except Exception as e:
        print("Groq error:", e)
        return []

# (весь інший код — без змін — від @bot.message_handler і нижче — залишається точно як у тебе був)
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Привіт! Динамічний тест Magento Frontend\nОбирай тему:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text in THEMES)
def theme(m):
    user_data[m.chat.id] = {"theme": m.text}
    bot.send_message(m.chat.id, f"Тема: {m.text}\nСкільки питань (1–10)?", reply_markup=numbers_kb())

@bot.message_handler(func=lambda m: m.text.isdigit() and 1 <= int(m.text) <= 10)
def count(m):
    n = int(m.text)
    bot.send_message(m.chat.id, "Генерую питання… (5–10 сек)")
    questions = asyncio.run(generate_questions(user_data[m.chat.id]["theme"], n))
    if not questions or len(questions) == 0:
        bot.send_message(m.chat.id, "Помилка генерації. Спробуй ще раз")
        return
    random.shuffle(questions)
    user_data[m.chat.id].update({"q": questions, "i": 0, "ok": 0, "log": []})
    ask(m.chat.id)

def ask(cid):
    u = user_data[cid]
    if u["i"] >= len(u["q"]):
        result(cid)
        return
    qq = u["q"][u["i"]]
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for o in qq["options"]:
        kb.add(KeyboardButton(o))
    bot.send_message(cid, f"Питання {u['i']+1}/{len(u['q'])}\n\n{qq['question']}", reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def answer(m):
    cid = m.chat.id
    if cid not in user_data or "i" not in user_data[cid]:
        return
    u = user_data[cid]
    qq = u["q"][u["i"]]
    correct = qq["options"][qq["correct"]]
    if m.text == correct:
        u["ok"] += 1
    u["log"].append({"q": qq["question"], "u": m.text, "c": correct, "e": qq["explanation"]})
    u["i"] += 1
    ask(cid)

def result(cid):
    u = user_data[cid]
    text = f"Тест завершено!\nПравильних: {u['ok']}/{len(u['q'])}\n\n"
    for i, x in enumerate(u["log"], 1):
        status = "Правильно" if x["u"] == x["c"] else "Помилка"
        text += f"{status} {i}. {x['q']}\nТвоя: {x['u']}\nПравильна: {x['c']}\n→ {x['e']}\n\n"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Надіслати результат викладачу"))
    bot.send_message(cid, text, reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "Надіслати результат викладачу")
def send(m):
    u = user_data[m.chat.id]
    bot.send_message(TEACHER_CHAT_ID, f"Новий результат!\nТема: {u['theme']}\nУчень: {m.from_user.full_name}\n{u['ok']}/{len(u['q'])}")
    bot.forward_message(TEACHER_CHAT_ID, m.chat.id, m.message_id - 1)
    bot.send_message(m.chat.id, "Надіслано викладачу!", reply_markup=main_menu())
    del user_data[m.chat.id]

print("Бот запущено – працює на Groq (ключ у змінних середовища)!")
import os
if os.getenv("RENDER"):
    import threading
    import http.server
    import socketserver
    def fake_server():
        with socketserver.TCPServer(("0.0.0.0", 10000), lambda *args: None) as httpd:
            httpd.serve_forever()
    threading.Thread(target=fake_server, daemon=True).start()
bot.infinity_polling()




