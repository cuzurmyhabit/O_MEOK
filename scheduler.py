<<<<<<< HEAD
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from neis_api import get_meal
from config import CHANNEL_ID

def setup_scheduler(bot):
    scheduler = AsyncIOScheduler()

    async def send_daily_meal():
        channel = bot.get_channel(CHANNEL_ID)
        today = datetime.date.today().strftime("%Y%m%d")
        meals = get_meal(today)
        msg = f"🍽 오늘의 급식 ({today})\n"
        for meal_time, menu in meals.items():
            msg += f"{meal_time}: {menu}\n"
        await channel.send(msg)

    scheduler.add_job(send_daily_meal, 'cron', hour=8, minute=0)
=======
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime
from neis_api import get_meal
from user_data import get_favorites
from config import CHANNEL_ID


def setup_scheduler(bot):
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    @scheduler.scheduled_job("cron", hour=9, minute=51)
    async def send_daily_meal():
        today = datetime.date.today().strftime("%Y%m%d")

        # 채널 가져오기
        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            print(f"⚠️ 채널을 찾을 수 없습니다. CHANNEL_ID: {CHANNEL_ID}")
            return

        # 오늘 급식 가져오기
        meals = get_meal(today)
        msg = f"🍽️ 오늘의 급식 ({today})\n"
        for meal_time, menu in meals.items():
            msg += f"{meal_time}: {menu}\n"

        # 채널에 메시지 전송
        try:
            await channel.send(msg)
            print("✅ 채널 메시지 전송 완료")
        except Exception as e:
            print(f"❌ 채널 메시지 전송 실패: {e}")

        # 개인 DM 전송
        for guild in bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                favorites = get_favorites(member.id)
                if not favorites:
                    continue
                for meal in meals.values():
                    for fav in favorites:
                        if fav in meal:
                            try:
                                await member.send(f"💖 오늘 급식에 **{fav}**가 포함되어 있어요!")
                                break
                            except Exception as e:
                                print(f"DM 전송 실패: {member} - {e}")

>>>>>>> 6fe3fb5 (feat: 예약 메시지 발송)
    scheduler.start()
