"""
Tests for the command line version
"""
import pytest
import subprocess
import os
from shutil import rmtree


def test_git_init(tmp_path):
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    cmd = os.path.abspath(os.path.join(tests_dir, "../pico_project.py"))
    project_name = "test_git_project"
    # clear any previous data
    try:
        rmtree(os.path.join(tmp_path, project_name))
    except FileNotFoundError:
        pass
    os.chdir(tmp_path)
    cli_cmd = [cmd, "--project", "git", project_name]
    result = subprocess.run(cli_cmd, capture_output=True, text=True)
    assert result.returncode == 0
    for generated_file in [".gitignore", "LICENCE.txt", "README.md"]:
        exists = os.path.exists(os.path.join(tmp_path, project_name, generated_file))
        assert exists is True
    os.chdir(os.path.join(tmp_path, project_name))
    result = subprocess.run(["git", "log"], capture_output=True, text=True)
    assert result.returncode == 0, f"git log test failed {result.stderr}"


if __name__ == "__main__":
    test_git_init("/tmp")
