"""Tests for skill system."""

import pytest
from pathlib import Path
from deerflow_core.core.skill import SkillMetadata
from deerflow_core.extensions.skills import FileSkillLoader, FileBasedSkill
from deerflow_core.core.exceptions import SkillError


class TestFileBasedSkill:
    """Tests for FileBasedSkill."""

    @pytest.fixture
    def temp_skill_dir(self, tmp_path):
        """Create a temporary skill directory with SKILL.md."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("""---
name: test-skill
description: A test skill for testing purposes
---

# Test Skill

## Overview
This is a test skill.
""")
        return skill_dir

    @pytest.mark.asyncio
    async def test_execute_returns_content(self, temp_skill_dir):
        """execute() should return SKILL.md content."""
        loader = FileSkillLoader(temp_skill_dir.parent)
        skill = loader.load_skill(temp_skill_dir)

        class MockContext:
            pass

        result = await skill.execute(MockContext())

        assert "content" in result
        assert "test skill" in result["content"].lower()
        assert result["name"] == "test-skill"
        assert result["description"] == "A test skill for testing purposes"

    @pytest.mark.asyncio
    async def test_execute_missing_skill_file(self, tmp_path):
        """execute() raises SkillError if SKILL.md missing."""
        # Create a skill directory without SKILL.md
        skill_dir = tmp_path / "empty-skill"
        skill_dir.mkdir()

        loader = FileSkillLoader(tmp_path)
        skill = loader.load_skill(skill_dir)

        class MockContext:
            pass

        with pytest.raises(SkillError, match="SKILL.md not found"):
            await skill.execute(MockContext())


class TestSkillsPromptSection:
    """Tests for skills prompt generation."""

    def test_get_skills_prompt_section_empty(self):
        """Empty list returns empty string."""
        from deerflow_core.extensions.skills import get_skills_prompt_section
        result = get_skills_prompt_section([])
        assert result == ""

    def test_get_skills_prompt_section_with_skills(self):
        """Skills are formatted correctly in prompt section."""
        from deerflow_core.extensions.skills import get_skills_prompt_section
        skills = [
            SkillMetadata(name="deep-research", description="Research skill"),
            SkillMetadata(name="code-review", description="Review code"),
        ]

        result = get_skills_prompt_section(skills)

        assert "<skill_system>" in result
        assert "<available_skills>" in result
        assert "deep-research" in result
        assert "Research skill" in result
        assert "code-review" in result


class TestFileSkillLoader:
    """Tests for FileSkillLoader."""

    def test_load_skill_with_allowed_tools(self, tmp_path):
        """Skill with allowed_tools parses correctly."""
        skill_dir = tmp_path / "tool-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: tool-skill
description: A skill with allowed tools
allowed-tools: bash, read_file, write_file
---

# Tool Skill

## Overview
This skill uses specific tools.
""")
        loader = FileSkillLoader(tmp_path)
        skills = loader.list_skills()

        tool_skill_meta = next(s for s in skills if s.name == "tool-skill")
        assert tool_skill_meta.allowed_tools == ["bash", "read_file", "write_file"]
