"""
Main MCP Server implementation for Freelancer.com API
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from .config import settings
from .models import (
    ProjectSearchRequest, ProjectDetailsRequest, 
    UserSearchRequest, FreelancerSession
)
from .exceptions import FreelancerMCPError, AuthenticationError

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FreelancerMCPServer:
    """Main MCP server class for Freelancer API integration."""
    
    def __init__(self):
        self.mcp = FastMCP(settings.server_name)
        self.session_manager = FreelancerSession()
        self._setup_tools()
        self._setup_resources()
        
    def _setup_tools(self):
        """Set up MCP tools."""
        
        @self.mcp.tool()
        def search_projects(request: ProjectSearchRequest) -> Dict[str, Any]:
            """
            Search for projects on Freelancer.com
            
            Args:
                request: ProjectSearchRequest with search parameters
                
            Returns:
                Dict containing search results with project information
            """
            try:
                session = self.session_manager.get_session()
                
                # Import SDK functions
                from freelancersdk.resources.projects.projects import search_projects as sdk_search
                from freelancersdk.resources.projects.helpers import create_search_projects_filter
                from freelancersdk.resources.projects.exceptions import ProjectsNotFoundException
                
                search_filter = create_search_projects_filter(
                    sort_field=request.sort_field,
                    or_search_query=request.or_search_query,
                )
                
                result = sdk_search(
                    session,
                    query=request.query,
                    search_filter=search_filter
                )
                
                # Process and return results
                projects_data = []
                if hasattr(result, 'projects') and result.projects:
                    for project in result.projects[:request.limit]:
                        project_info = {
                            'id': getattr(project, 'id', None),
                            'title': getattr(project, 'title', None),
                            'description': getattr(project, 'description', None),
                            'type': getattr(project, 'type', None),
                            'budget': self._extract_budget_info(project),
                            'owner': self._extract_owner_info(project),
                            'time_updated': str(getattr(project, 'time_updated', None)),
                            'submitdate': str(getattr(project, 'submitdate', None)),
                            'bid_count': getattr(project, 'bid_count', None),
                        }
                        projects_data.append(project_info)
                
                return {
                    'success': True,
                    'query': request.query,
                    'total_results': len(projects_data),
                    'projects': projects_data
                }
                
            except Exception as e:
                logger.error(f"Error in search_projects: {e}")
                return {
                    'success': False,
                    'error': 'Search failed',
                    'message': 'Please check your OAuth token and try again'
                }

        @self.mcp.tool()
        def search_freelancers(request: UserSearchRequest) -> Dict[str, Any]:
            """
            Search for freelancers on Freelancer.com
            
            Args:
                request: UserSearchRequest with search parameters
                
            Returns:
                Dict containing freelancer search results
            """
            try:
                session = self.session_manager.get_session()
                
                # Import SDK functions
                from freelancersdk.resources.users.users import search_freelancers as sdk_search
                from freelancersdk.resources.users.exceptions import UsersNotFoundException
                
                # Build search parameters
                search_params = {
                    'query': request.query,
                }
                
                if request.job_ids:
                    search_params['job_ids'] = request.job_ids
                if request.location_ids:
                    search_params['location_ids'] = request.location_ids
                    
                result = sdk_search(session, **search_params)
                
                # Process results
                freelancers_data = []
                if hasattr(result, 'users') and result.users:
                    for user in result.users[:request.limit]:
                        freelancer_info = {
                            'id': getattr(user, 'id', None),
                            'username': getattr(user, 'username', None),
                            'display_name': getattr(user, 'display_name', None),
                            'avatar': getattr(user, 'avatar', None),
                            'location': self._extract_location_info(user),
                            'status': getattr(user, 'status', None),
                            'reputation': self._extract_reputation_info(user),
                            'hourly_rate': getattr(user, 'hourly_rate', None),
                            'jobs': self._extract_user_jobs_info(user)
                        }
                        freelancers_data.append(freelancer_info)
                
                return {
                    'success': True,
                    'query': request.query,
                    'total_results': len(freelancers_data),
                    'freelancers': freelancers_data
                }
                
            except Exception as e:
                logger.error(f"Error in search_freelancers: {e}")
                return {
                    'success': False,
                    'error': 'Search failed',
                    'message': 'Please check your OAuth token and try again'
                }

        @self.mcp.tool()
        def health_check() -> Dict[str, Any]:
            """
            Check the health status of the MCP server and Freelancer API connection
            
            Returns:
                Dict containing health status information
            """
            try:
                session = self.session_manager.get_session()
                
                health_status = {
                    'server_status': 'healthy',
                    'api_connection': 'active',
                    'session_valid': True,
                    'timestamp': datetime.now().isoformat(),
                    'api_url': settings.api_url,
                    'version': settings.server_version
                }
                
                return health_status
                
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return {
                    'server_status': 'degraded',
                    'api_connection': 'failed',
                    'session_valid': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }

    def _setup_resources(self):
        """Set up MCP resources."""
        
        @self.mcp.resource("freelancer://config")
        async def get_config_resource() -> str:
            """Get current Freelancer API configuration"""
            import json
            return json.dumps({
                'api_url': settings.api_url,
                'has_token': bool(settings.oauth_token),
                'session_active': bool(self.session_manager.session),
                'server_name': settings.server_name,
                'version': settings.server_version
            }, indent=2)

        @self.mcp.resource("freelancer://help")
        async def get_help_resource() -> str:
            """Get help information about available tools and resources"""
            import json
            help_info = {
                'tools': {
                    'search_projects': 'Search for projects by query with filtering options',
                    'search_freelancers': 'Search for freelancers with various filters',
                    'health_check': 'Check server and API connectivity status'
                },
                'resources': {
                    'freelancer://config': 'Current API configuration status',
                    'freelancer://help': 'This help information',
                    'freelancer://examples': 'Usage examples for all tools'
                },
                'authentication': {
                    'required_env_vars': {
                        'FLN_OAUTH_TOKEN': 'OAuth2 token for Freelancer API (required)',
                        'FLN_URL': 'API base URL (optional, defaults to https://www.freelancer.com)'
                    },
                    'how_to_get_token': 'Visit https://developers.freelancer.com to create an app and get OAuth token'
                }
            }
            return json.dumps(help_info, indent=2)

    # Helper methods for data extraction
    def _extract_budget_info(self, project) -> Dict[str, Any]:
        """Extract budget information from project."""
        if hasattr(project, 'budget') and project.budget:
            return {
                'minimum': getattr(project.budget, 'minimum', None),
                'maximum': getattr(project.budget, 'maximum', None),
                'currency': getattr(project.budget.currency, 'code', None) if hasattr(project.budget, 'currency') else None
            }
        return {'minimum': None, 'maximum': None, 'currency': None}

    def _extract_owner_info(self, project) -> Dict[str, Any]:
        """Extract owner information from project."""
        if hasattr(project, 'owner') and project.owner:
            return {
                'id': getattr(project.owner, 'id', None),
                'username': getattr(project.owner, 'username', None),
                'display_name': getattr(project.owner, 'display_name', None)
            }
        return {'id': None, 'username': None, 'display_name': None}

    def _extract_location_info(self, user) -> Dict[str, Any]:
        """Extract location information from user."""
        if hasattr(user, 'location') and user.location:
            return {
                'country': getattr(user.location.country, 'name', None) if hasattr(user.location, 'country') else None,
                'city': getattr(user.location.city, 'name', None) if hasattr(user.location, 'city') else None
            }
        return {'country': None, 'city': None}

    def _extract_reputation_info(self, user) -> Dict[str, Any]:
        """Extract reputation information from user."""
        if hasattr(user, 'reputation') and user.reputation:
            return {
                'entire_site': getattr(user.reputation.entire_site, 'rating', None) if hasattr(user.reputation, 'entire_site') else None,
                'category_ratings': getattr(user.reputation, 'category_ratings', [])
            }
        return {'entire_site': None, 'category_ratings': []}

    def _extract_user_jobs_info(self, user) -> List[Dict[str, Any]]:
        """Extract jobs/skills information from user."""
        if hasattr(user, 'jobs') and user.jobs:
            return [
                {
                    'id': getattr(job, 'id', None),
                    'name': getattr(job, 'name', None)
                } for job in user.jobs
            ]
        return []

    def run(self):
        """Start the MCP server."""
        logger.info("Starting Freelancer MCP Server...")
        logger.info(f"Server: {settings.server_name} v{settings.server_version}")
        logger.info(f"API URL: {settings.api_url}")
        
        if not settings.oauth_token:
            logger.error("Missing required environment variable: FLN_OAUTH_TOKEN")
            logger.error("Please set your Freelancer OAuth token in the environment")
            return
        
        logger.info("Available tools: search_projects, search_freelancers, health_check")
        logger.info("Available resources: freelancer://config, freelancer://help")
        
        self.mcp.run()


def main():
    """Main entry point for the MCP server"""
    try:
        server = FreelancerMCPServer()
        server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise


if __name__ == "__main__":
    main()
