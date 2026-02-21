"""测试工具过滤器"""

import pytest
from hello_agents.tools.tool_filter import (
    ToolFilter,
    ReadOnlyFilter,
    FullAccessFilter,
    CustomFilter
)


class TestReadOnlyFilter:
    """测试只读工具过滤器"""
    
    def test_filter_readonly_tools(self):
        """测试只保留只读工具"""
        filter_obj = ReadOnlyFilter()
        
        all_tools = [
            "Read", "Write", "Edit", "LS", "Grep",
            "Bash", "MemoryTool", "SearchTool"
        ]
        
        filtered = filter_obj.filter(all_tools)
        
        # 应该只保留只读工具
        assert "Read" in filtered
        assert "LS" in filtered
        assert "Grep" in filtered
        assert "MemoryTool" in filtered
        assert "SearchTool" in filtered
        
        # 不应该包含写入工具
        assert "Write" not in filtered
        assert "Edit" not in filtered
        assert "Bash" not in filtered
    
    def test_is_allowed(self):
        """测试单个工具检查"""
        filter_obj = ReadOnlyFilter()
        
        assert filter_obj.is_allowed("Read") is True
        assert filter_obj.is_allowed("LS") is True
        assert filter_obj.is_allowed("Write") is False
        assert filter_obj.is_allowed("Bash") is False
    
    def test_additional_allowed(self):
        """测试额外允许的工具"""
        filter_obj = ReadOnlyFilter(additional_allowed=["CustomTool"])
        
        assert filter_obj.is_allowed("Read") is True
        assert filter_obj.is_allowed("CustomTool") is True
        assert filter_obj.is_allowed("Write") is False


class TestFullAccessFilter:
    """测试完全访问过滤器"""
    
    def test_filter_deny_dangerous_tools(self):
        """测试排除危险工具"""
        filter_obj = FullAccessFilter()
        
        all_tools = [
            "Read", "Write", "Edit", "LS", "Grep",
            "Bash", "Terminal", "MemoryTool"
        ]
        
        filtered = filter_obj.filter(all_tools)
        
        # 应该包含大部分工具
        assert "Read" in filtered
        assert "Write" in filtered
        assert "Edit" in filtered
        assert "LS" in filtered
        
        # 不应该包含危险工具
        assert "Bash" not in filtered
        assert "Terminal" not in filtered
    
    def test_is_allowed(self):
        """测试单个工具检查"""
        filter_obj = FullAccessFilter()
        
        assert filter_obj.is_allowed("Read") is True
        assert filter_obj.is_allowed("Write") is True
        assert filter_obj.is_allowed("Bash") is False
        assert filter_obj.is_allowed("Terminal") is False
    
    def test_additional_denied(self):
        """测试额外禁止的工具"""
        filter_obj = FullAccessFilter(additional_denied=["Write"])
        
        assert filter_obj.is_allowed("Read") is True
        assert filter_obj.is_allowed("Write") is False
        assert filter_obj.is_allowed("Bash") is False


class TestCustomFilter:
    """测试自定义过滤器"""
    
    def test_whitelist_mode(self):
        """测试白名单模式"""
        filter_obj = CustomFilter(
            allowed=["Read", "LS", "Grep"],
            mode="whitelist"
        )
        
        all_tools = ["Read", "Write", "LS", "Grep", "Bash"]
        filtered = filter_obj.filter(all_tools)
        
        assert filtered == ["Read", "LS", "Grep"]
    
    def test_blacklist_mode(self):
        """测试黑名单模式"""
        filter_obj = CustomFilter(
            denied=["Bash", "Terminal"],
            mode="blacklist"
        )
        
        all_tools = ["Read", "Write", "Bash", "Terminal", "LS"]
        filtered = filter_obj.filter(all_tools)
        
        assert "Read" in filtered
        assert "Write" in filtered
        assert "LS" in filtered
        assert "Bash" not in filtered
        assert "Terminal" not in filtered
    
    def test_is_allowed_whitelist(self):
        """测试白名单模式的单个工具检查"""
        filter_obj = CustomFilter(
            allowed=["Read", "LS"],
            mode="whitelist"
        )
        
        assert filter_obj.is_allowed("Read") is True
        assert filter_obj.is_allowed("LS") is True
        assert filter_obj.is_allowed("Write") is False
    
    def test_is_allowed_blacklist(self):
        """测试黑名单模式的单个工具检查"""
        filter_obj = CustomFilter(
            denied=["Bash"],
            mode="blacklist"
        )
        
        assert filter_obj.is_allowed("Read") is True
        assert filter_obj.is_allowed("Write") is True
        assert filter_obj.is_allowed("Bash") is False
    
    def test_invalid_mode(self):
        """测试无效模式"""
        with pytest.raises(ValueError, match="Invalid mode"):
            CustomFilter(mode="invalid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

