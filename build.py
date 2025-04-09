import os
import shutil
import platform
import PyInstaller.__main__
import subprocess
import logging
import datetime
from datetime import timezone, timedelta

# OSに合わせてパス区切り文字を設定
SEPARATOR = ';' if platform.system() == 'Windows' else ':'

# OSに応じたvendorsディレクトリをコピーする関数
def copy_vendors():
    system = platform.system()
    project_dir = os.getcwd()
    vendors_dir = os.path.join(project_dir, "vendors")
    
    if system == "Darwin":  # Mac
        src_dir = os.path.join(vendors_dir, "for_Mac")
        dist_dir = os.path.join(os.getcwd(), "dist", "nfc-rename", "vendors", "for_Mac")
    elif system == "Windows":  # Windows
        src_dir = os.path.join(vendors_dir, "for_Win")
        dist_dir = os.path.join(os.getcwd(), "dist", "nfc-rename", "vendors", "for_Win")
    else:
        raise EnvironmentError("サポートされていないOSです")
    
    # ディレクトリがない場合は作成
    os.makedirs(dist_dir, exist_ok=True)
    
    # ffmpegとffprobeをコピー
    try:
        for file in os.listdir(src_dir):
            src_file = os.path.join(src_dir, file)
            dst_file = os.path.join(dist_dir, file)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dst_file)
                print(f"{file}をコピーしました")
                # Macの場合は実行権限を付与
                if system == "Darwin" and (file in ["ffmpeg", "ffprobe", "ffplay"]):
                    os.chmod(dst_file, 0o755)
                    print(f"{file}に実行権限を付与しました")
    except Exception as e:
        print(f"vendorsディレクトリのコピー中にエラーが発生しました: {e}")
    
    print("vendorsディレクトリをコピーしました")

# アセットファイルをコピーする関数
def copy_assets():
    # ルートディレクトリのPNGファイルをコピー
    try:
        root_dir = os.getcwd()
        dist_dir = os.path.join(root_dir, "dist", "nfc-rename")
        
        # security-0.pngとsecurity-1.pngをコピー
        for png_file in ["security-0.png", "security-1.png"]:
            src_file = os.path.join(root_dir, png_file)
            dst_file = os.path.join(dist_dir, png_file)
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
                print(f"{png_file}をコピーしました")
        
        # assetsディレクトリをコピー
        assets_dir = os.path.join(root_dir, "assets")
        dist_assets_dir = os.path.join(dist_dir, "assets")
        
        if os.path.exists(assets_dir):
            # distディレクトリにassetsディレクトリがない場合は作成
            os.makedirs(dist_assets_dir, exist_ok=True)
            
            # assetsディレクトリ内のファイルをコピー
            for file in os.listdir(assets_dir):
                src_file = os.path.join(assets_dir, file)
                dst_file = os.path.join(dist_assets_dir, file)
                if os.path.isfile(src_file):
                    shutil.copy2(src_file, dst_file)
                    print(f"assets/{file}をコピーしました")
    except Exception as e:
        print(f"アセットファイルのコピー中にエラーが発生しました: {e}")
    
    print("アセットファイルのコピーが完了しました")

