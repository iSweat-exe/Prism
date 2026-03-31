import aiodocker


class DockerService:
    def __init__(self):
        self.client: aiodocker.Docker = None

    def init(self):
        """
        Initialize the aiodocker client.
        """
        if self.client is None:
            self.client = aiodocker.Docker()

    async def close(self):
        """
        Close the aiodocker client.
        """
        if self.client is not None:
            await self.client.close()
            self.client = None


# Global singleton instance
docker_service = DockerService()
