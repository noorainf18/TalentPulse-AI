"""
File:   core/exceptions.py
Folder: core/

"""

class TalentPulseBaseError(Exception):
    """Base exception for all TalentPulse errors."""
    pass


class AgentError(TalentPulseBaseError):
    """Raised when the LangGraph agent encounters an unrecoverable error."""
    pass


class MCPToolError(TalentPulseBaseError):
    """Raised when a FastMCP tool call fails."""
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        super().__init__(f"[{tool_name}] {message}")


class GitHubFetchError(TalentPulseBaseError):
    """Raised when the GitHub API call fails or returns no usable data."""
    pass


class EvaluationError(TalentPulseBaseError):
    """Raised when Claude fails to generate a valid score/reasoning."""
    pass


class PDFParseError(TalentPulseBaseError):
    """Raised when PDF text extraction fails."""
    pass


class EmailSendError(TalentPulseBaseError):
    """Raised when the email delivery fails."""
    pass
