import asyncio
import json
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config import BOT_TOKEN, ADMIN_ID, WEBHOOK_PATH, WEBHOOK_URL

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

CHANNELS_FILE = "channels.json"
AD_FILE = "ad.json"
STOP_AD = False

menu = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="➕ Kanal qo‘shish"), KeyboardButton(text="❌ Kanalni o‘chirish")],
    [KeyboardButton(text="✏️ Reklama kiritish"), KeyboardButton(text="🖼 Media yuklash")],
    [KeyboardButton(text="⏸ Reklamani to‘xtatish"), KeyboardButton(text="♻️ Reklamani yangilash")],
    [KeyboardButton(text="❌ Reklamani o‘chirish")]
])

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {} if 'ad' in path else []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

class Form(StatesGroup):
    channel = State()
    delete_channel = State()
    ad_text = State()
    ad_media = State()

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Kechirasiz, siz admin emassiz.")
    await message.answer("Reklama botiga xush kelibsiz!", reply_markup=menu)

@dp.message(F.text == "➕ Kanal qo‘shish")
async def ask_channel(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Kanal usernameni yuboring:")
    await state.set_state(Form.channel)

@dp.message(Form.channel)
async def save_channel(message: Message, state: FSMContext):
    chans = load_json(CHANNELS_FILE)
    chans.append(message.text)
    save_json(CHANNELS_FILE, chans)
    await message.answer("Kanal qo‘shildi.")
    await state.clear()

@dp.message(F.text == "❌ Kanalni o‘chirish")
async def ask_delete_channel(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("O‘chirmoqchi bo‘lgan kanal usernameni yuboring:")
    await state.set_state(Form.delete_channel)

@dp.message(Form.delete_channel)
async def delete_channel(message: Message, state: FSMContext):
    chans = load_json(CHANNELS_FILE)
    if message.text in chans:
        chans.remove(message.text)
        save_json(CHANNELS_FILE, chans)
        await message.answer("Kanal o‘chirildi.")
    else:
        await message.answer("Bunday kanal topilmadi.")
    await state.clear()

@dp.message(F.text == "✏️ Reklama kiritish")
async def ask_ad_text(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Reklama matnini yuboring:")
    await state.set_state(Form.ad_text)

@dp.message(Form.ad_text)
async def save_ad_text(message: Message, state: FSMContext):
    ad = load_json(AD_FILE)
    ad["text"] = message.text
    save_json(AD_FILE, ad)
    await message.answer("Reklama saqlandi.")
    await state.clear()

@dp.message(F.text == "🖼 Media yuklash")
async def ask_ad_media(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("Media fayl (rasm/video) yuboring:")
    await state.set_state(Form.ad_media)

@dp.message(Form.ad_media, F.content_type.in_({"photo", "video"}))
async def save_ad_media(message: Message, state: FSMContext):
    ad = load_json(AD_FILE)
    if message.photo:
        ad["photo"] = message.photo[-1].file_id
    elif message.video:
        ad["video"] = message.video.file_id
    save_json(AD_FILE, ad)
    await message.answer("Media saqlandi.")
    await state.clear()

@dp.message(F.text == "❌ Reklamani o‘chirish")
async def delete_ad(message: Message):
    if message.from_user.id != ADMIN_ID: return
    save_json(AD_FILE, {})
    await message.answer("Reklama o‘chirildi.")

@dp.message(F.text == "⏸ Reklamani to‘xtatish")
async def stop_ads(message: Message):
    global STOP_AD
    if message.from_user.id != ADMIN_ID: return
    STOP_AD = True
    await message.answer("Reklama to‘xtatildi.")

@dp.message(F.text == "♻️ Reklamani yangilash")
async def resume_ads(message: Message):
    global STOP_AD
    if message.from_user.id != ADMIN_ID: return
    STOP_AD = False
    await message.answer("Reklama davom etadi.")

async def send_ads():
    global STOP_AD
    while True:
        if not STOP_AD:
            ad = load_json(AD_FILE)
            chans = load_json(CHANNELS_FILE)
            for ch in chans:
                try:
                    if "photo" in ad:
                        await bot.send_photo(ch, ad["photo"], caption=ad.get("text", ""))
                    elif "video" in ad:
                        await bot.send_video(ch, ad["video"], caption=ad.get("text", ""))
                    elif "text" in ad:
                        await bot.send_message(ch, ad["text"])
                except Exception as e:
                    print(f"Xatolik: {e}")
        await asyncio.sleep(300)

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(send_ads())

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()

async def main():
    app = web.Application()
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    return app

if __name__ == "__main__":
    web.run_app(main())