import discord
from discord.ext import commands
from discord import app_commands
import firebase_admin
from firebase_admin import firestore

class RoleButton(discord.ui.Button):
    def __init__(self, label, role_id):
        # 使用 role_id 作為 custom_id 的一部分，這樣觸發時才知道要給哪個身分組
        super().__init__(label=label, style=discord.ButtonStyle.blurple, custom_id=f"role_btn:{role_id}")

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.custom_id.split(":")[1])
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message("❌ 找不到該身分組，請聯絡管理員檢查設定！", ephemeral=True)
            return

        # 如果成員已經有該身分組就移除，沒有就加上（Toggle 功能）
        if role in interaction.user.roles:
            try:
                await interaction.user.remove_roles(role)
                # 修正這裡：拿掉原本誤寫的 False，讓文字正確回應
                await interaction.response.send_message(f"✅ 已為您移除身分組：**{role.name}**", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ 機器人權限不足，無法為您移除身分組！請確保機器人身分組排序在該身分組之上。", ephemeral=True)
        else:
            try:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ 已為您領取身分組：**{role.name}**", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ 機器人權限不足，無法為您發放身分組！請確保機器人身分組排序在該身分組之上。", ephemeral=True)

class RoleView(discord.ui.View):
    def __init__(self, buttons_data):
        super().__init__(timeout=None) # timeout=None 讓按鈕永久有效
        for btn in buttons_data:
            if btn.get('label') and btn.get('role_id'):
                self.add_item(RoleButton(label=btn['label'], role_id=btn['role_id']))

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = firestore.client()

    @commands.Cog.listener()
    async def on_ready(self):
        # 機器人重啟時，必須重新註冊 View 才能讓舊的按鈕繼續有效（Persistent View）
        print("[身分組系統] 正在從 Firestore 重新載入所有伺服器的按鈕監聽...")
        try:
            docs = self.db.collection('guild_settings').stream()
            for doc in docs:
                data = doc.to_dict()
                buttons = data.get('role_buttons', [])
                if buttons:
                    self.bot.add_view(RoleView(buttons))
            print("[身分組系統] 歷史按鈕監聽註冊成功！")
        except Exception as e:
            print(f"[身分組系統 警告] 重新註冊按鈕監聽失敗: {e}")

    @app_commands.command(name="setup_roles", description="根據網頁設定生成按鈕領取身分組的訊息")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_roles(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        doc_ref = self.db.collection('guild_settings').document(guild_id)
        doc = doc_ref.get()

        if not doc.exists:
            await interaction.response.send_message("❌ 請先至網頁後台設定身分組按鈕規則！", ephemeral=True)
            return

        data = doc.to_dict()
        embed_title = data.get('role_embed_title', "🍾 自訂身分組領取專區")
        embed_desc = data.get('role_embed_desc', "點擊下方對應的按鈕即可領取或移除身分組。")
        buttons_data = data.get('role_buttons', [])

        if not buttons_data:
            await interaction.response.send_message("❌ 網頁後台尚未設定任何按鈕欄位！", ephemeral=True)
            return

        embed = discord.Embed(title=embed_title, description=embed_desc, color=0x5865F2)
        view = RoleView(buttons_data)

        await interaction.response.send_message("⌛ 正在生成身分組面板...", ephemeral=True)
        await interaction.channel.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))