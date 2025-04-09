# -*- coding: utf-8 -*-
import flet as ft
import os
import shutil
import wave
import datetime
from datetime import timezone, timedelta
import re
import logging
import sys
import ffmpeg
import subprocess
import json
import platform
import math
import unicodedata

class StreamToLogger:
    """
    標準出力または標準エラーのメッセージをログファイルに書き込むためのクラス
    """
    def __init__(self, logger, log_level):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass


# ログファイルのパスを設定
home_dir = os.path.expanduser('~')
log_dir = os.path.join(home_dir, '.nfc')
log_file = os.path.join(log_dir, 'nfc-rename.log')

# ログディレクトリが存在しない場合は作成
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# ログの設定
logging.basicConfig(
    level=logging.INFO,  # INFOレベルでログを記録
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename=log_file,
    filemode='a'
)

# 標準出力と標準エラーをリダイレクト
sys.stdout = StreamToLogger(logging.getLogger('STDOUT'), logging.INFO)
sys.stderr = StreamToLogger(logging.getLogger('STDERR'), logging.ERROR)

# ログのテスト
logging.info('ログファイルスタート')
logging.debug('デバッグモードで実行中')

audio_extensions = ['.wav','.mp3']
#audio_extensions = ['.wav','.mp3']
# 録音サイトのメタデータを格納するグローバル変数
#dict_site = {
#    'サイト名': ''#,
#    #'県名': '',
#    #'市町村': '',
#    #'緯度': '',
#    #'経度': '',
#}
dict_ICR = {
    'dummy_start': 'START',
    'DM-750': 'START',
    'LS-7': 'START',
    'DR-05': 'STOP',
    'dummy_stop': 'STOP'
}

def get_os():
    """
    現在実行中のOSを判定する関数
    :return: OSの名前を文字列で返す
    """
    os_name = platform.system()
    return os_name


# グローバル変数定義
def set_ffmpeg_path():
    """
    OSに応じてffmpegのパスを設定する関数
    :return: ffmpegのパスを文字列で返す
    """
    os_name = get_os()
    # 実行ファイルのディレクトリを取得
    if getattr(sys, 'frozen', False):
        # PyInstallerでビルドされた場合
        application_path = os.path.dirname(sys.executable)
    else:
        # 通常のPython実行の場合
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    print("アプリケーションパス:", application_path)
    
    if os_name == 'Darwin':  # MacOSXの場合
        return os.path.join(application_path, 'vendors', 'for_Mac')
    elif os_name == 'Windows':  # Windowsの場合
        return os.path.join(application_path, 'vendors', 'for_Win')
    else:
        raise EnvironmentError('サポートされていないOSです。')

ffmpeg_path = set_ffmpeg_path()
ffmpeg_command = os.path.join(ffmpeg_path, "ffmpeg.exe")
ffprobe_command = os.path.join(ffmpeg_path, "ffprobe.exe")
ffplay_command = os.path.join(ffmpeg_path, "ffplay.exe")

# ffmpegのパスをログに記録
logging.info(f"ffmpeg_path: {ffmpeg_path}")
logging.info(f"ffmpeg_command: {ffmpeg_command}")
logging.info(f"ffmpeg_command exists: {os.path.exists(ffmpeg_command)}")

selected_ICR=''
name_site=''
dir_sounds="" # 音声ディレクトリ
dir_output="" # 変換後の出力ディレクトリ
list_rename={} # リネームするファイル辞書
metadata_group={} # 同一音源のメタデータ（filename、mtime、is666、file_pathとか）
filelist_recover=[] # recoverを変更するファイルリスト
filelist_remtime=[] # mtimeを変更するファイルリスト
pattern = r'(\d{6})_(\d{6})[_-](\d{6})_'

msg_rename="""\
フォルダ内のWAVファイル名を666+形式にリネームします。①〜⑤を順に設定してください。
【注意】
　- ICレコーダを変更したら、ディレクトリを選び直してください。
　- ⭕️はファイルスタンプが同じ同一音源でファイル名を降順にリネームします。
　- ✅はリネーム済みでリネームしません。
"""


def check_ICR_type(selected_ICR, is_group):
    """
    ICレコーダーの種類に応じて、単独ファイルかグループファイルかを判定する関数
    :param selected_ICR: 選択されたICレコーダーの型番
    :param is_group: グループファイルかどうかのブール値
    :return: 'DM-750'の場合、単独ファイルならTrue、グループファイルならFalseを返す
    """
    if selected_ICR == 'DM-750' :
        return not is_group
    if selected_ICR == "LS-7" :
        return not is_group
    else:
        # 他のICレコーダーの場合は、この関数では判定しない
        return None



def is_exist_dir_path(dir_path):
    # 指定されたパスが存在し、ディレクトリであるかを確認する関数
    return os.path.exists(dir_path) and os.path.isdir(dir_path)


