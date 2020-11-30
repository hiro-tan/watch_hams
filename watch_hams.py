#!/usr/bin/python

import os
from datetime import datetime
import adafruit_dht
from board import D18
import gspread

from linebot import LineBotApi
from linebot.models import TextSendMessage

spreadsheet_id = os.getenv('SPREADSHEET_ID')
RECORD_COUNT = 720

dht_device = adafruit_dht.DHT22(D18)
ALERT_TEMP_MIN = 20
ALERT_TEMP_MAX = 26
ALERT_INTERVAL = 10

channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_user_ids = os.getenv('LINE_USER_IDS').split(',')
line_bot_api = LineBotApi(channel_access_token)


def get_sheet():
    gc = gspread.service_account()
    sh = gc.open_by_key(spreadsheet_id)
    return sh.sheet1


def delete_old_data(sheet):
    sheet.add_rows(1)
    sheet.delete_rows(2)


def is_invalid_temp(temp):
    return temp < ALERT_TEMP_MIN or ALERT_TEMP_MAX < temp


def send_push_notification(values, temp):
    common_message = f'気温が{round(temp, 1)}℃になっています'
    if not values:
        line_bot_api.multicast(
            line_user_ids,
            TextSendMessage(text=common_message)
        )
        return True
    elif len(values) >= ALERT_INTERVAL \
        and all(list(map(
            lambda v: is_invalid_temp(float(v['temp']))
            and not bool(int(v['notified'])),
            values[-ALERT_INTERVAL:]))):
        line_bot_api.multicast(
            line_user_ids,
            TextSendMessage(text=f'不快な気温が続いています！\n{common_message}')
        )
        return True
    elif not is_invalid_temp(float(values[-1]['temp'])):
        line_bot_api.multicast(
            line_user_ids,
            TextSendMessage(text=common_message)
        )
        return True
    return False


def main():
    sheet = get_sheet()
    values = sheet.get_all_records()

    column_num = len(values)
    # データ数が RECORD_COUNT を超える場合は一番古いデータを削除する
    if column_num >= RECORD_COUNT:
        delete_old_data(sheet)
        column_num -= 1

    temp = dht_device.temperature
    humidity = dht_device.humidity
    # 温度が適温でない時はLINEでpush通知を送る
    # ただし直前の温度も適温でなかった時は連続では通知を送らない
    # ALERT_INTERVAL の間適温でない状態が続いた時は追加の通知を送る
    is_notified = False
    if is_invalid_temp(temp):
        is_notified = send_push_notification(values, temp)

    sheet.update(
        f'A{column_num + 2}:D',
        [[str(datetime.now()), temp, humidity, int(is_notified)]]
    )


if __name__ == '__main__':
    main()
