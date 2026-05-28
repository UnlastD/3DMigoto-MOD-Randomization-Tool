# -*- coding: utf-8 -*-
"""
ZZMI Mod 随机管理器 - 自动随机化入口（无界面，显示控制台）
打包命令：pyinstaller --onefile --console --name "ZZMI_Mod_Manager_Auto" ZZMI_Auto_Entry.py
"""

import os
import sys
import random
import json
import io

# ==================== 获取正确的工作目录 ====================
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

# ==================== 核心随机化函数（与UI版相同，略） ====================
# 以下代码与UI版中的核心函数一致，为避免重复，此处只写函数名，实际使用时需复制完整函数。
# 为了减少回答长度，这里只写框架，但最终代码中需要包含完整实现。
# 由于完整代码较长，这里提供一种方法：将上方 UI 版中的核心函数部分（count_enabled_mods 到 run_randomizer_from_preset）复制过来即可。
# 下面我直接完整写出自动版需要的所有函数（简化版，实际与UI版相同）。

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

def process_group(char_path, group_name, group_mod_map, log_func=print):
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

def run_randomizer_from_preset(mod_root, preset, log_func=print):
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

    # 最终统计
    log_func("\n" + "=" * 50)
    unprocessed = [c for c in all_chars if c not in target_chars]
    processed = target_chars
    if unprocessed:
        log_func("---未随机的角色---")
        max_len = max(len(c) for c in unprocessed) if unprocessed else 0
        for char in unprocessed:
            enabled, total = count_enabled_mods(os.path.join(mod_root, char))
            log_func("{:<{}}  {}/{}".format(char, max_len, enabled, total))
    if processed:
        log_func("---已随机的角色---")
        max_len = max(len(c) for c in processed) if processed else 0
        for char in processed:
            enabled, total = stats.get(char, count_enabled_mods(os.path.join(mod_root, char)))
            log_func("{:<{}}  {}/{}".format(char, max_len, enabled, total))
    log_func("=" * 50)
    log_func("所有角色处理完成！")
    return True

def load_preset_file(presets_file):
    default_preset = {"角色勾选": {}, "锁定配置": {}, "分组配置": {}, "auto_run": False}
    presets = {}
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

if __name__ == "__main__":
    config_file = os.path.join(BASE_DIR, "mod_manager_config.json")
    presets_file = os.path.join(BASE_DIR, "mod_manager_presets.json")
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