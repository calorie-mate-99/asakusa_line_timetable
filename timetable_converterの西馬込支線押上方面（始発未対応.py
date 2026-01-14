#!/usr/bin/env python3
"""
東京都交通局の時刻表HTMLをNextTrain形式に変換するスクリプト
"""

from bs4 import BeautifulSoup
import sys
from typing import Dict, List


class TimetableConverter:
    def __init__(self):
        # 列車種別のマッピング（コード: [正式名称, 略称, カラーコード]）
        self.train_type_definitions = {
            'k': ['アクセス特急', 'ア', '#EE7A00'],
            'l': ['普通', '普', '#000000'],
            'm': ['快速', '快', '#FC82FC'],
            'n': ['特急', '特', '#FF0033'],
            'o': ['快特', '快', '#009966'],
        }

        # 行先のマッピング（コード: [正式名称, 略称]）
        self.destination_definitions = {
            'a': ['印旛日本医大', '印'],
            'b': ['芝山千代田', '芝'],
            'c': ['印西牧の原', '牧'],
            'd': ['押上', '押'],
            'e': ['京成高砂', '高'],
            'f': ['京成佐倉', '佐'],
            'g': ['京成成田', '成'],
            'h': ['成田空港', '空'],
            'i': ['青砥', '青'],
            'j': ['泉岳寺', '泉'],
        }

        # 列車種別のマッピング（略称→コード）
        self.train_type_map = {
            '普通': 'l',
            '無印': 'l',
            '快速': 'm',
            '速': 'm',
            '特急': 'n',
            '特': 'n',
            'アクセス特急': 'k',
            'ア': 'k',
            '快特': 'o',
            '快': 'o',
        }

        # 行先のマッピング（略称→コード）
        self.destination_map = {
            '印旛日本医大': 'a',
            '医': 'a',
            '芝山千代田': 'b',
            '芝': 'b',
            '印西牧の原': 'c',
            '印': 'c',
            '押上': 'd',
            '押': 'd',
            '京成高砂': 'e',
            '高': 'e',
            '京成佐倉': 'f',
            '佐': 'f',
            '京成成田': 'g',
            '成': 'g',
            '成田空港': 'h',
            '空': 'h',
            '青砥': 'i',
            '青': 'i',
            '泉岳寺': 'j',
            '●': 'j',  # 無印は泉岳寺行
        }

    def parse_html(self, html_content: str) -> Dict:
        """HTMLから時刻表データを抽出"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # 駅情報を取得
        station_info = self.extract_station_info(soup)

        # 時刻表テーブルを解析
        timetable = self.extract_timetable(soup)

        # 凡例を解析
        legends = self.extract_legends(soup)

        return {
            'station': station_info,
            'timetable': timetable,
            'legends': legends
        }

    def extract_station_info(self, soup: BeautifulSoup) -> Dict:
        """駅情報を抽出"""
        info = {
            'name': '',
            'direction': '',
            'day_type': ''
        }

        # 駅名を取得
        station_name_elem = soup.find('h1', class_='station-name')
        if station_name_elem:
            info['name'] = station_name_elem.text.strip()

        # 方面を取得
        direction_elem = soup.find('li', class_='directionNavi__item is-active')
        if direction_elem:
            info['direction'] = direction_elem.find('a').text.strip()

        # 曜日タイプを取得
        day_elem = soup.find('li', class_='dayNavi__item is-active')
        if day_elem:
            day_text = day_elem.find('a').text.strip()
            if '平日' in day_text:
                info['day_type'] = 'weekday'
            elif '土曜' in day_text or '休日' in day_text:
                info['day_type'] = 'holiday'

        return info

    def extract_timetable(self, soup: BeautifulSoup) -> Dict[str, List[Dict]]:
        """時刻表データを抽出（列車種別と行先の凡例も含む）"""
        timetable = {}

        table = soup.find('table', class_='tt-table')
        if not table:
            return timetable

        tbody = table.find('tbody')
        if not tbody:
            return timetable

        rows = tbody.find_all('tr')
        for row in rows:
            hour_elem = row.find('th')
            if not hour_elem:
                continue

            hour = hour_elem.text.strip()

            time_cell = row.find('td')
            if not time_cell:
                continue

            times = []
            wrap_times = time_cell.find_all('div', class_='wrapTime')

            for wrap_time in wrap_times:
                # 列車種別を判定（色クラスから）
                train_type = 'l'  # デフォルトは普通
                if 'color-pink' in wrap_time.get('class', []):
                    train_type = 'm'  # 快速
                elif 'color-red' in wrap_time.get('class', []):
                    train_type = 'n'  # 特急
                elif 'color-orange' in wrap_time.get('class', []):
                    train_type = 'k'  # アクセス特急
                elif 'color-green' in wrap_time.get('class', []):
                    train_type = 'o'  # 快特

                # 凡例（行先など）を取得
                legend_elem = wrap_time.find('div', class_='wrapLegend')
                legends = []
                destination = 'j'  # デフォルトは泉岳寺

                if legend_elem:
                    legend_spans = legend_elem.find_all('span')
                    for span in legend_spans:
                        text = span.text.strip()
                        if text:
                            legends.append(text)

                    # 行先を判定
                    # 凡例から行先を探す（種別記号は除外）
                    train_type_symbols = ['ア', '速', '特', '快']  # 種別を示す記号
                    for legend in legends:
                        # 種別記号をスキップ
                        if legend in train_type_symbols:
                            continue
                        # 行先記号を探す
                        if legend in self.destination_map:
                            destination = self.destination_map[legend]
                            break

                # 分を取得
                time_elem = wrap_time.find('span', class_='time')
                if time_elem:
                    minute = time_elem.text.strip()
                    times.append({
                        'minute': minute,
                        'train_type': train_type,
                        'destination': destination,
                        'legends': legends
                    })

            if times:
                timetable[hour] = times

        return timetable

    def extract_legends(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """凡例を抽出"""
        legends = {
            'train_types': [],
            'destinations': [],
            'connections': []
        }

        legend_sections = soup.find_all('dl', class_='time-legend')
        for section in legend_sections:
            head = section.find('dt', class_='time-legend__head')
            if not head:
                continue

            head_text = head.text.strip()
            items = section.find_all('li')

            for item in items:
                text = item.text.strip()

                if '種別' in head_text:
                    legends['train_types'].append(text)
                elif '行先' in head_text:
                    legends['destinations'].append(text)
                elif '接続' in head_text:
                    legends['connections'].append(text)

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
            # 方面名から余分な文字を削除（例: "押上・京成線・北総線方面" → "押上方面"）
            direction = station['direction']
            if '・' in direction:
                # 最初の行先名のみを使用
                direction = direction.split('・')[0] + '方面'

            title = f"# {station['name']}駅 {direction}({day_type_text})"
            lines.append(title)

            # 時刻データを変換
            for hour in sorted(timetable.keys(), key=lambda x: int(x) if x.isdigit() else 0):
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
        print("  python timetable_converter.py <HTMLファイル1> [HTMLファイル2 ...] [出力ファイル]")
        print("  python timetable_converter.py --analyze <HTMLファイル>  (解析結果のみ表示)")
        print("\n例:")
        print("  # 平日のみを変換")
        print("  python timetable_converter.py magome_weekday.html output.txt")
        print("")
        print("  # 平日と土休日を1つのファイルに変換")
        print("  python timetable_converter.py magome_weekday.html magome_holiday.html output.txt")
        print("")
        print("  # 解析のみ")
        print("  python timetable_converter.py --analyze magome_weekday.html")
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
        # 全てHTMLファイル、標準出力に出力
        html_files = args
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
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(nexttrain_output)
        print(f"\n✓ 変換完了: {output_file}")
        print(f"  入力ファイル数: {len(html_files)}")
    else:
        print("\n=== NextTrain形式出力 ===")
        print(nexttrain_output)


if __name__ == '__main__':
    main()
