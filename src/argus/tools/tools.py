import importlib

def run(name: str, command: str, args: list) -> str:
    """
    Run a tool by dynamically importing its controller and executing it.

    Args:
        name: Name of the tool
        command: Command to execute
        args: List of arguments for the command
    Returns:
        Result of the tool execution as a string
    """

    try:
        # Dynamically import the tool's controller module
        module_path = f"argus.tools.{name}.controller"
        controller_module = importlib.import_module(module_path)

        # Get the controller class (assumed to be named 'Controller')
        controller_class = getattr(controller_module, f"{name.capitalize()}Controller")

        # Instantiate the controller
        controller_instance = controller_class()

        # Execute the tool's main functionality
        result = controller_instance.execute(command, args)

        return result

    except ModuleNotFoundError:
        return f"Error: Tool '{name}' not found."

    except AttributeError:
        return f"Error: Controller class not found in tool '{name}'."

    except Exception as e:
        return f"Error executing tool '{name}': {str(e)}"
