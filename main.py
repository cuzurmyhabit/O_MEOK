import discord
import datetime
from discord.ext import commands, tasks
from config import TOKEN
from neis_api import get_meal
from db import (
    init_db, register_user, save_meal, rate_meal, 
    get_weekly_top3, save_notification, is_notification_sent_today,
    get_user_stats, get_menu_stats
)

# DB 초기화
init_db()

# 기본 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="$", intents=intents)

AUTO_CHANNEL_ID = 1428960374035578955

# 인기 급식 버튼
class RankingButtonView(discord.ui.View):
    @discord.ui.button(label="이번주 인기 TOP3 보기 🔥", style=discord.ButtonStyle.primary)
    async def show_ranking(self, interaction, button):
        top = get_weekly_top3()
        if not top:
            msg = "이번 주에는 아직 평가가 없습니다."
        else:
            msg = "🔥 이번 주 인기 메뉴 TOP3 🔥\n"
            for i, (menu, cnt) in enumerate(top, 1):
                msg += f"{i}. {menu} ({cnt}회 추천)\n"
        await interaction.response.send_message(msg, ephemeral=True)

# --- 급식 평가 버튼 UI ---
class RatingView(discord.ui.View):
    def __init__(self, date, meal_time, menu_items):
        super().__init__(timeout=None)
        self.date = date
        self.meal_time = meal_time
        self.menu_items = menu_items  # 리스트로 받음

    @discord.ui.button(label="추천 👍", style=discord.ButtonStyle.success, custom_id="recommend")
    async def recommend(self, interaction, button):
        # 사용자 등록
        register_user(interaction.user.id, interaction.user.name)
        
        # 메뉴 선택 UI 표시
        await interaction.response.send_message(
            "어떤 메뉴를 추천하시나요?",
            view=MenuSelectView(self.date, self.meal_time, self.menu_items, "추천"),
            ephemeral=True
        )

    @discord.ui.button(label="비추천 👎", style=discord.ButtonStyle.danger, custom_id="not_recommend")
    async def not_recommend(self, interaction, button):
        # 사용자 등록
        register_user(interaction.user.id, interaction.user.name)
        
        # 메뉴 선택 UI 표시
        await interaction.response.send_message(
            "어떤 메뉴를 비추천하시나요?",
            view=MenuSelectView(self.date, self.meal_time, self.menu_items, "비추천"),
            ephemeral=True
        )

# 메뉴 선택 UI
class MenuSelectView(discord.ui.View):
    def __init__(self, date, meal_time, menu_items, rating):
        super().__init__(timeout=60)
        self.date = date
        self.meal_time = meal_time
        self.rating = rating
        
        options = [
            discord.SelectOption(label=menu, value=menu)
            for menu in menu_items
        ]
        
        select = discord.ui.Select(
            placeholder="메뉴를 선택하세요",
            options=options,
            custom_id="menu_select"
        )
        select.callback = self.select_callback
        self.add_item(select)
    
    async def select_callback(self, interaction):
        selected_menu = interaction.data["values"][0]
        
        result = rate_meal(
            interaction.user.id,
            self.date,
            self.meal_time,
            selected_menu,
            self.rating
        )
        
        stats = get_menu_stats(selected_menu)
        
        dt = datetime.datetime.strptime(self.date, "%Y%m%d")
        date_str = f"{dt.month}월 {dt.day}일 {self.meal_time}"
        
        if result == "updated":
            msg = f"**{selected_menu}** {self.rating} ({date_str})\n평가가 수정되었습니다."
        else:
            msg = f"**{selected_menu}** {self.rating} ({date_str})\n평가가 등록되었습니다."
        
        msg += f"\n\n이 메뉴의 평가: 👍 {stats['recommend']} / 👎 {stats['not_recommend']}"
        
        await interaction.response.send_message(
            msg,
            ephemeral=True,
            view=RankingButtonView()
        )


