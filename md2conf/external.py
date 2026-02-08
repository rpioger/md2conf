"""
External reference resolution for markdown files outside the sync directory.

Copyright 2022-2026, Levente Hunyadi

:see: https://github.com/hunyadi/md2conf
"""

import logging
from pathlib import Path

from .metadata import ConfluencePageMetadata
from .scanner import Scanner

LOGGER = logging.getLogger(__name__)


class ExternalReferenceResolver:
    """
    Resolves references to markdown files outside the current directory hierarchy.
    
    Files are considered resolvable if they:
    1. Exist on the file system
    2. Have a valid confluence-page-id tag
    3. Can be successfully parsed
    """
    
    def __init__(self) -> None:
        self._cache: dict[Path, ConfluencePageMetadata | None] = {}
    
    def resolve(self, markdown_path: Path) -> ConfluencePageMetadata | None:
        """
        Extract page_id, space_key, and title from external markdown file.
        
        :param markdown_path: Absolute path to the markdown file
        :returns: ConfluencePageMetadata if resolvable, None otherwise
        """
        if markdown_path in self._cache:
            return self._cache[markdown_path]
        
        if not markdown_path.exists():
            LOGGER.debug("External file does not exist: %s", markdown_path)
            self._cache[markdown_path] = None
            return None
        
        try:
            # Parse the file using Scanner
            document = Scanner().read(markdown_path)
            
            # Must have a page_id to be resolvable
            if document.properties.page_id is None:
                LOGGER.debug("External file %s has no confluence-page-id tag", markdown_path)
                self._cache[markdown_path] = None
                return None
            
            metadata = ConfluencePageMetadata(
                page_id=document.properties.page_id,
                space_key=document.properties.space_key or "UNKNOWN",
                title=document.properties.title or markdown_path.stem,
                synchronized=False  # External files are not synchronized
            )
            
            self._cache[markdown_path] = metadata
            LOGGER.info("Resolved external reference: %s -> page %s", markdown_path, metadata.page_id)
            return metadata
            
        except Exception as e:
            LOGGER.warning("Failed to resolve external reference %s: %s", markdown_path, e)
            self._cache[markdown_path] = None
            return None
