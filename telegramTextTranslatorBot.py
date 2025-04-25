import telebot
from telebot import types
from googletrans import Translator
from db import get_connection


with open('/home/alex/Documents/Python/files/TOKEN.txt', 'r') as file:
    bot = telebot.TeleBot(file.read().strip())

translator = Translator()

@bot.message_handler(content_types=['new_chat_members'])
def new_member_handler(message):
    conn = get_connection()
    cur = conn.cursor()
    for new_member in message.new_chat_members:
        if new_member.id == bot.get_me().id:
            cur.execute("SELECT EXISTS (SELECT 1 FROM chats WHERE id = %s);", (message.chat.id,))
            exists = cur.fetchone()[0]

            if not exists:
                cur.execute("INSERT INTO chats (id) VALUES (%s);", (message.chat.id,))
    
    conn.commit()
    cur.close()
    conn.close()
            


@bot.message_handler(commands=['language'])
def commands(message):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Русский", callback_data='ru')
    button2 = types.InlineKeyboardButton("English", callback_data='en')
    button3 = types.InlineKeyboardButton("Français", callback_data='fr')
    markup.add(button1, button2, button3)
    bot.send_message(message.chat.id, "Choose a language", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    conn = get_connection()
    cur = conn.cursor()
    bot.send_message(call.message.chat.id, translator.translate("Language selected", src='en', dest=call.data).text)

    cur.execute("SELECT EXISTS (SELECT 1 FROM users WHERE id = %s);", (call.from_user.id,))
    exists = cur.fetchone()[0]


    if exists:
        cur.execute("UPDATE users SET language =%s WHERE id = %s;", (call.data, call.from_user.id))

    else:
        cur.execute("INSERT INTO users (id, language) VALUES (%s, %s);", (call.from_user.id, call.data))
    

    cur.execute("SELECT EXISTS (SELECT 1 FROM chats WHERE id = %s);", (call.message.chat.id,))
    exists = cur.fetchone()[0]
    if not exists:
        cur.execute("INSERT INTO chats (id) VALUES (%s);", (call.message.chat.id,))

    cur.execute("SELECT EXISTS (SELECT * FROM chats WHERE %s = ANY(languages) AND id = %s);", (call.data, call.message.chat.id))
    exists = cur.fetchone()[0]
    if not exists:
        cur.execute("UPDATE chats SET languages =  array_append(languages, %s) WHERE id = %s;", (call.data, call.message.chat.id))


    conn.commit()
    cur.close()
    conn.close()

@bot.message_handler()
def main(message):
    conn = get_connection()
    cur = conn.cursor()
    user_lang = ''
    languages = ''

    cur.execute("SELECT language FROM users WHERE id = %s;", (message.from_user.id,))
    try:
        user_lang = cur.fetchone()[0]
    except:
        print("User not specified his language")
    cur.execute("SELECT languages FROM chats WHERE id = %s;", (message.chat.id,))
    try:
        languages = cur.fetchone()[0]
    except:
        print("Chat has no specified languages")

    if languages:
        if user_lang:
            for language in languages:
                print(language)
                if language != user_lang:
                    result = translator.translate(message.text, src=user_lang, dest=language)
                    bot.reply_to(message, result.text)
        else:
            for language in languages[0]:
                print(language)
                result = translator.translate(message.text, dest=language)
                bot.reply_to(message, result.text)



    conn.commit()
    cur.close()
    conn.close()


bot.polling(none_stop=True)

