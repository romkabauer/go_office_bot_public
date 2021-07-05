import datetime
from datetime import timedelta

tomorrow = datetime.date.today() + timedelta(days=1)

pool_question = f'{tomorrow.strftime("%A, %d %B")} 🏢🚶‍♂️?'
pool_options = ["Zastavskaya, 22, K2A", "Pevcheskiy, 12", "B.Posadskaya, 12", "Nab. Chyornoy rechki, 41", "Show results"]
