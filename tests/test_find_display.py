
import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
import sys
import os

# Adjust path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cli import app
from src.domain.models import FindResponse, FindResultItem

runner = CliRunner()

def test_find_no_double_header():
    """Test that the find command does not print the reference header twice."""
    
    # Mock service response
    mock_response = FindResponse(
        lemma="test",
        original="test",
        total=1,
        results=[
            FindResultItem(
                text="Some text",
                ref="Jn 1:1",
                book_code="Jn",
                chapter=1,
                verse=1,
                corpus="NT",
                highlights=[],
                translations={"fr": "French text"}
            )
        ]
    )
    
    # Patch the BibleService class where it is defined, since it is imported inside the function
    with patch("src.application.services.BibleService") as MockService:
        # Configure the mock instance
        mock_instance = MockService.return_value
        mock_instance.find.return_value = mock_response
        # Set normalizer to None or a Mock to avoid AttributeError
        mock_instance.normalizer = None
        
        result = runner.invoke(app, ["find", "test", "-t", "fr"])
        
        if result.exit_code != 0:
            print(result.stdout)
            print(result.exception)
            
        assert result.exit_code == 0
        
        # Check output
        output = result.stdout
        header = "Jn 1:1"
        
        count = output.count(header)
        # Should be 1
        assert count == 1, f"Header '{header}' appeared {count} times in output:\n{output}"

