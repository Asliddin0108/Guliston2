import asyncio
import re
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# =======================
# 🔐 SOZLAMALAR
# =======================

BOT_TOKEN = "8248768480:AAERzNVEBPNaLWNRhAPJtgY4WR7H8mtK73I"
GROUP_ID = -1003555493835
ADMIN_ID = 8238730404

# =======================
# 🤖 BOT
# =======================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# =======================
# 🗄 DATABASE
# =======================

db = sqlite3.connect("bot.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS drivers (
    driver_id INTEGER PRIMARY KEY,
    phone TEXT,
    is_active INTEGER DEFAULT 1
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    route TEXT,
    phone TEXT,
    name TEXT,
    type TEXT,
    status TEXT,
    taken_by INTEGER
)
""")
db.commit()

def is_driver(user_id: int):
    cur.execute("SELECT is_active FROM drivers WHERE driver_id=?", (user_id,))
    row = cur.fetchone()
    return row and row[0] == 1

def get_driver_phone(driver_id: int):
    cur.execute("SELECT phone FROM drivers WHERE driver_id=?", (driver_id,))
    row = cur.fetchone()
    return row[0] if row else "Noma’lum"

# =======================
# 🧠 STATES
# =======================

class OrderState(StatesGroup):
    route = State()
    phone = State()
    name = State()

class AdminAddDriver(StatesGroup):
    driver_id = State()
    phone = State()

class AdminRemoveDriver(StatesGroup):
    driver_id = State()

# =======================
# 🎛 KEYBOARDS
# =======================

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚕 Taksi chaqirish", callback_data="taksi")],
        [InlineKeyboardButton(text="📦 Pochta yuborish", callback_data="pochta")]
    ])

def take_button(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚖 OLISH", callback_data=f"take_{order_id}")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Haydovchi qo‘shish", callback_data="admin_add")],
        [InlineKeyboardButton(text="➖ Haydovchi o‘chirish", callback_data="admin_remove")]
    ])

# =======================
# ▶️ START (HAMMA UCHUN)
# =======================

@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return

    await state.clear()
    await message.answer(
        "Assalomu alaykum 👋\nXizmat turini tanlang:",
        reply_markup=main_menu()
    )

# =======================
# 👮 ADMIN PANEL
# =======================

@dp.message(F.text == "/admin")
async def admin_panel(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Siz admin emassiz")
        return

    await state.clear()
    await message.answer(
        "👮 Admin panel\nQuyidagilardan birini tanlang:",
        reply_markup=admin_menu()
    )

# =======================
# ➕ ADMIN: HAYDOVCHI QO‘SHISH
# =======================

@dp.callback_query(F.data == "admin_add")
async def admin_add_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Ruxsat yo‘q", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminAddDriver.driver_id)

    await call.message.edit_text(
        "➕ Haydovchi qo‘shish\n\n"
        "🆔 Haydovchi ID sini yuboring\n\n"
        "❌ Bekor qilish uchun /cancel yozing"
    )
    await call.answer()

@dp.message(AdminAddDriver.driver_id)
async def admin_get_driver_id(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_menu())
        return

    try:
        driver_id = int(message.text)
        await state.update_data(driver_id=driver_id)
        await state.set_state(AdminAddDriver.phone)

        await message.answer(
            "📞 Haydovchi telefon raqamini yuboring\n"
            "Masalan: +998901234567\n\n"
            "❌ Bekor qilish uchun /cancel yozing"
        )
    except:
        await message.answer("❌ Faqat raqamli ID yuboring")

@dp.message(AdminAddDriver.phone)
async def admin_get_driver_phone(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_menu())
        return

    phone = message.text.replace(" ", "")
    if not re.fullmatch(r"\+998\d{9}", phone):
        await message.answer("❌ Telefon formati noto‘g‘ri\nMasalan: +998901234567")
        return

    data = await state.get_data()

    cur.execute(
        "INSERT OR REPLACE INTO drivers (driver_id, phone, is_active) VALUES (?, ?, 1)",
        (data["driver_id"], phone)
    )
    db.commit()

    await message.answer(
        "✅ Haydovchi muvaffaqiyatli qo‘shildi\n\n"
        f"🆔 ID: {data['driver_id']}\n"
        f"📞 Telefon: {phone}",
        reply_markup=admin_menu()
    )
    await state.clear()

# =======================
# ➖ ADMIN: HAYDOVCHI O‘CHIRISH
# =======================

@dp.callback_query(F.data == "admin_remove")
async def admin_remove_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id != ADMIN_ID:
        await call.answer("⛔ Ruxsat yo‘q", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminRemoveDriver.driver_id)

    await call.message.edit_text(
        "➖ Haydovchi o‘chirish\n\n"
        "🆔 O‘chiriladigan haydovchi ID sini yuboring\n\n"
        "❌ Bekor qilish uchun /cancel yozing"
    )
    await call.answer()

@dp.message(AdminRemoveDriver.driver_id)
async def admin_remove_driver(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi", reply_markup=admin_menu())
        return

    try:
        driver_id = int(message.text)
        cur.execute("UPDATE drivers SET is_active=0 WHERE driver_id=?", (driver_id,))
        db.commit()

        await message.answer(
            f"⛔ Haydovchi o‘chirildi\n🆔 ID: {driver_id}",
            reply_markup=admin_menu()
        )
        await state.clear()
    except:
        await message.answer("❌ Faqat raqamli ID yuboring")

# =======================
# 🚕 / 📦 TANLASH
# =======================

@dp.callback_query(F.data.in_(["taksi", "pochta"]))
async def choose_type(call: types.CallbackQuery, state: FSMContext):
    await state.update_data(type=call.data)
    await call.message.answer("📍 Yo‘nalishni kiriting\nMasalan: Toshkent → Guliston")
    await state.set_state(OrderState.route)
    await call.answer()

# =======================
# 📍 YO‘NALISH
# =======================

@dp.message(OrderState.route)
async def get_route(message: types.Message, state: FSMContext):
    await state.update_data(route=message.text)
    await message.answer("📞 Telefon raqamni kiriting\nFormat: +998901234567")
    await state.set_state(OrderState.phone)

# =======================
# 📞 TELEFON
# =======================

@dp.message(OrderState.phone)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.text.replace(" ", "")
    if not re.fullmatch(r"\+998\d{9}", phone):
        await message.answer("❌ Telefon raqam noto‘g‘ri\nQayta kiriting")
        return

    await state.update_data(phone=phone)
    await message.answer("👤 Ismingizni kiriting")
    await state.set_state(OrderState.name)

# =======================
# 👤 ISM → ZAKAZ
# =======================

@dp.message(OrderState.name)
async def finish_order(message: types.Message, state: FSMContext):
    data = await state.get_data()

    cur.execute("""
    INSERT INTO orders (user_id, route, phone, name, type, status)
    VALUES (?, ?, ?, ?, ?, 'new')
    """, (
        message.from_user.id,
        data["route"],
        data["phone"],
        message.text,
        data["type"]
    ))
    db.commit()

    order_id = cur.lastrowid
    username = f"@{message.from_user.username}" if message.from_user.username else "Yopiq"

    text = (
        f"🆕 YANGI {'TAKSI' if data['type']=='taksi' else 'POCHTA'} ZAKAZ\n\n"
        f"📍 Yo‘nalish:\n{data['route']}\n\n"
        f"👤 Ismi: {message.text}\n"
        f"📞 Telefon: {data['phone']}\n"
        f"🆔 Profil ID: {message.from_user.id}\n"
        f"🔗 Profil: {username}"
    )

    await bot.send_message(GROUP_ID, text, reply_markup=take_button(order_id))

    msg = await message.answer("✅ Ma’lumotlar qabul qilindi\n⏳ Iltimos kuting...")
    await asyncio.sleep(4)
    await msg.delete()

    await state.clear()

# =======================
# 🚖 OLISH
# =======================

@dp.callback_query(F.data.startswith("take_"))
async def take_order(call: types.CallbackQuery):
    driver_id = call.from_user.id
    order_id = int(call.data.split("_")[1])

    if not is_driver(driver_id):
        await call.answer("❌ Siz haydovchi emassiz", show_alert=True)
        return

    cur.execute("SELECT status, user_id, route, phone, name FROM orders WHERE order_id=?", (order_id,))
    order = cur.fetchone()

    if not order or order[0] != "new":
        await call.answer("❌ Zakaz allaqachon olingan", show_alert=True)
        return

    cur.execute(
        "UPDATE orders SET status='taken', taken_by=? WHERE order_id=?",
        (driver_id, order_id)
    )
    db.commit()

    await call.message.edit_reply_markup(None)

    driver_phone = get_driver_phone(driver_id)

    await bot.send_message(
        order[1],
        "✅ Zakaz qabul qilindi\n\n"
        f"🚖 Haydovchi: {call.from_user.full_name}\n"
        f"📞 Telefon: {driver_phone}"
    )

    await bot.send_message(
        driver_id,
        f"📍 Zakaz:\n{order[2]}\n👤 {order[4]}\n📞 {order[3]}"
    )

    await call.answer("✅ Zakaz sizniki")

# =======================
# 🚀 RUN
# =======================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
