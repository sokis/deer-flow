"""Skills extension."""

from pathlib import Path
from typing import Any

from deerflow_core.core.context import Context
from deerflow_core.core.skill import Skill, SkillLoader, SkillMetadata


def get_skills_prompt_section(skills: list["SkillMetadata"]) -> str:
    """Generate the skills section for agent system prompt.

    This matches the format used in the main deer-flow project.

    Args:
        skills: List of skill metadata to include.

    Returns:
        Formatted skill system prompt section.
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


class FileSkillLoader(SkillLoader):
    """File-based skill loader.

    Loads skills from a directory structure containing SKILL.md files.
    """

    def __init__(self, skills_dir: Path):
        self._skills_dir = skills_dir

    def load_skill(self, path: Path) -> Skill:
        """Load a skill from a path.

        Args:
            path: Path to the skill directory.

        Returns:
            Loaded Skill instance.
        """
        skill_md = path / "SKILL.md"
        if not skill_md.exists():
            raise ValueError(f"SKILL.md not found in {path}")

        metadata = self._parse_skill_md(skill_md)

        # Create a simple skill instance
        return FileBasedSkill(metadata=metadata, path=path)

    def list_skills(self) -> list[SkillMetadata]:
        """List all available skills."""
        skills = []
        if not self._skills_dir.exists():
            return skills

        for item in self._skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                try:
                    metadata = self._parse_skill_md(item / "SKILL.md")
                    skills.append(metadata)
                except Exception:
                    continue

        return skills

    def _parse_skill_md(self, path: Path) -> SkillMetadata:
        """Parse SKILL.md file for metadata."""
        content = path.read_text()

        # Simple frontmatter parsing
        metadata: dict[str, Any] = {}
        in_frontmatter = False
        current_key = None
        current_lines: list[str] = []

        for line in content.split("\n"):
            stripped = line.strip()

            if stripped == "---":
                in_frontmatter = not in_frontmatter
                if not in_frontmatter and current_key:
                    metadata[current_key] = "\n".join(current_lines)
                    current_key = None
                    current_lines = []
                continue

            if in_frontmatter:
                if ":" in line:
                    if current_key:
                        metadata[current_key] = "\n".join(current_lines)
                    key, _, value = line.partition(":")
                    current_key = key.strip()
                    current_lines = [value.strip()] if value.strip() else []
                else:
                    current_lines.append(line.strip())
            elif stripped.startswith("#") and not current_key:
                # Title line
                continue

        if current_key:
            metadata[current_key] = "\n".join(current_lines)

        def _strip_list(value: str) -> list[str]:
            """Split comma-separated value and strip whitespace."""
            return [v.strip() for v in value.split(",") if v.strip()]

        return SkillMetadata(
            name=metadata.get("name", path.parent.name),
            description=metadata.get("description", ""),
            version=metadata.get("version", "1.0.0"),
            author=metadata.get("author"),
            license=metadata.get("license"),
            tags=_strip_list(metadata.get("tags", "")) if metadata.get("tags") else [],
            allowed_tools=_strip_list(metadata.get("allowed-tools", "")) if metadata.get("allowed-tools") else [],
        )


class FileBasedSkill(Skill):
    """A skill loaded from the filesystem."""

    def __init__(self, metadata: SkillMetadata, path: Path):
        self._metadata = metadata
        self._path = path
        self._resources: dict[str, Any] = {}

    @property
    def metadata(self) -> SkillMetadata:
        return self._metadata

    async def load_resources(self, resource_dir: Path | None = None) -> dict[str, Any]:
        """Load skill resources."""
        if resource_dir is None:
            resource_dir = self._path

        for item in resource_dir.iterdir():
            if item.is_file():
                self._resources[item.name] = item.read_text()
            elif item.is_dir():
                self._resources[f"{item.name}/"] = list(item.iterdir())

        return self._resources

    async def execute(self, context: Context, **kwargs: Any) -> Any:
        """Execute the skill by returning its content.

        In the deer-flow skill system, skills are NOT executed as code.
        Instead, they return their SKILL.md content which the agent
        reads and follows autonomously.

        Args:
            context: The execution context.
            **kwargs: Additional arguments (unused for now).

        Returns:
            Dict containing skill content and metadata.
        """
        skill_file = self._path / "SKILL.md"

        if not skill_file.exists():
            from deerflow_core.core.exceptions import SkillError
            raise SkillError(f"SKILL.md not found for skill {self.name}")

        content = skill_file.read_text(encoding="utf-8")

        return {
            "content": content,
            "metadata": self._metadata,
            "path": str(self._path),
            "name": self.name,
            "description": self.description,
        }
