import sys
from os import makedirs

from PySide6 import QtWidgets
from PySide6.QtWidgets import QStyleFactory

from .config import ConfigManager
from .files import get_models_dir, get_data_dir
from .log import setup_logging
from .ui import FloatingToolbar
from .worker import SkanlatorController


def main() -> None:
    # Set up initial logging before loading config
    setup_logging("INFO", "DEBUG")

    makedirs(get_data_dir(), exist_ok=True)
    makedirs(get_models_dir(), exist_ok=True)

    config_manager = ConfigManager()
    config_manager.load()

    # Reconfigure logging using levels loaded from configuration
    console_level = config_manager.get("log_console_level")
    file_level = config_manager.get("log_file_level")
    setup_logging(console_level, file_level)

    # Create SkanlatorController and initialize the engine
    controller = SkanlatorController(config_manager)
    controller.initialize_engine()

    qt_app = QtWidgets.QApplication(sys.argv)
    qt_app.setStyle(QStyleFactory.create("windows11"))

    # Pass the controller to the toolbar
    toolbox = FloatingToolbar(controller=controller)
    toolbox.show()

    # Run application
    exit_code = qt_app.exec()

    # Stop and destroy engine on exit
    controller.destroy_engine()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
