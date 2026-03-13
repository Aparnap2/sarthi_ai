"""
Import guard for Sarthi v4.2 LLM factory pattern.

Usage:
    Add this import at the top of agent files to enforce factory pattern:
    
    ```python
    from src.config.llm_guard import enforce_llm_factory
    enforce_llm_factory(__file__)
    ```

This module:
1. Scans the importing file for direct AzureOpenAI instantiation
2. Raises ImportError if found
3. Fails fast at import time (not runtime)

ONE RULE: All LLM calls MUST go through src/config/llm.py factory.
No direct AzureOpenAI instantiation in agents. Ever.
"""
import re
import os
from pathlib import Path


# Pattern to detect direct AzureOpenAI instantiation
# Matches: AzureOpenAI( but NOT imports or comments
AZURE_OPENAI_INSTANTIATION_PATTERN = re.compile(
    r'^[^#]*\bAzureOpenAI\s*\(',  # Not in comment, followed by (
    re.MULTILINE
)

# Files that are allowed to import AzureOpenAI directly
ALLOWED_FILES = {
    'llm.py',  # The factory itself
    'llm_guard.py',  # This guard module
}


def enforce_llm_factory(file_path: str) -> None:
    """
    Enforce LLM factory pattern for the given file.
    
    Scans the file for direct AzureOpenAI instantiation and raises
    ImportError if found.
    
    Args:
        file_path: Path to the file being imported
        
    Raises:
        ImportError: If direct AzureOpenAI instantiation is detected
        
    Example:
        >>> from src.config.llm_guard import enforce_llm_factory
        >>> enforce_llm_factory(__file__)
    """
    filename = os.path.basename(file_path)
    
    # Skip allowed files
    if filename in ALLOWED_FILES:
        return
    
    # Read file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (IOError, OSError):
        # Can't read file, skip check
        return
    
    # Check for violations
    matches = AZURE_OPENAI_INSTANTIATION_PATTERN.findall(content)
    
    if matches:
        raise ImportError(
            f"LLM Factory Pattern Violation in {filename}!\n"
            f"Direct AzureOpenAI instantiation detected: {matches[0]}\n\n"
            f"FIX: Use the factory pattern instead:\n"
            f"  from src.config.llm import get_llm_client\n"
            f"  client = get_llm_client()\n\n"
            f"See: apps/ai/src/config/llm.py"
        )


def scan_directory_for_violations(directory: str) -> list[str]:
    """
    Scan a directory for LLM factory pattern violations.
    
    Useful for CI/CD checks or pre-commit hooks.
    
    Args:
        directory: Directory to scan
        
    Returns:
        List of file paths with violations
    """
    violations = []
    
    for root, _, files in os.walk(directory):
        for filename in files:
            if not filename.endswith('.py'):
                continue
            
            if filename in ALLOWED_FILES:
                continue
            
            file_path = os.path.join(root, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if AZURE_OPENAI_INSTANTIATION_PATTERN.search(content):
                    violations.append(file_path)
            except (IOError, OSError):
                continue
    
    return violations