def get_duration_mp3(mp3_path):
    """
    ffmpegを使用してMP3ファイルの長さを取得する関数
    :param mp3_path: MP3ファイルのパス
    :return: ファイルの長さ（秒）
    """
    try:
        # ffprobeコマンドを実行し、JSON形式でメタデータを取得
        result = subprocess.run(
            [ffprobe_command, "-v", "error", "-show_entries", "format=duration", "-of", "json", mp3_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        # 結果をJSONとして解析
        duration = json.loads(result.stdout)['format']['duration']
        return float(duration)
    except Exception as e:
        print(f"Error occurred while getting duration of {mp3_path}: {e}")
        return None


# waveを用いて長さを取得する
def get_duration_wav(wav_path):
    try:
        with wave.open(wav_path, 'r') as wav_file:
            duration = wav_file.getnframes() / wav_file.getframerate()
            return duration
    except:
        return None

# 切り捨てか、四捨五入かなど小数を整数化する関数を一括に定義しておく
def normalize(x):
    return int(x)


def convert_epoch_to_string(epoch_time):
    epoch_time = normalize(epoch_time)
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%Y-%m-%d %H:%M:%S')


def convert_epoch_to_66(epoch_time):
    epoch_time = normalize(epoch_time)
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%y%m%d_%H%M%S')


def convert_epoch_to_x6(epoch_time):
    epoch_time = normalize(epoch_time)
    return datetime.datetime.fromtimestamp(epoch_time).strftime('_%H%M%S')


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
    # "_"か"-"で区切られたファイル名を分割するコードを挿入
    parts = re.split(r'[_-]', filename)
    #    parts = filename.split('_')
    # 最初の4つの部分を削除する
    recovered_parts = parts[4:]
    # 残りの部分を"_"で結合して返す
    recovered_filename = '_'.join(recovered_parts)
    return recovered_filename

def split_filename(filename):
    # "_","-"で区切られたファイル名を分割する
    parts = re.split(r'[_-]', filename)
    #parts = filename.split('_')
    # 最初の要素をdate_str、２番目をstart_time,３番目をstop_timeに分ける
    if len(parts) >= 3:
        date_str = parts[0]
        start_time = parts[1]
        stop_time = parts[2]
        return date_str, start_time, stop_time

def get_start_stop_from_666(filename):
    # 666形式のファイル名から開始と終了のエポックタイムを抽出する正規表現
    global pattern
    match = re.search(pattern, filename)
    if match:
        date_str, start_time, stop_time = split_filename(filename)
        start_str = f"{date_str}_{start_time}"
        stop_str = f"{date_str}_{stop_time}"
        # 日付と時刻の文字列をdatetimeオブジェクトに変換
        start_dt = datetime.datetime.strptime(start_str, '%y%m%d_%H%M%S')
        stop_dt = datetime.datetime.strptime(stop_str, '%y%m%d_%H%M%S')
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
        is_start = dict_ICR[selected_ICR] == 'START'
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
    logging.debug('main関数が呼び出されました')
    page.title="nfc-rename"
    page.window_width=800
    page.window_height=1000
    page.scroll=True
    logging.debug('ページ設定完了')

    # --- client_storageからサイト名を読み込み ---
    global name_site
    cached_site_name = page.client_storage.get("cached_site_name")
    if cached_site_name:
        name_site = cached_site_name
        logging.info(f"キャッシュからサイト名を読み込みました: {name_site}")
    else:
        name_site = "" # キャッシュがない場合は空文字に初期化
    # -------------------------------------------

    # flet関連
    status_rename_result = ft.TextField(
        text_size=10,
        label="結果:",
        multiline=True,
        min_lines=1,
        read_only=True,
        max_lines=None,
        value=""
        )
    info_sound_dir = ft.Text(size=10)
    output_dir_path = ft.Text(size=10)
    name_ICR = ft.Text(size=10)

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
        label="変更前後のファイル名：",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value="",
    )

    info_split_result = ft.TextField(
        text_size=10,
        label="分割結果：",
        multiline=True,
        min_lines=4,
        read_only=True,
        max_lines=None,
        value="",
    )
    def init_renamed_info():
        renamed_info.value = ""
        renamed_info.update()

    def init_renamed_result():
        status_rename_result.value = ""
        status_rename_result.update()

    info_name_site = ft.Text(size=10, value=name_site) # 初期値を設定
    info_selected_ICR = ft.Text(size=10)

    # dict_ICRから動的に生成する。
    dropdown_options = [ft.dropdown.Option(key) for key, value in dict_ICR.items()]

    
    info_modified_mtime = ft.TextField(
        text_size=10,
        label="結果:",
        multiline=True,
        min_lines=1,
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

    status_recover_result = ft. TextField(
        text_size=10,
        label="結果",
        multiline=True,
        min_lines=1,
        read_only=True,
        max_lines=None,
        value="",
        )


    # --- サイト名入力フィールドの事前定義を削除 ---
    # site_name_field = ft.TextField(...)
    # ------------------------------------------

    def changed_name_site(e):
        global name_site
        name_site=e.control.value
        info_name_site.value = name_site
        info_name_site.update()
        # --- client_storageにサイト名を保存 ---
        page.client_storage.set("cached_site_name", name_site)
        logging.info(f"サイト名をキャッシュに保存しました: {name_site}")
        # ------------------------------------
        print(f'name_site:{name_site}')


    def on_dropdown_change(e):
        global selected_ICR  # selected_ICRをグローバル変数として宣言
        selected_ICR = e.control.value  # 選択されたOptionのvalue属性がキーになります
        print(f'select_ICR:{selected_ICR}')
        update_ICR_info()


    def get_sounds_list(directory):
        global audio_extensions
        # 対象の音声ファイルの拡張子
        # ディレクトリ内の全ファイルを取得
        all_files = os.listdir(directory)
        # 音声ファイルのみをフィルタリング
        audio_files = [file for file in all_files if os.path.splitext(file)[1].lower() in audio_extensions]
        # 音声データのリスト
        return audio_files

    def set_output_directory(e: ft.FilePickerResultEvent):
        global dir_output
        if e.path:
            dir_output = e.path
            output_dir_path.value = dir_output
        else:
            output_dir_path.value = "Cancelled!"
        output_dir_path.update()


    # 同一録音ファイルをマージせず、ファイル毎のmtimeの設定とファイル名変更する
    def set_each_mtime(metadata_in_same_groups, is_start):
        len_metadata = len(metadata_in_same_groups)
        # mtimeがstartかstopかで計算を変える
        if is_start:
            metadata_in_same_groups.sort(key=lambda x: x['filename'])
            for i in range(len_metadata):
                duration = metadata_in_same_groups[i]['duration']
                mtime = metadata_in_same_groups[i]['mtime']
                # 一番最初のファイルの開始時間はmtimeであるのでstop_epochに書いておく
                if i == 0: 
                    stop_epoch = mtime
                # start_epochは前のstop_epochである。
                start_epoch = stop_epoch
                print(f"{i}: {metadata_in_same_groups[i]['filename']}: start={convert_epoch_to_66(start_epoch)}: mtime={convert_epoch_to_66(mtime)}: duration={duration}")
                metadata_in_same_groups[i]['mtime'] = start_epoch
                # 次のために計算しておく
                stop_epoch = start_epoch + duration
        else:
            metadata_in_same_groups.sort(key=lambda x: x['filename'], reverse=True)
            for i in range(len_metadata):
                duration = metadata_in_same_groups[i]['duration']
                mtime = metadata_in_same_groups[i]['mtime']
                # 一番最初のファイルの開始時間はmtimeであるのでstop_epochに書いておく
                if i == 0: 
                    start_epoch = mtime
                # start_epochは前のstop_epochである。
                stop_epoch = start_epoch
                print(f"{i}: {metadata_in_same_groups[i]['filename']}: stop={convert_epoch_to_66(stop_epoch)}: mtime={convert_epoch_to_66(mtime)}: duration={duration}")
                metadata_in_same_groups[i]['mtime'] = stop_epoch
                # 次のために計算しておく
                start_epoch = stop_epoch - duration
        return metadata_in_same_groups


    def get_renamed_sound(metadata_sound, is_start):
        global name_site
        filename = metadata_sound['filename']
        mtime = metadata_sound['mtime']
        duration = metadata_sound['duration']
        start_epoch, stop_epoch = (mtime, mtime + duration) if is_start else (mtime - duration, mtime)
        new_filename = get_666(filename, start_epoch, stop_epoch, name_site)
        return new_filename

    # 同一録音ファイルをマージしたとしてそのファイル名を返す
    def get_renamed_sounds(metadata_in_same_groups, is_start):
        global name_site
        filename = metadata_in_same_groups[0]['filename']
        mtime = metadata_in_same_groups[0]['mtime']
        total_duration = sum(file['duration'] for file in metadata_in_same_groups)
        start_epoch, stop_epoch = (mtime, mtime + total_duration) if is_start else (mtime - total_duration, mtime)
        new_filename = get_666(filename, start_epoch, stop_epoch, name_site)
        return new_filename

    def update_rename_result(msg):
        status_rename_result.value += msg
        status_rename_result.update()


    def update_recover_result(msg):
        status_recover_result.value += msg
        status_recover_result.update()
        
    # ファイル名の変更に関する情報を更新する関数
    def update_rename_info(metadata_group):
        msg=[]
        is_start = None
        # metadata_groupをキー'mtime'の値の小さい順に並び替える
        metadata_group = dict(sorted(metadata_group.items(), key=lambda item: item[0]))
        if is_set_site() & is_set_ICR() :
            is_start = dict_ICR[selected_ICR] == 'START'
            for mtime, files in metadata_group.items():
                # ファイル名が既にフォーマットされている場合は処理をスキップ
                if check_filename_format(files[0]['filename']):
                    continue
                if len(files) == 1:
                    filename = files[0]['filename']
                    new_filename = get_renamed_sound(files[0], is_start)
                    msg.append(f"{filename} -> {new_filename}")
                else: # 同一録音の場合
                    if checkbox_merge.value: 
                        # 同一録音を一つにマージする
                        filename = '⭕️ ' + ' +\n⭕️ '.join(f['filename'] for f in files)
                        new_filename = get_renamed_sounds(files,is_start)
                        msg.append(f"{filename} -> {new_filename}")
                    else: 
                        # マージしない（個別に設定）
                        metadata_in_same_groups = set_each_mtime(files,is_start)
                        for file in metadata_in_same_groups:
                            filename = file['filename']
                            new_filename = get_renamed_sound(file, is_start)
                            msg.append(f"{filename}-> {new_filename}")
            # msgをソートして自分に入れ直すコード
            msg.sort()
        else:
            msg.append(f"Error: ICレコーダもしくはサイト名が設定されていません")
        renamed_info.value +=  '\n' + '\n'.join(msg)
        renamed_info.update()
    

    def update_ICR_info(e=None):
        #name_ICR.value = f'ICレコーダー[{selected_ICR}] タイムスタンプ：{dict_ICR[selected_ICR]}'
        #name_ICR.update()
        info_selected_ICR.value = f'{dict_ICR[selected_ICR]}'
        info_selected_ICR.update()

    def update_sounds_info(metadata_group):
        msg = []
        str_666 =""
        str_group = ""
        counter_group = 0
        # metadata_groupをキー'mtime'の値の小さい順に並び替える
        metadata_group = dict(sorted(metadata_group.items(), key=lambda item: item[0]))
        for mtime, files in metadata_group.items():
            decimal_duration = 0
            if len(files) == 1:
                str_group = "　    "
            else:
                counter_group +=1
                str_group = f"⭕-{counter_group}: "
            # 選択されたfiles[0]のfilename, mtime, durationを取得
            files.sort(key=lambda x: x['filename'])
            for file in files:
                filename = file['filename']
                mtime = file['mtime']
                duration = file['duration']
                str_666 = "️\n✅ " if check_filename_format(filename) else "　  "
                mtime_formatted = convert_epoch_to_string(mtime)
                duration_formatted = str(timedelta(seconds=duration))
                msg.append(f"{str_666}{str_group} {filename}: mtime: {mtime_formatted}, 長さ: {duration_formatted}")
                # 小数点以下のdurationの和
                decimal_duration += duration - int(duration)
            if len(files) > 1:
                msg.append(f"　　　　　(ファイル名と実際の長さに{decimal_duration:.3f}秒の差があります）")
        sound_info.value = '\n'.join(msg)
        sound_info.update()


    # 指定されたパスから音声ファイルのリストを取得し、情報欄を更新する
    def update_sounds_list_and_rename_list(e: ft.FilePickerResultEvent):
        global dir_sounds
        global metadata_group 
        list_sounds = []
        metadata_group= {}
        init_renamed_info()
        init_renamed_result()
        if e.path:
            dir_sounds = e.path
            info_sound_dir.value = dir_sounds
            list_sounds = get_sounds_list(dir_sounds)
            metadata_sounds = get_metadata_sounds(list_sounds,dir_sounds)
            metadata_group = grouping_sounds(metadata_sounds)
            update_sounds_info(metadata_group) 
            update_rename_info(metadata_group) 
        else:
            info_sound_dir.value = "Cancelled!"
        info_sound_dir.update()


    # ファイル名をfrom_filenameからto_filenameに変更する関数
    def rename(from_file_path, to_file_path):
        msg = []
        if to_file_path:
            try:
                #msg.append(f"rename実：{from_file_path} -> {to_file_path} ")
                shutil.move(from_file_path, to_file_path)# ファイルシステムを超えて移動を可能にする
            except OSError as e:
                msg.append(f"リネーム中にエラーが発生しました: {e}")
        print(f"rename実行：{from_file_path}:to:{to_file_path} ")
        return msg


    def remtime(file_path, mtime):
        msg = []
        if file_path:
            try:
                msg.append(f'{file_path}')
                os.utime(file_path, (mtime, mtime))
            except:
                msg.append("ERROR: mtimeが設定できませんでした。")
        print(f're-mtime実行：{file_path}:mtime:{mtime}')
        return msg


    def execute_rename(metadata_group, output_dir_path,is_start):
        msg = []
        renamed_files = []  # リネームしたファイルのパスを記録するリスト
        for mtime, file in metadata_group.items():
            org_file_path = file['file_path']
            new_filename = get_renamed_sound(file,is_start)
            new_file_path = os.path.join(output_dir_path, new_filename)
            update_rename_result(f'\n rename実行：{org_file_path} → {new_file_path}')
            msg.extend(rename(org_file_path, new_file_path))
            msg.extend(remtime(new_file_path,mtime))
            renamed_files.append(new_file_path)
        return msg, renamed_files


    def update_info_modify_mtime_files(e: ft.FilePickerResultEvent):
        global filelist_remtime
        filelist_remtime = []
        selected_files_mtime = []
        msg = []
        if e.files:
            for file in e.files:
                mtime = os.path.getmtime(file.path)
                # mtimeを人が読める形式に変換
                readable_mtime = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                filelist_remtime.append(file.path)
                selected_files_mtime.append(f"{readable_mtime}: {file.name}")
                msg.append(f"{readable_mtime}: {file.name}")
        else:
            msg.append('Cancelled')
        info_modify_files.value = '\n'.join(msg)
        info_modify_files.update()


    
    # 音声ファイルリストから、メタデータとしてファイル名、タイムスタンプとdurationを得る関数
    def get_metadata_sounds(list_sounds,directory):
        # 音声ファイルの属性を格納するリスト
        metadata_sounds = []
        msg = []
        for filename in list_sounds:
            is666 = check_filename_format(filename)
            file_path = os.path.join(directory, filename)
            # ファイルの最終変更時刻を取得
            mtime = os.path.getmtime(file_path)
            # ファイルサイズが0でないことを確認
            if os.path.getsize(file_path) == 0:
                duration = None # エラーをNoneで判定
                msg.append(f"スキップ: {filename} 空のファイル")
            else:
                # 拡張子に応じて適切な関数を使用してdurationを取得する
                if filename.lower().endswith('.wav'):
                    duration = get_duration_wav(file_path)
                elif filename.lower().endswith('.mp3'):
                    duration = get_duration_mp3(file_path)
                #print(f"duration={duration}")
                if duration is not None:
                    metadata_sounds.append({ 
                        'filename': filename, 
                        'mtime': mtime, 
                        'duration': duration, 
                        'file_path': file_path, 
                        'is666': is666})
                else:
                    msg.append(f"スキップ: {filename} durationが取得できませんでした")
        if msg:
            str = '\n'.join(msg)
            renamed_info.value += str
            print(f'metadata取得失敗:{str}')
        renamed_info.update()
        return metadata_sounds
        
    def update_info_recover_filename(e: ft.FilePickerResultEvent):
        global filelist_recover
        # ファイルが選択されるたびにリストは空にする
        filelist_recover = []
        filenames_recover = []
        # 選択したファイルのmtimeを得し、人が読める形式でmtime_of_selected_file.valueに設定
        selected_files = []
        if e.files:
            for file in e.files:
                filenames_recover.append(file.path)
                # ファイルのmtimeを取得
                mtime = os.path.getmtime(file.path)
                # mtimeを人が読める形式に変換
                readable_mtime = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S.%f')
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
            try:
                # 666形式のファイル名かどうかをチェックする正規表現パターン
                if re.match(pattern, filename):
                    recovered_filename = recover_filename(filename)
                    recovered_path = os.path.join(os.path.dirname(file_path), recovered_filename)
                else:
                    raise ValueError("ファイル名が666形式ではありません。")

                if not is_set_ICR():
                    raise ValueError( "ICレコーダが選択されてません。")

                # ファイル名からstart_epochとstop_epochを取得
                start_epoch, stop_epoch = get_start_stop_from_666(filename)
                # dict_ICRの値に基づいてmtimeをstart_epochまたはstop_epochに設定
                if dict_ICR[selected_ICR] == 'START':
                    mtime = start_epoch
                elif dict_ICR[selected_ICR] == 'STOP':
                    mtime = stop_epoch
                else:
                    raise ValueError("ICレコーダが選択されてません")

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
            status_recover.value = f'recover file name:\n' + '\n'.join(selected_files)
        status_recover.update()

    def update_info_split_files(e: ft.FilePickerResultEvent):
        global filelist_split
        # ファイル選択時にinfo_split_filesとfilelist_splitをクリア
        info_split_files.value = ""
        info_split_files.update()
        filelist_split = []

        selected_files = []
        if e.files:
            for file in e.files:
                filename = os.path.basename(file.path)
                if not check_filename_format(filename):
                    info_split_files.value = f"× {filename}は666形式ではありません"
                    info_split_files.update()
                    return
                selected_files.append(file.path)
        
        # 更新されたファイルリストをグローバル変数に保存
        filelist_split = selected_files
        # 選択されたファイルをinfo_split_filesに表示
        info_split_files.value = '\n'.join(selected_files)
        info_split_files.update()


    def datebox_change(e):
        date_picked.value = e.control.value
        date_picked.update()


    def timebox_change(e):
        time_picked.value = e.control.value
        time_picked.update()


    # リネーム実行ボタン：ICレコーダ毎にファイル名を変える
    def btn_rename(_):
        global dir_output
        msg = []
        renamed_files = []  # リネームしたファイルのパスを記録するリスト

        if not is_exist_dir_path(dir_sounds):
            msg.append(f"音声フォルダが選択されていません")
        elif not metadata_group:
            msg.append(f"音声ファイルがありません")
        elif not is_exist_dir_path(dir_output):
            msg.append(f"出力フォルダが選択されていません")
        elif not is_set_site():
            msg.append(f"サイト名が設定されていません")
        elif not is_set_ICR():
            msg.append(f"ICレコーダーが選択されていません")
        else:
            is_start = dict_ICR[selected_ICR] == 'START'
            # filesにはmetadataが入っている
            for mtime, files in metadata_group.items():
                try:
                    if not check_filename_format(files[0]['filename']):
                        if len(files) == 1: # 単一ファイルの場合
                            org_file_path = files[0]['file_path']
                            new_filename = get_renamed_sound(files[0],is_start)
                            new_file_path = os.path.join(dir_output, new_filename)
                            update_rename_result(f'\n rename実行：{org_file_path} → {new_file_path}')
                            try:
                                # リネーム処理を実行
                                result = rename(from_file_path=org_file_path, to_file_path=new_file_path)
                                
                                # リネーム成功したらリストに追加
                                if os.path.exists(new_file_path):
                                    renamed_files.append(new_file_path)
                                    logging.info(f"renamed_files に追加しました: {new_file_path}")
                                
                                # 返り値がリストの場合、文字列のリストに変換
                                if isinstance(result, list):
                                    for item in result:
                                        if item:  # 空でない場合のみ追加
                                            msg.append(str(item))
                                else:
                                    msg.append(str(result))
                            except Exception as e:
                                logging.error(f"リネーム中にエラーが発生しました: {str(e)}")
                                msg.append(f"エラー: {str(e)}")
                            
                            # 同一録音のマージ機能は、無効化して開発終了とする
                            #if cb_merge_WAV:
                            #    msg.extend(merge_and_rename_audio_files(metadata_group, output_file=new_file_path))
                        else: # 同一録音（グループファイル）の場合
                            if not checkbox_merge.value: # マージのチェックボックスしない（個別に設定）
                                print(f'ICR={selected_ICR},Group=True,is_start={is_start}')
                                # ここで newed_metadata を辞書に変換する必要がある
                                newed_metadata = set_each_mtime(metadata_in_same_groups=files,is_start=is_start)
                                newed_metadata_dict = {file['mtime']: file for file in newed_metadata}
                                result = execute_rename(newed_metadata_dict, output_dir_path=dir_output, is_start=is_start)
                                # 返り値がリストの場合、文字列のリストに変換
                                if isinstance(result, list):
                                    for item in result:
                                        if item:  # 空でない場合のみ追加
                                            msg.append(str(item))
                                else:
                                    msg.append(str(result))
                            else: # 同一録音を一つにマージする
                                merge_and_rename_audio_files(metadata_group, output_file=new_file_path)
                        
                        # リストの内容を文字列に変換（デバッグ用）
                        debug_msg = []
                        for item in msg:
                            debug_msg.append(str(item))
                        debug_str = '\n'.join(debug_msg)
                        print(f'btn_rename:{debug_str}')
                except ValueError as e:
                    msg.append(f"ファイル名変更中にエラーが発生しました：{e}")
        
        # リネーム処理完了後に文字コード検証
        if renamed_files:
            logging.info(f"--- ファイル名文字コード検証の開始 --- 検証対象: {len(renamed_files)}件")
            for rf in renamed_files:
                logging.debug(f"検証対象ファイル: {rf}")
            try:
                # 内部で文字コード検証を行う
                results = []
                issues = []
                
                for file_path in renamed_files:
                    if os.path.exists(file_path):
                        logging.debug(f"検証中: {file_path}")
                        try:
                            # 以下はvalidate_filename_encodingの処理を直接実装
                            filename = os.path.basename(file_path)
                            
                            # 1. NFC正規化チェック
                            normalized = unicodedata.normalize('NFC', filename)
                            is_nfc = (normalized == filename)
                            
                            # 2. UTF-8としてエンコード・デコード可能か確認
                            try:
                                encoded = filename.encode('utf-8')
                                decoded = encoded.decode('utf-8')
                                utf8_compatible = (decoded == filename)
                            except UnicodeError:
                                utf8_compatible = False
                            
                            # 3. OS固有の問題チェック
                            os_compatible = True
                            if platform.system() == 'Windows':
                                # Windowsの禁止文字チェック
                                if re.search(r'[\\/:*?"<>|]', filename):
                                    os_compatible = False
                            elif platform.system() in ['Darwin', 'Linux']:
                                # macOS/Linuxでの禁止文字チェック
                                if '/' in filename:
                                    os_compatible = False
                            
                            result = {
                                'is_nfc': is_nfc,
                                'utf8_compatible': utf8_compatible,
                                'os_compatible': os_compatible,
                                'filename': filename,
                                'path': file_path
                            }
                            
                            results.append(result)
                            
                            # 問題があれば記録
                            if not (result['is_nfc'] and result['utf8_compatible'] and result['os_compatible']):
                                issue = f"警告: {result['filename']} - "
                                if not result['is_nfc']:
                                    issue += "Unicode NFC形式でない "
                                if not result['utf8_compatible']:
                                    issue += "UTF-8互換でない "
                                if not result['os_compatible']:
                                    issue += f"{platform.system()}で使用できない文字を含む "
                                issues.append(issue)
                                logging.warning(f"問題検出: {issue}")
                            else:
                                logging.debug(f"問題なし: {file_path}")
                        except Exception as e:
                            logging.error(f"検証中の個別エラー: {str(e)}")
                    else:
                        logging.warning(f"ファイルが存在しません: {file_path}")
                
                if issues:
                    for issue in issues:
                        logging.warning(issue)
                    logging.info(f"{len(issues)}件の問題を検出しました")
                else:
                    logging.info("すべてのファイル名はUTF-8+Unicode NFC形式で問題ありません")
            except Exception as e:
                logging.error(f"文字コード検証中にエラーが発生しました: {str(e)}")
                import traceback
                logging.error(traceback.format_exc())
            logging.info("--- ファイル名文字コード検証の終了 ---")
        
        # msgリストの各要素が確実に文字列であることを確認
        str_msg = []
        for item in msg:
            if item is not None:
                str_msg.append(str(item))
            
        status_rename_result.value += "\nリネーム終了\n" + '\n'.join(str_msg)
        status_rename_result.update()


    # ファイル名復元実行ボタンのイベントハンドラ
    def btn_recover(_):
        global filelist_recover
        msg = []
        new_filename = []
        for file_info in filelist_recover:
            try:
                prev_file_path = file_info['file_path']
                if not os.path.exists(prev_file_path):
                    raise ValueError(f"ファイルが存在しません: {prev_file_path}")
                mtime = file_info['mtime']
                recover_file_path = file_info['recover_path']
                new_filename.append(os.path.basename(recover_file_path))
                update_recover_result(f'\n recover実行：{prev_file_path} → {recover_file_path}')
                msg.extend(rename(prev_file_path, recover_file_path))
                msg.extend(remtime(recover_file_path, mtime))
            except ValueError as e:
                msg.append(f"ファイル名の更新中にエラーが発生しました: {e}")
        status_recover_result.value += '\n復元終了\n' + '\n'.join(msg)
        status_recover_result.update()


    def change_mtime_for_selected_files():
        global filelist_remtime
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

        datetime_str = f"{date_picked.value} {time_picked.value}"
        try:
            # datetime_strのフォーマットを判定し、対応するフォーマットで日時をパースしてエポック秒に変換するコード
            try:
                # "%Y%m%d %H%M%S"のフォーマットでパースを試みる
                datetime_obj = datetime.datetime.strptime(datetime_str, "%y%m%d %H%M%S")
            except ValueError:
                # 失敗した場合は"%Y-%m-%d %H:%M:%S"のフォーマットでパースを試みる
                datetime_obj = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            # タイムゾーンを設定
            datetime_obj = datetime_obj.replace(tzinfo=tz_info)
            # エポック秒に変換
            epoch_seconds = int(datetime_obj.timestamp())
        except ValueError as e:
            info_modified_mtime.value = f"日付または時刻の形式が正しくありません: {e}"
            info_modified_mtime.update()
            return

        # 選択されたファイルのmtimeを変更
        msg = []
        for file_path in filelist_remtime:
            if file_path:  # 空の行を無視
                try:
                    datetime_from_epoch = datetime.datetime.fromtimestamp(epoch_seconds, tz_info)
                    msg.extend(remtime(file_path,datetime_from_epoch.timestamp()))
                    file_name = os.path.basename(file_path)
                    mtime_str = datetime_from_epoch.strftime("%Y-%m-%d %H:%M:%S")
                    msg.append(f"{file_name} のmtimeを{mtime_str}に更新しました。")
                except FileNotFoundError:
                    msg.append(f"{file_path} が見つかりません。")
                except Exception as e:
                    msg.append(f"エラーが発生しました: {e}")
        info_modified_mtime.value = '\n'.join(msg)
        info_modified_mtime.update()


    def split_audio_files():
        """音声ファイルを1時間ごとに分割する"""
        msg = []
        try:
            # 選択されたファイルを取得
            if not dialogue_split_audio_file.result or not dialogue_split_audio_file.result.files:
                error_msg = "分割するファイルが選択されていません"
                logging.error(error_msg)
                info_split_result.value = error_msg
                info_split_result.update()
                return
            
            # 処理開始メッセージ
            start_msg = "音声ファイルの分割を開始します..."
            logging.info(start_msg)
            info_split_result.value = start_msg
            info_split_result.update()
            
            # 選択されたファイルのパスを取得
            selected_files = [file.path for file in dialogue_split_audio_file.result.files]
            total_files = len(selected_files)
            
            for file_index, file_path in enumerate(selected_files, 1):
                try:
                    if not os.path.exists(file_path):
                        error_msg = f"ファイルが見つかりません: {file_path}"
                        logging.error(error_msg)
                        msg.append(error_msg)
                        continue
                    
                    # ファイル名から開始時刻と終了時刻を取得
                    filename = os.path.basename(file_path)
                    logging.info(f'ファイル処理開始: {filename} ({file_index}/{total_files})')
                    info_split_result.value = f"ファイル処理中: {filename} ({file_index}/{total_files})"
                    info_split_result.update()
                    
                    start_epoch, stop_epoch = get_start_stop_from_666(filename)
                    
                    # 開始時刻と終了時刻をdatetimeオブジェクトに変換
                    start_dt = datetime.datetime.fromtimestamp(start_epoch)
                    end_dt = datetime.datetime.fromtimestamp(stop_epoch)
                    
                    # 総分割数を計算
                    total_duration = (end_dt - start_dt).total_seconds()
                    total_segments = math.ceil(total_duration / 3600)
                    
                    # 1時間ごとの区切り時刻を生成
                    current_time = start_dt
                    segment_count = 0
                    while current_time < end_dt:
                        try:
                            # 次の区切り時刻を計算（1時間後、または終了時刻の早い方）
                            next_time = min(current_time + datetime.timedelta(hours=1), end_dt)
                            segment_count += 1
                            
                            # 進捗メッセージを表示
                            progress_msg = f"ファイル {filename} ({file_index}/{total_files})\nセグメント {segment_count}/{total_segments} を処理中..."
                            info_split_result.value = progress_msg
                            info_split_result.update()
                            
                            # 出力ファイル名を生成（元のファイル名の情報を保持）
                            start_time_str = current_time.strftime('%y%m%d_%H%M%S')
                            end_time_str = next_time.strftime('%H%M%S')
                            # 元のファイル名からサイト名を抽出
                            original_filename = os.path.basename(file_path)
                            site_name = original_filename.split('_')[-2] if len(original_filename.split('_')) >= 2 else ""
                            output_filename = f"{start_time_str}_{end_time_str}_{site_name}.WAV"
                            output_path = os.path.join(os.path.dirname(file_path), output_filename)
                            
                            # 分割の開始オフセットと継続時間を計算
                            start_offset = (current_time - start_dt).total_seconds()
                            duration = (next_time - current_time).total_seconds()
                            
                            # ffmpegコマンドを構築
                            cmd = [
                                ffmpeg_command,
                                '-i', file_path,
                                '-ss', str(start_offset),
                                '-t', str(duration),
                                '-acodec', 'copy',
                                output_path
                            ]
                            
                            # ffmpegコマンドの存在を再確認
                            if not os.path.exists(ffmpeg_command):
                                error_msg = f"ffmpegコマンドが見つかりません: {ffmpeg_command}"
                                logging.error(error_msg)
                                msg.append(error_msg)
                                break
                            
                            # ffmpegを実行
                            logging.debug(f'ffmpegコマンド実行: {" ".join(cmd)}')
                            try:
                                if platform.system() == 'Windows':
                                    # Windowsの場合、CREATE_NO_WINDOWフラグを使用
                                    process = subprocess.Popen(
                                        cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        creationflags=subprocess.CREATE_NO_WINDOW,
                                        encoding='utf-8',
                                        errors='replace'
                                    )
                                else:
                                    process = subprocess.Popen(
                                        cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        encoding='utf-8',
                                        errors='replace'
                                    )
                                
                                # プロセスの完了を待つ（タイムアウトを5分に設定）
                                try:
                                    stdout, stderr = process.communicate(timeout=300)  # 5分のタイムアウト
                                except subprocess.TimeoutExpired:
                                    process.kill()  # プロセスを強制終了
                                    error_msg = f"分割処理がタイムアウトしました: {output_filename}"
                                    logging.error(error_msg)
                                    msg.append(error_msg)
                                    info_split_result.value = f"{progress_msg}\n{error_msg}"
                                    info_split_result.update()
                                    return
                                
                                # コマンドの実行結果をログに記録
                                logging.debug(f'ffmpegコマンドの標準出力: {stdout}')
                                if stderr:
                                    logging.debug(f'ffmpegコマンドの標準エラー出力: {stderr}')
                                
                                if process.returncode == 0:
                                    success_msg = f"分割成功: {output_filename}"
                                    logging.info(success_msg)
                                    msg.append(success_msg)
                                    info_split_result.value = f"{progress_msg}\n{success_msg}"
                                    info_split_result.update()
                                else:
                                    error_msg = f"分割失敗: {output_filename}\nエラー: {stderr}"
                                    logging.error(error_msg)
                                    msg.append(error_msg)
                                    info_split_result.value = f"{progress_msg}\n{error_msg}"
                                    info_split_result.update()
                            except Exception as e:
                                error_msg = f"予期せぬエラーが発生しました: {str(e)}"
                                logging.error(error_msg)
                                msg.append(error_msg)
                                info_split_result.value = f"{progress_msg}\n{error_msg}"
                                info_split_result.update()
                            
                            # 次の区切り時刻に進む
                            current_time = next_time
                        except Exception as e:
                            error_msg = f"分割処理中にエラーが発生しました: {str(e)}"
                            logging.error(error_msg)
                            msg.append(error_msg)
                            info_split_result.value = f"{progress_msg}\n{error_msg}"
                            info_split_result.update()
                            break
                    
                    # ファイル処理完了メッセージ
                    complete_msg = f"ファイル {filename} ({file_index}/{total_files}) の処理が完了しました"
                    logging.info(complete_msg)
                    info_split_result.value = complete_msg
                    info_split_result.update()
                
                except Exception as e:
                    error_msg = f"ファイル {filename} の処理中にエラーが発生しました: {str(e)}"
                    logging.error(error_msg)
                    msg.append(error_msg)
                    info_split_result.value = error_msg
                    info_split_result.update()
            
            # 最終結果を表示
            final_msg = "処理が完了しました\n" + '\n'.join(msg)
            info_split_result.value = final_msg
            info_split_result.update()
            
        except Exception as e:
            error_msg = f"予期せぬエラーが発生しました: {str(e)}"
            logging.error(error_msg)
            info_split_result.value = error_msg
            info_split_result.update()

    # ダイアローグの追加                
    dialogue_sounds_dir = ft.FilePicker(on_result=update_sounds_list_and_rename_list)
    dialogue_output_dir = ft.FilePicker(on_result=set_output_directory)
    dialogue_modify_mtime_file = ft.FilePicker(on_result=update_info_modify_mtime_files)
    dialogue_recover_filename = ft.FilePicker(on_result=update_info_recover_filename)
    dialogue_split_audio_file = ft.FilePicker(on_result=update_info_split_files)

    page.overlay.append(dialogue_sounds_dir)
    page.overlay.append(dialogue_output_dir)
    page.overlay.append(dialogue_modify_mtime_file)
    page.overlay.append(dialogue_recover_filename)
    page.overlay.append(dialogue_split_audio_file)

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
    info_split_files = ft.TextField(
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
    checkbox_merge=ft.Checkbox(
        label="同一録音のマージ（選択不可）",
        value=False,
        disabled=True,
        #on_change=on_merge_checkbox_change
    )

    # UIの定義
    t = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(
                text="リネーム",
                icon=ft.icons.DRIVE_FILE_MOVE_OUTLINE,
                content=ft.Container(
                    margin = 20,
                    content=ft.Column([
                        ft.Text(msg_rename),
                        ft.Row([
                            # --- TextFieldを直接定義し、初期値を設定 ---
                            ft.TextField(
                                icon=ft.icons.PLACE,
                                label = "①サイト名（県名+市名）",
                                autofocus = True,
                                text_size=14,
                                hint_text="福井県越前市",
                                disabled= False,
                                value=name_site, # キャッシュ or 空文字で初期化
                                on_change=changed_name_site,
                            ),
                            # -------------------------------------
                            info_name_site,
                        ]),
                        ft.Row([
                            ft.Dropdown(
                                icon=ft.icons.KEYBOARD_VOICE,
                                label = "②レコーダ",
                                hint_text="レコーダにはタイムスタンプが開始(START)か終了(STOP)の2種があります。",
                                options = dropdown_options,
                                on_change=on_dropdown_change
                            ),
                            info_selected_ICR,
                        ]),
                        ft.Row([
                            ft.ElevatedButton(
                                "③音声フォルダ",
                                icon=ft.icons.FOLDER,
                                on_click=lambda _: dialogue_sounds_dir.get_directory_path(),
                            ),
                            info_sound_dir,
                        ]),
                        ft.Row([
                            ft.ElevatedButton(
                                "④出力フォルダ",
                                icon=ft.icons.FOLDER,
                                on_click=lambda _: dialogue_output_dir.get_directory_path(),
                            ),
                            output_dir_path,
                        ]),
                        sound_info,
                        renamed_info,
                        checkbox_merge,
                        ft.Row([
                            ft.ElevatedButton(
                                "⑤リネーム実行",
                                icon=ft.icons.EMOJI_EMOTIONS,
                                on_click=btn_rename,  # 修正したイベントハンドラを使用
                            ),
                        ]),
                        status_rename_result
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
                                "復元",
                                icon=ft.icons.EMOJI_EMOTIONS,
                                on_click=btn_recover,  # 修正したイベントハンドラを使用
                            ),
                        ]),
                        status_recover_result
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
                                hint_text="240101",
                                icon=ft.icons.CALENDAR_MONTH_OUTLINED,
                                multiline=False,
                                on_change=datebox_change,
                            ),
                            date_picked,
                        ]),
                        ft.Row([
                            ft.TextField(
                                label="時刻入力",
                                hint_text="012345",
                                icon=ft.icons.ACCESS_TIME,
                                multiline=False,
                                on_change=timebox_change,
                            ),
                            time_picked
                        ]),
                        ft.Row([
                            ft.ElevatedButton(
                                "タイムスタンプ変更",
                                icon=ft.icons.EMOJI_EMOTIONS,
                                on_click=lambda _: change_mtime_for_selected_files()
                            ),
                        ]),
                        info_modified_mtime
                    ])
                ),
            ),
            ft.Tab(
                text="音声分割",
                icon=ft.icons.CONTENT_CUT_ROUNDED,
                content=ft.Container(
                    margin=20,
                    content=ft.Column([
                        ft.Text("音声ファイルを1時間ごとに分割します。"),
                        ft.Text("分割は0分0秒ちょうどで行います。"),
                        ft.Row([
                            ft.ElevatedButton(
                                "ファイル選択",
                                icon=ft.icons.AUDIO_FILE_OUTLINED,
                                on_click=lambda _: dialogue_split_audio_file.pick_files(
                                    allow_multiple=True
                                ),
                            ),
                        ]),
                        info_split_files,
                        ft.Row([
                            ft.ElevatedButton(
                                "1時間ごとに分割",
                                icon=ft.icons.CONTENT_CUT_ROUNDED,
                                on_click=lambda _: split_audio_files()
                            ),
                        ]),
                        info_split_result
                    ])
                ),
            ),
            ft.Tab(
                text="about",
                icon=ft.icons.INFO_OUTLINE_ROUNDED,
                content=ft.Container(
                    ft.Column([
                        ft.Text(
                            "nfc-rename",
                            size=20,
                            ),
                        ft.Text(
                            "version:0.9 (2025-04-07)",
                            size=12,
                            ),
                        ft.Text(
                            "author:Hideki Osaka",
                            size=12,
                            ),
                        ft.Text("【機能】"),
                        ft.Text(" - リネーム： wavデータのファイル名を'666形式+場所の名前'でリネームします。"),
                        ft.Text(" - ファイル名復元： 666形式のファイル名をオリジナルのファイル名に復元します"),
                        ft.Text(" - タイムスタンプ変更： ファイルのタイムスタンプ（最終変更日時:mtime)を変更します"),
                        ft.Text(" - 音声分割： 666形式のファイルを1時間ごとに分割します"),
                        ft.Text(" - サイト名キャッシュ: 入力したサイト名は次回起動時に自動で読み込まれます。"),
                        ft.Text("【ヒント】"),
                        ft.Text(" - 同一録音の再設定は、オリジナルファイル名を複数選択し、同じmtimeを設定してください。これは同じmtimeを持ち、連続するファイル名の場合に有効です。"),
                        ft.Text(" - 作成日(Birthday)は変更しません。"),
                        ft.Text(" - Olympus: DM-750とLS-7は2GBを超えるファイルが自動分割されます。このとき生成されたファイルはすべて同じタイムスタンプ（録音開始時刻のmtime）を持ちます。そのため、同じ録音ファイルを同一グループとしファイル名の若い順にファイル名を生成します。なおDR-05(TASCAM）も自動分割されますが、タイムスタンプは録音終了時刻が設定されています。"),
                        ft.Markdown("詳細はこちら: [GitHub Repository](https://github.com/woodie2wopper/nfc-rename)"),
                    ]),
                ),
            )
        ],
        expand=1,
    )

    page.add(t)

    def on_close(e):
        logging.info('アプリケーションが正常に終了しました。')
        logging.debug('on_close イベントハンドラが呼び出されました')

    page.on_close = on_close
    logging.debug('ページの初期化が完了しました')


