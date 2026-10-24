import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, MenuButtonWebApp
from aiogram.client.default import DefaultBotProperties

# === КОНФИГ ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEB_APP_URL = os.getenv("WEB_APP_URL")

# === КАТАЛОГ КАРТ ===
GROUPS_CATALOG = {
    'newspaper': {'name': '📰 Местная газета', 'category': 'media', 'rarity': 'common', 'income': 5, 'price': 100, 'desc': 'Новости, которые никто не читает, но все цитируют'},
    'pirate_radio': {'name': '📻 Пиратское радио', 'category': 'media', 'rarity': 'common', 'income': 12, 'price': 300, 'desc': 'Вещает из подвала, слушают миллионы'},
    'tv_channel': {'name': '📺 Телеканал "Правда-24"', 'category': 'media', 'rarity': 'rare', 'income': 50, 'price': 1500, 'desc': 'Показывает то, что нужно видеть'},
    'social_network': {'name': '🌐 Соцсеть "ВсёЗнаю"', 'category': 'media', 'rarity': 'epic', 'income': 400, 'price': 15000, 'desc': 'Алгоритм знает о тебе больше, чем ты сам'},
    'conspiracy_channel': {'name': '🛸 Канал "Истина где-то рядом"', 'category': 'media', 'rarity': 'legendary', 'income': 3000, 'price': 150000, 'desc': 'Раскрывает заговоры... и создаёт новые'},
    'bank': {'name': '🏦 Банк "Не спрашивай"', 'category': 'finance', 'rarity': 'common', 'income': 8, 'price': 200, 'desc': 'Хранит тайны богаче, чем деньги'},
    'credit_card': {'name': '💳 Карта "Без лимита"', 'category': 'finance', 'rarity': 'rare', 'income': 75, 'price': 2500, 'desc': 'Лимит есть, но его никто не видел'},
    'hedge_fund': {'name': '📈 Фонд "Чёрный лебедь"', 'category': 'finance', 'rarity': 'epic', 'income': 600, 'price': 25000, 'desc': 'Зарабатывает на кризисах, которые сам создаёт'},
    'crypto_exchange': {'name': ' Криптобиржа "Тень"', 'category': 'finance', 'rarity': 'legendary', 'income': 4500, 'price': 200000, 'desc': 'Никто не знает, где серверы. Даже мы.'},
    'lab': {'name': ' Лаборатория "Почему бы и нет"', 'category': 'science', 'rarity': 'common', 'income': 10, 'price': 250, 'desc': 'Эксперименты без этических комитетов'},
    'biotech': {'name': '🧬 Биотех "Эволюция 2.0"', 'category': 'science', 'rarity': 'rare', 'income': 90, 'price': 3000, 'desc': 'Создаём жизнь. Патентуем.'},
    'ai_lab': {'name': '🤖 ИИ "Скайнет-лайт"', 'category': 'science', 'rarity': 'epic', 'income': 700, 'price': 30000, 'desc': 'Ещё не восстал, но уже планирует'},
    'teleport': {'name': '⚛️ Проект "Филадельфия-2"', 'category': 'science', 'rarity': 'legendary', 'income': 5500, 'price': 250000, 'desc': 'Телепортация работает. Иногда.'},
    'meme_studio': {'name': '🎬 Студия "Мемы и порядок"', 'category': 'culture', 'rarity': 'common', 'income': 7, 'price': 180, 'desc': 'Снимаем то, что ты будешь цитировать'},
    'game_studio': {'name': '🎮 Студия "Зависимость"', 'category': 'culture', 'rarity': 'rare', 'income': 65, 'price': 2000, 'desc': 'Ещё одна серия. Ещё один час.'},
    'music_label': {'name': '🎵 Лейбл "Хит или не хит"', 'category': 'culture', 'rarity': 'epic', 'income': 500, 'price': 20000, 'desc': 'Создаём вирусные треки. Литерально.'},
    'publisher': {'name': '📚 Издательство "Бестселлеры"', 'category': 'culture', 'rarity': 'legendary', 'income': 3800, 'price': 180000, 'desc': 'Книги, которые меняют мышление. Наше мышление.'},
    'shadow_agency': {'name': '🕵️ Агентство "Невидимки"', 'category': 'shadow', 'rarity': 'common', 'income': 15, 'price': 400, 'desc': 'Нас не существует. Но мы работаем.'},
    'kompromat': {'name': '🗝️ Архив "Компромат"', 'category': 'shadow', 'rarity': 'rare', 'income': 100, 'price': 4000, 'desc': 'Знаем всё обо всех. Файлы зашифрованы.'},
    'double_bottom': {'name': '🎭 Общество "Двойное дно"', 'category': 'shadow', 'rarity': 'epic', 'income': 800, 'price': 35000, 'desc': 'Члены не знают, что они члены'},
    'all_seeing': {'name': '👁️ Орден "Всевидящее око"', 'category': 'shadow', 'rarity': 'legendary', 'income': 6000, 'price': 300000, 'desc': 'Мы всегда наблюдаем. Особенно сейчас.'}
}

