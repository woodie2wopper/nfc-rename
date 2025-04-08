#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import subprocess
import traceback

# ログファイルの設定
home_dir = os.path.expanduser('~')
log_dir = os.path.join(home_dir, '.nfc')
log_file = os.path.join(log_dir, 'nfc-rename-debug.log')

# ログディレクトリが存在しない場合は作成
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# ログの設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename=log_file,
    filemode='w'  # 'a'ではなく'w'でログを上書き
)

# コンソールにもログを出力
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def check_environment():
    """環境変数やシステム情報を確認してログに記録"""
    try:
        logging.info("=== システム情報 ===")
        import platform
        logging.info(f"OS: {platform.system()} {platform.release()}")
        logging.info(f"Python: {sys.version}")
        
        # fletのバージョン確認
        try:
            import flet
            logging.info(f"Flet バージョン: {getattr(flet, '__version__', 'Unknown')}")
        except ImportError:
            logging.error("fletがインストールされていません")
        
        # 環境変数
        logging.info("=== 環境変数 ===")
        for var in ['PYTHONPATH', 'PATH', 'DISPLAY', 'HOME']:
            if var in os.environ:
                logging.info(f"{var}: {os.environ[var]}")
    except Exception as e:
        logging.error(f"環境情報の取得中にエラー: {e}")

def run_app_with_console():
    """アプリケーションをコンソール出力を取得しながら実行"""
    try:
        logging.info("アプリケーションを実行します")
        # アプリを直接実行
        result = subprocess.run(
            [sys.executable, "main.py"],
            capture_output=True,
            text=True,
            check=False
        )
        
        # 標準出力をログに記録
        if result.stdout:
            logging.info("=== 標準出力 ===")
            for line in result.stdout.splitlines():
                logging.info(f"STDOUT: {line}")
        
        # 標準エラー出力をログに記録
        if result.stderr:
            logging.error("=== 標準エラー出力 ===")
            for line in result.stderr.splitlines():
                logging.error(f"STDERR: {line}")
        
        # 終了コードを記録
        logging.info(f"アプリケーション終了コード: {result.returncode}")
        return result.returncode
    except Exception as e:
        logging.error(f"アプリケーション実行中にエラー: {e}")
        logging.error(traceback.format_exc())
        return 1

def check_log_file():
    """アプリケーションのログファイルを確認"""
    app_log_file = os.path.join(log_dir, 'nfc-rename.log')
    
    try:
        if os.path.exists(app_log_file):
            logging.info(f"=== アプリケーションログ ({app_log_file}) ===")
            with open(app_log_file, 'r') as f:
                # 最後の50行だけ表示
                lines = f.readlines()
                if len(lines) > 50:
                    logging.info(f"... {len(lines)-50}行省略 ...")
                for line in lines[-50:]:
                    logging.info(f"APP LOG: {line.strip()}")
        else:
            logging.warning(f"アプリケーションログファイルが見つかりません: {app_log_file}")
    except Exception as e:
        logging.error(f"ログファイル確認中にエラー: {e}")

if __name__ == "__main__":
    try:
        logging.info("=== デバッグ実行開始 ===")
        # 環境情報を確認
        check_environment()
        
        # アプリケーションを実行
        exit_code = run_app_with_console()
        
        # ログファイルを確認
        check_log_file()
        
        logging.info("=== デバッグ実行終了 ===")
        sys.exit(exit_code)
    except Exception as e:
        logging.error(f"デバッグ実行中に予期しないエラー: {e}")
        logging.error(traceback.format_exc())
        sys.exit(1) 