# -*- coding: utf-8 -*-
import flet as ft
import os
import pathlib
import wave
from datetime import timezone, datetime, timedelta


# 録音サイトのメタデータを格納するグローバル変数
dict_site = {
    'サイト名': ''#,
    #'県名': '',
    #'市町村': '',
    #'緯度': '',
    #'経度': '',
}
dict_ICR = {
    'DM-750': 'START',
    'LS-7': 'START',
    'dummy_stop': 'STOP'
}

msg_rename="""\
【使い方】
　サイトとICレコーダを選択 > 音声フォルダの選択 > 出力フォルダを選択 > 確認後、リネーム実行
【注意】
　- ICレコーダを変更したら、ディレクトリを選び直してください
　- ✅は666リネーム済みでリネームしません
　- 同一録音はマージされます（ DM-750では長時間録音は自動分割され同じタイムスタンプを持つためファイル統合します。）
"""
selected_ICR=''
selected_site=''
dir_sounds="" # 音声ディレクトリ
dir_output="" # 変換後の出力ディレクトリ
list_rename={} # リネームするファイル辞書
file_groups={} # 同一音源のファイル辞書
filelist_remtime=[] # mtimeを変更するファイルリスト


def convert_epoch_to_string(epoch_time):
    return datetime.fromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')


def convert_epoch_to_66(epoch_time):
    return datetime.fromtimestamp(epoch_time).strftime('%y%m%d_%H%M%S')


def convert_epoch_to_x6(epoch_time):
    return datetime.fromtimestamp(epoch_time).strftime('-%H%M%S')


def convert_epoch_to_666(start_epoch, stop_epoch):
    start_66 = convert_epoch_to_66(start_epoch)
    stop_x6  = convert_epoch_to_x6(stop_epoch)
    return start_66 + stop_x6

def get_666(filename,start_epoch,stop_epoch,name_site):
    body_666 = convert_epoch_to_666(start_epoch,stop_epoch)
    new_filename = f'{body_666}_{name_site}_{filename}'
    return new_filename

def check_filename_format(filename):
    import re
    # 6桁の数字とアンダースコアで区切られた形式にマッチする正規表現パターン
    pattern = r'^\d{6}_\d{6}[_-]\d{6}_.*'
    # 正規表現でファイル名がパターンにマッチするかチェック
    return bool(re.match(pattern, filename))

# 音声ファイルリストから、メタデータとしてファイル名、タイムスタンプとdurationを得る関数
def get_metadata_sounds(list_sounds,directory):
    # 音声ファイルの属性を格納するリスト
    metadata_sounds = []
    for file in list_sounds:
        file_stat = os.stat(os.path.join(directory, file))
        mtime = file_stat.st_mtime
        with wave.open(os.path.join(directory, file), 'r') as wav_file:
            duration = wav_file.getnframes() / wav_file.getframerate()
            metadata_sounds.append({ 'filename': file, 'mtime': mtime, 'duration': duration })
    return metadata_sounds


# 同一の録音をmtimeでグループ化する。中身はmetadata
def grouping_sounds(metadata_sounds):
    global file_groups
    # 連続するファイルでmtimeが同じなら同一録音と判断する
    for metadata in sorted(metadata_sounds, key=lambda x: x['filename'], reverse=True):
        # mtimeを四捨五入する
        mtime = round(metadata['mtime'])
        if mtime not in file_groups:
            file_groups[mtime] = []  # 新しいキーに対して空のリストを作成
        file_groups[mtime].append(metadata)
    return file_groups


# ICRが設定されているか？
def is_set_ICR():
    try:
        isStart = dict_ICR[selected_ICR] == 'START'
        return True
    except KeyError:
        return False


# siteが設定されているか？
def is_set_site():
    return bool(selected_site)


