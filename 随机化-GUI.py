# -*- coding: utf-8 -*-
"""
ZZMI Mod 随机管理器 - 最终修复版（鼠标滚轮无报错）
用法：
    python 脚本.py           # 启动图形界面
    python 脚本.py -auto     # 无界面自动随机化
"""

import os
import sys
import random
import json
import io

AUTO_MODE = "-auto" in sys.argv

# ==================== 核心随机化函数 ====================
def count_enabled_mods(char_path):
    if not os.path.isdir(char_path):
        return 0, 0
    count = 0
    total = 0
    for entry in os.listdir(char_path):
        if os.path.isdir(os.path.join(char_path, entry)):
            total += 1
            if not entry.startswith("DISABLED_"):
                count += 1
    return count, total

def process_group(char_path, group_name, group_mod_map, log_func):
    if not group_mod_map:
        return
    log_func("    分组【{}】:".format(group_name))
    selected_mod = random.choice(list(group_mod_map.keys()))
    log_func("      随机选中的mod: {}".format(selected_mod))
    for original_name, current_name in group_mod_map.items():
        if original_name == selected_mod:
            target_name = original_name
        else:
            target_name = "DISABLED_{}".format(original_name)
        if current_name == target_name:
            log_func("      无需修改: {} (已是目标状态)".format(current_name))
            continue
        current_full = os.path.join(char_path, current_name)
        target_full = os.path.join(char_path, target_name)
        if os.path.exists(target_full):
            log_func("      警告：目标路径已存在，跳过: {}".format(target_name))
            continue
        try:
            os.rename(current_full, target_full)
            log_func("      已修改: {} -> {}".format(current_name, target_name))
        except Exception as e:
            log_func("      错误：修改 {} 失败: {}".format(current_name, str(e)))

