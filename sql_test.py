import logging
from typing import Dict
from datetime import datetime
import pandas as pd

class SqlTest:
    def compute(self, input: Dict[str, pd.DataFrame],  current_time: datetime) -> Dict[str, pd.DataFrame]:
        for key, value in input.items():
            if value is None:
                logging.info(f"{key}的数据是空")
            else:
                logging.info(f"{key}的数据是{value}")
        return {}