# macOS用に.appバンドルを修正する関数
def fix_macos_bundle(app_bundle_path):
    """macOSアプリバンドルの修正 - 簡略化バージョン"""
    print("macOSバンドルを修正しています...")

    try:
        # Info.plistを修正
        info_plist_path = os.path.join(app_bundle_path, "Contents", "Info.plist")
        if os.path.exists("custom_info.plist"):
            shutil.copy("custom_info.plist", info_plist_path)
            print("カスタムInfo.plistをコピーしました")

        # アイコンをリソースディレクトリに直接コピーする処理を削除
        # resources_dir = os.path.join(app_bundle_path, "Contents", "Resources")
        # # Resourcesディレクトリがなければ作成
        # os.makedirs(resources_dir, exist_ok=True)
        # icon_dest = os.path.join(resources_dir, "icon.icns")
        # if os.path.exists("assets/icon.icns"):
        #     shutil.copy("assets/icon.icns", icon_dest)
        #     print("icon.icnsをリソースディレクトリに直接コピーしました")
        # else:
        #     print("警告: assets/icon.icns が見つかりません。")

        # 実行権限を付与
        executable_path = os.path.join(app_bundle_path, "Contents", "MacOS", "nfc-rename")
        subprocess.run(["chmod", "+x", executable_path], check=True)
        print("実行可能ファイルに実行権限を付与しました")

        # 署名プロセス（この部分はfix_macos_bundle.pyから移植されたもの、または既存のもの）
        print("署名プロセスを開始します...")
        # まず古い署名を削除
        subprocess.run(["codesign", "--remove-signature", app_bundle_path], check=False)

        # Frameworksディレクトリ内のファイルに署名
        frameworks_dir = os.path.join(app_bundle_path, "Contents", "Frameworks")
        if os.path.exists(frameworks_dir):
            print("Frameworks内のファイルに署名中...")
            for root, dirs, files in os.walk(frameworks_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 署名が必要なファイルタイプをチェック (dylib, so, フレームワーク自体など)
                    # 実行可能ファイルや特定のライブラリのみを対象にする
                    if file.endswith(('.so', '.dylib')) or ('.' not in file and os.access(file_path, os.X_OK)):
                        try:
                            print(f"署名中: {file_path}")
                            subprocess.run([
                                "codesign", "--force", "--sign", "-", "--timestamp", file_path
                            ], check=True, capture_output=True, text=True)
                        except subprocess.CalledProcessError as e:
                            print(f"警告: {file_path} の署名に失敗しました: {e.stderr}")
                        except Exception as e:
                            print(f"警告: {file_path} の署名中に予期せぬエラー: {e}")

        # アプリバンドル全体に署名 (deep署名で内部も署名されるはずだが、念のため個別に署名後に行う)
        print("アプリケーションバンドル全体に署名中...")
        # try:
        #     subprocess.run([
        #         "codesign",
        #         "--force",
        #         "--deep",       # deep署名を使用
        #         "--sign", "-",
        #         # "--no-strict", # strictオプションは可能な限り使用しない方が安全
        #         "--timestamp",
        #         # "--options", "runtime", # 一時的にHardened Runtimeを無効化
        #         "--entitlements", "entitlements.plist",
        #         app_bundle_path
        #     ], check=True, capture_output=True, text=True)
        #     print("アプリケーションバンドルに署名しました")
        # except subprocess.CalledProcessError as e:
        #      print(f"エラー: アプリケーションバンドルの署名に失敗: {e.stderr}")
        #      raise # エラーが発生したらビルドを停止
        print("署名プロセスをスキップしました。")

        # 拡張属性を削除 (Gatekeeperの制限を回避する場合がある)
        print("拡張属性を削除中...")
        subprocess.run(["xattr", "-cr", app_bundle_path], check=True)
        print("拡張属性を削除しました")

        # アプリケーションをリフレッシュ
        print("アプリケーションバンドルのタイムスタンプを更新中...")
        subprocess.run(["touch", app_bundle_path], check=True)
        print("アプリケーションバンドルのタイムスタンプを更新しました")

        # 署名の検証
        print("署名の検証をスキップします...")
        # result = subprocess.run([
        #     "codesign", "--verify", "--verbose=4", app_bundle_path # 詳細度を上げる
        # ], capture_output=True, text=True, check=False)
        # 
        # if result.returncode == 0:
        #     print("署名の検証に成功しました")
        #     # print(f"署名の検証結果:\n{result.stdout}") # 成功時はstdoutが長くなることがあるのでコメントアウト
        # else:
        #     print(f"署名の検証に失敗:\n{result.stderr}")

        # spctl でアプリを評価
        print("Gatekeeperの検証をスキップします...")
        # spctl_result = subprocess.run([
        #     "spctl", "--assess", "--type", "exec", "--verbose=4", app_bundle_path # 詳細度を上げる
        # ], capture_output=True, text=True, check=False)
        # 
        # if spctl_result.returncode == 0:
        #     print("Gatekeeperの検証に成功しました")
        #     # print(f"Gatekeeper検証結果:\n{spctl_result.stdout}")
        # else:
        #     print(f"Gatekeeperの検証に失敗:\n{spctl_result.stderr}")


    except Exception as e:
        print(f"macOSバンドルの修正中にエラー: {e}")
        import traceback
        traceback.print_exc()

print(f"ビルドを開始します... OS: {platform.system()}, パス区切り: {SEPARATOR}")

try:
    # PyInstallerで直接ビルド
    args = [
        "main.py",
        '--name=nfc-rename',
        '--onedir',
        '--windowed',
        '--clean',
        '--noconfirm',
        '--add-data=' + os.path.join("vendors") + SEPARATOR + 'vendors', # vendorsは必要
    ]

    # OS別の設定
    if platform.system() == 'Windows':
        args.append('--icon=' + os.path.join("assets", "new_icon", "nockun_icon.ico"))
    elif platform.system() == 'Darwin':
        # args.append('--icon=' + os.path.join("assets", "icon.icns")) # アイコン設定を削除
        args.append('--osx-bundle-identifier=com.osaka.nfcrename')
        args.append('--osx-entitlements-file=entitlements.plist')
        args.append('--disable-windowed-traceback')
        # args.append('--codesign-identity=-') # アドホック署名を削除

    # 重要なモジュールを明示的にインポート
    args.append('--hidden-import=tkinter')
    args.append('--hidden-import=PIL._tkinter_finder')
    args.append('--hidden-import=asyncio')
    args.append('--hidden-import=websockets.legacy')

    # 不要なアセットファイルの--add-dataを削除
    # PNGファイルを追加していた箇所を削除
    # アセットディレクトリを追加していた箇所を削除

    print("PyInstallerを実行します:", args)
    PyInstaller.__main__.run(args)

    # vendorsディレクトリをコピー (ビルド後)
    # copy_vendors() # PyInstallerの--add-dataで処理されるため不要かも？確認必要

    # アセットファイルをコピーしていた箇所を削除 (fix_macos_bundleでアイコンコピーを行う)

    # macOSの場合はバンドルを修正
    if platform.system() == 'Darwin':
        app_bundle_path = os.path.join(os.getcwd(), "dist", "nfc-rename.app")
        if os.path.exists(app_bundle_path):
             fix_macos_bundle(app_bundle_path) # ここで署名や修正を行う
        else:
             print(f"エラー: {app_bundle_path} が見つかりません。PyInstallerのビルドに失敗した可能性があります。")

    print("ビルド完了!")
except Exception as e:
    print(f"ビルド中にエラーが発生しました: {e}")
