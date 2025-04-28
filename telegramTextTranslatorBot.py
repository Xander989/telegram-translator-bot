import telebot
from telebot import types
from googletrans import Translator
from db import get_connection
import json
import os


script_dir = os.path.dirname(os.path.abspath(__file__))
token_path = os.path.join(script_dir, 'TOKEN.txt')
with open(token_path, 'r') as file:
    bot = telebot.TeleBot(file.read().strip())


with open('languages.json', 'r') as file:
    languages = json.load(file)

code_to_name = {}

for lang in languages:
    code = lang['code']
    name = lang['name']
    code_to_name[code] = name

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

    for lang in languages:
        button = types.InlineKeyboardButton(lang['name'], callback_data=lang['code'])
        markup.add(button)
    bot.send_message(message.chat.id, "Choose a language", reply_markup=markup)


# Add or Remove a language to a chat.
@bot.message_handler(commands=['chatlanguage'])
def commands(message):
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Add a language", callback_data='add')
    button2 = types.InlineKeyboardButton("Remove a language", callback_data='remove')
    markup.add(button1, button2)
    bot.send_message(message.chat.id, "Configure chat's languages", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'add')
def handle_callback(call):
    conn = get_connection()
    cur = conn.cursor()
    markup = types.InlineKeyboardMarkup()

    cur.execute("SELECT languages FROM chats WHERE id = %s", (call.message.chat.id,))
    chat_langs = cur.fetchone()[0]
    print(chat_langs)
    temp_langs = languages
    for clang in chat_langs:
        temp_langs = [lang for lang in temp_langs if lang['code'] != clang]
    for lang in temp_langs:
        button = types.InlineKeyboardButton(lang['name'], callback_data="add_" + lang['code'])
        markup.add(button)
    
    bot.send_message(call.message.chat.id, "Choose a language to add", reply_markup=markup)

    conn.commit()
    cur.close()
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith("add_"))
def handle_callback(call):
    conn = get_connection()
    cur = conn.cursor()


    temp = call.data
    lang = temp.replace("add_", "")

    cur.execute("SELECT languages FROM chats WHERE id = %s", (call.message.chat.id,))
    chat_langs = cur.fetchone()[0]
    print(chat_langs)
    chat_langs.append(lang)
    
    cur.execute("UPDATE chats SET languages = %s WHERE id = %s", (chat_langs, call.message.chat.id))
    bot.send_message(call.message.chat.id, "Language sucessfully added")

    conn.commit()
    cur.close()
    conn.close()

# Remove a language from a chat.
@bot.callback_query_handler(func=lambda call: call.data == 'remove')
def handle_callback(call):
    conn = get_connection()
    cur = conn.cursor()
    markup = types.InlineKeyboardMarkup()
    cur.execute("SELECT languages FROM chats WHERE id = %s", (call.message.chat.id,))
    languages = cur.fetchone()[0]
    if languages:
        for lang in languages:
            button = types.InlineKeyboardButton(code_to_name[lang], callback_data="remove_" + str(lang))
            markup.add(button)
        bot.send_message(call.message.chat.id, "Choose a language to remove", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "This chat has no added languages")


    
    conn.commit()
    cur.close()
    conn.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_"))
def handle_callback(call):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT languages FROM chats WHERE id = %s;", (call.message.chat.id,))
    languages = cur.fetchone()[0]
    temp = call.data
    lang = temp.replace("remove_", "")
    print(lang)
    print(languages)
    if languages:
        if lang in languages:
            languages.remove(lang)
            cur.execute("UPDATE chats SET languages = %s WHERE id = %s;", (languages, call.message.chat.id))
            bot.send_message(call.message.chat.id, "Language successfully removed")


    

    
    conn.commit()
    cur.close()
    conn.close()

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

