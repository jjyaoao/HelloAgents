"""任务依赖管理系统测试"""

import pytest
from unittest.mock import Mock

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv()

from hello_agents.tools.builtin.task_dep_manager import (
    TaskDepManager,
    TaskDepTool,
    DAGBuilder,
    NoteToolIntegration,
    Task,
    TaskStatus,
)


class TestDAGBuilder:
    """DAG构建器测试"""

    def test_add_edge(self):
        dag = DAGBuilder()
        dag.add_edge("A", "B")
        assert "B" in dag.graph["A"]
        assert dag.in_degree["B"] == 1

    def test_topological_sort_simple(self):
        dag = DAGBuilder()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")
        result = dag.topological_sort()
        assert result.index("A") < result.index("B") < result.index("C")

    def test_topological_sort_parallel(self):
        dag = DAGBuilder()
        dag.add_edge("A", "B")
        dag.add_edge("A", "C")
        dag.add_edge("B", "D")
        dag.add_edge("C", "D")
        result = dag.topological_sort()
        a_idx = result.index("A")
        assert result.index("B") > a_idx
        assert result.index("C") > a_idx
        assert result.index("D") > result.index("B")
        assert result.index("D") > result.index("C")

    def test_cycle_detection(self):
        dag = DAGBuilder()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")
        dag.add_edge("C", "A")
        assert dag.has_cycle() is True

    def test_no_cycle(self):
        dag = DAGBuilder()
        dag.add_edge("A", "B")
        dag.add_edge("B", "C")
        assert dag.has_cycle() is False

    def test_self_cycle_detection(self):
        dag = DAGBuilder()
        dag.add_edge("A", "A")
        assert dag.has_cycle() is True

    def test_independent_nodes(self):
        dag = DAGBuilder()
        dag.add_edge("A", "B")
        dag.add_edge("C", "D")
        result = dag.topological_sort()
        assert len(result) == 4

    def test_get_ready_tasks(self):
        dag = DAGBuilder()
        dag.add_edge("A", "B")
        dag.add_edge("A", "C")
        dag.add_edge("B", "D")
        dag.add_edge("C", "D")

        ready = dag.get_ready_tasks(set())
        assert "A" in ready

        ready = dag.get_ready_tasks({"A"})
        assert "B" in ready
        assert "C" in ready

        ready = dag.get_ready_tasks({"A", "B", "C"})
        assert "D" in ready

    def test_get_ready_tasks_excludes_completed(self):
        dag = DAGBuilder()
        dag.add_edge("A", "B")

        ready = dag.get_ready_tasks({"A", "B"})
        assert "A" not in ready
        assert "B" not in ready


class TestTask:
    """任务数据模型测试"""

    def test_create_task(self):
        task = Task(
            task_id="task_1", name="测试任务", description="测试描述", depends_on=[]
        )
        assert task.task_id == "task_1"
        assert task.name == "测试任务"
        assert task.status == TaskStatus.PENDING

    def test_task_with_dependencies(self):
        task = Task(task_id="task_2", name="任务2", depends_on=["task_1", "task_3"])
        assert len(task.depends_on) == 2
        assert "task_1" in task.depends_on

    def test_task_to_dict(self):
        task = Task(task_id="task_1", name="测试任务")
        d = task.to_dict()
        assert d["task_id"] == "task_1"
        assert d["status"] == "pending"
        assert d["name"] == "测试任务"

    def test_task_with_tags(self):
        task = Task(task_id="task_1", name="测试任务", tags=["tag1", "tag2"])
        assert len(task.tags) == 2
        assert "tag1" in task.tags

    def test_task_default_values(self):
        task = Task(task_id="t1", name="n1")
        assert task.status == TaskStatus.PENDING
        assert task.depends_on == []
        assert task.tags == []
        assert task.result is None
        assert task.error is None


