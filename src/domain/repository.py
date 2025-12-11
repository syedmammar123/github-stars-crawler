from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

@dataclass(frozen=True)  # frozen=True makes it immutable!
class Repository:
    """
    Domain entity representing a GitHub repository.
    Immutable by design (frozen=True).
    """
    id: int
    full_name: str
    star_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_crawled_at: Optional[datetime] = None
    
    @classmethod
    def from_github_response(cls, data: dict) -> 'Repository':
        """
        Factory method to create Repository from GitHub API response.
        This is our anti-corruption layer in the domain.
        """
        # Extract GitHub's internal database ID
        github_id = data.get('databaseId') or data.get('id')
        
        # Handle GitHub's node ID (needs conversion if it's the GraphQL node ID)
        if isinstance(github_id, str) and github_id.startswith('R_'):
            # For now, we'll use the numeric ID from nameWithOwner hash
            # In production, you'd decode the base64 node ID
            github_id = abs(hash(data['nameWithOwner'])) % (10 ** 10)
        
        return cls(
            id=int(github_id),
            full_name=data['nameWithOwner'],
            star_count=data['stargazerCount'],
            last_crawled_at=datetime.now(timezone.utc)
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            'id': self.id,
            'full_name': self.full_name,
            'star_count': self.star_count,
            'last_crawled_at': self.last_crawled_at
        }