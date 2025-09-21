# 📄 Simple PDF Download Fix

## Problem
Current PDF downloads return 0 files despite finding URLs correctly.

## Root Cause
The PDF download logic is overcomplicated and doesn't use the authenticated browser session properly.

## Solution
Replace the complex PDF manager with a simple, direct approach:

```python
async def download_pdf_simple(self, url: str, filename: str) -> Optional[Path]:
    """Simple PDF download using authenticated browser session"""
    try:
        # Create download directory
        pdf_dir = self.output_dir / "pdfs"
        pdf_dir.mkdir(exist_ok=True)
        pdf_path = pdf_dir / filename

        # Use the authenticated page to download
        response = await self.page.goto(url, wait_until="networkidle")

        if response.status == 200:
            # Get the content
            content = await response.body()

            # Verify it's a PDF
            if content[:4] == b'%PDF':
                # Save to file
                with open(pdf_path, 'wb') as f:
                    f.write(content)

                # Verify size
                if pdf_path.stat().st_size > 1000:  # At least 1KB
                    logger.info(f"✅ Downloaded: {filename} ({len(content)} bytes)")
                    return pdf_path
                else:
                    logger.warning(f"PDF too small: {filename}")
                    pdf_path.unlink()
            else:
                logger.warning(f"Not a PDF: {url}")
        else:
            logger.error(f"HTTP {response.status}: {url}")

    except Exception as e:
        logger.error(f"Download failed: {e}")

    return None
```

## Implementation
1. Replace the complex `EnhancedPDFManager` with this simple method
2. Call it directly from the manuscript parsing
3. Use the authenticated browser session (no separate downloads)

## Expected Results
- All PDF URLs should download successfully
- Files saved to `output/pdfs/` directory
- Proper error handling for failed downloads

This approach is simpler, more reliable, and uses the existing authentication context.
