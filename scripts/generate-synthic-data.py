import itertools
import json
import random
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ==========================================
# CẤU HÌNH (CONFIGURATION)
# ==========================================
class Config:
    NUM_IMAGES = 50
    MAX_RETRIES_PLACEMENT = 50  # Số lần thử tìm vị trí trống trước khi bỏ qua

    # Paths
    BASE_DIR = Path(".")
    ASSETS_DIR = BASE_DIR / "assets"
    FONTS_DIALOG_DIR = ASSETS_DIR / "fonts" / "dialog"
    FONTS_SFX_DIR = ASSETS_DIR / "fonts" / "sfx"
    CORPUS_DIALOG = ASSETS_DIR / "corpus" / "dialog.txt"
    CORPUS_SFX = ASSETS_DIR / "corpus" / "sfx.txt"
    BACKGROUNDS_DIR = ASSETS_DIR / "background"

    OUTPUT_DIR = BASE_DIR / "generated"
    OUTPUT_IMAGES_DIR = OUTPUT_DIR / "images"
    OUTPUT_LABEL_FILE = OUTPUT_DIR / "labels.txt"

    # Tỉ lệ xuất hiện của các loại (Dialog Bubble, Color Box, Text on BG, SFX)
    # Tổng nên là 1.0 (75% dialog các loại, 25% SFX)
    WEIGHTS = [0.55, 0.15, 0.05, 0.25]
    TYPES = ['bubble', 'box', 'text_bg', 'sfx']


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def check_overlap(new_box: Tuple[int, int, int, int], existing_boxes: List[Tuple[int, int, int, int]],
                  margin: int = 10) -> bool:
    """Kiểm tra xem bounding box mới có đè lên các box cũ không."""
    nx1, ny1, nx2, ny2 = new_box
    nx1 -= margin
    ny1 -= margin
    nx2 += margin
    ny2 += margin

    for ex1, ey1, ex2, ey2 in existing_boxes:
        # Nếu không nằm hoàn toàn bên trái, phải, trên, dưới -> là có giao nhau
        if not (nx2 < ex1 or nx1 > ex2 or ny2 < ey1 or ny1 > ey2):
            return True
    return False


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    """Cắt text thành nhiều dòng sao cho không vượt quá max_width."""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        # Sử dụng textbbox cho Pillow bản mới
        bbox = draw.textbbox((0, 0), line_str, font=font)
        w = bbox[2] - bbox[0]

        if w > max_width:
            if len(current_line) == 1:
                # Từ quá dài, bắt buộc phải thêm
                lines.append(current_line.pop())
            else:
                current_line.pop()  # Bỏ từ vừa thêm ra
                lines.append(" ".join(current_line))
                current_line = [word]

    if current_line:
        lines.append(" ".join(current_line))
    return lines


