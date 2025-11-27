# Example Plugin

This is a simple example plugin for Argus that demonstrates how to create a custom MCP tool plugin.

## What This Plugin Does

The example plugin provides a simple tool called `greet` that:

- Takes a name as input
- Returns a friendly greeting message
- Demonstrates basic plugin structure and configuration

## Plugin Structure

```
example-plugin/
├── README.md              # This file
├── pyproject.toml         # Package configuration and entry points
└── example_plugin/
    ├── __init__.py        # Package init (exports the plugin class)
    └── plugin.py          # Main plugin implementation
```

## Installation

To install this plugin for use with Argus:

```bash
# From the example-plugin directory
pip install -e .
```

Or to install from the parent directory:

```bash
pip install -e examples/example-plugin
```

## How It Works

### 1. Plugin Class

The plugin inherits from `MCPToolPlugin` and implements:

- `name`: Unique identifier for the plugin
- `version`: Plugin version
- `description`: Human-readable description
- `initialize()`: Setup method called when plugin is loaded
- Tool methods: Async functions that implement the actual functionality

### 2. Entry Point Registration

In `pyproject.toml`, the plugin is registered under the `argus.mcp.tools` entry point:

```toml
[project.entry-points."argus.mcp.tools"]
example = "example_plugin:ExamplePlugin"
```

This tells Argus to discover and load this plugin automatically.

### 3. Tool Implementation

The `greet` tool is an async function that:

- Accepts parameters (name, language)
- Performs the action (generates greeting)
- Returns a structured result

## Usage

Once installed, the plugin is automatically discovered by Argus. You can use it via the MCP server:

```python
# Through the MCP client
result = await session.call_tool(
    "greet",
    arguments={
        "name": "Alice",
        "language": "en"
    }
)
```

Or directly in code:

```python
from argus.plugins import get_plugin_registry

# Get the plugin
registry = get_plugin_registry()
registry.discover_plugins("argus.mcp.tools")
example_plugin = registry.get_plugin("example", "argus.mcp.tools")

# Initialize it
example_plugin.initialize()

# Use the tool
result = await hello_plugin.greet(name="Alice", language="en")
print(result)  # {"success": True, "greeting": "Hello, Alice!", ...}
```

## Extending This Example

You can extend this plugin by:

1. **Adding more tools**: Add more async methods and register them in `initialize()`
2. **Adding configuration**: Define a `config_schema` and use config in `initialize()`
3. **Adding external dependencies**: List them in `pyproject.toml` dependencies
4. **Adding resources**: Create a `MCPResourcePlugin` instead
5. **Adding prompts**: Create a `MCPPromptPlugin` instead

## Testing

Create tests in a `tests/` directory:

```bash
pytest tests/
```

## Key Concepts

- **Plugin Discovery**: Argus uses Python entry points to automatically discover plugins
- **Initialization**: Plugins are initialized with configuration when loaded
- **Tools**: Async functions that the LLM can call to perform actions
- **MCP Protocol**: Tools follow the Model Context Protocol for standardized communication

## See Also

- Main Argus documentation
- MCP Protocol specification
- Other example plugins in `src/argus/server/tools/`
