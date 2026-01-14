#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
東京都交通局の時刻表HTMLをNextTrain形式に変換するスクリプト
西馬込方面用
"""

import re
import sys
from typing import Dict, List


class TimetableConverter:
    def __init__(self):
        # 列車種別のマッピング（コード: [正式名称, 略称, カラーコード]）
        self.train_type_definitions = {
            'm': ['快特', '快', '#009966'],
            'n': ['急行', '急', '#0033FF'],
            'o': ['普通', '普', '#000000'],
            'p': ['特急', '特', '#FF0033'],
            'q': ['エアポート快特', 'エ', '#EE7A00'],
        }

        # 行先のマッピング（コード: [正式名称, 略称]）
        self.destination_definitions = {
            'a': ['羽田空港', '羽'],
            'b': ['京急久里浜', 'ク'],
            'c': ['三浦海岸', '海'],
            'd': ['三崎口', '三'],
            'e': ['神奈川新町', '神'],
            'f': ["西馬込'", "馬'"],  # 西馬込1番線着
            'g': ["西馬込''", "馬''"],  # 西馬込2番線着
            'h': ['泉岳寺', '泉'],
            'i': ['浅草橋', '草'],
            'j': ['品川', '品'],
            'k': ['金沢文庫', '文'],
            'l': ['逗子・葉山', '逗'],
        }

        # 列車種別のマッピング（略称→コード）
        self.train_type_map = {
            '普通': 'o',
            '無印': 'o',
            '急行': 'n',
            '急': 'n',
            '特急': 'p',
            '特': 'p',
            '快特': 'm',
            '快': 'm',
            'エアポート快特': 'q',
            'エ': 'q',
        }

        # 行先のマッピング（略称→コード）
        self.destination_map = {
            '羽田空港': 'a',
            '羽': 'a',
            '京急久里浜': 'b',
            '久': 'b',
            'ク': 'b',
            '三浦海岸': 'c',
            '海': 'c',
            '三崎口': 'd',
            '三': 'd',
            '神奈川新町': 'e',
            '神': 'e',
            '新': 'e',  # 神奈川新町
            '泉岳寺': 'h',
            '泉': 'h',
            '浅草橋': 'i',
            '草': 'i',
            '浅': 'i',
            '品川': 'j',
            '品': 'j',
            '金沢文庫': 'k',
            '文': 'k',
            '逗子・葉山': 'l',
            '逗': 'l',
            '①': 'f',  # 西馬込1番線
            '②': 'g',  # 西馬込2番線
        }

    def parse_html(self, html_content: str) -> Dict:
        """HTMLから時刻表データを抽出"""
        # 駅情報を取得
        station_info = self.extract_station_info(html_content)

        # 時刻表テーブルを解析
        timetable = self.extract_timetable(html_content)

        # 凡例を解析
        legends = self.extract_legends(html_content)

        return {
            'station': station_info,
            'timetable': timetable,
            'legends': legends
        }

    def extract_station_info(self, html_content: str) -> Dict:
        """駅情報を抽出"""
        info = {
            'name': '',
            'direction': '',
            'day_type': ''
        }

        # 駅名を取得
        station_match = re.search(r'<h1[^>]*class="station-name"[^>]*>([^<]+)</h1>', html_content)
        if station_match:
            info['name'] = station_match.group(1).strip()

        # 方面を取得
        direction_match = re.search(r'<li[^>]*class="[^"]*directionNavi__item[^"]*is-active[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', html_content, re.DOTALL)
        if direction_match:
            info['direction'] = direction_match.group(1).strip()

        # 曜日タイプを取得
        day_match = re.search(r'<li[^>]*class="[^"]*dayNavi__item[^"]*is-active[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', html_content, re.DOTALL)
        if day_match:
            day_text = day_match.group(1).strip()
            if '平日' in day_text:
                info['day_type'] = 'weekday'
            elif '土曜' in day_text or '休日' in day_text:
                info['day_type'] = 'holiday'

        return info

    def extract_timetable(self, html_content: str) -> Dict[str, List[Dict]]:
        """時刻表データを抽出（列車種別と行先の凡例も含む）"""
        timetable = {}

        # テーブルのtbodyを抽出
        tbody_match = re.search(r'<tbody>(.*?)</tbody>', html_content, re.DOTALL)
        if not tbody_match:
            return timetable

        tbody = tbody_match.group(1)

        # 各時間帯の行を抽出
        rows = re.findall(r'<tr>\s*<th>(\d+)</th>\s*<td>(.*?)</td>\s*</tr>', tbody, re.DOTALL)

        for hour, trains_html in rows:
            # 各列車のwrapTime要素全体を抽出
            train_blocks = []
            for match in re.finditer(r'<div class="(wrapTime[^"]*)">((?:<div[^>]*>.*?</div>|<span[^>]*>.*?</span>|\s)*)</div>', trains_html, re.DOTALL):
                train_blocks.append((match.group(1), match.group(2)))

            times = []
            for color_class, train_inner_html in train_blocks:
                # 凡例を抽出
                legend_match = re.search(r'<div class="wrapLegend">(.*?)</div>', train_inner_html, re.DOTALL)
                legends = []
                if legend_match:
                    legend_spans = re.findall(r'<span>([^<]+)</span>', legend_match.group(1))
                    legends = legend_spans

                # 行先と番線を判定（種別判定の前に行う）
                destination = None
                platform = None
                train_type_symbols = ['快', '急', '特', 'エ']  # 種別を示す記号

                for legend in legends:
                    # 種別記号はスキップ（後で使う）
                    if legend in train_type_symbols:
                        continue
                    # 番線記号を確認
                    if legend == '①':
                        platform = 'f'
                    elif legend == '②':
                        platform = 'g'
                    # 行先記号を探す
                    elif legend in self.destination_map:
                        destination = self.destination_map[legend]

                # 列車種別を判定（凡例を優先、次に色クラス）
                train_type = 'o'  # デフォルトは普通

                # 「エ」（エアポート快特）の特殊処理
                if 'エ' in legends:
                    # エアポート快特は色に関係なくエアポート快特
                    # （色は泉岳寺から先の種別を示すのみ）
                    train_type = 'q'  # エアポート快特
                else:
                    # 通常の種別判定（色クラスから）
                    if 'color-green' in color_class:
                        train_type = 'm'  # 快特
                    elif 'color-blue' in color_class:
                        train_type = 'n'  # 急行
                    elif 'color-red' in color_class:
                        train_type = 'p'  # 特急
                    elif 'color-orange' in color_class:
                        train_type = 'q'  # エアポート快特

                # 行先がない場合は番線情報を使う、それもない場合は西馬込1番線と仮定
                if destination is None:
                    if platform is not None:
                        destination = platform
                    else:
                        destination = 'f'  # デフォルトは西馬込1番線

                # 分を取得
                time_match = re.search(r'<span class="time">([^<]+)</span>', train_inner_html)
                if time_match:
                    minute = time_match.group(1)
                    # ハイフン（通過）はスキップ
                    if minute == '－':
                        continue
                    times.append({
                        'minute': minute,
                        'train_type': train_type,
                        'destination': destination,
                        'legends': legends
                    })

            if times:
                timetable[hour] = times

        return timetable

    def extract_legends(self, html_content: str) -> Dict[str, List[str]]:
        """凡例を抽出"""
        legends = {
            'train_types': [],
            'destinations': [],
            'connections': []
        }

        # 凡例セクションを抽出
        legend_sections = re.findall(r'<dl[^>]*class="[^"]*time-legend[^"]*"[^>]*>(.*?)</dl>', html_content, re.DOTALL)

        for section in legend_sections:
            # ヘッダーを取得
            head_match = re.search(r'<dt[^>]*class="[^"]*time-legend__head[^"]*"[^>]*>([^<]+)</dt>', section)
            if not head_match:
                continue

            head_text = head_match.group(1).strip()

            # リストアイテムを取得
            items = re.findall(r'<li[^>]*>([^<]+)</li>', section)

            for text in items:
                if '種別' in head_text:
                    legends['train_types'].append(text.strip())
                elif '行先' in head_text:
                    legends['destinations'].append(text.strip())
                elif '接続' in head_text:
                    legends['connections'].append(text.strip())

        return legends

    def convert_to_nexttrain(self, parsed_data_list: List[Dict]) -> str:
        """NextTrain形式に変換（複数の時刻表データに対応）"""
        lines = []

        # 行先定義を出力
        for code in sorted(self.destination_definitions.keys()):
            name, abbr = self.destination_definitions[code]
            lines.append(f"{code}:{name};{abbr}")

        # 列車種別定義を出力
        for code in sorted(self.train_type_definitions.keys()):
            name, abbr, color = self.train_type_definitions[code]
            lines.append(f"{code}:{name};{abbr};{color}")

        # 各時刻表データを処理
        for parsed_data in parsed_data_list:
            station = parsed_data['station']
            timetable = parsed_data['timetable']

            # 空行
            lines.append('')

            # 曜日ヘッダー
            if station['day_type'] == 'weekday':
                day_header = '[MON][TUE][WED][THU][FRI]'
                day_type_text = '平日'
            else:
                day_header = '[SAT][SUN][HOL]'
                day_type_text = '土休日'

            lines.append(day_header)

            # タイトル
            # 方面名から余分な文字を削除（例: "西馬込・京急線方面" → "西馬込方面"）
            direction = station['direction']
            if '・' in direction:
                # 最初の行先名のみを使用
                direction = direction.split('・')[0] + '方面'

            title = f"# {station['name']}駅 {direction}({day_type_text})"
            lines.append(title)

            # 時刻データを変換
            # ソートキー: 0時台と1時台は24時台、25時台として扱う
            def sort_hour(hour_str):
                if not hour_str.isdigit():
                    return 0
                hour = int(hour_str)
                # 0時と1時は24時、25時として扱う（23時の後に来るように）
                if hour <= 1:
                    return hour + 24
                return hour

            for hour in sorted(timetable.keys(), key=sort_hour):
                times = timetable[hour]
                if not times:
                    continue

                time_entries = []
                for time_data in times:
                    minute = time_data['minute']
                    train_type = time_data['train_type']
                    destination = time_data['destination']

                    # NextTrain形式: [列車種別][行先][時刻]
                    entry = f"{train_type}{destination}{minute}"
                    time_entries.append(entry)

                line = f"{hour}: {' '.join(time_entries)}"
                lines.append(line)

        return '\n'.join(lines)

    def print_analysis(self, parsed_data: Dict):
        """解析結果を表示"""
        print("\n=== 時刻表解析結果 ===")
        station = parsed_data['station']
        print(f"駅名: {station['name']}")
        print(f"方面: {station['direction']}")
        print(f"曜日: {'平日' if station['day_type'] == 'weekday' else '土休日'}")

        print("\n【凡例情報】")
        legends = parsed_data['legends']

        if legends['train_types']:
            print("\n種別:")
            for item in legends['train_types']:
                print(f"  {item}")

        if legends['destinations']:
            print("\n行先:")
            for item in legends['destinations']:
                print(f"  {item}")

        if legends['connections']:
            print("\n接続等:")
            for item in legends['connections']:
                print(f"  {item}")

        print("\n【時刻データサンプル（最初の3時間）】")
        count = 0
        for hour in sorted(parsed_data['timetable'].keys(), key=lambda x: int(x) if x.isdigit() else 0):
            if count >= 3:
                break
            times = parsed_data['timetable'][hour]
            if times:
                print(f"\n{hour}時台:")
                for time_data in times[:5]:  # 最初の5本まで表示
                    legends_str = ','.join(time_data['legends']) if time_data['legends'] else 'なし'
                    print(f"  {time_data['minute']}分 - 種別:{time_data['train_type']}, 行先:{time_data['destination']}, 凡例:[{legends_str}]")
                count += 1


def main():
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python timetable_converter_nishimagome_html.py <HTMLファイル1> [HTMLファイル2 ...]")
        print("  python timetable_converter_nishimagome_html.py <HTMLファイル1> [HTMLファイル2 ...] <出力ファイル>")
        print("  python timetable_converter_nishimagome_html.py --analyze <HTMLファイル>  (解析結果のみ表示)")
        print("\n例:")
        print("  # 平日と土休日を変換（出力ファイル名自動生成: output_A18.txt）")
        print("  python timetable_converter_nishimagome_html.py A18SD.html A18SH.html")
        print("")
        print("  # 出力ファイル名を指定")
        print("  python timetable_converter_nishimagome_html.py A18SD.html A18SH.html output_asakusa.txt")
        print("")
        print("  # 解析のみ")
        print("  python timetable_converter_nishimagome_html.py --analyze A18SD.html")
        sys.exit(1)

    # --analyze モード
    if sys.argv[1] == '--analyze':
        if len(sys.argv) < 3:
            print("エラー: HTMLファイルを指定してください")
            sys.exit(1)

        html_file = sys.argv[2]
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        converter = TimetableConverter()
        parsed_data = converter.parse_html(html_content)
        converter.print_analysis(parsed_data)
        sys.exit(0)

    # 通常の変換モード
    # 引数を解析: 最後の引数が.htmlで終わらない場合は出力ファイル名
    args = sys.argv[1:]
    html_files = []
    output_file = None

    if args[-1].endswith('.html'):
        # 全てHTMLファイル、出力ファイル名を自動生成
        html_files = args
        # 最初のHTMLファイル名から出力ファイル名を生成
        # 例: A18SD.html -> output_A18.txt
        import os
        base_name = os.path.basename(html_files[0])
        # ファイル名から拡張子と末尾のD/Hを除去
        name_without_ext = os.path.splitext(base_name)[0]
        # 末尾のS, D, Hを除去（例: A18SD -> A18）
        if name_without_ext and name_without_ext[-1] in ['D', 'H']:
            name_without_ext = name_without_ext[:-1]
        if name_without_ext and name_without_ext[-1] == 'S':
            name_without_ext = name_without_ext[:-1]
        output_file = f"output_{name_without_ext}.txt"
    else:
        # 最後の引数は出力ファイル名
        output_file = args[-1]
        html_files = args[:-1]

    if not html_files:
        print("エラー: HTMLファイルを指定してください")
        sys.exit(1)

    # 変換処理
    converter = TimetableConverter()
    parsed_data_list = []

    for html_file in html_files:
        print(f"読み込み中: {html_file}")
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()

        parsed_data = converter.parse_html(html_content)
        parsed_data_list.append(parsed_data)

        # 解析結果を表示
        converter.print_analysis(parsed_data)

    # NextTrain形式に変換
    nexttrain_output = converter.convert_to_nexttrain(parsed_data_list)

    # 出力
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(nexttrain_output)
    print(f"\n✓ 変換完了: {output_file}")
    print(f"  入力ファイル数: {len(html_files)}")


if __name__ == '__main__':
    main()
