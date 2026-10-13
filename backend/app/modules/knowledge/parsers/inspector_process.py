"""Bound optional native inspection so a pathological PDF cannot hold a worker."""

import asyncio
import logging
import subprocess
import sys

from app.modules.knowledge.parsers.pdf_inspector import PDFInspectionResult

logger = logging.getLogger(__name__)


async def inspect_pdf_safely(content: bytes, timeout: float = 15) -> PDFInspectionResult:
    command = "import sys; from app.modules.knowledge.parsers.pdf_inspector import PDFInspector; print(PDFInspector.inspect_bytes(sys.stdin.buffer.read()).model_dump_json())"
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-c", command, stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(content), timeout=timeout)
        if process.returncode != 0:
            logger.warning("PDF Inspector exited unsuccessfully; retaining native evidence")
            return PDFInspectionResult(inspector_engine="native-inspector-failed")
        return PDFInspectionResult.model_validate_json(stdout.strip().splitlines()[-1])
    except TimeoutError:
        logger.warning("PDF Inspector exceeded %.1fs; retaining native evidence", timeout)
        return PDFInspectionResult(inspector_engine="native-inspector-timeout")
    except (ValueError, IndexError):
        logger.warning("PDF Inspector returned invalid evidence; retaining native evidence")
        return PDFInspectionResult(inspector_engine="native-inspector-invalid")
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()
