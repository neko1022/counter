#!/usr/bin/env python3
# アイコン生成スクリプト (Pillowなしで動作)
# 純粋なPythonのstruct/zlibを使ってPNGを生成

import struct
import zlib
import os
import math

def create_png(width, height, pixels):
    """
    pixels: list of (R, G, B, A) tuples, row-major order
    Returns PNG binary data
    """
    def make_chunk(chunk_type, data):
        chunk_len = struct.pack('>I', len(data))
        chunk_data = chunk_type + data
        chunk_crc = struct.pack('>I', zlib.crc32(chunk_data) & 0xffffffff)
        return chunk_len + chunk_data + chunk_crc

    # PNG signature
    png_sig = b'\x89PNG\r\n\x1a\n'

    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = make_chunk(b'IHDR', ihdr_data)

    # IDAT chunk (image data)
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # filter type: None
        for x in range(width):
            r, g, b, a = pixels[y * width + x]
            raw_data += struct.pack('BBBB', r, g, b, a)

    compressed = zlib.compress(raw_data, 9)
    idat = make_chunk(b'IDAT', compressed)

    # IEND chunk
    iend = make_chunk(b'IEND', b'')

    return png_sig + ihdr + idat + iend


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def blend(fg, bg):
    """Alpha compositing: fg over bg"""
    fr, fg_c, fb, fa = fg
    br, bg_c, bb, ba = bg
    fa_n = fa / 255.0
    ba_n = ba / 255.0
    out_a = fa_n + ba_n * (1 - fa_n)
    if out_a == 0:
        return (0, 0, 0, 0)
    out_r = (fr * fa_n + br * ba_n * (1 - fa_n)) / out_a
    out_g = (fg_c * fa_n + bg_c * ba_n * (1 - fa_n)) / out_a
    out_b = (fb * fa_n + bb * ba_n * (1 - fa_n)) / out_a
    return (int(clamp(out_r, 0, 255)),
            int(clamp(out_g, 0, 255)),
            int(clamp(out_b, 0, 255)),
            int(clamp(out_a * 255, 0, 255)))


