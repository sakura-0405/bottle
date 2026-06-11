from flask import Flask
from threading import Thread

# 建立一個 Flask 網頁應用程式
app = Flask('')

@app.route('/')
def home():
    """當有人瀏覽網頁首頁時回傳這段文字"""
    return "瓶子正在雲端順暢運作中！"

def run():
    # Render 部署時會自動分配 PORT 環境變數，如果沒有就預設使用 8080
    # host="0.0.0.0" 代表允許外網連線
    import os
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    """利用多線程 (Threading) 讓網頁跟 Discord Bot 可以同時並存執行"""
    t = Thread(target=run)
    t.start()