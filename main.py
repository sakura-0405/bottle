import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"--- 機器人已上線 ---")
    print(f"名稱：{bot.user.name}")
    print(f"ID：{bot.user.id}")
    print(f"------------------")

@bot.command(name="sync")
@commands.is_owner()
async def sync(ctx: commands.Context):
    try:
        bot.tree.copy_global_to(guild=ctx.guild)
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ 成功將 {len(synced)} 個斜線指令同步到此伺服器！")
    except Exception as e:
        await ctx.send(f"❌ 同步失敗: {e}")

async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"成功載入服務：{filename}")

async def main():
    async with bot:
        await load_extensions()
        
        TOKEN = os.getenv("DISCORD_TOKEN")
        if not TOKEN:
            raise ValueError("找不到 DISCORD_TOKEN 環境變數！")
            
        await bot.start(TOKEN)

if __name__ == "__main__":
    print("正在啟動保活網頁服務...")
    # 🔴 關鍵修正：將 bot 物件傳給 keep_alive，讓網頁與 Bot 共享資料
    keep_alive(bot)
    asyncio.run(main())