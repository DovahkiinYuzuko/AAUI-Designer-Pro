"""
画像解析および輪郭（エッジ）抽出エンジン。
Pillowライブラリを使用し、入力画像からUIレイアウトの境界線を抽出する。
抽出された画像は、GUIキャンバス上でAAパーツを配置するための背景ガイド（トレス用下敷き）として利用される。
"""

from PIL import Image, ImageFilter, ImageOps

def create_guide_image(image_path, target_width=None):
    """
    指定された画像ファイルから輪郭を抽出し、背景ガイド用の画像を生成する。
    
    処理手順:
    1. 画像の読み込みとRGB変換。
    2. 必要に応じて幅を指定サイズにリサイズ（アスペクト比維持）。
    3. グレースケール化。
    4. エッジ検出フィルタの適用。
    5. 色の反転と明度調整（背景を白、輪郭線をグレーにするため）。
    
    引数:
        image_path (str): 読み込む画像ファイルの絶対パスまたは相対パス。
        target_width (int, optional): リサイズ後の幅（ピクセル）。指定がない場合は元のサイズを維持する。
        
    戻り値:
        PIL.Image.Image: 輪郭抽出処理が完了した画像オブジェクト。
                         エラー発生時は例外を送出する。
    """
    try:
        # 画像を読み込み、RGBAなどの透過情報によるエラーを防ぐためRGBに変換する。
        img = Image.open(image_path).convert("RGB")
    except Exception as e:
        raise RuntimeError(f"画像の読み込みに失敗した。詳細: {e}")

    # 指定幅がある場合は、アスペクト比を維持してリサイズする。
    if target_width and img.width > target_width:
        aspect_ratio = img.height / img.width
        target_height = int(target_width * aspect_ratio)
        # LANCZOSは高品質なダウンサンプリングフィルタである。
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # グレースケールに変換する。
    gray_img = img.convert("L")

    # Pillowの組み込みフィルタを使用してエッジ（輪郭）を抽出する。
    # この時点では黒背景に白い線となる。
    edge_img = gray_img.filter(ImageFilter.FIND_EDGES)

    # 背景を白、線を黒にするために色を反転させる。
    inverted_img = ImageOps.invert(edge_img)

    # ガイドとして主張しすぎないよう、全体を明るく（線をグレーに）して返す。
    # 白（255）のベタ塗り画像とのブレンド率を0.7（70%白）に設定している。
    final_img = Image.blend(inverted_img, Image.new("L", inverted_img.size, 255), alpha=0.7)

    return final_img