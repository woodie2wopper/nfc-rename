# -*- coding: utf-8 -*-
import flet as ft
import os
import pathlib
#import wave
import soundfile as sf
from datetime import timezone, datetime, timedelta
import re


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
　サイト名入力＋ICレコーダ選択 > 録音フォルダ選択 > 出力フォルダ選択 > 確認後、リネーム実行
【注意】
　- ICレコーダを変更したら、ディレクトリを選び直してください
　- ⭕️は同一音源と思われます
　- ✅は666リネーム済みでリネームしません
　- 同一録音はマージされます（ DM-750では長時間録音は自動分割され同じタイムスタンプを持つためファイル統合します。）
"""
selected_ICR=''
name_site=''
dir_sounds="" # 音声ディレクトリ
dir_output="" # 変換後の出力ディレクトリ
list_rename={} # リネームするファイル辞書
metadata_group={} # 同一音源のメタデータ（filename、mtime、is666、file_pathとか）
filelist_recover=[] # recoverを変更するファイルリスト
filelist_remtime=[] # mtimeを変更するファイルリスト
pattern = r'(\d{6})_(\d{6})[_-](\d{6})_'


def convert_epoch_to_string(epoch_time):
    return datetime.fromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')


def convert_epoch_to_66(epoch_time):
    return datetime.fromtimestamp(epoch_time).strftime('%y%m%d_%H%M%S')


def convert_epoch_to_x6(epoch_time):
    return datetime.fromtimestamp(epoch_time).strftime('_%H%M%S')


def convert_epoch_to_666(start_epoch, stop_epoch):
    start_66 = convert_epoch_to_66(start_epoch)
    stop_x6  = convert_epoch_to_x6(stop_epoch)
    return start_66 + stop_x6

def get_666(filename,start_epoch,stop_epoch,name_site_str):
    body_666 = convert_epoch_to_666(start_epoch,stop_epoch)
    new_filename = f'{body_666}_{name_site_str}_{filename}'
    return new_filename

        
def show_message(instance_text,msg):
    instance_text.value = msg
    instance_text.update()


def recover_filename(filename):
    # "_"で区切られたファイル名を分割する
    parts = filename.split('_')
    # 最初の4つの部分を削除する
    recovered_parts = parts[4:]
    # 残りの部分を"_"で結合して返す
    recovered_filename = '_'.join(recovered_parts)
    return recovered_filename

def split_filename(filename):
    # "_"で区切られたファイル名を分割する
    parts = filename.split('_')
    # 最初の要素をdate_str、２番目をstart_time,３番目をstop_timeに分ける
    if len(parts) >= 3:
        date_str = parts[0]
        start_time = parts[1]
        stop_time = parts[2]
        return date_str, start_time, stop_time

def get_start_stop_from_666(filename):
    # 666形式のファイル名から開始と終了のエポックタイムを抽出する正規表現
    global pattern
    #pattern = r'(\d{6})_(\d{6})[_-](\d{6})_'
    match = re.search(pattern, filename)
    if match:
        date_str, start_time, stop_time = split_filename(filename)
        start_str = f"{date_str}_{start_time}"
        stop_str = f"{date_str}_{stop_time}"
        # 日付と時刻の文字列をdatetimeオブジェクトに変換
        start_dt = datetime.strptime(start_str, '%y%m%d_%H%M%S')
        stop_dt = datetime.strptime(stop_str, '%y%m%d_%H%M%S')
        # datetimeオブジェクトからエポックタイムに変換
        start_epoch = int(start_dt.timestamp())
        stop_epoch = int(stop_dt.timestamp())
        if stop_epoch < start_epoch:
            stop_epoch += 12 * 60 * 60  # 12時間を秒数で足す
        return start_epoch, stop_epoch
    else:
        raise ValueError(" ファイル名が666形式ではありません。")


# 正規表現でファイル名がパターンにマッチするかチェック
def check_filename_format(filename):
    import re
    global pattern
    return bool(re.match(pattern, filename))


# 同一の録音をmtimeでグループ化する。中身はmetadata
def grouping_sounds(metadata_sounds):
    global metadata_group
    # 連続するファイルでmtimeが同じなら同一録音と判断する
    for metadata in sorted(metadata_sounds, key=lambda x: x['filename'], reverse=True):
        # mtimeを四捨五入する
        mtime = round(metadata['mtime'])
        if mtime not in metadata_group:
            metadata_group[mtime] = []  # 新しいキーに対して空のリストを作成
        metadata_group[mtime].append(metadata)
    return metadata_group


# ICRが設定されているか？
def is_set_ICR():
    try:
        isStart = dict_ICR[selected_ICR] == 'START'
        return True
    except KeyError:
        return False


# siteが設定されているか？
def is_set_site():
    return bool(name_site)


# 複数の音声ファイルを結合する関数
def merge_and_rename_audio_files(metadata_group, output_file):
    # ファイルリストが空かどうかを確認
    if not metadata_group:
        raise ValueError("ファイルリストが空です。")

    # 最初のファイルを出力ファイルとして開く
    with wave.open(metadata_group[0], 'rb') as wave_file:
        output_params = wave_file.getparams()

    # 出力ファイルを作成
    with wave.open(output_file, 'wb') as output_wave:
        output_wave.setparams(output_params)

        # ファイル名をソートして順番に読み込み出力ファイルに追記する
        sorted_file_list = sorted(metadata_group)
        print(f'sorted_file_list:{sorted_file_list}')
        for file in sorted_file_list:
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
    page.window_width=800
    page.window_height=1000
    #def update_dict_site(key, value):
    #    global selected_site
    #    dict_site[key] = value
    #    selected_site = value
    #    page.update()
    #    update_site_info()

    # flet関連
    status_rename_result = ft.Text(size=10)
    info_sound_dir = ft.Text(size=10)
    output_dir_path = ft.Text(size=10)
    name_ICR = ft.Text(size=10)

    btn_sounds_dir = ft.Row([
        ft.ElevatedButton(
            "音声フォルダ",
            icon=ft.icons.FOLDER,
            on_click=lambda _: dialogue_sounds_dir.get_directory_path(),
        ),
        info_sound_dir,
    ])

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


    renamed_info = ft.TextField(
        text_size=10,
        label="メッセージ：",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value="",
    )

    info_name_site = ft.Text(size=10)
    info_selected_ICR = ft.Text(size=10)

    # dict_ICRから動的に生成する。
    dropdown_options = [ft.dropdown.Option(key) for key, value in dict_ICR.items()]

    
    info_modified_mtime = ft.TextField(
        text_size=10,
        label="変更結果",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value="",
        )

    status_recover = ft.TextField(
        text_size=10,
        label="メッセージ：",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value="",
        )

    status_recover_result = ft. Text(size=10)


    def changed_name_site(e):
        global name_site
        name_site=e.control.value
        info_name_site.value = name_site
        info_name_site.update()


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

    def get_renamed_sound(metadata_sound, isStart):
        global name_site
        filename = metadata_sound['filename']
        mtime = metadata_sound['mtime']
        duration = metadata_sound['duration']
        start_epoch, stop_epoch = (mtime, mtime + duration) if isStart else (mtime - duration, mtime)
        new_filename = get_666(filename, start_epoch, stop_epoch, name_site)
        return new_filename


    def get_renamed_sounds(metadata_in_same_groups, isStart):
        global name_site
        filename = metadata_in_same_groups[0]['filename']
        mtime = metadata_in_same_groups[0]['mtime']
        total_duration = sum(file['duration'] for file in metadata_in_same_groups)
        start_epoch, stop_epoch = (mtime, mtime + total_duration) if isStart else (mtime - total_duration, mtime)
        new_filename = get_666(filename, start_epoch, stop_epoch, name_site)
        return new_filename

    # ファイル名の変更に関する情報を更新する関数
    def update_rename_info(metadata_group):
        msg=""
        isStart = None

        if is_set_site() & is_set_ICR() :
            isStart = dict_ICR[selected_ICR] == 'START'
            for mtime, files in metadata_group.items():
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
        #name_ICR.value = f'ICレコーダー[{selected_ICR}] タイムスタンプ：{dict_ICR[selected_ICR]}'
        #name_ICR.update()
        info_selected_ICR.value = f'{dict_ICR[selected_ICR]}'
        info_selected_ICR.update()


    #def update_site_info(e=None):
    #    name_site.value = f'ファイル名に追加されるサイト名：{selected_site}'
    #    name_site.update()
    #    info_selected_site.value = selected_site
    #    info_selected_site.update()


    def update_sounds_info(metadata_group):
        msg = ""
        str_666 =""
        str_group = ""
        counter_group = 0
        for mtime, files in metadata_group.items():
            if len(files) == 1:
                str_group = ""
            else:
                counter_group +=1
                str_group += f"⭕"
            # 選択されたfiles[0]のfilename, mtime, durationを取得
            for selected_file in files:
                filename = selected_file['filename']
                str_666 = "️\n✅" if check_filename_format(filename) else "　 "
                mtime = selected_file['mtime']
                duration = selected_file['duration']
                mtime_formatted = convert_epoch_to_string(mtime)
                duration_formatted = str(timedelta(seconds=duration))
                msg += f"{str_666} {str_group} : {filename}: 変更時刻: {mtime_formatted}, 長さ: {duration_formatted}\n"

        sound_info.value = msg
        sound_info.update()


    # 指定されたパスから音声ファイルのリストを取得し、情報欄を更新する
    def update_sounds_list_and_rename_list(e: ft.FilePickerResultEvent):
        global dir_sounds
        global metadata_group 
        list_sounds = []
        metadata_group= {}
        if e.path:
            dir_sounds = e.path
            info_sound_dir.value = dir_sounds
            list_sounds = get_sounds_list(dir_sounds)
            #print(f'list_sounds:{list_sounds}')
            metadata_sounds = get_metadata_sounds(list_sounds,dir_sounds)
            print(f'metadata_sounds:{metadata_sounds}')
            metadata_group = grouping_sounds(metadata_sounds)
            update_sounds_info(metadata_group) 
            update_rename_info(metadata_group) 
        else:
            info_sound_dir.value = "Cancelled!"
        info_sound_dir.update()


    #def rename(from_file_path, to_file_path):
    #    # ファイル名をfrom_filenameからto_filenameに変更する関数
    #    try:
    #        os.rename(from_file_path, to_file_path)
    #        print(f"{from_file_path} を {to_file_path} にリネームしました。")
    #    except OSError as e:
    #        print(f"リネーム中にエラーが発生しました: {e}")

    #def execute_rename():
    #    if is_set_site() & is_set_ICR() :
    #        isStart = dict_ICR[selected_ICR] == 'START'
    #        for mtime, files in metadata_group.items():
    #            print(files)
    #            if len(files) == 1:
    #                # 単一ファイルの場合、リストの最初の要素の 'filename' キーを使用
    #                org_filename = files[0]['filename']
    #                org_file_path = os.path.join(dir_sounds, org_filename)
    #                new_filename = get_renamed_sound(files[0],isStart)
    #                new_file_path = os.path.join(dir_output, new_filename)
    #                if not check_filename_format(org_filename):
    #                    rename(org_file_path, new_file_path)
    #            else:
    #                if not any(check_filename_format(f['filename']) for f in files):
    #                    # 拡張子を除いたファイル名を連結し、最後に拡張子を追加する
    #                    filename = '_'.join(f['filename'].rsplit('.', 1)[0] for f in files) + '.' + files[0]['filename'].split('.')[-1]
    #                    new_filename = get_renamed_sounds(files)
    #                    after_filename = f"{dir_output}/{new_filename}"
    #                    merge_and_rename_audio_files(metadata_group,output_file=after_filename)


    #def cancel_rename():
    #    # モーダルを閉じる処理
    #    dialogue_confirm_to_rename.open = False
    #    page.update()
    
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


    
    # 音声ファイルリストから、メタデータとしてファイル名、タイムスタンプとdurationを得る関数
    def get_metadata_sounds(list_sounds,directory):
        # 音声ファイルの属性を格納するリスト
        metadata_sounds = []
        #status_messages = []
        for filename in list_sounds:
            is666 = check_filename_format(filename)
            file_path = os.path.join(directory, filename)
            # ファイルの最終変更時刻を取得
            mtime = os.path.getmtime(file_path)
            # ファイルサイズが0でないことを確認
            if os.path.getsize(file_path) == 0:
                print(f"スキップされた空のファイル: {filename}")
                continue
            try:
            # soundfileを使用してファイルを読み込む
                data, samplerate = sf.read(file_path)
                duration = len(data) / float(samplerate)
                metadata_sounds.append({ 
                    'filename': filename, 
                    'mtime': mtime, 
                    'duration': duration, 
                    'file_path': file_path, 
                    'is666': is666})
            except RuntimeError as e:
                print(f"スキップされた無効なオーディオファイル: {filename} ({e})")

            #    file_stat = os.stat(file_path)
            #    mtime = file_stat.st_mtime
            #    with wave.open(file_path, 'r') as wav_file:
            #        duration = wav_file.getnframes() / wav_file.getframerate()
            #        metadata_sounds.append({ 
            #            'filename': filename, 
            #            'mtime': mtime, 
            #            'duration': duration, 
            #            'file_path': file_path, 
            #            'is666': is666})
            #except ValueError as e:
            #    status_messages.append(f"スキップされた無効なWAVEファイル: {filename} ({e})")
            #if not status_messages:
            #    status_rename_result.value =  "リネーム成功: " + '\n'.join(new_filename) 
            #else:
            #    status_rename_result.value = '\n'.join(status_messages)
        return metadata_sounds
        
    def update_info_recover_filename(e: ft.FilePickerResultEvent):
        filenames_recover = []
        # 選択したファイルのmtimeを取得し、人が読める形式でmtime_of_selected_file.valueに設定
        selected_files = []
        for file in e.files:
            filenames_recover.append(file.path)
            # ファイルのmtimeを取得
            mtime = os.path.getmtime(file.path)
            # mtimeを人が読める形式に変換
            readable_mtime = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            selected_files.append(f"{readable_mtime} {file.name}")
        
        info_recover_filename.value = '\n'.join(selected_files)
        info_recover_filename.update()

        # 復元後のファイル名表示
        update_status_recover(filenames_recover)


    def update_status_recover(filenames_recover):
        global filelist_recover
        global pattern
        # status_recoverに表示するメッセージを初期化
        status_messages = []
        selected_files = []
        for file_path in filenames_recover:
            filename = os.path.basename(file_path)
            # 666形式のファイル名かどうかをチェックする正規表現パターン
            #pattern = r'^\d{6}_\d{6}[_-]\d{6}_.*$'
            # 正規表現でファイル名がパターンにマッチするかチェック
            try:
                if re.match(pattern, filename):
                    recovered_filename = recover_filename(filename)
                    recovered_path = os.path.join(os.path.dirname(file_path), recovered_filename)
                else:
                    raise ValueError("ファイル名が666形式ではありません。")

                if not is_set_ICR():
                    raise ValueError( "ICレコーダが選択されていないか、無効な値です")

                # ファイル名からstart_epochとstop_epochを取得
                start_epoch, stop_epoch = get_start_stop_from_666(filename)
                # dict_ICRの値に基づいてmtimeをstart_epochまたはstop_epochに設定
                if dict_ICR[selected_ICR] == 'START':
                    mtime = start_epoch
                elif dict_ICR[selected_ICR] == 'STOP':
                    mtime = stop_epoch
                else:
                    raise ValueError("ICレコーダが選択されていません")

                # 取得したタイムスタンプを人が読める形式に変換
                readable_mtime = convert_epoch_to_string(mtime)
                # 復元したファイル名とタイムスタンプをリストに追加
                selected_files.append(f"{readable_mtime}: {recovered_filename}")
                filelist_recover.append({
                    'mtime': mtime,
                    'recover_path': recovered_path,
                    'filename': filename,
                    'file_path': file_path
                })
            except ValueError as ve:
                status_messages.append(f"エラー: {ve}")

        if status_messages:
            status_recover.value = '\n'.join(status_messages)
        else:
            status_recover.value = '\n'.join(selected_files)
        status_recover.update()


    def datebox_change(e):
        date_picked.value = e.control.value
        date_picked.update()


    def timebox_change(e):
        time_picked.value = e.control.value
        time_picked.update()


    # リネーム実行ボタンのイベントハンドラ
    def btn_extract_rename(_):
        global dir_output
        status_messages =[]

        if is_set_site() and is_set_ICR():
            isStart = dict_ICR[selected_ICR] == 'START'
            for mtime, files in metadata_group.items():
                print(files)
                try:
                    if len(files) == 1:
                        # 単一ファイルの場合、リストの最初の要素の 'filename' キーを使用
                        #org_filename = files[0]['filename']
                        #org_file_path = os.path.join(dir_sounds, org_filename)
                        org_file_path = files[0]['file_path']
                        new_filename = get_renamed_sound(files[0],isStart)
                        new_file_path = os.path.join(dir_output, new_filename)
                        print(f"new_file_path:{new_file_path}")
                        os.rename(org_file_path, new_file_path)
                    else:
                        if not any(check_filename_format(f['filename']) for f in files):
                            # 拡張子を除いたファイル名を連結し、最後に拡張子を追加する
                            filename = '_'.join(f['filename'].rsplit('.', 1)[0] for f in files) + '.' + files[0]['filename'].split('.')[-1]
                            new_filename = get_renamed_sounds(files)
                            new_file_path = os.path.join(dir_output,new_filename)
                            merge_and_rename_audio_files(metadata_group,output_file=new_file_path)
                except ValueError as e:
                    status_messages.append(f"ファイル名変更中にエラーが発生しました：{e}")
        if not status_messages:
            status_rename_result.value =  "リネーム成功: " + '\n'.join(new_filename) 
        else:
            status_rename_result.value = '\n'.join(status_messages)
        status_rename_result.update()


    # ファイル名復元実行ボタンのイベントハンドラ
    def btn_extract_recover(_):
        global filelist_recover
        status_messages = []
        new_filename = []

        for file_info in filelist_recover:
            try:
                prev_file_path = file_info['file_path']
                # ソースファイルの存在を確認
                if not os.path.exists(prev_file_path):
                    raise ValueError(f"ファイルが存在しません: {prev_file_path}")

                mtime = file_info['mtime']
                recover_file_path = file_info['recover_path']
                # new_filenameをnew_pathから生成するコード
                new_filename.append(os.path.basename(recover_file_path))
                # prev_filenameをnew_filenameにリネームするコード
                os.rename(prev_file_path, recover_file_path)
                # mtimeをタイムスタンプに変換し、ファイルのmtimeを設定
                os.utime(recover_file_path, (mtime, mtime))
            except ValueError as e:
                status_messages.append(f"ファイル名の更新中にエラーが発生しました: {e}")

        if not status_messages:
            status_recover_result.value =  "復元成功: " + '\n'.join(new_filename) 
        else:
            status_recover_result.value = '\n'.join(status_messages)
        status_recover_result.update()


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
    dialogue_sounds_dir = ft.FilePicker(on_result=update_sounds_list_and_rename_list)
    dialogue_output_dir = ft.FilePicker(on_result=get_output_directory)
    dialogue_modify_mtime_file = ft.FilePicker(on_result=update_info_modify_mtime_files)
    dialogue_recover_filename = ft.FilePicker(on_result=update_info_recover_filename)

    page.overlay.append(dialogue_sounds_dir)
    page.overlay.append(dialogue_output_dir)
    page.overlay.append(dialogue_modify_mtime_file)
    page.overlay.append(dialogue_recover_filename)

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
    info_recover_filename = ft.TextField(
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
        selected_index=0,
        animation_duration=300,
        #tabs=[
            #ft.Tab(
            #    text="サイト名",
            #    icon=ft.icons.PLACE,
            #    content=ft.Container(
            #        padding=20,
            #        content=ft.Column([
            #            ft.Text(value="録音地を登録してください（暫定の入力です）。"),
            #            ft.TextField(label="サイト名(例FukuiEchizen)",
            #                        autofocus = True,
            #                        value=dict_site['サイト名'],
            #                        on_change=lambda e: update_dict_site('サイト名', e.control.value)
            #                        ),
            #            name_site
            #        ]),
            #    ),
            #),
            #ft.Tab(
            #    text="ICレコーダ",
            #    icon=ft.icons.KEYBOARD_VOICE,
            #    content=ft.Container(
            #        padding=20,
            #        content=ft.Column([
            #            ft.Dropdown(
            #                label = "IC Recorder",
            #                hint_text="録音したICレコーダを選択してください。用いるデータはタイムスタンプが開始(START)か終了(STOP)です。",
            #                options = dropdown_options,
            #                on_change=on_dropdown_change
            #            ),
            #            name_ICR
            #        ])
            #    ),
            #),
        tabs=[
            ft.Tab(
                text="リネーム",
                icon=ft.icons.DRIVE_FILE_MOVE_OUTLINE,
                content=ft.Container(
                    margin = 20,
                    content=ft.Column([
                        ft.Text(msg_rename),
                        ft.Row([
                            #info_selected_site,
                            ft.TextField(
                                icon=ft.icons.PLACE,
                                label = "サイト名入力:",
                                autofocus = True,
                                text_size=14,
                                hint_text="AwatabeEchizenFukui",
                                disabled= False,
                                value="",
                                on_change=changed_name_site,
                            ),
                            info_name_site,
                            ft.Dropdown(
                                icon=ft.icons.KEYBOARD_VOICE,
                                label = "レコーダ選択",
                                hint_text="レコーダにはタイムスタンプが開始(START)か終了(STOP)の2種があります。",
                                options = dropdown_options,
                                on_change=on_dropdown_change
                            ),
                            info_selected_ICR,
                            #name_ICR
                        ]),
                        btn_sounds_dir,
                        btn_output_dir,
                        sound_info,
                        renamed_info,
                        ft.Row([
                            ft.ElevatedButton(
                                "リネーム実行",
                                icon=ft.icons.EMOJI_EMOTIONS,
                                on_click=btn_extract_rename,  # 修正したイベントハンドラを使用
                            ),
                            status_rename_result
                        ]),
                    ])
                ),
            ),
            ft.Tab(
                text="ファイル名復元",
                icon=ft.icons.DRIVE_FILE_MOVE_RTL_OUTLINED,
                content=ft.Container(
                    margin=20,
                    content=ft.Column([
                        ft.Text("666形式のファイル名から元のファイル名に復元します。タイムスタンプが開始か終了かはICレコーダの選択で変わります。"),
                        ft.Dropdown(
                            label = "IC Recorder",
                            hint_text="録音したICレコーダを選択してください。用いるデータはタイムスタンプが開始(START)か終了(STOP)です。",
                            options = dropdown_options,
                            on_change=on_dropdown_change
                        ),
                        name_ICR,
                        ft.Row([
                            ft.ElevatedButton(
                                "ファイル選択",
                                icon=ft.icons.AUDIO_FILE_OUTLINED,
                                on_click=lambda _: dialogue_recover_filename.pick_files(
                                    allow_multiple=True
                                ),
                            ),
                        ]),
                        info_recover_filename,
                        status_recover,
                        ft.Row([
                            ft.ElevatedButton(
                                "復元実行",
                                icon=ft.icons.EMOJI_EMOTIONS,
                                on_click=btn_extract_recover,  # 修正したイベントハンドラを使用
                            ),
                            status_recover_result
                        ]),
                    ])
                ),
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