# 급식 전송
async def send_meal(ctx, date: str):
    full_date = date if len(date) == 8 else f"2025{date}"
    meals = get_meal(full_date)
    
    if ctx:
        channel = ctx.channel
        user_id = ctx.author.id
    else:
        user_id = None
        if AUTO_CHANNEL_ID:
            channel = bot.get_channel(AUTO_CHANNEL_ID)
        else:
            channel = None
    
        if not channel:
            for guild in bot.guilds:
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        channel = ch
                        print(f"📍 자동 알림 채널: {ch.name} (ID: {ch.id})")
                        break
                if channel:
                    break
        
        if not channel:
            print(f"메시지를 보낼 수 있는 채널을 찾을 수 없습니다.")
            return

    date_obj = datetime.datetime.strptime(full_date, "%Y%m%d")
    header = f"🍱 **{date_obj.month}월 {date_obj.day}일 급식 메뉴**"
    await channel.send(header)

    for meal_time, menu in meals.items():
        menu_items = [item.strip() for item in menu.split(',')]
        
        meal_id = save_meal(full_date, meal_time, menu_items)
        
        formatted_menu = '\n'.join(menu_items)
        
        icons = {"조식": "🌅", "중식": "☀️", "석식": "🌙"}
        icon = icons.get(meal_time, "🍽️")
        
        content = f"{icon} **{meal_time}**\n{formatted_menu}"
        await channel.send(content, view=RatingView(full_date, meal_time, menu_items))
        
        if not ctx:
            save_notification(user_id, meal_id, channel.id)


# 자동 발송
@tasks.loop(minutes=1)
async def send_daily_meal():
    await bot.wait_until_ready()
    
    now = datetime.datetime.now()
    
    if now.hour == 7 and now.minute == 0:
        date_str = now.strftime("%Y%m%d")
        
        if not is_notification_sent_today(date_str):
            print(f"자동 급식 알림 발송 중... ({now})")
            await send_meal(None, date_str)
            print("자동 급식 알림 발송 완료!!!!! ✅")


# 봇 로그인 시 동작
@bot.event
async def on_ready():
    print(f"{bot.user.name} 로그인 성공 ㅎㅎ ✅")
    print(f"자동 알림 채널 ID: {AUTO_CHANNEL_ID}")
    
    print(f"\n봇이 접근 가능한 서버 및 채널:")
    for guild in bot.guilds:
        print(f"  서버: {guild.name} (ID: {guild.id})")
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                print(f"    #{channel.name} (ID: {channel.id})")
    
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game('오먹')
    )
    if not send_daily_meal.is_running():
        send_daily_meal.start()
        print("\n자동 알림 스케줄러 시작")


# 급식 조회
@bot.command(name="급식")
async def get_meal_cmd(ctx, date: str):
    await send_meal(ctx, date)


# 인기 급식
@bot.command(name="이번주인기")
async def top3(ctx):
    top = get_weekly_top3()
    if not top:
        await ctx.send("이번 주에는 아직 평가가 없습니다.")
        return
    msg = "🔥 이번 주 인기 메뉴 TOP3 🔥\n"
    for i, (menu, cnt) in enumerate(top, 1):
        msg += f"{i}. {menu} ({cnt}회 추천)\n"
    await ctx.send(msg)

# 메뉴 통계
@bot.command(name="메뉴통계")
async def menu_stat(ctx, *, menu_name: str):
    stats = get_menu_stats(menu_name)
    
    if stats["recommend"] == 0 and stats["not_recommend"] == 0:
        await ctx.send(f"'{menu_name}'에 대한 평가가 아직 없습니다.")
        return
    
    total = stats["recommend"] + stats["not_recommend"]
    recommend_pct = (stats["recommend"] / total * 100) if total > 0 else 0
    
    msg = f"**{menu_name}** 평가 통계\n"
    msg += f"👍 추천: {stats['recommend']}회 ({recommend_pct:.1f}%)\n"
    msg += f"👎 비추천: {stats['not_recommend']}회"
    
    await ctx.send(msg)


# 채널 확인 (디버깅)
@bot.command(name="채널확인")
async def check_channel(ctx):
    channel = bot.get_channel(AUTO_CHANNEL_ID)
    if channel:
        await ctx.send(f"채널을 찾았습니다: {channel.name} (ID: {channel.id})")
    else:
        await ctx.send(f"채널 ID {AUTO_CHANNEL_ID}를 찾을 수 없음.\n현재 채널 ID: {ctx.channel.id}")


# 자연어 명령어 감지
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    today = datetime.date.today()
    ctx = await bot.get_context(message)

    if "오늘 급식" in content or "오늘급식" in content:
        date_str = today.strftime("%Y%m%d")
        await send_meal(ctx, date_str)
        return
    
    elif "내일 급식" in content or "내일급식" in content:
        tomorrow = today + datetime.timedelta(days=1)
        date_str = tomorrow.strftime("%Y%m%d")
        await send_meal(ctx, date_str)
        return
    
    import re
    date_pattern = r'(\d{1,2})월\s*(\d{1,2})일\s*급식'
    match = re.search(date_pattern, content)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        year = today.year
        
        if month < today.month:
            year += 1
        
        date_str = f"{year}{month:02d}{day:02d}"
        await send_meal(ctx, date_str)
        return

    await bot.process_commands(message)

bot.run(TOKEN)