# 複数の音声ファイルを結合する関数
def merge_and_rename_audio_files(file_groups, output_file):
    # ファイルリストが空かどうかを確認
    if not file_groups:
        raise ValueError("ファイルリストが空です。")

    # 最初のファイルを出力ファイルとして開く
    with wave.open(file_groups[0], 'rb') as wave_file:
        output_params = wave_file.getparams()

    # 出力ファイルを作成
    with wave.open(output_file, 'wb') as output_wave:
        output_wave.setparams(output_params)

        # ファイル名をソートして順番に読み込み出力ファイルに追記する
        sorted_file_list = sorted(file_groups)
        for file in sorted_file_list:
            print(f'ファイルのマージ：{file} :-> append {output_file}')
            with wave.open(file, 'rb') as input_wave:
                # パラメータの互換性を確認
                if input_wave.getparams() != output_params:
                    raise ValueError(f"音声ファイル {file} のパラメータが一致しません。")

                # フレームを読み込み、出力ファイルに書き込む
                frames = input_wave.readframes(input_wave.getnframes())
                output_wave.writeframes(frames)


def get_duration_of_sound(file):
    # 出力ファイルのdurationを取得する関数
    with wave.open(file, 'rb') as wave_file:
        frames = wave_file.getnframes()
        rate = wave_file.getframerate()
        duration = frames / float(rate)
        return duration



