import discord
from discord import app_commands
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_cog_load(self):
        """當這個 Cog 被載入時，自動同步斜線指令"""
        # 為了開發時能「瞬間」看到指令，我們改成手動到主程式或用指令同步
        # 這裡先留空，把同步邏輯移到主程式更安全
        pass

    # 建立一個簡單的斜線指令 /ping
    @app_commands.command(name="ping", description="測試機器人的延遲時間")
    async def ping(self, interaction: discord.Interaction):
        # 計算延遲（毫秒）
        latency = round(self.bot.latency * 1000)
        # 回覆使用者
        await interaction.response.send_message(f"🏓 Pong! 延遲時間：{latency}ms")

async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))