# Skill 系统设计文档

**日期**: 2026-03-26
**状态**: 待批准
**优先级**: P0

---

## 1. 背景与目标

**目标**: 在 deer-flow-core 中实现与主项目一致的 SKILL 系统。

**已知事实**:
- deer-flow 的 SKILL 不是"可执行代码"，而是**提示词注入系统**
- Agent 通过读取 SKILL.md 获取技能指令，然后自我引导执行
- 核心是 SKILL.md 解析 + 元数据暴露 + 渐进式加载

---

## 2. 现有系统分析

### 2.1 SKILL.md 格式 (来自 `backend/packages/harness/deerflow/skills/`)

```yaml
---
name: skill-name            # 必须: hyphen-case
description: Description... # 必须: 1-1024 chars, no angle brackets
license: MIT License        # 可选
allowed-tools: tool1,tool2  # 可选: 逗号分隔
version: 1.0.0             # 可选
author: Author Name         # 可选
compatibility:             # 可选
  nodejs: ">=18.0.0"
---

# Skill Title

## Overview

Skill description and usage instructions...

## Workflow

Step-by-step instructions...
```

### 2.2 验证规则 (`validation.py`)

- `name`: `^[a-z0-9-]+$`, max 64 chars, no leading/trailing hyphens
- `description`: max 1024 chars, no `<` or `>`
- `allowed-tools`: 逗号分隔的工具名列表

### 2.3 目录结构

```
skills/
├── public/                    # 内置技能
│   ├── deep-research/
│   │   ├── SKILL.md
│   │   └── references/
│   └── skill-creator/
│       ├── SKILL.md
│       └── scripts/
└── custom/                    # 用户安装的技能
```

### 2.4 核心机制：渐进式加载

```python
# 在 Agent 提示词中注入技能元数据
<skill_system>
**Skills are located at:** /mnt/skills

<available_skills>
    <skill>
        <name>skill-name</name>
        <description>Skill description...</description>
        <location>/mnt/skills/public/skill-name/SKILL.md</location>
    </skill>
</available_skills>
</skill_system>

# Agent 触发时读取完整内容
await context.sandbox.read("/mnt/skills/public/deep-research/SKILL.md")
```

---

## 3. deer-flow-core 中的 Skill 实现

### 3.1 设计原则

1. **保持一致**: 与主项目 SKILL.md 格式完全兼容
2. **零依赖**: 解析器在 core 模块中实现，无外部依赖
3. **可扩展**: 支持 future 扩展（如 skill 安装器）

### 3.2 架构组件

| 组件 | 位置 | 职责 |
|------|------|------|
| `SkillMetadata` | `core/skill.py` | 元数据结构 (已有) |
| `Skill` | `core/skill.py` | 抽象接口 (已有) |
| `SkillLoader` | `core/skill.py` | 抽象加载器 (已有) |
| `FileSkillLoader` | `extensions/skills/__init__.py` | 文件系统加载器 (已有) |
| `FileBasedSkill` | `extensions/skills/__init__.py` | 基于文件的技能 (已有) |

### 3.3 当前状态

```python
# core/skill.py - 已定义
class Skill(ABC):
    metadata: SkillMetadata
    async load_resources(resource_dir: Path) -> dict
    async execute(context: Context) -> Any  # 当前抛出 NotImplementedError

# extensions/skills/__init__.py - 部分实现
class FileBasedSkill(Skill):
    execute()  # 当前抛出 NotImplementedError
```

---

## 4. 实现方案

### 4.1 FileBasedSkill.execute() 实现

**关键洞察**: `execute()` 不是"执行代码"，而是**返回技能内容供 Agent 读取**

```python
async def execute(self, context: Context, **kwargs: Any) -> Any:
    """Execute the skill by returning its content for the agent.

    In the deer-flow skill system, skills are NOT executed as code.
    Instead, they return their SKILL.md content which the agent
    reads and follows autonomously.

    Args:
        context: The execution context.

    Returns:
        Dict containing:
        - content: The raw SKILL.md content
        - metadata: SkillMetadata
        - path: Path to the skill directory
    """
    skill_file = self._path / "SKILL.md"

    if not skill_file.exists():
        raise SkillError(f"SKILL.md not found for skill {self.name}")

    # Read and return the skill content
    content = skill_file.read_text(encoding="utf-8")

    return {
        "content": content,
        "metadata": self._metadata,
        "path": str(self._path),
        "name": self.name,
        "description": self.description,
    }
```

