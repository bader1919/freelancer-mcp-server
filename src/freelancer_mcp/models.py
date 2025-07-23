"""
Pydantic models for request/response validation
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from freelancersdk.session import Session
from .config import settings
from .exceptions import AuthenticationError


class ProjectSearchRequest(BaseModel):
    """Request model for project search"""
    query: str = Field(description="Search query for projects")
    sort_field: str = Field(default="time_updated", description="Field to sort by")
    or_search_query: bool = Field(default=True, description="Use OR logic for search terms")
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=100)


class ProjectDetailsRequest(BaseModel):
    """Request model for project details"""
    project_ids: List[int] = Field(description="List of project IDs to fetch")
    full_description: bool = Field(default=True, description="Include full project description")
    include_jobs: bool = Field(default=True, description="Include job/skill information")
    include_qualifications: bool = Field(default=False, description="Include qualification requirements")


class UserSearchRequest(BaseModel):
    """Request model for freelancer search"""
    query: str = Field(description="Search query for freelancers")
    job_ids: Optional[List[int]] = Field(default=None, description="Filter by specific job/skill IDs")
    location_ids: Optional[List[int]] = Field(default=None, description="Filter by location IDs")
    limit: int = Field(default=10, description="Maximum number of results", ge=1, le=100)


class FreelancerSession:
    """Manages Freelancer API session"""
    
    def __init__(self):
        self.session = None
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize the Freelancer API session"""
        if not settings.oauth_token:
            raise AuthenticationError("OAuth token is required")
        
        try:
            self.session = Session(
                oauth_token=settings.oauth_token,
                url=settings.api_url
            )
        except Exception as e:
            raise AuthenticationError(f"Failed to create session: {e}")
    
    def get_session(self) -> Session:
        """Get the current session, creating it if necessary"""
        if not self.session:
            self._initialize_session()
        
        if not self.session:
            raise AuthenticationError("No valid session available")
        
        return self.session
