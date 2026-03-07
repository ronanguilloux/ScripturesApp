import pytest
from typer.testing import CliRunner
import os
import json
from src.cli import app

runner = CliRunner()

def test_generate_openapi(tmp_path):
    """Test generating the OpenAPI JSON file."""
    output_file = tmp_path / "openapi.json"
    
    result = runner.invoke(app, ["generate-openapi", "-o", str(output_file)])
    
    assert result.exit_code == 0
    assert "Successfully generated" in result.output
    
    # Check if file exists and is valid JSON
    assert output_file.exists()
    
    with open(output_file, 'r') as f:
        schema = json.load(f)
        
    # Check for basic OpenAPI structure
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema
    assert "/health" in schema["paths"]
    assert "/search" in schema["paths"] # From semantic search
    assert "/api/v1/search" in schema["paths"] # From main app