### 4.2 渐进式加载支持

提供辅助方法让 Agent 获取技能列表和触发技能：

```python
class FileSkillLoader(SkillLoader):
    """File-based skill loader."""

    async def list_skills_async(self) -> list[SkillMetadata]:
        """Async version of list_skills."""
        return self.list_skills()

    async def get_skill_content(self, skill_name: str) -> str:
        """Get the SKILL.md content for a skill."""
        skills = self.list_skills()
        for skill_meta in skills:
            if skill_meta.name == skill_name:
                skill = self.load_skill(Path(skill_meta.name))
                content = (skill._path / "SKILL.md").read_text()
                return content
        raise SkillError(f"Skill not found: {skill_name}")
```

### 4.3 错误处理

```python
class SkillError(DeerFlowError):
    """Skill-related error."""
    pass
```

错误场景：
- SKILL.md 不存在
- 技能名称无效
- 解析失败

---

## 5. 与 Agent 集成

### 5.1 提供技能提示片段

```python
def get_skills_prompt_section(skills: list[SkillMetadata]) -> str:
    """Generate the skills section for agent system prompt.

    This matches the format used in the main deer-flow project.
    """
    if not skills:
        return ""

    skill_listings = []
    for meta in skills:
        skill_listings.append(f"""    <skill>
        <name>{meta.name}</name>
        <description>{meta.description}</description>
    </skill>""")

    return f"""<skill_system>
You have access to skills that provide optimized workflows for specific tasks.

**Progressive Loading Pattern:**
1. When a user query matches a skill's use case, immediately call `read_file` on the skill's main file
2. Read and understand the skill's workflow and instructions
3. Follow the skill's instructions precisely

**Skills are located at:** /skills

<available_skills>
{chr(10).join(skill_listings)}
</available_skills>
</skill_system>"""
```

### 5.2 使用示例

```python
# Agent 获取技能列表
loader = FileSkillLoader(Path("/skills"))
skills = loader.list_skills()

# 生成提示词片段
prompt_section = get_skills_prompt_section(skills)

# Agent 触发技能
skill = loader.load_skill(Path("/skills/deep-research"))
result = await skill.execute(context)
# result = {"content": "...SKILL.md content...", "metadata": ..., "path": ...}
```

---

## 6. 测试策略 (TDD)

### 6.1 测试用例

1. `test_skill_loading` - 验证技能加载
2. `test_skill_metadata_parsing` - 验证 frontmatter 解析
3. `test_skill_execute_returns_content` - 验证 execute() 返回内容
4. `test_skill_validation` - 验证名称/描述规则
5. `test_get_skills_prompt_section` - 验证提示词生成

### 6.2 测试结构

```
tests/
└── test_skills.py  # 新增
```

---

## 7. 实现清单

| 项目 | 状态 | 说明 |
|------|------|------|
| SkillError 异常 | 待添加 | 添加到 core/exceptions.py |
| FileBasedSkill.execute() | 待实现 | 返回 SKILL.md 内容 |
| FileSkillLoader 增强 | 待实现 | async 方法、get_skill_content |
| get_skills_prompt_section() | 待实现 | 提示词生成器 |
| 测试用例 | 待实现 | TDD 方式 |

---

## 8. 后续阶段

- **Phase 2**: TaskQueue 实现
- **Phase 3**: LoopDetectionMiddleware
- **Phase 4**: MCP 集成
- **Phase 5**: 性能和错误处理优化

---

## 9. 验收标准

- [ ] FileBasedSkill.execute() 返回 SKILL.md 内容和元数据
- [ ] 与主项目 SKILL.md 格式完全兼容
- [ ] get_skills_prompt_section() 生成正确格式的提示词
- [ ] 所有新增代码通过 ruff 检查
- [ ] TDD 测试覆盖
