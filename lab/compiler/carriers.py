"""Requested prompt carriers for one accepted score (plan slice 3): YAML, XML and the hybrid envelope.

The build owner selects which controls are emitted; this module only serializes that one selection, so
YAML, XML and JSON carry the same payload and a hybrid's sections share it. Each reader inverts its writer
exactly; the readers exist so tests and package checks compare parsed meaning, not bytes. XML is written
by an escaping writer and read only through defusedxml (release security policy).
"""
from __future__ import annotations

import json
import re
from typing import Any
from xml.sax.saxutils import escape, quoteattr

import yaml
from defusedxml import ElementTree as DefusedElementTree

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


def _node(tag: str, attributes: str, value: Any, depth: int, where: str) -> list[str]:
    """Typed, order-preserving and exactly reversible: lists and non-string scalars say their type."""
    pad = "  " * depth
    if isinstance(value, dict):
        if not value:
            return [f'{pad}<{tag}{attributes} type="map" />']
        lines = [f"{pad}<{tag}{attributes}>"]
        for key in sorted(value):
            lines += _keyed(key, value[key], depth + 1)
        return lines + [f"{pad}</{tag}>"]
    if isinstance(value, list):
        if not value:
            return [f'{pad}<{tag}{attributes} type="list" />']
        lines = [f'{pad}<{tag}{attributes} type="list">']
        for item in value:
            lines += _node("item", "", item, depth + 1, where)
        return lines + [f"{pad}</{tag}>"]
    if value is None:
        return [f'{pad}<{tag}{attributes} type="null" />']
    if isinstance(value, bool):
        kind, text = "bool", "true" if value else "false"
    elif isinstance(value, int):
        kind, text = "int", str(value)
    elif isinstance(value, float):
        kind, text = "float", json.dumps(value)
    else:
        kind, text = None, escape(_legal(str(value), where), {"\r": "&#13;"})
    typed = f' type="{kind}"' if kind else ""
    return [f"{pad}<{tag}{attributes}{typed}>{text}</{tag}>"]


def _keyed(key: str, value: Any, depth: int) -> list[str]:
    if _NAME.match(key) and not key.lower().startswith("xml"):
        return _node(key, "", value, depth, key)
    return _node("entry", " key=" + quoteattr(_legal(key, "a key")), value, depth, key)


def _document(tag: str, attributes: str, payload: dict) -> str:
    lines = [f"<{tag}{attributes}>"]
    for key in sorted(payload):
        lines += _keyed(key, payload[key], 1)
    return "\n".join(lines + [f"</{tag}>"])


def xml_text(payload: dict) -> str:
    return _document("cpcs_prompt", f' carrier="xml" score_id={quoteattr(payload["score_id"])}', payload) + "\n"


def _value(element: Any) -> Any:
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
        return _children(element)
    return element.text or ""


def _children(element: Any) -> dict:
    return {(child.get("key") if child.tag == "entry" and child.get("key") is not None else child.tag): _value(child)
            for child in element}


def read_xml(text: str) -> dict:
    """The payload an XML carrier (standalone, or a hybrid's xml section) holds."""
    return _children(DefusedElementTree.fromstring(text))


def _cdata(text: str, where: str) -> str:
    return "<![CDATA[\n" + _legal(text, where).replace("]]>", "]]]]><![CDATA[>") + "]]>"


def hybrid_text(score_id: str, texts: dict[str, str], payload: dict) -> str:
    """The requested sections, in the requested order, under one score in the `<cpcs_prompt>` envelope."""
    lines = [f'<cpcs_prompt carrier="hybrid" score_id={quoteattr(score_id)} sections="{" ".join(texts)}">',
             f"<authority>The canonical score {escape(score_id)} owns meaning. Each section projects it and adds no controls.</authority>"]
    for name, text in texts.items():
        if name == "xml":
            lines.append(_document(_TAGS["xml"], "", payload))
        else:
            lines.append(f"<{_TAGS[name]}>{_cdata(text, name + ' section')}</{_TAGS[name]}>")
    return "\n".join(lines + ["</cpcs_prompt>"]) + "\n"


def read_hybrid(text: str) -> dict[str, str]:
    """Section name -> section text, in printed order; the xml section comes back as its own XML text."""
    names = {tag: name for name, tag in _TAGS.items()}
    sections: dict[str, str] = {}
    for child in DefusedElementTree.fromstring(text):
        if child.tag not in names:
            continue
        name = names[child.tag]
        sections[name] = (_document(_TAGS["xml"], "", _children(child)) if name == "xml"
                          else (child.text or "").removeprefix("\n"))
    return sections
