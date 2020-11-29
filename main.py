import os
import gspread
from flask import abort
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

spreadsheet_id = os.getenv('SPREADSHEET_ID')

channel_secret = os.getenv('LINE_CHANNEL_SECRET')
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)


def parse_request(request):
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)
    return events


def get_sheet():
    gc = gspread.service_account(filename='service_account.json')
    sh = gc.open_by_key(spreadsheet_id)
    return sh.sheet1


def select_temp_and_humidity(sheet):
    values = sheet.get_all_records()
    last = values[-1]
    return float(last['temp']), float(last['humidity'])


def create_response_text():
    sheet = get_sheet()
    temp, humidity = select_temp_and_humidity(sheet)
    return f'今の気温は{round(temp, 1)}℃で湿度は{round(humidity, 1)}％です'


def callback(request):
    events = parse_request(request)
    # for logging request contents
    print(events)

    for event in events:
        # テキスト形式のメッセージでない場合は何も返さない
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

        request_text = response_text = event.message.text
        if request_text in '気温' or request_text in '湿度':
            response_text = create_response_text()

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_text)
        )

    return 'OK'
