import discord
from discord.ext import commands
from firebase_admin import firestore

class Features(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # 動態建立的語音頻道暫存仍保留在記憶體中
        self.dynamic_channels = []
        # 🔴 獲取 Firestore 客戶端實例
        self.db = firestore.client()

    # ================= 1. 動態歡迎新成員 =================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_id = str(member.guild.id)
        
        # 🔴 從 Firestore 讀取該伺服器的專屬歡迎頻道
        doc_ref = self.db.collection('guild_settings').document(guild_id)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            welcome_channel_id = data.get('welcome_channel')
            
            # 如果使用者有設定歡迎頻道，才執行發送
            if welcome_channel_id:
                channel = member.guild.get_channel(int(welcome_channel_id))
                if channel:
                    embed = discord.Embed(
                        title="✨ 歡迎新成員加入！ ✨",
                        description=f"熱烈歡迎 {member.mention} 來到 **{member.guild.name}**！",
                        color=discord.Color.blue()
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.add_field(name="成員總數", value=f"你是第 {member.guild.member_count} 位成員！", inline=False)
                    embed.set_footer(text=f"ID: {member.id}")
                    
                    await channel.send(embed=embed)

    # ================= 2. 動態語音頻道 =================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild_id = str(member.guild.id)
        
        # 🔴 從 Firestore 讀取該伺服器的專屬動態創房頻道
        doc_ref = self.db.collection('guild_settings').document(guild_id)
        doc = doc_ref.get()
        
        creator_channel_id = None
        if doc.exists:
            data = doc.to_dict()
            creator_channel_id = data.get('voice_channel')

        # 情況 A：成員進入了網頁上設定的那個「點我創房」頻道
        if after.channel and creator_channel_id and str(after.channel.id) == creator_channel_id:
            guild = member.guild
            category = after.channel.category
            
            new_channel = await guild.create_voice_channel(
                name=f"💬 {member.display_name} 的語音房",
                category=category
            )
            
            self.dynamic_channels.append(new_channel.id)
            await member.move_to(new_channel)
            print(f"[{guild.name}] 動態創房成功：{new_channel.name}")

        # 情況 B：成員離開了某個語音頻道（這部分邏輯不變，依然檢查暫存清單）
        if before.channel:
            if before.channel.id in self.dynamic_channels:
                if len(before.channel.members) == 0:
                    try:
                        await before.channel.delete()
                        self.dynamic_channels.remove(before.channel.id)
                        print(f"動態刪房成功：{before.channel.name}")
                    except Exception as e:
                        print(f"刪除動態頻道失敗: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Features(bot))