class TestNoteToolIntegration:
    """NoteTool集成测试"""

    def test_create_task_note(self):
        mock_note_tool = Mock()
        mock_note_tool.run.return_value = "笔记创建成功"

        integration = NoteToolIntegration(mock_note_tool)
        task = Task(
            task_id="task_1",
            name="测试任务",
            description="测试描述",
            task_type="build",
            tags=["test"],
        )

        _ = integration.create_task_note(task)

        mock_note_tool.run.assert_called_once()
        call_args = mock_note_tool.run.call_args[0][0]
        assert call_args["action"] == "create"
        assert call_args["title"] == "任务: 测试任务"
        assert call_args["note_type"] == "task_state"
        assert "test" in call_args["tags"]
        assert "task_1" in call_args["tags"]

    def test_update_task_note(self):
        mock_note_tool = Mock()
        mock_note_tool.run.return_value = "笔记更新成功"

        integration = NoteToolIntegration(mock_note_tool)

        _ = integration.update_task_note("task_1", TaskStatus.COMPLETED)

        mock_note_tool.run.assert_called_once()

    def test_create_blocker_note(self):
        mock_note_tool = Mock()
        mock_note_tool.run.return_value = "阻塞项创建成功"

        integration = NoteToolIntegration(mock_note_tool)

        _ = integration.create_blocker_note("task_1", "等待前置任务完成")

        mock_note_tool.run.assert_called_once()
        call_args = mock_note_tool.run.call_args[0][0]
        assert call_args["note_type"] == "blocker"

    def test_record_conclusion(self):
        mock_note_tool = Mock()
        mock_note_tool.run.return_value = "结论创建成功"

        integration = NoteToolIntegration(mock_note_tool)

        _ = integration.record_conclusion("task_1", "任务执行成功")

        mock_note_tool.run.assert_called_once()
        call_args = mock_note_tool.run.call_args[0][0]
        assert call_args["note_type"] == "conclusion"


