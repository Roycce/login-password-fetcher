from telegram import Bot
import asyncio
from google.oauth2 import service_account
from googleapiclient.discovery import build
import re
import logging
from dotenv import load_dotenv
import os
load_dotenv()
script_dir = os.path.dirname(os.path.realpath(__file__))
class LoginPasswordFetcher:
    def __init__(self, service_account_file, bot_token, chat_id, document_id):
        self.service_account_file = service_account_file
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.document_id = document_id
        self.last_login = ''
        self.last_password = ''
        self.credentials = service_account.Credentials.from_service_account_file(
            self.service_account_file, scopes=['https://www.googleapis.com/auth/documents'])
        self.service = build('docs', 'v1', credentials=self.credentials)
        self.bot = Bot(token=self.bot_token)

    def get_login_and_password(self):
        try:
            doc = self.service.documents().get(documentId=self.document_id).execute()
            content = doc.get('body', {}).get('content', [])

            login = ''
            password = ''

            for element in content:
                if 'paragraph' in element:
                    paragraph_text = ''
                    for part in element['paragraph']['elements']:
                        if 'textRun' in part:
                            paragraph_text += part['textRun'].get('content', '')

                    if "Логин" in paragraph_text:
                        match = re.search(r"Логин\s*-\s*(\S+@\S+)", paragraph_text)
                        if match:
                            login = match.group(1)

                    if "Пароль" in paragraph_text:
                        match = re.search(r"Пароль\s*-\s*(\S+)", paragraph_text)
                        if match:
                            password = match.group(1)

            return login, password
        except Exception as e:
            logging.error(f"Error fetching document: {e}")
            return '', ''

    async def send_message_to_telegram(self, login, password):
        message = f"Данные обновились:\nЛогин: {login}\nПароль: {password}"
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
        except Exception as e:
            logging.error(f"Error sending message to Telegram: {e}")

    async def monitor_changes(self, check_interval):
        while True:
            login, password = self.get_login_and_password()

            if login != self.last_login or password != self.last_password:
                print("Данные обновились:")
                print(f"Логин: {login}")
                print(f"Пароль: {password}")

                await self.send_message_to_telegram(login, password)

                self.last_login = login
                self.last_password = password

            await asyncio.sleep(check_interval)

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    fetcher = LoginPasswordFetcher(
        service_account_file= os.path.join(script_dir, 'service_account_key.json'),
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        chat_id=os.getenv("TELEGRAM_CHAT_ID"),
        document_id=os.getenv("DOCUMENT_ID")
    )
    asyncio.run(fetcher.monitor_changes(3600))
