"""
Data Analytics MCP Server - 测试套件

可以在 PyCharm 中直接运行（右键 -> Run 'test_xxx'）
也支持命令行: pytest tests/test_data_analytics.py -v
"""

import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hello_agents.protocols.mcp.data_analytics.tools.database import (
    query_database,
    init_sample_database,
)
from hello_agents.protocols.mcp.data_analytics.tools.visualization import (
    visualize_data,
    visualize_summary,
)
from hello_agents.protocols.mcp.data_analytics.tools.reporting import (
    generate_report,
    create_report_from_analysis,
)
from hello_agents.protocols.mcp.data_analytics.orchestrator import (
    ToolOrchestrator,
    AnalysisContext,
    TaskStep,
)
from dotenv import load_dotenv

load_dotenv()

try:
    from hello_agents.protocols.mcp.data_analytics.server import DataAnalyticsServer

    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False

try:
    import asyncio

    HAS_ASYNCIO = True
except ImportError:
    HAS_ASYNCIO = False


def get_test_db_path():
    """获取测试数据库路径"""
    return os.path.join(tempfile.gettempdir(), "test_analytics.db")


def run_async_test(coro):
    """在同步环境中运行异步测试"""
    if HAS_ASYNCIO:
        return asyncio.get_event_loop().run_until_complete(coro)
    else:
        pytest.skip("asyncio not available")


class TestDatabaseTools:
    """数据库查询工具测试"""

    def setup_method(self):
        """每个测试前初始化数据库"""
        self.db_path = get_test_db_path()
        init_sample_database(self.db_path)

    def teardown_method(self):
        """每个测试后清理"""
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except OSError:
            pass

    def test_simple_select_query(self):
        """测试简单的 SELECT 查询"""
        result = query_database("SELECT 1 as id, 'test' as name", self.db_path)
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["columns"] == ["id", "name"]
        assert result["rows"][0]["id"] == 1
        assert result["rows"][0]["name"] == "test"

    def test_select_with_alias(self):
        """测试带别名的查询"""
        result = query_database(
            "SELECT 1 + 2 as total, 'hello' as greeting", self.db_path
        )
        assert result["success"] is True
        assert result["rows"][0]["total"] == 3
        assert result["rows"][0]["greeting"] == "hello"

    def test_query_with_limit(self):
        """测试带 LIMIT 的查询"""
        result = query_database("SELECT * FROM sales", self.db_path, limit=3)
        assert result["success"] is True
        assert result["row_count"] <= 3

    def test_reject_non_select_query(self):
        """测试拒绝非 SELECT 语句"""
        result = query_database("DELETE FROM sales WHERE id = 1", self.db_path)
        assert result["success"] is False
        assert "Only SELECT" in result["error"]

        result = query_database("INSERT INTO sales VALUES (1, 'test')", self.db_path)
        assert result["success"] is False

    def test_reject_multiple_statements(self):
        """测试拒绝多语句"""
        result = query_database("SELECT 1; SELECT 2", self.db_path)
        assert result["success"] is False
        assert "Multiple statements" in result["error"]

    def test_query_with_aggregation(self):
        """测试聚合查询"""
        result = query_database(
            "SELECT region, SUM(revenue) as total_revenue FROM sales GROUP BY region",
            self.db_path,
        )
        assert result["success"] is True
        assert len(result["rows"]) == 2
        regions = {row["region"] for row in result["rows"]}
        assert regions == {"North", "South"}

    def test_query_with_order_by(self):
        """测试 ORDER BY 查询"""
        result = query_database(
            "SELECT * FROM sales ORDER BY revenue DESC", self.db_path, limit=3
        )
        assert result["success"] is True
        if len(result["rows"]) > 1:
            assert result["rows"][0]["revenue"] >= result["rows"][1]["revenue"]

    def test_invalid_sql_syntax(self):
        """测试无效 SQL 语法"""
        result = query_database("SELEC * FROM nonexistent", self.db_path)
        assert result["success"] is False
        assert "error" in result

    def test_negative_limit(self):
        """测试负数 LIMIT"""
        result = query_database("SELECT 1", self.db_path, limit=-1)
        assert result["success"] is False
        assert "Limit must be positive" in result["error"]

    def test_init_sample_database(self):
        """测试初始化示例数据库"""
        result = init_sample_database(self.db_path)
        assert result["success"] is True
        query_result = query_database("SELECT COUNT(*) as cnt FROM sales", self.db_path)
        assert query_result["success"] is True
        assert query_result["rows"][0]["cnt"] > 0


