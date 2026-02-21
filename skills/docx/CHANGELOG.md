# Changelog

## [Added Comment Feature - python-docx Method] - 2026-01-29

### Added
- **批注功能 (Comment Feature)**: 使用python-docx的简单可靠方案
  - **推荐方法**: `scripts/add_comment_simple.py` - 使用python-docx直接操作.docx文件
  - **完整示例**: `scripts/examples/add_comments_pythondocx.py` - 展示各种使用场景
  - SKILL.md: 更新为推荐python-docx方法
  - ooxml.md: 保留OOXML方法作为高级选项
  - COMMENTS_UPDATE.md: 详细的功能更新说明

### Features
- ✅ 简单易用：无需解压/打包文档
- ✅ 批注人自动设置为"Z.ai"
- ✅ 经过实际验证：在Word中正常显示
- ✅ 支持多种定位方式：文本搜索、段落索引、条件判断等
- ✅ 代码简洁：比OOXML方法简单得多

### Method Comparison

**Recommended: python-docx**
```python
from docx import Document
doc = Document('input.docx')
doc.add_comment(runs=[para.runs[0]], text="批注", author="Z.ai")
doc.save('output.docx')
```

**Alternative: OOXML (Advanced)**
```python
from scripts.document import Document
doc = Document('unpacked', author="Z.ai")
para = doc["word/document.xml"].get_node(tag="w:p", contains="text")
doc.add_comment(start=para, end=para, text="批注")
doc.save()
```

### Usage Examples

#### 推荐方法（python-docx）
```bash
# 安装依赖
pip install python-docx

# 使用简单脚本
python scripts/add_comment_simple.py input.docx output.docx

# 使用完整示例
python scripts/examples/add_comments_pythondocx.py document.docx reviewed.docx
```

#### 高级方法（OOXML）
```bash
# 解压、处理、打包
python ooxml/scripts/unpack.py document.docx unpacked
python scripts/add_comment.py unpacked 10 "批注内容"
python ooxml/scripts/pack.py unpacked output.docx
```

### Testing
- ✅ python-docx方法经过实际验证
- ✅ 批注在Microsoft Word中正常显示
- ✅ 作者正确显示为"Z.ai"
- ✅ 支持各种定位方式
- ✅ 代码简洁可靠

### Documentation
- SKILL.md: 推荐python-docx方法，保留OOXML作为高级选项
- COMMENTS_UPDATE.md: 详细说明两种方法的区别
- 新增python-docx示例脚本
- 保留OOXML示例供高级用户使用

### Why python-docx is Recommended
1. **简单**: 无需解压/打包文档
2. **可靠**: 经过实际验证，在Word中正常工作
3. **直接**: 直接操作.docx文件，一步到位
4. **维护性**: 代码简洁，易于理解和修改
5. **兼容性**: 使用标准库，兼容性好

OOXML方法适合：
- 需要低级XML控制
- 需要同时处理tracked changes
- 需要批注回复等复杂功能
- 已经在使用解压文档的工作流
