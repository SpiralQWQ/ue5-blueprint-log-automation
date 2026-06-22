#!/usr/bin/env python3
"""
export_bp_metadata.py — UE5 蓝图资产元数据导出工具
====================================================
必须在 UE5 编辑器 Python 环境中运行。不支持外部 Python 解释器。

用法（任选一种）：
  1. 在 UE5 Output Log 中选择 Python 模式，执行：
     py "E:/AAA.Program/UEStudy/Mydemo/tools/export_bp_metadata.py"

  2. 或在 UE5 Python 控制台中：
     import sys
     sys.path.append(r"E:/AAA.Program/UEStudy/Mydemo/tools")
     import export_bp_metadata
     export_bp_metadata.main()

输出文件：<项目根>/AssessStatus_Json/ue_blueprint_status_<项目名>.json
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# 配置区
# ============================================================================

# 输出路径 —— 自动按项目名分文件，存放于项目根目录下的 AssessStatus_Json/
# 注意：OUTPUT_FILE 在 main() 中延迟赋值（此时 unreal 已就绪），避免模块导入时取错项目名
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR: str = os.path.join(_PROJECT_ROOT, "AssessStatus_Json")

def _get_project_name() -> str:
    """获取当前 UE 项目名。优先用 UE5 API（运行时），回退到磁盘扫描。"""
    # 方法 1：UE5 运行时 API（最可靠，必须在 main() 中调用而非模块导入时）
    try:
        if UNREAL_AVAILABLE:
            path = unreal.Paths.get_project_file_path()
            if path:
                return path.split("/")[-1].replace(".uproject", "")
    except Exception:
        pass
    # 方法 2：递归扫描子目录中的 .uproject 文件（仅外部语法检查时回退）
    for root, dirs, files in os.walk(_PROJECT_ROOT):
        for f in files:
            if f.endswith(".uproject"):
                return f.replace(".uproject", "")
    raise FileNotFoundError(
        f"[FATAL] {_PROJECT_ROOT} 及其子目录下未找到 .uproject 文件，无法确定项目名。"
    )

# 延迟到 main() 中赋值，避免模块导入时 unreal 未就绪导致取错项目名
OUTPUT_FILE: str = ""

# 扫描范围
SCAN_PATHS: List[str] = ["/Game/"]

# 白名单排除 —— 这些路径下的蓝图不会被导出
EXCLUDE_PREFIXES: Tuple[str, ...] = (
    "/Engine/",
    "/Game/StarterContent/",
    "/Game/FirstPerson/",
    "/Game/Characters/",
    "/Game/Collections/",
    "/Game/Developers/",
    "/Game/Input/",
    "/Game/__ExternalActors__/",
    "/Game/__ExternalObjects__/",
)

# 要导出的蓝图类名（不仅限于 Blueprint，也包括 Widget 等）
BLUEPRINT_CLASS_NAMES: Tuple[str, ...] = (
    "Blueprint",
    "WidgetBlueprint",
    "AnimBlueprint",
)

# 内部函数前缀 —— 这些不会被写入函数列表
INTERNAL_FUNC_PREFIXES: Tuple[str, ...] = (
    "ExecuteUbergraph",
    "InpActEvt_",
    "InpAxisEvt_",
    "Receive",
    "UserConstructionScript",
    "BndEvt__",
)

# 内部变量前缀 —— 元数据辅助变量，非用户自定义
INTERNAL_VAR_PREFIXES: Tuple[str, ...] = (
    "UberGraphFrame",
    "bIsEditorOnly",
)

# ============================================================================
# 安全导入 unreal（仅 UE5 内部可用）
# ============================================================================

try:
    import unreal
    UNREAL_AVAILABLE = True
except ModuleNotFoundError:
    UNREAL_AVAILABLE = False
    # 创建一个占位对象，防止后续代码在语法检查时直接 NameError
    class _FakeUnreal:
        """占位符 — 仅在外部语法检查时使用，实际运行时由 UE5 提供。"""
        pass
    unreal = _FakeUnreal()


# ============================================================================
# 辅助工具
# ============================================================================

def _get_asset_file_path(package_name: str) -> str:
    """
    将包路径转换为磁盘上的绝对文件路径。

    Args:
        package_name: 如 /Game/MyMaps/BluePrint/BP_Player

    Returns:
        /Path/To/Your/UE_Project/Content/MyMaps/BluePrint/BP_Player.uasset
    """
    try:
        content_dir = unreal.Paths.convert_relative_path_to_full(
            unreal.Paths.project_content_dir()
        )
        # 去掉 /Game/ 前缀，替换为 Content 目录
        if package_name.startswith("/Game/"):
            relative = package_name[6:]  # 去掉 "/Game/"
        else:
            relative = package_name.lstrip("/")
        return os.path.join(content_dir, relative + ".uasset")
    except Exception:
        return ""


def _get_file_timestamp(package_name: str) -> Optional[str]:
    """获取 .uasset 文件的最后修改时间（ISO 8601）。"""
    file_path = _get_asset_file_path(package_name)
    if file_path and os.path.isfile(file_path):
        try:
            mtime = os.path.getmtime(file_path)
            return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        except OSError:
            pass
    return None


def _get_file_size_kb(package_name: str) -> Optional[float]:
    """获取 .uasset 文件大小（KB）。"""
    file_path = _get_asset_file_path(package_name)
    if file_path and os.path.isfile(file_path):
        try:
            return round(os.path.getsize(file_path) / 1024.0, 2)
        except OSError:
            pass
    return None


def _is_excluded(package_name: str) -> bool:
    """检查路径是否在白名单排除列表中。"""
    for prefix in EXCLUDE_PREFIXES:
        if package_name.startswith(prefix):
            return True
    return False


# ============================================================================
# 蓝图数据提取
# ============================================================================

def extract_parent_class(asset_data, loaded_bp) -> str:
    """
    获取蓝图的父类名称。

    Returns:
        父类的简短类名，如 "Pawn"、"Actor"、"UserWidget"
    """
    # 方法 1：从 AssetData 标签读取（最快，不依赖加载）
    try:
        parent_path = asset_data.get_tag_value("ParentClass")
        if parent_path:
            # ParentClass 通常是完整路径，如 "Class'/Script/Engine.Pawn'"
            # 或 "Class /Script/CoreUObject.Class'/Script/Engine.Pawn'"
            # 提取末尾的类名
            if "'" in parent_path:
                parent_path = parent_path.split("'")[-2] if parent_path.count("'") >= 2 else parent_path
            if "." in parent_path:
                return parent_path.rsplit(".", 1)[-1]
            return parent_path.split("/")[-1]
    except Exception:
        pass

    # 方法 2：从已加载的蓝图对象读取
    try:
        gen_class = loaded_bp.generated_class()
        super_class = gen_class.get_class().get_super_class()
        if super_class:
            return super_class.get_name()
    except Exception:
        pass

    return "Unknown"


def extract_components(loaded_bp) -> List[Dict[str, str]]:
    """
    提取 SimpleConstructionScript 中的组件列表。

    Returns:
        [{"name": "StaticMeshComponent0", "class": "StaticMeshComponent"}, ...]
    """
    components: List[Dict[str, str]] = []
    try:
        scs = loaded_bp.get_editor_property("simple_construction_script")
        if scs is None:
            return components

        all_nodes = scs.get_editor_property("all_nodes")
        if all_nodes is None:
            return components

        for node in all_nodes:
            try:
                node_class = node.get_class().get_name()
                if "SCS_Node" in node_class or node_class == "SCS_Node":
                    # 尝试获取组件模板
                    try:
                        comp_template = node.get_editor_property("component_template")
                        if comp_template is not None:
                            comp_name = comp_template.get_name()
                            comp_class = comp_template.get_class().get_name()
                            components.append({
                                "name": comp_name,
                                "class": comp_class,
                            })
                    except Exception:
                        pass
                    # 另一种方式：读取变量名
                    try:
                        internal_var = node.get_editor_property("internal_variable_name")
                        if internal_var and internal_var not in [c["name"] for c in components]:
                            components.append({
                                "name": str(internal_var),
                                "class": "Unknown",
                            })
                    except Exception:
                        pass
            except Exception:
                continue
    except Exception:
        pass

    return components


def extract_variables(asset_data, loaded_bp) -> List[Dict[str, Any]]:
    """
    提取蓝图的自定义变量列表。

    Returns:
        [{"name": "MoveSpeed", "type": "float", "default_value": "600.0", ...}, ...]
    """
    variables: List[Dict[str, Any]] = []

    # 方法 1：从 AssetData 标签获取变量列表（部分信息）
    try:
        # 尝试读取蓝图分类标签
        _ = asset_data.get_tag_value("BlueprintCategory")
    except Exception:
        pass

    # 方法 2：从 Blueprint.new_variables（UE 5.0-5.2 可用）
    try:
        new_vars = loaded_bp.get_editor_property("new_variables")
        if new_vars is not None:
            for var in new_vars:
                try:
                    var_name = str(var.get_editor_property("var_name"))
                    # 跳过内部变量
                    if any(var_name.startswith(p) for p in INTERNAL_VAR_PREFIXES):
                        continue

                    var_type = str(var.get_editor_property("var_type"))
                    var_guid = str(var.get_editor_property("var_guid"))
                    friendly = str(var.get_editor_property("friendly_name") or "")
                    category = str(var.get_editor_property("category") or "")

                    # 默认值
                    default_value = ""
                    try:
                        default_value = str(var.get_editor_property("default_value") or "")
                    except Exception:
                        pass

                    # 是否为数组
                    is_array = False
                    try:
                        container_type = str(var.get_editor_property("container_type") or "")
                        is_array = "Array" in container_type
                    except Exception:
                        pass

                    # 是否为可编辑/暴露
                    is_editable = False
                    try:
                        prop_flags = var.get_editor_property("property_flags")
                        if prop_flags is not None:
                            is_editable = (int(prop_flags) & (1 << 0)) != 0  # CPF_Edit
                    except Exception:
                        pass

                    variables.append({
                        "name": var_name,
                        "type": var_type,
                        "is_array": is_array,
                        "is_editable": is_editable,
                        "category": category,
                        "friendly_name": friendly or var_name,
                        "default_value": default_value,
                    })
                except Exception:
                    continue
    except Exception:
        pass

    return variables


def extract_functions(loaded_bp) -> List[Dict[str, str]]:
    """
    提取蓝图中的自定义函数/事件列表。

    注意：UE5 Python API 对蓝图节点图的访问有限，
    这里只能获取到 UFunction 级别的函数（如自定义函数、重写函数）。

    Returns:
        [{"name": "OnOverlapFood", "type": "Event"}, ...]
    """
    functions: List[Dict[str, str]] = []
    try:
        gen_class = loaded_bp.generated_class()
        uclass = gen_class.get_class()

        for ufunc in uclass.get_functions():
            try:
                func_name = ufunc.get_name()

                # 跳过 UE 内部函数
                if any(func_name.startswith(p) for p in INTERNAL_FUNC_PREFIXES):
                    continue
                if func_name.startswith("__") or func_name.startswith("K2Node_"):
                    continue

                # 判断函数类型
                func_type = "Function"
                func_flags = ufunc.get_editor_property("function_flags")
                if func_flags is not None:
                    flags_int = int(func_flags)
                    # BlueprintEvent = Has FUNC_BlueprintEvent (1<<11 = 2048)
                    if flags_int & 2048:
                        func_type = "Event"

                functions.append({
                    "name": func_name,
                    "type": func_type,
                })
            except Exception:
                continue
    except Exception:
        pass

    return functions


def extract_interfaces(loaded_bp) -> List[str]:
    """
    提取蓝图实现的接口列表。

    Returns:
        ["BPI_Interact", "BPI_Player_State", ...]
    """
    interfaces: List[str] = []
    try:
        implemented = loaded_bp.get_editor_property("implemented_interfaces")
        if implemented is not None:
            for iface in implemented:
                try:
                    iface_class = iface.get_editor_property("interface")
                    if iface_class is not None:
                        interfaces.append(iface_class.get_name())
                except Exception:
                    pass
    except Exception:
        pass
    return interfaces


def extract_delegate_bindings(loaded_bp) -> List[Dict[str, str]]:
    """
    提取组件委托绑定信息（如 OnComponentBeginOverlap 绑定到哪个函数）。

    Returns:
        [{"component": "Box", "event": "OnComponentBeginOverlap", "handler": "BndEvt__..."}]
    """
    bindings: List[Dict[str, str]] = []
    try:
        comp_bindings = loaded_bp.get_editor_property("component_delegate_bindings")
        if comp_bindings is not None:
            for binding in comp_bindings:
                try:
                    comp_name = str(binding.get_editor_property("component_property_name") or "")
                    delegate_prop = str(binding.get_editor_property("delegate_property_name") or "")
                    bindings.append({
                        "component": comp_name,
                        "event": delegate_prop,
                    })
                except Exception:
                    continue
    except Exception:
        pass
    return bindings


# ============================================================================
# 主扫描逻辑
# ============================================================================

def scan_blueprints() -> List[Dict[str, Any]]:
    """
    扫描 /Game/ 下所有蓝图资产并提取元数据。

    Returns:
        蓝图数据列表
    """
    if not UNREAL_AVAILABLE:
        raise RuntimeError(
            "unreal 模块不可用。此脚本必须在 UE5 编辑器内部执行。\n"
            "在 UE5 Output Log 中选择 Python 模式后运行：\n"
            f"py \"{os.path.join(OUTPUT_DIR, 'tools', 'export_bp_metadata.py')}\""
        )

    results: List[Dict[str, Any]] = []

    # ---- 获取 AssetRegistry ----
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

    # 等待资产扫描完成（确保新创建的蓝图也被纳入）
    unreal.log("⏳ 等待 AssetRegistry 扫描完成...")
    asset_registry.wait_for_completion()
    unreal.log("✓ AssetRegistry 就绪")

    # ---- 扫描所有路径 ----
    all_assets: List = []
    for scan_path in SCAN_PATHS:
        try:
            assets = asset_registry.get_assets_by_path(
                scan_path, recursive=True, include_only_on_disk_assets=False
            )
            all_assets.extend(assets)
            unreal.log(f"  扫描 {scan_path}: 找到 {len(assets)} 个资产")
        except Exception as exc:
            unreal.log_warning(f"  ⚠ 扫描路径失败 {scan_path}: {exc}")

    unreal.log(f"\n📦 总计扫描到 {len(all_assets)} 个资产，正在过滤蓝图...")

    # ---- 过滤蓝图 ----
    blueprint_count = 0
    skipped_count = 0
    error_count = 0

    for asset_data in all_assets:
        try:
            # 获取资产基本信息
            asset_name = str(asset_data.asset_name)
            package_name = str(asset_data.package_name)

            # 跳过其他目录资产（Exclude 列表内的）
            if _is_excluded(package_name):
                skipped_count += 1
                continue

            # 获取资产类名
            try:
                asset_class = str(asset_data.asset_class_path.asset_name)
            except Exception:
                try:
                    asset_class = str(asset_data.asset_class)
                except Exception:
                    asset_class = ""

            # 仅处理蓝图类型
            if asset_class not in BLUEPRINT_CLASS_NAMES:
                continue

            blueprint_count += 1
            unreal.log(f"  📄 [{blueprint_count}] {asset_name} ({asset_class})")

            # ---- 尝试加载蓝图以获取深层数据 ----
            loaded_bp = None
            try:
                loaded_bp = unreal.EditorAssetLibrary.load_asset(package_name)
            except Exception:
                pass

            # ---- 构建蓝图条目 ----
            bp_entry: Dict[str, Any] = {
                "name": asset_name,
                "path": package_name,
                "type": asset_class,
            }

            # 父类
            bp_entry["parent_class"] = extract_parent_class(asset_data, loaded_bp)

            # 文件信息
            bp_entry["file_size_kb"] = _get_file_size_kb(package_name)
            bp_entry["last_modified"] = _get_file_timestamp(package_name)

            # ★ C++ 拓扑导出 — 完整节点图（节点/引脚/连线）
            if loaded_bp is not None:
                try:
                    topo_json = unreal.BlueprintTopologyExporter.dump_blueprint_logic_to_json(loaded_bp)
                    if topo_json and "error" not in topo_json[:50].lower():
                        bp_entry["topology"] = json.loads(topo_json).get("graphs", [])
                        total_nodes = sum(len(g.get("nodes", [])) for g in bp_entry["topology"])
                        unreal.log(f"      [OK] 拓扑: {len(bp_entry['topology'])} 图, {total_nodes} 节点")
                except Exception:
                    pass  # C++ 插件未编译时静默跳过

            # 组件
            if loaded_bp is not None:
                bp_entry["components"] = extract_components(loaded_bp)

                # 变量
                bp_entry["variables"] = extract_variables(asset_data, loaded_bp)

                # 函数
                bp_entry["functions"] = extract_functions(loaded_bp)

                # 接口
                bp_entry["interfaces"] = extract_interfaces(loaded_bp)

                # 委托绑定
                bp_entry["delegate_bindings"] = extract_delegate_bindings(loaded_bp)

                # 蓝图状态
                try:
                    bp_status = str(loaded_bp.get_editor_property("status") or "")
                    bp_entry["status"] = bp_status
                except Exception:
                    bp_entry["status"] = "Unknown"

            # 确保必要字段存在
            bp_entry.setdefault("components", [])
            bp_entry.setdefault("variables", [])
            bp_entry.setdefault("functions", [])
            bp_entry.setdefault("interfaces", [])
            bp_entry.setdefault("delegate_bindings", [])

            results.append(bp_entry)

        except Exception as exc:
            error_count += 1
            unreal.log_warning(f"  ❌ 处理资产时出错: {exc}")
            unreal.log_warning(f"     {traceback.format_exc()}")
            continue

    unreal.log(f"\n{'='*60}")
    unreal.log(f"📊 扫描完成: {blueprint_count} 个蓝图, {skipped_count} 个已跳过, {error_count} 个错误")
    unreal.log(f"{'='*60}")

    return results


# ============================================================================
# JSON 输出
# ============================================================================

def generate_json(blueprints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    将蓝图数据组织为最终 JSON 结构。
    """
    # 按路径排序
    blueprints.sort(key=lambda bp: bp.get("path", ""))

    # 统计
    stats = _compute_stats(blueprints)

    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tool_version": "1.0.0",
            "project": _get_project_name(),
            "total_blueprints": len(blueprints),
            "stats": stats,
        },
        "blueprints": blueprints,
    }


