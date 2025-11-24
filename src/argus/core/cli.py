"""Command-line interface for Argus."""

from importlib.metadata import version, PackageNotFoundError

import click

try:
    __version__ = version("argus")
except PackageNotFoundError:
    __version__ = "0.1.0"  # fallback


@click.group()
@click.version_option(version=__version__, prog_name="argus")
def cli():
    """Argus CLI."""


@cli.command()
@click.argument("project_root", type=click.Path(exists=True))
def analyze(project_root):
    """Analyze a project at PROJECT_ROOT."""
    click.echo(f"Analyzing project at: {project_root}")
    # TODO: Implement analysis logic


@cli.command()
@click.argument("name")
@click.argument("args", nargs=-1)
def tool(name, args):
    """Execute a tool given NAME and ARGS."""
    click.echo(f"Running MCP tool: {name}")
    click.echo(f"Tool arguments: {' '.join(args)}")
    # TODO: Implement tool execution logic


@cli.command()
@click.argument("name")
def resource(name):
    """Access a resource by NAME."""
    click.echo(f"Accessing MCP resource: {name}")
    # TODO: Implement resource access logic


@cli.command()
@click.option(
    "--generator",
    required=True,
    default="generator",
    help="Generator to use for generation",
)
@click.argument("analysis_report", type=click.Path(exists=True))
def generate(generator, analysis_report):
    """Generate tests using GENERATOR based on ANALYSIS_REPORT."""
    click.echo(f"Generating tests with generator: {generator}")
    click.echo(f"Using analysis report: {analysis_report}")
    # TODO: Implement generation logic


def main() -> None:
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
