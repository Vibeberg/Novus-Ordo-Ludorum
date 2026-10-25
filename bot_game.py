import os, json, sqlite3, asyncio
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

load_dotenv()
bot = Bot(os.getenv("BOT_TOKEN"))
dp = Dispatcher()
DB = 'order.db'

CATALOG = {
    'newspaper': {'name': 'Местная газета', 'cat': 'media', 'inc': 5, 'price': 100, 'icon': '📰'},
    'pirate_radio': {'name': 'Пиратское радио', 'cat': 'media', 'inc': 12, 'price': 300, 'icon': '📻'},
    'tv_channel': {'name': 'Телеканал Правда-24', 'cat': 'media', 'inc': 50, 'price': 1500, 'icon': '📺'},
    'social_net': {'name': 'Соцсеть ВсёЗнаю', 'cat': 'media', 'inc': 400, 'price': 15000, 'icon': '🌐'},
    'conspiracy': {'name': 'Канал Истина', 'cat': 'media', 'inc': 3000, 'price': 150000, 'icon': ''},
    'bank': {'name': 'Банк Не спрашивай', 'cat': 'finance', 'inc': 8, 'price': 200, 'icon': '🏦'},
    'credit_card': {'name': 'Карта Без лимита', 'cat': 'finance', 'inc': 75, 'price': 2500, 'icon': '💳'},
    'hedge_fund': {'name': 'Фонд Чёрный лебедь', 'cat': 'finance', 'inc': 600, 'price': 25000, 'icon': ''},
    'crypto': {'name': 'Криптобиржа Тень', 'cat': 'finance', 'inc': 4500, 'price': 200000, 'icon': '🪙'},
    'lab': {'name': 'Лаборатория', 'cat': 'science', 'inc': 10, 'price': 250, 'icon': '🔬'},
    'biotech': {'name': 'Биотех Эволюция', 'cat': 'science', 'inc': 90, 'price': 3000, 'icon': '🧬'},
    'ai_lab': {'name': 'ИИ Скайнет-лайт', 'cat': 'science', 'inc': 700, 'price': 30000, 'icon': ''},
    'teleport': {'name': 'Проект Филадельфия', 'cat': 'science', 'inc': 5500, 'price': 250000, 'icon': '⚛️'},
    'meme': {'name': 'Студия Мемы', 'cat': 'culture', 'inc': 7, 'price': 180, 'icon': ''},
    'game': {'name': 'Студия Зависимость', 'cat': 'culture', 'inc': 65, 'price': 2000, 'icon': ''},
    'music': {'name': 'Лейбл Хит', 'cat': 'culture', 'inc': 500, 'price': 20000, 'icon': ''},
    'publisher': {'name': 'Издательство', 'cat': 'culture', 'inc': 3800, 'price': 180000, 'icon': ''},
    'shadow': {'name': 'Агентство Невидимки', 'cat': 'shadow', 'inc': 15, 'price': 400, 'icon': '🕵️'},
    'kompromat': {'name': 'Архив Компромат', 'cat': 'shadow', 'inc': 100, 'price': 4000, 'icon': '️'},
    'double': {'name': 'Общество Двойное дно', 'cat': 'shadow', 'inc': 800, 'price': 35000, 'icon': '🎭'},
    'all_seeing': {'name': 'Орден Всевидящее око', 'cat': 'shadow', 'inc': 6000, 'price': 300000, 'icon': '👁️'}
}