def _compute_stats(blueprints: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算统计摘要。"""
    stats: Dict[str, Any] = {
        "by_type": {},
        "by_parent_class": {},
        "total_variables": 0,
        "total_functions": 0,
        "total_components": 0,
        "total_interfaces": 0,
    }

    for bp in blueprints:
        # 按类型统计
        bp_type = bp.get("type", "Unknown")
        stats["by_type"][bp_type] = stats["by_type"].get(bp_type, 0) + 1

        # 按父类统计
        parent = bp.get("parent_class", "Unknown")
        stats["by_parent_class"][parent] = stats["by_parent_class"].get(parent, 0) + 1

        # 全局计数
        stats["total_variables"] += len(bp.get("variables", []))
        stats["total_functions"] += len(bp.get("functions", []))
        stats["total_components"] += len(bp.get("components", []))
        stats["total_interfaces"] += len(bp.get("interfaces", []))

    return stats


def save_json(data: Dict[str, Any]) -> str:
    """
    将数据写入 JSON 文件。

    Returns:
        输出文件的绝对路径
    """
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path) or OUTPUT_DIR, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=False)

    return output_path


# ============================================================================
# 入口
# ============================================================================

def main() -> None:
    """
    主入口 — 扫描蓝图资产并导出为 JSON。

    在 UE5 Output Log (Python) 中执行：
        py "E:/AAA.Program/UEStudy/Mydemo/tools/export_bp_metadata.py"
    """
    if not UNREAL_AVAILABLE:
        print("=" * 60)
        print("  此脚本必须在 UE5 编辑器 Python 环境中运行！")
        print("=" * 60)
        print()
        print("步骤：")
        print("  1. 打开你的 UE5 项目")
        print("  2. Window → Developer Tools → Output Log")
        print("  3. 在 Output Log 底部下拉框中选择 'Python' (不是 Cmd)")
        print("  4. 输入以下命令并回车：")
        print(f"     py \"{os.path.join(OUTPUT_DIR, 'tools', 'export_bp_metadata.py').replace(chr(92), '/')}\"")
        print()
        print("  或者复制粘贴以下命令：")
        print(f"  py \"E:/AAA.Program/UEStudy/Mydemo/tools/export_bp_metadata.py\"")
        print()
        return

    # 延迟赋值：此时 unreal 已完全就绪，确保取到正确的项目名
    global OUTPUT_FILE
    OUTPUT_FILE = f"ue_blueprint_status_{_get_project_name()}.json"

    try:
        unreal.log("=" * 60)
        unreal.log("🚀 UE5 蓝图元数据导出工具 v1.0.0")
        unreal.log("=" * 60)

        # 1. 扫描蓝图
        blueprints = scan_blueprints()

        if not blueprints:
            unreal.log_warning("⚠ 未找到任何蓝图资产。请检查：")
            unreal.log_warning("  1. 项目是否包含 Content/ 目录下的蓝图")
            unreal.log_warning("  2. EXCLUDE_PREFIXES 配置是否过于激进")
            return

        # 2. 生成 JSON
        unreal.log("\n📝 正在生成 JSON...")
        json_data = generate_json(blueprints)

        # 3. 写入文件
        output_path = save_json(json_data)

        unreal.log(f"\n✅ 导出成功！")
        unreal.log(f"📄 输出文件: {output_path}")
        unreal.log(f"📊 蓝图计数: {json_data['metadata']['total_blueprints']}")
        unreal.log(f"📏 文件大小: {os.path.getsize(output_path):,} bytes")

        # 4. 打印摘要
        stats = json_data["metadata"]["stats"]
        unreal.log(f"\n📋 摘要:")
        unreal.log(f"   类型分布: {stats['by_type']}")
        unreal.log(f"   父类 Top 5: {dict(sorted(stats['by_parent_class'].items(), key=lambda x: -x[1])[:5])}")
        unreal.log(f"   变量总数: {stats['total_variables']}")
        unreal.log(f"   函数总数: {stats['total_functions']}")
        unreal.log(f"   组件总数: {stats['total_components']}")

    except Exception as exc:
        unreal.log_error(f"❌ 导出失败: {exc}")
        unreal.log_error(traceback.format_exc())
        raise


# ============================================================================
# 脚本直接执行入口
# ============================================================================

if __name__ == "__main__":
    main()
