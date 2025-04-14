import webbrowser
import markdown as md_lib
from omegaconf import OmegaConf, DictConfig as OmegaConfigDict
from typing import *
from pathlib import Path
from confuk.parse import flatten, parse_config


def extract_docs(config_dict: OmegaConfigDict):
    """Extracts documentation comments from a config/docconfig object"""
    return flatten(config_dict, "", ("_doc_",), use_parent_key_for_filter=True)


def extract_docs_from_file(config_path: Path):
    cfg = parse_config(config_path, "o")
    return extract_docs(cfg)


def generate_html(docs, output_file, title="*"):
    """Generates an HTML file with collapsible sections"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title}</title>
    """ + """
        <style>
            body { font-family: Arial, sans-serif; }
            .section { margin-bottom: 10px; }
            .header { font-weight: bold; cursor: pointer; color: blue; }
            .content { display: none; padding-left: 10px; }
        </style>
        <script>
            function toggleVisibility(id) {
                var content = document.getElementById(id);
                content.style.display = (content.style.display === 'block') ? 'none' : 'block';
            }
        </script>
    </head>
    <body>
    """ + f"""
        <h1>{title}</h1>
    """
    for i, (key, desc) in enumerate(docs.items()):
        html_content += f'<div class="section">\n'
        html_content += f'  <div class="header" onclick="toggleVisibility(\'section{i}\')">{key}</div>\n'
        html_content += f'  <div id="section{i}" class="content">{desc}</div>\n'
        html_content += f'</div>'
    html_content += "</body></html>"
    
    Path(output_file).write_text(html_content)


def generate_html_from_markdown(md_text, output_file, title="Documentation"):
    """Converts Markdown string to HTML and saves to file"""
    html_body = md_lib.markdown(md_text)

    html_full = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: auto; padding: 20px; }}
        h1, h2, h3, h4 {{ color: #333; }}
        ul {{ padding-left: 1.2em; }}
        li {{ margin: 0.5em 0; }}
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
