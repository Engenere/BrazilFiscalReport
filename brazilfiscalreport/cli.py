from importlib import import_module
from pathlib import Path

import click
import yaml

from brazilfiscalreport import __version__


def load_config():
    try:
        config_path = Path("config.yaml").resolve()
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
        return config_data
    except FileNotFoundError:
        click.echo("Config file 'config.yaml' not found. Using default configuration.")
        return {}


def get_default_issuer():
    return {
        "nome": "EMPRESA LTDA",
        "end": "AV. TEST, 100",
        "bairro": "TEST",
        "cep": "88888-88",
        "cidade": "SÃO PAULO",
        "uf": "SP",
        "fone": "(11) 1234-5678",
    }


def _load_module(module_name):
    try:
        return import_module(f"brazilfiscalreport.{module_name}")
    except ImportError:
        click.echo(
            f"Error: The brazilfiscalreport package "
            f"or its {module_name} module is not installed."
        )
        return None


def _resolve_output_path(xml_path):
    return (Path.cwd() / xml_path.stem).with_suffix(".pdf")


def _read_xml(xml_path):
    with open(xml_path, encoding="utf-8") as xml_file:
        return xml_file.read()


def _resolve_logo(config_data):
    logo = config_data.get("LOGO")
    if not logo:
        return None
    logo_path = Path(logo).resolve()
    if not logo_path.exists():
        click.echo("Logo file not found, proceeding without logo.")
        return None
    return logo_path


def _build_margins(config_data, margins_cls):
    return margins_cls(
        top=config_data.get("TOP_MARGIN", margins_cls.top),
        right=config_data.get("RIGHT_MARGIN", margins_cls.right),
        bottom=config_data.get("BOTTOM_MARGIN", margins_cls.bottom),
        left=config_data.get("LEFT_MARGIN", margins_cls.left),
    )


def _generate_document(module_name, doc_label, xml, build_instance):
    """
    Shared driver for the `bfrep` subcommands: resolves the module, reads
    the XML/config, delegates instance creation to `build_instance`
    (signature differs per document type) and writes the output PDF.
    """
    module = _load_module(module_name)
    if module is None:
        return

    config_data = load_config()
    xml_path = Path(xml).resolve()
    xml_content = _read_xml(xml_path)

    instance = build_instance(module, config_data, xml_content)
    output_path = _resolve_output_path(xml_path)
    instance.output(output_path)
    click.echo(f"{doc_label} generated successfully: {output_path}")


def _build_dacce(module, config_data, xml_content):
    issuer = config_data.get("ISSUER", get_default_issuer())
    return module.DaCCe(xml=xml_content, emitente=issuer)


def _build_danfe(module, config_data, xml_content):
    config = module.DanfeConfig(
        margins=_build_margins(config_data, module.Margins),
        logo=_resolve_logo(config_data),
    )
    return module.Danfe(xml=xml_content, config=config)


def _build_dacte(module, config_data, xml_content):
    config = module.DacteConfig(
        margins=_build_margins(config_data, module.Margins),
        logo=_resolve_logo(config_data),
    )
    return module.Dacte(xml=xml_content, config=config)


def _build_damdfe(module, config_data, xml_content):
    config = module.DamdfeConfig(
        margins=_build_margins(config_data, module.Margins),
        logo=_resolve_logo(config_data),
    )
    return module.Damdfe(xml=xml_content, config=config)


def _build_danfse(module, config_data, xml_content):
    # DanfseConfig has no `logo` field: DANFSe always uses the embedded
    # NFS-e brasão, so no logo resolution here.
    config = module.DanfseConfig(margins=_build_margins(config_data, module.Margins))
    return module.Danfse(xml=xml_content, config=config)


@click.group()
@click.version_option(
    __version__, "-v", "--version", message="bfrep version %(version)s"
)
def cli():
    pass


@cli.command("dacce")
@click.argument("xml", type=click.Path(exists=True))
def generate_dacce(xml):
    _generate_document("dacce", "DACCe", xml, _build_dacce)


@cli.command("danfe")
@click.argument("xml", type=click.Path(exists=True))
def generate_danfe(xml):
    _generate_document("danfe", "DANFE", xml, _build_danfe)


@cli.command("dacte")
@click.argument("xml", type=click.Path(exists=True))
def generate_dacte(xml):
    _generate_document("dacte", "DACTE", xml, _build_dacte)


@cli.command("damdfe")
@click.argument("xml", type=click.Path(exists=True))
def generate_damdfe(xml):
    _generate_document("damdfe", "DAMDFE", xml, _build_damdfe)


@cli.command("danfse")
@click.argument("xml", type=click.Path(exists=True))
def generate_danfse(xml):
    _generate_document("danfse", "DANFSE", xml, _build_danfse)


if __name__ == "__main__":
    cli()
