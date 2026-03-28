"""
AAUI Designer Proのメインアプリケーション起動モジュール。
各マネージャー（State, UI, Canvas, File）を初期化し、イベントのルーティングとメインループを統括する。
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, colorchooser
import customtkinter as ctk
from PIL import Image
import os
import json

import config
from state_manager import StateManager
from ui_components import UIManager
from canvas_manager import CanvasManager
from file_manager import FileManager

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

WINDOW_CONFIG_PATH = "configs/window_config.json"

class AAUIDesignerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.current_lang = "JP"
        self.show_grid_flag = True
        
        os.makedirs("configs", exist_ok=True)
        
        self.shortcuts = config.load_shortcuts()
        self._current_binds = []
        
        self.available_fonts = config.load_font_cache()
        self.current_export_font = self.available_fonts.get("msgothic.ttc", "")
        if not self.current_export_font and self.available_fonts:
            self.current_export_font = list(self.available_fonts.values())[0]
        
        self._load_icons()
        
        self.app_state = StateManager(self)
        self.ui = UIManager(self)
        self.canvas_mgr = CanvasManager(self)
        self.file_mgr = FileManager(self)
        
        self.update_title()
        self._create_menu()
        self.canvas_mgr.draw_rulers_and_grid()
        self.ui.update_ui_text()
        self.ui.update_layer_ui()
        
        self.window_config = self._load_window_config()
        self.geometry(f"{self.window_config['width']}x{self.window_config['height']}")
        
        if self.window_config.get("zoomed", True):
            self.after(0, lambda: self.state("zoomed"))
            
        self.after(500, self._adjust_sash)
        
        self.apply_shortcuts()
        
        self.app_state.save_state()
        self.app_state.mark_clean()
        self.after(config.AUTO_SAVE_INTERVAL, self.file_mgr.auto_backup)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _load_window_config(self):
        default_config = {"width": 1800, "height": 1000, "zoomed": True, "sash_ratio": 0.65}
        if os.path.exists(WINDOW_CONFIG_PATH):
            try:
                with open(WINDOW_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_config.update(data)
            except Exception:
                pass
        return default_config

    def on_closing(self):
        w = self.winfo_width()
        current_sash = self.ui.paned_window.sash_coord(0)[0]
        sash_ratio = current_sash / w if w > 0 else 0.65

        is_zoomed = self.state() == "zoomed"
        config_data = {
            "width": self.winfo_width() if not is_zoomed else self.window_config.get("width", 1800),
            "height": self.winfo_height() if not is_zoomed else self.window_config.get("height", 1000),
            "zoomed": is_zoomed,
            "sash_ratio": sash_ratio
        }
        try:
            with open(WINDOW_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config_data, f)
        except Exception as e:
            print(f"Failed to save window config: {e}")
            
        if self.app_state.is_dirty:
            if messagebox.askyesno("Quit", "保存されていない変更があります。終了しますか？"):
                self.destroy()
        else:
            self.destroy()

    def is_input_focused(self):
        focused = self.focus_get()
        return isinstance(focused, (tk.Entry, tk.Text, ctk.CTkEntry))

    def safe_bind_func(self, func):
        def wrapper(event):
            if self.is_input_focused():
                return
            func(event)
        return wrapper

    def apply_shortcuts(self):
        for seq in self._current_binds:
            try:
                self.unbind(seq)
            except Exception:
                pass
        self._current_binds = []

        def do_bind(seq, func, safe=True):
            if seq:
                final_func = self.safe_bind_func(func) if safe else func
                self.bind(seq, final_func)
                self._current_binds.append(seq)

        s = self.shortcuts
        do_bind(s.get("delete"), lambda e: self.canvas_mgr.delete_selected_parts())
        do_bind(s.get("delete_alt"), lambda e: self.canvas_mgr.delete_selected_parts())
        do_bind(s.get("escape"), self.canvas_mgr.on_escape, safe=False)
        do_bind(s.get("undo"), lambda e: self.app_state.undo())
        do_bind(s.get("redo"), lambda e: self.app_state.redo())
        do_bind(s.get("copy"), lambda e: self.app_state.copy_action())
        do_bind(s.get("paste"), lambda e: self.app_state.paste_action())
        do_bind(s.get("cut"), lambda e: self.canvas_mgr.cut_action())
        do_bind(s.get("save"), lambda e: self.file_mgr.save_project())
        do_bind(s.get("duplicate"), lambda e: self.canvas_mgr.duplicate_action())
        
        do_bind(s.get("move_up"), lambda e: self.canvas_mgr.move_selected(0, -1))
        do_bind(s.get("move_down"), lambda e: self.canvas_mgr.move_selected(0, 1))
        do_bind(s.get("move_left"), lambda e: self.canvas_mgr.move_selected(-1, 0))
        do_bind(s.get("move_right"), lambda e: self.canvas_mgr.move_selected(1, 0))

        do_bind(s.get("bring_front"), lambda e: self.canvas_mgr.bring_to_front())
        do_bind(s.get("send_back"), lambda e: self.canvas_mgr.send_to_back())
        do_bind(s.get("bring_forward"), lambda e: self.canvas_mgr.bring_forward())
        do_bind(s.get("send_backward"), lambda e: self.canvas_mgr.send_backward())
        
        do_bind(s.get("zoom"), self.canvas_mgr.on_zoom, safe=False)
        do_bind(s.get("reset_zoom"), self.canvas_mgr.reset_zoom, safe=False)
        
        if hasattr(self.canvas_mgr, 'focus_part'):
            do_bind(s.get("focus_next"), lambda e: self.canvas_mgr.focus_part("next"))
            do_bind(s.get("focus_prev"), lambda e: self.canvas_mgr.focus_part("prev"))
            
        do_bind(s.get("group"), lambda e: self.app_state.group_selected())
        do_bind(s.get("ungroup"), lambda e: self.app_state.ungroup_selected())
        do_bind("<Control-l>", lambda e: self.canvas_mgr.toggle_part_lock(), safe=False)

    def switch_language(self):
        if self.current_lang == "JP":
            self.current_lang = "EN"
        else:
            self.current_lang = "JP"
            
        self.ui.update_ui_text()
        self._create_menu()
        self.ui.update_layer_ui()
        
        if hasattr(self, 'canvas_mgr'):
            self.canvas_mgr.update_realtime_preview()
            
        t = config.UI_TEXT.get(self.current_lang, config.UI_TEXT["JP"])
        self.set_status(str(t.get("status_ready", "Language switched.")))

    def open_shortcut_editor(self):
        dialog = ctk.CTkToplevel(self)
        title_text = "ショートカット編集" if self.current_lang == "JP" else "Edit Shortcuts"
        dialog.title(str(title_text))
        dialog.geometry("500x700")
        dialog.transient(self)
        dialog.grab_set()

        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        recording_info = {"key": None, "button": None}

        def on_key_press(event):
            if not recording_info["key"]: return
            
            keysym = event.keysym
            
            if keysym == "Escape":
                if recording_info["button"]:
                    orig_seq = self.shortcuts.get(recording_info["key"], "")
                    recording_info["button"].configure(text=str(orig_seq))
                recording_info["key"] = None
                recording_info["button"] = None
                dialog.unbind("<Key>")
                return
                
            if keysym in ("Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Win_L", "Win_R", "Num_Lock", "Caps_Lock", "Scroll_Lock"):
                return
                
            mods = []
            if event.state & 0x0004: mods.append("Control")
            if event.state & 0x0001: mods.append("Shift")
            if event.state & 0x20000: mods.append("Alt")
            
            seq = f"<{'-'.join(mods + [keysym])}>" if mods else f"<{keysym}>"
            
            self.shortcuts[recording_info["key"]] = seq
            if recording_info["button"]:
                recording_info["button"].configure(text=seq)
                
            recording_info["key"] = None
            recording_info["button"] = None
            dialog.unbind("<Key>")

        def start_record(k, btn):
            recording_info["key"] = k
            recording_info["button"] = btn
            rec_text = "キーを押してください..." if self.current_lang == "JP" else "Press a key..."
            btn.configure(text=str(rec_text))
            dialog.focus_set()
            dialog.bind("<Key>", on_key_press)

        def populate(data):
            for widget in scroll.winfo_children():
                widget.destroy()
            for key, val in data.items():
                frame = ctk.CTkFrame(scroll, fg_color="transparent")
                frame.pack(fill="x", pady=2)
                
                disp_name = config.SHORTCUT_NAMES.get(key, {}).get(self.current_lang, key)
                lbl = ctk.CTkLabel(frame, text=str(disp_name), width=200, anchor="w")
                lbl.pack(side="left")
                
                btn = ctk.CTkButton(frame, text=str(val), width=150, fg_color="#34495e", hover_color="#2c3e50")
                btn.configure(command=lambda k=key, b=btn: start_record(k, b))
                btn.pack(side="right")

        populate(self.shortcuts)

        def save():
            config.save_shortcuts(self.shortcuts)
            self.apply_shortcuts()
            msg = "ショートカットを更新しました。" if self.current_lang == "JP" else "Shortcuts updated."
            self.set_status(str(msg))
            dialog.destroy()

        def restore_defaults():
            self.shortcuts = config.DEFAULT_SHORTCUTS.copy()
            populate(self.shortcuts)
            msg = "デフォルトに戻しました（未保存）。" if self.current_lang == "JP" else "Restored to defaults (Not saved)."
            self.set_status(str(msg))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        save_text = "保存して適用" if self.current_lang == "JP" else "Save & Apply"
        btn_save = ctk.CTkButton(btn_frame, text=str(save_text), command=save)
        btn_save.pack(side="left", padx=5)
        
        reset_text = "デフォルトに戻す" if self.current_lang == "JP" else "Restore Defaults"
        btn_reset = ctk.CTkButton(btn_frame, text=str(reset_text), fg_color="#c0392b", hover_color="#e74c3c", command=restore_defaults)
        btn_reset.pack(side="left", padx=5)

    def change_bg_color(self):
        color_code = colorchooser.askcolor(title="Choose Background Color", initialcolor=self.app_state.bg_color)[1]
        if color_code:
            self.app_state.bg_color = color_code
            self.ui.canvas.configure(bg=color_code)
            self.app_state.save_state()
            self.set_status(f"Background color changed to {color_code}")

    def export_png(self):
        self.canvas_mgr.commit_inline_edit()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")]
        )
        if not file_path: return
        
        ans = messagebox.askyesno("Background", "背景を透過させますか？\n(Yes: 透過 / No: 背景色を含める)")
        self.canvas_mgr.export_as_image(file_path, transparent=ans)
        t = config.UI_TEXT.get(self.current_lang, config.UI_TEXT["JP"])
        self.set_status(f"{t.get('status_exported', 'Exported: ') or ''}{os.path.basename(file_path)}")

    def copy_for_llm(self):
        aa_text = self.canvas_mgr.generate_aa_text()
        if not aa_text:
            messagebox.showinfo("Info", "No AA to copy.")
            return
        self.clipboard_clear()
        self.clipboard_append(f"```aa\n{aa_text}\n```")
        self.update()
        t = config.UI_TEXT.get(self.current_lang, config.UI_TEXT["JP"])
        self.set_status(str(t.get("status_copied", "Copied to clipboard")))

    def _adjust_sash(self):
        try:
            w = self.winfo_width()
            ratio = self.window_config.get("sash_ratio", 0.65)
            new_sash_pos = max(400, int(w * ratio))
            self.ui.paned_window.sash_place(0, new_sash_pos, 0)
            
            if hasattr(self, 'canvas_mgr'):
                self.canvas_mgr.redraw_all()
        except Exception:
            pass

    def _load_icons(self):
        try:
            if os.path.exists(config.ICON_LOCK_PATH):
                self.icon_lock = ctk.CTkImage(light_image=Image.open(config.ICON_LOCK_PATH), size=config.ICON_SIZE)
            else: self.icon_lock = None
                
            if os.path.exists(config.ICON_UNLOCK_PATH):
                self.icon_unlock = ctk.CTkImage(light_image=Image.open(config.ICON_UNLOCK_PATH), size=config.ICON_SIZE)
            else: self.icon_unlock = None

            if os.path.exists(config.ICON_VISIBLE_PATH):
                self.icon_visible = ctk.CTkImage(light_image=Image.open(config.ICON_VISIBLE_PATH), size=config.ICON_SIZE)
            else: self.icon_visible = None

            if os.path.exists(config.ICON_INVISIBLE_PATH):
                self.icon_invisible = ctk.CTkImage(light_image=Image.open(config.ICON_INVISIBLE_PATH), size=config.ICON_SIZE)
            else: self.icon_invisible = None

            up_path = "assets/LayerUp.png"
            dn_path = "assets/LayerDown.png"
            
            if os.path.exists(up_path):
                self.icon_layer_up = ctk.CTkImage(light_image=Image.open(up_path), size=(16, 16))
            else: self.icon_layer_up = None

            if os.path.exists(dn_path):
                self.icon_layer_dn = ctk.CTkImage(light_image=Image.open(dn_path), size=(16, 16))
            else: self.icon_layer_dn = None

        except Exception:
            self.icon_lock = None
            self.icon_unlock = None
            self.icon_visible = None
            self.icon_invisible = None
            self.icon_layer_up = None
            self.icon_layer_dn = None

    def set_status(self, text):
        self.ui.status_label.configure(text=str(text or ""))

    def update_title(self):
        t = config.UI_TEXT.get(self.current_lang, config.UI_TEXT["JP"])
        base_title = t.get("title", "AAUI Designer Pro") or ""
        
        if self.app_state.current_project_path:
            file_name = os.path.basename(self.app_state.current_project_path)
        else:
            file_name = "Untitled"
            
        dirty_mark = "*" if self.app_state.is_dirty else ""
        self.title(f"{base_title} - {file_name}{dirty_mark}")

    def _create_menu(self):
        t = config.UI_TEXT.get(self.current_lang, config.UI_TEXT["JP"])
        if hasattr(self, 'menubar') and self.menubar:
            self.menubar.destroy()
            
        self.menubar = tk.Menu(self)
        self.config(menu=self.menubar)
        
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=str(t.get("menu_file", "File")), menu=self.file_menu)
        self.file_menu.add_command(label=str(t.get("menu_new", "New")), command=self.new_project)
        self.file_menu.add_command(label=str(t.get("menu_open", "Open...")), command=lambda: self.file_mgr.load_project())
        
        self.recent_menu = tk.Menu(self.file_menu, tearoff=0)
        self.file_menu.add_cascade(label=str(t.get("menu_recent", "Recent Files")), menu=self.recent_menu)
        self.update_recent_menu()
        
        self.file_menu.add_separator()
        self.file_menu.add_command(label=str(t.get("menu_save", "Save")), command=lambda: self.file_mgr.save_project(), accelerator="Ctrl+S")
        self.file_menu.add_command(label=str(t.get("menu_save_as", "Save As...")), command=lambda: self.file_mgr.save_project(as_new=True))
        self.file_menu.add_separator()
        
        self.export_menu = tk.Menu(self.file_menu, tearoff=0)
        self.file_menu.add_cascade(label=str(t.get("menu_export", "Export")), menu=self.export_menu)
        self.export_menu.add_command(label=str(t.get("menu_export_md", "Markdown (.md)")), command=self.file_mgr.export_as_markdown)
        self.export_menu.add_command(label=str(t.get("menu_export_txt", "Text (.txt)")), command=self.file_mgr.export_as_text)
        self.export_menu.add_command(label=str(t.get("menu_export_png", "Export as Image (.png)")), command=self.export_png)
        
        self.file_menu.add_separator()
        self.file_menu.add_command(label=str(t.get("menu_exit", "Exit")), command=self.on_closing)
        
        self.edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=str(t.get("menu_edit", "Edit")), menu=self.edit_menu)
        self.edit_menu.add_command(label=str(t.get("menu_undo", "Undo")), command=self.app_state.undo, accelerator="Ctrl+Z")
        self.edit_menu.add_command(label=str(t.get("menu_redo", "Redo")), command=self.app_state.redo, accelerator="Ctrl+Y")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label=str(t.get("menu_cut", "Cut")), command=self.canvas_mgr.cut_action, accelerator="Ctrl+X")
        self.edit_menu.add_command(label=str(t.get("menu_copy", "Copy")), command=self.app_state.copy_action, accelerator="Ctrl+C")
        self.edit_menu.add_command(label=str(t.get("menu_paste", "Paste")), command=self.app_state.paste_action, accelerator="Ctrl+V")
        self.edit_menu.add_command(label=str(t.get("menu_duplicate", "Duplicate")), command=self.canvas_mgr.duplicate_action)
        self.edit_menu.add_command(label=str(t.get("menu_delete", "Delete")), command=self.canvas_mgr.delete_selected_parts)
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label=str(t.get("menu_group", "Group")), command=self.app_state.group_selected, accelerator="Ctrl+G")
        self.edit_menu.add_command(label=str(t.get("menu_ungroup", "Ungroup")), command=self.app_state.ungroup_selected, accelerator="Ctrl+Shift+G")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label=str(t.get("menu_copy_llm", "LLM用AAコピー")), command=self.copy_for_llm)
        self.edit_menu.add_command(label=str(t.get("menu_edit_shortcuts", "ショートカット編集...")), command=self.open_shortcut_editor)
        
        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=str(t.get("menu_view", "View")), menu=self.view_menu)
        self.view_menu.add_command(label=str(t.get("menu_toggle_grid", "Toggle Grid")), command=self.toggle_grid)
        self.view_menu.add_command(label=str(t.get("menu_bg_color", "Change Background Color...")), command=self.change_bg_color)
        
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=str(t.get("menu_help", "Help")), menu=self.help_menu)
        self.help_menu.add_command(label=str(t.get("menu_about", "About")), command=self.show_about)

    def update_recent_menu(self):
        self.recent_menu.delete(0, tk.END)
        if not self.file_mgr.recent_files:
            self.recent_menu.add_command(label="No recent files", state="disabled")
            return
        for path in self.file_mgr.recent_files:
            if os.path.exists(path):
                self.recent_menu.add_command(label=os.path.basename(path), command=lambda p=path: self.file_mgr.load_project(p))

    def toggle_grid(self):
        self.show_grid_flag = not self.show_grid_flag
        state = "normal" if self.show_grid_flag else "hidden"
        self.ui.canvas.itemconfig("grid", state=state)

    def show_about(self):
        t = config.UI_TEXT.get(self.current_lang, config.UI_TEXT["JP"])
        title = t.get("title", "AAUI Designer Pro") or ""
        desc = f"{title}\n\nA tool for designing ASCII Art User Interfaces intuitively.\nSupports layer management, precise grid snapping, and real-time previews."
        messagebox.showinfo("About", str(desc))

    def new_project(self):
        if self.app_state.is_dirty:
            if not messagebox.askyesno("Confirm", "保存されていない変更があります。破棄して新規作成しますか？"):
                return
        self.canvas_mgr.clear_all_parts()
        self.app_state.current_project_path = None
        self.app_state.init_layers()
        self.app_state.history.clear()
        self.app_state.history_index = -1
        self.ui.update_layer_ui()
        self.app_state.save_state()
        self.app_state.mark_clean()
        self.set_status("New project created.")

    def is_layer_locked(self, layer_id):
        for lyr in self.app_state.layers:
            if lyr["id"] == layer_id: return lyr["locked"]
        return False

    def set_active_layer(self, layer_id):
        self.app_state.active_layer_id = layer_id
        self.canvas_mgr.deselect_all()
        self.ui.update_layer_ui()

    def toggle_specific_layer_lock(self, layer_id):
        for lyr in self.app_state.layers:
            if lyr["id"] == layer_id:
                lyr["locked"] = not lyr["locked"]
                break
        self.ui.update_layer_ui()
        self.app_state.save_state()

    def toggle_layer_visibility(self, layer_id):
        for lyr in self.app_state.layers:
            if lyr["id"] == layer_id:
                lyr["visible"] = not lyr.get("visible", True)
                break
        self.canvas_mgr.deselect_all()
        self.canvas_mgr.apply_layer_visibility()
        self.ui.update_layer_ui()
        self.app_state.save_state()

    def rename_specific_layer(self, layer_id):
        self.ui.rename_layer_dialog(layer_id)

    def layer_add(self):
        import uuid
        new_id = "L_" + str(uuid.uuid4())[:8]
        new_name = f"Layer {len(self.app_state.layers) + 1}"
        self.app_state.layers.append({"id": new_id, "name": new_name, "locked": False, "visible": True, "opacity": 1.0})
        self.app_state.active_layer_id = new_id
        self.canvas_mgr.apply_z_order()
        self.ui.update_layer_ui()
        self.app_state.save_state()

    def layer_delete(self):
        if len(self.app_state.layers) <= 1:
            messagebox.showwarning("Warning", "これ以上レイヤーを削除できません。")
            return
        idx = next((i for i, lyr in enumerate(self.app_state.layers) if lyr["id"] == self.app_state.active_layer_id), None)
        if idx is not None:
            # 🚨 レイヤー削除前のロック確認を追加 🚨
            if self.app_state.layers[idx].get("locked", False):
                msg = "ロックされているレイヤーは削除できません。" if self.current_lang == "JP" else "Cannot delete locked layer."
                messagebox.showwarning("Warning", str(msg))
                return
                
            del_id = self.app_state.layers[idx]["id"]

            for p_id, data in list(self.app_state.parts_data.items()):
                if data.get("layer_id") == del_id:
                    self.ui.canvas.delete(p_id)
                    del self.app_state.parts_data[p_id]
                
            del self.app_state.layers[idx]
            self.app_state.active_layer_id = self.app_state.layers[-1]["id"]
            self.canvas_mgr.apply_z_order()
            self.ui.update_layer_ui()
            self.app_state.save_state()

    def layer_move_up(self):
        idx = next((i for i, lyr in enumerate(self.app_state.layers) if lyr["id"] == self.app_state.active_layer_id), None)
        if idx is not None and idx < len(self.app_state.layers) - 1:
            self.app_state.layers[idx], self.app_state.layers[idx+1] = self.app_state.layers[idx+1], self.app_state.layers[idx]
            self.canvas_mgr.apply_z_order()
            self.ui.update_layer_ui()
            self.app_state.save_state()

    def layer_move_down(self):
        idx = next((i for i, lyr in enumerate(self.app_state.layers) if lyr["id"] == self.app_state.active_layer_id), None)
        if idx is not None and idx > 0:
            self.app_state.layers[idx], self.app_state.layers[idx-1] = self.app_state.layers[idx-1], self.app_state.layers[idx]
            self.canvas_mgr.apply_z_order()
            self.ui.update_layer_ui()
            self.app_state.save_state()

    def layer_merge_down(self):
        idx = next((i for i, lyr in enumerate(self.app_state.layers) if lyr["id"] == self.app_state.active_layer_id), None)
        if idx is None or idx == 0: return 
        target_id = self.app_state.layers[idx]["id"]
        dest_id = self.app_state.layers[idx - 1]["id"]
        for p_id, data in self.app_state.parts_data.items():
            if data.get("layer_id") == target_id:
                data["layer_id"] = dest_id
            
        del self.app_state.layers[idx]
        self.app_state.active_layer_id = dest_id
        self.canvas_mgr.apply_z_order()
        self.ui.update_layer_ui()
        self.app_state.save_state()

if __name__ == "__main__":
    app = AAUIDesignerApp()
    app.mainloop()