import os
import shutil
import platform
import PyInstaller.__main__

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

print(f"ビルドを開始します... OS: {platform.system()}, パス区切り: {SEPARATOR}")

try:
    # PyInstallerで直接ビルド
    args = [
        "main.py",  # ルートディレクトリ内のmain.pyを指定
        '--name=nfc-rename',
        '--onedir',
        '--windowed',
        '--clean',
        '--add-data=' + os.path.join("vendors") + SEPARATOR + 'vendors',
        '--icon=' + os.path.join("assets", "icon.ico"),  # Windowsの場合
    ]
    
    # PNGファイルを追加
    for png_file in ["security-0.png", "security-1.png"]:
        if os.path.exists(png_file):
            args.append('--add-data=' + png_file + SEPARATOR + '.')
    
    # アセットディレクトリを追加（存在する場合）
    assets_dir = os.path.join("assets")
    if os.path.exists(assets_dir):
        args.append('--add-data=' + assets_dir + SEPARATOR + 'assets')
    
    print("PyInstallerを実行します:", args)
    PyInstaller.__main__.run(args)
    
    # vendorsディレクトリをコピー
    copy_vendors()
    
    # アセットファイルをコピー
    copy_assets()
    
    print("ビルド完了!")
except Exception as e:
    print(f"ビルド中にエラーが発生しました: {e}")
