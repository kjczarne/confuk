from rich.console import Console
from rich.markdown import Markdown
from rich.tree import Tree
from confuk.parse import flatten


def display_flat(objs):
    """Displays configs or documentation as a flat list using Markdown"""
    console = Console()
    output = "\n".join([f"**{key}**\n{desc}\n" for key, desc in objs.items()])
    console.pager()  # Enable paging
    console.print(Markdown(output))


def display_tree(objs, tree_name: str = "*"):
    """Displays configs or documentation as a tree structure"""
    console = Console()
    tree = Tree(f"[bold]{tree_name}[/bold]")
    
    nodes = {}
    for key, doc in sorted(objs.items()):
        parts = key.split('.')
        current = tree
        path = ""
        for i, part in enumerate(parts):
            path = f"{path}.{part}" if path else part
            if path not in nodes:
                new_node = current.add(f"[bold]{part}[/bold]" if i < len(parts) - 1 else f"[bold]{part}[/bold]: {doc}")
                nodes[path] = new_node
            current = nodes[path]
    console.pager()
    console.print(tree)


def display_in_console(objs, tree_view=False, unpack: bool = False, md: bool = False):
    """Renders configs/documentation to the console with optional tree view"""
    if tree_view:
        if unpack:
            # `display_tree` accepts a flat list and then reconstructs
            # a tree so we pass a flattened one here. It's a bit dumb
            # and inefficient but I have no time to fix this now
            objs_ = flatten(objs)
        else:
            objs_ = objs
        display_tree(objs_)
    else:
        if md:
            display_markdown_tree(objs)
        else:
            display_flat(objs)


def display_markdown_tree(objs):
    """Displays configs/documentation as an indented Markdown trees"""
    def get_nested_dict():
        from collections import defaultdict
        return defaultdict(get_nested_dict)

    def insert_nested(d, keys, value):
        for key in keys[:-1]:
            if not isinstance(d.get(key), dict):
                d[key] = get_nested_dict()
            d = d[key]
        d[keys[-1]] = value

    # Build nested dict structure
    nested = get_nested_dict()
    for key, desc in objs.items():
        parts = key.split('.')
        insert_nested(nested, parts, desc)

    # Recursively format Markdown
    def format_markdown(d, level=0):
        md = ""
        indent = "    " * level
        for k, v in d.items():
            if isinstance(v, dict):
                md += f"{indent}- **{k}**\n"
                md += format_markdown(v, level + 1)
            else:
                md += f"{indent}- **{k}**: {v}\n"
        return md

    console = Console()
    markdown_output = format_markdown(nested)
    console.pager()
    console.print(Markdown(markdown_output))