def main(page: ft.Page):
    page.title="nfc-rename"
    def update_dict_site(key, value):
        global selected_site
        dict_site[key] = value
        selected_site = value
        page.update()
        update_site_info()

    def on_dropdown_change(e):
        global selected_ICR  # selected_ICRをグローバル変数として宣言
        selected_ICR = e.control.value  # 選択されたOptionのvalue属性がキーになります
        update_ICR_info()


    def get_sounds_list(directory):
        # 対象の音声ファイルの拡張子
        audio_extensions = ['.wav']
        # ディレクトリ内の全ファイルを取得
        all_files = os.listdir(directory)
        # 音声ファイルのみをフィルタリング
        audio_files = [file for file in all_files if os.path.splitext(file)[1].lower() in audio_extensions]
        # 音声データのリスト
        return audio_files

    def get_output_directory(e: ft.FilePickerResultEvent):
        global dir_output
        if e.path:
            dir_output = e.path
            output_dir_path.value = dir_output
        else:
            output_dir_path.value = "Cancelled!"
        output_dir_path.update()

    def get_renamed_sounds(files_in_same_groups, isStart):
        filename = files_in_same_groups[0]['filename']
        mtime = files_in_same_groups[0]['mtime']
        total_duration = sum(file['duration'] for file in files_in_same_groups)
        start_epoch, stop_epoch = (mtime, mtime + total_duration) if isStart else (mtime - total_duration, mtime)
        new_filename = get_666(filename, start_epoch, stop_epoch, selected_site)

        return new_filename

    # ファイル名の変更に関する情報を更新する関数
    def update_rename_info(file_groups):
        msg=""
        isStart = None
        

        if is_set_site() & is_set_ICR() :
            isStart = dict_ICR[selected_ICR] == 'START'
            for mtime, files in file_groups.items():
                # ファイル名が既にフォーマットされている場合は処理をスキップ
                if not check_filename_format(files[0]['filename']):
                    if len(files) == 1:
                        # 単一ファイルの場合、リストの最初の要素の 'filename' キーを使用
                        filename = files[0]['filename']
                    else:
                        # 拡張子を除いたファイル名を連結し、最後に拡張子を追加する
                        filename = '_'.join(f['filename'].rsplit('.', 1)[0] for f in files) + '.' + files[0]['filename'].split('.')[-1]
                    new_filename = get_renamed_sounds(files,isStart)
                    msg += f"{filename} -> {new_filename}\n"
        else:
            msg = f"Error: 'ICレコーダもしくはサイト名が設定されていません'"
                
        renamed_info.value = msg
        renamed_info.update()
    

    def update_ICR_info(e=None):
        name_ICR.value = f'ICレコーダー[{selected_ICR}] タイムスタンプ：{dict_ICR[selected_ICR]}'
        name_ICR.update()
        info_selected_ICR.value = f'{selected_ICR}: {dict_ICR[selected_ICR]}'
        info_selected_ICR.update()


    def update_site_info(e=None):
        name_site.value = f'ファイル名に追加されるサイト名：{selected_site}'
        name_site.update()
        info_selected_site.value = selected_site
        info_selected_site.update()


    def update_sounds_info(file_groups):
        msg = ""
        str_666 =""
        str_group = ""
        counter_group = 0
        for mtime, files in file_groups.items():
            print(mtime)
            if len(files) == 1:
                str_group = ""
            else:
                counter_group +=1
                str_group = f"同一音源-{counter_group}: "
            # 選択されたfiles[0]のfilename, mtime, durationを取得
            for selected_file in files:
                filename = selected_file['filename']
                str_666 = "️\n✅" if check_filename_format(filename) else "　 "
                mtime = selected_file['mtime']
                duration = selected_file['duration']
                mtime_formatted = convert_epoch_to_string(mtime)
                duration_formatted = str(timedelta(seconds=duration))
                msg += f"{str_666} {str_group}{filename}: 変更時刻: {mtime_formatted}, 長さ: {duration_formatted}\n"

        sound_info.value = msg
        sound_info.update()
        

    # 指定されたパスから音声ファイルのリストを取得し、情報欄を更新する
    def update_sounds_list_and_rename_list(e: ft.FilePickerResultEvent):
        global dir_sounds
        global file_groups 
        list_sounds = []
        file_groups= {}
        if e.path:
            dir_sounds = e.path
            info_sound_dir.value = dir_sounds
            list_sounds = get_sounds_list(dir_sounds)
            metadata_sounds = get_metadata_sounds(list_sounds,dir_sounds)
            file_groups = grouping_sounds(metadata_sounds)
            update_sounds_info(file_groups) # sound欄の更新
            update_rename_info(file_groups) # rename欄の更新
        else:
            info_sound_dir.value = "Cancelled!"
        info_sound_dir.update()


    def rename(from_filename, to_filename):
        print(f"{from_filename} :-> {to_filename}")
        # ファイル名をfrom_filenameからto_filenameに変更する関数
        try:
            # os.rename(from_filename, to_filename)
            print(f"{from_filename} を {to_filename} にリネームしました。")
        except OSError as e:
            print(f"リネーム中にエラーが発生しました: {e}")

    def execute_rename():
        if is_set_site() & is_set_ICR() :
            isStart = dict_ICR[selected_ICR] == 'START'
            for mtime, files in file_groups.items():
                if len(files) == 1:
                    # 単一ファイルの場合、リストの最初の要素の 'filename' キーを使用
                    filename = files[0]['filename']
                    new_filename = get_renamed_sounds(files[0],isStart)
                    original_filename = f"{dir_sounds}/{filename}"
                    after_filename = f"{dir_output}/{new_filename}"
                    if not check_filename_format(filename):
                        rename(original_filename, after_filename)
                else:
                    if not any(check_filename_format(f['filename']) for f in files):
                        # 拡張子を除いたファイル名を連結し、最後に拡張子を追加する
                        filename = '_'.join(f['filename'].rsplit('.', 1)[0] for f in files) + '.' + files[0]['filename'].split('.')[-1]
                        new_filename = get_renamed_sounds(files)
                        after_filename = f"{dir_output}/{new_filename}"
                        merge_and_rename_audio_files(file_groups,output_file=after_filename)


    def cancel_rename():
        # モーダルを閉じる処理
        dialogue_confirm_to_rename.open = False
        page.update()
    
    def update_info_modify_mtime_files(e: ft.FilePickerResultEvent):
        # 選択したファイルのmtimeを取得し、人が読める形式でmtime_of_selected_file.valueに設定
        selected_files_mtime = []
        for file in e.files:
            # ファイルのmtimeを取得
            mtime = os.path.getmtime(file.path)
            # mtimeを人が読める形式に変換
            readable_mtime = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            filelist_remtime.append(file.path)
            selected_files_mtime.append(f"{readable_mtime}: {file.name}")

        info_modify_files.value = '\n'.join(selected_files_mtime)
        info_modify_files.update()


    def datebox_change(e):
        date_picked.value = e.control.value
        date_picked.update()


    def timebox_change(e):
        time_picked.value = e.control.value
        time_picked.update()


    dialogue_confirm_to_rename = ft.AlertDialog(
        title=ft.Text("リネームの確認"),
        content=ft.Text("リネームを実行しますか？"),
        actions=[
            ft.TextButton(
                "実行",
                on_click=lambda e: execute_rename()
            ),
            ft.TextButton(
                "キャンセル",
                on_click=lambda e: cancel_rename()
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )

    # ディレクトリの設定関連
    info_sound_dir = ft.Text(size=10)
    btn_sounds_dir = ft.Row([
        ft.ElevatedButton(
            "音声フォルダ",
            icon=ft.icons.FOLDER,
            on_click=lambda _: dialogue_sounds_dir.get_directory_path(),
        ),
        info_sound_dir,
    ])

    output_dir_path = ft.Text(size=10)
    btn_output_dir = ft.Row([
        ft.ElevatedButton(
            "出力フォルダ",
            icon=ft.icons.FOLDER,
            on_click=lambda _: dialogue_output_dir.get_directory_path(),
        ),
        output_dir_path,
    ])

    sound_info = ft.TextField(
        text_size=10,
        label="オーディオファイル:",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value=""
    )


    dialogue_sounds_dir = ft.FilePicker(on_result=update_sounds_list_and_rename_list)
    dialogue_output_dir = ft.FilePicker(on_result=get_output_directory)
    dialogue_modify_mtime_file = ft.FilePicker(on_result=update_info_modify_mtime_files)

    renamed_info = ft.TextField(
        text_size=10,
        label="ファイル名変更後：",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value="",
    )


    name_site = ft.Text()
    name_ICR = ft.Text()

    info_selected_site = ft.TextField(
        label = f"録音サイト:{selected_site}",
        text_size=14,
        disabled= True)

    info_selected_ICR = ft.TextField(
        label = f"ICレコーダ:{selected_ICR}",
        text_size=14,
        disabled= True)

    # dict_ICRから動的に生成する。
    dropdown_options = [ft.dropdown.Option(key) for key, value in dict_ICR.items()]

    
    status_rename = ft.Text(size=10)
    info_modified_mtime = ft.TextField(
        text_size=10,
        label="変更結果",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value="",
        )


    # リネーム実行ボタンのイベントハンドラを修正
    def btn_extract_on_click(_):
        if is_set_site() and is_set_ICR():
            dialogue_confirm_to_rename.open = True  # AlertDialogを開く
            page.update()


    def change_mtime_for_selected_files():
        tz_info = timezone(timedelta(hours=9))

        if not filelist_remtime:
            info_modified_mtime.value = "mtimeを変更するファイルが選択されていません。"
            info_modified_mtime.update()
            return

        # 日付と時刻が設定されているか確認
        if not date_picked.value or not time_picked.value:
            info_modified_mtime.value = "日付または時刻が設定されていません。"
            info_modified_mtime.update()
            return

        # date_picked とtime_picked からタイムゾーンTZ=9でエポック秒に変換
        datetime_str = f"{date_picked.value} {time_picked.value}"
        try:
            datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            datetime_obj = datetime_obj.replace(tzinfo=tz_info)
            epoch_seconds = int(datetime_obj.timestamp())
        except ValueError as e:
            info_modified_mtime.value = f"日付または時刻の形式が正しくありません: {e}"
            info_modified_mtime.update()
            return

        # 選択されたファイルのmtimeを変更
        msg = ""
        for file_path in filelist_remtime:
            print(file_path)
            if file_path:  # 空の行を無視
                try:
                    datetime_from_epoch = datetime.fromtimestamp(epoch_seconds, tz_info)
                    os.utime(file_path, (datetime_from_epoch.timestamp(), datetime_from_epoch.timestamp()))
                    file_name = os.path.basename(file_path)
                    msg += f"{file_name} のmtimeを更新しました。\n"
                except FileNotFoundError:
                    msg += f"{file_path} が見つかりません。\n"
                except Exception as e:
                    msg += f"エラーが発生しました: {e}\n"
        info_modified_mtime.value = msg
        info_modified_mtime.update()


    # ダイアローグの追加                
    page.overlay.append(dialogue_sounds_dir)
    page.overlay.append(dialogue_output_dir)
    page.overlay.append(dialogue_confirm_to_rename)
    page.overlay.append(dialogue_modify_mtime_file)

    # タイムスタンプの設定関係
    info_modify_files = ft.TextField(
        text_size=10,
        label="選択ファイル：",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value=""
    )
    date_picked=ft.Text("date",size=10)
    time_picked=ft.Text("time",size=10)
    # UIの定義
    t = ft.Tabs(
        selected_index=2,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="サイト名",
                icon=ft.icons.PLACE,
                content=ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Text(value="録音地を登録してください（暫定の入力です）。"),
                        ft.TextField(label="サイト名(例FukuiEchizen)",
                                    autofocus = True,
                                    value=dict_site['サイト名'],
                                    on_change=lambda e: update_dict_site('サイト名', e.control.value)
                                    ),
                        name_site
                    ]),
                ),
            ),
            ft.Tab(
                text="ICレコーダ",
                icon=ft.icons.KEYBOARD_VOICE,
                content=ft.Container(
                    padding=20,
                    content=ft.Column([
                        ft.Dropdown(
                            label = "IC Recorder",
                            hint_text="録音したICレコーダを選択してください。用いるデータはタイムスタンプが開始(START)か終了(STOP)です。",
                            options = dropdown_options,
                            on_change=on_dropdown_change
                        ),
                        name_ICR
                    ])
                ),
            ),
            ft.Tab(
                text="リネーム to 666",
                icon=ft.icons.DRIVE_FILE_MOVE_OUTLINE,
                content=ft.Container(
                    margin = 20,
                    content=ft.Column([
                        ft.Text(msg_rename),
                        ft.Row([
                            info_selected_site,
                            info_selected_ICR,
                        ]),
                        btn_sounds_dir,
                        btn_output_dir,
                        sound_info,
                        renamed_info,
                        ft.Row([
                            ft.ElevatedButton(
                                "リネーム実行",
                                icon=ft.icons.EMOJI_EMOTIONS,
                                on_click=btn_extract_on_click,  # 修正したイベントハンドラを使用
                            ),
                            status_rename,
                        ]),
                    ])
                ),
            ),
            ft.Tab(
                text="recover from 666",
                icon=ft.icons.DRIVE_FILE_MOVE_RTL_OUTLINED,
                content=ft.Text("under constructing"),
            ),
            ft.Tab(
                text="タイムスタンプ変更",
                icon=ft.icons.MORE_TIME_ROUNDED,
                content=ft.Container(
                    margin=20,
                    content=ft.Column([
                        ft.Text("ファイルのタイムスタンプを変更します。変更するのは最終修正時刻(mtime)です。Macの場合、作成日(birthtime)がありますが、これは変更されません。"),
                        ft.Row([
                            ft.ElevatedButton(
                                "ファイル選択",
                                icon=ft.icons.AUDIO_FILE_OUTLINED,
                                on_click=lambda _: dialogue_modify_mtime_file.pick_files(
                                    allow_multiple=True
                                ),
                            ),
                        ]),
                        info_modify_files,
                        ft.Row([
                            ft.TextField(
                                label="日付入力",
                                hint_text="2024-04-01",
                                icon=ft.icons.CALENDAR_MONTH_OUTLINED,
                                multiline=False,
                                on_change=datebox_change,
                            ),
                            date_picked,
                        ]),
                        ft.Row([
                            ft.TextField(
                                label="時刻入力",
                                hint_text="01:23:45",
                                icon=ft.icons.ACCESS_TIME,
                                multiline=False,
                                on_change=timebox_change,
                            ),
                            time_picked
                        ]),
                        ft.Row([
                            ft.ElevatedButton(
                                "時刻入力",
                                icon=ft.icons.EMOJI_EMOTIONS,
                                on_click=lambda _: change_mtime_for_selected_files()
                            ),
                        ]),
                        info_modified_mtime
                    ])
                ),
            ),
        ],
        expand=1,
    )

    page.add(t)

ft.app(target=main)
