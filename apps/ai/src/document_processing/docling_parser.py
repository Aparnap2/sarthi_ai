"""
Docling PDF Parser for Sarthi.

Converts PDFs (bank statements, invoices, contracts) to structured JSON
with preserved table structure, section hierarchy, and bounding boxes.

Example:
    >>> parser = DoclingParser()
    >>> result = parser.parse_pdf("invoices/aws_march_2026.pdf")
    >>> print(f"Parsed {len(result['pages'])} pages")
    
    >>> chunks = parser.parse_to_doc_chunks("invoices/aws_march_2026.pdf")
    >>> for chunk in chunks:
    ...     print(f"Chunk: {chunk.text[:100]}...")
    
    >>> tables = parser.extract_tables("invoices/aws_march_2026.pdf")
    >>> for table in tables:
    ...     print(f"Table on page {table['page_no']}: {len(table['cells'])} cells")
"""
from docling.document_converter import DocumentConverter
from docling.chunking import DocChunk
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PipelineOptions
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class DoclingParserError(Exception):
    """Base exception for Docling parser errors."""

    pass


class PDFParseError(DoclingParserError):
    """Raised when PDF parsing fails."""

    pass


class TableExtractionError(DoclingParserError):
    """Raised when table extraction fails."""

    pass


class DoclingParser:
    """
    Parse PDFs to structured JSON using Docling.
    
    Supports:
    - PDF, DOCX, and image formats
    - Table structure preservation with TableFormer
    - Bounding box extraction for layout analysis
    - Section hierarchy preservation
    - Character-level source tracing
    
    Attributes:
        converter: DocumentConverter instance for PDF parsing
        
    Example:
        >>> parser = DoclingParser()
        >>> result = parser.parse_pdf("invoice.pdf")
        >>> assert "filename" in result
        >>> assert "pages" in result
        >>> assert "metadata" in result
    """

    def __init__(
        self,
        pipeline_options: Optional[PipelineOptions] = None,
        do_ocr: bool = True,
        do_table_structure: bool = True,
    ) -> None:
        """
        Initialize Docling parser.
        
        Args:
            pipeline_options: Optional pipeline configuration
            do_ocr: Enable OCR for scanned documents (default: True)
            do_table_structure: Enable table structure extraction (default: True)
            
        Example:
            >>> parser = DoclingParser(do_ocr=True, do_table_structure=True)
        """
        if pipeline_options is None:
            pipeline_options = PipelineOptions()
            pipeline_options.do_ocr = do_ocr
            pipeline_options.do_table_structure = do_table_structure
        
        self.converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF, InputFormat.DOCX, InputFormat.IMAGE],
            pipeline_options=pipeline_options,
        )
        logger.info("DoclingParser initialized with OCR=%s, TableStructure=%s", do_ocr, do_table_structure)

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse PDF to structured JSON.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with:
            - filename: Source filename
            - pages: List of page dicts with sections, tables, text_blocks
            - metadata: author, creation_date, etc.
            
        Raises:
            PDFParseError: If PDF parsing fails
            
        Example:
            >>> parser = DoclingParser()
            >>> result = parser.parse_pdf("invoices/aws_march_2026.pdf")
            >>> print(f"Filename: {result['filename']}")
            >>> print(f"Pages: {len(result['pages'])}")
            >>> print(f"Metadata: {result['metadata']}")
        """
        try:
            path = Path(pdf_path)
            if not path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            logger.info("Parsing PDF: %s", pdf_path)
            result = self.converter.convert(str(path))
            
            # Export to structured JSON
            json_export = result.document.export_to_dict()
            
            parsed_result = {
                "filename": path.name,
                "pages": json_export.get("pages", []),
                "metadata": json_export.get("metadata", {}),
                "text": result.document.export_to_text(),
            }
            
            logger.info(
                "Parsed %s: %d pages, %d tables",
                pdf_path,
                len(parsed_result["pages"]),
                sum(len(page.get("tables", [])) for page in parsed_result["pages"]),
            )
            
            return parsed_result
            
        except Exception as err:
            logger.error("Failed to parse PDF %s: %s", pdf_path, err)
            raise PDFParseError(f"Failed to parse PDF {pdf_path}: {err}") from err

    def parse_to_doc_chunks(
        self,
        pdf_path: str,
        max_chunk_size: int = 500,
        min_chunk_size: int = 100,
    ) -> List[DocChunk]:
        """
        Parse PDF to list of DocChunk objects.
        
        Each DocChunk has:
        - text: The chunk text
        - meta.origin.filename: Source filename
        - meta.headings: Section hierarchy
        - meta.doc_items[0].prov[0].page_no: Page number
        - meta.doc_items[0].prov[0].bbox: Bounding box
        
        Args:
            pdf_path: Path to PDF file
            max_chunk_size: Maximum characters per chunk (default: 500)
            min_chunk_size: Minimum characters per chunk (default: 100)
            
        Returns:
            List of DocChunk objects with text and metadata
            
        Raises:
            PDFParseError: If PDF parsing fails
            
        Example:
            >>> parser = DoclingParser()
            >>> chunks = parser.parse_to_doc_chunks("board_deck_q1_2026.pdf")
            >>> for chunk in chunks:
            ...     print(f"Page {chunk.meta.doc_items[0].prov[0].page_no}: {chunk.text[:50]}...")
        """
        try:
            path = Path(pdf_path)
            logger.info("Parsing PDF to chunks: %s", pdf_path)
            result = self.converter.convert(str(path))
            
            # Chunk the document
            chunks = list(result.document.chunk())
            
            logger.info(
                "Created %d chunks from %s (max_size=%d, min_size=%d)",
                len(chunks),
                pdf_path,
                max_chunk_size,
                min_chunk_size,
            )
            
            return chunks
            
        except Exception as err:
            logger.error("Failed to chunk PDF %s: %s", pdf_path, err)
            raise PDFParseError(f"Failed to chunk PDF {pdf_path}: {err}") from err

    def extract_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract tables from PDF with structure preserved.
        
        Uses TableFormer model to predict table structure and bounding boxes
        from PDF images. Preserves cell row/column indices and text content.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of dicts with:
            - page_no: Page number (0-indexed)
            - bbox: Bounding box [left, top, right, bottom]
            - cells: List of cell dicts {row, col, text}
            - num_rows: Number of rows in table
            - num_cols: Number of columns in table
            
        Raises:
            TableExtractionError: If table extraction fails
            
        Example:
            >>> parser = DoclingParser()
            >>> tables = parser.extract_tables("bank_statement_march_2026.pdf")
            >>> for table in tables:
            ...     print(f"Table on page {table['page_no']}: {table['num_rows']}x{table['num_cols']}")
            ...     for cell in table['cells'][:5]:
            ...         print(f"  [{cell['row']},{cell['col']}]: {cell['text']}")
        """
        try:
            path = Path(pdf_path)
            logger.info("Extracting tables from PDF: %s", pdf_path)
            result = self.converter.convert(str(path))
            
            tables = []
            for page_idx, page in enumerate(result.document.pages):
                page_tables = []
                
                for table in page.tables:
                    table_data = {
                        "page_no": page_idx,
                        "bbox": list(table.bbox.as_tuple()),
                        "cells": [
                            {
                                "row": cell.row_idx,
                                "col": cell.col_idx,
                                "text": cell.text.strip() if cell.text else "",
                            }
                            for cell in table.cells
                        ],
                        "num_rows": table.num_rows,
                        "num_cols": table.num_cols,
                    }
                    page_tables.append(table_data)
                
                tables.extend(page_tables)
            
            logger.info(
                "Extracted %d tables from %s",
                len(tables),
                pdf_path,
            )
            
            return tables
            
        except Exception as err:
            logger.error("Failed to extract tables from PDF %s: %s", pdf_path, err)
            raise TableExtractionError(f"Failed to extract tables from PDF {pdf_path}: {err}") from err

    def extract_text_blocks(
        self,
        pdf_path: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract text blocks with bounding boxes from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of dicts with:
            - page_no: Page number (0-indexed)
            - text: Text content
            - bbox: Bounding box [left, top, right, bottom]
            - section: Section heading (if applicable)
            
        Example:
            >>> parser = DoclingParser()
            >>> blocks = parser.extract_text_blocks("invoice.pdf")
            >>> for block in blocks:
            ...     print(f"Page {block['page_no']}: {block['text'][:50]}...")
        """
        try:
            path = Path(pdf_path)
            logger.info("Extracting text blocks from PDF: %s", pdf_path)
            result = self.converter.convert(str(path))
            
            text_blocks = []
            for page_idx, page in enumerate(result.document.pages):
                for text_item in page.texts:
                    block_data = {
                        "page_no": page_idx,
                        "text": text_item.text.strip() if text_item.text else "",
                        "bbox": list(text_item.bbox.as_tuple()),
                    }
                    text_blocks.append(block_data)
            
            logger.info(
                "Extracted %d text blocks from %s",
                len(text_blocks),
                pdf_path,
            )
            
            return text_blocks
            
        except Exception as err:
            logger.error("Failed to extract text blocks from PDF %s: %s", pdf_path, err)
            raise PDFParseError(f"Failed to extract text blocks from PDF {pdf_path}: {err}") from err

    def export_to_json(
        self,
        pdf_path: str,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse PDF and export to JSON file.
        
        Args:
            pdf_path: Path to PDF file
            output_path: Optional path to write JSON output (default: None)
            
        Returns:
            Parsed JSON dict
            
        Example:
            >>> parser = DoclingParser()
            >>> result = parser.export_to_json("invoice.pdf", "output/invoice.json")
        """
        parsed = self.parse_pdf(pdf_path)
        
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            
            logger.info("Exported parsed PDF to %s", output_path)
        
        return parsed

    def get_document_structure(
        self,
        pdf_path: str,
    ) -> Dict[str, Any]:
        """
        Extract document structure (headings, sections) from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dict with hierarchical structure:
            - title: Document title
            - sections: List of section dicts with headings and subsections
            
        Example:
            >>> parser = DoclingParser()
            >>> structure = parser.get_document_structure("board_deck.pdf")
            >>> print(f"Title: {structure['title']}")
            >>> for section in structure['sections']:
            ...     print(f"Section: {section['heading']}")
        """
        parsed = self.parse_pdf(pdf_path)
        
        structure = {
            "title": parsed["metadata"].get("title", parsed["filename"]),
            "sections": [],
        }
        
        # Extract section hierarchy from pages
        for page in parsed["pages"]:
            for section in page.get("sections", []):
                section_data = {
                    "heading": section.get("heading", ""),
                    "page_no": page.get("page_no", 0),
                    "text_blocks": len(section.get("text_blocks", [])),
                    "tables": len(section.get("tables", [])),
                }
                structure["sections"].append(section_data)
        
        return structure