try:
    logging.debug('アプリケーション起動開始')
    # AppViewの利用可能な値を確認
    logging.debug(f"利用可能なAppView: {[member.name for member in ft.AppView]}")
    
    # アプリケーション実行環境の情報をログに記録
    logging.info(f"OS: {platform.system()} {platform.release()}")
    logging.info(f"Python: {sys.version}")
    logging.info(f"環境変数PATH: {os.environ.get('PATH', '未設定')}")
    
    # デバッグ情報を記録
    logging.debug(f"現在時刻: {datetime.datetime.now()}")
    logging.debug(f"ログファイル: {log_file}")
    
    # Fletアプリケーションの起動
    ft.app(
        target=main,
        assets_dir="assets",
        view=ft.AppView.FLET_APP  # FLET_APPはネイティブアプリケーションとして実行
    )
    logging.debug('アプリケーション正常終了')
except Exception as e:
    logging.error(f'アプリケーション実行中にエラーが発生: {str(e)}')
    logging.exception("詳細なスタックトレース:")
    
    # エラー情報をファイルに保存（デバッグ用）
    try:
        import traceback
        error_log_path = os.path.join(os.path.expanduser('~'), '.nfc', 'error.log')
        os.makedirs(os.path.dirname(error_log_path), exist_ok=True)
        with open(error_log_path, 'w', encoding='utf-8') as f:
            f.write(f"エラー発生時刻: {datetime.datetime.now()}\n")
            f.write(f"エラー内容: {str(e)}\n")
            f.write(f"OS: {platform.system()} {platform.release()}\n")
            f.write(f"Python: {sys.version}\n")
            f.write(traceback.format_exc())
    except Exception as write_error:
        logging.error(f"エラーログ保存中にエラー発生: {write_error}")
    
    # macOS環境ではダイアログを表示
    if platform.system() == "Darwin":
        try:
            subprocess.run(["osascript", "-e", f'display dialog "アプリケーションエラー: {str(e)}" buttons {{"OK"}} default button "OK" with icon stop'])
        except Exception:
            pass

