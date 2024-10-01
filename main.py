import os
import random

from telebot import types, TeleBot, custom_filters
from telebot.states import StatesGroup, State
from telebot.storage import StateMemoryStorage

from DB.db_funcs import add_connect, add_user, get_target_word, get_other_words_for_answer, check_user, add_user_words, \
    delete_words

try:
    conn = add_connect()
except Exception as e:
    print(f'Не удалось подключиться к базе данных: {e}')
    exit(1)

print('Start telegram bot...')

cursor = conn.cursor()

state_storage = StateMemoryStorage()
token_bot = os.getenv('TG_TOKEN')
bot = TeleBot(token_bot, state_storage=state_storage)

buttons = []


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()
    add_word = State()
    delete_word = State()


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    user = check_user(cid)
    if not user:
        add_user(cid)
        bot.send_message(cid,
                         "Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном "
                         "для себя темпе"
                         "У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную "
                         "базу для обучения. Для этого воспользуйтесь инструментами:\n"
                         "- добавить слово ➕,\n- удалить слово 🔙.\nНу что, начнём ⬇️")
    else:
        bot.send_message(cid, "Продолжим?")

    markup = types.ReplyKeyboardMarkup(row_width=2)
    global buttons
    buttons = []

    target_word, translate = get_target_word(cid)

    target_word_btn = types.KeyboardButton(translate)

    others = get_other_words_for_answer(cid, target_word)
    other_words_buttons = [types.KeyboardButton(word) for word in others]

    buttons = [target_word_btn] + other_words_buttons
    random.shuffle(buttons)

    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {target_word}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)

    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_card(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text not in [Command.ADD_WORD, Command.DELETE_WORD],
                     content_types=['text'])
def message_reply(message):
    text = message.text.strip()
    markup = types.ReplyKeyboardMarkup(row_width=2)

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data.get('translate_word')
        if target_word is None:
            bot.send_message(message.chat.id, "Целевое слово не найдено.")
            return

        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤️", hint]
            hint = show_hint(*hint_text)
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❤️'
                    break
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            else:
                bot.send_message(message.chat.id, "Кнопка не найдена.")
                return

            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['target_word']}")

    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    bot.send_message(cid, "Введите слово на русском и английском языке ЧЕРЕЗ ПРОБЕЛ,"
                          " для добавления в таблицу слов:")
    bot.register_next_step_handler(message, user_input)


def user_input(message):
    cid = message.chat.id
    words = str(message.text).lower().strip().split()

    if len(words) != 2:
        bot.send_message(cid, "Пожалуйста, введите два слова через пробел.")
        return

    rus_word, eng_word = words

    try:
        if add_user_words(rus_word, eng_word, cid):
            bot.send_message(cid, "Добавлена новая пара слов")
        else:
            bot.send_message(cid, "Слово уже присутствует в таблице")
    except Exception as error:
        bot.send_message(cid, f"Произошла ошибка при добавлении слова: {error}")

    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    cid = message.chat.id
    bot.send_message(cid, "Введите слово на английском или на русском для удаления:")
    bot.register_next_step_handler(message, user_input_for_delete)


def user_input_for_delete(message):
    cid = message.chat.id
    word_to_delete = str(message.text).strip().lower()

    try:
        if delete_words(word_to_delete, cid):
            bot.send_message(cid, "Слово удалено")
        else:
            bot.send_message(cid, "Вы можете удалить только те слова, которые добавили сами.")
    except Exception as error:
        bot.send_message(cid, f"Произошла ошибка при удалении слова: {error}")

    create_cards(message)




if __name__ == '__main__':
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.infinity_polling(skip_pending=True)