class TestVisualizationTools:
    """数据可视化工具测试"""

    def test_bar_chart_generation(self):
        """测试柱状图生成"""
        data = [
            {"month": "Jan", "sales": 100},
            {"month": "Feb", "sales": 150},
            {"month": "Mar", "sales": 120},
        ]
        result = visualize_data(
            data=data,
            chart_type="bar",
            title="Monthly Sales",
            x_axis="month",
            y_axis="sales",
            output_format="json",
        )
        assert result["success"] is True
        assert result["chart_type"] == "bar"
        assert result["metadata"]["data_points"] == 3

    def test_line_chart_generation(self):
        """测试折线图生成"""
        data = [{"x": 1, "y": 10}, {"x": 2, "y": 20}, {"x": 3, "y": 15}]
        result = visualize_data(
            data=data,
            chart_type="line",
            title="Trend",
            x_axis="x",
            y_axis="y",
            output_format="ascii",
        )
        assert result["success"] is True
        assert "●" in result["image_data"]

    def test_pie_chart_generation(self):
        """测试饼图生成"""
        data = [{"category": "A", "value": 30}, {"category": "B", "value": 50}]
        result = visualize_data(
            data=data,
            chart_type="pie",
            title="Distribution",
            x_axis="category",
            y_axis="value",
        )
        assert result["success"] is True

    def test_svg_output(self):
        """测试 SVG 输出格式"""
        data = [{"label": "A", "value": 50}]
        result = visualize_data(
            data=data,
            chart_type="bar",
            title="Test",
            x_axis="label",
            y_axis="value",
            output_format="svg",
        )
        assert result["success"] is True
        assert "<svg" in result["image_data"]

    def test_invalid_chart_type(self):
        """测试无效图表类型"""
        data = [{"x": 1, "y": 2}]
        result = visualize_data(
            data=data, chart_type="invalid", title="Test", x_axis="x", y_axis="y"
        )
        assert result["success"] is False
        assert "Unsupported" in result["error"]

    def test_empty_data(self):
        """测试空数据"""
        result = visualize_data(
            data=[], chart_type="bar", title="Empty", x_axis="x", y_axis="y"
        )
        assert result["success"] is False

    def test_visualize_summary(self):
        """测试数据摘要"""
        data = [{"id": 1, "value": 100}, {"id": 2, "value": 200}]
        result = visualize_summary(data, title="Test Summary")
        assert result["success"] is True
        assert result["summary"]["total_records"] == 2
        assert "value" in result["summary"]["numeric_fields"]


class TestReportingTools:
    """报表生成工具测试"""

    def test_markdown_report_with_table(self):
        """测试 Markdown 表格报表"""
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        result = generate_report(title="User Report", data=data, format="markdown")
        assert result["success"] is True
        assert "# User Report" in result["content"]
        assert "| name | age |" in result["content"]

    def test_html_report_generation(self):
        """测试 HTML 报表生成"""
        data = [{"col": "value"}]
        result = generate_report(title="HTML Report", data=data, format="html")
        assert result["success"] is True
        assert "<!DOCTYPE html>" in result["content"]
        assert "<table>" in result["content"]

    def test_custom_sections(self):
        """测试自定义章节"""
        sections = [
            {"type": "text", "title": "Intro", "content": "Hello"},
            {"type": "chart", "title": "Chart", "data": {"chart_type": "bar"}},
        ]
        result = generate_report(
            title="Custom Report", data=None, sections=sections, format="markdown"
        )
        assert result["success"] is True
        assert "1. Intro" in result["content"]

    def test_invalid_format(self):
        """测试无效格式"""
        result = generate_report(title="Test", data={}, format="xml")
        assert result["success"] is False

    def test_create_report_with_visualization(self):
        """测试创建带可视化的报表"""
        query_result = {
            "success": True,
            "rows": [{"month": "Jan", "sales": 100}],
            "row_count": 1,
            "sql": "SELECT * FROM data",
            "execution_time_ms": 5.0,
        }
        visualization_result = {
            "success": True,
            "chart_type": "bar",
            "title": "Sales Chart",
            "image_data": "<svg>...</svg>",
            "format": "svg",
        }
        result = create_report_from_analysis(
            query_result=query_result,
            visualization_result=visualization_result,
            title="Analysis Report",
        )
        assert result["success"] is True
        assert "Query Results" in result["content"]
        assert "Sales Chart" in result["content"]


