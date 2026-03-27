"""
AAUI Designer Pro のファイル入出力および履歴管理モジュール。
プロジェクトの保存、ロード、エクスポート、最近使ったファイル、オートバックアップを統括する。
"""

import json
import os
from tkinter import filedialog, messagebox
import config

class FileManager:
    def __init__(self, app):
        self.app = app
        self.recent_files = self.load_recent_files()

    def load_recent_files(self):
        if os.path.exists(config.RECENT_FILES_PATH):
            try:
                with open(config.RECENT_FILES_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_recent_files(self):
        try:
            with open(config.RECENT_FILES_PATH, "w", encoding="utf-8") as f:
                json.dump(self.recent_files, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save recent files: {e}")

    def add_to_recent(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        if len(self.recent_files) > config.MAX_RECENT_FILES:
            self.recent_files = self.recent_files[:config.MAX_RECENT_FILES]
        self.save_recent_files()
        self.app.update_recent_menu()

    def save_project(self, as_new=False):
        self.app.canvas_mgr.commit_inline_edit()
        if as_new or not self.app.app_state.current_project_path:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".aaui",
                filetypes=[("AAUI Project", "*.aaui"), ("All Files", "*.*")]
            )
            if not file_path: return
            self.app.app_state.current_project_path = file_path
            self.add_to_recent(file_path)
            
        try:
            state_str = self.app.app_state.history[self.app.app_state.history_index]
            with open(self.app.app_state.current_project_path, "w", encoding="utf-8") as f:
                f.write(state_str)
            self.app.app_state.mark_clean()
            t = config.UI_TEXT.get(self.app.current_lang, config.UI_TEXT["JP"])
            self.app.set_status(f"Saved: {os.path.basename(self.app.app_state.current_project_path)}")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def load_project(self, file_path=None):
        if self.app.app_state.is_dirty:
            if not messagebox.askyesno("Confirm", "保存されていない変更があります。破棄して開きますか？"):
                return
        if not file_path:
            file_path = filedialog.askopenfilename(
                filetypes=[("AAUI Project", "*.aaui"), ("All Files", "*.*")]
            )
        if not file_path: return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                state_str = f.read()
            self.app.canvas_mgr.clear_all_parts()
            self.app.app_state.history.clear()
            self.app.app_state.history_index = -1
            self.app.app_state.current_project_path = file_path
            self.app.app_state._is_restoring = False
            self.app.app_state.load_state_from_history(state_str)
            self.app.app_state.save_state()
            self.app.app_state.mark_clean()
            self.add_to_recent(file_path)
            self.app.set_status(f"Loaded: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))

    def auto_backup(self):
        if self.app.app_state.is_dirty and self.app.app_state.history:
            try:
                os.makedirs(config.BACKUP_DIR, exist_ok=True)
                state_str = self.app.app_state.history[self.app.app_state.history_index]
                with open(config.AUTO_BACKUP_PATH, "w", encoding="utf-8") as f:
                    f.write(state_str)
                t = config.UI_TEXT.get(self.app.current_lang, config.UI_TEXT["JP"])
                self.app.set_status(str(t.get("status_autosaved", "Auto-backup completed")))
            except Exception as e:
                print(f"Auto-backup failed: {e}")
        self.app.after(config.AUTO_SAVE_INTERVAL, self.auto_backup)

    def export_as_markdown(self):
        self.app.canvas_mgr.commit_inline_edit()
        final_text = self.app.canvas_mgr.generate_aa_text()
        if not final_text:
            messagebox.showinfo("Info", "No AA to export.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("All Files", "*.*")]
        )
        if not file_path: return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"```aa\n{final_text}\n```")
            t = config.UI_TEXT.get(self.app.current_lang, config.UI_TEXT["JP"])
            self.app.set_status(f"{t.get('status_exported', 'Exported: ')}{os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def export_as_text(self):
        self.app.canvas_mgr.commit_inline_edit()
        final_text = self.app.canvas_mgr.generate_aa_text()
        if not final_text:
            messagebox.showinfo("Info", "No AA to export.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not file_path: return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(final_text)
            t = config.UI_TEXT.get(self.app.current_lang, config.UI_TEXT["JP"])
            self.app.set_status(f"{t.get('status_exported', 'Exported: ')}{os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))