# ==========================================
# MAIN GENERATOR CLASS
# ==========================================
class WebtoonSynthGenerator:
    def __init__(self):
        self._check_and_create_dirs()
        self._load_assets()

    @staticmethod
    def _check_and_create_dirs():
        Config.OUTPUT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        for d in [Config.FONTS_DIALOG_DIR, Config.FONTS_SFX_DIR, Config.BACKGROUNDS_DIR, Config.ASSETS_DIR / "corpus"]:
            d.mkdir(parents=True, exist_ok=True)

    def _load_assets(self):
        print("Đang tải assets...")
        self.dialog_fonts = list(Config.FONTS_DIALOG_DIR.glob("*.ttf")) + list(Config.FONTS_DIALOG_DIR.glob("*.otf"))
        self.sfx_fonts = list(Config.FONTS_SFX_DIR.glob("*.ttf")) + list(Config.FONTS_SFX_DIR.glob("*.otf"))
        self.backgrounds = list(Config.BACKGROUNDS_DIR.glob("*.jpg")) + list(Config.BACKGROUNDS_DIR.glob("*.png"))

        if not self.backgrounds:
            raise ValueError(f"Không tìm thấy background nào trong {Config.BACKGROUNDS_DIR}")
        if not self.dialog_fonts:
            raise ValueError(f"Không tìm thấy font dialog nào trong {Config.FONTS_DIALOG_DIR}")

        self.bg_cycle = itertools.cycle(self.backgrounds)

        # Load corpus
        with open(Config.CORPUS_DIALOG, 'r', encoding='utf-8') as f:
            self.dialog_corpus = [line.strip() for line in f if line.strip()]

        with open(Config.CORPUS_SFX, 'r', encoding='utf-8') as f:
            self.sfx_corpus = [line.strip() for line in f if line.strip()]

    def generate(self):
        labels_data = []

        for idx in range(1, Config.NUM_IMAGES + 1):
            bg_path = next(self.bg_cycle)
            try:
                bg_img = Image.open(bg_path).convert("RGBA")
            except Exception as e:
                print(f"Lỗi đọc ảnh {bg_path}: {e}")
                continue

            bg_width, bg_height = bg_img.size
            draw_bg = ImageDraw.Draw(bg_img)

            num_items = random.randint(3, 7)
            existing_boxes = []
            image_labels = []

            for _ in range(num_items):
                item_type = random.choices(Config.TYPES, weights=Config.WEIGHTS, k=1)[0]

                # Setup cơ bản cho item
                if item_type == 'sfx':
                    text = random.choice(self.sfx_corpus)
                    font_path = random.choice(self.sfx_fonts) if self.sfx_fonts else random.choice(self.dialog_fonts)
                    font_size = random.randint(50, 120)
                else:
                    text = random.choice(self.dialog_corpus)
                    font_path = random.choice(self.dialog_fonts)
                    font_size = random.randint(18, 32)

                font = ImageFont.truetype(str(font_path), font_size)

                # Thử tìm vị trí đặt không bị đè
                placed = False
                for _ in range(Config.MAX_RETRIES_PLACEMENT):
                    if item_type == 'sfx':
                        success, bbox = self._draw_sfx(bg_img, text, font, existing_boxes)
                    else:
                        success, bbox, lines_data = self._draw_dialog(bg_img, text, font, item_type, existing_boxes)

                    if success:
                        existing_boxes.append(bbox)
                        if item_type != 'sfx':  # SFX không gán nhãn theo yêu cầu
                            image_labels.extend(lines_data)
                        placed = True
                        break

            # Lưu ảnh
            out_filename = f"synth-{idx:04d}.jpg"
            out_filepath = Config.OUTPUT_IMAGES_DIR / out_filename

            # Convert lại RGB để lưu JPG
            final_img = bg_img.convert("RGB")
            final_img.save(out_filepath, quality=90)

            # Format PPOCR label: img_path \t [{"transcription": "...", "points": [...]}]
            label_json = json.dumps(image_labels, ensure_ascii=False)
            labels_data.append(f"{out_filepath.as_posix()}\t{label_json}")

            if idx % 50 == 0:
                print(f"Đã tạo {idx}/{Config.NUM_IMAGES} ảnh...")

        # Ghi file label
        with open(Config.OUTPUT_LABEL_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(labels_data))

        print(f"Hoàn tất! Dữ liệu được lưu tại: {Config.OUTPUT_DIR}")

    def _draw_dialog(self, bg_img: Image.Image, text: str, font: ImageFont.FreeTypeFont,
                     dialog_type: str, existing_boxes: List[Tuple[int, int, int, int]]):
        """Vẽ dialog (bubble, box, text_bg) và trả về bounding box cùng nhãn từng dòng."""
        bg_w, bg_h = bg_img.size
        temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))

        max_text_width = random.randint(150, 400)
        lines = wrap_text(text, font, max_text_width, temp_draw)

        # Tính toán kích thước khối chữ
        line_heights = []
        line_widths = []
        for line in lines:
            bbox = temp_draw.textbbox((0, 0), line, font=font)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append(bbox[3] - bbox[1])

        total_text_width = max(line_widths) if line_widths else 0
        total_text_height = sum(line_heights) + (len(lines) - 1) * 5  # spacing = 5

        padding_x = random.randint(20, 40)
        padding_y = random.randint(20, 40)

        # SỬA LỖI: Bubble (Hình Elip) sẽ bị cắt góc nếu padding quá nhỏ.
        # Ta tăng padding lên dựa vào tỉ lệ text để đảm bảo khối chữ chữ nhật fit bên trong elip.
        if dialog_type == 'bubble':
            padding_x += int(total_text_width * 0.25)
            padding_y += int(total_text_height * 0.25)

        box_w = total_text_width + padding_x * 2
        box_h = total_text_height + padding_y * 2

        # Random vị trí
        if box_w >= bg_w or box_h >= bg_h:
            return False, None, None

        pos_x = random.randint(0, bg_w - box_w)
        pos_y = random.randint(0, bg_h - box_h)

        bbox = (pos_x, pos_y, pos_x + box_w, pos_y + box_h)
        if check_overlap(bbox, existing_boxes):
            return False, None, None

        # Bắt đầu vẽ lên một layer riêng
        layer = Image.new('RGBA', bg_img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(layer)

        # 5% dialog box background có color effect
        has_color_effect = random.random() < 0.05

        if dialog_type == 'bubble':
            # Vẽ hình ellipse
            fill_color = (255, 255, 255, 255)
            if has_color_effect:
                fill_color = (random.randint(150, 255), random.randint(150, 255), random.randint(150, 255), 255)
            draw.ellipse([pos_x, pos_y, pos_x + box_w, pos_y + box_h], fill=fill_color, outline=(0, 0, 0, 255), width=2)
        elif dialog_type == 'box':
            # Vẽ hình chữ nhật bo góc
            fill_color = (255, 255, 255, 230)
            if has_color_effect:
                fill_color = (random.randint(150, 255), random.randint(150, 255), random.randint(150, 255), 230)
            draw.rounded_rectangle([pos_x, pos_y, pos_x + box_w, pos_y + box_h], radius=15, fill=fill_color,
                                   outline=(50, 50, 50, 255), width=2)
        # Nếu là text_bg thì không vẽ nền

        # THÊM MỚI: Thiết lập hiệu ứng Glow với random màu
        use_glow = False
        glow_color = (255, 255, 255, 255)
        text_color = (0, 0, 0, 255)

        def get_random_glow():
            return random.randint(50, 255), random.randint(50, 255), random.randint(50, 255), 255

        if dialog_type == 'text_bg':
            use_glow = True
            rand_style = random.random()
            # Random style cho text trên nền:
            if rand_style > 0.66:
                # Chữ trắng viền đen
                text_color = (255, 255, 255, 255)
                glow_color = (0, 0, 0, 255)
            elif rand_style > 0.33:
                # Chữ đen viền trắng
                text_color = (0, 0, 0, 255)
                glow_color = (255, 255, 255, 255)
            else:
                # Chữ trắng viền ngẫu nhiên (glow màu)
                text_color = (255, 255, 255, 255)
                glow_color = get_random_glow()

        elif dialog_type == 'box':
            text_color = (0, 0, 0, 255)
            # 40% box sẽ có hiệu ứng glow
            if random.random() < 0.4:
                use_glow = True
                # Glow trắng hoặc Glow có màu
                glow_color = get_random_glow() if random.random() > 0.5 else (255, 255, 255, 255)
        elif dialog_type == 'bubble':
            text_color = (0, 0, 0, 255)

        glow_layer = None
        glow_draw = None
        if use_glow:
            glow_layer = Image.new('RGBA', bg_img.size, (255, 255, 255, 0))
            glow_draw = ImageDraw.Draw(glow_layer)

        # Vẽ text và thu thập label
        current_y = pos_y + padding_y
        lines_data = []

        for idx, line in enumerate(lines):
            lw = line_widths[idx]
            lh = line_heights[idx]
            # Center align text inside the box
            line_x = pos_x + padding_x + (total_text_width - lw) // 2

            # Vẽ stroke siêu dày lên layer glow (nếu có)
            if use_glow:
                glow_draw.text((line_x, current_y), line, font=font, fill=glow_color, stroke_width=8,
                               stroke_fill=glow_color)

            # Lấy chính xác hộp bao quanh (bounding box) của nét chữ
            exact_bbox = temp_draw.textbbox((line_x, current_y), line, font=font)
            left, top, right, bottom = exact_bbox

            # Thêm 2px padding để nhãn bọc an toàn các viền mờ (anti-aliasing) của font
            pad = 2

            # Format PPOCR points: [TL, TR, BR, BL]
            p_tl = [int(left - pad), int(top - pad)]
            p_tr = [int(right + pad), int(top - pad)]
            p_br = [int(right + pad), int(bottom + pad)]
            p_bl = [int(left - pad), int(bottom + pad)]

            lines_data.append({
                "transcription": line,
                "points": [p_tl, p_tr, p_br, p_bl]
            })

            current_y += lh + 5  # cộng thêm spacing

        # Áp dụng blur cho layer glow và gộp vào layer chính
        if use_glow:
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(3))
            layer.alpha_composite(glow_layer)

        # Vẽ text sắc nét đè lên trên cùng
        current_y = pos_y + padding_y
        for idx, line in enumerate(lines):
            lw = line_widths[idx]
            lh = line_heights[idx]
            line_x = pos_x + padding_x + (total_text_width - lw) // 2
            draw.text((line_x, current_y), line, font=font, fill=text_color)
            current_y += lh + 5

        # Hợp nhất layer vào background
        bg_img.alpha_composite(layer)

        return True, bbox, lines_data

    @staticmethod
    def _draw_sfx(bg_img: Image.Image, text: str, font: ImageFont.FreeTypeFont,
                  existing_boxes: List[Tuple[int, int, int, int]]):
        """Vẽ SFX với rotation và outline dày."""
        temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        bbox_text = temp_draw.textbbox((0, 0), text, font=font)
        tw = bbox_text[2] - bbox_text[0]
        th = bbox_text[3] - bbox_text[1]

        # SỬA LỖI SFX BỊ CẮT GÓC:
        # Tăng canvas ảo lên thật bự (ví dụ 100px mỗi chiều) để chữ và viền (stroke) không bị tràn ra ngoài
        stroke_w = 4
        canvas_pad = 100

        sfx_canvas = Image.new('RGBA', (tw + canvas_pad * 2, th + canvas_pad * 2), (255, 255, 255, 0))
        sfx_draw = ImageDraw.Draw(sfx_canvas)

        # Random màu SFX sặc sỡ
        colors = [(255, 50, 50), (50, 255, 50), (255, 255, 50), (255, 150, 50)]
        fill_color = random.choice(colors) + (255,)

        # Vẽ chữ ở giữa canvas rộng
        sfx_draw.text((canvas_pad, canvas_pad), text, font=font, fill=fill_color, stroke_width=stroke_w,
                      stroke_fill=(0, 0, 0, 255))

        # Xoay ngẫu nhiên
        angle = random.randint(-30, 30)
        sfx_canvas = sfx_canvas.rotate(angle, expand=True, resample=Image.BICUBIC)

        # Sau khi xoay xong, ta crop (cắt) canvas lại vừa vặn với chữ thực tế
        actual_bbox = sfx_canvas.getbbox()
        if actual_bbox:
            sfx_canvas = sfx_canvas.crop(actual_bbox)

        sw, sh = sfx_canvas.size
        bg_w, bg_h = bg_img.size

        if sw >= bg_w or sh >= bg_h:
            return False, None

        pos_x = random.randint(0, bg_w - sw)
        pos_y = random.randint(0, bg_h - sh)

        bbox = (pos_x, pos_y, pos_x + sw, pos_y + sh)
        if check_overlap(bbox, existing_boxes, margin=5):
            return False, None

        # Paste SFX sử dụng chính nó làm mask để giữ alpha
        bg_img.paste(sfx_canvas, (pos_x, pos_y), sfx_canvas)

        return True, bbox