def draw_icon(size):
    """スロットマシンアイコンを描画してピクセル配列を返す"""
    pixels = [(26, 10, 36, 255)] * (size * size)  # 背景色 #1a0a24

    s = size / 192.0  # スケール

    def px(x, y, color):
        """1ピクセルを描画"""
        xi, yi = int(x), int(y)
        if 0 <= xi < size and 0 <= yi < size:
            pixels[yi * size + xi] = blend(color, pixels[yi * size + xi])

    def fill_rect(x, y, w, h, color, radius=0):
        """矩形を塗りつぶす (角丸対応)"""
        for py in range(int(y), int(y + h) + 1):
            for px_ in range(int(x), int(x + w) + 1):
                if not (0 <= px_ < size and 0 <= py < size):
                    continue
                # 角丸チェック
                if radius > 0:
                    # 四隅の距離チェック
                    dx = max(0, max(x + radius - px_, px_ - (x + w - radius)))
                    dy = max(0, max(y + radius - py, py - (y + h - radius)))
                    if dx * dx + dy * dy > radius * radius:
                        continue
                idx = py * size + px_
                pixels[idx] = blend(color, pixels[idx])

    def draw_circle(cx, cy, r, color, filled=True):
        for py in range(int(cy - r) - 1, int(cy + r) + 2):
            for px_ in range(int(cx - r) - 1, int(cx + r) + 2):
                if not (0 <= px_ < size and 0 <= py < size):
                    continue
                dist = math.sqrt((px_ - cx)**2 + (py - cy)**2)
                if filled:
                    if dist <= r:
                        idx = py * size + px_
                        pixels[idx] = blend(color, pixels[idx])
                else:
                    if abs(dist - r) < 1.5:
                        alpha = int(255 * max(0, 1 - abs(dist - r)))
                        c = (color[0], color[1], color[2], alpha)
                        idx = py * size + px_
                        pixels[idx] = blend(c, pixels[idx])

    def draw_rect_border(x, y, w, h, color, thickness=2, radius=0):
        """矩形の枠線を描画"""
        for t in range(int(thickness)):
            off = t
            fill_rect(x + off, y + off, w - off*2, h - off*2,
                      (0, 0, 0, 0), radius)  # 内側は透明 (fill無し)

        # 実際に枠線を描く
        for py in range(int(y), int(y + h) + 1):
            for px_ in range(int(x), int(x + w) + 1):
                if not (0 <= px_ < size and 0 <= py < size):
                    continue
                if radius > 0:
                    dx = max(0, max(x + radius - px_, px_ - (x + w - radius)))
                    dy = max(0, max(y + radius - py, py - (y + h - radius)))
                    dist_corner = math.sqrt(dx*dx + dy*dy)
                    if dist_corner > radius:
                        continue

                # 枠線判定
                in_border = (px_ < x + thickness or px_ > x + w - thickness or
                             py < y + thickness or py > y + h - thickness)
                if in_border:
                    idx = py * size + px_
                    pixels[idx] = blend(color, pixels[idx])

    # ===== 背景グラデーション (放射状) =====
    cx, cy = size / 2.0, size / 2.0
    max_dist = math.sqrt(cx**2 + cy**2)
    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            t = dist / max_dist
            # #2a1040 -> #1a0a24
            r = int(lerp(42, 26, t))
            g = int(lerp(16, 10, t))
            b = int(lerp(64, 36, t))
            pixels[y * size + x] = (r, g, b, 255)

    margin = int(16 * s)

    # ===== 角丸矩形の本体 =====
    radius_body = int(24 * s)
    bx, by = margin, margin
    bw, bh = size - margin*2, size - margin*2

    # 本体塗りつぶし
    fill_rect(bx, by, bw, bh, (55, 25, 75, 255), radius_body)

    # 本体枠線 (紫グラデーション風)
    border_thick = int(max(2, 3 * s))
    draw_rect_border(bx, by, bw, bh, (160, 32, 184, 230), border_thick, radius_body)

    # ===== ヘッダー部分 =====
    header_h = int(32 * s)
    fill_rect(bx, by, bw, header_h, (123, 15, 160, 200), radius_body)

    # ===== リール3つ =====
    reel_w = int(36 * s)
    reel_h = int(44 * s)
    reel_y = int(50 * s)
    reel_gap = int(8 * s)
    total_reel_w = reel_w * 3 + reel_gap * 2
    reel_start_x = (size - total_reel_w) // 2

    reel_colors = [
        (255, 215, 0, 255),    # ゴールド (ベル)
        (239, 68, 68, 255),    # 赤 (チェリー)
        (34, 197, 94, 255),    # 緑 (スイカ)
    ]

    for i in range(3):
        rx = reel_start_x + i * (reel_w + reel_gap)
        # リール背景 (白)
        fill_rect(rx, reel_y, reel_w, reel_h, (248, 242, 252, 255), int(5 * s))
        # リール内のカラーバー
        bar_h = int(reel_h * 0.45)
        bar_y = reel_y + (reel_h - bar_h) // 2
        fill_rect(rx + int(4*s), bar_y, reel_w - int(8*s), bar_h,
                  reel_colors[i], int(3 * s))

    # ===== 当選ライン (点線) =====
    line_y = reel_y + reel_h // 2
    dot_spacing = int(6 * s)
    for x in range(bx + int(8*s), bx + bw - int(8*s), dot_spacing * 2):
        fill_rect(x, line_y - 1, int(dot_spacing * 0.8), int(2 * s),
                  (255, 215, 0, 200))

    # ===== テキストエリア (簡略版: 色ブロックで表現) =====
    text_y = int(110 * s)

    # "スロットカウンター" を示す紫色のバー
    text_bar_w = int(100 * s)
    text_bar_h = int(8 * s)
    fill_rect((size - text_bar_w) // 2, text_y, text_bar_w, text_bar_h,
              (160, 32, 184, 200), int(4 * s))

    text_bar2_w = int(80 * s)
    fill_rect((size - text_bar2_w) // 2, text_y + int(12 * s),
              text_bar2_w, int(6 * s), (123, 15, 160, 150), int(3 * s))

    # ===== カウンター表示エリア =====
    counter_y = int(134 * s)
    counter_h = int(22 * s)
    counter_w = int(120 * s)
    counter_x = (size - counter_w) // 2
    fill_rect(counter_x, counter_y, counter_w, counter_h, (26, 10, 36, 255), int(4 * s))
    draw_rect_border(counter_x, counter_y, counter_w, counter_h,
                     (160, 32, 184, 200), int(max(1, 1.5 * s)), int(4 * s))

    # カウンター内のドット
    dot_y = counter_y + counter_h // 2
    for i in range(6):
        dot_x = counter_x + int(10 * s) + i * int(15 * s)
        fill_rect(dot_x, dot_y - int(2*s), int(10*s), int(4*s),
                  (160, 32, 184, 180), int(2*s))

    # ===== 四隅の輝き =====
    corner_colors = [
        (255, 215, 0, 255),    # 左上: ゴールド
        (239, 68, 68, 255),    # 右上: 赤
        (34, 197, 94, 255),    # 左下: 緑
        (168, 85, 247, 255),   # 右下: 紫
    ]
    corner_pos = [
        (bx + int(10*s), by + int(10*s)),
        (bx + bw - int(10*s), by + int(10*s)),
        (bx + int(10*s), by + bh - int(10*s)),
        (bx + bw - int(10*s), by + bh - int(10*s)),
    ]
    for (cx_c, cy_c), color in zip(corner_pos, corner_colors):
        draw_circle(cx_c, cy_c, int(5 * s), color)

    # ===== 上部のLEDライト風装飾 =====
    led_colors = [
        (255, 215, 0, 220),
        (239, 68, 68, 220),
        (34, 197, 94, 220),
        (56, 189, 248, 220),
        (160, 32, 184, 220),
    ]
    led_y = by + int(14 * s)
    total_led_w = len(led_colors) * int(14 * s) - int(4 * s)
    led_start = (size - total_led_w) // 2
    for i, lc in enumerate(led_colors):
        lx = led_start + i * int(14 * s)
        draw_circle(lx, led_y, int(4 * s), lc)

    return pixels


# アイコンを生成して保存
output_dir = os.path.join(os.path.dirname(__file__), 'icons')
os.makedirs(output_dir, exist_ok=True)

for size in [192, 512]:
    print(f'アイコン {size}x{size} を生成中...')
    pixels = draw_icon(size)
    png_data = create_png(size, size, pixels)
    out_path = os.path.join(output_dir, f'icon-{size}.png')
    with open(out_path, 'wb') as f:
        f.write(png_data)
    print(f'  -> {out_path} ({len(png_data):,} bytes)')

print('完了!')
