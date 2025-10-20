import json, os
from collections import Counter

DATA_FILE = "db.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"favorites": {}, "ratings": {}}, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def rate_meal(date, rating, menu_name):
    data = load_data()
    if date not in data["ratings"]:
        data["ratings"][date] = []
    data["ratings"][date].append({"menu": menu_name, "rating": rating})
    save_data(data)

def get_weekly_top3():
    data = load_data()["ratings"]
    all_menus = [r["menu"] for d in data.values() for r in d if r["rating"] == "추천"]
    counter = Counter(all_menus)
    return counter.most_common(3)
