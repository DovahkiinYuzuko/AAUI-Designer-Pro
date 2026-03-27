"""
AAUI Designer の設定およびパーツ生成モジュール。
多言語対応のUIテキストデータ、キャンバスのグリッド定数、および動的にリサイズ可能なAAパーツの生成ロジックを管理する。
"""

import unicodedata
import platform
import os
import json

ASSETS_DIR = "assets"
ICON_LOCK_PATH = os.path.join(ASSETS_DIR, "locked.png")
ICON_UNLOCK_PATH = os.path.join(ASSETS_DIR, "lock_open.png")
ICON_VISIBLE_PATH = os.path.join(ASSETS_DIR, "visible.png")
ICON_INVISIBLE_PATH = os.path.join(ASSETS_DIR, "invisible.png")
ICON_SIZE = (16, 16)

BACKUP_DIR = "backups"
RECENT_FILES_PATH = "configs/recent_files.json"
SHORTCUTS_PATH = "configs/shortcuts.json"
FONT_CACHE_PATH = "configs/font_cache.json"
AUTO_BACKUP_PATH = os.path.join(BACKUP_DIR, "backup.aaui")
AUTO_SAVE_INTERVAL = 300000
MAX_RECENT_FILES = 5

GRID_WIDTH = 12
GRID_HEIGHT = 24

DEFAULT_SHORTCUTS = {
    "delete": "<Delete>",
    "delete_alt": "<BackSpace>",
    "escape": "<Escape>",
    "undo": "<Control-z>",
    "redo": "<Control-y>",
    "copy": "<Control-c>",
    "paste": "<Control-v>",
    "cut": "<Control-x>",
    "save": "<Control-s>",
    "duplicate": "<Control-d>",
    "move_up": "<Up>",
    "move_down": "<Down>",
    "move_left": "<Left>",
    "move_right": "<Right>",
    "bring_front": "<Control-Shift-Up>",
    "send_back": "<Control-Shift-Down>",
    "bring_forward": "<Control-Up>",
    "send_backward": "<Control-Down>",
    "zoom": "<Control-MouseWheel>",
    "reset_zoom": "<Control-0>",
    "focus_next": "<Control-Right>",
    "focus_prev": "<Control-Left>",
    "group": "<Control-g>",
    "ungroup": "<Control-Shift-G>"
}

SHORTCUT_NAMES = {
    "delete": {"JP": "削除", "EN": "Delete"},
    "delete_alt": {"JP": "削除 (代替)", "EN": "Delete (Alt)"},
    "escape": {"JP": "選択解除 / キャンセル", "EN": "Deselect / Cancel"},
    "undo": {"JP": "元に戻す", "EN": "Undo"},
    "redo": {"JP": "やり直し", "EN": "Redo"},
    "copy": {"JP": "コピー", "EN": "Copy"},
    "paste": {"JP": "貼り付け", "EN": "Paste"},
    "cut": {"JP": "切り取り", "EN": "Cut"},
    "save": {"JP": "保存", "EN": "Save"},
    "duplicate": {"JP": "複製", "EN": "Duplicate"},
    "move_up": {"JP": "上に移動", "EN": "Move Up"},
    "move_down": {"JP": "下に移動", "EN": "Move Down"},
    "move_left": {"JP": "左に移動", "EN": "Move Left"},
    "move_right": {"JP": "右に移動", "EN": "Move Right"},
    "bring_front": {"JP": "最前面へ移動", "EN": "Bring to Front"},
    "send_back": {"JP": "最背面へ移動", "EN": "Send to Back"},
    "bring_forward": {"JP": "前面へ移動", "EN": "Bring Forward"},
    "send_backward": {"JP": "背面へ移動", "EN": "Send Backward"},
    "zoom": {"JP": "ズーム", "EN": "Zoom"},
    "reset_zoom": {"JP": "ズームリセット", "EN": "Reset Zoom"},
    "focus_next": {"JP": "次のパーツへ", "EN": "Focus Next Part"},
    "focus_prev": {"JP": "前のパーツへ", "EN": "Focus Previous Part"},
    "group": {"JP": "グループ化", "EN": "Group"},
    "ungroup": {"JP": "グループ解除", "EN": "Ungroup"}
}

