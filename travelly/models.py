import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel

class Tasks(Enum):
    flights = "flights"
    hotels = "hotels"
    activities = "activities"


class TravelRequest(BaseModel):
    origin: str
    destination: Optional[str] = None
    start_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None
    # Решил обозначить бюджет уровнями (1 - бомж уровень, 2 - уже чуть погулять можно, 3 - бомоклат рич милионейре, 4 - топ 10 форбс)
    # сделал это, так как валюта везде разная и тд и тп. сделал это на начале, мб и не надо было
    budget_level: Optional[int] = 2
    todo: List[Tasks] = [Tasks.flights, Tasks.hotels, Tasks.activities]





