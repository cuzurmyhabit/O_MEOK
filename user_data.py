# 사용자 선호 메뉴
user_favorites = {}  # {"user_id": ["돈까스", "김치볶음밥"]}

# 급식 평가 기록
meal_ratings = {}    # {"YYYYMMDD": {"추천": 5, "비추천": 2}}

def add_favorite(user_id, menus):
    user_favorites[str(user_id)] = menus

def get_favorites(user_id):
    return user_favorites.get(str(user_id), [])

def rate_meal(date, rating):
    if date not in meal_ratings:
        meal_ratings[date] = {"추천": 0, "비추천": 0}
    if rating == "추천":
        meal_ratings[date]["추천"] += 1
    elif rating == "비추천":
        meal_ratings[date]["비추천"] += 1
