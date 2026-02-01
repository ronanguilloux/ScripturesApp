import pytest
import re
import subprocess
import os
import sys

# Constants
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(PROJECT_ROOT, "README.md")
MANUAL_PATH = os.path.join(PROJECT_ROOT, "MANUAL.md")
CLI_HELP_PATH = os.path.join(PROJECT_ROOT, "src", "cli_help.py")
BIN_DIR = os.path.join(PROJECT_ROOT, "bin")

def extract_commands_from_text(text):
    """
    Extracts commands starting with 'biblecli', 'tob', or 'bj' from code blocks.
    Basic heuristic: valid commands usually start a line in a code block.
    """
    commands = []
    # Find code blocks
    code_blocks = re.findall(r'```(?:sh|bash)?\n(.*?)```', text, re.DOTALL)
    for block in code_blocks:
        lines = block.strip().split('\n')
        for line in lines:
            line = line.strip()
            # Handle lines starting with bin/ or just the command
            if line.startswith("biblecli") or line.startswith("tob") or line.startswith("bj") or \
               line.startswith("bin/biblecli") or line.startswith("bin/tob") or line.startswith("bin/bj"):
                
                # Normalize command to run from project root (bin/...)
                cmd = line
                if not cmd.startswith("bin/"):
                    if cmd.startswith("biblecli"):
                        cmd = "bin/" + cmd
                    elif cmd.startswith("tob"):
                         cmd = "bin/" + cmd
                    elif cmd.startswith("bj"):
                         cmd = "bin/" + cmd
                
                # Verify it is a complete command (not just a variable assignment etc)
                # Ignore description lines like "biblecli - Command-line interface..."
                if " - " in cmd and cmd.split(" - ")[0].strip() in ["biblecli", "tob", "bj", "bin/biblecli", "bin/tob", "bin/bj"]:
                     continue
                
                # Ignore syntax description lines with placeholders (brackets)
                if "[" in cmd and "]" in cmd:
                     continue

                if " " in cmd or cmd.endswith("biblecli") or cmd.endswith("list books"): 
                    commands.append(cmd)
    
    return commands

def test_readme_commands():
    if not os.path.exists(README_PATH):
        pytest.skip("README.md not found")
        
    with open(README_PATH, "r") as f:
        content = f.read()
        
    commands = extract_commands_from_text(content)
    assert len(commands) > 0, "No commands found in README.md"
    
    for cmd in commands:
        if "make install" in cmd or "pip install" in cmd: continue
        if "git clone" in cmd: continue
        if "export PATH" in cmd: continue
        if "add -c" in cmd: continue # Skipping 'add' commands as they modify state/files
        
        # Execute
        print(f"Testing README command: {cmd}")
        # Run relative to project root
        result = subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode == 0, f"Command failed: {cmd}\nStderr: {result.stderr.decode()}"

def test_manual_commands():
    if not os.path.exists(MANUAL_PATH):
        pytest.skip("MANUAL.md not found")
        
    with open(MANUAL_PATH, "r") as f:
        content = f.read()
        
    commands = extract_commands_from_text(content)
    assert len(commands) > 0, "No commands found in MANUAL.md"
    
    for cmd in commands:
        if "add -c" in cmd: continue 
        print(f"Testing MANUAL command: {cmd}")
        result = subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert result.returncode == 0, f"Command failed: {cmd}\nStderr: {result.stderr.decode()}"

def test_help_output_commands():
    # Get help output dynamically
    cmd = "bin/biblecli --help"
    result = subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert result.returncode == 0
    help_output = result.stdout
    
    # Help output in plain text usually has indented examples
    # We can try to regex for lines starting with whitespace + biblecli/tob/bj
    
    commands = []
    for line in help_output.splitlines():
        line = line.strip()
        if (line.startswith("biblecli") or line.startswith("tob") or line.startswith("bj")) and " " in line:
            # Skip syntax lines like "biblecli [COMMAND...]"
            if "[" in line and "]" in line: continue
            if "search [QUERY]" in line: continue
            if "add -c" in line: continue
            # Skip description lines
            if " - " in line: continue
            
            # Construct runnable command
            run_cmd = "bin/" + line
            commands.append(run_cmd)
            
    assert len(commands) > 0, "No commands found in help output"
    
    for cmd in commands:
        print(f"Testing Help command: {cmd}")
        # Skip search (coming soon)
        if "search" in cmd: continue
        
        res = subprocess.run(cmd, shell=True, cwd=PROJECT_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert res.returncode == 0, f"Command failed: {cmd}\nStderr: {res.stderr.decode()}"
