"""
Test external reference resolution.

Copyright 2022-2026, Levente Hunyadi

:see: https://github.com/hunyadi/md2conf
"""

import logging
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from md2conf.reference import ExternalReferenceResolver

logging.basicConfig(level=logging.INFO)


class TestExternalReferences(unittest.TestCase):
    def test_resolve_with_page_id(self):
        """Test resolving a file with confluence-page-id."""
        resolver = ExternalReferenceResolver()
        
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "external.md"
            test_file.write_text(
                "<!-- confluence-page-id: 123456 -->\n"
                "<!-- confluence-space-key: TEST -->\n"
                "# External Page\n"
            )
            
            metadata = resolver.resolve(test_file)
            
            self.assertIsNotNone(metadata)
            self.assertEqual(metadata.page_id, "123456")
            self.assertEqual(metadata.space_key, "TEST")
            self.assertFalse(metadata.synchronized)
    
    def test_resolve_without_page_id(self):
        """Test that files without page IDs are not resolved."""
        resolver = ExternalReferenceResolver()
        
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "no-id.md"
            test_file.write_text("# Page Without ID\n")
            
            metadata = resolver.resolve(test_file)
            
            self.assertIsNone(metadata)
    
    def test_resolve_nonexistent_file(self):
        """Test that nonexistent files return None."""
        resolver = ExternalReferenceResolver()
        
        metadata = resolver.resolve(Path("/nonexistent/file.md"))
        
        self.assertIsNone(metadata)
    
    def test_caching(self):
        """Test that results are cached."""
        resolver = ExternalReferenceResolver()
        
        with TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "cached.md"
            test_file.write_text(
                "<!-- confluence-page-id: 789012 -->\n"
                "# Cached Page\n"
            )
            
            # First call
            metadata1 = resolver.resolve(test_file)
            
            # Modify file (shouldn't affect cached result)
            test_file.write_text("# Modified\n")
            
            # Second call should return cached result
            metadata2 = resolver.resolve(test_file)
            
            self.assertEqual(metadata1.page_id, metadata2.page_id)


if __name__ == "__main__":
    unittest.main()
