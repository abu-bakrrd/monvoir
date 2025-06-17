import telebot
from telebot import types
from rembg import remove
from PIL import Image
from io import BytesIO

TOKEN = '7560565832:AAFQXWb1QWbyg3kAh056pFTUML3yS9xLbrA'
bot = telebot.TeleBot(TOKEN)

ALLOWED_USERS = [5644397480, 796365934]  # замените на ваш user_id
user_images = {}
global_background = None  # Глобальное фоновое изображение
user_states = {} 


@bot.message_handler(commands=['start'])
def start(msg):
    if msg.from_user.id not in ALLOWED_USERS:
        return bot.reply_to(msg, "⛔️ У тебя нет доступа.")
    bot.send_message(msg.chat.id, "👋 Добро пожаловать в Monvoir Bot!\n\nОтправь фото с объектом, и я наложу его на установленный фон.\nДля замены фона используй команду /setbg")


@bot.message_handler(commands=['id'])
def send_user_id(msg):
    bot.send_message(msg.chat.id, f"🆔 Твой Telegram ID: `{msg.from_user.id}`", parse_mode="Markdown")


@bot.message_handler(commands=['setbg'])
def set_background_start(msg):
    if msg.from_user.id not in ALLOWED_USERS:
        return bot.reply_to(msg, "⛔️ Нет доступа.")
    bot.send_message(msg.chat.id, "📸 Отправь новое изображение для фона.")
    user_images[msg.chat.id] = {'awaiting_bg': True}


@bot.message_handler(content_types=['photo'])
def handle_photo(msg):
    chat_id = msg.chat.id
    user_id = msg.from_user.id

    if user_id not in ALLOWED_USERS:
        return bot.reply_to(msg, "⛔️ У тебя нет доступа.")

    file_info = bot.get_file(msg.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    image = Image.open(BytesIO(downloaded_file)).convert("RGBA")

    # Если пользователь хочет установить фон
    if chat_id in user_images and user_images[chat_id].get('awaiting_bg'):
        global global_background
        global_background = image
        user_images.pop(chat_id)
        return bot.send_message(chat_id, "✅ Фон успешно обновлён!")

    # Проверка: фон должен быть установлен
    if global_background is None:
        return bot.send_message(chat_id, "⚠️ Сначала установи фон с помощью /setbg")

    bot.send_message(chat_id, "🛠 Удаляю фон и размещаю изображение...")

    # Удаляем фон
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    no_bg = remove(buffered.getvalue())
    object_no_bg = Image.open(BytesIO(no_bg)).convert("RGBA")

    # Центрируем и масштабируем
    bg = global_background.copy()
    bg_w, bg_h = bg.size
    target_w, target_h = int(bg_w * 0.7), int(bg_h * 0.7)
    obj_w, obj_h = object_no_bg.size
    scale = min(target_w / obj_w, target_h / obj_h)
    new_size = (int(obj_w * scale), int(obj_h * scale))
    resized_object = object_no_bg.resize(new_size, Image.LANCZOS)
    pos = ((bg_w - new_size[0]) // 2, (bg_h - new_size[1]) // 2)
    bg.paste(resized_object, pos, resized_object)

    # Сохраняем обработанное изображение
    output = BytesIO()
    bg.save(output, format="PNG")
    output.seek(0)

    # Переход к шагу ввода цены
    user_states[chat_id] = {
        'image': output,
        'step': 'price'
    }
    bot.send_message(chat_id, "💰 Введите цену:")


@bot.message_handler(content_types=['text'])
def handle_text(msg):
    chat_id = msg.chat.id

    if chat_id not in user_states:
        return

    state = user_states[chat_id]

    if state['step'] == 'price':
        state['price'] = msg.text
        state['step'] = 'category'
        bot.send_message(chat_id, "🏷 Введите категорию (например, #одежда):")
    
    elif state['step'] == 'category':
        state['category'] = msg.text
        state['step'] = 'brand'
        bot.send_message(chat_id, "🧵 Введите бренд:")
    
    elif state['step'] == 'brand':
        state['brand'] = msg.text
        state['step'] = 'size'
        bot.send_message(chat_id, "📏 Введите размеры (например, S, M, L, 40-44):")
    
    elif state['step'] == 'size':
        state['size'] = msg.text
        image = state['image']

        caption = (
            f"🖤 <b>𝗠𝗢𝗡𝗩𝗢𝗜𝗥</b> | Эстетика в каждой детали\n\n"
            f"✨ Всё в люксовом качестве. Отборные модели, продуманные до мелочей.\n\n"
            f"💸 <b>Цена:</b> <code>{state['price']}</code>\n"
            f"🏷 <b>Категория:</b> {state['category']}\n"
            f"👔 <b>Бренд:</b> {state['brand']}\n"
            f"📏 <b>Размеры:</b> {state['size']}\n\n"
            f"🚚 <b>Доставка:</b> 7–11 дней по Узбекистану\n"
            f"📦 <i>Ограниченный тираж. Успей оформить до распродажи!</i>"
        )


        image.seek(0)
        bot.send_photo(chat_id, image, caption=caption, parse_mode="HTML    ")
        user_states.pop(chat_id)


bot.polling(none_stop=True)