def fix_macos_bundle():
    # 既存のコード...
    
    # コード署名の再適用
    subprocess.run([
        "codesign", "--force", "--deep", "--sign", "-", 
        "--entitlements", "entitlements.plist",
        app_bundle
    ], check=True)
    print("アプリケーションの署名を再適用しました")

def normalize_unicode(text, form='NFC'):
    """
    Unicodeテキストを指定された正規化形式に変換する
    - NFC: 正準等価性による合成（推奨）
    - NFD: 正準等価性による分解
    - NFKC: 互換等価性による合成
    - NFKD: 互換等価性による分解
    """
    if text is None:
        return None
    return unicodedata.normalize(form, text)

def safe_filename(filename):
    """
    ファイル名を安全に処理し、NFCに正規化する
    """
    # Unicode正規化（NFC形式）
    normalized = normalize_unicode(filename, 'NFC')
    
    # OSごとの禁止文字を置換
    if platform.system() == 'Windows':
        # Windowsでの禁止文字を置換
        normalized = re.sub(r'[\\/:*?"<>|]', '_', normalized)
    elif platform.system() == 'Darwin' or platform.system() == 'Linux':
        # macOS/Linuxでの禁止文字を置換
        normalized = normalized.replace('/', '_')
    
    return normalized

def safe_path(path):
    """
    OSに依存しないパス処理を行う
    """
    # パス区切り文字を正規化
    normalized_path = os.path.normpath(path)
    
    # パスの各部分を取得
    parts = []
    head, tail = os.path.split(normalized_path)
    while tail:
        parts.append(safe_filename(tail))
        head, tail = os.path.split(head)
    if head:
        parts.append(head)
    
    # 逆順にして結合
    parts.reverse()
    return os.path.join(*parts)