class TestTaskDepManager:
    """任务依赖管理器测试"""

    def test_register_task(self):
        manager = TaskDepManager()

        result = manager.register_task(
            task_id="task_1", name="任务1", description="测试任务"
        )

        assert "成功" in result
        assert "task_1" in manager.tasks
        assert manager.tasks["task_1"].name == "任务1"

    def test_register_task_with_dependency(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        result = manager.register_task(
            task_id="task_2", name="任务2", depends_on=["task_1"]
        )

        assert "成功" in result
        assert "task_1" in manager.tasks["task_2"].depends_on

    def test_register_task_duplicate(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        result = manager.register_task("task_1", "任务1重复")

        assert "已存在" in result
        assert len(manager.tasks) == 1

    def test_register_task_with_nonexistent_dependency(self):
        manager = TaskDepManager()

        result = manager.register_task(
            task_id="task_1", name="任务1", depends_on=["task_nonexistent"]
        )

        assert "不存在" in result
        assert "task_1" not in manager.tasks

    def test_register_cycle_detection(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])
        result = manager.add_dependency("task_1", ["task_2"])

        assert "循环依赖" in result

    def test_register_task_with_cyclic_dependency_at_creation(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])
        result = manager.register_task("task_1", "任务1", depends_on=["task_2"])

        assert "已存在" in result

    def test_add_dependency(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2")

        result = manager.add_dependency("task_2", ["task_1"])

        assert "成功" in result
        assert "task_1" in manager.tasks["task_2"].depends_on

    def test_add_cycle_via_dependency(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])
        result = manager.add_dependency("task_1", ["task_2"])

        assert "循环依赖" in result

    def test_remove_dependency(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])

        result = manager.remove_dependency("task_2", ["task_1"])

        assert "成功" in result
        assert "task_1" not in manager.tasks["task_2"].depends_on

    def test_get_execution_order(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])
        manager.register_task("task_3", "任务3", depends_on=["task_1"])
        manager.register_task("task_4", "任务4", depends_on=["task_2", "task_3"])

        order = manager.get_execution_order()

        assert order.index("task_1") < order.index("task_2")
        assert order.index("task_1") < order.index("task_3")
        assert order.index("task_2") < order.index("task_4")
        assert order.index("task_3") < order.index("task_4")

    def test_get_execution_order_with_error(self):
        manager = TaskDepManager()

        manager.register_task("A", "任务A")
        manager.register_task("B", "任务B", depends_on=["A"])

        result = manager.add_dependency("A", ["B"])

        assert "循环依赖" in result

    def test_get_ready_tasks(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])
        manager.register_task("task_3", "任务3")

        ready = manager.get_ready_tasks_internal()

        assert "task_1" in ready
        assert "task_3" in ready
        assert "task_2" not in ready

    def test_get_ready_tasks_after_completion(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])

        manager.tasks["task_1"].status = TaskStatus.COMPLETED

        ready = manager.get_ready_tasks_internal()

        assert "task_2" in ready

    def test_execute_task_success(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")

        def executor(task):
            return "执行成功"

        _ = manager.execute_task_internal("task_1", executor)

        assert manager.tasks["task_1"].status == TaskStatus.COMPLETED
        assert manager.tasks["task_1"].result == "执行成功"

    def test_execute_task_with_pending_dependency(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])

        result = manager.execute_task_internal("task_2")

        assert "依赖任务未完成" in result
        assert manager.tasks["task_2"].status == TaskStatus.PENDING

    def test_execute_task_failure(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")

        def executor(task):
            raise ValueError("执行错误")

        result = manager.execute_task_internal("task_1", executor)

        assert "失败" in result
        assert manager.tasks["task_1"].status == TaskStatus.FAILED
        assert manager.tasks["task_1"].error is not None

    def test_execute_task_already_running(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.tasks["task_1"].status = TaskStatus.RUNNING

        result = manager.execute_task_internal("task_1")

        assert "状态不允许执行" in result

    def test_execute_task_already_completed(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.tasks["task_1"].status = TaskStatus.COMPLETED

        result = manager.execute_task_internal("task_1")

        assert "状态不允许执行" in result

    def test_execute_all(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])
        manager.register_task("task_3", "任务3", depends_on=["task_1"])
        manager.register_task("task_4", "任务4", depends_on=["task_2", "task_3"])

        results = manager.execute_all()

        assert "成功: 4" in results
        assert "失败: 0" in results
        for task in manager.tasks.values():
            assert task.status == TaskStatus.COMPLETED

    def test_execute_all_parallel(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2")
        manager.register_task("task_3", "任务3", depends_on=["task_1", "task_2"])

        results = manager.execute_all()

        assert "成功: 3" in results

    def test_get_task_status(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")

        status = manager.get_task_status("task_1")
        assert "pending" in status
        assert "任务1" in status

    def test_get_task_status_not_found(self):
        manager = TaskDepManager()

        status = manager.get_task_status("nonexistent")
        assert "不存在" in status

    def test_list_tasks(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2")

        result = manager.list_tasks()

        assert "任务1" in result
        assert "任务2" in result
        assert "共 2 个" in result

    def test_list_empty(self):
        manager = TaskDepManager()

        result = manager.list_tasks()

        assert "暂无任务" in result

    def test_cancel_task(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")

        result = manager.cancel_task("task_1")

        assert "取消" in result
        assert manager.tasks["task_1"].status == TaskStatus.CANCELLED

    def test_cancel_completed_task(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.tasks["task_1"].status = TaskStatus.COMPLETED

        result = manager.cancel_task("task_1")

        assert "无法取消" in result

    def test_visualize(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])

        dot = manager.visualize()

        assert "digraph" in dot
        assert "task_1" in dot
        assert "task_2" in dot

    def test_to_dict(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")

        d = manager.to_dict()

        assert "tasks" in d
        assert "execution_order" in d
        assert "task_1" in d["tasks"]


class TestTaskDepTool:
    """任务依赖工具测试"""

    def test_create_tool(self):
        tool = TaskDepTool()

        assert tool.name == "task_dep"
        assert tool.expandable is True

    def test_register_action(self):
        tool = TaskDepTool()

        result = tool.run({"action": "register", "task_id": "task_1", "name": "任务1"})

        assert "成功" in result

    def test_list_action(self):
        tool = TaskDepTool()

        tool.run({"action": "register", "task_id": "task_1", "name": "任务1"})

        result = tool.run({"action": "list"})

        assert "任务1" in result

    def test_status_action(self):
        tool = TaskDepTool()

        tool.run({"action": "register", "task_id": "task_1", "name": "任务1"})

        result = tool.run({"action": "status", "task_id": "task_1"})

        assert "pending" in result

    def test_get_order_action(self):
        tool = TaskDepTool()

        tool.run({"action": "register", "task_id": "task_1", "name": "任务1"})

        result = tool.run({"action": "get_order"})

        assert "执行顺序" in result

    def test_add_dep_action(self):
        tool = TaskDepTool()

        tool.run({"action": "register", "task_id": "t1", "name": "任务1"})
        tool.run({"action": "register", "task_id": "t2", "name": "任务2"})

        result = tool.run({"action": "add_dep", "task_id": "t2", "depends_on": ["t1"]})

        assert "成功" in result

    def test_cancel_action(self):
        tool = TaskDepTool()

        tool.run({"action": "register", "task_id": "task_1", "name": "任务1"})

        result = tool.run({"action": "cancel", "task_id": "task_1"})

        assert "取消" in result

    def test_execute_action(self):
        tool = TaskDepTool()

        tool.run({"action": "register", "task_id": "task_1", "name": "任务1"})

        result = tool.run({"action": "execute", "task_id": "task_1"})

        assert "成功" in result

    def test_execute_all_action(self):
        tool = TaskDepTool()

        tool.run({"action": "register", "task_id": "t1", "name": "任务1"})
        tool.run(
            {
                "action": "register",
                "task_id": "t2",
                "name": "任务2",
                "depends_on": ["t1"],
            }
        )

        result = tool.run({"action": "execute_all"})

        assert "执行完成" in result

    def test_invalid_action(self):
        tool = TaskDepTool()

        result = tool.run({"action": "invalid_action"})

        assert "不支持" in result

    def test_get_parameters(self):
        tool = TaskDepTool()

        params = tool.get_parameters()

        assert len(params) > 0
        assert any(p.name == "action" for p in params)


class TestTaskDepManagerWithNoteTool:
    """集成NoteTool的测试"""

    def test_register_task_with_note_integration(self):
        mock_note_tool = Mock()
        mock_note_tool.run.return_value = "笔记创建成功"

        manager = TaskDepManager(note_tool=mock_note_tool)

        result = manager.register_task(task_id="task_1", name="任务1", tags=["test"])

        assert "成功" in result
        mock_note_tool.run.assert_called()

    def test_execute_updates_note(self):
        mock_note_tool = Mock()
        mock_note_tool.run.return_value = "成功"

        manager = TaskDepManager(note_tool=mock_note_tool)
        manager.register_task("task_1", "任务1")

        manager.execute_task_internal("task_1")

        assert mock_note_tool.run.call_count >= 2


class TestComplexScenarios:
    """复杂场景测试"""

    def test_multiple_parallel_branches(self):
        manager = TaskDepManager()

        manager.register_task("A", "根任务")
        manager.register_task("B1", "分支1", depends_on=["A"])
        manager.register_task("B2", "分支2", depends_on=["A"])
        manager.register_task("B3", "分支3", depends_on=["A"])
        manager.register_task("C", "汇合", depends_on=["B1", "B2", "B3"])

        order = manager.get_execution_order()

        assert order.index("A") < order.index("B1")
        assert order.index("A") < order.index("B2")
        assert order.index("A") < order.index("B3")
        assert order.index("B1") < order.index("C")
        assert order.index("B2") < order.index("C")
        assert order.index("B3") < order.index("C")

    def test_complex_dependency_chain(self):
        manager = TaskDepManager()

        manager.register_task("init", "初始化")
        manager.register_task("setup", "环境配置", depends_on=["init"])
        manager.register_task("build", "编译构建", depends_on=["setup"])
        manager.register_task("test", "运行测试", depends_on=["build"])
        manager.register_task("deploy", "部署发布", depends_on=["test"])

        results = manager.execute_all()

        assert "成功: 5" in results
        for task in manager.tasks.values():
            assert task.status == TaskStatus.COMPLETED

    def test_dependency_failure_propagation(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])

        manager.tasks["task_1"].status = TaskStatus.FAILED

        ready = manager.get_ready_tasks_internal()

        assert "task_2" not in ready

    def test_empty_dependency_list(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1", depends_on=[])

        assert len(manager.tasks["task_1"].depends_on) == 0

    def test_multiple_dependencies_same_task(self):
        manager = TaskDepManager()

        manager.register_task("A", "任务A")
        manager.register_task("B", "任务B")
        manager.register_task("C", "任务C", depends_on=["A", "B"])

        assert len(manager.tasks["C"].depends_on) == 2

    def test_diamond_dependency(self):
        manager = TaskDepManager()

        manager.register_task("A", "任务A")
        manager.register_task("B", "任务B", depends_on=["A"])
        manager.register_task("C", "任务C", depends_on=["A"])
        manager.register_task("D", "任务D", depends_on=["B", "C"])

        order = manager.get_execution_order()

        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_task_execution_order_preserved(self):
        manager = TaskDepManager()

        manager.register_task("task_1", "任务1")
        manager.register_task("task_2", "任务2", depends_on=["task_1"])
        manager.register_task("task_3", "任务3", depends_on=["task_1"])

        execution_order = []

        def track_executor(task):
            execution_order.append(task.task_id)
            return "done"

        manager.execute_all(track_executor)

        assert execution_order[0] == "task_1"
        assert "task_2" in execution_order[1:]
        assert "task_3" in execution_order[1:]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
