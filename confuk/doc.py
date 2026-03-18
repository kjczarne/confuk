import webbrowser
import mistune
from omegaconf import OmegaConf, DictConfig as OmegaConfigDict
from typing import *
from pathlib import Path
from confuk.parse import flatten, parse_config
from confuk.display import get_markdown_tree
import re

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
    """
    Converts Markdown string to HTML and saves to file with:
      - GFM-style callouts (> [!NOTE])
      - Mermaid code block handling
      - A structural TOC collected during block parsing (Option A: TOC before body)
    """
    # -----------------------------
    # Custom renderer
    # -----------------------------
    class MermaidRenderer(mistune.HTMLRenderer):
        def __init__(self):
            super().__init__()
            # The renderer does not collect TOC in this implementation;
            # plugin_toc_tree (below) will attach toc to the Markdown instance.
            # Keep renderer light and focused on HTML rendering.
            self.list_depth = 0

        def block_code(self, code, info=None):
            """Handle mermaid code blocks specially"""
            if info and info.strip().lower() == 'mermaid':
                return f'<div class="mermaid">\n{mistune.escape(code)}\n</div>\n'
            else:
                if info:
                    return f'<pre><code class="language-{mistune.escape(info)}">{mistune.escape(code)}</code></pre>\n'
                return f'<pre><code>{mistune.escape(code)}</code></pre>\n'

        # Keep list rendering standard; the plugin will collect structural TOC.
        def list(self, text, ordered, **attrs):
            if ordered:
                return f'<ol>\n{text}</ol>\n'
            else:
                return f'<ul>\n{text}</ul>\n'

        def list_item(self, text):
            return f'<li>{text}</li>\n'

    # -----------------------------
    # Plugin: GFM-style callouts
    # -----------------------------
    def plugin_gfm_alerts(md):
        """
        Detects GitHub-style callouts:
          > [!NOTE]
          > note text...
        and produces a 'gfm_alert' token with children parsed locally.
        """
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
            # Remove leading ">" characters from each content line
            stripped = re.sub(r"^>\s?", "", content, flags=re.MULTILINE).strip()

            # Parse child tokens using a fresh local state to avoid polluting global state
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

        # Register block rule BEFORE block_quote so it is tested first
        md.block.register("gfm_alert", ALERT_PATTERN, parse_alert, before="block_quote")

        # Register renderer hook if HTML renderer is present
        if md.renderer and getattr(md.renderer, "NAME", "") == "html":
            md.renderer.register("gfm_alert", render_gfm_alert)

    def plugin_toc_tree(md):
        """
        Collect hierarchical TOC items during rendering.
        Tracks nesting by intercepting both list and list_item rendering.
        """
        if not hasattr(md, 'renderer') or not md.renderer:
            return
        
        md.toc_items = []
        
        # Store original methods
        original_list = md.renderer.list
        original_list_item = md.renderer.list_item
        
        # Use a stack to track depth more accurately
        depth_stack = [0]  # Start at depth 0
        
        def list_with_depth(text, ordered, **attrs):
            """Track entering/exiting lists"""
            # When we enter a list, we're going one level deeper
            current_depth = depth_stack[-1] + 1
            depth_stack.append(current_depth)
            
            result = original_list(text, ordered, **attrs)
            
            # Exit this list level
            depth_stack.pop()
            return result
        
        def list_item_with_toc(text):
            """Collect TOC entries from list items with strong emphasis"""
            # Look for strong tags in the text
            strong_match = re.search(r'<strong>([^<]+)</strong>', text)
            if strong_match:
                key_name = strong_match.group(1).strip()
                item_id = re.sub(r'[^a-zA-Z0-9_.-]', '-', key_name).strip('-').lower()
                # Current depth is the last item in the stack minus 1 (0-indexed)
                level = max(0, depth_stack[-1] - 1)
                
                md.toc_items.append({
                    "id": item_id,
                    "name": key_name,
                    "level": level
                })
                
                # Add id attribute to the list item
                return f'<li id="{item_id}">{text}</li>\n'
            
            return original_list_item(text)
        
        # Replace renderer methods
        md.renderer.list = list_with_depth
        md.renderer.list_item = list_item_with_toc

    # -----------------------------
    # Markdown creation with plugins
    # -----------------------------
    renderer = MermaidRenderer()

    markdown = mistune.create_markdown(
        renderer=renderer,
        plugins=[
            "strikethrough",
            "table",
            "url",
            "task_lists",
            plugin_gfm_alerts,
            plugin_toc_tree,
        ],
    )

    # -----------------------------
    # Render markdown to HTML body
    # -----------------------------
    html_body = markdown(md_text)

    # -----------------------------
    # Build nested TOC HTML from markdown.toc_items (collected by plugin_toc_tree)
    # -----------------------------
    def build_nested_toc(items):
        """
        Build a nested <ul> TOC from a list of items with 'level' (0-based).
        Creates properly nested lists based on hierarchical levels.
        """
        if not items:
            return ""

        out = []
        out.append('<div class="toc">\n<h2>Table of Contents</h2>\n')
        
        # Start with the first level
        out.append('<ul>\n')
        stack_depth = 0
        
        for it in items:
            lvl = int(it.get("level", 0))
            name = it.get("name", "")
            item_id = it.get("id", "")

            # Open deeper levels
            while stack_depth < lvl:
                out.append('<ul>\n')
                stack_depth += 1

            # Close levels
            while stack_depth > lvl:
                out.append('</ul>\n</li>\n')
                stack_depth -= 1

            # Add the list item
            out.append(f'<li><a href="#{item_id}">{mistune.escape(name)}</a>')
            
            # Check if next item is deeper (will need to open a nested list)
            # If so, don't close this <li> yet
            # Otherwise, close it now
            next_idx = items.index(it) + 1
            if next_idx < len(items):
                next_lvl = int(items[next_idx].get("level", 0))
                if next_lvl <= lvl:
                    out.append('</li>\n')
            else:
                out.append('</li>\n')

        # Close remaining open lists
        while stack_depth > 0:
            out.append('</ul>\n</li>\n')
            stack_depth -= 1
        
        out.append('</ul>\n')  # Close the initial <ul>
        out.append('</div>\n')
        return "".join(out)

    toc_items = getattr(markdown, "toc_items", []) or []
    toc_html = build_nested_toc(toc_items)

    # -----------------------------
    # Final HTML assembly
    # -----------------------------
    html_full = f"""<!DOCTYPE html>
<html>
<head>
    <title>{mistune.escape(title)}</title>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            max-width: 1200px;
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
        /* Table of Contents styling */
        .toc {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 1.5em;
            margin: 2em 0;
            position: sticky;
            top: 20px;
            max-height: 80vh;
            overflow-y: auto;
        }}
        .toc h2 {{
            margin-top: 0;
            margin-bottom: 1em;
            font-size: 1.3em;
            color: #2c3e50;
        }}
        .toc > ul {{
            list-style: none;
            padding-left: 0;
            margin: 0;
        }}
        .toc ul {{
            list-style: none;
            padding-left: 0;
            margin: 0.25em 0;
        }}
        .toc ul ul {{
            padding-left: 1.5em;
            margin-top: 0.25em;
        }}
        .toc li {{
            margin: 0.4em 0;
        }}
        .toc a {{
            color: #0969da;
            text-decoration: none;
            display: block;
            padding: 0.2em 0;
        }}
        .toc a:hover {{
            color: #0550ae;
            text-decoration: underline;
        }}
        /* Content area */
        .content {{
            margin-top: 2em;
        }}
        :target {{
            animation: highlight 2s ease;
            scroll-margin-top: 20px;
        }}
        @keyframes highlight {{
            0% {{ background-color: #fff3cd; }}
            100% {{ background-color: transparent; }}
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
        /* Responsive */
        @media (max-width: 768px) {{
            .toc {{
                position: static;
                max-height: none;
            }}
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
    <h1>{mistune.escape(title)}</h1>
    {toc_html}
    <div class="content">
        {html_body}
    </div>
</body>
</html>"""

    Path(output_file).write_text(html_full)


def open_in_browser(output_file):
    """Opens the generated HTML file in the browser"""
    webbrowser.open(f"file://{Path(output_file).resolve()}")
