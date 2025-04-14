import click
from rich.console import Console
from confuk.parse import parse_config
from confuk.display import display_in_console, get_markdown_tree
from confuk.doc import extract_docs_from_file, generate_html, open_in_browser, generate_html_from_markdown
from pathlib import Path


@click.group()
def main():
    pass


@main.command()
@click.argument('config_file', type=click.Path(exists=True, path_type=Path))
@click.option('-t', '--tree', is_flag=True, help="Print in a tree format")
def parse(config_file: Path, tree: bool):
    console = Console()
    console.print(f"[blue]{config_file}[/blue]")
    cfg = parse_config(config_file)
    display_in_console(cfg, tree, unpack=True, md=True)


@main.command()
@click.argument('doc_file', type=click.Path(exists=True, path_type=Path))
@click.option('-t', '--tree', is_flag=True, help="Print in a tree format")
@click.option('-f', '--file', type=click.Path(path_type=Path),
              default=None, help="If set, this should be a path to an output HTML file")
@click.option('-o', '--open-html', is_flag=True,
              help="Whether to open the HTML file in the web browser")
@click.option('-l', '--flatten-html', is_flag=True,
              help="Whether the HTML output should be presented as a flat dotlist")
def doc(doc_file: Path, tree: bool, file: Path | None, open_html: bool, flatten_html: bool):
    console = Console()
    console.print(f"[blue]{doc_file}[/blue]")
    docs = extract_docs_from_file(doc_file)
    display_in_console(docs, tree, md=True)
    if file is not None:
        if not flatten_html:
            md_tree = get_markdown_tree(docs)
            generate_html_from_markdown(md_tree, file, title=doc_file.stem)
        else:
            generate_html(docs, file, title=doc_file.stem)
        if open_html:
            open_in_browser(file)


if __name__ == "__main__":
    main()
