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


def main(page: ft.Page):


    dlg = ft.AlertDialog(
        title=ft.Text("Hello, you!"), on_dismiss=lambda e: print("Dialog dismissed!")
    )
    

    def close_dlg(e):
        dlg_modal.open = False
        page.update()
    


    def open_dlg_modal(e):
        global selected_site
        # dlg_modalのcontentを動的に生成して更新
        dlg_modal.content = ft.Column([
            ft.Text("サイト名: " + dict_site['サイト名']),
            #ft.Text("緯度: " + dict_site['緯度']),
            #ft.Text("経度: " + dict_site['経度']),
            #ft.Text("県名: " + dict_site['県名']),
            #ft.Text("市町村: " + dict_site['市町村'])
        ])
        selected_site = dict_site['サイト名']
        page.dialog = dlg_modal
        dlg_modal.open = True
        page.update()
        update_site_info()



    def set_name_site(e=None):
        #global selected_site
        #selected_site = dict_site['サイト名']
        #page.dialog = dlg_modal
        #dlg_modal.open = True
        #page.update()
        update_site_info()
        name_site.value = selected_site
        name_site.update()


    dlg_modal = ft.AlertDialog(
        modal=True,
        title=ft.Text("サイト情報の確認"),
        content=ft.Column([]),
        actions=[
            ft.TextButton("ok", on_click=close_dlg),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=lambda e: print("Modal dialog dismissed!"),
    )

    def open_dlg(e):
        page.dialog = dlg
        dlg.open = True
        page.update()


    def update_dict_site(key, value):
        global selected_site
        dict_site[key] = value
        selected_site = value
        page.update()
        update_site_info()

    def on_dropdown_change(e):
        global selected_ICR  # selected_ICRをグローバル変数として宣言
        selected_ICR = e.control.value  # 選択されたOptionのvalue属性がキーになります
        # print(f"選択されたICレコーダのキー: {selected_ICR}")
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


    def get_sound_directory(e: ft.FilePickerResultEvent):
        #msg = ""
        list_sounds = []
        if e.path:
            sounds_dir_path.value = e.path
            #list_sounds = get_merge_sounds_group(e.path)
            list_sounds = get_sounds_list(e.path)
            update_sounds_info(list_sounds,sounds_dir_path)
            update_rename_info(list_sounds)
        else:
            sounds_dir_path.value = "Cancelled!"
        sounds_dir_path.update()


    def update_ICR_info():
        info_selected_ICR.value = selected_ICR
        info_selected_ICR.update()


    def update_site_info():
        info_selected_site.value = selected_site
        info_selected_site.update()

    def update_sounds_info(list_sounds,directory):
        # 音声ファイルの属性を格納するリスト
        timestamp_sounds = []
        # 同じmtimeを持っているグループを作成
        def set_timestamp_sounds_group(timestamp_sounds):
            msg = ""
            file_groups = {}
            prev_mtime = 0
            prev_start_epoch = 0
            for timestamp in sorted(timestamp_sounds, key=lambda x: x['filname'], reverse=True):
                mtime_epoch = timestamp['mtime']
                mtime_formatted = convert_epoch_to_string(mtime_epoch)
                #print(f"mtime_epoch: {mtime_epoch}, ファイル名: {timestamp['filname']}")
                if mtime_epoch not in file_groups:
                    file_groups[mtime_epoch] = []
                    # 同一録音グループの条件
                    if mtime_epoch == prev_mtime:
                        stop_epoch = prev_start_epoch
                    else:
                        stop_epoch = timestamp['mtime']
                file_groups[mtime_epoch].append(timestamp['filname'])

                duration = timestamp['duration']
                start_epoch = stop_epoch - duration
                duration_formatted = str(timedelta(seconds=timestamp['duration']))
                start_formatted = convert_epoch_to_string(start_epoch)
                stop_formatted = convert_epoch_to_string(stop_epoch)
                msg += f" {timestamp['filname']}: 変更時刻: {mtime_formatted}, 長さ: {duration_formatted}\n"
                # 一つ前を記憶する
                prev_mtime = mtime_epoch
                prev_start_epoch = start_epoch
            return msg
        for file in list_sounds:
            file_stat = os.stat(os.path.join(directory.value, file))
            file_timestamp = file_stat.st_mtime
            with wave.open(os.path.join(directory.value, file), 'r') as wav_file:
                duration = wav_file.getnframes() / wav_file.getframerate()
                timestamp_sounds.append({ 'filname': file, 'mtime': file_timestamp, 'duration': duration })
        msg = set_timestamp_sounds_group(timestamp_sounds)
        sounds_info_in_directory.value = msg
        sounds_info_in_directory.update()



    def update_rename_info(msg):
        sounds_info_rename.value = msg
        sounds_info_rename.update()
    #pick_directory_dialog = ft.FilePicker(
    #    on_result=pick_directory_result,
    #    pick_directories=True
    #)
    #selected_directory = ft.Text()
    sounds_dir_path = ft.Text(size=10)
    select_sounds_dir= ft.Row([
                                ft.ElevatedButton(
                                    "音声フォルダ選択",
                                    icon=ft.icons.SNIPPET_FOLDER,
                                    on_click=lambda _: dialogue_sounds_dir.get_directory_path(),
                                ),
                                sounds_dir_path,
                        ])
    output_dir_path = ft.Text(size=10)
    select_output_dir= ft.Row([
                                ft.ElevatedButton(
                                    "出力フォルダ選択",
                                    icon=ft.icons.FOLDER,
                                    on_click=lambda _: dialogue_output_dir.get_directory_path(),
                                ),
                                output_dir_path,
                        ])
    default_sound_info = f""
    sounds_info_in_directory = ft.TextField(
        text_size=10,
        label="オーディオファイル",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value=default_sound_info,
    )
    dialogue_sounds_dir = ft.FilePicker(on_result=get_sound_directory)
    dialogue_output_dir = ft.FilePicker(on_result=get_output_directory)

    sounds_info_rename = ft.TextField(
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

    info_selected_site = ft.TextField(
        label = f"録音サイト:{selected_site}",
        text_size=10,
        disabled= True)

    info_selected_ICR = ft.TextField(
        label = f"ICレコーダ:{selected_ICR}",
        text_size=10,
        disabled= True)

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
                        ft.TextField(label="サイト名(例FukuiEchizen)", value=dict_site['サイト名'], on_change=lambda e: update_dict_site('サイト名', e.control.value)),

                        #ft.TextField(label="県名", value=dict_site['県名'], on_change=lambda e: update_dict_site('県名', e.control.value)),
                        #ft.TextField(label="市町村", value=dict_site['市町村'], on_change=lambda e: update_dict_site('市町村', e.control.value)),
                        #ft.TextField(label="緯度", value=dict_site['緯度'], on_change=lambda e: update_dict_site('緯度', e.control.value)),
                        #ft.TextField(label="経度", value=dict_site['経度'], on_change=lambda e: update_dict_site('経度', e.control.value)),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    text="設定",
                                    on_click = set_name_site
                                    ),
                                ft.Text("ファイル名に用いられるサイト名："),
                                name_site
                                ]
                            ),
                    ]),
                ),
            ),
            ft.Tab(
                text="ICレコーダ",
                icon=ft.icons.KEYBOARD_VOICE,
                content=ft.Container(
                    padding=20,
                    content=ft.Dropdown(
                        label = "IC Recorder",
                        hint_text="録音したICレコーダを選択してください。用いるデータはタイムスタンプが開始(START)か終了(STOP)です。",
                        options=[
                            ft.dropdown.Option('DM-750: ' + dict_ICR['DM-750']),
                            ft.dropdown.Option('LS-7: ' + dict_ICR['LS-7']),
                            ft.dropdown.Option('dummy: ' + dict_ICR['dummy_stop']),
                        ],
                        on_change=on_dropdown_change
                    )
                ),
            ),
            ft.Tab(
                text="rename to 666",
                icon=ft.icons.DRIVE_FILE_MOVE_OUTLINE,
                content=ft.Container(
                    margin = 20,
                    content=ft.Column([
                        ft.Row([
                            info_selected_site,
                            info_selected_ICR,
                        ]),
                        select_sounds_dir,
                        select_output_dir,
                        sounds_info_in_directory,
                        sounds_info_rename 
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
