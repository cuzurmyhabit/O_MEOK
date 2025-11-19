import sqlite3
import datetime

DB_FILE = "meal.db"

# DB 초기화
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 식단 정보
    c.execute("""
    CREATE TABLE IF NOT EXISTS meals (
        meal_id TEXT PRIMARY KEY,
        date TEXT,
        meal_time TEXT,
        menu_item TEXT
    )
    """)

    # 평가 정보
    c.execute("""
    CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_id TEXT,
        user_id TEXT,
        menu_item TEXT,
        rating TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()


# 급식 저장
def save_meal(meal_id, date, meal_time, menu_item):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        INSERT OR REPLACE INTO meals (meal_id, date, meal_time, menu_item)
        VALUES (?, ?, ?, ?)
    """, (meal_id, date, meal_time, menu_item))

    conn.commit()
    conn.close()

# 급식 조회
def get_meal(meal_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT * FROM meals WHERE meal_id = ?", (meal_id,))
    row = c.fetchone()

    conn.close()
    return row

# 평가 저장 (중복 방지)
def rate_meal(meal_id, user_id, menu_item, rating):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    today = datetime.date.today().strftime("%Y%m%d")

    # 동일 사용자 + 동일 메뉴 평가가 있는지 확인
    c.execute("""
        SELECT id FROM ratings
        WHERE meal_id = ? AND user_id = ? AND menu_item = ?
    """, (meal_id, user_id, menu_item))

    row = c.fetchone()

    if row:
        # 기존 평가 수정
        c.execute("""
            UPDATE ratings
            SET rating = ?, date = ?
            WHERE id = ?
        """, (rating, today, row[0]))
        status = "updated"
    else:
        # 새 평가 등록
        c.execute("""
            INSERT INTO ratings (meal_id, user_id, menu_item, rating, date)
            VALUES (?, ?, ?, ?, ?)
        """, (meal_id, user_id, menu_item, rating, today))
        status = "inserted"

    conn.commit()
    conn.close()
    return status

# 특정 메뉴 전체 통계\
def get_menu_stats(menu_item):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT 
            SUM(CASE WHEN rating = '추천' THEN 1 ELSE 0 END),
            SUM(CASE WHEN rating = '비추천' THEN 1 ELSE 0 END)
        FROM ratings
        WHERE menu_item = ?
    """, (menu_item,))

    recommend, not_recommend = c.fetchone()
    conn.close()

    recommend = recommend or 0
    not_recommend = not_recommend or 0

    return {
        "menu": menu_item,
        "recommend": recommend,
        "not_recommend": not_recommend,
        "total": recommend + not_recommend
    }

# 이번 주 TOP3 메뉴
def get_weekly_top3():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    monday_str = monday.strftime("%Y%m%d")

    c.execute("""
        SELECT menu_item, COUNT(*) as cnt
        FROM ratings
        WHERE date >= ?
          AND rating = '추천'
        GROUP BY menu_item
        ORDER BY cnt DESC
        LIMIT 3
    """, (monday_str,))

    result = c.fetchall()
    conn.close()
    return result

# 사용자 통계
def get_user_stats(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        SELECT
            SUM(CASE WHEN rating = '추천' THEN 1 ELSE 0 END),
            SUM(CASE WHEN rating = '비추천' THEN 1 ELSE 0 END)
        FROM ratings
        WHERE user_id = ?
    """, (user_id,))

    recommend, not_recommend = c.fetchone()
    conn.close()

    recommend = recommend or 0
    not_recommend = not_recommend or 0

    return {
        "user": user_id,
        "recommend": recommend,
        "not_recommend": not_recommend,
        "total": recommend + not_recommend
    }