"""
AAUI Designer Pro の状態管理モジュール。
パーツデータ、レイヤー情報、選択状態、Undo/Redo履歴、クリップボードなどの
アプリケーションのコアデータを一元管理する。
"""

import json
import uuid
import config

class StateManager:
    def __init__(self, app):
        self.app = app
        self.parts_data = {}
        self.selected_items = set()
        self.layers = []
        self.active_layer_id = "L_DEFAULT"
        self.bg_color = "#1e1e1e"
        
        self.history = []
        self.history_index = -1
        self._is_restoring = False
        
        self.clipboard = []
        self.current_project_path = None
        self.is_dirty = False
        
        self.init_layers()

    def init_layers(self):
        t = config.UI_TEXT.get(self.app.current_lang, config.UI_TEXT["JP"])
        self.layers = [
            {"id": "L_DEFAULT", "name": "Layer 1", "locked": False, "visible": True, "opacity": 1.0, "image_data": None, "image_x": 0, "image_y": 0, "image_scale": 1.0}
        ]
        self.active_layer_id = "L_DEFAULT"

    def mark_dirty(self):
        if not self.is_dirty:
            self.is_dirty = True
            self.app.update_title()

    def mark_clean(self):
        if self.is_dirty:
            self.is_dirty = False
            self.app.update_title()

    def save_state(self):
        if self._is_restoring: return
        
        state_parts = []
        for p_id, d in self.parts_data.items():
            state_d = d.copy()
            state_d.pop("canvas_items", None)
            state_d["id"] = p_id
            state_parts.append(state_d)
            
        state_layers = []
        for lyr in self.layers:
            safe_lyr = lyr.copy()
            if "image_data" in safe_lyr:
                safe_lyr["image_data"] = "IMAGE_EXISTS" if safe_lyr["image_data"] else None
            state_layers.append(safe_lyr)

        state = {
            "layers": state_layers,
            "parts": state_parts,
            "bg_color": self.bg_color
        }
        state_str = json.dumps(state)
        self.history = self.history[:self.history_index + 1]
        self.history.append(state_str)
        self.history_index += 1
        
        self.mark_dirty()
        if hasattr(self.app, 'canvas_mgr'):
            self.app.canvas_mgr.update_realtime_preview()

    def load_state_from_history(self, state_str):
        self._is_restoring = True
        self.app.canvas_mgr.commit_inline_edit()
        
        for p_id in list(self.parts_data.keys()):
            self.app.ui.canvas.delete(p_id)
        self.parts_data.clear()
        self.app.canvas_mgr.deselect_all()
        
        data_dict = json.loads(state_str)
        t = config.UI_TEXT.get(self.app.current_lang, config.UI_TEXT["JP"])
        
        current_images = {lyr["id"]: lyr.get("image_data") for lyr in self.layers}
        
        self.layers = data_dict.get("layers", [{"id": "L_DEFAULT", "name": "Layer 1", "locked": False, "visible": True, "opacity": 1.0, "image_scale": 1.0}])
        for lyr in self.layers:
            if lyr["id"] in current_images:
                lyr["image_data"] = current_images[lyr["id"]]
            else:
                lyr["image_data"] = None
                
            if "image_scale" not in lyr:
                lyr["image_scale"] = 1.0
            if "image_x" not in lyr:
                lyr["image_x"] = 0
            if "image_y" not in lyr:
                lyr["image_y"] = 0
        
        self.bg_color = data_dict.get("bg_color", "#1e1e1e")
        self.app.ui.canvas.configure(bg=self.bg_color)
        
        for data in data_dict.get("parts", []):
            p_id = data.get("id", str(uuid.uuid4()))
            self.parts_data[p_id] = {
                "type": data["type"],
                "col": data["col"],
                "row": data["row"],
                "width": data["width"],
                "height": data["height"],
                "label": data["label"],
                "color": data.get("color", "#FFFFFF"),
                "layer_id": data.get("layer_id", "L_DEFAULT"),
                "group_id": data.get("group_id", None),
                "locked": data.get("locked", False),
                "canvas_items": [],
                "z_order": data.get("z_order", 0)
            }
            self.app.canvas_mgr.redraw_part(p_id, update_preview=False)
        
        self.app.canvas_mgr.apply_z_order()
        self.app.ui.update_layer_ui()
        self.app.canvas_mgr.apply_layer_visibility()
        self.app.canvas_mgr.update_guide_display()
        
        self._is_restoring = False
        
        self.mark_dirty()
        self.app.canvas_mgr.update_realtime_preview()

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.load_state_from_history(self.history[self.history_index])
            self.app.set_status("Undo completed.")

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.load_state_from_history(self.history[self.history_index])
            self.app.set_status("Redo completed.")

    def copy_action(self):
        self.clipboard = [self.parts_data[p_id].copy() for p_id in self.selected_items if p_id in self.parts_data]
        self.app.set_status(f"Copied {len(self.clipboard)} item(s).")

    def paste_action(self):
        if not self.clipboard: return
        
        self.app.canvas_mgr.deselect_all()
        self._is_restoring = True
        
        group_map = {}
        
        for data in self.clipboard:
            new_p_id = str(uuid.uuid4())
            old_group_id = data.get("group_id")
            
            new_group_id = None
            if old_group_id:
                if old_group_id not in group_map:
                    group_map[old_group_id] = str(uuid.uuid4())
                new_group_id = group_map[old_group_id]

            self.parts_data[new_p_id] = {
                "type": data["type"],
                "col": data["col"] + 2,
                "row": data["row"] + 2,
                "width": data["width"],
                "height": data["height"],
                "label": data["label"],
                "color": data.get("color", "#FFFFFF"),
                "layer_id": self.active_layer_id,
                "group_id": new_group_id,
                "locked": data.get("locked", False),
                "canvas_items": [],
                "z_order": data.get("z_order", 0)
            }
            self.app.canvas_mgr.redraw_part(new_p_id, update_preview=False)
            self.app.canvas_mgr.select_item(new_p_id, add_to_selection=True)
            
        self.app.canvas_mgr.apply_z_order()
        self._is_restoring = False
        self.save_state()
        self.app.set_status(f"Pasted {len(self.clipboard)} item(s).")

    def group_selected(self):
        if len(self.selected_items) < 2: return
        new_group_id = str(uuid.uuid4())
        for p_id in self.selected_items:
            if p_id in self.parts_data:
                self.parts_data[p_id]["group_id"] = new_group_id
        self.save_state()
        self.app.set_status(f"Grouped {len(self.selected_items)} item(s).")

    def ungroup_selected(self):
        if not self.selected_items: return
        ungrouped = False
        for p_id in self.selected_items:
            if p_id in self.parts_data and self.parts_data[p_id].get("group_id"):
                self.parts_data[p_id]["group_id"] = None
                ungrouped = True
        if ungrouped:
            self.save_state()
            self.app.set_status("Ungrouped selected item(s).")