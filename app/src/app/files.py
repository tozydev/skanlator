import os


def get_data_dir() -> str:
    return os.path.join(os.getcwd(), "data")


def get_config_path() -> str:
    return os.path.join(get_data_dir(), "config.json")


def get_models_dir() -> str:
    return os.path.join(get_data_dir(), "models")


def get_logs_dir() -> str:
    return os.path.join(get_data_dir(), "logs")