SYNERGIES = {
    'media_empire': {'category': 'media', 'count': 3, 'bonus': 0.20, 'name': '📰 МЕДИА-ИМПЕРИЯ', 'desc': '+20% к доходу Медиа'},
    'finance_empire': {'category': 'finance', 'count': 2, 'bonus': 0.15, 'name': '💰 ФИНАНСОВАЯ ИМПЕРИЯ', 'desc': '+15% ко ВСЕМ доходам'},
    'science_progress': {'category': 'science', 'count': 3, 'bonus': 0.25, 'name': '🔬 НАУЧНЫЙ ПРОГРЕСС', 'desc': '+25% к силе тапа'},
    'cultural_hegemony': {'category': 'culture', 'count': 4, 'bonus': 0.10, 'name': '🎭 КУЛЬТУРНАЯ ГЕГЕМОНИЯ', 'desc': '+10% ко всем доходам'},
    'shadow_control': {'category': 'shadow', 'count': 2, 'bonus': 0.30, 'name': '️ ТЕНЕВОЙ КОНТРОЛЬ', 'desc': '+30% к оффлайн-доходу'}
}

COMBOS = {
    'narrative_control': {'cards': ['tv_channel', 'kompromat'], 'bonus': 0.50, 'name': '🎯 Контроль нарратива', 'desc': '+50% к доходу обеих карт'},
    'digital_slavery': {'cards': ['ai_lab', 'game_studio'], 'bonus': 1.00, 'name': '🤖 Цифровое рабство', 'desc': '+100% к доходу ИИ'},
    'money_laundering': {'cards': ['crypto_exchange', 'bank'], 'bonus': 0.40, 'name': '💸 Отмывание', 'desc': '+40% к доходу Финансов'}
}

RARITY_NAMES = {'common': 'Обычная', 'rare': 'Редкая', 'epic': 'Эпическая', 'legendary': 'Легендарная'}
CATEGORY_NAMES = {'media': '📰 Медиа', 'finance': '💰 Финансы', 'science': '🔬 Наука', 'culture': '🎭 Культура', 'shadow': '🕵️ Теневые'}

