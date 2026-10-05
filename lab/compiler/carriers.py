"""Requested prompt carriers for one accepted score (plan slice 3): YAML, XML and the hybrid envelope.

The build owner selects which controls are emitted; this module only serializes that one selection, so
YAML, XML and JSON carry the same payload and a hybrid's sections share it. Each reader inverts its writer
exactly; the readers exist so tests and package checks compare parsed meaning, not bytes.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from typing import Any

import yaml

SECTIONS = ("prose", "yaml", "json", "xml")
_TAGS = {"prose": "prose", "yaml": "yaml_projection", "json": "json_projection", "xml": "xml_projection"}
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9._-]*$")
_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def yaml_text(payload: dict) -> str:
    return yaml.safe_dump(payload, sort_keys=True, allow_unicode=True, default_flow_style=False, width=4096)


def _legal(text: str, where: str) -> str:
    found = _ILLEGAL.search(text)
    if found:
        raise ValueError(f"XML cannot carry control character U+{ord(found.group()):04X} in {where}")
    return text


def _element(key: str, value: Any) -> ET.Element:
    element = ET.Element(key) if _NAME.match(key) and not key.lower().startswith("xml") else ET.Element("entry", {"key": key})
    _fill(element, value, key)
    return element


def _fill(element: ET.Element, value: Any, where: str) -> None:
    """Typed, order-preserving and exactly reversible: lists and non-string scalars say their type."""
    if isinstance(value, dict):
        if not value:
            element.set("type", "map")
        for key in sorted(value):
            element.append(_element(key, value[key]))
    elif isinstance(value, list):
        element.set("type", "list")
        for item in value:
            child = ET.SubElement(element, "item")
            _fill(child, item, where)
    elif value is None:
        element.set("type", "null")
    elif isinstance(value, bool):
        element.set("type", "bool")
        element.text = "true" if value else "false"
    elif isinstance(value, int):
        element.set("type", "int")
        element.text = str(value)
    elif isinstance(value, float):
        element.set("type", "float")
        element.text = json.dumps(value)
    else:
        element.text = _legal(str(value), where)


def _tree(tag: str, payload: dict, attributes: dict[str, str]) -> ET.Element:
    root = ET.Element(tag, attributes)
    _fill(root, payload, tag)
    ET.indent(root, space="  ")
    return root


def xml_text(payload: dict) -> str:
    root = _tree("cpcs_prompt", payload, {"carrier": "xml", "score_id": payload["score_id"]})
    return ET.tostring(root, encoding="unicode") + "\n"


def _value(element: ET.Element) -> Any:
    kind = element.get("type")
    if kind == "list":
        return [_value(child) for child in element]
    if kind == "map":
        return {}
    if kind == "null":
        return None
    if kind == "bool":
        return element.text == "true"
    if kind == "int":
        return int(element.text)
    if kind == "float":
        return float(element.text)
    if len(element):
        return {(child.get("key") if child.tag == "entry" and child.get("key") is not None else child.tag): _value(child)
                for child in element}
    return element.text or ""


def read_xml(text: str) -> dict:
    """The payload an XML carrier (standalone, or a hybrid's xml section) holds."""
    root = ET.fromstring(text)
    return {(child.get("key") if child.tag == "entry" and child.get("key") is not None else child.tag): _value(child)
            for child in root}


def _cdata(text: str, where: str) -> str:
    return "<![CDATA[\n" + _legal(text, where).replace("]]>", "]]]]><![CDATA[>") + "]]>"


def hybrid_text(score_id: str, texts: dict[str, str], payload: dict) -> str:
    """The requested sections, in the requested order, under one score in the `<cpcs_prompt>` envelope."""
    lines = [f'<cpcs_prompt carrier="hybrid" score_id="{score_id}" sections="{" ".join(texts)}">',
             f"<authority>The canonical score {score_id} owns meaning. Each section projects it and adds no controls.</authority>"]
    for name, text in texts.items():
        if name == "xml":
            lines.append(ET.tostring(_tree(_TAGS["xml"], payload, {}), encoding="unicode"))
        else:
            lines.append(f"<{_TAGS[name]}>{_cdata(text, name + ' section')}</{_TAGS[name]}>")
    return "\n".join(lines + ["</cpcs_prompt>"]) + "\n"


def read_hybrid(text: str) -> dict[str, str]:
    """Section name -> section text, in printed order; the xml section is returned as its own XML text."""
    names = {tag: name for name, tag in _TAGS.items()}
    sections: dict[str, str] = {}
    for child in ET.fromstring(text):
        if child.tag not in names:
            continue
        name = names[child.tag]
        sections[name] = ET.tostring(child, encoding="unicode") if name == "xml" else (child.text or "").removeprefix("\n")
    return sections
