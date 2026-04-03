from typing import Dict, List, Optional

from pydantic import BaseModel


class ContainerCreate(BaseModel):
    """
    Pydantic model for container creation parameters.
    """

    image: str
    name: Optional[str] = None
    command: Optional[List[str]] = None
    environment: Optional[List[str]] = None
    ports: Optional[Dict[str, str]] = None  # format: {"80/tcp": "8080"}
    volumes: Optional[List[str]] = None  # format: ["/host:/container:ro"]
    start_after_creation: bool = True


class ImagePullRequest(BaseModel):
    """
    Pydantic model for image pull requests.
    """

    image: str
