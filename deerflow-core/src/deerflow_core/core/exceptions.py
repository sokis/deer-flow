"""DeerFlow Core 公共异常类定义.

此模块定义项目使用的所有异常类型，采用层次化设计：
- DeerFlowCoreError: 所有异常的基类
- AgentError: Agent 相关错误
- SandboxError: 沙箱操作错误
- ToolError: 工具执行错误
- ExecutionError: 任务执行错误
- ConfigurationError: 配置错误
- TimeoutError: 超时错误

设计决策:
- 单一基类：所有异常继承自 DeerFlowCoreError
- 层次清晰：按模块划分异常类型
- 标准模式：遵循 Python 内置异常的命名约定

使用示例:
    try:
        result = await sandbox.execute(command)
    except SandboxError as e:
        logger.error(f"命令执行失败: {e}")
    except DeerFlowCoreError as e:
        # 捕获所有 DeerFlow 相关错误
        logger.error(f"未知错误: {e}")

作者: DeerFlow Team
版本: 0.1.0
许可证: MIT
"""


class DeerFlowCoreError(Exception):
    """DeerFlow Core 所有异常的基类.

    所有 DeerFlow 相关的异常都应该继承此类。
    允许用户通过捕获此异常来处理所有 DeerFlow 错误。

    使用示例:
        try:
            # DeerFlow 操作
            pass
        except DeerFlowCoreError as e:
            # 捕获所有 DeerFlow 错误
            print(f"发生错误: {e}")
    """
    pass


class AgentError(DeerFlowCoreError):
    """Agent 执行过程中发生的错误.

    当 Agent 遇到以下情况时抛出：
    - 模型调用失败
    - 响应解析错误
    - 工具调用异常
    - 状态管理错误

    使用示例:
        raise AgentError("模型调用失败: API 限流")
    """
    pass


class SandboxError(DeerFlowCoreError):
    """沙箱操作相关的错误.

    当沙箱环境操作失败时抛出，包括：
    - 命令执行失败或超时
    - 文件读取/写入错误
    - 目录访问错误
    - 路径安全检查失败

    使用示例:
        raise SandboxError(f"文件读取失败: {path} 不存在")
    """
    pass


class ToolError(DeerFlowCoreError):
    """工具执行相关的错误.

    当工具执行失败时抛出，包括：
    - 输入参数验证失败
    - 工具内部错误
    - 资源访问错误
    - 返回值格式错误

    使用示例:
        raise ToolError(f"工具 {tool_name} 执行失败: 无效参数")
    """
    pass


class ExecutionError(DeerFlowCoreError):
    """任务执行相关的错误.

    当任务执行过程中发生错误时抛出，包括：
    - 子代理执行失败
    - 任务超时
    - 资源不足
    - 状态转换错误

    使用示例:
        raise ExecutionError(f"任务执行失败: {task_id} 超时")
    """
    pass


class ConfigurationError(DeerFlowCoreError):
    """配置相关的错误.

    当配置无效或缺失时抛出，包括：
    - 缺少必需的配置项
    - 配置值类型错误
    - 配置值超出有效范围
    - 配置文件不存在

    使用示例:
        raise ConfigurationError("缺少必需配置: model_name")
    """
    pass


class TimeoutError(DeerFlowCoreError):
    """操作超时错误.

    当操作超过指定时间限制时抛出，包括：
    - 命令执行超时
    - API 调用超时
    - 网络请求超时
    - 任务执行超时

    使用示例:
        raise TimeoutError("沙箱命令执行超过 30 秒限制")
    """
    pass


class SkillError(DeerFlowCoreError):
    """技能系统相关的错误.

    当技能加载、解析或执行失败时抛出，包括：
    - SKILL.md 文件不存在
    - 技能元数据解析错误
    - 技能验证失败

    使用示例:
        raise SkillError(f"技能加载失败: {skill_name} 的 SKILL.md 不存在")
    """
    pass
