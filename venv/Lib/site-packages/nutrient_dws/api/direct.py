"""Direct API methods for supported document processing tools.

This file provides convenient methods that wrap the Nutrient Build API
for supported document processing operations.
"""

from typing import TYPE_CHECKING, Any, List, Optional, Protocol

from nutrient_dws.file_handler import FileInput

if TYPE_CHECKING:
    from nutrient_dws.builder import BuildAPIWrapper
    from nutrient_dws.http_client import HTTPClient


class HasBuildMethod(Protocol):
    """Protocol for objects that have a build method."""

    def build(self, input_file: FileInput) -> "BuildAPIWrapper":
        """Build method signature."""
        ...

    @property
    def _http_client(self) -> "HTTPClient":
        """HTTP client property."""
        ...


class DirectAPIMixin:
    """Mixin class containing Direct API methods.

    These methods provide a simplified interface to common document
    processing operations. They internally use the Build API.

    Note: The API automatically converts supported document formats
    (DOCX, XLSX, PPTX) to PDF when processing.
    """

    def _process_file(
        self,
        tool: str,
        input_file: FileInput,
        output_path: Optional[str] = None,
        **options: Any,
    ) -> Optional[bytes]:
        """Process file method that will be provided by NutrientClient."""
        raise NotImplementedError("This method is provided by NutrientClient")

    def convert_to_pdf(
        self,
        input_file: FileInput,
        output_path: Optional[str] = None,
    ) -> Optional[bytes]:
        """Convert a document to PDF.

        Converts Office documents (DOCX, XLSX, PPTX) to PDF format.
        This uses the API's implicit conversion - simply uploading a
        non-PDF document returns it as a PDF.

        Args:
            input_file: Input document (DOCX, XLSX, PPTX, etc).
            output_path: Optional path to save the output PDF.

        Returns:
            Converted PDF as bytes, or None if output_path is provided.

        Raises:
            AuthenticationError: If API key is missing or invalid.
            APIError: For other API errors (e.g., unsupported format).

        Note:
            HTML files are not currently supported by the API.
        """
        # Use builder with no actions - implicit conversion happens
        # Type checking: at runtime, self is NutrientClient which has these methods
        return self.build(input_file).execute(output_path)  # type: ignore[attr-defined,no-any-return]

    def flatten_annotations(
        self, input_file: FileInput, output_path: Optional[str] = None
    ) -> Optional[bytes]:
        """Flatten annotations and form fields in a PDF.

        Converts all annotations and form fields into static page content.
        If input is an Office document, it will be converted to PDF first.

        Args:
            input_file: Input file (PDF or Office document).
            output_path: Optional path to save the output file.

        Returns:
            Processed file as bytes, or None if output_path is provided.

        Raises:
            AuthenticationError: If API key is missing or invalid.
            APIError: For other API errors.
        """
        return self._process_file("flatten-annotations", input_file, output_path)

    def rotate_pages(
        self,
        input_file: FileInput,
        output_path: Optional[str] = None,
        degrees: int = 0,
        page_indexes: Optional[List[int]] = None,
    ) -> Optional[bytes]:
        """Rotate pages in a PDF.

        Rotate all pages or specific pages by the specified degrees.
        If input is an Office document, it will be converted to PDF first.

        Args:
            input_file: Input file (PDF or Office document).
            output_path: Optional path to save the output file.
            degrees: Rotation angle (90, 180, 270, or -90).
            page_indexes: Optional list of page indexes to rotate (0-based).

        Returns:
            Processed file as bytes, or None if output_path is provided.

        Raises:
            AuthenticationError: If API key is missing or invalid.
            APIError: For other API errors.
        """
        options = {"degrees": degrees}
        if page_indexes is not None:
            options["page_indexes"] = page_indexes  # type: ignore
        return self._process_file("rotate-pages", input_file, output_path, **options)

    def ocr_pdf(
        self,
        input_file: FileInput,
        output_path: Optional[str] = None,
        language: str = "english",
    ) -> Optional[bytes]:
        """Apply OCR to a PDF to make it searchable.

        Performs optical character recognition on the PDF to extract text
        and make it searchable. If input is an Office document, it will
        be converted to PDF first.

        Args:
            input_file: Input file (PDF or Office document).
            output_path: Optional path to save the output file.
            language: OCR language. Supported: "english", "eng", "deu", "german".
                     Default is "english".

        Returns:
            Processed file as bytes, or None if output_path is provided.

        Raises:
            AuthenticationError: If API key is missing or invalid.
            APIError: For other API errors.
        """
        return self._process_file("ocr-pdf", input_file, output_path, language=language)

    def watermark_pdf(
        self,
        input_file: FileInput,
        output_path: Optional[str] = None,
        text: Optional[str] = None,
        image_url: Optional[str] = None,
        width: int = 200,
        height: int = 100,
        opacity: float = 1.0,
        position: str = "center",
    ) -> Optional[bytes]:
        """Add a watermark to a PDF.

        Adds a text or image watermark to all pages of the PDF.
        If input is an Office document, it will be converted to PDF first.

        Args:
            input_file: Input file (PDF or Office document).
            output_path: Optional path to save the output file.
            text: Text to use as watermark. Either text or image_url required.
            image_url: URL of image to use as watermark.
            width: Width of the watermark in points (required).
            height: Height of the watermark in points (required).
            opacity: Opacity of the watermark (0.0 to 1.0).
            position: Position of watermark. One of: "top-left", "top-center",
                     "top-right", "center", "bottom-left", "bottom-center",
                     "bottom-right".

        Returns:
            Processed file as bytes, or None if output_path is provided.

        Raises:
            AuthenticationError: If API key is missing or invalid.
            APIError: For other API errors.
            ValueError: If neither text nor image_url is provided.
        """
        if not text and not image_url:
            raise ValueError("Either text or image_url must be provided")

        options = {
            "width": width,
            "height": height,
            "opacity": opacity,
            "position": position,
        }

        if text:
            options["text"] = text
        else:
            options["image_url"] = image_url

        return self._process_file("watermark-pdf", input_file, output_path, **options)

    def apply_redactions(
        self,
        input_file: FileInput,
        output_path: Optional[str] = None,
    ) -> Optional[bytes]:
        """Apply redaction annotations to permanently remove content.

        Applies any redaction annotations in the PDF to permanently remove
        the underlying content. If input is an Office document, it will
        be converted to PDF first.

        Args:
            input_file: Input file (PDF or Office document).
            output_path: Optional path to save the output file.

        Returns:
            Processed file as bytes, or None if output_path is provided.

        Raises:
            AuthenticationError: If API key is missing or invalid.
            APIError: For other API errors.
        """
        return self._process_file("apply-redactions", input_file, output_path)

    def merge_pdfs(
        self,
        input_files: List[FileInput],
        output_path: Optional[str] = None,
    ) -> Optional[bytes]:
        """Merge multiple PDF files into one.

        Combines multiple files into a single PDF in the order provided.
        Office documents (DOCX, XLSX, PPTX) will be automatically converted
        to PDF before merging.

        Args:
            input_files: List of input files (PDFs or Office documents).
            output_path: Optional path to save the output file.

        Returns:
            Merged PDF as bytes, or None if output_path is provided.

        Raises:
            AuthenticationError: If API key is missing or invalid.
            APIError: For other API errors.
            ValueError: If less than 2 files provided.

        Example:
            # Merge PDFs and Office documents
            client.merge_pdfs([
                "document1.pdf",
                "document2.docx",
                "spreadsheet.xlsx"
            ], "merged.pdf")
        """
        if len(input_files) < 2:
            raise ValueError("At least 2 files required for merge")

        from nutrient_dws.file_handler import prepare_file_for_upload, save_file_output

        # Prepare files for upload
        files = {}
        parts = []

        for i, file in enumerate(input_files):
            field_name = f"file{i}"
            file_field, file_data = prepare_file_for_upload(file, field_name)
            files[file_field] = file_data
            parts.append({"file": field_name})

        # Build instructions for merge (no actions needed)
        instructions = {"parts": parts, "actions": []}

        # Make API request
        # Type checking: at runtime, self is NutrientClient which has _http_client
        result = self._http_client.post(  # type: ignore[attr-defined]
            "/build",
            files=files,
            json_data=instructions,
        )

        # Handle output
        if output_path:
            save_file_output(result, output_path)
            return None
        else:
            return result  # type: ignore[no-any-return]
