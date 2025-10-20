import requests
from config import NEIS_API_KEY, EDU_OFFICE_CODE, SCHOOL_CODE

def get_meal(date: str):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": NEIS_API_KEY,
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": EDU_OFFICE_CODE,
        "SD_SCHUL_CODE": SCHOOL_CODE,
        "MLSV_YMD": date
    }
    res = requests.get(url, params=params)
    data = res.json()
    
    meals = {}
    try:
        for item in data['mealServiceDietInfo'][1]['row']:
            meals[item['MMEAL_SC_NM']] = item['DDISH_NM'].replace("<br/>", ", ")
    except KeyError:
        meals = {"조식": "정보 없음", "중식": "정보 없음", "석식": "정보 없음"}
    
    return meals