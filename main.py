import discord
import datetime
from discord.ext import commands, tasks
from config import TOKEN
from neis_api import get_meal
from db import (
    init_db, save_meal, rate_meal,
    get_weekly_top3, get_menu_stats, get_user_stats
)

init_db()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="$", intents=intents)

AUTO_CHANNEL_ID = 1428960374035578955

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

class RatingView(discord.ui.View):
    def __init__(self, date, meal_time, menu_items):
        super().__init__(timeout=None)
        self.date = date
        self.meal_time = meal_time
        self.menu_items = menu_items

    @discord.ui.button(label="추천 👍", style=discord.ButtonStyle.success, custom_id="recommend")
    async def recommend(self, interaction, button):
        await interaction.response.send_message(
            "어떤 메뉴를 추천하시나요?",
            view=MenuSelectView(self.date, self.meal_time, self.menu_items, "추천"),
            ephemeral=True
        )

    @discord.ui.button(label="비추천 👎", style=discord.ButtonStyle.danger, custom_id="not_recommend")
    async def not_recommend(self, interaction, button):
        await interaction.response.send_message(
            "어떤 메뉴를 비추천하시나요?",
            view=MenuSelectView(self.date, self.meal_time, self.menu_items, "비추천"),
            ephemeral=True
        )

class MenuSelectView(discord.ui.View):
    def __init__(self, date, meal_time, menu_items, rating):
        super().__init__(timeout=60)
        self.date = date
        self.meal_time = meal_time
        self.rating = rating
        self.menu_items = menu_items

        options = [discord.SelectOption(label=menu, value=menu) for menu in menu_items]
        select = discord.ui.Select(placeholder="메뉴를 선택하세요", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction):
        selected_menu = interaction.data["values"][0]
        meal_id = f"{self.date}_{self.meal_time}_{selected_menu}"

        result = rate_meal(meal_id, interaction.user.id, selected_menu, self.rating)
        stats = get_menu_stats(selected_menu)

        dt = datetime.datetime.strptime(self.date, "%Y%m%d")
        date_str = f"{dt.month}월 {dt.day}일 {self.meal_time}"

        if result == "updated":
            msg = f"**{selected_menu}** {self.rating} ({date_str})\n평가가 수정되었습니다."
        else:
            msg = f"**{selected_menu}** {self.rating} ({date_str})\n평가가 등록되었습니다."

        msg += f"\n\n이 메뉴의 평가: 👍 {stats['recommend']} / 👎 {stats['not_recommend']}"
        await interaction.response.send_message(msg, ephemeral=True, view=RankingButtonView())

async def send_meal(ctx, date: str):
    full_date = date if len(date) == 8 else f"2025{date}"
    meals = get_meal(full_date)

    if ctx:
        channel = ctx.channel
    else:
        channel = bot.get_channel(AUTO_CHANNEL_ID)
        if not channel:
            for guild in bot.guilds:
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        channel = ch
                        break
                if channel:
                    break
        if not channel:
            print("메시지를 보낼 채널이 없습니다.")
            return

    date_obj = datetime.datetime.strptime(full_date, "%Y%m%d")
    await channel.send(f"🍱 **{date_obj.month}월 {date_obj.day}일 급식 메뉴**")

    for meal_time, menu_str in meals.items():
        menu_items = [item.strip() for item in menu_str.split(',')]
        for menu_item in menu_items:
            meal_id = f"{full_date}_{meal_time}_{menu_item}"
            save_meal(meal_id, full_date, meal_time, menu_item)

        formatted_menu = '\n'.join(menu_items)
        icons = {"조식": "🌅", "중식": "☀️", "석식": "🌙"}
        icon = icons.get(meal_time, "🍽️")
        await channel.send(f"{icon} **{meal_time}**\n{formatted_menu}", view=RatingView(full_date, meal_time, menu_items))

@tasks.loop(minutes=1)
async def send_daily_meal():
    await bot.wait_until_ready()
    now = datetime.datetime.now()
    if now.hour == 7 and now.minute == 0:
        date_str = now.strftime("%Y%m%d")
        await send_meal(None, date_str)

@bot.event
async def on_ready():
    print(f"{bot.user.name} 로그인 완료 ✅")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("오먹"))
    if not send_daily_meal.is_running():
        send_daily_meal.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    content = message.content.strip()
    today = datetime.date.today()
    ctx = await bot.get_context(message)

    if "오늘 급식" in content or "오늘급식" in content:
        await send_meal(ctx, today.strftime("%Y%m%d"))
        return
    elif "내일 급식" in content or "내일급식" in content:
        tomorrow = today + datetime.timedelta(days=1)
        await send_meal(ctx, tomorrow.strftime("%Y%m%d"))
        return

    import re
    m = re.search(r'(\d{1,2})월\s*(\d{1,2})일\s*급식', content)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        year = today.year
        if month < today.month:
            year += 1
        await send_meal(ctx, f"{year}{month:02d}{day:02d}")
        return

    await bot.process_commands(message)

@bot.command(name="급식")
async def get_meal_cmd(ctx, date: str):
    await send_meal(ctx, date)

@bot.command(name="이번주인기")
async def top3(ctx):
    top = get_weekly_top3()
    if not top:
        await ctx.send("이번 주에는 평가가 없습니다.")
        return
    msg = "🔥 이번 주 인기 메뉴 TOP3 🔥\n"
    for i, (menu, cnt) in enumerate(top, 1):
        msg += f"{i}. {menu} ({cnt}회 추천)\n"
    await ctx.send(msg)

@bot.command(name="메뉴통계")
async def menu_stat(ctx, *, menu_name: str):
    stats = get_menu_stats(menu_name)
    total = stats["recommend"] + stats["not_recommend"]
    if total == 0:
        await ctx.send(f"'{menu_name}'에 대한 평가가 없습니다.")
        return
    pct = stats["recommend"] / total * 100
    await ctx.send(f"**{menu_name}** 평가 통계\n👍 {stats['recommend']}회 ({pct:.1f}%)\n👎 {stats['not_recommend']}회")

bot.run(TOKEN)