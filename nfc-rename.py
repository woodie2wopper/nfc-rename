# -*- coding: utf-8 -*-
import flet as ft
import os
import wave
from datetime import datetime, timedelta



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

selected_ICR=''
selected_site=''


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
    file_groups = {}
    # 連続するファイルでmtimeが同じなら同一録音と判断する
    for metadata in sorted(metadata_sounds, key=lambda x: x['filename'], reverse=True):
        mtime = int(metadata['mtime'])
        if mtime not in file_groups:
            file_groups[mtime] = []  # 新しいキーに対して空のリストを作成
        file_groups[mtime].append(metadata)
    #for mtime, group in file_groups.items():
    return file_groups


def is_set_ICR():
    try:
        isStart = dict_ICR[selected_ICR] == 'START'
        return True
    except KeyError:
        return False


def is_set_site():
    return bool(selected_site)

# dlg = ft.AlertDialog(
#     title=ft.Text("Hello, you!"), on_dismiss=lambda e: print("Dialog dismissed!")
# )
# 

# def close_dlg(e):
#     dlg_modal.open = False
#     page.update()
# 


# def open_dlg_modal(e):
#     global selected_site
#     # dlg_modalのcontentを動的に生成して更新
#     dlg_modal.content = ft.Column([
#         ft.Text("サイト名: " + dict_site['サイト名']),
#         #ft.Text("緯度: " + dict_site['緯度']),
#         #ft.Text("経度: " + dict_site['経度']),
#         #ft.Text("県名: " + dict_site['県名']),
#         #ft.Text("市町村: " + dict_site['市町村'])
#     ])
#     selected_site = dict_site['サイト名']
#     page.dialog = dlg_modal
#     dlg_modal.open = True
#     page.update()
#     update_site_info()


# dlg_modal = ft.AlertDialog(
#     modal=True,
#     title=ft.Text("サイト情報の確認"),
#     content=ft.Column([]),
#     actions=[
#         ft.TextButton("ok", on_click=close_dlg),
#     ],
#     actions_alignment=ft.MainAxisAlignment.END,
#     on_dismiss=lambda e: print("Modal dialog dismissed!"),
# )

# def open_dlg(e):
#     page.dialog = dlg
#     dlg.open = True
#     page.update()



def main(page: ft.Page):


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
        #msg = ""
        if e.path:
            output_dir_path.value = e.path
            #list_sounds = get_merge_sounds_group(e.path)
        else:
            output_dir_path.value = "Cancelled!"
        output_dir_path.update()


    # ファイル名の変更に関する情報を更新する関数
    def update_rename_info(file_groups):
        msg=""
        isStart = None
        
        def get_renamed_sounds(files_in_same_groups):
            mtime = files[0]['mtime']
            total_duration = sum(file['duration'] for file in files_in_same_groups)
            start_epoch, stop_epoch = (mtime, mtime + total_duration) if isStart else (mtime - total_duration, mtime)
            new_filename = get_666(filename, start_epoch, stop_epoch, selected_site)

            return new_filename

        if is_set_site() & is_set_ICR() :
            isStart = dict_ICR[selected_ICR] == 'START'
            for mtime, files in file_groups.items():
                if len(files) == 1:
                    # 単一ファイルの場合、リストの最初の要素の 'filename' キーを使用
                    filename = files[0]['filename']
                else:
                    # 拡張子を除いたファイル名を連結し、最後に拡張子を追加する
                    filename = '_'.join(f['filename'].rsplit('.', 1)[0] for f in files) + '.' + files[0]['filename'].split('.')[-1]
                new_filename = get_renamed_sounds(files)
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
                mtime = selected_file['mtime']
                duration = selected_file['duration']
                mtime_formatted = convert_epoch_to_string(mtime)
                duration_formatted = str(timedelta(seconds=duration))
                msg += f"{str_group}{filename}: 変更時刻: {mtime_formatted}, 長さ: {duration_formatted}\n"

        sound_info.value = msg
        sound_info.update()
        

    # 指定されたパスから音声ファイルのリストを取得し、情報欄を更新する
    def update_sounds_list_and_rename_list(e: ft.FilePickerResultEvent):
        list_sounds = []
        if e.path:
            info_sound_dir.value = e.path
            list_sounds = get_sounds_list(e.path)
            metadata_sounds = get_metadata_sounds(list_sounds,e.path)
            file_groups = grouping_sounds(metadata_sounds)
            update_sounds_info(file_groups) # sound欄の更新
            update_rename_info(file_groups) # rename欄の更新
        else:
            info_sound_dir.value = "Cancelled!"
        info_sound_dir.update()


    # ディレクトリの設定関連
    info_sound_dir = ft.Text(size=10)
    btn_sounds_dir = ft.Row([
                                ft.ElevatedButton(
                                    "音声フォルダ選択",
                                    icon=ft.icons.FOLDER,
                                    on_click=lambda _: dialogue_sounds_dir.get_directory_path(),
                                ),
                                info_sound_dir,
                        ])

    output_dir_path = ft.Text(size=10)
    btn_output_dir = ft.Row([
                                ft.ElevatedButton(
                                    "出力フォルダ選択",
                                    icon=ft.icons.FOLDER,
                                    on_click=lambda _: dialogue_output_dir.get_directory_path(),
                                ),
                                output_dir_path,
                        ])

    # リネーム関連
    status_rename = ft.Text(size=10)
    btn_extract = ft.Row([
                            ft.ElevatedButton(
                                "リネーム実行",
                                icon=ft.icons.EMOJI_EMOTIONS,
                                on_click=lambda _: dialogue_output_dir.open_confirm_to_rename(),
                            ),
                            status_rename,
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

    renamed_info = ft.TextField(
        text_size=10,
        label="ファイル名変更後：",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value="",
    )

    page.overlay.append(dialogue_sounds_dir)
    page.overlay.append(dialogue_output_dir)

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
                            options=dropdown_options,
                            #[
                            #    ft.dropdown.Option('DM-750' + dict_ICR['DM-750']),
                            #    ft.dropdown.Option('LS-7' + dict_ICR['LS-7']),
                            #    ft.dropdown.Option('dummy_stop' + dict_ICR['dummy_stop']),
                            #],
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
                        ft.Text("""DM-750で長時間録音されファイルサイズが2GBを超えると自動で分割されます。
                                分割されたファイルは同じタイムスタンプを持つため、そのままファイル名を666形式にすると実際と異なった時刻を示すことになります。
                                そのため、分割されたファイルを一つのファイルに統合し、666形式にリネームされます。
                                【条件：連続したファイルでmtimeが同じなら同一音源である】
                                """),
                        ft.Row([
                            info_selected_site,
                            info_selected_ICR,
                        ]),
                        btn_sounds_dir,
                        btn_output_dir,
                        sound_info,
                        renamed_info,
                        btn_extract

                    ])
                ),
            ),
            ft.Tab(
                text="recover from 666",
                icon=ft.icons.DRIVE_FILE_MOVE_RTL_OUTLINED,
                content=ft.Text("under constructing"),
            ),
        ],
        expand=1,
    )

    page.add(t)

ft.app(target=main)
