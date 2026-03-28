"""
AAUI Designer Pro のキャンバス管理モジュール。
エディタキャンバスおよびリアルタイムプレビュー領域の描画、座標計算、
マウス・キーボードイベント、パーツの選択・移動・変形ロジックを統括する。
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import uuid
import os
import customtkinter as ctk
import config

class CanvasManager:
    def __init__(self, app):
        self.app = app
        self.drag_data = {"x": 0, "y": 0, "mode": None, "item": None, "corner": None, "group_offsets": {}}
        
        self.marquee_id = None
        self.resize_handle_ids = []
        self.is_editing_inline = False
        self.inline_window_id = None
        self.inline_entry = None
        self.editing_item_id = None
        self.scale = 1.0
        
        self.bind_events()

    def bind_events(self):
        c = self.app.ui.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_drag)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Double-Button-1>", self.on_double_click)
        c.bind("<Button-3>", self.show_context_menu)

    def on_zoom(self, event):
        if event.delta > 0 or getattr(event, 'num', 0) == 4:
            new_scale = min(5.0, self.scale * 1.2)
        else:
            new_scale = max(0.2, self.scale / 1.2)
            
        if new_scale != self.scale:
            self.scale = new_scale
            self.redraw_all()
            self.app.set_status(f"Zoom: {int(self.scale * 100)}%")

    def reset_zoom(self, event=None):
        self.scale = 1.0
        self.redraw_all()
        self.app.set_status("Zoom: 100%")

    def reset_view_full(self):
        self.scale = 1.0
        self.redraw_all()
        self.app.ui.canvas.xview_moveto(0)
        self.app.ui.canvas.yview_moveto(0)
        self.app.set_status("View reset to origin.")

    def focus_part(self, direction="next"):
        layer_id = self.app.app_state.active_layer_id
        parts = self._get_parts_in_layer(layer_id)
        if not parts:
            self.app.set_status("No parts in active layer to focus.")
            return

        current_idx = -1
        if self.app.app_state.selected_items:
            sel_id = list(self.app.app_state.selected_items)[0]
            for i, (p_id, d) in enumerate(parts):
                if p_id == sel_id:
                    current_idx = i
                    break

        if direction == "next":
            target_idx = (current_idx + 1) % len(parts)
        elif direction == "prev":
            target_idx = (current_idx - 1) % len(parts)
        elif direction == "first":
            target_idx = 0
        else:
            target_idx = 0

        target_p_id = parts[target_idx][0]
        self.select_item(target_p_id)

        bbox = self.get_part_bbox(target_p_id)
        if bbox:
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            
            cw = self.app.ui.canvas.winfo_width()
            ch = self.app.ui.canvas.winfo_height()
            
            sr = self.app.ui.canvas.cget("scrollregion")
            if sr:
                try:
                    sr_vals = [float(x) for x in sr.split()]
                    total_w = sr_vals[2] - sr_vals[0]
                    total_h = sr_vals[3] - sr_vals[1]
                except Exception:
                    total_w, total_h = 4000, 4000
            else:
                total_w, total_h = 4000, 4000
            
            frac_x = (cx - cw / 2) / total_w
            frac_y = (cy - ch / 2) / total_h
            
            self.app.ui.canvas.xview_moveto(max(0.0, min(1.0, frac_x)))
            self.app.ui.canvas.yview_moveto(max(0.0, min(1.0, frac_y)))
            self.app.set_status(f"Focused on part {target_idx + 1}/{len(parts)}")

    def redraw_all(self, update_preview=True):
        self.draw_rulers_and_grid()
        for p_id in list(self.app.app_state.parts_data.keys()):
            self.redraw_part(p_id, update_preview=False)
        self.apply_z_order()
        if update_preview:
            self.update_realtime_preview()

    def get_part_id_from_item(self, item_id):
        for p_id, data in self.app.app_state.parts_data.items():
            if item_id in data.get("canvas_items", []):
                return p_id
        return None

    def get_part_bbox(self, p_id):
        items = self.app.app_state.parts_data.get(p_id, {}).get("canvas_items", [])
        if not items: return None
        c = self.app.ui.canvas
        bboxes = [c.bbox(i) for i in items if c.bbox(i)]
        if not bboxes: return None
        x1 = min(b[0] for b in bboxes)
        y1 = min(b[1] for b in bboxes)
        x2 = max(b[2] for b in bboxes)
        y2 = max(b[3] for b in bboxes)
        return x1, y1, x2, y2

    def clear_all_parts(self):
        for p_id in list(self.app.app_state.parts_data.keys()):
            self.app.ui.canvas.delete(p_id)
        self.app.app_state.parts_data.clear()
        self.deselect_all()
        self.update_realtime_preview()

    def apply_layer_visibility(self):
        for p_id, data in self.app.app_state.parts_data.items():
            l_id = data.get("layer_id")
            lyr = next((l for l in self.app.app_state.layers if l["id"] == l_id), None)
            is_vis = lyr.get("visible", True) if lyr else True
            state = "normal" if is_vis else "hidden"
            for item in data.get("canvas_items", []):
                self.app.ui.canvas.itemconfig(item, state=state)
        self.update_realtime_preview()

    def draw_rulers_and_grid(self):
        self.app.ui.top_ruler.delete("all")
        self.app.ui.left_ruler.delete("all")
        self.app.ui.canvas.delete("grid")
        
        gw = config.GRID_WIDTH * self.scale
        gh = config.GRID_HEIGHT * self.scale
        
        for col in range(0, int(4000 / config.GRID_WIDTH)):
            if col % 5 == 0:
                self.app.ui.top_ruler.create_text(col * gw + 2, 10, text=str(col), fill="#888888", anchor="w", font=("Arial", 8))
        for row in range(0, int(4000 / config.GRID_HEIGHT)):
            self.app.ui.left_ruler.create_text(15, row * gh + 10, text=str(row + 1), fill="#888888", font=("Arial", 8))
        for x_idx in range(0, int(4000 / config.GRID_WIDTH)):
            for y_idx in range(0, int(4000 / config.GRID_HEIGHT)):
                if x_idx % 2 == 0 and y_idx % 2 == 0:
                    x = x_idx * gw
                    y = y_idx * gh
                    self.app.ui.canvas.create_rectangle(x, y, x+1, y+1, fill="#444444", outline="", tags="grid")
                    
        state = "normal" if self.app.show_grid_flag else "hidden"
        self.app.ui.canvas.itemconfig("grid", state=state)
        self.app.ui.canvas.tag_lower("grid")
        self.apply_z_order()

    def apply_z_order(self):
        self.app.ui.canvas.tag_lower("grid")
        for lyr in self.app.app_state.layers:
            l_id = lyr["id"]
            p_ids = [p_id for p_id, d in self.app.app_state.parts_data.items() if d.get("layer_id") == l_id]
            p_ids.sort(key=lambda p_id: self.app.app_state.parts_data[p_id].get("z_order", 0))
            for p_id in p_ids:
                for item in self.app.app_state.parts_data[p_id].get("canvas_items", []):
                    self.app.ui.canvas.tag_raise(item)

        for hid in self.resize_handle_ids:
            self.app.ui.canvas.tag_raise(hid)

    def redraw_part(self, p_id, update_preview=True):
        if p_id not in self.app.app_state.parts_data: return
        data = self.app.app_state.parts_data[p_id]
        c = self.app.ui.canvas
        for item in data.get("canvas_items", []):
            c.delete(item)
            
        gw = config.GRID_WIDTH * self.scale
        gh = config.GRID_HEIGHT * self.scale
            
        x1 = data["col"] * gw
        y1 = data["row"] * gh
        
        logical_width = max(data["width"], sum(config.get_display_width(ch) for ch in data["label"])) if data["type"] == "Text" else data["width"]
        x2 = x1 + logical_width * gw
        y2 = y1 + data["height"] * gh
        
        lyr = next((l for l in self.app.app_state.layers if l["id"] == data.get("layer_id")), None)
        opacity = lyr.get("opacity", 1.0) if lyr else 1.0
        
        is_selected = p_id in self.app.app_state.selected_items
        dash_pattern = (4, 4) if data.get("locked", False) else ()

        if data["type"] == "Image":
            image_path = data.get("image_path")
            if image_path and os.path.exists(image_path):
                try:
                    raw_img = Image.open(image_path).convert("RGBA")
                    scaled_w = max(1, int(data["width"] * gw))
                    scaled_h = max(1, int(data["height"] * gh))
                    resized_img = raw_img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
                    
                    if opacity < 1.0:
                        alpha = resized_img.getchannel('A')
                        alpha = alpha.point(lambda i: int(i * opacity))
                        resized_img.putalpha(alpha)
                        
                    photo = ImageTk.PhotoImage(resized_img)
                    data["image_obj"] = photo
                    
                    item_id = c.create_image(x1, y1, anchor="nw", image=photo, tags=("draggable", "part", p_id))
                    self.app.app_state.parts_data[p_id]["canvas_items"] = [item_id]
                    
                    if is_selected:
                        sel_outline = c.create_rectangle(x1, y1, x2, y2, fill="", outline="#00FF00", width=max(1, int(2*self.scale)), dash=dash_pattern, tags=("draggable", "part", p_id))
                        self.app.app_state.parts_data[p_id]["canvas_items"].append(sel_outline)
                        
                except Exception as e:
                    print(f"Failed to load image: {e}")
            else:
                rect_id = c.create_rectangle(x1, y1, x2, y2, fill="#333", outline="red", dash=(4,4), tags=("draggable", "part", p_id))
                text_id = c.create_text((x1+x2)/2, (y1+y2)/2, text="Image Not Found", fill="red", tags=("draggable", "part", p_id))
                self.app.app_state.parts_data[p_id]["canvas_items"] = [rect_id, text_id]
        else:
            stipple_val = ""
            if opacity < 0.25:
                stipple_val = "gray12"
            elif opacity < 0.5:
                stipple_val = "gray25"
            elif opacity < 0.75:
                stipple_val = "gray50"
            elif opacity < 0.95:
                stipple_val = "gray75"
            
            fill_color = "#2b2b2b" if data["type"] != "Text" else ""
            outline_color = "#00FF00" if is_selected else data.get("color", "#FFFFFF")
            line_width = max(1, int(2 * self.scale)) if is_selected else max(1, int(1 * self.scale))
            
            rect_id = c.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline=outline_color, width=line_width, stipple=stipple_val, dash=dash_pattern, tags=("draggable", "part", p_id))
            
            display_text = f"{data['type']}: {data['label']}" if data['label'] else data['type']
            if data["type"] == "Text":
                display_text = data["label"]
                
            font_size = max(6, int(10 * self.scale))
            text_id = c.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=display_text, fill=outline_color, font=("Arial", font_size, "bold"), stipple=stipple_val, tags=("draggable", "part", p_id))
            
            self.app.app_state.parts_data[p_id]["canvas_items"] = [rect_id, text_id]
        
        if is_selected and len(self.app.app_state.selected_items) == 1 and not data.get("locked", False):
            self._draw_resize_handles(x1, y1, x2, y2)
        elif len(self.app.app_state.selected_items) > 1 or data.get("locked", False):
            self._clear_resize_handles()
            
        self.apply_layer_visibility()
        self.apply_z_order()
        
        if update_preview:
            self.update_realtime_preview()

    def _draw_resize_handles(self, x1, y1, x2, y2):
        self._clear_resize_handles()
        c = self.app.ui.canvas
        s = 6
        self.resize_handle_ids.append(c.create_rectangle(x1-s, y1-s, x1+s, y1+s, fill="#e74c3c", outline="white", tags=("resize_handle_nw", "resize_handle")))
        self.resize_handle_ids.append(c.create_rectangle(x2-s, y1-s, x2+s, y1+s, fill="#e74c3c", outline="white", tags=("resize_handle_ne", "resize_handle")))
        self.resize_handle_ids.append(c.create_rectangle(x1-s, y2-s, x1+s, y2+s, fill="#e74c3c", outline="white", tags=("resize_handle_sw", "resize_handle")))
        self.resize_handle_ids.append(c.create_rectangle(x2-s, y2-s, x2+s, y2+s, fill="#e74c3c", outline="white", tags=("resize_handle_se", "resize_handle")))

    def _clear_resize_handles(self):
        for hid in self.resize_handle_ids:
            self.app.ui.canvas.delete(hid)
        self.resize_handle_ids.clear()

    def update_realtime_preview(self):
        pc = self.app.ui.preview_canvas
        pc.delete("all")
        final_text = self.generate_aa_text()
        
        if not final_text:
            pc.configure(scrollregion=(0, 0, 2000, 2000))
            return
            
        lines = final_text.split("\n")
        font_setting = config.get_best_font()
        
        line_nums = "\n".join(f"{i+1:3d} |" for i in range(len(lines)))
        pc.create_text(5, 10, text=line_nums, anchor="nw", font=font_setting, fill="#555555")
        pc.create_text(45, 10, text=final_text, anchor="nw", font=font_setting, fill="#FFFFFF")
        
        line_h = 16
        max_y = 10 + len(lines) * line_h + 50
        max_x = 45 + (max(len(l) for l in lines) * 10) + 50 if lines else 2000
        pc.configure(scrollregion=(0, 0, max(800, max_x), max(800, max_y)))

    def generate_aa_text(self):
        if not self.app.app_state.parts_data: return ""
        
        visible_parts = {}
        for p_id, data in self.app.app_state.parts_data.items():
            lyr = next((l for l in self.app.app_state.layers if l["id"] == data.get("layer_id")), None)
            if lyr and not lyr.get("visible", True):
                continue
            visible_parts[p_id] = data

        if not visible_parts: return ""

        max_col, max_row = 0, 0
        for p_id, data in visible_parts.items():
            gen = config.PARTS_LIBRARY[data["type"]]["generator"]
            lines = gen(data["width"], data["height"], data["label"]).split("\n")
            max_row = max(max_row, data["row"] + len(lines))
            for line in lines:
                max_col = max(max_col, data["col"] + sum(config.get_display_width(c) for c in line))

        grid = [[" " for _ in range(max_col + 1)] for _ in range(max_row + 1)]
        def get_sort_key(item):
            data = item[1]
            layer_idx = next((i for i, lyr in enumerate(self.app.app_state.layers) if lyr["id"] == data.get("layer_id")), 0)
            z_idx = data.get("z_order", 0)
            return (layer_idx, z_idx)

        for p_id, data in sorted(visible_parts.items(), key=get_sort_key):
            lines = config.PARTS_LIBRARY[data["type"]]["generator"](data["width"], data["height"], data["label"]).split("\n")
            for r_idx, line in enumerate(lines):
                r = data["row"] + r_idx
                current_c = data["col"]
                for char in line:
                    char_w = config.get_display_width(char)
                    if r < len(grid) and current_c < len(grid[0]) and char != " ":
                        existing = grid[r][current_c]
                        if existing in ("|", "+") and char in ("-", "_", "="):
                            grid[r][current_c] = "+"
                        elif existing in ("-", "_", "=", "+") and char == "|":
                            grid[r][current_c] = "+"
                        else:
                            grid[r][current_c] = char
                        if char_w == 2 and current_c + 1 < len(grid[0]):
                            grid[r][current_c + 1] = ""
                    current_c += char_w
        return "\n".join(["".join(row).rstrip() for row in grid])

    def export_as_image(self, file_path, transparent=False):
        final_text = self.generate_aa_text()
        if not final_text:
            messagebox.showinfo("Info", "No AA to export.")
            return

        lines = final_text.split("\n")
        
        scale_factor = 4
        base_pt_size = 14
        pt_size = base_pt_size * scale_factor
        
        font_path = self.app.current_export_font
        try:
            font = ImageFont.truetype(font_path, pt_size)
        except IOError:
            try:
                font = ImageFont.truetype("msgothic.ttc", pt_size)
            except IOError:
                font = ImageFont.load_default()
                scale_factor = 1

        dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        
        if hasattr(dummy_draw, 'textbbox') and scale_factor > 1:
            bbox = dummy_draw.textbbox((0, 0), "A", font=font)
            char_w = bbox[2] - bbox[0]
            char_h = bbox[3] - bbox[1]
        else:
            char_w = 8 * scale_factor
            char_h = 14 * scale_factor
            
        line_spacing = int(char_h + 2 * scale_factor)
        char_w_adj = max(1, int(char_w))

        max_len = max([sum(config.get_display_width(c) for c in line) for line in lines]) if lines else 0
        img_width = int(max_len * char_w_adj + 20 * scale_factor)
        img_height = int(len(lines) * line_spacing + 20 * scale_factor)

        if transparent:
            img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        else:
            hex_color = self.app.app_state.bg_color.lstrip('#')
            try:
                bg_rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            except ValueError:
                bg_rgb = (30, 30, 30)
            img = Image.new("RGB", (img_width, img_height), bg_rgb)

        def get_sort_key(item):
            data = item[1]
            layer_idx = next((i for i, lyr in enumerate(self.app.app_state.layers) if lyr["id"] == data.get("layer_id")), 0)
            z_idx = data.get("z_order", 0)
            return (layer_idx, z_idx)

        for p_id, data in sorted(self.app.app_state.parts_data.items(), key=get_sort_key):
            lyr = next((l for l in self.app.app_state.layers if l["id"] == data.get("layer_id")), None)
            if not lyr or not lyr.get("visible", True):
                continue
            if data["type"] == "Image" and data.get("image_path"):
                try:
                    img_part = Image.open(data["image_path"]).convert("RGBA")
                    scaled_w = int(data["width"] * char_w_adj)
                    scaled_h = int(data["height"] * line_spacing)
                    if scaled_w > 0 and scaled_h > 0:
                        img_part = img_part.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
                        lyr_opacity = lyr.get("opacity", 1.0)
                        if lyr_opacity < 1.0:
                            alpha = img_part.getchannel('A')
                            alpha = alpha.point(lambda i: int(i * lyr_opacity))
                            img_part.putalpha(alpha)
                        px = int(data["col"] * char_w_adj) + 10 * scale_factor
                        py = int(data["row"] * line_spacing) + 10 * scale_factor
                        img.paste(img_part, (px, py), img_part)
                except Exception as e:
                    print(f"Export image error: {e}")
            
        draw = ImageDraw.Draw(img)
        color_map = {}

        for p_id, data in sorted(self.app.app_state.parts_data.items(), key=get_sort_key):
            lyr = next((l for l in self.app.app_state.layers if l["id"] == data.get("layer_id")), None)
            if lyr and not lyr.get("visible", True):
                continue
                
            gen = config.PARTS_LIBRARY[data["type"]]["generator"]
            part_lines = gen(data["width"], data["height"], data["label"]).split("\n")
            for r_idx, line in enumerate(part_lines):
                r = data["row"] + r_idx
                current_c = data["col"]
                for char in line:
                    char_w_disp = config.get_display_width(char)
                    if char != " ":
                        color_map[(r, current_c)] = data.get("color", "#FFFFFF")
                    current_c += char_w_disp

        y_pos = 10 * scale_factor
        for r_idx, line in enumerate(lines):
            x_pos = 10 * scale_factor
            current_c = 0
            for char in line:
                char_w_disp = config.get_display_width(char)
                color = color_map.get((r_idx, current_c), "#FFFFFF")
                draw.text((x_pos, y_pos), char, font=font, fill=color)
                
                x_pos += int(char_w_adj * char_w_disp)
                current_c += char_w_disp
                
            y_pos += line_spacing

        if scale_factor > 1:
            final_width = img_width // scale_factor
            final_height = img_height // scale_factor
            img = img.resize((final_width, final_height), Image.Resampling.LANCZOS)

        try:
            img.save(file_path, "PNG")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save image:\n{e}")

    def add_part(self, part_name, x=None, y=None, label_override=None):
        if self.app.is_layer_locked(self.app.app_state.active_layer_id):
            messagebox.showinfo("Info", "現在のアクティブレイヤーはロックされています。")
            return None
        self.commit_inline_edit()
        p_def = config.PARTS_LIBRARY[part_name]
        
        image_path = None
        if part_name == "Image":
            file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
            if not file_path: return None
            
            # 🚨 engine.py を使った輪郭抽出の確認ダイアログ 🚨
            msg = "輪郭を抽出してトレス用の線画にしますか？\n\n[Yes] 輪郭抽出\n[No] そのまま読み込む" if self.app.current_lang == "JP" else "Extract outlines for tracing?\n\n[Yes] Extract Outlines\n[No] Load as is"
            ans = messagebox.askyesnocancel("Image Load", msg)
            if ans is None: return None # キャンセル時は中止
            
            if ans:
                import engine
                try:
                    processed_img = engine.create_guide_image(file_path)
                    # configsフォルダ内に一時保存
                    temp_dir = os.path.join(os.getcwd(), "configs")
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_path = os.path.join(temp_dir, f"outline_{uuid.uuid4().hex[:8]}.png")
                    processed_img.save(temp_path)
                    image_path = temp_path
                except Exception as e:
                    messagebox.showerror("Error", f"輪郭抽出に失敗しました:\n{e}")
                    return None
            else:
                image_path = file_path

            try:
                with Image.open(image_path) as tmp_img:
                    w = max(1, int(tmp_img.width / config.GRID_WIDTH))
                    h = max(1, int(tmp_img.height / config.GRID_HEIGHT))
            except:
                w, h = p_def["default_w"], p_def["default_h"]
        else:
            w, h = p_def["default_w"], p_def["default_h"]

        dl = p_def.get("default_label", "")
        label = label_override if label_override is not None else (dl.get(self.app.current_lang, "") if isinstance(dl, dict) else dl)
        
        if x is None or y is None:
            cx, cy = self.app.ui.canvas.canvasx(100), self.app.ui.canvas.canvasy(100)
            x = max(0, int(cx / (config.GRID_WIDTH * self.scale)) * config.GRID_WIDTH)
            y = max(0, int(cy / (config.GRID_HEIGHT * self.scale)) * config.GRID_HEIGHT)
            
        p_id = str(uuid.uuid4())
        max_z = max([d.get("z_order", 0) for d in self.app.app_state.parts_data.values()] or [0])
        
        self.app.app_state.parts_data[p_id] = {
            "type": part_name,
            "col": int(x / config.GRID_WIDTH),
            "row": int(y / config.GRID_HEIGHT),
            "width": w, "height": h, "label": label, "color": "#FFFFFF",
            "layer_id": self.app.app_state.active_layer_id, "group_id": None, "locked": False, "canvas_items": [],
            "z_order": max_z + 1,
            "image_path": image_path
        }
        self.redraw_part(p_id)
        self.select_item(p_id)
        self.apply_z_order()
        self.app.app_state.save_state()
        return p_id

    def _get_parts_in_layer(self, layer_id):
        parts = [(p_id, d) for p_id, d in self.app.app_state.parts_data.items() if d.get("layer_id") == layer_id]
        parts.sort(key=lambda x: x[1].get("z_order", 0))
        return parts

    def bring_to_front(self, event=None):
        if not self.app.app_state.selected_items: return
        self.commit_inline_edit()
        max_z = max([d.get("z_order", 0) for d in self.app.app_state.parts_data.values()] or [0])
        for p_id in self.app.app_state.selected_items:
            max_z += 1
            self.app.app_state.parts_data[p_id]["z_order"] = max_z
        self.apply_z_order()
        self.app.app_state.save_state()

    def send_to_back(self, event=None):
        if not self.app.app_state.selected_items: return
        self.commit_inline_edit()
        min_z = min([d.get("z_order", 0) for d in self.app.app_state.parts_data.values()] or [0])
        for p_id in self.app.app_state.selected_items:
            min_z -= 1
            self.app.app_state.parts_data[p_id]["z_order"] = min_z
        self.apply_z_order()
        self.app.app_state.save_state()

    def bring_forward(self, event=None):
        if not self.app.app_state.selected_items: return
        self.commit_inline_edit()
        for p_id in self.app.app_state.selected_items:
            layer_id = self.app.app_state.parts_data[p_id].get("layer_id")
            layer_parts = self._get_parts_in_layer(layer_id)
            idx = next((i for i, v in enumerate(layer_parts) if v[0] == p_id), -1)
            if idx != -1 and idx < len(layer_parts) - 1:
                current_z = layer_parts[idx][1].get("z_order", 0)
                next_z = layer_parts[idx+1][1].get("z_order", 0)
                if current_z == next_z: next_z += 1
                layer_parts[idx][1]["z_order"], layer_parts[idx+1][1]["z_order"] = next_z, current_z
        self.apply_z_order()
        self.app.app_state.save_state()

    def send_backward(self, event=None):
        if not self.app.app_state.selected_items: return
        self.commit_inline_edit()
        for p_id in self.app.app_state.selected_items:
            layer_id = self.app.app_state.parts_data[p_id].get("layer_id")
            layer_parts = self._get_parts_in_layer(layer_id)
            idx = next((i for i, v in enumerate(layer_parts) if v[0] == p_id), -1)
            if idx > 0:
                current_z = layer_parts[idx][1].get("z_order", 0)
                prev_z = layer_parts[idx-1][1].get("z_order", 0)
                if current_z == prev_z: prev_z -= 1
                layer_parts[idx][1]["z_order"], layer_parts[idx-1][1]["z_order"] = prev_z, current_z
        self.apply_z_order()
        self.app.app_state.save_state()

    def toggle_part_lock(self):
        if not self.app.app_state.selected_items: return
        self.commit_inline_edit()
        for p_id in self.app.app_state.selected_items:
            current = self.app.app_state.parts_data[p_id].get("locked", False)
            self.app.app_state.parts_data[p_id]["locked"] = not current
            self.redraw_part(p_id, update_preview=False)
        self.update_realtime_preview()
        self.app.app_state.save_state()
        self.app.set_status("Part lock toggled.")

    def show_context_menu(self, event):
        c = self.app.ui.canvas
        cx, cy = c.canvasx(event.x), c.canvasy(event.y)
        items = c.find_overlapping(cx-1, cy-1, cx+1, cy+1)
        
        clicked_part = None
        for item_id in items:
            p_id = self.get_part_id_from_item(item_id)
            if p_id:
                clicked_part = p_id
                break
                
        t = config.UI_TEXT.get(self.app.current_lang, config.UI_TEXT["JP"])
        menu = tk.Menu(self.app, tearoff=0)

        if clicked_part:
            if clicked_part not in self.app.app_state.selected_items:
                self.select_item(clicked_part)
            
            menu.add_command(label=t.get("menu_cut", "Cut"), command=self.cut_action)
            menu.add_command(label=t.get("menu_copy", "Copy"), command=self.app.app_state.copy_action)
            menu.add_command(label=t.get("menu_duplicate", "Duplicate"), command=self.duplicate_action)
            menu.add_command(label=t.get("menu_delete", "Delete"), command=self.delete_selected_parts)
            menu.add_separator()
            lock_label = "配置固定 / 解除" if self.app.current_lang == "JP" else "Lock / Unlock Part"
            menu.add_command(label=lock_label, command=self.toggle_part_lock)
            menu.add_separator()
            menu.add_command(label=t.get("menu_group", "Group"), command=self.app.app_state.group_selected)
            menu.add_command(label=t.get("menu_ungroup", "Ungroup"), command=self.app.app_state.ungroup_selected)
            menu.add_separator()
            menu.add_command(label=t.get("menu_bring_front", "Bring to Front"), command=self.bring_to_front)
            menu.add_command(label=t.get("menu_bring_forward", "Bring Forward"), command=self.bring_forward)
            menu.add_command(label=t.get("menu_send_backward", "Send Backward"), command=self.send_backward)
            menu.add_command(label=t.get("menu_send_back", "Send to Back"), command=self.send_to_back)
        else:
            if self.app.app_state.clipboard:
                menu.add_command(label=t.get("menu_paste", "Paste"), command=self.app.app_state.paste_action)
                menu.add_separator()
            menu.add_command(label="View Reset (100%)", command=self.reset_view_full)
            menu.add_command(label="Focus First Part", command=lambda: self.focus_part("first"))
            menu.add_separator()
            menu.add_command(label=t.get("menu_copy_llm", "LLM用AAコピー"), command=self.app.copy_for_llm)

        menu.post(event.x_root, event.y_root)

    def select_item(self, p_id, add_to_selection=False):
        if not add_to_selection: self.deselect_all()
        
        target_ids = {p_id}
        group_id = self.app.app_state.parts_data[p_id].get("group_id")
        if group_id:
            for pid, data in self.app.app_state.parts_data.items():
                if data.get("group_id") == group_id:
                    target_ids.add(pid)
                    
        for tid in target_ids:
            self.app.app_state.selected_items.add(tid)
            self.redraw_part(tid)
        
        if len(self.app.app_state.selected_items) == 1:
            data = self.app.app_state.parts_data.get(p_id)
            if data:
                self.app.ui.prop_entry_label.delete(0, tk.END)
                self.app.ui.prop_entry_label.insert(0, data["label"])
                self.app.ui.prop_entry_x.delete(0, tk.END)
                self.app.ui.prop_entry_x.insert(0, str(data["col"]))
                self.app.ui.prop_entry_y.delete(0, tk.END)
                self.app.ui.prop_entry_y.insert(0, str(data["row"]))
                self.app.ui.prop_entry_w.delete(0, tk.END)
                self.app.ui.prop_entry_w.insert(0, str(data["width"]))
                self.app.ui.prop_entry_h.delete(0, tk.END)
                self.app.ui.prop_entry_h.insert(0, str(data["height"]))
        else:
            self.app.ui.prop_entry_label.delete(0, tk.END)
            self.app.ui.prop_entry_x.delete(0, tk.END)
            self.app.ui.prop_entry_y.delete(0, tk.END)
            self.app.ui.prop_entry_w.delete(0, tk.END)
            self.app.ui.prop_entry_h.delete(0, tk.END)

    def deselect_all(self):
        old_selected = list(self.app.app_state.selected_items)
        self.app.app_state.selected_items.clear()
        for p_id in old_selected:
            if p_id in self.app.app_state.parts_data:
                self.redraw_part(p_id)
        self.app.ui.prop_entry_label.delete(0, tk.END)
        self.app.ui.prop_entry_x.delete(0, tk.END)
        self.app.ui.prop_entry_y.delete(0, tk.END)
        self.app.ui.prop_entry_w.delete(0, tk.END)
        self.app.ui.prop_entry_h.delete(0, tk.END)
        self._clear_resize_handles()

    def apply_properties(self):
        if len(self.app.app_state.selected_items) != 1: return
        p_id = list(self.app.app_state.selected_items)[0]
        if p_id not in self.app.app_state.parts_data: return
        
        data = self.app.app_state.parts_data[p_id]
        if data.get("locked", False): return
        
        try:
            new_x = int(self.app.ui.prop_entry_x.get() or 0)
            new_y = int(self.app.ui.prop_entry_y.get() or 0)
            new_w = int(self.app.ui.prop_entry_w.get() or 0)
            new_h = int(self.app.ui.prop_entry_h.get() or 0)
        except ValueError: return
        
        data["col"] = max(0, new_x)
        data["row"] = max(0, new_y)
        
        if data["type"] == "Line":
            data["width"] = max(1, new_w)
            data["height"] = 1
        elif data["type"] == "V-Line":
            data["width"] = 1
            data["height"] = max(1, new_h)
        else:
            data["width"] = max(1, new_w)
            data["height"] = max(1, new_h)
            
        data["label"] = self.app.ui.prop_entry_label.get()
        
        self.redraw_part(p_id)
        self.app.app_state.save_state()
        
        self.app.ui.canvas.focus_set()

    def align_parts(self, mode):
        if len(self.app.app_state.selected_items) < 2: return
        self.commit_inline_edit()
        items = [self.app.app_state.parts_data[p_id] for p_id in self.app.app_state.selected_items]
        if mode == "left":
            min_col = min(item["col"] for item in items)
            for p_id in self.app.app_state.selected_items:
                if not self.app.app_state.parts_data[p_id].get("locked", False):
                    self.app.app_state.parts_data[p_id]["col"] = min_col
                    self.redraw_part(p_id)
        elif mode == "top":
            min_row = min(item["row"] for item in items)
            for p_id in self.app.app_state.selected_items:
                if not self.app.app_state.parts_data[p_id].get("locked", False):
                    self.app.app_state.parts_data[p_id]["row"] = min_row
                    self.redraw_part(p_id)
        self.app.app_state.save_state()

    def duplicate_action(self):
        if not self.app.app_state.selected_items: return
        self.commit_inline_edit()
        new_selected = set()
        max_z = max([d.get("z_order", 0) for d in self.app.app_state.parts_data.values()] or [0])
        
        group_map = {}
        for p_id in list(self.app.app_state.selected_items):
            data = self.app.app_state.parts_data[p_id]
            new_p_id = str(uuid.uuid4())
            max_z += 1
            
            old_gid = data.get("group_id")
            new_gid = None
            if old_gid:
                if old_gid not in group_map:
                    group_map[old_gid] = str(uuid.uuid4())
                new_gid = group_map[old_gid]

            self.app.app_state.parts_data[new_p_id] = {
                "type": data["type"], "col": data["col"] + 1, "row": data["row"] + 1,
                "width": data["width"], "height": data["height"], "label": data["label"],
                "color": data["color"], "layer_id": self.app.app_state.active_layer_id, 
                "group_id": new_gid, "locked": False, "canvas_items": [],
                "z_order": max_z,
                "image_path": data.get("image_path")
            }
            self.redraw_part(new_p_id)
            new_selected.add(new_p_id)
            
        self.deselect_all()
        for np_id in new_selected:
            self.select_item(np_id, add_to_selection=True)
        self.apply_z_order()
        self.app.app_state.save_state()

    def move_selected(self, dx, dy):
        if not self.app.app_state.selected_items: return
        self.commit_inline_edit()
        for p_id in self.app.app_state.selected_items:
            if not self.app.app_state.parts_data[p_id].get("locked", False):
                self.app.app_state.parts_data[p_id]["col"] = max(0, self.app.app_state.parts_data[p_id]["col"] + dx)
                self.app.app_state.parts_data[p_id]["row"] = max(0, self.app.app_state.parts_data[p_id]["row"] + dy)
                self.redraw_part(p_id)
        self.app.app_state.save_state()

    def delete_selected_parts(self):
        focused = self.app.focus_get()
        if isinstance(focused, (tk.Entry, ctk.CTkEntry)): return
        if self.is_editing_inline or not self.app.app_state.selected_items: return
        deleted = False
        
        safe_items = []
        for p in self.app.app_state.selected_items:
            part_data = self.app.app_state.parts_data.get(p)
            if p in self.app.app_state.parts_data:
                # 🚨 パーツの親レイヤーがロックされているか厳密に判定 🚨
                layer_id = self.app.app_state.parts_data[p].get("layer_id")
                is_layer_locked = self.app.is_layer_locked(layer_id)
                is_part_locked = self.app.app_state.parts_data[p].get("locked", False)
                
                if not is_layer_locked and not is_part_locked:
                    safe_items.append(p)
        
        for p_id in safe_items:
            self.app.ui.canvas.delete(p_id)
            del self.app.app_state.parts_data[p_id]
            deleted = True
            
        self.deselect_all()
        if deleted:
            self.app.app_state.save_state()
            self.app.set_status("Part(s) deleted.")
        elif self.app.app_state.selected_items:
            self.app.set_status("Cannot delete: Part or Layer is locked.")

    def cut_action(self):
        self.app.app_state.copy_action()
        self.delete_selected_parts()

    def on_escape(self, event):
        if self.is_editing_inline:
            self.cancel_inline_edit()
        else:
            self.deselect_all()
            if self.marquee_id is not None:
                self.app.ui.canvas.delete(self.marquee_id)
                self.marquee_id = None
            self.app.set_status("Selection cleared.")

    def start_inline_edit(self, p_id):
        self.commit_inline_edit()
        self.is_editing_inline = True
        self.editing_item_id = p_id
        self.select_item(p_id)
        
        gw = config.GRID_WIDTH * self.scale
        gh = config.GRID_HEIGHT * self.scale
        x = self.app.app_state.parts_data[p_id]["col"] * gw
        y = self.app.app_state.parts_data[p_id]["row"] * gh
        
        current_label = self.app.app_state.parts_data[p_id]["label"]
        font_size = max(8, int(12 * self.scale))
        self.inline_entry = tk.Entry(self.app.ui.canvas, font=("Arial", font_size), bg="#333333", fg="#FFFFFF", insertbackground="white")
        self.inline_entry.insert(0, current_label)
        self.inline_window_id = self.app.ui.canvas.create_window(x, y, window=self.inline_entry, anchor="nw")
        self.inline_entry.focus_set()
        self.inline_entry.bind("<Return>", lambda e: self.commit_inline_edit())
        self.inline_entry.bind("<FocusOut>", lambda e: self.commit_inline_edit())

    def commit_inline_edit(self):
        if not self.is_editing_inline: return
        self.is_editing_inline = False
        new_text = self.inline_entry.get() if self.inline_entry else ""
        if self.inline_entry: self.inline_entry.destroy(); self.inline_entry = None
        if self.inline_window_id: self.app.ui.canvas.delete(self.inline_window_id); self.inline_window_id = None
        p_id = self.editing_item_id
        if p_id and p_id in self.app.app_state.parts_data:
            if not new_text.strip() and self.app.app_state.parts_data[p_id]["type"] == "Text":
                self.app.ui.canvas.delete(p_id)
                del self.app.app_state.parts_data[p_id]
                self.deselect_all()
            else:
                self.app.app_state.parts_data[p_id]["label"] = new_text
                if len(self.app.app_state.selected_items) == 1 and p_id in self.app.app_state.selected_items:
                    self.app.ui.prop_entry_label.delete(0, tk.END)
                    self.app.ui.prop_entry_label.insert(0, new_text)
                self.redraw_part(p_id)
        self.editing_item_id = None
        self.app.app_state.save_state()
        
        self.app.ui.canvas.focus_set()

    def cancel_inline_edit(self):
        if not self.is_editing_inline: return
        self.is_editing_inline = False
        if self.inline_window_id: self.app.ui.canvas.delete(self.inline_window_id); self.inline_window_id = None
        if self.inline_entry: self.inline_entry.destroy(); self.inline_entry = None
        p_id = self.editing_item_id
        if p_id and p_id in self.app.app_state.parts_data:
            label = self.app.app_state.parts_data[p_id]["label"]
            if not label.strip() and self.app.app_state.parts_data[p_id]["type"] == "Text":
                self.app.ui.canvas.delete(p_id)
                del self.app.app_state.parts_data[p_id]
        self.editing_item_id = None
        self.deselect_all()
        self.app.set_status("Input canceled.")
        
        self.app.ui.canvas.focus_set()

    def on_press(self, event):
        self.commit_inline_edit()
        c = self.app.ui.canvas
        cx, cy = c.canvasx(event.x), c.canvasy(event.y)

        tool = self.app.ui.tool_var.get()
        if tool in ["Select", "選択モード"]:
            item = c.find_withtag("current")
            if item:
                tags = c.gettags(item[0])
                            
                if "resize_handle_nw" in tags:
                    self.drag_data.update({"mode": "resize", "corner": "nw", "item": list(self.app.app_state.selected_items)[0]})
                    return
                elif "resize_handle_ne" in tags:
                    self.drag_data.update({"mode": "resize", "corner": "ne", "item": list(self.app.app_state.selected_items)[0]})
                    return
                elif "resize_handle_sw" in tags:
                    self.drag_data.update({"mode": "resize", "corner": "sw", "item": list(self.app.app_state.selected_items)[0]})
                    return
                elif "resize_handle_se" in tags or "resize_handle" in tags:
                    self.drag_data.update({"mode": "resize", "corner": "se", "item": list(self.app.app_state.selected_items)[0]})
                    return
                
                if "draggable" in tags:
                    p_id = self.get_part_id_from_item(item[0])
                    if p_id:
                        if p_id not in self.app.app_state.selected_items: 
                            self.select_item(p_id)
                            
                        self._clear_resize_handles()
                        self.drag_data.update({"mode": "move", "x": cx, "y": cy})
                        return

            self.deselect_all()
            self.drag_data["mode"] = None

        elif tool in ["Text", "テキスト"]:
            self.deselect_all()
            gw = config.GRID_WIDTH * self.scale
            gh = config.GRID_HEIGHT * self.scale
            col = max(0, round(cx / gw))
            row = max(0, round(cy / gh))
            sx_unscaled = col * config.GRID_WIDTH
            sy_unscaled = row * config.GRID_HEIGHT
            p_id = self.add_part("Text", sx_unscaled, sy_unscaled, label_override="")
            if p_id: self.start_inline_edit(p_id)

        elif tool in ["Marquee", "範囲選択"]:
            self.deselect_all()
            self.drag_data.update({"start_x": cx, "start_y": cy})
            if self.marquee_id: c.delete(self.marquee_id)
            self.marquee_id = c.create_rectangle(cx, cy, cx, cy, outline="white", dash=(4, 4))

    def on_drag(self, event):
        c = self.app.ui.canvas
        cx, cy = c.canvasx(event.x), c.canvasy(event.y)

        tool = self.app.ui.tool_var.get()
        if tool in ["Select", "選択モード"]:
            gw = config.GRID_WIDTH * self.scale
            gh = config.GRID_HEIGHT * self.scale
            
            if self.drag_data.get("mode") == "resize" and self.drag_data.get("item"):
                p_id = self.drag_data["item"]
                corner = self.drag_data.get("corner", "se")
                data = self.app.app_state.parts_data[p_id]
                
                if data.get("locked", False):
                    return
                
                original_col = data["col"]
                original_row = data["row"]
                original_w = data["width"]
                original_h = data["height"]
                
                new_col = original_col
                new_row = original_row
                new_w = original_w
                new_h = original_h
                
                if corner == "se":
                    new_w = max(3, round((cx - (original_col * gw)) / gw))
                    new_h = max(1, round((cy - (original_row * gh)) / gh))
                elif corner == "sw":
                    new_col = max(0, round(cx / gw))
                    delta_col = original_col - new_col
                    new_w = max(3, original_w + delta_col)
                    if new_w > 3:
                        new_col = original_col - (new_w - original_w)
                    new_h = max(1, round((cy - (original_row * gh)) / gh))
                elif corner == "ne":
                    new_w = max(3, round((cx - (original_col * gw)) / gw))
                    new_row = max(0, round(cy / gh))
                    delta_row = original_row - new_row
                    new_h = max(1, original_h + delta_row)
                    if new_h > 1:
                        new_row = original_row - (new_h - original_h)
                elif corner == "nw":
                    new_col = max(0, round(cx / gw))
                    delta_col = original_col - new_col
                    new_w = max(3, original_w + delta_col)
                    if new_w > 3:
                        new_col = original_col - (new_w - original_w)
                    new_row = max(0, round(cy / gh))
                    delta_row = original_row - new_row
                    new_h = max(1, original_h + delta_row)
                    if new_h > 1:
                        new_row = original_row - (new_h - original_h)

                if data["type"] == "Line":
                    new_h = 1
                    if corner in ["nw", "ne"]: new_row = original_row
                elif data["type"] == "V-Line":
                    new_w = 1
                    if corner in ["nw", "sw"]: new_col = original_col

                data["col"] = new_col
                data["row"] = new_row
                data["width"] = max(1, new_w)
                data["height"] = max(1, new_h)

                self.app.ui.prop_entry_w.delete(0, tk.END); self.app.ui.prop_entry_w.insert(0, str(data["width"]))
                self.app.ui.prop_entry_h.delete(0, tk.END); self.app.ui.prop_entry_h.insert(0, str(data["height"]))
                self.app.ui.prop_entry_x.delete(0, tk.END); self.app.ui.prop_entry_x.insert(0, str(data["col"]))
                self.app.ui.prop_entry_y.delete(0, tk.END); self.app.ui.prop_entry_y.insert(0, str(data["row"]))
                
                self.redraw_part(p_id, update_preview=False)
                
            elif self.drag_data.get("mode") == "move" and self.app.app_state.selected_items:
                dx = cx - self.drag_data["x"]
                dy = cy - self.drag_data["y"]
                
                for p_id in self.app.app_state.selected_items:
                    if self.app.app_state.parts_data[p_id].get("locked", False):
                        continue
                    for item in self.app.app_state.parts_data[p_id].get("canvas_items", []):
                        c.move(item, dx, dy)
                        
                self.drag_data["x"] = cx
                self.drag_data["y"] = cy

        elif tool in ["Marquee", "範囲選択"] and self.marquee_id:
            c.coords(self.marquee_id, self.drag_data["start_x"], self.drag_data["start_y"], cx, cy)

    def on_release(self, event):
        c = self.app.ui.canvas
        tool = self.app.ui.tool_var.get()
        gw = config.GRID_WIDTH * self.scale
        gh = config.GRID_HEIGHT * self.scale
        
        if tool in ["Select", "選択モード"]:
            if self.drag_data.get("mode") in ["move", "resize"] and self.app.app_state.selected_items:
                if self.drag_data.get("mode") == "move":
                    for p_id in self.app.app_state.selected_items:
                        if self.app.app_state.parts_data[p_id].get("locked", False):
                            continue
                        items = self.app.app_state.parts_data[p_id].get("canvas_items", [])
                        if items:
                            coords = c.coords(items[0])
                            new_col = max(0, round(coords[0] / gw))
                            new_row = max(0, round(coords[1] / gh))
                            self.app.app_state.parts_data[p_id]["col"] = new_col
                            self.app.app_state.parts_data[p_id]["row"] = new_row
                        self.redraw_part(p_id, update_preview=False)

                self.update_realtime_preview()
                self.app.app_state.save_state()
                
                if len(self.app.app_state.selected_items) == 1:
                    p_id = list(self.app.app_state.selected_items)[0]
                    data = self.app.app_state.parts_data[p_id]
                    self.app.ui.prop_entry_x.delete(0, tk.END); self.app.ui.prop_entry_x.insert(0, str(data["col"]))
                    self.app.ui.prop_entry_y.delete(0, tk.END); self.app.ui.prop_entry_y.insert(0, str(data["row"]))
                    self.app.ui.prop_entry_w.delete(0, tk.END); self.app.ui.prop_entry_w.insert(0, str(data["width"]))
                    self.app.ui.prop_entry_h.delete(0, tk.END); self.app.ui.prop_entry_h.insert(0, str(data["height"]))
                    
            self.drag_data["mode"] = None

        elif tool in ["Marquee", "範囲選択"] and self.marquee_id:
            x1, y1, x2, y2 = c.coords(self.marquee_id)
            c.delete(self.marquee_id); self.marquee_id = None
            items = c.find_overlapping(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            for item_id in items:
                if "draggable" in c.gettags(item_id):
                    p_id = self.get_part_id_from_item(item_id)
                    if p_id:
                        self.select_item(p_id, add_to_selection=True)
            
            t = config.UI_TEXT.get(self.app.current_lang, config.UI_TEXT["JP"])
            select_text = str(t.get("tool_select", "Select"))
            self.app.ui.tool_var.set(select_text)
            self.app.ui.tool_seg.set(select_text)
            self.app.ui.on_tool_change(select_text)

    def on_double_click(self, event):
        tool = self.app.ui.tool_var.get()
        if tool in ["Select", "選択モード"]:
            item = self.app.ui.canvas.find_withtag("current")
            if item and "draggable" in self.app.ui.canvas.gettags(item[0]):
                p_id = self.get_part_id_from_item(item[0])
                if p_id:
                    self.start_inline_edit(p_id)