
import pytest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import json
from pathlib import Path

# Adjust path to find src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cli import ProcessManager, app
from typer.testing import CliRunner

runner = CliRunner()

@pytest.fixture
def mock_state_file(tmp_path):
    """Mock the state directory and file"""
    state_dir = tmp_path / ".scripturesapp"
    state_dir.mkdir()
    state_file = state_dir / "state.json"
    return state_file

@pytest.fixture
def process_manager(mock_state_file):
    """Return a ProcessManager instance with mocked paths"""
    with patch("src.cli.Path") as mock_path:
        # We need Path.home() to return our tmp_path
        mock_path.home.return_value = mock_state_file.parent.parent
        # We need other paths to resolve correctly or be mocked
        # Actually initializing ProcessManager calls Path.home()
        
        # Let's just patch the class instance attributes after init if possible,
        # or patch the class locally.
        pass
    
    # Better: Patch Path.home globally for the test
    with patch("pathlib.Path.home", return_value=mock_state_file.parent.parent):
        pm = ProcessManager()
        # Ensure it uses our mock state file
        assert pm.state_file == mock_state_file
        return pm

def test_start_api(process_manager):
    with patch("subprocess.Popen") as mock_popen, \
         patch("builtins.open", mock_open()) as mock_file:
        mock_popen.return_value.pid = 1234
        
        pid = process_manager.start_api(port=9000)
        
        assert pid == 1234
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "uvicorn" in args
        # Verify log file opened
        mock_file.assert_called()

def test_start_app(process_manager):
    with patch("subprocess.run") as mock_run, \
         patch("subprocess.Popen") as mock_popen, \
         patch("builtins.open", mock_open()) as mock_file:
        
        # Mock successful build
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "build stdout"
        mock_run.return_value.stderr = "build stderr"
        
        # Mock app launch
        mock_popen.return_value.pid = 5678
        
        pid = process_manager.start_app()
        
        assert pid == 5678
        mock_run.assert_called_once() # swift build
        assert "swift" in mock_run.call_args[0][0]
        assert "build" in mock_run.call_args[0][0]
        
        mock_popen.assert_called_once() # swift run
        assert "swift" in mock_popen.call_args[0][0]
        assert "run" in mock_popen.call_args[0][0]

def test_save_state(process_manager, mock_state_file):
    process_manager.save_state(123, 456)
    
    assert mock_state_file.exists()
    data = json.loads(mock_state_file.read_text())
    assert data["api_pid"] == 123
    assert data["app_pid"] == 456

def test_stop_processes(process_manager, mock_state_file):
    # Setup state
    state = {"api_pid": 111, "app_pid": 222}
    mock_state_file.write_text(json.dumps(state))
    
    with patch("os.kill") as mock_kill:
        process_manager.stop_processes()
        
        # Check kills
        assert mock_kill.call_count == 2
        
        # Check file removal
        assert not mock_state_file.exists()

def test_cli_start_command(mock_state_file):
    """Test the full CLI start command flow using mocks"""
    with patch("pathlib.Path.home", return_value=mock_state_file.parent.parent), \
         patch("src.cli.ProcessManager.start_api", return_value=100) as mock_start_api, \
         patch("src.cli.ProcessManager.start_app", return_value=200) as mock_start_app, \
         patch("src.cli.ProcessManager.save_state") as mock_save, \
         patch("time.sleep", side_effect=[None, KeyboardInterrupt]): # 1. Delay, 2. Break loop
        
        result = runner.invoke(app, ["start", "--detach"])
        
        # 0 is success, 130 is Script terminated by Control-C (which we simulate)
        assert result.exit_code in [0, 130]
        assert "API Server started" in result.stdout
        assert "App launched" in result.stdout
        
        mock_start_api.assert_called_once()
        mock_start_app.assert_called_once()
        mock_save.assert_called_with(100, 200)

