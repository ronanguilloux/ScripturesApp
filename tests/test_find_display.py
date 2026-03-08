
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
                highlights=[],
                translations={"fr": "French text"}
            )
        ]
    )
    
    # Patch the UseCase and DependencyContainer so we don't load TF data
    with patch("src.cli.DependencyContainer") as MockDep, patch("src.cli.FindWordsUseCase") as MockUseCase:
        # Configure the mock instance
        mock_instance = MockUseCase.return_value
        mock_instance.execute.return_value = mock_response
        
        mock_norm = MagicMock()
        mock_norm.n1904_to_tob.get.return_value = "Jn"
        MockDep.get_bible_adapter.return_value.normalizer = mock_norm
        
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

