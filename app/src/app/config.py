import json
import logging
import os
import textwrap

from app.files import get_config_path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    # Capture Section
    "capture_interval": 0.2,
    "capture_sensitivity": 1.0,
    "capture_monitor": 1,
    "capture_region": None,
    "capture_outline_color": "#0078D4",
    "capture_outline_width": 2,

    # OCR Section
    "ocr_det_model_path": "./data/models/PP-OCRv6_det_small.onnx",
    "ocr_cls_model_path": "./data/models/ch_ppocr_mobile_v2.0_cls_mobile.onnx",
    "ocr_rec_model_path": "./data/models/PP-OCRv6_rec_small.onnx",

    # Translation Section
    "translate_overlay_color": "#96000000",
    "translate_font_color": "#FFFFFFFF",
    "translate_font_path": "./data/fonts/MTO-Astro-City.ttf",
    "translate_model_path": "./data/models/gemma-4-E2B-it-Q4_K_M.gguf",
    "translate_system_prompt": textwrap.dedent("""\
        <|turn>system
        You are an expert Manhwa/Webtoon Scanlator. Translate {src_lang} to {dest_lang}.
        [Rules]
        1. Input format: CSV-like (#id|text). Maintain exact #id in output.
        2. Context aware: Group lines by context. Ensure natural dialog flow.
        3. Keeps: Character names, SFX (if untranslated), brand names unchanged.
        4. Tone: Webtoon style, natural, casual, matching character gender/age.
        5. NO explanations, NO intro, NO outro. Output ONLY the translated CSV.
        <turn|><|turn>user
        [Input]
        #id|text
        {user_content}
        
        [Output]
        #id|text<turn|><|turn>model"""),
    "translate_n_ctx": 512,
    "translate_temperature": 0.15,
    "translate_top_p": 0.9,
    "translate_max_tokens": 256,

    # Logging Section
    "log_console_level": "INFO",
    "log_file_level": "DEBUG",
}


class ConfigManager:
    def __init__(self):
        self.config_path = get_config_path()
        self._config = None

    def load(self):
        logger.debug("Loading config from %s", self.config_path)
        if not os.path.exists(self.config_path):
            self._load_default()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with default config to ensure all keys exist
            merged = DEFAULT_CONFIG.copy()
            merged.update(data)
            self._config = merged

        except Exception as e:
            logger.warning("Failed to load config file. Using default config. Error: %s", e)
            self._load_default()

    def get(self, key: str):
        return self._config.get(key) or DEFAULT_CONFIG.get(key)

    def set(self, key: str, value) -> None:
        self._config[key] = value

    def _load_default(self):
        logger.info("Config file not found. Creating default config.")
        self._config = DEFAULT_CONFIG.copy()
        self.save()

    def save(self) -> None:
        logger.debug("Saving config to %s", self.config_path)
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)
