"""persist.filelib – utilidades para gravar sem sobrescrever.

Exporta funções genéricas que aceitam:
    * texto puro
    * linhas CSV
    * trechos XML
    * páginas PDF
Todas escrevem *em append*.
"""

from __future__ import annotations
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, List, Union

# ----------------------------------------------------------------------
# Texto puro / JSON / CSV (texto)
# ----------------------------------------------------------------------
def append_text(filepath: Union[str, Path], data: str) -> None:
    """Acrescenta `data` ao final do arquivo (cria se não existir)."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)   # garante diretório
    with path.open("a", encoding="utf-8") as f:
        f.write(data + "\n")        # garante nova linha


def append_csv(
    file_path: Union[str, Path],
    row: Iterable,
    *,
    header: bool = False,
    newline: str = "",
) -> None:
    """Adiciona uma linha ao CSV (cria o cabeçalho se solicitado)."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Detecta se o arquivo já tem extensão .csv ou se será criado agora
    write_header = not path.is_file() or header

    with path.open("a", newline=newline, encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(row)          # primeira linha = header
        else:
            writer.writerow(row)          # apenas adiciona a nova linha


# ----------------------------------------------------------------------
# XML
# ----------------------------------------------------------------------
def append_xml(
    xml_path: Union[str, Path],
    parent_tag: str,
    new_xml_fragment: str,
) -> None:
    """
    Anexa <new_xml_fragment/> como filho do elemento <parent_tag/>.
    Não altera o conteúdo já existente.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    parent = root.find(parent_tag)
    if parent is None:
        raise ValueError(f"<{parent_tag}> não encontrado no XML.")
    child = ET.fromstring(new_xml_fragment)
    parent.append(child)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)


# ----------------------------------------------------------------------
# PDF (requer PyPDF2)
# ----------------------------------------------------------------------
def merge_pdf_pages(
    src_pdf: Union[str, Path],
    page_pdf: Union[str, Path],
    dest_pdf: Union[str, Path],
) -> None:
    """
    Junta as páginas de `page_pdf` ao final de `src_pdf` → `dest_pdf`.
    Mantém o arquivo original intacto.
    """
    from PyPDF2 import PdfReader, PdfWriter

    src = PdfReader(src_pdf)
    add = PdfReader(page_pdf)
    writer = PdfWriter()

    for page in src.pages:
        writer.add_page(page)
    for page in add.pages:
        writer.add_page(page)

    with open(dest_pdf, "wb") as out_f:
        writer.write(out_f)