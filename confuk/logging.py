import logging
from omegaconf import OmegaConf
from rich.console import Console
from rich.logging import RichHandler


def get_console_and_logger(config):
    """Creates an instance of a logger (Python's built-in `logging.Logger`)
    and `rich.console.Console`, ties them together and returns both objects.

    This function accepts a basic logging config which should look like this:
    ```yaml
    logging:
      level: info
      logfile: "<path-to-a-logfile>"  # can be set to `null`
    ```
    """

    # Create a console instance for printing
    console = Console()

    # Create a logger
    logger = logging.getLogger(__name__)

    loaded = OmegaConf.select(config, "logging.loaded", default=False)
    if not loaded:
        level = getattr(logging, config.logging.level.upper())
        logger.setLevel(level)

        # Setup RichHandler (for console logging)
        rich_handler = RichHandler(console=console,
                                   rich_tracebacks=True,
                                   show_time=True,
                                   show_level=True,
                                   markup=True)

        if config.logging.logfile is not None:
            # Setup File Handler (for file logging)
            file_handler = logging.FileHandler(config.logging.logfile, mode="w")
            file_handler.setLevel(level)  # Log everything to the file

            # Format logs for file (plain text)
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(formatter)

            # Add handlers to the logger
            logger.addHandler(file_handler)

        # Add handlers to the logger
        logger.addHandler(rich_handler)

    config.logging.loaded = True

    return console, logger


if __name__ == "__main__":
    config = OmegaConf.from_dotlist(
        [
            "logging.loaded=False",
            "logging.level=debug",
            "logging.logfile=lol.log"
        ]
    )
    console, logger = get_console_and_logger(config)
    logger.info("LOLOLOL")
    console, logger = get_console_and_logger(config)
    logger.info("ROTFLMAO")