def read_file(file_path):
    """
    ファイルをUTF-8で読み込む
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(file_path, content):
    """
    ファイルをUTF-8で書き込む
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def run_command(cmd, input_data=None):
    """
    コマンドを実行し、入出力をUTF-8で処理する
    """
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE if input_data else None,
        universal_newlines=True,  # テキストモード
        encoding='utf-8'  # UTF-8を明示指定
    )
    
    stdout, stderr = process.communicate(input=input_data)
    return process.returncode, stdout, stderr

def validate_filename_encoding(file_path):
    """
    ファイル名のエンコーディングと正規化を検証する関数
    """
    filename = os.path.basename(file_path)
    dirname = os.path.dirname(file_path)
    
    # 1. NFC正規化チェック
    normalized = unicodedata.normalize('NFC', filename)
    is_nfc = (normalized == filename)
    
    # 2. UTF-8としてエンコード・デコード可能か確認
    try:
        encoded = filename.encode('utf-8')
        decoded = encoded.decode('utf-8')
        utf8_compatible = (decoded == filename)
    except UnicodeError:
        utf8_compatible = False
    
    # 3. OS固有の問題チェック
    os_compatible = True
    if platform.system() == 'Windows':
        # Windowsの禁止文字チェック
        if re.search(r'[\\/:*?"<>|]', filename):
            os_compatible = False
    elif platform.system() in ['Darwin', 'Linux']:
        # macOS/Linuxでの禁止文字チェック
        if '/' in filename:
            os_compatible = False
    
    return {
        'is_nfc': is_nfc,
        'utf8_compatible': utf8_compatible,
        'os_compatible': os_compatible,
        'filename': filename,
        'path': file_path
    }

