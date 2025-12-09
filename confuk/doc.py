import webbrowser
import mistune
from omegaconf import OmegaConf, DictConfig as OmegaConfigDict
from typing import *
from pathlib import Path
from confuk.parse import flatten, parse_config
from confuk.display import get_markdown_tree


def extract_docs(config_dict: OmegaConfigDict):
    """Extracts documentation comments from a config/docconfig object"""
    return flatten(config_dict, "", ("_doc_",), use_parent_key_for_filter=True)


def extract_docs_from_file(config_path: Path):
    cfg = parse_config(config_path, "o")
    return extract_docs(cfg)


def generate_html(docs, output_file, title="Documentation"):
    """Generates an HTML file from documentation using Markdown as intermediate format"""
    # Convert docs to markdown tree
    md_text = get_markdown_tree(docs)
    
    # Convert markdown to HTML
    generate_html_from_markdown(md_text, output_file, title)


def generate_html_from_markdown(md_text, output_file, title="Documentation"):
    """Converts Markdown string to HTML and saves to file"""
    
    # mistune v3 (latest) has excellent nested structure handling
    html_body = mistune.html(md_text)

    html_full = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            max-width: 900px;
            margin: auto;
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 0.5em;
        }}
        h2, h3, h4 {{
            color: #34495e;
            margin-top: 1.5em;
        }}
        ul, ol {{
            padding-left: 1.5em;
        }}
        li {{
            margin: 0.5em 0;
        }}
        code {{
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 12px;
            overflow-x: auto;
            margin: 1em 0;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
        }}
        blockquote {{
            border-left: 4px solid #3498db;
            margin: 1em 0;
            padding-left: 1em;
            color: #555;
            font-style: italic;
        }}
        strong {{
            color: #2c3e50;
        }}
        /* Ensure nested lists maintain proper indentation */
        ul ul, ol ul, ul ol, ol ol {{
            margin-top: 0.5em;
            margin-bottom: 0.5em;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {html_body}
</body>
</html>"""

    Path(output_file).write_text(html_full)


def open_in_browser(output_file):
    """Opens the generated HTML file in the browser"""
    webbrowser.open(f"file://{Path(output_file).resolve()}")