def run_randomizer_from_preset(mod_root, preset, log_func):
    if not os.path.isdir(mod_root):
        log_func("错误：Mod总路径无效: {}".format(mod_root))
        return False

    locked_mods = preset.get("锁定配置", {})
    group_mods = preset.get("分组配置", {})
    char_checks = preset.get("角色勾选", {})
    all_chars = [d for d in os.listdir(mod_root) if os.path.isdir(os.path.join(mod_root, d))]
    all_chars.sort()
    target_chars = [c for c in all_chars if char_checks.get(c, False)]
    if not target_chars:
        log_func("错误：预设中没有勾选任何角色，请先通过UI设置。")
        return False

    log_func("找到 {} 个待处理角色，开始处理...".format(len(target_chars)))
    log_func("-" * 50)

    stats = {}
    for char_name in target_chars:
        char_path = os.path.join(mod_root, char_name)
        log_func("\n处理角色: {}".format(char_name))

        all_available_mods = {}
        has_error = False
        count_locked = 0
        char_locked = locked_mods.get(char_name, [])

        for entry in os.listdir(char_path):
            entry_path = os.path.join(char_path, entry)
            if not os.path.isdir(entry_path):
                continue
            if entry.startswith("DISABLED_"):
                original_name = entry[9:]
            else:
                original_name = entry
            if original_name in char_locked:
                log_func("  跳过锁定的mod: {}".format(entry))
                count_locked += 1
                continue
            if original_name in all_available_mods:
                log_func("  错误：发现重复的mod: {}，请手动处理".format(original_name))
                has_error = True
                break
            all_available_mods[original_name] = entry

        if has_error:
            log_func("  跳过该角色的处理。")
            enabled, total = count_enabled_mods(char_path)
            stats[char_name] = (enabled, total)
            continue
        if count_locked > 0:
            log_func("  共锁定了 {} 个mod".format(count_locked))
        if not all_available_mods:
            log_func("  该角色下没有可处理的mod，跳过。")
            enabled, total = count_enabled_mods(char_path)
            stats[char_name] = (enabled, total)
            continue

        char_groups = group_mods.get(char_name, None)
        if char_groups is None:
            log_func("  未配置分组，所有mod作为单个分组处理")
            process_group(char_path, "默认分组", all_available_mods, log_func)
        else:
            log_func("  已配置分组，将按分组独立随机")
            groups_mod_maps = {g_name: {} for g_name in char_groups}
            groups_mod_maps["普通mod组"] = {}
            for original_name, current_name in all_available_mods.items():
                assigned = False
                for g_name, g_mods in char_groups.items():
                    if original_name in g_mods:
                        groups_mod_maps[g_name][original_name] = current_name
                        assigned = True
                        break
                if not assigned:
                    groups_mod_maps["普通mod组"][original_name] = current_name
            for g_name, g_mod_map in groups_mod_maps.items():
                process_group(char_path, g_name, g_mod_map, log_func)

        enabled, total = count_enabled_mods(char_path)
        stats[char_name] = (enabled, total)
        log_func("  角色 [{}] 当前已生效Mod: {}/{}".format(char_name, enabled, total))

    # 最终统计 - 多列竖线分隔
    log_func("\n" + "=" * 50)
    unprocessed = [c for c in all_chars if c not in target_chars]
    processed = target_chars

    def format_item(name, en, total):
        name_fixed = (name[:12] if len(name) > 12 else name).ljust(12)
        return "{}  {}/{}".format(name_fixed, en, total)

    def output_multicolumn(items, col_count=3, sep=" | ", color_func=None):
        if not items:
            return
        rows = [items[i:i+col_count] for i in range(0, len(items), col_count)]
        col_widths = [0] * col_count
        for row in rows:
            for idx, it in enumerate(row):
                w = len(it)
                if w > col_widths[idx]:
                    col_widths[idx] = w
        for row in rows:
            cells = [it.ljust(col_widths[i]) for i, it in enumerate(row)]
            line = sep.join(cells)
            if color_func:
                log_func(line, color=color_func)
            else:
                log_func(line)

    if unprocessed:
        items = [format_item(c, *count_enabled_mods(os.path.join(mod_root, c))) for c in unprocessed]
        output_multicolumn(items, col_count=3, sep=" | ", color_func="gray")
    if processed:
        items = [format_item(c, *stats.get(c, count_enabled_mods(os.path.join(mod_root, c)))) for c in processed]
        output_multicolumn(items, col_count=3, sep=" | ", color_func="green")

    log_func("=" * 50)
    log_func("所有角色处理完成！")
    return True

