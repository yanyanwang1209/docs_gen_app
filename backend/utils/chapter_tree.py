"""章节树操作工具：展平、编号、构建树"""
from typing import List, Optional, Dict
import json
import copy


def flatten_tree(nodes: list, depth: int = 0) -> list:
    """将章节树按深度优先展平为列表"""
    result = []
    for node in sorted(nodes, key=lambda n: n.get("sort_order", 0)):
        node_copy = dict(node)
        node_copy["_depth"] = depth
        result.append(node_copy)
        children = node.get("children", [])
        if children:
            result.extend(flatten_tree(children, depth + 1))
    return result


def auto_number(nodes: list, parent_numbers: Optional[List[int]] = None) -> list:
    """自动为章节编号（1, 1.1, 1.1.1...）"""
    if parent_numbers is None:
        parent_numbers = []

    result = []
    for i, node in enumerate(nodes):
        current_numbers = parent_numbers + [i + 1]
        number_str = ".".join(str(n) for n in current_numbers)

        # 去除旧编号，添加新编号
        title = node.get("title", "")
        # 移除已有的编号前缀（如 "1. " 或 "1.1 "）
        parts = title.split(" ", 1)
        if parts and parts[0].replace(".", "").isdigit():
            title = parts[1] if len(parts) > 1 else title
        node["title"] = f"{number_str} {title}"

        # 递归处理子节点
        children = node.get("children", [])
        if children:
            node["children"] = auto_number(children, current_numbers)

        result.append(node)
    return result


def build_tree_from_list(flat_nodes: list) -> list:
    """从扁平节点列表构建树结构"""
    node_map: Dict[str, dict] = {}
    roots = []

    for node in flat_nodes:
        node_id = node.get("id", "")
        node_copy = dict(node)
        node_copy["children"] = []
        node_map[node_id] = node_copy

    for node in flat_nodes:
        node_id = node.get("id", "")
        parent_id = node.get("parent_id")
        if parent_id and parent_id in node_map:
            node_map[parent_id]["children"].append(node_map[node_id])
        else:
            roots.append(node_map[node_id])

    return roots


def get_node_path(tree: list, target_id: str) -> list:
    """获取从根到目标节点的路径（用于生成上下文）"""
    def _find(nodes, path):
        for node in nodes:
            current_path = path + [node]
            if node.get("id") == target_id:
                return current_path
            children = node.get("children", [])
            if children:
                result = _find(children, current_path)
                if result:
                    return result
        return None

    return _find(tree, target_id) or []


def count_chapters(nodes: list) -> int:
    """统计章节总数（不包括 title_only 为 True 的节点）"""
    count = 0
    for node in nodes:
        if not node.get("title_only", False):
            count += 1
        children = node.get("children", [])
        if children:
            count += count_chapters(children)
    return count


def get_all_chapter_ids(nodes: list) -> list:
    """获取所有章节 ID（深度优先）"""
    ids = []
    for node in nodes:
        ids.append(node.get("id", ""))
        children = node.get("children", [])
        if children:
            ids.extend(get_all_chapter_ids(children))
    return ids


def deep_copy_tree(nodes: list) -> list:
    """深拷贝章节树"""
    return json.loads(json.dumps(nodes, default=str))