# Yale Medicine Policy Crawler

This application crawls the Yale Department of Radiology web pages and documents to extract policy and guideline information.

## Features

- **Recursive Web Crawling**: Automatically crawls Yale Medicine web pages, following links randomly
- **Document Processing**: Downloads and converts PDF and Word documents to markdown
- **PDF OCR Processing**: Uses Mistral OCR to extract text and images from PDFs
- **Policy Detection**: Analyzes content using OpenAI's o3-mini model to identify radiology policies
- **Organized Output**: Saves content in a structured folder hierarchy with metadata

## Project Structure

```
yale-crawler/
├── main.py                # Main entry point
├── config.py              # Configuration settings
├── crawler.py             # Web crawler implementation
├── document_processor.py  # Document handling and conversion
├── pdf_processor.py       # PDF to markdown conversion
├── llm_processor.py       # LLM interaction for policy detection
├── llm_prompts.py         # Prompts for LLM interactions
└── requirements.txt       # Dependencies
```

## Setup

1. Clone the repository and navigate to the project directory
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   - Create a `.env` file in the project root
   - Add your API keys:
     ```
     OPENAI_API_KEY=your_openai_api_key
     MISTRAL_API_KEY=your_mistral_api_key
     ```

## Usage

Run the crawler with default settings:

```
python main.py
```

Or specify starting URL and maximum crawl depth:

```
python main.py --url https://medicine.yale.edu/diagnosticradiology/facintranet/policies --depth 3
```

The crawler will:

1. Open the starting URL in a browser
2. Wait for you to log in manually
3. Begin crawling the site, asking for confirmation before following each new link
4. Download and process documents (PDFs, Word files)
5. Save all content as markdown
6. Identify and extract policy-related content
7. Record findings in the data directory

## Output

All output is stored in the `yale_policies_data` directory:

- `markdown_files/`: Contains the markdown versions of all crawled content
  - `full_*.md`: Complete content from each page
  - `policy_*.md`: Extracted policy content (only for pages with relevant policies)
- `documents/`: Downloaded documents and their processed versions
- `crawler.log`: Log of the crawling process
- `policies_data.csv`: Summary of all found policies with their URLs and file paths

## Requirements

- Python 3.8+
- Chrome/Chromium browser for Selenium
- OpenAI API key for policy detection
- Mistral API key for PDF OCR processing
