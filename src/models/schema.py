"""
Data models and schema for the QA Documentation Generator.
"""

from typing import List, Dict, Optional, Any, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class JobStatus(str, Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ElementType(str, Enum):
    """Types of UI elements that can be identified."""
    BUTTON = "button"
    INPUT_TEXT = "input_text"
    INPUT_PASSWORD = "input_password"
    INPUT_EMAIL = "input_email"
    INPUT_NUMBER = "input_number"
    INPUT_CHECKBOX = "input_checkbox"
    INPUT_RADIO = "input_radio"
    SELECT_DROPDOWN = "select_dropdown"
    TEXTAREA = "textarea"
    LINK = "link"
    FORM = "form"
    IMAGE = "image"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    LABEL = "label"
    IFRAME = "iframe"
    VIDEO = "video"
    GENERAL_CONTAINER = "general_container"


class TestCaseType(str, Enum):
    """Types of test cases that can be generated."""
    FUNCTIONAL = "functional"
    USABILITY = "usability"
    EDGE_CASE = "edge_case"
    ACCESSIBILITY_CHECK = "accessibility_check"


class TestCasePriority(str, Enum):
    """Priority levels for test cases."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Position(BaseModel):
    """Position and dimensions of a UI element."""
    x: int
    y: int
    width: int
    height: int


class UIElement(BaseModel):
    """Representation of a UI element on a web page."""
    element_id: str = Field(..., description="A unique identifier for the element on the page")
    element_type: ElementType
    selector: str = Field(..., description="CSS selector or XPath for the element")
    attributes: Dict[str, str] = Field(default_factory=dict)
    visible_text: Optional[str] = None
    position: Optional[Position] = None


class TestStep(BaseModel):
    """A step in a test case with action and expected result."""
    step_number: int
    action: str
    expected_result: str


class TestCase(BaseModel):
    """Test case generated for the UI element."""
    test_case_id: str
    test_case_title: str
    type: TestCaseType
    priority: Optional[TestCasePriority] = TestCasePriority.MEDIUM
    description: str
    preconditions: List[str] = Field(default_factory=list)
    steps: List[TestStep]
    related_element_id: Optional[str] = None


class QADocumentation(BaseModel):
    """Complete QA documentation for a web page."""
    source_url: HttpUrl
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    page_title: Optional[str] = None
    identified_elements: List[UIElement] = Field(default_factory=list)
    generated_test_cases: List[TestCase] = Field(default_factory=list)


class JobRequest(BaseModel):
    """Request to process one or more URLs."""
    urls: List[HttpUrl]
    auth_config: Optional[Dict[str, Any]] = None
    rate_limit_requests_per_minute: Optional[int] = None


class JobResponse(BaseModel):
    """Response with job details."""
    job_id: str
    status: JobStatus
    urls: List[HttpUrl]
    created_at: datetime
    updated_at: Optional[datetime] = None
    message: Optional[str] = None


class AuthConfig(BaseModel):
    """Authentication configuration for website crawling."""
    auth_type: Literal["basic", "session_token"] = "basic"
    username: Optional[str] = None
    password: Optional[str] = None
    token_type: Optional[Literal["cookie", "bearer"]] = None
    token_name: Optional[str] = None
    token_value: Optional[str] = None 