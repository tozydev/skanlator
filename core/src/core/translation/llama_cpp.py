import logging
import os
import time
from typing import List, Optional

import llama_cpp

from ..services import TranslationService, OcrResult, TranslationResult, Language

logger = logging.getLogger(__name__)


def is_vulkan_available():
    if os.name == "nt":
        try:
            import ctypes
            vulkan_lib = ctypes.CDLL("vulkan-1.dll")
            if vulkan_lib:
                return True
        except Exception:
            logger.info("Vulkan is not available on this system. Llama.cpp will run on CPU.")
            pass
    return False


class LlamaCppTranslation(TranslationService):
    def __init__(
            self,
            model_path: str,
            prompt_template: str,
            n_ctx: int = 512,
            temperature: float = 0.0,
            top_p: float = 0.95,
            max_tokens: int = 256,
    ) -> None:
        """Initializes the llama.cpp-based Translation Service (CPU-only)."""
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.prompt_template = prompt_template
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.llm: Optional[llama_cpp.Llama] = None

    def initialize(self) -> None:
        threads = min(min(4, os.cpu_count() or 1), 8)
        has_vulkan = is_vulkan_available()

        logger.info(
            f"Loading Llama.cpp GGUF Model from {self.model_path} with {threads} threads. Vulkan available: {has_vulkan}"
        )

        self.llm = llama_cpp.Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=-1 if has_vulkan else 0,
            n_threads=threads,
            flash_attn=True,
            verbose=True,
        )
        response = self.llm("Hello ", max_tokens=5)
        logger.debug("Warm-up model response: %s", response)
        logger.info("Llama.cpp GGUF model loaded successfully.")

    def translate(self, regions: List[OcrResult], src: Language, dest: Language) -> TranslationResult:
        if not self.llm:
            raise RuntimeError("LlamaCppTranslation model is not initialized. Please call initialize() first.")

        if not regions:
            return TranslationResult(success=False, translations={})

        translations = {region.id: region.text.strip() for region in regions}

        user_lines = []
        for res in regions:
            clean_text = res.text.strip()
            if clean_text:
                user_lines.append(f"#{res.id}|{clean_text}")

        if not user_lines:
            return TranslationResult(success=False, translations={})

        user_content = "\n".join(user_lines)

        full_prompt = self.prompt_template.format(user_content=user_content, src_lang=src.value, dest_lang=dest.value)

        try:
            logger.debug("Sending prompt to Llama.cpp model:\n%s", full_prompt)
            start_time = time.perf_counter()
            response = self.llm(
                prompt=full_prompt,
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens,
                stop=["<turn|>", "<|turn>"],
            )
            inference_time = time.perf_counter() - start_time

            logger.debug(f"Received response from Llama.cpp model in {inference_time:.2f} seconds: {response}")
            text_response = response["choices"][0]["text"].strip()

            translated_lines = text_response.split('\n')
            for line in translated_lines:
                line = line.strip()
                if '|' in line:
                    raw_id, translated_text = line.split('|', 1)

                    # Trích xuất toàn bộ ký số có trong ID
                    clean_id = "".join(c for c in raw_id if c.isdigit())

                    if clean_id in translations:
                        translations[clean_id] = translated_text.strip()

            success = True

        except Exception as e:
            logger.error(f"Error during raw translation completion: {e}", exc_info=True)
            success = False

        return TranslationResult(success=success, translations=translations)