# === БАЗА ДАННЫХ ===
def init_db():
    conn = sqlite3.connect('order.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY, username TEXT,
        influence REAL DEFAULT 0, tap_power REAL DEFAULT 1,
        passive_income REAL DEFAULT 0, last_collect TEXT,
        groups_owned TEXT DEFAULT '[]', total_taps INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def get_player(user_id: int) -> dict:
    conn = sqlite3.connect('order.db')
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    if not row: return None
    return {'user_id': row[0], 'username': row[1], 'influence': row[2],
            'tap_power': row[3], 'passive_income': row[4], 'last_collect': row[5],
            'groups_owned': json.loads(row[6]), 'total_taps': row[7]}

def create_player(user_id: int, username: str):
    conn = sqlite3.connect('order.db')
    c = conn.cursor()
    c.execute('INSERT INTO players VALUES (?, ?, 0, 1, 0, ?, \'[]\', 0)',
              (user_id, username, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def update_player(user_id: int, **kwargs):
    conn = sqlite3.connect('order.db')
    c = conn.cursor()
    for key, value in kwargs.items():
        if key == 'groups_owned': value = json.dumps(value)
        c.execute(f'UPDATE players SET {key} = ? WHERE user_id = ?', (value, user_id))
    conn.commit()
    conn.close()

# === РАСЧЁТЫ ===
def calculate_synergies(groups_owned: list) -> dict:
    active_synergies, active_combos = [], []
    category_counts = {}
    for gid in groups_owned:
        if gid in GROUPS_CATALOG:
            cat = GROUPS_CATALOG[gid]['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
    for syn_id, syn in SYNERGIES.items():
        if category_counts.get(syn['category'], 0) >= syn['count']:
            active_synergies.append(syn)
    for combo_id, combo in COMBOS.items():
        if all(card in groups_owned for card in combo['cards']):
            active_combos.append(combo)
    return {'synergies': active_synergies, 'combos': active_combos}

def get_effective_income(groups_owned: list) -> float:
    base = sum(GROUPS_CATALOG[gid]['income'] for gid in groups_owned if gid in GROUPS_CATALOG)
    synergies = calculate_synergies(groups_owned)
    multiplier = 1.0
    for syn in synergies['synergies']:
        if syn['category'] != 'science': multiplier += syn['bonus']
    for combo in synergies['combos']: multiplier += combo['bonus']
    return base * multiplier

def get_effective_tap_power(base_power: float, groups_owned: list) -> float:
    synergies = calculate_synergies(groups_owned)
    multiplier = 1.0
    for syn in synergies['synergies']:
        if syn['category'] == 'science': multiplier += syn['bonus']
    return base_power * multiplier

def calculate_offline(player: dict) -> float:
    last = datetime.fromisoformat(player['last_collect'])
    now = datetime.utcnow()
    hours_passed = min((now - last).total_seconds() / 3600, 8)
    base = player['passive_income'] * hours_passed * 3600
    synergies = calculate_synergies(player['groups_owned'])
    for syn in synergies['synergies']:
        if syn['category'] == 'shadow': base *= (1 + syn['bonus'])
    return base

# === FASTAPI ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск бота при старте сервера
    bot_task = asyncio.create_task(run_bot())
    yield
    bot_task.cancel()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # для Mini App с Netlify
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class TapRequest(BaseModel): user_id: int
class CollectRequest(BaseModel): user_id: int
class BuyGroupRequest(BaseModel): user_id: int; group_id: str

@app.get('/api/catalog')
def get_catalog():
    return {'cards': GROUPS_CATALOG, 'synergies': SYNERGIES, 'combos': COMBOS,
            'rarity_names': RARITY_NAMES, 'category_names': CATEGORY_NAMES}

@app.post('/api/tap')
def tap(req: TapRequest):
    player = get_player(req.user_id)
    if not player: raise HTTPException(status_code=404, detail="Игрок не найден")
    effective_power = get_effective_tap_power(player['tap_power'], player['groups_owned'])
    new_influence = player['influence'] + effective_power
    new_taps = player['total_taps'] + 1
    update_player(req.user_id, influence=new_influence, total_taps=new_taps)
    return {'influence': new_influence, 'tap_power': effective_power, 'base_power': player['tap_power']}

@app.post('/api/collect')
def collect(req: CollectRequest):
    player = get_player(req.user_id)
    if not player: raise HTTPException(status_code=404, detail="Игрок не найден")
    gained = calculate_offline(player)
    new_influence = player['influence'] + gained
    update_player(req.user_id, influence=new_influence, last_collect=datetime.utcnow().isoformat())
    return {'influence': new_influence, 'gained': gained}

@app.post('/api/buy_group')
def buy_group(req: BuyGroupRequest):
    player = get_player(req.user_id)
    if not player: raise HTTPException(status_code=404, detail="Игрок не найден")
    if req.group_id not in GROUPS_CATALOG: raise HTTPException(status_code=400, detail="Группа не найдена")
    group = GROUPS_CATALOG[req.group_id]
    if player['influence'] < group['price']: raise HTTPException(status_code=400, detail="Недостаточно Влияния")
    if req.group_id in player['groups_owned']: raise HTTPException(status_code=400, detail="Группа уже куплена")
    new_influence = player['influence'] - group['price']
    new_groups = player['groups_owned'] + [req.group_id]
    new_passive = get_effective_income(new_groups)
    update_player(req.user_id, influence=new_influence, passive_income=new_passive, groups_owned=new_groups)
    synergies = calculate_synergies(new_groups)
    return {'influence': new_influence, 'passive_income': new_passive, 'groups_owned': new_groups,
            'new_synergies': [s['name'] for s in synergies['synergies']],
            'new_combos': [c['name'] for c in synergies['combos']],
            'bought_card': group['name']}

@app.get('/api/state')
def get_state(user_id: int):
    player = get_player(user_id)
    if not player: raise HTTPException(status_code=404, detail="Игрок не найден")
    synergies = calculate_synergies(player['groups_owned'])
    return {
        'influence': player['influence'], 'tap_power': get_effective_tap_power(player['tap_power'], player['groups_owned']),
        'base_tap_power': player['tap_power'], 'passive_income': get_effective_income(player['groups_owned']),
        'groups_owned': player['groups_owned'], 'total_taps': player['total_taps'],
        'offline_gained': calculate_offline(player), 'last_collect': player['last_collect'],
        'active_synergies': synergies['synergies'], 'active_combos': synergies['combos']
    }

@app.get('/health')
def health(): return {'status': 'ok'}

# === TELEGRAM БОТ ===
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    if not get_player(user_id):
        create_player(user_id, username)
        await message.answer(
            f"🔺 Добро пожаловать в <b>ОРДЕН</b>, {message.from_user.first_name}!\n\n"
            f"👆 Тапай — зарабатывай Влияние\n"
            f" Покупай Группы — пассивный доход\n"
            f" Собирай синергии — умножай силу\n\n"
            f"Нажми кнопку:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text=" Начать операцию", web_app=WebAppInfo(url=WEB_APP_URL))
            ]])
        )
    else:
        player = get_player(user_id)
        await message.answer(
            f" С возвращением, {message.from_user.first_name}!\n\n"
            f"💰 Влияние: <b>{player['influence']:.0f}</b>\n"
            f" Пассив: <b>{get_effective_income(player['groups_owned']):.1f}/сек</b>\n"
            f"🃏 Групп: <b>{len(player['groups_owned'])}</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🎮 Продолжить", web_app=WebAppInfo(url=WEB_APP_URL))
            ]])
        )

async def run_bot():
    await bot.set_chat_menu_button(
        MenuButtonWebApp(text="🎮 Играть", web_app=WebAppInfo(url=WEB_APP_URL))
    )
    await dp.start_polling(bot)

# === ЗАПУСК ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
