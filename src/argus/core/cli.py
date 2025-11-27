"""
Argus CLI: Command-line interface for running security analysis
"""

from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import sys
import logging
import json
import asyncio
import click

from argus.core import conf, ArgusOrchestrator

try:
    __version__ = version("argus")
except PackageNotFoundError:
    __version__ = "0.1.0"  # fallback


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set argus.console logger
    logger = logging.getLogger("argus.console")
    logger.setLevel(level)


@click.group()
@click.version_option(version=__version__, prog_name="argus")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx, verbose):
    """Argus CLI."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose)


@cli.command()
@click.argument("project_root", type=click.Path(exists=True))
@click.pass_context
def analyze(ctx, project_root):
    """Analyze a project at PROJECT_ROOT."""

    exit_code = asyncio.run(_analyze(project_root, ctx.obj["verbose"]))
    ctx.exit(exit_code)


async def _analyze(project_root: str, verbose: bool) -> int:
    logger = logging.getLogger("argus.console")
    logger.info("Analyzing project at: %s", project_root)

    # Validate project path
    project = Path(project_root).resolve()
    if not project.exists():
        logger.error("Project path does not exist: %s", project)
        return 1
    if not project.is_dir():
        logger.error("Project path is not a directory: %s", project)
        return 1

    # Create and run orchestrator
    try:
        orchestrator = ArgusOrchestrator(project.as_posix())
        result = await orchestrator.run()

        if result.get("success"):
            logger.info("\nAnalysis completed successfully")
            logger.info("\tContracts analyzed: %d", result.get("contracts_analyzed", 0))
            logger.info("\tTests generated: %d", result.get("tests_generated", 0))
            logger.info("\tDuration: %.1f s", result.get("duration", 0))
            if result.get("report_path"):
                logger.info("\tReport: %s", result.get("report_path"))
            return 0
        else:
            logger.error("\nAnalysis failed: %s", result.get("error", "Unknown error"))
            return 1

    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user.")
        return -1

    except Exception as e:
        logger.error("Unexpected error: %s", e)
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


@cli.command()
@click.option(
    "--key",
    default=None,
    help="Key to show from the configuration (dot notation)",
)
@click.pass_context
def config(ctx, key):
    """Show the identified Argus configuration."""
    logger = logging.getLogger("argus.console")
    logger.info("Argus configuration:\n")
    logger.info("> Path: %s", conf.path)
    if key:
        logger.info("> Key: Value")
        value = json.dumps(conf.get(key, "undefined"), indent=2)
        logger.info("%s: %s", key, value)
    else:
        logger.info("> Configuration Dictionary:")
        logger.info(json.dumps(conf.config, indent=2))


@cli.command()
@click.argument("name")
@click.argument("args", nargs=-1)
@click.pass_context
def tool(ctx, name, args):
    """Execute a tool given NAME and ARGS."""
    logger = logging.getLogger("argus.console")
    logger.info("Running MCP tool: %s", name)
    logger.debug("Tool arguments: %s", " ".join(args))
    # TODO: Implement tool execution logic


@cli.command()
@click.argument("name")
@click.pass_context
def resource(ctx, name):
    """Access a resource by NAME."""
    logger = logging.getLogger("argus.console")
    logger.info("Accessing MCP resource: %s", name)
    # TODO: Implement resource access logic


@cli.command()
@click.option(
    "--generator",
    default="generator",
    help="Generator to use for generation",
)
@click.argument("analysis_report", type=click.Path(exists=True))
@click.pass_context
def generate(ctx, generator, analysis_report):
    """Generate tests using GENERATOR based on ANALYSIS_REPORT."""
    logger = logging.getLogger("argus.console")
    logger.info("Generating tests with generator: %s", generator)
    logger.debug("Using analysis report: %s", analysis_report)
    # TODO: Implement generation logic


def main() -> None:
    """Entry point for CLI."""

    # pylint: disable=no-value-for-parameter
    cli()


if __name__ == "__main__":
    main()