def check_renamed_files(renamed_files):
    """
    リネームされたファイル群の文字コードを検証する
    """
    logging.info(f"check_renamed_files: {len(renamed_files)}件のファイルを検証します")
    results = []
    issues = []
    
    for file_path in renamed_files:
        if os.path.exists(file_path):
            logging.debug(f"check_renamed_files: 検証中: {file_path}")
            result = validate_filename_encoding(file_path)
            results.append(result)
            
            # 問題があれば記録
            if not (result['is_nfc'] and result['utf8_compatible'] and result['os_compatible']):
                issue = f"警告: {result['filename']} - "
                if not result['is_nfc']:
                    issue += "Unicode NFC形式でない "
                if not result['utf8_compatible']:
                    issue += "UTF-8互換でない "
                if not result['os_compatible']:
                    issue += f"{platform.system()}で使用できない文字を含む "
                issues.append(issue)
                logging.warning(f"check_renamed_files: 問題検出: {issue}")
            else:
                logging.debug(f"check_renamed_files: 問題なし: {file_path}")
        else:
            logging.warning(f"check_renamed_files: ファイルが存在しません: {file_path}")
    
    if issues:
        logging.info(f"check_renamed_files: {len(issues)}件の問題を検出しました")
    else:
        logging.info("check_renamed_files: すべてのファイル名に問題はありません")
    
    return results, issues
