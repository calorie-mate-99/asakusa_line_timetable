都営浅草線の都営交通Webサイト上の時刻表htmlファイルを取り込み、NextTrain形式データへ変換するPythonコードです。
方面別、区間別にコードが分かれています。
・timetable_converter.py
⇒　泉岳寺以北の押上方面に対応。浅草橋駅の始発属性には非対応のため手打ち対応要
・timetable_converterの西馬込支線押上方面（始発未対応.py
⇒　高輪台以南の西馬込支線に対応。西馬込駅の発着番線表記には非対応
・timetable_converter_nishimagome.py
⇒　西馬込方面に対応、始発属性非対応のため手打ち対応要

■実行方法
第一引数と第二引数に平日及び土休日の時刻表html、第三引数に出力先のファイル名を入力して実行します。以下例
python timetable_converter.py ./honjoagatsumabashi_weekday.html ./honjoagatsumabashi_holiday.html output_honjoagatsumabashi.txt

■補足
行き先名の「西馬込'」は西馬込駅1番線着、「西馬込''」は西馬込駅2番線着です。
