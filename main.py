import discord
import datetime
from discord.ext import commands, tasks  # commands: 명령어 처리 tasks: 반복 작업 스케줄링
from config import TOKEN
from neis_api import get_meal
from db import (
    init_db, save_meal, rate_meal,
    get_weekly_top3, get_menu_stats, get_user_stats
)

init_db()

# Intents 설정 - 봇이 어떤 이벤트를 수신할지 결정
intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용 읽기 권한 활성화
bot = commands.Bot(command_prefix="$", intents=intents)  

AUTO_CHANNEL_ID = 1428960374035578955

# Discord UI View 클래스 (라이브러리에서 제공하는 거임) - 버튼과 같은 상호작용 요소를 포함
class RankingButtonView(discord.ui.View):
    # @discord.ui.button - 버튼 UI 요소를 메서드에 연결
    @discord.ui.button(label="이번주 인기 TOP3 보기 🔥", style=discord.ButtonStyle.primary)
    async def show_ranking(self, interaction, button):
        # 버튼 누르면 콜백 함수 호출
        top = get_weekly_top3()
        if not top:
            msg = "이번 주에는 아직 평가가 없습니다."
        else:
            msg = "🔥 이번 주 인기 메뉴 TOP3 🔥\n"
            for i, (menu, cnt) in enumerate(top, 1):
                msg += f"{i}. {menu} ({cnt}회 추천)\n"
        
        # interaction.response - 버튼 클릭에 대한 응답 (ephemeral=True: 본인만 보이게 하는 거임ㅠ)
        await interaction.response.send_message(msg, ephemeral=True)

class RatingView(discord.ui.View):
    # 급식 평가 뷰
    def __init__(self, date, meal_time, menu_items):
        super().__init__(timeout=None) 
        self.date = date
        self.meal_time = meal_time
        self.menu_items = menu_items

    # custom_id - 버튼의 고유 식별자 (봇 재시작 후에도 유지)
    @discord.ui.button(label="추천 👍", 
                       style=discord.ButtonStyle.success, 
                       custom_id="recommend")
    
    async def recommend(self, interaction, button):
        await interaction.response.send_message(
            "어떤 메뉴를 추천하시나요?",
            view=MenuSelectView(self.date, self.meal_time, self.menu_items, "추천"),
            ephemeral=True
        )

    @discord.ui.button(label="비추천 👎", 
                       style=discord.ButtonStyle.danger, 
                       custom_id="not_recommend")
    
    async def not_recommend(self, interaction, button):
        await interaction.response.send_message(
            "어떤 메뉴를 비추천하시나요?",
            view=MenuSelectView(self.date, self.meal_time, self.menu_items, "비추천"),
            ephemeral=True
        )

class MenuSelectView(discord.ui.View):
    def __init__(self, date, meal_time, menu_items, rating):
        super().__init__(timeout=None)
        self.date = date
        self.meal_time = meal_time
        self.rating = rating
        self.menu_items = menu_items

        options = []

        for menu in menu_items:
            option = discord.SelectOption(label=menu, value=menu)
            options.append(option)

        select = discord.ui.Select(placeholder="메뉴를 선택하세요", options=options)
        
        select.callback = self.select_callback
        
        self.add_item(select)

    async def select_callback(self, interaction):
        
        #사용자 상호작용 데이터 딕셔너리
        selected_menu = interaction.data["values"][0]
        meal_id = f"{self.date}_{self.meal_time}_{selected_menu}"

        result = rate_meal(meal_id, interaction.user.id, selected_menu, self.rating)
        stats = get_menu_stats(selected_menu)

        # datetime.strptime() - 문자열을 datetime 객체로 파싱
        dt = datetime.datetime.strptime(self.date, "%Y%m%d")
        date_str = f"{dt.month}월 {dt.day}일 {self.meal_time}"

        if result == "updated":
            msg = f"**{selected_menu}** {self.rating} ({date_str})\n평가가 수정되었습니다."
        else:
            msg = f"**{selected_menu}** {self.rating} ({date_str})\n평가가 등록되었습니다."

        # 딕셔너리 인덱싱으로 통계 데이터 접근
        msg += f"\n\n이 메뉴의 평가: 👍 {stats['recommend']} / 👎 {stats['not_recommend']}"
        await interaction.response.send_message(msg, ephemeral=True, view=RankingButtonView())

