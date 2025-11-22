class BaseController:
    """Base controller class for Argus tools."""

    def __init__(self):
        pass

    async def execute(self, *args, **kwargs):
        """Execute the tool's main functionality."""
        raise NotImplementedError("This method should be overridden by subclasses.")
