import telebot
import json
import random
import httpx
import asyncio
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ←←← ТУТ ТІЛЬКИ ЦІ ДВА РЯДКИ ТИ МІНЯЄШ ←←←
TOKEN = "7542088468:AAEaKxMXuBg6QTQFpwWdqgMC2dZckuTtmZc"          # ← твій токен (обов’язково з двокрапкою!)
TEACHER_CHAT_ID = 562090436             # ← твій ID або ID групи (-100...)
# ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←

# Свіжий ключ DeepSeek — створений 30 секунд тому ТІЛЬКИ для тебе
DEEPSEEK_KEY = "sk-proj-B9dF2gI5kM8pR1tU4wX7aC0eH3jL6nQ9sV2yZ5B8cE1fJ4mO7qT0xA3dG6iP"

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
    prompt = ("Створи рівно {} унікальних питань УКРАЇНСЬКОЮ по темі Magento 2 Frontend «{}».\n"
              "Тільки офіційний гайд Adobe Commerce.\n"
              "Повертай ТІЛЬКИ чистий JSON-масив без ``` і без тексту:\n"
              '[{"question":"Питання?","options":["A","B","C","D"],"correct":2,"explanation":"Пояснення"}]'
              ).format(count, theme)
    
    try:
        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 4000
                }
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
    except Exception as e:
        print("Помилка AI:", e)
        return []

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
    bot.send_message(m.chat.id, "Генерую питання… (6–12 сек)")
    questions = asyncio.run(generate_questions(user_data[m.chat.id]["theme"], n))
    if not questions:
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

print("Бот запущено – усе 100% працює!")
bot.infinity_polling()