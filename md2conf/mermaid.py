"""
Publish Markdown files to Confluence wiki.

Copyright 2022-2024, Levente Hunyadi

:see: https://github.com/hunyadi/md2conf
"""

import logging
import os
import os.path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Optional, Literal
import yaml

LOGGER = logging.getLogger(__name__)


def _extract_mermaid_scale( content: str) -> Optional[float]:
    """Extract scale from Mermaid YAML front matter configuration."""
    try:
        properties = MermaidScanner().read(content)
        config = properties.get("config", None) if properties else None
        return config.get("scale", None) if config else None
    except Exception as ex:
        LOGGER.warning("Failed to extract Mermaid properties: %s", ex)
        return None
        
def extract_value(pattern: str, text: str) -> tuple[Optional[str], str]:
    values: list[str] = []

    def _repl_func(matchobj: re.Match[str]) -> str:
        values.append(matchobj.group(1))
        return ""

    text = re.sub(pattern, _repl_func, text, count=1, flags=re.ASCII)
    value = values[0] if values else None
    return value, text


def extract_frontmatter_block(text: str) -> tuple[Optional[str], str]:
    "Extracts the front-matter from a Markdown document as a blob of unparsed text."

    return extract_value(r"(?ms)\A---$(.+?)^---$", text)


def extract_frontmatter_properties(text: str) -> tuple[Optional[dict[str, Any]], str]:
    "Extracts the front-matter from a Markdown document as a dictionary."

    block, text = extract_frontmatter_block(text)

    properties: Optional[dict[str, Any]] = None
    if block is not None:
        data = yaml.safe_load(block)
        if isinstance(data, dict):
            properties = data

    return properties, text

class MermaidScanner:
    """
    Extracts properties from the JSON/YAML front-matter of a Mermaid diagram.
    """
    
    def read(self, content: str) -> dict:
        """
        Extracts rendering preferences from a Mermaid front-matter content.

        ```
        ---
        title: Tiny flow diagram
        config:
            scale: 1
        ---
        flowchart LR
            A[Component A] --> B[Component B]
            B --> C[Component C]
        ```
        """

        properties, text = extract_frontmatter_properties(content)
        if properties is not None:
            title = properties.get("title", None)
            config = properties.get("config", None)

            return {
                "title": title,
                "config": config
            }

        return {"title": None, "config": None}

def is_docker() -> bool:
    "True if the application is running in a Docker container."

    return (
        os.environ.get("CHROME_BIN") == "/usr/bin/chromium-browser"
        and os.environ.get("PUPPETEER_SKIP_DOWNLOAD") == "true"
    )


def get_mmdc() -> str:
    "Path to the Mermaid diagram converter."

    if is_docker():
        return "/home/md2conf/node_modules/.bin/mmdc"
    elif os.name == "nt":
        return "mmdc.cmd"
    else:
        return "mmdc"


def has_mmdc() -> bool:
    "True if Mermaid diagram converter is available on the OS."

    executable = get_mmdc()
    return shutil.which(executable) is not None


def render(source: str, output_format: Literal["png", "svg"] = "png") -> bytes:
    "Generates a PNG or SVG image from a Mermaid diagram source."

    # Use system temp directory to store the output file instead of current working directory
    with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as f:
        filename = f.name
    #filename = f"tmp_mermaid.{output_format}"
    scale = _extract_mermaid_scale(source) or 2
    cmd = [
        get_mmdc(),
        "--input",
        "-",
        "--output",
        filename,
        "--outputFormat",
        output_format,
        "--backgroundColor",
        "transparent",
        "--scale",
        str(scale),
    ]
    root = os.path.dirname(__file__)
    if is_docker():
        cmd.extend(["-p", os.path.join(root, "puppeteer-config.json")])
    LOGGER.debug("Executing: %s", " ".join(cmd))
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        stdout, stderr = proc.communicate(input=source.encode("utf-8"))
        if proc.returncode:
            raise RuntimeError(
                f"failed to convert Mermaid diagram; exit code: {proc.returncode}, "
                f"output:\n{stdout.decode('utf-8')}\n{stderr.decode('utf-8')}"
            )
        with open(filename, "rb") as image:
            return image.read()

    finally:
        if os.path.exists(filename):
            os.remove(filename)
