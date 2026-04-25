"""Tests for test_pioneer.project.create_template_structure"""
from test_pioneer.project.create_template_structure import create_dir, create_template, create_template_dir


class TestCreateDir:
    def test_create_new_directory(self, tmp_path):
        new_dir = tmp_path / "test_dir"
        create_dir(str(new_dir))
        assert new_dir.is_dir()

    def test_create_nested_directory(self, tmp_path):
        new_dir = tmp_path / "a" / "b" / "c"
        create_dir(str(new_dir))
        assert new_dir.is_dir()

    def test_create_existing_directory(self, tmp_path):
        existing = tmp_path / "existing"
        existing.mkdir()
        create_dir(str(existing))  # Should not raise
        assert existing.is_dir()


class TestCreateTemplate:
    def test_create_template_file(self, tmp_path):
        parent = ".TestPioneer"
        template_dir = tmp_path / parent
        template_dir.mkdir()

        create_template(parent, str(tmp_path))

        template_file = template_dir / f"{parent}.yml"
        assert template_file.is_file()
        content = template_file.read_text(encoding="utf-8")
        assert "jobs:" in content

    def test_create_template_dir_not_exists(self, tmp_path):
        # Should do nothing if directory doesn't exist
        create_template("nonexistent", str(tmp_path))


class TestCreateTemplateDir:
    def test_full_workflow(self, tmp_path):
        create_template_dir(project_path=str(tmp_path), parent_name=".TestProject")

        project_dir = tmp_path / ".TestProject"
        assert project_dir.is_dir()

        template_file = project_dir / ".TestProject.yml"
        assert template_file.is_file()
