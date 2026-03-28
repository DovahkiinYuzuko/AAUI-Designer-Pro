"""
AAUI Designer Pro のUI構築・管理モジュール。
メインフレーム、スプリッター（PanedWindow）、ツールパネル、キャンバス領域等のGUIレイアウトを担う.
"""

import tkinter as tk
from tkinter import colorchooser, simpledialog
import customtkinter as ctk
import config

class UIManager:
    def __init__(self, app):
        self.app = app
        self.tool_var = ctk.StringVar(value="Select")
        self.setup_ui()

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self.app, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True)

        self.left_pane = ctk.CTkFrame(self.main_frame, width=320, corner_radius=0)
        self.left_pane.pack(side="left", fill="y", padx=5, pady=5)
        self.left_pane.pack_propagate(False)

        self.tool_seg = ctk.CTkSegmentedButton(
            self.left_pane,
            values=["Select", "Text", "Marquee"],
            variable=self.tool_var,
            command=self.on_tool_change
        )
        self.tool_seg.pack(fill="x", padx=5, pady=(5, 10))

        self.scroll_container = ctk.CTkFrame(self.left_pane, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True)

        self.index_frame = ctk.CTkFrame(self.scroll_container, width=50, corner_radius=0)
        self.index_frame.pack(side="left", fill="y", padx=(0, 5))
        
        self.btn_idx_parts = ctk.CTkButton(self.index_frame, text="PRT", width=40, command=lambda: self.scroll_to_section(self.lbl_parts))
        self.btn_idx_parts.pack(pady=5, padx=2)
        self.btn_idx_props = ctk.CTkButton(self.index_frame, text="PRP", width=40, command=lambda: self.scroll_to_section(self.lbl_props))
        self.btn_idx_props.pack(pady=5, padx=2)
        self.btn_idx_sys = ctk.CTkButton(self.index_frame, text="SYS", width=40, command=lambda: self.scroll_to_section(self.lbl_sys))
        self.btn_idx_sys.pack(pady=5, padx=2)

        self.content_scroll = ctk.CTkScrollableFrame(self.scroll_container)
        self.content_scroll.pack(side="left", fill="both", expand=True)

        self.lbl_parts = ctk.CTkLabel(self.content_scroll, text="PARTS", font=("Arial", 14, "bold"))
        self.lbl_parts.pack(pady=(10, 5), anchor="w", padx=10)
        for p_name in config.PARTS_LIBRARY.keys():
            btn = ctk.CTkButton(self.content_scroll, text=p_name, command=lambda n=p_name: self.app.canvas_mgr.add_part(n))
            btn.pack(fill="x", padx=10, pady=4)

        self.lbl_props = ctk.CTkLabel(self.content_scroll, text="PROPERTIES", font=("Arial", 14, "bold"))
        self.lbl_props.pack(pady=(20, 5), anchor="w", padx=10)
        
        self.lbl_prop_label = ctk.CTkLabel(self.content_scroll, text="Label:", anchor="w")
        self.lbl_prop_label.pack(fill="x", padx=10)
        self.prop_entry_label = ctk.CTkEntry(self.content_scroll)
        self.prop_entry_label.pack(fill="x", padx=10, pady=2)
        self.prop_entry_label.bind("<Return>", lambda e: self.app.canvas_mgr.apply_properties())

        self.lbl_prop_pos = ctk.CTkLabel(self.content_scroll, text="Position (X/Y):", anchor="w")
        self.lbl_prop_pos.pack(fill="x", padx=10)
        pos_frame = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        pos_frame.pack(fill="x", padx=10, pady=2)
        self.prop_entry_x = ctk.CTkEntry(pos_frame, width=60)
        self.prop_entry_x.pack(side="left", padx=(0, 5))
        self.prop_entry_x.bind("<Return>", lambda e: self.app.canvas_mgr.apply_properties())
        self.prop_entry_y = ctk.CTkEntry(pos_frame, width=60)
        self.prop_entry_y.pack(side="left")
        self.prop_entry_y.bind("<Return>", lambda e: self.app.canvas_mgr.apply_properties())

        self.lbl_prop_size = ctk.CTkLabel(self.content_scroll, text="Width / Height:", anchor="w")
        self.lbl_prop_size.pack(fill="x", padx=10)
        size_frame = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        size_frame.pack(fill="x", padx=10, pady=2)
        self.prop_entry_w = ctk.CTkEntry(size_frame, width=60)
        self.prop_entry_w.pack(side="left", padx=(0, 5))
        self.prop_entry_w.bind("<Return>", lambda e: self.app.canvas_mgr.apply_properties())
        self.prop_entry_h = ctk.CTkEntry(size_frame, width=60)
        self.prop_entry_h.pack(side="left")
        self.prop_entry_h.bind("<Return>", lambda e: self.app.canvas_mgr.apply_properties())

        self.prop_apply_btn = ctk.CTkButton(self.content_scroll, text="Apply Changes", command=lambda: self.app.canvas_mgr.apply_properties())
        self.prop_apply_btn.pack(fill="x", padx=10, pady=10)

        align_frame = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        align_frame.pack(fill="x", padx=10, pady=5)
        self.align_left_btn = ctk.CTkButton(align_frame, text="Align Left", width=80, command=lambda: self.app.canvas_mgr.align_parts("left"))
        self.align_left_btn.pack(side="left", padx=(0, 5))
        self.align_top_btn = ctk.CTkButton(align_frame, text="Align Top", width=80, command=lambda: self.app.canvas_mgr.align_parts("top"))
        self.align_top_btn.pack(side="left")

        self.lock_btn = ctk.CTkButton(self.content_scroll, text="配置固定 / 解除", fg_color="#f39c12", hover_color="#e67e22", command=lambda: self.app.canvas_mgr.toggle_part_lock())
        self.lock_btn.pack(fill="x", padx=10, pady=5)

        self.color_btn = ctk.CTkButton(self.content_scroll, text="Choose Color", fg_color="#8E44AD", hover_color="#9B59B6", command=self.choose_color)
        self.color_btn.pack(fill="x", padx=10, pady=5)

        self.delete_btn = ctk.CTkButton(self.content_scroll, text="Delete Part(s)", fg_color="#c0392b", hover_color="#e74c3c", command=lambda: self.app.canvas_mgr.delete_selected_parts())
        self.delete_btn.pack(fill="x", padx=10, pady=5)

        self.lbl_sys = ctk.CTkLabel(self.content_scroll, text="SYSTEM", font=("Arial", 14, "bold"))
        self.lbl_sys.pack(pady=(20, 5), anchor="w", padx=10)
        
        self.btn_lang_switch = ctk.CTkButton(self.content_scroll, text="Switch to English", command=self.app.switch_language)
        self.btn_lang_switch.pack(fill="x", padx=10, pady=5)
        
        self.btn_bg_color = ctk.CTkButton(self.content_scroll, text="Change Background Color...", command=self.app.change_bg_color)
        self.btn_bg_color.pack(fill="x", padx=10, pady=5)
        
        self.lbl_font_select = ctk.CTkLabel(self.content_scroll, text="Export Font:", anchor="w")
        self.lbl_font_select.pack(fill="x", padx=10)
        
        font_names = list(self.app.available_fonts.keys())
        default_val = ""
        for name in font_names:
            if "msgothic" in name.lower():
                default_val = name
                break
        if not default_val and font_names:
            default_val = font_names[0]
            
        self.font_var = ctk.StringVar(value=default_val)
        self.font_dropdown = ctk.CTkComboBox(self.content_scroll, values=font_names, variable=self.font_var, command=self.on_font_change)
        self.font_dropdown.pack(fill="x", padx=10, pady=5)
        
        self.btn_edit_shortcuts = ctk.CTkButton(self.content_scroll, text="Edit Shortcuts...", command=self.app.open_shortcut_editor)
        self.btn_edit_shortcuts.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.content_scroll, text="Grid Size:", anchor="w").pack(fill="x", padx=10)
        grid_frame = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10)
        self.grid_w_entry = ctk.CTkEntry(grid_frame, width=50)
        self.grid_w_entry.insert(0, str(config.GRID_WIDTH))
        self.grid_w_entry.pack(side="left", padx=(0, 5))
        self.grid_h_entry = ctk.CTkEntry(grid_frame, width=50)
        self.grid_h_entry.insert(0, str(config.GRID_HEIGHT))
        self.grid_h_entry.pack(side="left")
        
        self.grid_apply_btn = ctk.CTkButton(self.content_scroll, text="Apply Grid", command=self.apply_grid_size)
        self.grid_apply_btn.pack(fill="x", padx=10, pady=(10, 30))

        self.layer_mgr_frame = ctk.CTkFrame(self.left_pane, height=280)
        self.layer_mgr_frame.pack(side="bottom", fill="x", pady=(5, 0))
        self.layer_mgr_frame.pack_propagate(False)

        layer_header_frame = ctk.CTkFrame(self.layer_mgr_frame, fg_color="transparent")
        layer_header_frame.pack(fill="x", padx=10, pady=2)
        
        self.lbl_layer_title = ctk.CTkLabel(layer_header_frame, text="LAYER MANAGER", font=("Arial", 12, "bold"))
        self.lbl_layer_title.pack(side="left")
        
        self.btn_layer_add = ctk.CTkButton(layer_header_frame, text="+", width=30, height=24, command=lambda: self.app.layer_add())
        self.btn_layer_add.pack(side="right", padx=(2, 0))
        self.btn_layer_del = ctk.CTkButton(layer_header_frame, text="-", width=30, height=24, fg_color="#c0392b", hover_color="#e74c3c", command=lambda: self.app.layer_delete())
        self.btn_layer_del.pack(side="right", padx=(2, 0))

        self.layer_list_frame = ctk.CTkScrollableFrame(self.layer_mgr_frame, height=100, fg_color="#2b2b2b")
        self.layer_list_frame.pack(fill="x", padx=10, pady=2)
        
        lbl_layer_opacity = ctk.CTkLabel(self.layer_mgr_frame, text="Layer Opacity:", font=("Arial", 10))
        lbl_layer_opacity.pack(anchor="w", padx=10, pady=(5, 0))
        
        self.layer_opacity_slider = ctk.CTkSlider(self.layer_mgr_frame, from_=10, to=100, command=self.on_layer_opacity_change)
        self.layer_opacity_slider.set(100)
        self.layer_opacity_slider.pack(fill="x", padx=10, pady=(0, 5))

        btn_frame2 = ctk.CTkFrame(self.layer_mgr_frame, fg_color="transparent")
        btn_frame2.pack(fill="x", padx=5, pady=2)
        self.btn_layer_merge = ctk.CTkButton(btn_frame2, text="Merge Down", width=90, command=lambda: self.app.layer_merge_down())
        self.btn_layer_merge.pack(side="left", expand=True, padx=2)
        self.btn_layer_rename = ctk.CTkButton(btn_frame2, text="Rename", width=90, command=self.on_layer_rename_btn)
        self.btn_layer_rename.pack(side="left", expand=True, padx=2)

        self.paned_window = tk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL, bg="#2b2b2b", sashwidth=6, relief="flat")
        self.paned_window.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.editor_container = ctk.CTkFrame(self.paned_window, corner_radius=0, fg_color="transparent")
        self.paned_window.add(self.editor_container, minsize=400)
        
        self.editor_container.rowconfigure(1, weight=1)
        self.editor_container.columnconfigure(1, weight=1)

        self.top_ruler = tk.Canvas(self.editor_container, bg="#2b2b2b", height=20, highlightthickness=0)
        self.top_ruler.grid(row=0, column=1, sticky="ew")

        self.left_ruler = tk.Canvas(self.editor_container, bg="#2b2b2b", width=30, highlightthickness=0)
        self.left_ruler.grid(row=1, column=0, sticky="ns")

        self.canvas = tk.Canvas(self.editor_container, bg=self.app.app_state.bg_color, cursor="arrow", highlightthickness=0)
        self.canvas.grid(row=1, column=1, sticky="nsew")

        self.v_scroll = ctk.CTkScrollbar(self.editor_container, orientation="vertical", command=self.sync_y_view)
        self.v_scroll.grid(row=1, column=2, sticky="ns")

        self.h_scroll = ctk.CTkScrollbar(self.editor_container, orientation="horizontal", command=self.sync_x_view)
        self.h_scroll.grid(row=2, column=1, sticky="ew")

        self.canvas.configure(yscrollcommand=self.sync_y_set, xscrollcommand=self.sync_x_set, scrollregion=(0, 0, 4000, 4000))
        self.top_ruler.configure(scrollregion=(0, 0, 4000, 20))
        self.left_ruler.configure(scrollregion=(0, 0, 30, 4000))

        self.preview_container = ctk.CTkFrame(self.paned_window, corner_radius=0, fg_color="#1e1e1e")
        self.paned_window.add(self.preview_container, minsize=300)
        
        self.lbl_rt_preview = ctk.CTkLabel(self.preview_container, text="REAL-TIME PREVIEW", font=("Arial", 14, "bold"), fg_color="#2b2b2b", corner_radius=0)
        self.lbl_rt_preview.pack(fill="x")

        preview_scroll_frame = ctk.CTkFrame(self.preview_container, corner_radius=0, fg_color="transparent")
        preview_scroll_frame.pack(fill="both", expand=True)
        preview_scroll_frame.rowconfigure(0, weight=1)
        preview_scroll_frame.columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(preview_scroll_frame, bg="#1e1e1e", highlightthickness=0)
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        
        self.preview_v_scroll = ctk.CTkScrollbar(preview_scroll_frame, orientation="vertical", command=self.preview_canvas.yview)
        self.preview_v_scroll.grid(row=0, column=1, sticky="ns")
        self.preview_h_scroll = ctk.CTkScrollbar(preview_scroll_frame, orientation="horizontal", command=self.preview_canvas.xview)
        self.preview_h_scroll.grid(row=1, column=0, sticky="ew")
        
        self.preview_canvas.configure(yscrollcommand=self.preview_v_scroll.set, xscrollcommand=self.preview_h_scroll.set, scrollregion=(0, 0, 2000, 2000))

        self.control_frame = ctk.CTkFrame(self.app, height=30, corner_radius=0)
        self.control_frame.pack(side="bottom", fill="x")

        self.status_label = ctk.CTkLabel(self.control_frame, text="Ready...")
        self.status_label.pack(side="left", padx=20)

    def on_font_change(self, value):
        self.app.current_export_font = self.app.available_fonts.get(value, "")

    def on_layer_opacity_change(self, val):
        layer_id = self.app.app_state.active_layer_id
        for lyr in self.app.app_state.layers:
            if lyr["id"] == layer_id:
                lyr["opacity"] = float(val) / 100.0
                break
        if hasattr(self.app, 'canvas_mgr'):
            self.app.canvas_mgr.redraw_all()

    def sync_y_set(self, *args):
        self.v_scroll.set(*args)
        self.left_ruler.yview_moveto(args[0])

    def sync_y_view(self, *args):
        self.canvas.yview(*args)
        self.left_ruler.yview(*args)

    def sync_x_set(self, *args):
        self.h_scroll.set(*args)
        self.top_ruler.xview_moveto(args[0])

    def sync_x_view(self, *args):
        self.canvas.xview(*args)
        self.top_ruler.xview(*args)

    def scroll_to_section(self, widget):
        self.content_scroll._parent_canvas.yview_moveto(widget.winfo_y() / self.content_scroll.winfo_reqheight())

    def on_tool_change(self, value):
        self.canvas.focus_set()
        if value in ["Text", "テキスト"]:
            self.canvas.config(cursor="xterm")
            if hasattr(self.app, 'canvas_mgr'): self.app.canvas_mgr.deselect_all()
        elif value in ["Marquee", "範囲選択"]:
            self.canvas.config(cursor="crosshair")
            if hasattr(self.app, 'canvas_mgr'): self.app.canvas_mgr.deselect_all()
        else:
            self.canvas.config(cursor="arrow")

    def sync_grid_entries(self):
        self.grid_w_entry.delete(0, tk.END)
        self.grid_w_entry.insert(0, str(config.GRID_WIDTH))
        self.grid_h_entry.delete(0, tk.END)
        self.grid_h_entry.insert(0, str(config.GRID_HEIGHT))

    def apply_grid_size(self):
        try:
            new_w = int(self.grid_w_entry.get())
            new_h = int(self.grid_h_entry.get())
            if new_w > 0 and new_h > 0:
                config.GRID_WIDTH = new_w
                config.GRID_HEIGHT = new_h
                self.app.canvas_mgr.draw_rulers_and_grid()
                for p_id in self.app.app_state.parts_data.keys():
                    self.app.canvas_mgr.redraw_part(p_id)
                self.canvas.focus_set()
        except ValueError:
            pass

    def choose_color(self):
        if len(self.app.app_state.selected_items) == 1:
            p_id = list(self.app.app_state.selected_items)[0]
            current = self.app.app_state.parts_data[p_id].get("color", "#FFFFFF")
            color_code = colorchooser.askcolor(title="Choose Color", initialcolor=current)[1]
            if color_code:
                self.app.app_state.parts_data[p_id]["color"] = color_code
                self.app.canvas_mgr.redraw_part(p_id)
                self.app.app_state.save_state()
                self.app.set_status(f"Color changed to {color_code}")
                self.canvas.focus_set()

    def update_resize_handle(self):
        if self.app.canvas_mgr.resize_handle_id is not None:
            self.canvas.delete(self.app.canvas_mgr.resize_handle_id)
            self.app.canvas_mgr.resize_handle_id = None
        if len(self.app.app_state.selected_items) == 1:
            p_id = list(self.app.app_state.selected_items)[0]
            bbox = self.app.canvas_mgr.get_part_bbox(p_id)
            if bbox:
                x2, y2 = bbox[2], bbox[3]
                self.app.canvas_mgr.resize_handle_id = self.canvas.create_rectangle(
                    x2 - 8, y2 - 8, x2, y2, fill="#e74c3c", outline="white", tags="resize_handle"
                )

    def on_layer_double_click(self, event, layer_id):
        self.app.set_active_layer(layer_id)
        self.rename_layer_dialog(layer_id)
        
    def on_layer_right_click(self, event, layer_id):
        self.app.set_active_layer(layer_id)
        menu = tk.Menu(self.main_frame, tearoff=0)
        t = config.UI_TEXT.get(self.app.current_lang, config.UI_TEXT["JP"])
        menu.add_command(label=t.get("layer_rename", "Rename"), command=lambda: self.app.rename_specific_layer(layer_id))
        menu.add_command(label=t.get("layer_lock", "Lock"), command=lambda: self.app.toggle_specific_layer_lock(layer_id))
        menu.add_command(label=t.get("layer_del", "Delete"), command=lambda: self.app.layer_delete())
        menu.post(event.x_root, event.y_root)

    def on_layer_rename_btn(self):
        self.rename_layer_dialog(self.app.app_state.active_layer_id)

    def rename_layer_dialog(self, layer_id):
        for lyr in self.app.app_state.layers:
            if lyr["id"] == layer_id:
                title = "レイヤー名の変更" if self.app.current_lang == "JP" else "Rename Layer"
                prompt = "新しいレイヤー名:" if self.app.current_lang == "JP" else "New Layer Name:"
                
                new_name = simpledialog.askstring(title, prompt, initialvalue=lyr["name"])
                
                if new_name and new_name.strip() and new_name != lyr["name"]:
                    lyr["name"] = new_name.strip()
                    self.update_layer_ui()
                    self.app.app_state.save_state()
                    self.app.set_status(f"Layer renamed to '{lyr['name']}'")
                break

    def update_layer_ui(self):
        for widget in self.layer_list_frame.winfo_children():
            widget.destroy()
            
        for i, lyr in enumerate(reversed(self.app.app_state.layers)): 
            bg_color = "#3498db" if lyr["id"] == self.app.app_state.active_layer_id else "transparent"
            row_frame = ctk.CTkFrame(self.layer_list_frame, fg_color=bg_color, corner_radius=0)
            row_frame.pack(fill="x", pady=1)

            is_visible = lyr.get("visible", True)
            icon_vis = self.app.icon_visible if is_visible else self.app.icon_invisible
            if icon_vis:
                btn_vis = ctk.CTkButton(row_frame, image=icon_vis, text="", width=24, height=24, fg_color="transparent",
                                         command=lambda l_id=lyr["id"]: self.app.toggle_layer_visibility(l_id))
            else:
                vis_text = "[O]" if is_visible else "[X]"
                btn_vis = ctk.CTkButton(row_frame, text=vis_text, width=30, height=24, fg_color="transparent",
                                         command=lambda l_id=lyr["id"]: self.app.toggle_layer_visibility(l_id))
            btn_vis.pack(side="left", padx=2)
            
            icon = self.app.icon_lock if lyr["locked"] else self.app.icon_unlock
            if icon:
                btn_lock = ctk.CTkButton(row_frame, image=icon, text="", width=24, height=24, fg_color="transparent",
                                         command=lambda l_id=lyr["id"]: self.app.toggle_specific_layer_lock(l_id))
            else:
                lock_text = "[FIX]" if lyr["locked"] else "[   ]"
                btn_lock = ctk.CTkButton(row_frame, text=lock_text, width=30, height=24, fg_color="transparent",
                                         command=lambda l_id=lyr["id"]: self.app.toggle_specific_layer_lock(l_id))
            btn_lock.pack(side="left", padx=2)
            
            lbl_name = ctk.CTkLabel(row_frame, text=lyr["name"], anchor="w", cursor="hand2")
            lbl_name.pack(side="left", fill="x", expand=True, padx=5)

            if hasattr(self.app, 'icon_layer_dn') and self.app.icon_layer_dn:
                btn_dn = ctk.CTkButton(row_frame, image=self.app.icon_layer_dn, text="", width=24, height=24, fg_color="transparent",
                                       command=lambda l_id=lyr["id"]: (self.app.set_active_layer(l_id), self.app.layer_move_down()))
            else:
                btn_dn = ctk.CTkButton(row_frame, text="↓", width=24, height=24, fg_color="transparent",
                                       command=lambda l_id=lyr["id"]: (self.app.set_active_layer(l_id), self.app.layer_move_down()))
            btn_dn.pack(side="right", padx=1)

            if hasattr(self.app, 'icon_layer_up') and self.app.icon_layer_up:
                btn_up = ctk.CTkButton(row_frame, image=self.app.icon_layer_up, text="", width=24, height=24, fg_color="transparent",
                                       command=lambda l_id=lyr["id"]: (self.app.set_active_layer(l_id), self.app.layer_move_up()))
            else:
                btn_up = ctk.CTkButton(row_frame, text="↑", width=24, height=24, fg_color="transparent",
                                       command=lambda l_id=lyr["id"]: (self.app.set_active_layer(l_id), self.app.layer_move_up()))
            btn_up.pack(side="right", padx=1)
            
            lbl_name.bind("<Button-1>", lambda e, l_id=lyr["id"]: self.app.set_active_layer(l_id))
            row_frame.bind("<Button-1>", lambda e, l_id=lyr["id"]: self.app.set_active_layer(l_id))
            
            lbl_name.bind("<Double-Button-1>", lambda e, l_id=lyr["id"]: self.on_layer_double_click(e, l_id))
            lbl_name.bind("<Button-3>", lambda e, l_id=lyr["id"]: self.on_layer_right_click(e, l_id))
            row_frame.bind("<Button-3>", lambda e, l_id=lyr["id"]: self.on_layer_right_click(e, l_id))
            
        active_lyr = next((l for l in self.app.app_state.layers if l["id"] == self.app.app_state.active_layer_id), None)
        if active_lyr:
            self.layer_opacity_slider.set(int(active_lyr.get("opacity", 1.0) * 100))

    def update_ui_text(self):
        t = config.UI_TEXT.get(self.app.current_lang, config.UI_TEXT["JP"])
        
        current_tool = self.tool_var.get()
        self.tool_seg.configure(values=[str(t.get("tool_select", "Select")), str(t.get("tool_text", "Text")), str(t.get("tool_rect", "Marquee"))])
        if current_tool in ["Select", "選択モード"]: self.tool_seg.set(str(t.get("tool_select", "Select")))
        elif current_tool in ["Text", "テキスト"]: self.tool_seg.set(str(t.get("tool_text", "Text")))
        elif current_tool in ["Marquee", "範囲選択"]: self.tool_seg.set(str(t.get("tool_rect", "Marquee")))
        
        self.btn_idx_parts.configure(text=str(t.get("idx_parts", "PRT")))
        self.btn_idx_props.configure(text=str(t.get("idx_props", "PRP")))
        self.btn_idx_sys.configure(text=str(t.get("idx_sys", "SYS")))
        
        self.lbl_parts.configure(text=str(t.get("parts_palette", "PARTS")))
        self.lbl_props.configure(text=str(t.get("properties", "PROPERTIES")))
        self.lbl_prop_label.configure(text=str(t.get("prop_label", "Label:")))
        self.lbl_prop_pos.configure(text="Position (X/Y):")
        self.lbl_prop_size.configure(text=str(t.get("prop_size", "Width / Height:")))
        self.prop_apply_btn.configure(text=str(t.get("prop_apply", "Apply Changes")))
        
        lock_btn_text = "配置固定 / 解除" if self.app.current_lang == "JP" else "Lock/Unlock"
        self.lock_btn.configure(text=lock_btn_text)

        self.align_left_btn.configure(text=str(t.get("menu_align_left", "Align Left")))
        self.align_top_btn.configure(text=str(t.get("menu_align_top", "Align Top")))
        
        self.lbl_sys.configure(text=str(t.get("system", "SYSTEM")))
        self.lbl_layer_title.configure(text=str(t.get("layer_title", "LAYER MANAGER")))

        self.btn_layer_merge.configure(text=str(t.get("layer_merge", "Merge Down")))
        self.btn_layer_rename.configure(text=str(t.get("layer_rename", "Rename")))
        
        self.delete_btn.configure(text=str(t.get("delete_part", "Delete")))
        self.btn_edit_shortcuts.configure(text=str(t.get("menu_edit_shortcuts", "Edit Shortcuts...")))
        self.btn_bg_color.configure(text=str(t.get("menu_bg_color", "Change Background Color...")))
        self.lbl_font_select.configure(text=str(t.get("font_select", "Export Font:")))
        
        self.lbl_rt_preview.configure(text=str(t.get("rt_preview_title", "REAL-TIME PREVIEW")))
        self.color_btn.configure(text=str(t.get("choose_color", "Choose Color")))
        
        if self.app.current_lang == "JP":
            self.btn_lang_switch.configure(text="Switch to English")
        else:
            self.btn_lang_switch.configure(text="日本語に切り替え")
        
        if "Ready" in self.status_label.cget("text") or "待機中" in self.status_label.cget("text"):
            self.status_label.configure(text=str(t.get("status_ready", "Ready...")))