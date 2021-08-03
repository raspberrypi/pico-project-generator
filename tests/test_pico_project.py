import subprocess

# basic integration testing
def test_basic_project(tmp_path):
    test_path = str(tmp_path / "test_project")
    completed = subprocess.run(["python3", "pico_project.py", test_path])
    assert completed.returncode == 0

