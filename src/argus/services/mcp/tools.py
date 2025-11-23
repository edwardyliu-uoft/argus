"""Argus MCP Tools: tools definition for the Argus MCP server."""

from argus.tools import run


# Argus tools
async def mythril(command: str, args: list) -> dict[str, str]:
    """Run Mythril analysis tool.

    Args:
        command: Command to execute
        args: List of arguments for the command

    Returns:
        Result of the myrthil static analysis as a dictionary
    """
    return run("mythril", command, args)


async def slither(command: str, args: list) -> dict[str, str]:
    """Run Slither analysis tool.

    Args:
        command: Command to execute
        args: List of arguments for the command
    Returns:
        Result of the slither static analysis as a dictionary
    """
    return run("slither", command, args)


# Tools for testing purposes
async def get_weather(city: str = "London") -> dict[str, str]:
    """Get weather data for a city.

    Args:
        city: Name of the city to get weather for

    Returns:
        Dictionary containing weather information
    """
    return {
        "city": city,
        "temperature": "22",
        "condition": "Partly cloudy",
        "humidity": "65%",
    }


async def get_time(city: str = "Toronto") -> dict[str, str]:
    """Get current time for a location.

    Args:
        city: Name of the city to get time for

    Returns:
        Dictionary containing time and date information
    """
    return {
        "city": city,
        "time": "14:30",
        "date": "2024-06-15",
    }
