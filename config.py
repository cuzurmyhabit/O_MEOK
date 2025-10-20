from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Discord
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# NEIS API
NEIS_API_KEY = os.getenv("NEIS_API_KEY")
EDU_OFFICE_CODE = os.getenv("EDU_OFFICE_CODE")
SCHOOL_CODE = os.getenv("SCHOOL_CODE")

# 검증
if not TOKEN:
    raise ValueError("Discord 토큰 환경 변수가 설정되지 않았음 ㅠ .env 파일 확인 필요")
if not CHANNEL_ID:
    raise ValueError("Discord 토큰 환경 변수가 설정되지 않았음 ㅠ .env 파일 확인 필요")
if not NEIS_API_KEY or not EDU_OFFICE_CODE or not SCHOOL_CODE:
    raise ValueError("Discord 토큰 환경 변수가 설정되지 않았음 ㅠ .env 파일 확인 필요")