def load_preset_file(presets_file):
    presets = {}
    default_preset = {"角色勾选": {}, "锁定配置": {}, "分组配置": {}, "auto_run": False}
    if os.path.exists(presets_file):
        try:
            with io.open(presets_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    presets = data
        except:
            pass
    if "默认预设" not in presets:
        presets["默认预设"] = default_preset.copy()
    else:
        for key in default_preset:
            if key not in presets["默认预设"]:
                presets["默认预设"][key] = default_preset[key]
    return presets

def load_config(config_file):
    mod_root = ""
    current_preset = "默认预设"
    if os.path.exists(config_file):
        try:
            with io.open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                mod_root = config.get('mod_root_path', '')
                current_preset = config.get('current_preset', '默认预设')
        except:
            pass
    return mod_root, current_preset

# ==================== 图形界面 ====================
if not AUTO_MODE:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, simpledialog, ttk
    except ImportError:
        import Tkinter as tk
        import tkFileDialog as filedialog
        import tkMessageBox as messagebox
        import tkSimpleDialog as simpledialog
        import ttk

    class ZZMIModManagerApp(tk.Tk):
        def __init__(self):
            super(ZZMIModManagerApp, self).__init__()
            self.title("ZZMI Mod 随机管理器")
            self.geometry("1100x850")
            self.resizable(True, True)

            if getattr(sys, 'frozen', False):
                self.base_dir = os.path.dirname(sys.executable)
            else:
                self.base_dir = os.path.dirname(os.path.abspath(__file__))

            self.config_file = os.path.join(self.base_dir, "mod_manager_config.json")
            self.presets_file = os.path.join(self.base_dir, "mod_manager_presets.json")

            self.mod_root_path = tk.StringVar()
            self.locked_mods = {}
            self.group_mods = {}
            self.char_check_vars = {}
            self.char_color_blocks = {}
            self.current_char = None
            self.current_preset = "默认预设"
            self.presets = {}

            self.load_presets()
            self.load_config()
            self.init_ui()

            if self.mod_root_path.get() and os.path.isdir(self.mod_root_path.get()):
                self.load_characters()

            self.apply_preset(self.current_preset)

            if self.presets.get(self.current_preset, {}).get("auto_run", False):
                self.after(500, self.run_process)

            self.bind_all("<MouseWheel>", self._on_mousewheel)
            self.bind_all("<Button-4>", self._on_mousewheel)
            self.bind_all("<Button-5>", self._on_mousewheel)

        def _on_mousewheel(self, event):
            """修复版：递归检查父控件"""
            widget = self.winfo_containing(event.x_root, event.y_root)
            def is_descendant(child, ancestor):
                while child:
                    if child == ancestor:
                        return True
                    try:
                        child = child.master
                    except AttributeError:
                        return False
                return False

            if is_descendant(widget, self.char_canvas):
                if event.num == 5 or event.delta < 0:
                    self.char_canvas.yview_scroll(1, "units")
                else:
                    self.char_canvas.yview_scroll(-1, "units")
            elif is_descendant(widget, self.mod_canvas):
                if event.num == 5 or event.delta < 0:
                    self.mod_canvas.yview_scroll(1, "units")
                else:
                    self.mod_canvas.yview_scroll(-1, "units")
            elif is_descendant(widget, self.log_text):
                if event.num == 5 or event.delta < 0:
                    self.log_text.yview_scroll(1, "units")
                else:
                    self.log_text.yview_scroll(-1, "units")

        # ==================== 预设管理 ====================
        def load_presets(self):
            self.presets = load_preset_file(self.presets_file)

        def save_presets(self):
            try:
                with io.open(self.presets_file, 'w', encoding='utf-8') as f:
                    json.dump(self.presets, f, ensure_ascii=False, indent=2)
            except:
                pass

        def save_current_state_to_preset(self, preset_name):
            if preset_name not in self.presets:
                self.presets[preset_name] = {}
            char_checks = {char: var.get() for char, var in self.char_check_vars.items()}
            self.presets[preset_name]["角色勾选"] = char_checks
            self.presets[preset_name]["锁定配置"] = self.locked_mods.copy()
            self.presets[preset_name]["分组配置"] = self.group_mods.copy()
            self.presets[preset_name]["auto_run"] = self.auto_run_var.get()
            self.save_presets()

        def apply_preset(self, preset_name):
            if preset_name not in self.presets:
                if preset_name != "默认预设":
                    messagebox.showerror("错误", "预设 '{}' 不存在".format(preset_name))
                preset_name = "默认预设"
                if preset_name not in self.presets:
                    self.presets[preset_name] = {"角色勾选": {}, "锁定配置": {}, "分组配置": {}, "auto_run": False}
            preset = self.presets[preset_name]
            self.locked_mods = preset.get("锁定配置", {}).copy()
            self.group_mods = preset.get("分组配置", {}).copy()
            char_checks = preset.get("角色勾选", {})
            for char, var in self.char_check_vars.items():
                is_checked = char_checks.get(char, True)
                var.set(is_checked)
                if char in self.char_color_blocks:
                    self.char_color_blocks[char].config(bg="green" if is_checked else "red")
            self.auto_run_var.set(preset.get("auto_run", False))
            self.current_preset = preset_name
            self.preset_var.set(preset_name)
            if self.current_char:
                self.load_mods_of_char()

        def delete_preset(self):
            if self.current_preset == "默认预设":
                messagebox.showwarning("提示", "默认预设不可删除")
                return
            if messagebox.askyesno("确认", "删除预设 '{}'？".format(self.current_preset)):
                del self.presets[self.current_preset]
                self.save_presets()
                self.current_preset = "默认预设"
                self.apply_preset("默认预设")

        def new_preset(self):
            name = simpledialog.askstring("新建预设", "请输入预设名称：", parent=self)
            if not name or not name.strip():
                return
            name = name.strip()
            if name in self.presets:
                messagebox.showerror("错误", "预设已存在")
                return
            self.presets[name] = {}
            self.save_current_state_to_preset(name)
            self.current_preset = name
            self.preset_var.set(name)
            self.save_config()
            messagebox.showinfo("成功", "预设 '{}' 已创建".format(name))

        # ==================== 配置持久化 ====================
        def load_config(self):
            mod_root, current_preset = load_config(self.config_file)
            self.mod_root_path.set(mod_root)
            self.current_preset = current_preset

        def save_config(self):
            config = {
                'mod_root_path': self.mod_root_path.get(),
                'current_preset': self.current_preset
            }
            try:
                with io.open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except:
                pass

        # ==================== 界面构建 ====================
        def init_ui(self):
            top_frame = tk.Frame(self)
            top_frame.pack(fill=tk.X, padx=10, pady=8)

            path_frame = tk.Frame(top_frame)
            path_frame.pack(fill=tk.X, pady=2)
            tk.Label(path_frame, text="Mod总路径:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
            path_entry = tk.Entry(path_frame, textvariable=self.mod_root_path, width=60, font=("Microsoft YaHei", 10))
            path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            browse_btn = tk.Button(path_frame, text="浏览选择", command=self.browse_path, font=("Microsoft YaHei", 10))
            browse_btn.pack(side=tk.LEFT)

            preset_frame = tk.Frame(top_frame)
            preset_frame.pack(fill=tk.X, pady=2)
            tk.Label(preset_frame, text="预设管理:", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
            self.preset_var = tk.StringVar(value=self.current_preset)
            preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var, values=list(self.presets.keys()), width=20)
            preset_combo.pack(side=tk.LEFT, padx=8)
            preset_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_preset(self.preset_var.get()))
            tk.Button(preset_frame, text="新建预设", command=self.new_preset, font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=2)
            tk.Button(preset_frame, text="保存当前到预设", command=lambda: self.save_current_state_to_preset(self.current_preset), font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=2)
            tk.Button(preset_frame, text="删除预设", command=self.delete_preset, font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=2)

            self.auto_run_var = tk.BooleanVar(value=False)
            auto_run_cb = tk.Checkbutton(preset_frame, text="启动后自动随机化", variable=self.auto_run_var,
                                         command=lambda: self.save_current_state_to_preset(self.current_preset), font=("Microsoft YaHei", 9))
            auto_run_cb.pack(side=tk.LEFT, padx=10)

            tk.Frame(self, height=1, bg="#cccccc").pack(fill=tk.X, padx=10)

            main_frame = tk.Frame(self)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

            # 左侧：角色列表
            left_frame = tk.Frame(main_frame, width=240)
            left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
            tk.Label(left_frame, text="角色列表", font=("Microsoft YaHei", 11, "bold")).pack(anchor=tk.W)
            tk.Label(left_frame, text="点击色块切换是否处理此角色（绿=处理、红=跳过）", font=("Microsoft YaHei", 9), fg="#666666").pack(anchor=tk.W)
            self.char_select_all_btn = tk.Button(left_frame, text="全选/取消全选", command=self.toggle_select_all_chars, font=("Microsoft YaHei", 9))
            self.char_select_all_btn.pack(anchor=tk.W, pady=2)

            self.char_canvas = tk.Canvas(left_frame, width=220, highlightthickness=0)
            char_scrollbar = tk.Scrollbar(left_frame, orient="vertical", command=self.char_canvas.yview)
            self.char_frame = tk.Frame(self.char_canvas)
            self.char_frame.bind("<Configure>", lambda e: self.char_canvas.configure(scrollregion=self.char_canvas.bbox("all")))
            self.char_canvas.create_window((0, 0), window=self.char_frame, anchor="nw")
            self.char_canvas.configure(yscrollcommand=char_scrollbar.set)
            self.char_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            char_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # 右侧：Mod配置区
            right_frame = tk.Frame(main_frame)
            right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            tk.Label(right_frame, text="Mod配置", font=("Microsoft YaHei", 11, "bold")).pack(anchor=tk.W)
            tk.Label(right_frame, text="点击色块切换启用/禁用；🔒=锁定（不参与随机），分组内独立随机", font=("Microsoft YaHei", 9), fg="#666666").pack(anchor=tk.W)

            btn_row = tk.Frame(right_frame)
            btn_row.pack(anchor=tk.W, pady=2)
            self.mod_lock_all_btn = tk.Button(btn_row, text="全选/取消全选锁定", command=self.toggle_lock_all_mods, font=("Microsoft YaHei", 9))
            self.mod_lock_all_btn.pack(side=tk.LEFT, padx=(0, 5))
            self.new_group_btn = tk.Button(btn_row, text="新建自定义分组", command=self.create_new_group, font=("Microsoft YaHei", 9))
            self.new_group_btn.pack(side=tk.LEFT)

            self.mod_canvas = tk.Canvas(right_frame, highlightthickness=0)
            mod_scrollbar = tk.Scrollbar(right_frame, orient="vertical", command=self.mod_canvas.yview)
            self.mod_frame = tk.Frame(self.mod_canvas)
            self.mod_frame.bind("<Configure>", lambda e: self.mod_canvas.configure(scrollregion=self.mod_canvas.bbox("all")))
            self.mod_canvas.create_window((0, 0), window=self.mod_frame, anchor="nw")
            self.mod_canvas.configure(yscrollcommand=mod_scrollbar.set)
            self.mod_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            mod_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            tk.Frame(self, height=1, bg="#cccccc").pack(fill=tk.X, padx=10)

            # 底部：日志
            bottom_frame = tk.Frame(self)
            bottom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
            run_btn = tk.Button(bottom_frame, text="开始随机处理", command=self.run_process, bg="#4CAF50", fg="white", font=("Microsoft YaHei", 12, "bold"), height=2)
            run_btn.pack(pady=(0, 8))

            tk.Label(bottom_frame, text="处理日志", font=("Microsoft YaHei", 11, "bold")).pack(anchor=tk.W)
            log_frame = tk.Frame(bottom_frame)
            log_frame.pack(fill=tk.BOTH, expand=True)
            self.log_text = tk.Text(log_frame, height=12, font=("Consolas", 9), state=tk.DISABLED, bg="#f8f8f8", wrap=tk.WORD)
            log_scrollbar = tk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
            self.log_text.config(yscrollcommand=log_scrollbar.set)
            log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            self.log_text.tag_config("green", foreground="green")
            self.log_text.tag_config("gray", foreground="gray")

        # ==================== 角色与Mod加载 ====================
        def browse_path(self):
            path = filedialog.askdirectory(title="选择Mod总目录（SkinSelectImpact文件夹）")
            if path:
                self.mod_root_path.set(path)
                self.load_characters()
                self.apply_preset(self.current_preset)
                self.save_config()

        def load_characters(self):
            path = self.mod_root_path.get()
            if not os.path.isdir(path):
                return
            for widget in self.char_frame.winfo_children():
                widget.destroy()
            self.char_check_vars.clear()
            self.char_color_blocks.clear()
            chars = [entry for entry in os.listdir(path) if os.path.isdir(os.path.join(path, entry))]
            chars.sort()
            for char in chars:
                var = tk.BooleanVar(value=True)
                self.char_check_vars[char] = var
                row = tk.Frame(self.char_frame)
                row.pack(fill=tk.X, pady=3)
                color_block = tk.Label(row, bg="green", width=3, height=1, relief="raised", cursor="hand2")
                color_block.pack(side=tk.LEFT, padx=3)
                self.char_color_blocks[char] = color_block
                def toggle(char=char, block=color_block):
                    new_state = not self.char_check_vars[char].get()
                    self.char_check_vars[char].set(new_state)
                    block.config(bg="green" if new_state else "red")
                    self.save_current_state_to_preset(self.current_preset)
                color_block.bind("<Button-1>", lambda e, c=char, bl=color_block: toggle(c, bl))
                label = tk.Label(row, text=char, font=("Microsoft YaHei", 11), cursor="hand2")
                label.pack(side=tk.LEFT, padx=5)
                label.bind("<Button-1>", lambda e, c=char: self.on_char_click(c))
            if self.current_char and self.current_char in self.char_check_vars:
                self.load_mods_of_char()
            else:
                self.current_char = None
                for widget in self.mod_frame.winfo_children():
                    widget.destroy()

        def on_char_click(self, char_name):
            self.current_char = char_name
            self.load_mods_of_char()

        def load_mods_of_char(self):
            for widget in self.mod_frame.winfo_children():
                widget.destroy()
            char_path = os.path.join(self.mod_root_path.get(), self.current_char)
            if not os.path.isdir(char_path):
                return
            mods_info = []
            for entry in os.listdir(char_path):
                entry_path = os.path.join(char_path, entry)
                if not os.path.isdir(entry_path):
                    continue
                if entry.startswith("DISABLED_"):
                    original_name = entry[9:]
                    enabled = False
                else:
                    original_name = entry
                    enabled = True
                locked = (self.current_char in self.locked_mods and original_name in self.locked_mods[self.current_char])
                in_custom_group = False
                if self.current_char in self.group_mods:
                    for g_mods in self.group_mods[self.current_char].values():
                        if original_name in g_mods:
                            in_custom_group = True
                            break
                mods_info.append((original_name, entry, enabled, locked, in_custom_group))

            def sort_key(x):
                original_name, _, enabled, locked, in_custom_group = x
                if locked: priority = 0
                elif in_custom_group and enabled: priority = 1
                elif not in_custom_group and enabled: priority = 2
                elif in_custom_group and not enabled: priority = 3
                else: priority = 4
                return (priority, original_name)
            mods_info.sort(key=sort_key)

            if not mods_info:
                tk.Label(self.mod_frame, text="该角色下没有找到Mod", font=("Microsoft YaHei", 9), fg="#666666").pack()
                return

            header = tk.Frame(self.mod_frame)
            header.pack(fill=tk.X, pady=5)
            header.columnconfigure(0, minsize=60)
            header.columnconfigure(1, minsize=70)
            header.columnconfigure(2, weight=1)
            header.columnconfigure(3, minsize=120)
            tk.Label(header, text="状态", width=8, font=("Microsoft YaHei", 9, "bold")).grid(row=0, column=0)
            tk.Label(header, text="锁定", width=8, font=("Microsoft YaHei", 9, "bold")).grid(row=0, column=1)
            tk.Label(header, text="Mod名称", width=25, font=("Microsoft YaHei", 9, "bold")).grid(row=0, column=2, sticky="w")
            tk.Label(header, text="分组", width=15, font=("Microsoft YaHei", 9, "bold")).grid(row=0, column=3)

            group_options = ["普通分组"]
            if self.current_char in self.group_mods:
                group_options.extend(self.group_mods[self.current_char].keys())

            for original_name, current_name, enabled, locked, _ in mods_info:
                row = tk.Frame(self.mod_frame)
                row.pack(fill=tk.X, pady=2)
                row.columnconfigure(0, minsize=60)
                row.columnconfigure(1, minsize=70)
                row.columnconfigure(2, weight=1)
                row.columnconfigure(3, minsize=120)

                color = "green" if enabled else "red"
                status_label = tk.Label(row, bg=color, width=4, height=1, relief="raised", cursor="hand2")
                status_label.grid(row=0, column=0, padx=5, pady=2)
                status_label.bind("<Button-1>", lambda e, m=original_name, cur=current_name: self.manual_toggle_mod(m, cur))

                lock_label = tk.Label(row, text=u"🔒" if locked else u"  ", width=2, font=("Segoe UI", 12), cursor="hand2")
                lock_label.grid(row=0, column=1, padx=5)
                lock_label.bind("<Button-1>", lambda e, m=original_name, lab=lock_label: self.toggle_lock_icon(m, lab))

                name_label = tk.Label(row, text=original_name, anchor="w", font=("Microsoft YaHei", 9))
                name_label.grid(row=0, column=2, sticky="w", padx=5)

                current_group = "普通分组"
                if self.current_char in self.group_mods:
                    for g_name, g_mods in self.group_mods[self.current_char].items():
                        if original_name in g_mods:
                            current_group = g_name
                            break
                group_var = tk.StringVar(value=current_group)
                group_menu = tk.OptionMenu(row, group_var, *group_options,
                                           command=lambda g, m=original_name, v=group_var: self.change_group(m, g, v))
                group_menu.config(font=("Microsoft YaHei", 9))
                group_menu.grid(row=0, column=3, padx=5)

        # ==================== 锁定与分组操作 ====================
        def toggle_lock_icon(self, mod_name, label_widget):
            char = self.current_char
            if char in self.locked_mods and mod_name in self.locked_mods[char]:
                self.locked_mods[char].remove(mod_name)
                if not self.locked_mods[char]:
                    del self.locked_mods[char]
                label_widget.config(text=u"  ")
            else:
                if char not in self.locked_mods:
                    self.locked_mods[char] = []
                if mod_name not in self.locked_mods[char]:
                    self.locked_mods[char].append(mod_name)
                label_widget.config(text=u"🔒")
            self.save_current_state_to_preset(self.current_preset)

        def manual_toggle_mod(self, original_name, current_name):
            char_path = os.path.join(self.mod_root_path.get(), self.current_char)
            current_full = os.path.join(char_path, current_name)
            if not os.path.exists(current_full):
                self.log(u"错误：Mod文件夹不存在 {}".format(current_full))
                return
            if current_name.startswith("DISABLED_"):
                new_name = original_name
            else:
                new_name = u"DISABLED_{}".format(original_name)
            target_full = os.path.join(char_path, new_name)
            if os.path.exists(target_full):
                self.log(u"错误：目标路径已存在 {}".format(target_full))
                return
            try:
                os.rename(current_full, target_full)
                self.log(u"手动开关：{} -> {}".format(current_name, new_name))
                self.load_mods_of_char()
            except Exception as e:
                self.log(u"手动开关失败：{}".format(str(e)))

        def toggle_select_all_chars(self):
            if not self.char_check_vars:
                return
            all_selected = all(var.get() for var in self.char_check_vars.values())
            new_state = not all_selected
            for char, var in self.char_check_vars.items():
                var.set(new_state)
                if char in self.char_color_blocks:
                    self.char_color_blocks[char].config(bg="green" if new_state else "red")
            self.save_current_state_to_preset(self.current_preset)

        def toggle_lock_all_mods(self):
            if not self.current_char:
                return
            char = self.current_char
            char_path = os.path.join(self.mod_root_path.get(), char)
            if not os.path.isdir(char_path):
                return
            all_mods = []
            for entry in os.listdir(char_path):
                if not os.path.isdir(os.path.join(char_path, entry)):
                    continue
                if entry.startswith("DISABLED_"):
                    all_mods.append(entry[9:])
                else:
                    all_mods.append(entry)
            current_locked = self.locked_mods.get(char, [])
            all_selected = len(current_locked) == len(all_mods)
            new_state = not all_selected
            if new_state:
                self.locked_mods[char] = all_mods
            else:
                if char in self.locked_mods:
                    del self.locked_mods[char]
            self.load_mods_of_char()
            self.save_current_state_to_preset(self.current_preset)

        def change_group(self, mod_name, group_name, var):
            char = self.current_char
            if char in self.group_mods:
                for g_name, g_mods in list(self.group_mods[char].items()):
                    if mod_name in g_mods:
                        g_mods.remove(mod_name)
                        if not g_mods:
                            del self.group_mods[char][g_name]
                        break
            if group_name != "普通分组":
                if char not in self.group_mods:
                    self.group_mods[char] = {}
                if group_name not in self.group_mods[char]:
                    self.group_mods[char][group_name] = []
                if mod_name not in self.group_mods[char][group_name]:
                    self.group_mods[char][group_name].append(mod_name)
            self.save_current_state_to_preset(self.current_preset)

        def create_new_group(self):
            if not self.current_char:
                messagebox.showwarning("提示", "请先选择一个角色！")
                return
            group_name = simpledialog.askstring("新建分组", "请输入新分组的名称：", parent=self)
            if not group_name or not group_name.strip():
                return
            group_name = group_name.strip()
            if self.current_char in self.group_mods and group_name in self.group_mods[self.current_char]:
                messagebox.showinfo("提示", "该分组已经存在！")
                return
            if self.current_char not in self.group_mods:
                self.group_mods[self.current_char] = {}
            self.group_mods[self.current_char][group_name] = []
            self.load_mods_of_char()
            self.save_current_state_to_preset(self.current_preset)
            messagebox.showinfo("成功", u"分组「{}」创建完成！".format(group_name))

        def run_process(self):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.DISABLED)

            mod_root = self.mod_root_path.get()
            if not os.path.isdir(mod_root):
                messagebox.showerror("错误", "请先选择正确的Mod总路径！")
                return

            preset = {
                "角色勾选": {char: var.get() for char, var in self.char_check_vars.items()},
                "锁定配置": self.locked_mods,
                "分组配置": self.group_mods,
                "auto_run": self.auto_run_var.get()
            }
            success = run_randomizer_from_preset(mod_root, preset, self.log)
            if not success:
                messagebox.showerror("错误", "随机化处理失败，请检查日志。")
            if self.current_char and self.current_char in self.char_check_vars:
                self.load_mods_of_char()

        def log(self, msg, color=None):
            self.log_text.config(state=tk.NORMAL)
            if color == "green":
                self.log_text.insert(tk.END, msg + "\n", "green")
            elif color == "gray":
                self.log_text.insert(tk.END, msg + "\n", "gray")
            else:
                self.log_text.insert(tk.END, msg + "\n")
            self.log_text.config(state=tk.DISABLED)
            self.log_text.see(tk.END)
            self.update_idletasks()

    if __name__ == "__main__":
        app = ZZMIModManagerApp()
        app.mainloop()

else:
    # 无界面自动模式
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, "mod_manager_config.json")
    presets_file = os.path.join(script_dir, "mod_manager_presets.json")
    mod_root, current_preset = load_config(config_file)
    if not mod_root or not os.path.isdir(mod_root):
        print("错误：未找到有效的Mod总路径，请先运行图形界面进行配置。")
        sys.exit(1)
    presets = load_preset_file(presets_file)
    if current_preset not in presets:
        print("错误：预设 '{}' 不存在。".format(current_preset))
        sys.exit(1)
    preset = presets[current_preset]
    success = run_randomizer_from_preset(mod_root, preset, log_func=print)
    sys.exit(0 if success else 1)