<<<<<<< HEAD
import discord, random, datetime
from discord.ext import commands
from config import TOKEN
from neis_api import get_meal
from user_data import add_favorite, get_favorites, rate_meal
from scheduler import setup_scheduler
=======
import discord, datetime
from discord.ext import commands
from config import TOKEN
from neis_api import get_meal
from user_data import add_favorite, get_favorites
from scheduler import setup_scheduler
from meal_rating import rate_meal, get_weekly_top3
>>>>>>> 6fe3fb5 (feat: 예약 메시지 발송)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="$", intents=intents)

<<<<<<< HEAD

=======
>>>>>>> 6fe3fb5 (feat: 예약 메시지 발송)
@bot.event
async def on_ready():
    print(f"{bot.user.name} 로그인 성공")
    await bot.change_presence(status=discord.Status.online, activity=discord.Game('오먹'))
    setup_scheduler(bot)

<<<<<<< HEAD
# 날짜별 급식 조회 명령어
=======
# 급식 평가
class RatingView(discord.ui.View):
    def __init__(self, date, menu):
        super().__init__(timeout=None)
        self.date = date
        self.menu = menu

    @discord.ui.button(label="추천 👍", style=discord.ButtonStyle.success)
    async def recommend(self, interaction, button):
        rate_meal(self.date, "추천", self.menu)
        await interaction.response.send_message(f"{self.menu} 추천이 등록되었습니다.", ephemeral=True)

    @discord.ui.button(label="비추천 👎", style=discord.ButtonStyle.danger)
    async def not_recommend(self, interaction, button):
        rate_meal(self.date, "비추천", self.menu)
        await interaction.response.send_message(f"{self.menu} 비추천이 등록되었습니다.", ephemeral=True)


>>>>>>> 6fe3fb5 (feat: 예약 메시지 발송)
@bot.command(name="급식")
async def get_meal_cmd(ctx, date: str):
    full_date = date if len(date) == 8 else f"2025{date}"
    meals = get_meal(full_date)
<<<<<<< HEAD
    msg = f"📅 {full_date} 급식 메뉴\n"
    favorites = get_favorites(ctx.author.id)
    for meal_time, menu in meals.items():
        for fav in favorites:
            if fav in menu:
                menu = menu.replace(fav, f"**{fav}**")
        msg += f"{meal_time}: {menu}\n"
    await ctx.send(msg)


# 선호 메뉴 등록
@bot.command(name="선호메뉴")
async def set_favorites(ctx, *menus):
    add_favorite(ctx.author.id, list(menus))
    await ctx.send(f"{', '.join(menus)} 메뉴가 선호 메뉴로 등록되었습니다.")


# 급식 평가
@bot.command(name="급식평가")
async def rate_meal_cmd(ctx, date: str, rating: str):
    full_date = date if len(date) == 8 else f"2025{date}"
    if rating not in ["추천", "비추천"]:
        await ctx.send("❌ '추천' 또는 '비추천'으로 입력해주세요.")
        return
    rate_meal(full_date, rating)
    await ctx.send(f"✅ {full_date} 급식 평가가 등록되었습니다.")


# 💬 자연어 명령어 감지
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()

    today = datetime.date.today()
    if "오늘 급식" in content:
        date_str = today.strftime("%Y%m%d")
        ctx = await bot.get_context(message)
        await get_meal_cmd(ctx, date_str)
        return

    elif "내일 급식" in content:
        tomorrow = today + datetime.timedelta(days=1)
        date_str = tomorrow.strftime("%Y%m%d")
        ctx = await bot.get_context(message)
        await get_meal_cmd(ctx, date_str)
        return


bot.run(TOKEN)
=======

    await ctx.send(f"🍱 **{full_date} 급식 메뉴**")

    icons = {"조식": "🌅", "중식": "☀️", "석식": "🌙"}
    for meal_time, menu in meals.items():
        icon = icons.get(meal_time, "🍽️")
        content = f"{icon} **{meal_time}**\n{menu}"
        await ctx.send(content, view=RatingView(full_date, menu))

@bot.command(name="이번주인기")
async def top3(ctx):
    top = get_weekly_top3()
    if not top:
        await ctx.send("이번 주에는 아직 평가가 없습니다.")
    else:
        msg = "🔥 이번 주 인기 메뉴 TOP3 🔥\n"
        for i, (menu, cnt) in enumerate(top, 1):
            msg += f"{i}. {menu} ({cnt}회 추천)\n"
        await ctx.send(msg)


bot.run(TOKEN)
>>>>>>> 6fe3fb5 (feat: 예약 메시지 발송)