if __name__ == "__main__":
    # Check trước để hướng dẫn người dùng nếu thiếu thư mục
    if not (Config.BACKGROUNDS_DIR.exists() and any(Config.BACKGROUNDS_DIR.iterdir())):
        print(f"[*] VUI LÒNG CHUẨN BỊ DỮ LIỆU:")
        print(f" 1. Tạo file: {Config.CORPUS_DIALOG} và thêm text tiếng Anh vào (mỗi câu 1 dòng).")
        print(f" 2. Tạo file: {Config.CORPUS_SFX} và thêm SFX vào (VD: BOOM, WAM, SWISH...).")
        print(f" 3. Bỏ ảnh nền (raw webtoon) vào: {Config.BACKGROUNDS_DIR}")
        print(f" 4. Bỏ font .ttf/.otf vào: {Config.FONTS_DIALOG_DIR} và {Config.FONTS_SFX_DIR}")

        # Tạo thư mục mẫu để không bị lỗi hoàn toàn khi chạy lần đầu
        Config.BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
        Config.FONTS_DIALOG_DIR.mkdir(parents=True, exist_ok=True)
        Config.FONTS_SFX_DIR.mkdir(parents=True, exist_ok=True)
        (Config.ASSETS_DIR / "corpus").mkdir(parents=True, exist_ok=True)

        if not Config.CORPUS_DIALOG.exists():
            Config.CORPUS_DIALOG.write_text(
                "Hello there!\nThis is a long sentence that should be wrapped to multiple lines.\nAre you okay?\nI will defeat you!")
        if not Config.CORPUS_SFX.exists():
            Config.CORPUS_SFX.write_text("BOOM!\nSWOOSH\nCRASH\nBA-DUMP")

        print("\nĐã tạo cấu trúc thư mục mẫu. Vui lòng thêm fonts và backgrounds rồi chạy lại script.")
    else:
        generator = WebtoonSynthGenerator()
        generator.generate()
