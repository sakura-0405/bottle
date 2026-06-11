import discord
from discord.ext import commands

class Features(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # 儲存動態動態創建的語音頻道 ID
        self.dynamic_channels = []

    # ================= 1. 歡迎新成員功能 =================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """當有新成員加入 Discord 伺服器時觸發"""
        # [設定] 請把這裡的 ID 替換成你伺服器的「歡迎頻道 ID」
        WELCOME_CHANNEL_ID = 1323404796719403070
        
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            # 建立一個精美的內嵌訊息 (Embed)
            embed = discord.Embed(
                title="✨ 歡迎新成員加入！ ✨",
                description=f"熱烈歡迎 {member.mention} 來到 **{member.guild.name}**！",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="成員總數", value=f"你是第 {member.guild.member_count} 位成員！", inline=False)
            embed.set_footer(text=f"ID: {member.id}")
            
            await channel.send(embed=embed)

    # ================= 2. 動態語音頻道功能 =================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """當成員加入、離開、或移動語音頻道時觸發"""
        
        # [設定] 請把這裡的 ID 替換成你建立的「➕ 點我創房」語音頻道的 ID
        CREATOR_CHANNEL_ID = 1323404796719403071

        # 情況 A：成員進入了「➕ 點我創房」頻道
        if after.channel and after.channel.id == CREATOR_CHANNEL_ID:
            guild = member.guild
            category = after.channel.category  # 讓新創的房間跟原本的頻道在同一個分類下
            
            # 建立新的語音頻道，名稱叫「XXX 的語音房」
            new_channel = await guild.create_voice_channel(
                name=f"💬 {member.display_name} 的語音房",
                category=category
            )
            
            # 將該頻道 ID 記錄起來，以便之後檢查刪除
            self.dynamic_channels.append(new_channel.id)
            
            # 將該成員自動移動到新建立的語音房
            await member.move_to(new_channel)
            print(f"動態創房成功：{new_channel.name}")

        # 情況 B：成員離開了某個語音頻道
        if before.channel:
            # 檢查這個離開的頻道，是不是由我們 Bot 創立的動態房
            if before.channel.id in self.dynamic_channels:
                # 如果頻道裡面已經空無一人 (人數為 0)
                if len(before.channel.members) == 0:
                    try:
                        await before.channel.delete()
                        self.dynamic_channels.remove(before.channel.id)
                        print(f"動態刪房成功：{before.channel.name} 已無人使用")
                    except Exception as e:
                        print(f"刪除動態頻道失敗: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Features(bot))