SYN = {
    'media': {'need': 3, 'bonus': 0.20, 'name': '📰 МЕДИА-ИМПЕРИЯ +20%'},
    'finance': {'need': 2, 'bonus': 0.15, 'name': '💰 ФИНАНСОВАЯ ИМПЕРИЯ +15%'},
    'science': {'need': 3, 'bonus': 0.25, 'name': '🔬 НАУЧНЫЙ ПРОГРЕСС +25% тап'},
    'culture': {'need': 4, 'bonus': 0.10, 'name': ' КУЛЬТУРНАЯ ГЕГЕМОНИЯ +10%'},
    'shadow': {'need': 2, 'bonus': 0.30, 'name': '🕵️ ТЕНЕВОЙ КОНТРОЛЬ +30% оффлайн'}
}
def db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY, username TEXT,
        influence REAL DEFAULT 0, tap_power REAL DEFAULT 1,
        passive_income REAL DEFAULT 0, last_collect TEXT,
        groups_owned TEXT DEFAULT '[]', total_taps INTEGER DEFAULT 0
    )''')
    conn.commit()
    return conn

def get_p(uid):
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM players WHERE user_id=?', (uid,))
    r = c.fetchone()
    conn.close()
    if not r: return None
    return {'uid': r[0], 'username': r[1], 'inf': r[2], 'tap': r[3],
            'passive': r[4], 'last': r[5], 'groups': json.loads(r[6]), 'taps': r[7]}

def create_p(uid, uname):
    conn = db()
    c = conn.cursor()
    c.execute('INSERT INTO players VALUES (?,?,?,?,?,?,?,?)',
              (uid, uname, 0, 1, 0, datetime.utcnow().isoformat(), '[]', 0))
    conn.commit()
    conn.close()

def upd(uid, **kw):
    conn = db()
    c = conn.cursor()
    for k, v in kw.items():
        if k == 'groups': v = json.dumps(v)
        c.execute(f'UPDATE players SET {k}=? WHERE user_id=?', (v, uid))
    conn.commit()
    conn.close()

def calc_income(groups):
    base = sum(CATALOG[g]['inc'] for g in groups if g in CATALOG)
    cats = {}
    for g in groups:
        if g in CATALOG:
            c = CATALOG[g]['cat']
            cats[c] = cats.get(c, 0) + 1
    mult = 1.0
    for cat, s in SYN.items():
        if cats.get(cat, 0) >= s['need']:
            mult += s['bonus']
    return base * mult

def calc_offline(p):
    last = datetime.fromisoformat(p['last'])
    hours = min((datetime.utcnow() - last).total_seconds() / 3600, 8)
    return p['passive'] * hours * 3600

def get_active_syns(groups):
    cats = {}
    for g in groups:
        if g in CATALOG:
            c = CATALOG[g]['cat']
            cats[c] = cats.get(c, 0) + 1
    return [SYN[c]['name'] for c, s in SYN.items() if cats.get(c, 0) >= s['need']]
@dp.message(CommandStart())
async def start(m: Message):
    p = get_p(m.from_user.id)
    if not p:
        create_p(m.from_user.id, m.from_user.username or '')
        p = get_p(m.from_user.id)
    await m.answer(
        f"🔺 Привет, {m.from_user.first_name}!\n\n"
        f" Влияние: {p['inf']:.0f}\n"
        f"⚡ Сила тапа: {p['tap']:.0f}\n"
        f"📈 Пассив: {p['passive']:.1f}/сек\n"
        f"🃏 Карт: {len(p['groups'])}\n\n"
        f"Команды:\n"
        f"/tap — тапнуть\n"
        f"/shop — магазин\n"
        f"/inv — инвентарь\n"
        f"/collect — собрать оффлайн\n"
        f"/profile — полный профиль",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="👆 Тапнуть", callback_data="tap"),
            InlineKeyboardButton(text="🏛 Магазин", callback_data="shop")
        ]])
    )

@dp.message(Command("tap"))
async def tap_cmd(m: Message):
    p = get_p(m.from_user.id)
    if not p:
        await m.answer("Сначала /start")
        return
    gained = p['tap']
    upd(m.from_user.id, influence=p['inf'] + gained, total_taps=p['taps'] + 1)
    await m.answer(f"👆 +{gained:.0f} Влияния!\nВсего: {p['inf'] + gained:.0f}")

@dp.message(Command("collect"))
async def collect_cmd(m: Message):
    p = get_p(m.from_user.id)
    if not p:
        await m.answer("Сначала /start")
        return
    gained = calc_offline(p)
    if gained < 1:
        await m.answer("💤 Нечего собирать")
        return
    upd(m.from_user.id, influence=p['inf'] + gained, last_collect=datetime.utcnow().isoformat())
    await m.answer(f"💤 Пока тебя не было: +{gained:.0f} Влияния!")

@dp.message(Command("profile"))
async def profile(m: Message):
    p = get_p(m.from_user.id)
    if not p:
        await m.answer("Сначала /start")
        return
    syns = get_active_syns(p['groups'])
    syn_text = '\n'.join(f"• {s}" for s in syns) if syns else "нет"
    await m.answer(
        f"🔺 <b>Профиль</b>\n\n"
        f"💰 Влияние: <b>{p['inf']:.0f}</b>\n"
        f"⚡ Сила тапа: <b>{p['tap']:.0f}</b>\n"
        f"📈 Пассив: <b>{p['passive']:.1f}/сек</b>\n"
        f"👆 Всего тапов: <b>{p['taps']}</b>\n"
        f"🃏 Карт: <b>{len(p['groups'])}</b>\n\n"
        f"🎯 Синергии:\n{syn_text}",
        parse_mode="HTML"
    )
@dp.message(Command("shop"))
async def shop(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📰 Медиа", callback_data="shop_media"),
         InlineKeyboardButton(text="💰 Финансы", callback_data="shop_finance")],
        [InlineKeyboardButton(text="🔬 Наука", callback_data="shop_science"),
         InlineKeyboardButton(text="🎭 Культура", callback_data="shop_culture")],
        [InlineKeyboardButton(text="🕵️ Теневые", callback_data="shop_shadow")]
    ])
    await m.answer("🏛 <b>Магазин Групп</b>\n\nВыбери категорию:", reply_markup=kb, parse_mode="HTML")

@dp.message(Command("inv"))
async def inv(m: Message):
    p = get_p(m.from_user.id)
    if not p or not p['groups']:
        await m.answer(" Инвентарь пуст. Купи карты в /shop")
        return
    lines = []
    for g in p['groups']:
        if g in CATALOG:
            c = CATALOG[g]
            lines.append(f"{c['icon']} {c['name']} (+{c['inc']}/сек)")
    await m.answer(f"🃏 <b>Твои карты ({len(p['groups'])}):</b>\n\n" + "\n".join(lines), parse_mode="HTML")

@dp.callback_query(F.data == "tap")
async def cb_tap(cb: CallbackQuery):
    p = get_p(cb.from_user.id)
    if not p:
        await cb.answer("Сначала /start", show_alert=True)
        return
    gained = p['tap']
    upd(cb.from_user.id, influence=p['inf'] + gained, total_taps=p['taps'] + 1)
    await cb.answer(f"+{gained:.0f} 💰", show_alert=False)

@dp.callback_query(F.data.startswith("shop_"))
async def cb_shop(cb: CallbackQuery):
    cat = cb.data.split("_")[1]
    p = get_p(cb.from_user.id)
    if not p:
        await cb.answer("Сначала /start", show_alert=True)
        return
    kb = []
    for gid, c in CATALOG.items():
        if c['cat'] == cat:
            owned = gid in p['groups']
            can = p['inf'] >= c['price']
            if owned:
                label = f"✅ {c['icon']} {c['name']}"
            elif can:
                label = f"{c['icon']} {c['name']} — {c['price']}💰"
            else:
                label = f"🔒 {c['name']} ({c['price']}💰)"
            cb_data = f"buy_{gid}" if can and not owned else "no"
            kb.append([InlineKeyboardButton(text=label, callback_data=cb_data)])
    kb.append([InlineKeyboardButton(text="◀️ Назад", callback_data="shop_back")])
    await cb.message.edit_text(
        f"🏛 <b>{cat.title()}</b>\n\n💰 Твоё Влияние: {p['inf']:.0f}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "shop_back")
async def cb_shop_back(cb: CallbackQuery):
    await shop(cb.message)

@dp.callback_query(F.data == "no")
async def cb_no(cb: CallbackQuery):
    await cb.answer("Недостаточно Влияния", show_alert=True)

@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy(cb: CallbackQuery):
    gid = cb.data.split("_")[1]
    if gid not in CATALOG:
        await cb.answer("Карта не найдена", show_alert=True)
        return
    p = get_p(cb.from_user.id)
    c = CATALOG[gid]
    if gid in p['groups']:
        await cb.answer("Уже есть!", show_alert=True)
        return
    if p['inf'] < c['price']:
        await cb.answer(f"Нужно {c['price']}💰", show_alert=True)
        return
    new_groups = p['groups'] + [gid]
    new_passive = calc_income(new_groups)
    old_syns = get_active_syns(p['groups'])
    upd(cb.from_user.id, influence=p['inf'] - c['price'], passive_income=new_passive, groups=new_groups)
    new_syns = get_active_syns(new_groups)
    syn_msg = ""
    for s in new_syns:
        if s not in old_syns:
            syn_msg += f"\n🔥 Новая синергия: {s}!"
    await cb.answer(f"Куплено: {c['name']}", show_alert=False)
    await cb.message.answer(
        f"✅ Куплено: <b>{c['icon']} {c['name']}</b>\n"
        f" Осталось: {(p['inf'] - c['price']):.0f}\n"
        f"📈 Новый пассив: {new_passive:.1f}/сек{syn_msg}",
        parse_mode="HTML"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
