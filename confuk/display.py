from rich.console import Console
from rich.markdown import Markdown
from rich.tree import Tree
from confuk.parse import flatten
from collections import defaultdict


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


def get_markdown_tree(objs):

    def get_nested_dict():
        return defaultdict(get_nested_dict)

    def insert_doc(d, keys, value):
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                # Last key gets doc string
                d = d[key]  # ensure the node exists
                d["__doc__"] = value
            else:
                d = d[key]  # walk deeper

    # Build nested dict structure with __doc__ fields
    nested = get_nested_dict()
    for key, desc in objs.items():
        parts = key.split(".")
        insert_doc(nested, parts, desc)

    # Recursively format Markdown
    def format_markdown(d, level=0):
        md = ""
        indent = "    " * level
        for k, v in d.items():
            if isinstance(v, dict):
                doc = v.get("__doc__")
                md += f"{indent}- **{k}**"
                if doc:
                    md += f": {doc}"
                md += "\n"
                md += format_markdown({kk: vv for kk, vv in v.items() if kk != "__doc__"}, level + 1)
        return md

    return format_markdown(nested)


def display_markdown_tree(objs):
    """Displays configs/documentation as an indented Markdown tree from flattened keys"""
    console = Console()
    markdown_output = get_markdown_tree(objs)
    console.pager()
    console.print(Markdown(markdown_output))
