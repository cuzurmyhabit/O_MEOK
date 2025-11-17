import json
import os
import datetime
import hashlib

DB_FILE = "db.json"

# 초기화
def init_db():
    if not os.path.exists(DB_FILE):
        data = {
            "users": {},
            "meals": {},
            "evaluations": [],
            "notifications": []
        }
    else:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}

    # 필수 키가 없으면 추가
    required_keys = ["users", "meals", "evaluations", "notifications"]
    for key in required_keys:
        if key not in data:
            data[key] = {} if key in ["users", "meals"] else []

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# JSON 읽기/쓰기
def load_data():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# 사용자 등록/조회
def register_user(user_id, name):
    """Discord 사용자 정보 저장"""
    data = load_data()
    user_id = str(user_id)
    
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "name": name,
            "registered_at": datetime.datetime.now().isoformat()
        }
        save_data(data)

def get_user(user_id):
    """사용자 정보 조회"""
    data = load_data()
    return data["users"].get(str(user_id))


# 급식 정보 저장/조회
def save_meal(date, meal_type, menu_list):
    """급식 정보를 DB에 저장"""
    data = load_data()
    
    # meal_id 생성 (날짜_식사타입)
    meal_id = f"{date}_{meal_type}"
    
    # 메뉴를 정규화 (괄호 제거)
    import re
    cleaned_menu = [re.sub(r"\([^\)]*\)", "", item).strip() for item in menu_list]
    
    data["meals"][meal_id] = {
        "date": date,
        "meal_type": meal_type,
        "menu": cleaned_menu,
        "raw_menu": menu_list
    }
    
    save_data(data)
    return meal_id

def get_meal(meal_id):
    """저장된 급식 정보 조회"""
    data = load_data()
    return data["meals"].get(meal_id)


# 급식 평가 저장
def rate_meal(user_id, date, meal_type, menu_item, rating):
    """
    급식 평가 저장 (중복 방지)
    - user_id: 평가한 사용자
    - date: 급식 날짜 (YYYYMMDD)
    - meal_type: 조식/중식/석식
    - menu_item: 평가 대상 메뉴
    - rating: 추천/비추천
    """
    data = load_data()
    user_id = str(user_id)
    
    meal_id = f"{date}_{meal_type}"
    
    # 중복 평가 체크 (같은 사용자가 같은 메뉴에 이미 평가했는지)
    for eval in data["evaluations"]:
        if (eval["user_id"] == user_id and 
            eval["meal_id"] == meal_id and 
            eval["menu_item"] == menu_item):
            # 기존 평가 업데이트
            eval["rating"] = rating
            eval["updated_at"] = datetime.datetime.now().isoformat()
            save_data(data)
            return "updated"
    
    # 새 평가 추가
    data["evaluations"].append({
        "user_id": user_id,
        "meal_id": meal_id,
        "menu_item": menu_item,
        "rating": rating,
        "created_at": datetime.datetime.now().isoformat()
    })
    
    save_data(data)
    return "created"


# 이번 주 인기 메뉴 TOP3 조회
def get_weekly_top3():
    """이번 주 추천이 많은 메뉴 TOP3"""
    data = load_data()
    
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    monday_str = monday.strftime("%Y%m%d")
    
    counts = {}
    for eval in data["evaluations"]:
        meal_id = eval["meal_id"]
        date = meal_id.split("_")[0]
        
        if eval["rating"] == "추천" and date >= monday_str:
            menu = eval["menu_item"]
            counts[menu] = counts.get(menu, 0) + 1
    
    top3 = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:3]
    return top3


# 알림 기록 저장
def save_notification(user_id, meal_id, channel_id):
    """알림 발송 기록 저장"""
    data = load_data()
    
    data["notifications"].append({
        "user_id": str(user_id) if user_id else "auto",
        "meal_id": meal_id,
        "channel_id": str(channel_id),
        "send_time": datetime.datetime.now().isoformat(),
        "status": "sent"
    })
    
    save_data(data)


# 오늘 알림이 발송되었는지 체크
def is_notification_sent_today(date):
    """해당 날짜에 자동 알림이 발송되었는지 확인"""
    data = load_data()
    
    for noti in data["notifications"]:
        if noti["user_id"] == "auto" and noti["meal_id"].startswith(date):
            return True
    return False


# 통계: 사용자별 평가 수
def get_user_stats(user_id):
    """사용자의 평가 통계"""
    data = load_data()
    user_id = str(user_id)
    
    recommend_count = 0
    not_recommend_count = 0
    
    for eval in data["evaluations"]:
        if eval["user_id"] == user_id:
            if eval["rating"] == "추천":
                recommend_count += 1
            else:
                not_recommend_count += 1
    
    return {
        "recommend": recommend_count,
        "not_recommend": not_recommend_count,
        "total": recommend_count + not_recommend_count
    }


# 통계: 메뉴별 평가 조회
def get_menu_stats(menu_item):
    """특정 메뉴의 평가 통계"""
    data = load_data()
    
    recommend_count = 0
    not_recommend_count = 0
    
    for eval in data["evaluations"]:
        if eval["menu_item"] == menu_item:
            if eval["rating"] == "추천":
                recommend_count += 1
            else:
                not_recommend_count += 1
    
    return {
        "menu": menu_item,
        "recommend": recommend_count,
        "not_recommend": not_recommend_count
    }