# core/graph.py
"""
核心图构建模块。

提供一个通用的函数 `build_agent_app` 来根据状态、节点和边
快速组装一个 LangGraph 应用。
"""
from langgraph.graph import StateGraph, END

def build_agent_app(
    state_schema,
    nodes,
    entry_point,
    edges=None,
    conditional_edges=None
):
    """
    一个通用的图构建函数，支持条件边。

    Args:
        state_schema: Agent 状态的 TypedDict 定义。
        nodes (dict): 节点名称到节点函数的映射。
        entry_point (str): 图的入口节点名称。
        edges (list, optional): 普通边的列表，格式为 [("source", "target")]。
        conditional_edges (dict, optional): 条件边的配置。
            格式为: {
                "source_node": {
                    "path": path_function,
                    "path_map": {"path_name_1": "target_node_1", ...}
                }
            }

    Returns:
        A compiled LangGraph application.
    """
    workflow = StateGraph(state_schema)

    # 1. 添加所有节点
    for name, node in nodes.items():
        workflow.add_node(name, node)

    # 2. 设置入口点
    workflow.set_entry_point(entry_point)

    # 3. 添加所有普通边
    if edges:
        for start_key, end_key in edges:
            workflow.add_edge(start_key, end_key)

    # 4. 添加所有条件边
    if conditional_edges:
        for source_node, config in conditional_edges.items():
            path_function = config["path"]
            path_map = config.get("path_map", {})
            workflow.add_conditional_edges(source_node, path_function, path_map)

    # 5. 编译并返回应用
    return workflow.compile()