def load_shortcuts():
    if os.path.exists(SHORTCUTS_PATH):
        try:
            with open(SHORTCUTS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "toggle_snap" in data:
                    del data["toggle_snap"]
                merged = DEFAULT_SHORTCUTS.copy()
                merged.update(data)
                return merged
        except Exception as e:
            print(f"Failed to load shortcuts: {e}")
    save_shortcuts(DEFAULT_SHORTCUTS)
    return DEFAULT_SHORTCUTS.copy()

def save_shortcuts(data):
    try:
        with open(SHORTCUTS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to save shortcuts: {e}")

def scan_system_fonts():
    font_dirs = []
    os_name = platform.system()
    if os_name == "Windows":
        font_dirs = [os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")]
    elif os_name == "Darwin":
        font_dirs = ["/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
    else:
        font_dirs = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]

    fonts = {}
    for d in font_dirs:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for file in files:
                    if file.lower().endswith(('.ttf', '.ttc', '.otf')):
                        fonts[file] = os.path.join(root, file)
    return fonts

def load_font_cache():
    if os.path.exists(FONT_CACHE_PATH):
        try:
            with open(FONT_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    fonts = scan_system_fonts()
    save_font_cache(fonts)
    return fonts

def save_font_cache(fonts):
    try:
        with open(FONT_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(fonts, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Failed to save font cache: {e}")

def get_best_font(size=-14):
    os_name = platform.system()
    if os_name == "Windows":
        return ("MS Gothic", size)
    elif os_name == "Darwin":
        return ("Menlo", size)
    else:
        return ("DejaVu Sans Mono", size)

UI_TEXT = {
    "JP": {
        "title": "AAUI Designer Pro",
        "load_guide": "画像読込 (選択レイヤー)",
        "copy_llm": "LLM用コピー",
        "parts_palette": "パーツパレット",
        "properties": "プロパティ",
        "system": "システム設定",
        "grid_size": "グリッドサイズ:",
        "delete_part": "削除",
        "status_ready": "待機中...",
        "status_copied": "クリップボードにコピー完了",
        "status_exported": "エクスポート完了: ",
        "status_autosaved": "自動バックアップ完了",
        "lang_switch": "EN",
        "tool_select": "選択モード",
        "tool_text": "テキスト",
        "tool_rect": "範囲選択",
        "preview_btn": "プレビュー",
        "guide_opacity": "画像透明度:",
        "choose_color": "文字色を選択",
        "preview_title": "AA Preview (等幅フォント)",
        "clear_guide": "画像消去",
        
        "idx_parts": "パーツ",
        "idx_props": "設定",
        "idx_sys": "システム",
        
        "layer_title": "レイヤーマネージャー",
        "layer_add": "追加",
        "layer_del": "削除",
        "layer_up": "上へ",
        "layer_dn": "下へ",
        "layer_lock": "ロック",
        "layer_merge": "下に結合",
        "layer_rename": "名前変更",
        
        "layer_guide_name": "ガイド画像",
        
        "prop_label": "ラベル:",
        "prop_size": "論理サイズ (W/H):",
        "prop_apply": "変更を適用",
        "rt_preview_title": "リアルタイムプレビュー",
        
        "menu_file": "ファイル (F)",
        "menu_new": "新規作成 (N)",
        "menu_open": "開く (O)...",
        "menu_recent": "最近使ったファイル",
        "menu_save": "保存 (S)",
        "menu_save_as": "名前を付けて保存 (A)...",
        "menu_export": "エクスポート (E)",
        "menu_export_md": "Markdown形式で出力 (.md)",
        "menu_export_txt": "テキスト形式で出力 (.txt)",
        "menu_export_png": "画像として出力 (.png)",
        "menu_exit": "終了 (X)",
        
        "menu_edit": "編集 (E)",
        "menu_undo": "元に戻す (U)",
        "menu_redo": "やり直し (R)",
        "menu_cut": "切り取り (T)",
        "menu_copy": "コピー (C)",
        "menu_paste": "貼り付け (P)",
        "menu_duplicate": "複製",
        "menu_delete": "削除",
        "menu_copy_llm": "LLM用AAコピー",
        "menu_edit_shortcuts": "ショートカット編集...",
        "menu_group": "グループ化",
        "menu_ungroup": "グループ解除",
        
        "menu_view": "表示 (V)",
        "menu_toggle_guide": "下絵の表示/非表示",
        "menu_toggle_grid": "グリッドの表示/非表示",
        "menu_bg_color": "背景色を変更...",
        
        "menu_align": "整列 (A)",
        "menu_align_left": "左揃え",
        "menu_align_top": "上揃え",
        
        "menu_help": "ヘルプ (H)",
        "menu_about": "AAUI Designerについて",
        
        "menu_bring_front": "最前面へ移動",
        "menu_bring_forward": "前面へ移動",
        "menu_send_backward": "背面へ移動",
        "menu_send_back": "最背面へ移動",
        
        "font_select": "出力フォント:"
    },
    "EN": {
        "title": "AAUI Designer Pro v4.13",
        "load_guide": "Load Image",
        "copy_llm": "COPY FOR LLM",
        "parts_palette": "PARTS",
        "properties": "PROPERTIES",
        "system": "SYSTEM",
        "grid_size": "Grid Size:",
        "delete_part": "Delete",
        "status_ready": "Ready...",
        "status_copied": "Copied to clipboard",
        "status_exported": "Exported: ",
        "status_autosaved": "Auto-backup completed",
        "lang_switch": "JP",
        "tool_select": "Select",
        "tool_text": "Text",
        "tool_rect": "Marquee",
        "preview_btn": "Preview",
        "guide_opacity": "Image Opacity:",
        "choose_color": "Choose Color",
        "preview_title": "AA Preview (Monospace)",
        "clear_guide": "Clear Image",
        
        "idx_parts": "PRT",
        "idx_props": "PRP",
        "idx_sys": "SYS",
        
        "layer_title": "LAYER MANAGER",
        "layer_add": "Add",
        "layer_del": "Del",
        "layer_up": "Up",
        "layer_dn": "Dn",
        "layer_lock": "Lock",
        "layer_merge": "Merge Down",
        "layer_rename": "Rename",
        
        "layer_guide_name": "Guide Image",
        
        "prop_label": "Label:",
        "prop_size": "Logical Size (W/H):",
        "prop_apply": "Apply Changes",
        "rt_preview_title": "REAL-TIME PREVIEW",
        
        "menu_file": "File",
        "menu_new": "New",
        "menu_open": "Open...",
        "menu_recent": "Recent Files",
        "menu_save": "Save",
        "menu_save_as": "Save As...",
        "menu_export": "Export",
        "menu_export_md": "Export as Markdown (.md)",
        "menu_export_txt": "Export as Text (.txt)",
        "menu_export_png": "Export as Image (.png)",
        "menu_exit": "Exit",
        
        "menu_edit": "Edit",
        "menu_undo": "Undo",
        "menu_redo": "Redo",
        "menu_cut": "Cut",
        "menu_copy": "Copy",
        "menu_paste": "Paste",
        "menu_duplicate": "Duplicate",
        "menu_delete": "Delete",
        "menu_copy_llm": "Copy AA for LLM",
        "menu_edit_shortcuts": "Edit Shortcuts...",
        "menu_group": "Group",
        "menu_ungroup": "Ungroup",
        
        "menu_view": "View",
        "menu_toggle_guide": "Toggle Background Image",
        "menu_toggle_grid": "Toggle Grid",
        "menu_bg_color": "Change Background Color...",
        
        "menu_align": "Align",
        "menu_align_left": "Align Left",
        "menu_align_top": "Align Top",
        
        "menu_help": "Help",
        "menu_about": "About AAUI Designer",
        
        "menu_bring_front": "Bring to Front",
        "menu_bring_forward": "Bring Forward",
        "menu_send_backward": "Send Backward",
        "menu_send_back": "Send to Back",
        
        "font_select": "Export Font:"
    }
}

def get_display_width(text):
    width = 0
    for c in text:
        if unicodedata.east_asian_width(c) in ('F', 'W', 'A'):
            width += 2
        else:
            width += 1
    return width

def generate_box(width, height, label=""):
    label_width = get_display_width(label)
    min_width = label_width + 4 if label else 3
    actual_width = max(width, min_width)
    actual_height = max(height, 2)
    
    top_bottom = "+" + "-" * (actual_width - 2) + "+"
    
    lines = [top_bottom]
    for i in range(actual_height - 2):
        if i == 0 and label:
            display_label = label
            padding_total = actual_width - 2 - label_width
            pad_left = padding_total // 2
            pad_right = padding_total - pad_left
            lines.append("|" + " " * pad_left + display_label + " " * pad_right + "|")
        else:
            lines.append("|" + " " * (actual_width - 2) + "|")
    
    lines.append(top_bottom)
    return "\n".join(lines)

def generate_input(width, height=1, label=""):
    display_label = f"{label}: " if label else ""
    label_width = get_display_width(display_label)
    min_width = label_width + 4
    actual_width = max(width, min_width)
    underscore_len = max(1, actual_width - 4 - label_width)
    return f"[ {display_label}" + "_" * underscore_len + " ]"

def generate_button(width, height=1, label=""):
    label_width = get_display_width(label)
    min_width = label_width + 4 if label else 4
    actual_width = max(width, min_width)
    padding_total = actual_width - 4 - label_width
    pad_left = padding_total // 2
    pad_right = padding_total - pad_left
    return "< " + " " * pad_left + label + " " * pad_right + " >"

def generate_line(width, height=1, label=""):
    actual_width = max(width, 1)
    return "-" * actual_width

def generate_vline(width, height=1, label=""):
    actual_height = max(height, 1)
    return "\n".join(["|"] * actual_height)

def generate_text(width, height=1, label=""):
    return label

os.makedirs("configs", exist_ok=True)

PARTS_LIBRARY = {
    "Box": {"generator": generate_box, "default_w": 20, "default_h": 5, "default_label": {"JP": "ボックス", "EN": "BOX"}, "z_index": 1},
    "Input": {"generator": generate_input, "default_w": 20, "default_h": 1, "default_label": {"JP": "入力", "EN": "Input"}, "z_index": 2},
    "Button": {"generator": generate_button, "default_w": 15, "default_h": 1, "default_label": {"JP": "ボタン", "EN": "BTN"}, "z_index": 2},
    "Line": {"generator": generate_line, "default_w": 20, "default_h": 1, "default_label": {"JP": "", "EN": ""}, "z_index": 1},
    "V-Line": {"generator": generate_vline, "default_w": 1, "default_h": 5, "default_label": {"JP": "", "EN": ""}, "z_index": 1},
    "Text": {"generator": generate_text, "default_w": 10, "default_h": 1, "default_label": {"JP": "テキスト", "EN": "Text"}, "z_index": 3}
}