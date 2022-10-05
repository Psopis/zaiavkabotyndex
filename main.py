import base64

import asyncio

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import email
import imaplib
from aiogram import Bot, Dispatcher, executor, types
import psycopg2

loop = asyncio.get_event_loop()

BOT_TOKEN = "1750619081:AAHGHAfO-aNp6yg-TKW41UP-88b1OWp8lXk"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, loop=loop)

imapHost = 'imap.yandex.ru'
imapUser = 'experttvoi1@yandex.ru'
imapPasscode = 'experttvoi165Q'
# imapHost = 'imap.mail.ru'
# imapUser = 'konevvik05@mail.ru'
# imapPasscode = 'FSTMaH6UjvRx7gCGWABc'

imap_conn = imaplib.IMAP4_SSL(imapHost)
imap_conn.login(imapUser, imapPasscode)


def login(mailbox):
    print('Logging in again')
    imap_conn = imaplib.IMAP4_SSL(imapHost)
    imap_conn.login(imapUser, imapPasscode)
    lastmsg = imap_conn.select('INBOX')[-1]
    return lastmsg


conn = psycopg2.connect(
    host="localhost",
    database="postgres",
    user="postgres",
    password="29012005"
)


class email_class:
    def __init__(self, text, uid):
        anketa = text.split("Имя")[1].split("Возраст")[0]
        contact = text.split("Удобный способ связи:")[1]
        self.text = text
        self.uid = uid
        self.contact = f"{contact}"


def insert_quantity(quan, conn):
    cur = conn.cursor()
    cur.execute("""UPDATE old_mails_quantity SET mail_quantity= (%(quan)s)""", {'quan': quan})
    conn.commit()


def select_quantity(conn):
    cur = conn.cursor()
    cur.execute("""select mail_quantity from old_mails_quantity""")
    conn.commit()
    return cur.fetchone()[0]


class text_frommail_tocontactandtxt:
    def __init__(self, text):
        anketa = text.split("Имя:")[1].split("Возраст")[0]
        contact = text.split("Удобный")[1]
        # self.text = text.split("Контакты")[0]
        self.fulltext = f"{anketa} \n{contact}"


def decode_mail_to_text(raw):
    for part in raw.walk():
        if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'plain':
            decode_text = base64.b64decode(part.get_payload()).decode()
            return text_frommail_tocontactandtxt(decode_text)


def get_first_text_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
    elif maintype == 'text':
        return email_message_instance.get_payload()


def get_email(imap_conn, uid_mail):
    uid = uid_mail
    print(f"uid --- {uid}")
    print(f"isinstance --- {isinstance(uid_mail, list)}")
    if isinstance(uid_mail, list):
        uid = uid_mail[0]
    result, data = imap_conn.uid('fetch', uid, '(RFC822)')
    not_formated_text_fromMail = email.message_from_bytes(data[0][1])

    print(not_formated_text_fromMail['subject'])
    decode_subject = base64.b64decode(str(not_formated_text_fromMail['subject']).split('?')[3]).decode()
    text = get_first_text_block(not_formated_text_fromMail)
    if decode_subject == "Запрос общий":
        print(text)
        replaced_text = text.replace("<br>", "").split("Date")[0].replace('-', '').replace('Запрос общий', '')
        return email_class(replaced_text, uid_mail)
    return False


def write_in_file(num):
    file = open("number_of_last_message.txt", "w")
    file.write(num)
    file.close()


def read_from_file():
    file = open("number_of_last_message.txt", "r")
    readed = file.read()
    file.close()
    return int(readed)


def zaiavka_keyboard(contacts, id):
    keyboard = InlineKeyboardMarkup(row_width=1).insert(
        InlineKeyboardButton(text="Ответить на заявку", callback_data=f"uid_mail.{contacts}.{id}")
    )

    return keyboard


@dp.callback_query_handler(text_contains="uid_mail")
async def accept_query(call: types.CallbackQuery):
    fulltext = call.data.split(".")[1]
    user = call.from_user.id
    id = call.data.split(".")[2]
    await bot.send_message(text=f"Вы ответили на заявку №{id}\n Удобный способ связи: {fulltext}", chat_id=user)
    await call.message.edit_reply_markup()


@dp.message_handler(text="/start")
async def start():
    print()


async def email_checker():
    number_of_mail = 0
    while True:
        print("start")
        try:
            lastmsg = imap_conn.select('INBOX')[-1]
        except Exception as e:
            lastmsg = login('inbox')
        allmails = int(lastmsg[0])
        all_mails_old = read_from_file()
        for i in range(all_mails_old, allmails):
            _, uid_mail = imap_conn.uid('search', None, str(i))
            mail_textUid = get_email(imap_conn, uid_mail)

            if not mail_textUid:
                print("Не то что нужно")
                break
            else:
                number_of_mail += 1
                print(1)
                print(mail_textUid.text)
                # print(decode_mail_to_text(mail_textUid.text))
                await bot.send_message(chat_id=-1001891807208,
                                       text=f"№{number_of_mail}\n{mail_textUid.text}",
                                       reply_markup=zaiavka_keyboard(mail_textUid.contact, number_of_mail))

        write_in_file(str(allmails))

        await asyncio.sleep(5)


if __name__ == "__main__":
    dp.loop.create_task(email_checker())
    executor.start_polling(dp, skip_updates=True)
