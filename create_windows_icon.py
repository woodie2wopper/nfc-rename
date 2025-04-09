from PIL import Image
import os

def convert_to_ico(input_path, output_path, sizes=[16, 24, 32, 48, 64, 128, 256]):
    """
    PNG画像をWindows用のICOファイルに変換する
    
    :param input_path: 入力ファイルのパス（PNG画像）
    :param output_path: 出力ファイルのパス（ICOファイル）
    :param sizes: アイコンのサイズリスト
    """
    try:
        # 元の画像を開く
        img = Image.open(input_path)
        
        # 各サイズのアイコンを作成
        icon_sizes = [(size, size) for size in sizes]
        resized_images = [img.resize(size, Image.LANCZOS) for size in icon_sizes]
        
        # アルファチャンネルを確保
        for i, image in enumerate(resized_images):
            if image.mode != 'RGBA':
                resized_images[i] = image.convert('RGBA')
        
        # ICOファイルとして保存
        resized_images[0].save(
            output_path, 
            format='ICO', 
            sizes=[(image.width, image.height) for image in resized_images],
            append_images=resized_images[1:]
        )
        
        print(f"ICOファイルが正常に作成されました: {output_path}")
        return True
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    # 入力ファイルと出力ファイルのパス
    input_file = "assets/new_icon/nockun_square_rounded.png"
    output_file = "assets/new_icon/nockun_icon.ico"
    
    if not os.path.exists(input_file):
        print(f"入力ファイルが見つかりません: {input_file}")
    else:
        convert_to_ico(input_file, output_file) 