async def send_meal(ctx, date: str):
    # 삼항 연산자 (조건부 표현식) - 날짜 형식 보정
    full_date = date if len(date) == 8 else f"2025{date}"
    meals = get_meal(full_date)

    # ctx 존재 여부에 따른 채널 결정
    if ctx:
        channel = ctx.channel
    else:
        channel = bot.get_channel(AUTO_CHANNEL_ID)
        if not channel:
            for guild in bot.guilds:  # 봇이 들어간 모든 서버 확인
                for ch in guild.text_channels:  # 각 서버의 모든 텍스트 채널 확인
                    if ch.permissions_for(guild.me).send_messages:  # 봇이 메시지 보낼 권한 있나?
                        channel = ch
                        break  # 찾았다! 그만 찾자
                if channel:
                    break  # 찾았으니 서버 순회도 그만
        if not channel:
            print("메시지를 보낼 채널이 없습니다.")
            return

    date_obj = datetime.datetime.strptime(full_date, "%Y%m%d")
    await channel.send(f"🍱 **{date_obj.month}월 {date_obj.day}일 급식 메뉴**")

    # .items() - 딕셔너리의 키-값 쌍을 반환
    for meal_time, menu_str in meals.items():
        # List comprehension with strip() - 공백 제거하며 리스트 생성
        menu_items = [item.strip() for item in menu_str.split(',')]
        for menu_item in menu_items:
            meal_id = f"{full_date}_{meal_time}_{menu_item}"
            save_meal(meal_id, full_date, meal_time, menu_item)

        # join() - 리스트를 문자열로 결합
        formatted_menu = '\n'.join(menu_items)
        # 딕셔너리를 활용한 매핑
        icons = {"조식": "🌅", "중식": "☀️", "석식": "🌙"}
        # .get() - 키가 없을 때 기본값 반환
        icon = icons.get(meal_time, "🍽️")
        # View 객체를 메시지에 첨부하여 버튼 표시
        await channel.send(f"{icon} **{meal_time}**\n{formatted_menu}", view=RatingView(full_date, meal_time, menu_items))

# @tasks.loop - 주기적으로 실행되는 백그라운드 작업
@tasks.loop(minutes=1)
async def send_daily_meal():
    await bot.wait_until_ready()  # 봇이 준비될 때까지 대기
    now = datetime.datetime.now()
    # 시간 체크 - 정각 7시 정확히 실행
    if now.hour == 7 and now.minute == 0:
        date_str = now.strftime("%Y%m%d")  # 날짜 포매팅
        await send_meal(None, date_str)

# @bot.event - 특정 Discord 이벤트에 함수 연결
@bot.event
async def on_ready():
    print(f"{bot.user.name} 로그인 완료 ✅")
    # 봇 상태 변경 (온라인 + 게임 중)
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("오먹"))
    # 반복 작업이 실행 중이 아니면 시작
    if not send_daily_meal.is_running():
        send_daily_meal.start()

@bot.event
async def on_message(message):
    # 모든 메시지에 대해 실행되는 이벤트 핸들러
    # 봇 자신의 메시지는 무시
    if message.author.bot:
        return
    
    content = message.content.strip()
    today = datetime.date.today()
    # Context 객체 생성 - 명령어 처리에 필요한 정보
    ctx = await bot.get_context(message)

    # in 연산자 - 문자열 포함 여부 확인
    if "오늘 급식" in content or "오늘급식" in content:
        await send_meal(ctx, today.strftime("%Y%m%d"))
        return  # early return - 더 이상 처리하지 않음
    elif "내일 급식" in content or "내일급식" in content:
        # timedelta - 날짜 연산
        tomorrow = today + datetime.timedelta(days=1)
        await send_meal(ctx, tomorrow.strftime("%Y%m%d"))
        return

    # 정규표현식(regex) - 패턴 매칭으로 날짜 추출
    import re
    m = re.search(r'(\d{1,2})월\s*(\d{1,2})일\s*급식', content)

    if m:
        # 그룹으로 캡처한 값을 정수로 변환
        month = int(m.group(1))
        day = int(m.group(2))
        year = today.year
        # 월이 과거면 다음 해로 설정
        if month < today.month:
            year += 1
        await send_meal(ctx, f"{year}{month:02d}{day:02d}")
        return

    # 명령어 처리 (자연어 처리 후에만 실행)
    await bot.process_commands(message)

# @bot.command 데코레이터 - 봇 명령어 정의
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