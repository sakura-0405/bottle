import os
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, redirect, session, render_template_string
from threading import Thread

app = Flask('')
app.secret_key = os.getenv("SECRET_KEY", "bottle_secret_random_key_12345")

db = None
discord_bot = None
API_ENDPOINT = 'https://discord.com/api/v10'

# ================= HTML 範本區 =================
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>瓶子 Bot 控制面板</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #2f3136; color: white; padding: 40px; text-align: center; }
        .container { max-width: 600px; margin: 0 auto; }
        .btn { background: #5865F2; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; font-size: 16px; display: inline-block; }
        .btn:hover { background: #4752C4; }
        .guild-card { background: #36393f; padding: 20px; margin: 15px auto; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .guild-name { font-size: 18px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🍾 瓶子 機器人控制面板</h1>
        <hr style="border-color: #4f545c; margin: 20px 0;">
        
        {% if not logged_in %}
            <p>歡迎！請先登入 Discord 帳號以管理你的伺服器設定。</p>
            <br>
            <a class="btn" href="{{ login_url }}">使用 Discord 登入</a>
        {% else %}
            <p>你好！請選擇你要設定的伺服器：</p>
            <div style="margin-top: 20px;">
                {% for guild in guilds %}
                    <div class="guild-card">
                        <span class="guild-name">{{ guild.name }}</span>
                        {% if guild.bot_in %}
                            <a class="btn" style="background: #23a55a;" href="/manage/{{ guild.id }}">進入設定</a>
                        {% else %}
                            <a class="btn" style="background: #4f545c;" href="https://discord.com/oauth2/authorize?client_id={{ client_id }}&permissions=8&scope=bot%20applications.commands&guild_id={{ guild.id }}&disable_guild_select=true&redirect_uri={{ redirect_uri }}&response_type=code">邀請機器人</a>
                        {% endif %}
                    </div>
                {% endfor %}
            </div>
            <br><br>
            <a href="/logout" style="color: #ed4245; text-decoration: none;">登出帳號</a>
        {% endif %}
    </div>
</body>
</html>
"""

MANAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>管理 - {{ guild_name }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #2f3136; color: white; padding: 40px; }
        .container { max-width: 650px; margin: 0 auto; background: #36393f; padding: 30px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
        .section-box { background: #2f3136; padding: 20px; border-radius: 8px; margin-bottom: 25px; border-left: 5px solid #5865F2; }
        .form-group { margin-bottom: 25px; text-align: left; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #b9bbbe; }
        select, input[type="text"], textarea { width: 100%; padding: 10px; background: #202225; color: white; border: 1px solid #202225; border-radius: 5px; font-size: 16px; box-sizing: border-box; }
        textarea { font-family: inherit; resize: vertical; min-height: 100px; }
        .btn { background: #23a55a; color: white; padding: 12px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; width: 100%; font-weight: bold; }
        .btn:hover { background: #1a7f43; }
        .btn-add { background: #5865F2; color: white; width: auto; padding: 8px 15px; font-size: 14px; margin-top: 10px; }
        .btn-add:hover { background: #4752C4; }
        .btn-del { background: #ed4245; color: white; border: none; padding: 10px; border-radius: 5px; cursor: pointer; font-weight: bold; }
        .btn-del:hover { background: #c93b3e; }
        .button-row { display: flex; gap: 10px; margin-bottom: 10px; align-items: center; }
        .back-link { display: block; text-align: center; margin-top: 20px; color: #00b0f4; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>⚙️ 伺服器進階設定面板</h2>
        <h4 style="color: #b9bbbe; margin-top: -10px;">{{ guild_name }}</h4>
        <hr style="border-color: #4f545c; margin: 20px 0;">
        
        <form action="/save/{{ guild_id }}" method="POST">
            
            <div class="section-box">
                <h3 style="margin-top: 0; color: #5865F2;">✨ 基本自動化頻道</h3>
                <div class="form-group">
                    <label for="welcome_channel">✨ 新成員歡迎文字頻道</label>
                    <select name="welcome_channel" id="welcome_channel">
                        <option value="">-- 未啟用功能（不發送） --</option>
                        {% for ch in text_channels %}
                            <option value="{{ ch.id }}" {% if ch.id == current_welcome %}selected{% endif %}># {{ ch.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="voice_channel">➕ 動態語音創房頻道（點我創房）</label>
                    <select name="voice_channel" id="voice_channel">
                        <option value="">-- 未啟用功能（不創房） --</option>
                        {% for ch in voice_channels %}
                            <option value="{{ ch.id }}" {% if ch.id == current_voice %}selected{% endif %}>🔊 {{ ch.name }}</option>
                        {% endfor %}
                    </select>
                </div>
            </div>

            <div class="section-box" style="border-left-color: #f5a623;">
                <h3 style="margin-top: 0; color: #f5a623;">🔘 自訂按鈕領取身分組功能</h3>
                <p style="font-size: 13px; color: #b9bbbe; margin-top: -5px;">設定完成後，可在 Discord 輸入 <code>/setup_roles</code> 召喚出該功能面板。</p>
                
                <div class="form-group">
                    <label>📝 身分組說明框（Embed）標題</label>
                    <input type="text" name="role_embed_title" value="{{ current_embed_title }}" placeholder="例如：領取你的自訂身分組！">
                </div>
                <div class="form-group">
                    <label>💬 身分組說明框（Embed）敘述內容（支援換行與 Discord 語法）</label>
                    <textarea name="role_embed_desc" placeholder="請點擊下方按鈕領取身分組：&#10;➡️ 遊戲咖：解鎖遊戲聊天專區&#10;➡️ 通知咖：接收最新公告通知">{{ current_embed_desc }}</textarea>
                </div>

                <div class="form-group">
                    <label>🎛️ 按鈕與對應身分組規則設定</label>
                    <div id="button-container">
                        {% if current_buttons %}
                            {% for btn in current_buttons %}
                            <div class="button-row">
                                <input type="text" name="btn_label[]" value="{{ btn.label }}" placeholder="按鈕文字（如：遊戲咖）" style="flex: 2;" required>
                                <select name="btn_role[]" style="flex: 3;" required>
                                    <option value="">-- 選擇目標身分組 --</option>
                                    {% for role in roles %}
                                        <option value="{{ role.id }}" {% if role.id == btn.role_id %}selected{% endif %}>@ {{ role.name }}</option>
                                    {% endfor %}
                                </select>
                                <button type="button" class="btn-del" onclick="removeRow(this)">❌</button>
                            </div>
                            {% endfor %}
                        {% else %}
                            <div class="button-row">
                                <input type="text" name="btn_label[]" placeholder="按鈕文字（如：公告通知）" style="flex: 2;">
                                <select name="btn_role[]" style="flex: 3;">
                                    <option value="">-- 選擇目標身分組 --</option>
                                    {% for role in roles %}
                                        <option value="{{ role.id }}">@ {{ role.name }}</option>
                                    {% endfor %}
                                </select>
                                <button type="button" class="btn-del" onclick="removeRow(this)">❌</button>
                            </div>
                        {% endif %}
                    </div>
                    <button type="button" class="btn btn-add" onclick="addRow()">➕ 新增按鈕規則</button>
                </div>
            </div>
            
            <button type="submit" class="btn">💾 儲存所有進階設定</button>
        </form>
        
        <a class="back-link" href="/">← 返回伺服器清單</a>
    </div>

    <script>
        const rolesData = [
            {% for role in roles %}
                { id: "{{ role.id }}", name: "{{ role.name }}" },
            {% endfor %}
        ];

        function addRow() {
            const container = document.getElementById('button-container');
            const row = document.createElement('div');
            row.className = 'button-row';
            
            let optionsHtml = '<option value="">-- 選擇目標身分組 --</option>';
            rolesData.forEach(role => {
                optionsHtml += `<option value="${role.id}">@ ${role.name}</option>`;
            });

            row.innerHTML = `
                <input type="text" name="btn_label[]" placeholder="按鈕文字" style="flex: 2;" required>
                <select name="btn_role[]" style="flex: 3;" required>
                    ${optionsHtml}
                </select>
                <button type="button" class="btn-del" onclick="removeRow(this)">❌</button>
            `;
            container.appendChild(row);
        }

        function removeRow(btn) {
            const row = btn.parentElement;
            row.remove();
        }
    </script>
</body>
</html>
"""

# ================= 路由核心區 =================

@app.route('/')
def home():
    client_id = os.getenv("CLIENT_ID")
    redirect_uri = os.getenv("REDIRECT_URI", "http://127.0.0.1:8080/callback")
    
    if 'token' not in session:
        login_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=identify%20guilds"
        return render_template_string(INDEX_TEMPLATE, logged_in=False, login_url=login_url)
    
    try:
        headers = {'Authorization': f"Bearer {session['token']}"}
        guilds_res = requests.get(f"{API_ENDPOINT}/users/@me/guilds", headers=headers, timeout=5).json()
    except Exception as e:
        print(f"[Web 錯誤] 無法取得使用者伺服器清單: {e}")
        return "無法連線到 Discord API，請重新登入試試。", 502
    
    manageable_guilds = []
    if isinstance(guilds_res, list) and discord_bot:
        bot_guild_ids = [str(g.id) for g in discord_bot.guilds]
        for g in guilds_res:
            perms = int(g.get('permissions', 0))
            if (perms & 0x8) == 0x8:
                g['bot_in'] = str(g['id']) in bot_guild_ids
                g['id'] = str(g['id'])
                manageable_guilds.append(g)

    return render_template_string(INDEX_TEMPLATE, logged_in=True, guilds=manageable_guilds, client_id=client_id, redirect_uri=redirect_uri)

@app.route('/manage/<string:guild_id>')
def manage(guild_id):
    if 'token' not in session:
        return redirect('/')
        
    print(f"[Web 記錄] 收到進入設定請求！伺服器 ID: {guild_id}")
    bot_token = os.getenv("DISCORD_TOKEN")
    
    if not bot_token:
        return "環境變數中缺少 DISCORD_TOKEN，後端無法調用 API", 500

    headers = {'Authorization': f"Bot {bot_token}"}

    guild_name = "Discord 伺服器"
    try:
        g_res = requests.get(f"{API_ENDPOINT}/guilds/{guild_id}", headers=headers, timeout=5).json()
        guild_name = g_res.get('name', 'Discord 伺服器')
    except Exception as e:
        print(f"[Web 警告] 無法透過 API 獲取伺服器名稱: {e}")

    roles = []
    try:
        roles_res = requests.get(f"{API_ENDPOINT}/guilds/{guild_id}/roles", headers=headers, timeout=5).json()
        if isinstance(roles_res, list):
            for r in roles_res:
                if str(r.get('id')) != guild_id and not r.get('managed'):
                    roles.append({"id": str(r.get('id')), "name": r.get('name')})
    except Exception as e:
        print(f"[Web 錯誤] 獲取身分組清單失敗: {e}")

    current_welcome = ""
    current_voice = ""
    current_embed_title = "🍾 自訂身分組領取專專區"
    current_embed_desc = "點擊下方對應的按鈕即可領取或移除身分組。"
    current_buttons = []
    
    if db is not None:
        try:
            print("[Web 記錄] 正在向 Firestore 撈取設定資料...")
            doc_ref = db.collection('guild_settings').document(guild_id)
            doc = doc_ref.get(timeout=1)
            if doc.exists:
                data = doc.to_dict()
                current_welcome = str(data.get('welcome_channel', ''))
                current_voice = str(data.get('voice_channel', ''))
                current_embed_title = data.get('role_embed_title', current_embed_title)
                current_embed_desc = data.get('role_embed_desc', current_embed_desc)
                current_buttons = data.get('role_buttons', [])
                print("[Web 記錄] 成功撈取 Firestore 歷史設定！")
        except BaseException as e:
            print(f"[Web ⚠️ 異常強制放行] Firestore 連線無回應，已秒級跳過。原因: {e}")

    print("[Web 記錄] 正在透過 REST API 獲取頻道清單...")
    text_channels = []
    voice_channels = []
    try:
        channels_res = requests.get(f"{API_ENDPOINT}/guilds/{guild_id}/channels", headers=headers, timeout=5).json()
        if isinstance(channels_res, list):
            for ch in channels_res:
                ch_type = int(ch.get('type', 0))
                if ch_type == 0:
                    text_channels.append({"id": str(ch.get('id')), "name": ch.get('name')})
                elif ch_type == 2:
                    voice_channels.append({"id": str(ch.get('id')), "name": ch.get('name')})
    except Exception as e:
        print(f"[Web 錯誤] 透過 API 獲取頻道失敗: {e}")
        return "無法安全獲取伺服器頻道清單，請確認 Bot Token 是否正確且具備權限。", 500
    
    print("[Web 記錄] 設定頁面加載完成，正在渲染前端！")
    return render_template_string(
        MANAGE_TEMPLATE,
        guild_name=guild_name,
        guild_id=guild_id,
        text_channels=text_channels,
        voice_channels=voice_channels,
        roles=roles,
        current_welcome=current_welcome,
        current_voice=current_voice,
        current_embed_title=current_embed_title,
        current_embed_desc=current_embed_desc,
        current_buttons=current_buttons
    )

@app.route('/save/<string:guild_id>', methods=['POST'])
def save_config(guild_id):
    if db is None:
        return "資料庫尚未初始化", 500
        
    welcome_ch = request.form.get('welcome_channel')
    voice_ch = request.form.get('voice_channel')
    embed_title = request.form.get('role_embed_title')
    embed_desc = request.form.get('role_embed_desc')
    
    labels = request.form.getlist('btn_label[]')
    roles = request.form.getlist('btn_role[]')
    
    role_buttons = []
    for label, role_id in zip(labels, roles):
        if label.strip() and role_id.strip():
            role_buttons.append({
                "label": label.strip(),
                "role_id": str(role_id).strip()
            })
    
    print(f"[Web 記錄] 正在將多重設定整合更新至 Firestore，伺服器 ID: {guild_id}")
    try:
        doc_ref = db.collection('guild_settings').document(guild_id)
        doc_ref.set({
            'welcome_channel': str(welcome_ch) if welcome_ch else "",
            'voice_channel': str(voice_ch) if voice_ch else "",
            'role_embed_title': str(embed_title) if embed_title else "🍾 自訂身分組領取專區",
            'role_embed_desc': str(embed_desc) if embed_desc else "點擊下方對應的按鈕即可領取或移除身分組。",
            'role_buttons': role_buttons
        }, merge=True)
        print("[Web 記錄] Firestore 更新成功！")
        
        if discord_bot:
            cog = discord_bot.get_cog("ReactionRoles")
            if cog:
                from cogs.reaction_roles import RoleView
                discord_bot.add_view(RoleView(role_buttons))
                print("[Web 連動] 已即時向機器人核心刷新持久化按鈕 View！")
        
        return f"""
        <html>
        <head><title>儲存成功</title></head>
        <body style="background: #2f3136; color: white; padding: 40px; font-family: sans-serif; text-align: center;">
            <div style="max-width: 500px; margin: 0 auto; background: #36393f; padding: 30px; border-radius: 10px;">
                <h2>✅ 所有進階設定皆已完美儲存！</h2>
                <p>伺服器 ID: {guild_id}</p>
                <p>已儲存的按鈕規則數量: {len(role_buttons)} 組</p>
                <br>
                <a href="/manage/{guild_id}" style="background: #5865F2; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; display: inline-block;">點此返回設定頁面</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        print(f"[Web 錯誤] 儲存到 Firestore 失敗: {e}")
        return f"儲存失敗，錯誤原因: {e}", 500

@app.route('/callback')
def callback():
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    redirect_uri = os.getenv("REDIRECT_URI", "http://127.0.0.1:8080/callback")
    
    code = request.args.get('code')
    if not code:
        return "登入失敗，未取得驗證碼。", 400
        
    try:
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        res = requests.post(f"{API_ENDPOINT}/oauth2/token", data=data, headers=headers, timeout=5).json()
        
        if 'access_token' in res:
            session['token'] = res['access_token']
            return redirect('/')
        else:
            return f"換取 Token 失敗：{res}", 400
    except Exception as e:
        return f"網路超時或連線失敗: {e}", 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def run():
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port, threaded=True)

def keep_alive(bot_instance):
    global discord_bot, db
    discord_bot = bot_instance
    
    if not firebase_admin._apps:
        if os.getenv("FIREBASE_PRIVATE_KEY"):
            try:
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace(r'\n', '\n'),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "token_uri": "https://oauth2.googleapis.com/token",
                })
                firebase_admin.initialize_app(cred)
                print("[Firebase] 成功透過環境變數初始化！")
            except Exception as e:
                print(f"[Firebase 錯誤] 環境變數解析失敗: {e}")
        elif os.path.exists('firebase_key.json'):
            try:
                cred = credentials.Certificate('firebase_key.json')
                firebase_admin.initialize_app(cred)
                print("[Firebase] 成功透過 firebase_key.json 檔案初始化！")
            except Exception as e:
                print(f"[Firebase 錯誤] 檔案解析失敗: {e}")
        else:
            print("[Firebase ⚠️] 未發現任何金鑰配置，將嘗試預設初始化...")
            try:
                firebase_admin.initialize_app()
            except Exception:
                pass

    try:
        db = firestore.client()
        print("[Firebase] Firestore 用戶端已就緒。")
    except Exception as e:
        print(f"[Firebase 錯誤] Firestore 用戶端取得失敗: {e}")
    
    t = Thread(target=run)
    t.start()