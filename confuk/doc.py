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
    """Converts Markdown string to HTML and saves to file with GFM and Mermaid support"""
    import mistune
    import re
    
    # Custom renderer to handle Mermaid code blocks
    class MermaidRenderer(mistune.HTMLRenderer):
        def block_code(self, code, info=None):
            """Override block_code to handle mermaid blocks specially"""
            if info and info.strip().lower() == 'mermaid':
                # Render as a div with mermaid class for rendering
                return f'<div class="mermaid">\n{code}\n</div>\n'
            else:
                # Regular code block
                if info:
                    return f'<pre><code class="language-{mistune.escape(info)}">{mistune.escape(code)}</code></pre>\n'
                return f'<pre><code>{mistune.escape(code)}</code></pre>\n'
    
    def plugin_gfm_alerts(md):
        """
        GitHub-style callouts:
        
        > [!NOTE]
        > message

        Produces <div class="alert alert-note">...</div>
        """
        import re

        # Matches patterns like:
        #
        # > [!NOTE]
        # > Some text
        # > More text
        #
        ALERT_PATTERN = re.compile(
            r"""
            ^>[\ \t]*\[(?:!)(?P<type>NOTE|TIP|IMPORTANT|WARNING|CAUTION)\][ \t]*\n
            (?P<content>(?:>.*\n?)+)
            """,
            re.IGNORECASE | re.MULTILINE | re.VERBOSE,
        )

        def parse_alert(self, m, state):
            alert_type = m.group("type").upper()
            content = m.group("content")

            # Strip leading "> " markers from content lines
            stripped = re.sub(r"^>\s?", "", content, flags=re.MULTILINE).strip()

            # Parse child tokens using a fresh local state
            child_state = state.copy()
            child_state.process(stripped)
            children = child_state.tokens

            return {
                "type": "gfm_alert",
                "alert_type": alert_type,
                "children": children,
            }

        def render_gfm_alert(self, token):
            alert_type = token["alert_type"]
            children = self.render_children(token)

            alert_config = {
                "NOTE": {"icon": "ℹ️", "class": "alert-note"},
                "TIP": {"icon": "💡", "class": "alert-tip"},
                "IMPORTANT": {"icon": "❗", "class": "alert-important"},
                "WARNING": {"icon": "⚠️", "class": "alert-warning"},
                "CAUTION": {"icon": "🚨", "class": "alert-caution"},
            }
            cfg = alert_config.get(alert_type, alert_config["NOTE"])

            return (
                f'<div class="alert {cfg["class"]}">\n'
                f'  <div class="alert-title">{cfg["icon"]} {alert_type.capitalize()}</div>\n'
                f'  <div class="alert-content">{children}</div>\n'
                f'</div>\n'
            )

        # Register block rule BEFORE block_quote so it is evaluated first
        md.block.register(
            "gfm_alert",
            ALERT_PATTERN,
            parse_alert,
            before="block_quote",
        )

        # Register renderer when appropriate
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("gfm_alert", render_gfm_alert)

    
    # Create markdown renderer with custom renderer and GFM plugins
    markdown = mistune.create_markdown(
        renderer=MermaidRenderer(),
        plugins=[
            "strikethrough",
            "table",
            "url",
            "task_lists",
            plugin_gfm_alerts,     # GFM-style alerts
        ]
    )
    
    html_body = markdown(md_text)

    html_full = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
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
        /* Table styling for GFM tables */
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f8f8f8;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        /* Task list styling */
        input[type="checkbox"] {{
            margin-right: 0.5em;
        }}
        /* Mermaid diagram container */
        .mermaid {{
            text-align: center;
            margin: 1.5em 0;
            background-color: #fff;
            padding: 1em;
            border-radius: 4px;
        }}
        /* GFM Alert/Callout styling */
        .alert {{
            padding: 1em;
            margin: 1em 0;
            border-radius: 6px;
            border-left: 4px solid;
        }}
        .alert-title {{
            font-weight: bold;
            margin-bottom: 0.5em;
            font-size: 1.05em;
        }}
        .alert-content {{
            margin-left: 0.5em;
        }}
        .alert-content > *:first-child {{
            margin-top: 0;
        }}
        .alert-content > *:last-child {{
            margin-bottom: 0;
        }}
        .alert-note {{
            background-color: #e6f3ff;
            border-left-color: #0969da;
            color: #0a3069;
        }}
        .alert-tip {{
            background-color: #e6ffe6;
            border-left-color: #1a7f37;
            color: #0f5323;
        }}
        .alert-important {{
            background-color: #f5e6ff;
            border-left-color: #8250df;
            color: #4a1e7a;
        }}
        .alert-warning {{
            background-color: #fff8e6;
            border-left-color: #bf8700;
            color: #6f4e00;
        }}
        .alert-caution {{
            background-color: #ffe6e6;
            border-left-color: #d1242f;
            color: #86181d;
        }}
    </style>
    <!-- Mermaid.js for diagram rendering -->
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ 
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        }});
    </script>
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
