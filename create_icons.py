#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from PIL import Image

def resize_image(input_path, output_path, size):
    """画像をリサイズしてPNG形式で保存する"""
    try:
        img = Image.open(input_path)
        # アスペクト比を保持してリサイズ
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        
        # 正方形のキャンバスを作成
        square_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        
        # 中央に配置
        offset = ((size - img.width) // 2, (size - img.height) // 2)
        square_img.paste(img, offset, img if img.mode == 'RGBA' else None)
        
        # 保存
        square_img.save(output_path, format='PNG')
        return True
    except Exception as e:
        print(f"エラー: {e}")
        return False

def create_iconset(input_path, output_dir):
    """macOS用のiconsetディレクトリを作成"""
    iconset_path = os.path.join(output_dir, "app.iconset")
    os.makedirs(iconset_path, exist_ok=True)
    
    # 必要なアイコンサイズ
    icon_sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png")
    ]
    
    for size, filename in icon_sizes:
        output_path = os.path.join(iconset_path, filename)
        resize_image(input_path, output_path, size)
        print(f"サイズ {size}x{size} のアイコンを作成しました: {filename}")
    
    return iconset_path

def create_icns(iconset_path, output_dir):
    """iconsetからicnsファイルを作成"""
    icns_path = os.path.join(output_dir, "app.icns")
    
    # iconutilコマンドを使用してicnsファイルを生成
    try:
        subprocess.run(["iconutil", "-c", "icns", iconset_path, "-o", icns_path], check=True)
        print(f"icnsファイルを作成しました: {icns_path}")
        return icns_path
    except subprocess.CalledProcessError as e:
        print(f"icnsファイルの作成に失敗しました: {e}")
        return None

def create_ico(input_path, output_dir):
    """Windows用のicoファイルを作成"""
    ico_path = os.path.join(output_dir, "app.ico")
    
    # 必要なアイコンサイズ
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    # 各サイズの画像を作成
    images = []
    for size in sizes:
        tmp_path = os.path.join(output_dir, f"temp_{size[0]}x{size[1]}.png")
        if resize_image(input_path, tmp_path, size[0]):
            img = Image.open(tmp_path)
            images.append(img)
        os.remove(tmp_path)  # 一時ファイルを削除
    
    # icoファイルに保存
    if images:
        images[0].save(ico_path, format='ICO', sizes=[(img.width, img.height) for img in images], 
                      append_images=images[1:])
        print(f"icoファイルを作成しました: {ico_path}")
        return ico_path
    else:
        print("icoファイルの作成に失敗しました")
        return None

def copy_to_assets(icns_path, ico_path, assets_dir):
    """アイコンファイルをassetsディレクトリにコピー"""
    assets_icns_path = os.path.join(assets_dir, "icon.icns")
    assets_ico_path = os.path.join(assets_dir, "icon.ico")
    assets_png_path = os.path.join(assets_dir, "icon.png")
    
    try:
        if icns_path and os.path.exists(icns_path):
            import shutil
            shutil.copy2(icns_path, assets_icns_path)
            print(f"アイコンをコピーしました: {assets_icns_path}")
        
        if ico_path and os.path.exists(ico_path):
            import shutil
            shutil.copy2(ico_path, assets_ico_path)
            print(f"アイコンをコピーしました: {assets_ico_path}")
            
        # 512x512のPNGも作成してコピー
        resize_image(input_path, assets_png_path, 512)
        print(f"PNGアイコンを作成しました: {assets_png_path}")
        
        return True
    except Exception as e:
        print(f"アイコンコピー中にエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    # 画像ファイルの指定
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        print("使用方法: python create_icons.py [元画像パス]")
        sys.exit(1)
        
    # 出力ディレクトリ
    output_dir = "temp_icons"
    os.makedirs(output_dir, exist_ok=True)
    
    # assetsディレクトリ
    assets_dir = "assets"
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir, exist_ok=True)
    
    # macOS用のiconsetを作成
    iconset_path = create_iconset(input_path, output_dir)
    
    # icnsファイルを作成
    icns_path = create_icns(iconset_path, output_dir)
    
    # Windowsのicoファイルも作成
    ico_path = create_ico(input_path, output_dir)
    
    # アイコンをassetsディレクトリにコピー
    copy_to_assets(icns_path, ico_path, assets_dir)
    
    print("アイコン生成が完了しました。")
