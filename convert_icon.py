from PIL import Image
import os

# アセットディレクトリのパスを設定
assets_dir = os.path.join('nfc-rename', 'assets')
icon_path = os.path.join(assets_dir, 'icon.png')

# PNGをICOに変換
img = Image.open(icon_path)
icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save('icon.ico', format='ICO', sizes=icon_sizes) 