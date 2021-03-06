# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from linebot.models import *
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot import (
    LineBotApi, WebhookParser
)
from flask import Flask, request, abort
from imgurpython import ImgurClient
import pandas as pd
import matplotlib.pyplot as plt

import os
import random
import time
from datetime import timedelta, datetime
from pymongo import MongoClient

# ref: http://twstock.readthedocs.io/zh_TW/latest/quickstart.html#id2
import twstock

import matplotlib
matplotlib.use('Agg')  # ref: https://matplotlib.org/faq/howto_faq.html


app = Flask(__name__)


channel_secret_8 = os.environ.get("CHANNEL_SECRET")
channel_access_token_8 = os.environ.get("CHANNEL_ACCESS_TOKEN")

line_bot_api_8 = LineBotApi(channel_access_token_8)  # 傳送
parser_8 = WebhookParser(channel_secret_8)  # 接收


# ===================================================
#   stock bot
# ===================================================
@app.route("/callback_yangbot8", methods=['POST'])
def callback_yangbot8():
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser_8.parse(body, signature)  
    except InvalidSignatureError:
        abort(400)

    for event in events:
        if not isinstance(event, MessageEvent):  # 判斷是否為訊息事件
            continue
        if not isinstance(event.message, TextMessage):  # 判斷是否為文字
            continue

        text = event.message.text
        #userId = event['source']['userId']
        if(text.lower() == 'me'):
            content = str(event.source.user_id)

            line_bot_api_8.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
        elif(text.lower() == 'profile'):
            profile = line_bot_api_8.get_profile(event.source.user_id)
            my_status_message = profile.status_message
            if not my_status_message:
                my_status_message = '-'
            line_bot_api_8.reply_message(
                event.reply_token, [
                    TextSendMessage(
                        text='Display name: ' + profile.display_name
                    ),
                    TextSendMessage(
                        text='picture url: ' + profile.picture_url
                    ),
                    TextSendMessage(
                        text='status_message: ' + my_status_message
                    ),
                ]
            )

        elif(text.startswith('#')):
            text = text[1:]
            content = ''

            stock_rt = twstock.realtime.get(text)
            my_datetime = datetime.fromtimestamp(stock_rt['timestamp']+8*60*60)
            my_time = my_datetime.strftime('%H:%M:%S')

            content += '%s (%s) %s\n' % (
                stock_rt['info']['name'],
                stock_rt['info']['code'],
                my_time)
            content += '現價: %s / 開盤: %s\n' % (
                stock_rt['realtime']['latest_trade_price'],
                stock_rt['realtime']['open'])
            content += '最高: %s / 最低: %s\n' % (
                stock_rt['realtime']['high'],
                stock_rt['realtime']['low'])
            content += '量: %s\n' % (stock_rt['realtime']
                                    ['accumulate_trade_volume'])

            stock = twstock.Stock(text)  # twstock.Stock('2330')
            content += '-----\n'
            content += '最近五日價格: \n'
            price5 = stock.price[-5:][::-1]
            date5 = stock.date[-5:][::-1]
            for i in range(len(price5)):
                #content += '[%s] %s\n' %(date5[i].strftime("%Y-%m-%d %H:%M:%S"), price5[i])
                content += '[%s] %s\n' % (date5[i].strftime("%Y-%m-%d"),
                                          price5[i])
            line_bot_api_8.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )

        elif(text.startswith('/')):
            text = text[1:]
            fn = '%s.png' % (text)
            stock = twstock.Stock(text)
            my_data = {'close': stock.close,
                       'date': stock.date, 'open': stock.open}
            df1 = pd.DataFrame.from_dict(my_data)

            df1.plot(x='date', y='close')
            plt.title('[%s]' %(stock.sid))
            plt.savefig(fn)
            plt.close()

            # -- upload
            # imgur with account: your.mail@gmail.com
            client_id = os.environ.get("IMGUR_ID")
            client_secret = os.environ.get("IMGUR_SECRET")

            client = ImgurClient(client_id, client_secret)
            print("Uploading image... ")
            image = client.upload_from_path(fn, anon=True)
            print("Done")

            url = image['link']
            image_message = ImageSendMessage(
                original_content_url=url,
                preview_image_url=url
            )

            line_bot_api_8.reply_message(
                event.reply_token,
                image_message
            )

        elif(text.startswith('$')):
            text = text[1:]
            print(text)
            stock = twstock.Stock(text)
            bfp = twstock.BestFourPoint(stock)

            print(bfp.best_four_point())
            content = "建議做多，因為:\n" if bfp.best_four_point()[
                0] else "建議放空，因為:\n"
            content += bfp.best_four_point()[1]

            line_bot_api_8.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )
            
        else:
            content = "歡迎使用STOCK股票小精靈!( ^ω^)\n基礎功能請輸入:\n#股票代號 查詢即時股價。\n/股票代號 觀看股票線圖。\n$股票代號 觀看簡單分析。"
            line_bot_api_8.reply_message(
                event.reply_token,
                TextSendMessage(text=content)
            )

    return 'OK'


@app.route("/", methods=['GET'])
def basic_url():
    return 'OK'


if __name__ == "__main__":
    app.run()
