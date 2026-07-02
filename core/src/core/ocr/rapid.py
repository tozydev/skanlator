import logging
import time

import numpy as np
from rapidocr import RapidOCR, LangDet, LangRec, EngineType, ModelType, OCRVersion
from rapidocr.utils.output import RapidOCROutput

from ..services import OcrService, OcrResult, ServiceStatus

logger = logging.getLogger(__name__)


class RapidOcrService(OcrService):
    def __init__(
            self,
            model_root_dir: str | bytes,
            det_model_path: str | bytes,
            cls_model_path: str | bytes,
            rec_model_path: str | bytes,
    ) -> None:
        """Initializes the RapidOCR engine."""
        self.status = ServiceStatus.IDLE
        params = {
            "Global.use_cls": False,
            "Global.model_root_dir": model_root_dir,
            "EngineConfig.onnxruntime.use_dml": True,
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Det.lang_type": LangDet.EN,
            "Det.model_type": ModelType.SMALL,
            "Det.ocr_version": OCRVersion.PPOCRV6,
            "Det.model_path": det_model_path,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Rec.lang_type": LangRec.EN,
            "Rec.model_type": ModelType.SMALL,
            "Rec.ocr_version": OCRVersion.PPOCRV6,
            "Rec.model_path": rec_model_path,
            "Cls.engine_type": EngineType.ONNXRUNTIME,
            "Cls.lang_type": LangDet.EN,
            "Cls.model_type": ModelType.MOBILE,
            "Cls.ocr_version": OCRVersion.PPOCRV4,
            "Cls.model_path": cls_model_path,
        }

        self.engine = RapidOCR(params=params)

    def initialize(self) -> None:
        """Warm up the RapidOCR models with a dummy image."""
        self.status = ServiceStatus.INITIALIZING
        try:
            dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
            self.engine(dummy_image)
            self.status = ServiceStatus.READY
            logger.info("RapidOCR engine initialized and warmed up successfully.")
        except Exception as e:
            self.status = ServiceStatus.ERROR
            logger.error(f"Failed to initialize RapidOCR engine: {e}", exc_info=True)
            raise

    def destroy(self) -> None:
        """Destroy the OCR engine and release resources."""
        if hasattr(self, "engine"):
            del self.engine
            logger.info("RapidOCR engine destroyed.")

    def detect(self, image: np.ndarray) -> list[OcrResult]:
        """Perform OCR on the given image synchronously using RapidOCR."""
        start_time = time.perf_counter()
        out = self.engine(image)
        pipeline_time = time.perf_counter() - start_time
        if not isinstance(out, RapidOCROutput) or out.boxes is None:
            return []

        ocr_results = []
        for idx, (box, text, score) in enumerate(zip(out.boxes, out.txts or [], out.scores or [])):
            ocr_results.append(
                OcrResult(
                    id=str(idx),
                    box=np.array(box),
                    text=text,
                    confidence=float(score)
                )
            )

        logger.debug("Detected %d text regions in %.2f seconds: %s", len(ocr_results), pipeline_time, ocr_results)
        return ocr_results