class TestOrchestrator:
    """工具编排器测试"""

    def test_analysis_context_creation(self):
        """测试分析上下文创建"""
        context = AnalysisContext(task_id="test_001")
        assert context.task_id == "test_001"
        assert context.query_result is None

    def test_analysis_context_state_methods(self):
        """测试上下文状态方法"""
        context = AnalysisContext(task_id="test_002")
        assert not context.has_query_result()
        context.query_result = {"success": True, "rows": []}
        assert context.has_query_result()

    def test_analysis_context_serialization(self):
        """测试上下文序列化"""
        context = AnalysisContext(task_id="test_003", query_result={"success": True})
        data = context.to_dict()
        restored = AnalysisContext.from_dict(data)
        assert restored.task_id == "test_003"

    def test_task_step_creation(self):
        """测试任务步骤创建"""
        step = TaskStep(step_id="step1", tool_name="db_query", parameters={})
        assert step.step_id == "step1"

    def test_orchestrator_creation(self):
        """测试编排器创建"""
        orchestrator = ToolOrchestrator(task_id="orch_001")
        assert orchestrator.context.task_id == "orch_001"
        assert "db_query" in orchestrator._tools

    def test_orchestrator_get_summary(self):
        """测试获取摘要"""
        orchestrator = ToolOrchestrator(task_id="summary_test")
        orchestrator.context.query_result = {"success": True, "row_count": 10}
        summary = orchestrator.get_summary()
        assert summary["task_id"] == "summary_test"
        assert summary["query_row_count"] == 10


class TestOrchestratorAsync:
    """编排器异步测试"""

    def setup_method(self):
        """每个测试前初始化数据库"""
        self.db_path = get_test_db_path()
        init_sample_database(self.db_path)

    def teardown_method(self):
        """每个测试后清理"""
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except OSError:
            pass

    @pytest.mark.asyncio
    async def test_query_and_visualize_chain(self):
        """测试查询+可视化链式调用"""
        orchestrator = ToolOrchestrator(task_id="chain_001")
        context = await orchestrator.query_and_visualize(
            sql="SELECT month, SUM(revenue) as total FROM sales GROUP BY month",
            chart_type="bar",
            title="Monthly Revenue",
            x_axis="month",
            y_axis="total",
            connection_string=self.db_path,
        )

        assert context.has_query_result()
        assert context.query_result["success"] is True
        assert context.has_visualization()
        assert context.visualization_result["chart_type"] == "bar"

    @pytest.mark.asyncio
    async def test_full_analysis_chain(self):
        """测试完整分析流程"""
        orchestrator = ToolOrchestrator(task_id="full_001")
        context = await orchestrator.full_analysis(
            sql="SELECT region, SUM(revenue) as rev FROM sales GROUP BY region",
            chart_type="pie",
            report_title="Regional Report",
            x_axis="region",
            y_axis="rev",
            report_format="markdown",
            connection_string=self.db_path,
        )

        assert context.has_query_result()
        assert context.has_visualization()
        assert context.has_report()
        assert context.report_result["format"] == "markdown"


class TestDataAnalyticsServer:
    """数据分析服务器测试"""

    def test_server_creation(self):
        """测试服务器创建"""
        if not HAS_FASTMCP:
            pytest.skip("fastmcp library not installed")

        server = DataAnalyticsServer(name="test-server")
        assert server.name == "test-server"

    def test_default_tools(self):
        """测试默认工具"""
        if not HAS_FASTMCP:
            pytest.skip("fastmcp library not installed")

        server = DataAnalyticsServer()
        expected_tools = [
            "db_query",
            "init_sample_db",
            "visualize_data",
            "generate_report",
            "create_analysis_report",
        ]
        for tool in expected_tools:
            assert tool in server.get_info()["tools"]


class TestEndToEnd:
    """端到端测试"""

    def setup_method(self):
        """每个测试前初始化数据库"""
        self.db_path = get_test_db_path()
        init_sample_database(self.db_path)

    def teardown_method(self):
        """每个测试后清理"""
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except OSError:
            pass

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self):
        """测试完整分析工作流"""
        orchestrator = ToolOrchestrator(task_id="e2e_001")
        context = await orchestrator.full_analysis(
            sql="SELECT month, SUM(revenue) as rev FROM sales GROUP BY month",
            chart_type="bar",
            report_title="Sales Report",
            x_axis="month",
            y_axis="rev",
            report_format="markdown",
            connection_string=self.db_path,
        )

        assert context.has_query_result()
        assert context.has_visualization()
        assert context.has_report()


class TestErrorHandling:
    """错误处理测试"""

    def test_visualization_empty_data(self):
        """测试空数据可视化"""
        result = visualize_data(
            data=[], chart_type="bar", title="Empty", x_axis="x", y_axis="y"
        )
        assert result["success"] is False

    def test_report_invalid_format(self):
        """测试无效报表格式"""
        result = generate_report(title="Test", data={}, format="docx")
        assert result["success"] is False

    def test_context_from_dict_with_missing_fields(self):
        """测试从字典恢复上下文"""
        data = {"task_id": "incomplete"}
        context = AnalysisContext.from_dict(data)
        assert context.task_id == "incomplete"
        assert context.query_result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
