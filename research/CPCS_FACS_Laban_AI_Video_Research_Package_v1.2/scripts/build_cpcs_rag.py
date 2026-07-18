from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to parse the Markdown front matter") from exc

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover
    raise SystemExit("jsonschema is required to validate the generated RAG records") from exc

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / 'paper' / 'CPCS_FACS_Laban_AI_Video_Directorial_Control_Research_Paper.md'
JSONL_PATH = ROOT / 'rag' / 'CPCS_RAG_Corpus.jsonl'
MANIFEST_PATH = ROOT / 'manifests' / 'CPCS_RAG_Build_Manifest.json'
SCHEMA_PATH = ROOT / 'schemas' / 'CPCS_RAG_Record_Schema.json'
REFERENCE_MD_PATH = ROOT / 'references' / 'CPCS_Reference_Index.md'
REFERENCE_JSON_PATH = ROOT / 'references' / 'CPCS_Reference_Index.json'
REFERENCE_CSV_PATH = ROOT / 'references' / 'CPCS_Reference_Index.csv'
REFERENCE_URLS_PATH = ROOT / 'references' / 'CPCS_Source_URLs.tsv'
EXTRACTION_SCHEMA_PATH = ROOT / 'schemas' / 'CPCS_Video_Extraction_Record_Schema.json'
EXTRACTION_EXAMPLE_PATH = ROOT / 'examples' / 'source_video_extraction_example.json'
PIPELINE_CONFIG_PATH = ROOT / 'configs' / 'video_to_cpcs_pipeline.yaml'
PEGASUS_PROMPT_PATH = ROOT / 'prompts' / 'PEGASUS_VIDEO_TO_CPCS_SEGMENTS.json'
GEMINI_PROMPT_PATH = ROOT / 'prompts' / 'GEMINI_VIDEO_TO_CPCS_PROMPT.md'
CHECKSUM_PATH = ROOT / 'SHA256SUMS.txt'

TARGET_WORDS = 600
MAX_WORDS = 800
OVERLAP_WORDS = 80


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE))


def approx_tokens(text: str) -> int:
    # Language-agnostic approximation for planning only. Actual ingestion should
    # count tokens with the deployed embedding model's tokenizer.
    return math.ceil(len(text) / 4.0)


def normalize_ws(text: str) -> str:
    return re.sub(r'[ \t]+', ' ', text).strip()


def extract_front_matter(text: str) -> tuple[dict[str, Any], int]:
    if not text.startswith('---\n'):
        raise ValueError('Markdown does not start with YAML front matter')
    end = text.find('\n---\n', 4)
    if end < 0:
        raise ValueError('Unterminated YAML front matter')
    raw = text[4:end]
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError('Front matter is not a mapping')
    return data, end + len('\n---\n')


def parse_marker(line: str) -> dict[str, Any] | None:
    m = re.search(
        r'<!--\s*RAG_CHUNK\s+id="([^"]+)"\s+title="([^"]+)"\s+concepts="([^"]*)"\s*-->',
        line,
    )
    if not m:
        return None
    return {
        'id': m.group(1),
        'title': m.group(2),
        'concepts': [x.strip() for x in m.group(3).split(',') if x.strip()],
    }


def split_atomic_blocks(lines: list[str]) -> list[str]:
    """Split Markdown without breaking fenced code blocks or tables."""
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue

        # Fenced code block.
        if lines[i].lstrip().startswith('```'):
            start = i
            i += 1
            while i < len(lines):
                if lines[i].lstrip().startswith('```'):
                    i += 1
                    break
                i += 1
            blocks.append('\n'.join(lines[start:i]).strip())
            continue

        # Markdown table: keep contiguous table rows intact.
        if lines[i].lstrip().startswith('|'):
            start = i
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith('|'):
                i += 1
            blocks.append('\n'.join(lines[start:i]).strip())
            continue

        # HTML comment or anchor.
        if lines[i].lstrip().startswith('<!--') or re.match(r'\s*<a\s+id=', lines[i]):
            blocks.append(lines[i].strip())
            i += 1
            continue

        # List block, including indented continuation lines until a blank line.
        if re.match(r'^\s*(?:[-*+] |\d+\. )', lines[i]):
            start = i
            i += 1
            while i < len(lines) and lines[i].strip():
                # Stop at an unindented heading.
                if re.match(r'^#{1,6}\s+', lines[i]):
                    break
                i += 1
            blocks.append('\n'.join(lines[start:i]).strip())
            continue

        # Ordinary paragraph or display equation group.
        start = i
        i += 1
        while i < len(lines) and lines[i].strip():
            if lines[i].lstrip().startswith('```') or lines[i].lstrip().startswith('|'):
                break
            if re.match(r'^#{1,6}\s+', lines[i]):
                break
            i += 1
        blocks.append('\n'.join(lines[start:i]).strip())

    return [b for b in blocks if b]


@dataclass
class HeadingSection:
    heading_line: str
    heading_title: str
    heading_path: list[str]
    lines: list[str]


def split_heading_sections(region_lines: list[str], document_title: str, marker_title: str) -> list[HeadingSection]:
    sections: list[HeadingSection] = []
    heading_stack: list[tuple[int, str]] = []
    current_heading = f'## {marker_title}'
    current_title = marker_title
    current_path = [document_title, marker_title]
    current_lines: list[str] = []
    in_fence = False

    def flush() -> None:
        nonlocal current_lines
        # Remove empty-only sections and marker anchors from the start only if no substantive text.
        if any(line.strip() and not re.match(r'<a\s+id=', line.strip()) for line in current_lines):
            sections.append(
                HeadingSection(
                    heading_line=current_heading,
                    heading_title=current_title,
                    heading_path=current_path.copy(),
                    lines=current_lines.copy(),
                )
            )
        current_lines = []

    for line in region_lines:
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
        m = None if in_fence else re.match(r'^(#{1,6})\s+(.+?)\s*$', line)
        if m:
            flush()
            level = len(m.group(1))
            title = re.sub(r'\s+#+$', '', m.group(2)).strip()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            current_heading = line.strip()
            current_title = title
            current_path = [document_title] + [x[1] for x in heading_stack]
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    return sections


def tail_words(text: str, n: int) -> str:
    words = re.findall(r'\S+', text)
    return ' '.join(words[-n:]) if words else ''


def chunk_heading_section(section: HeadingSection) -> list[dict[str, Any]]:
    blocks = split_atomic_blocks(section.lines)
    if not blocks:
        return []

    chunks: list[dict[str, Any]] = []
    current: list[str] = []
    current_words = 0

    def flush() -> None:
        nonlocal current, current_words
        if not current:
            return
        body = '\n\n'.join(current).strip()
        text = f'{section.heading_line}\n\n{body}'.strip()
        chunks.append({'text': text, 'oversize_atomic_block': current_words > MAX_WORDS})
        current = []
        current_words = 0

    for block in blocks:
        bw = word_count(block)
        if current and current_words + bw > MAX_WORDS:
            flush()
        if not current and bw > MAX_WORDS:
            current = [block]
            current_words = bw
            flush()
        else:
            current.append(block)
            current_words += bw
            if current_words >= TARGET_WORDS:
                flush()
    flush()
    return chunks




def longest_common_prefix(paths: list[list[str]]) -> list[str]:
    if not paths:
        return []
    prefix = paths[0].copy()
    for path in paths[1:]:
        i = 0
        while i < min(len(prefix), len(path)) and prefix[i] == path[i]:
            i += 1
        prefix = prefix[:i]
        if not prefix:
            break
    return prefix


def merge_section_pieces(pieces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge adjacent short heading sections into retrieval-sized semantic chunks."""
    merged: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_words = 0

    def flush() -> None:
        nonlocal current, current_words
        if not current:
            return
        texts = [x['text'] for x in current]
        paths: list[list[str]] = []
        titles: list[str] = []
        for x in current:
            if x['heading_path'] not in paths:
                paths.append(x['heading_path'])
            if x['heading_title'] not in titles:
                titles.append(x['heading_title'])
        merged.append({
            'text': '\n\n'.join(texts).strip(),
            'heading_paths': paths,
            'heading_path': longest_common_prefix(paths),
            'heading_titles': titles,
            'oversize_atomic_block': any(x.get('oversize_atomic_block', False) for x in current),
        })
        current = []
        current_words = 0

    for piece in pieces:
        pw = word_count(piece['text'])
        if piece.get('oversize_atomic_block', False) or pw > MAX_WORDS:
            flush()
            current = [piece]
            current_words = pw
            flush()
            continue
        if current and current_words + pw > MAX_WORDS:
            flush()
        current.append(piece)
        current_words += pw
    flush()

    # Avoid tiny tail chunks when they fit safely into the preceding chunk.
    if len(merged) >= 2:
        tail = merged[-1]
        prev = merged[-2]
        tw = word_count(tail['text'])
        pw = word_count(prev['text'])
        if tw < 180 and pw + tw <= MAX_WORDS + 80 and not tail['oversize_atomic_block'] and not prev['oversize_atomic_block']:
            combined_paths = prev['heading_paths'] + [p for p in tail['heading_paths'] if p not in prev['heading_paths']]
            combined_titles = prev['heading_titles'] + [t for t in tail['heading_titles'] if t not in prev['heading_titles']]
            merged[-2] = {
                'text': prev['text'] + '\n\n' + tail['text'],
                'heading_paths': combined_paths,
                'heading_path': longest_common_prefix(combined_paths),
                'heading_titles': combined_titles,
                'oversize_atomic_block': False,
            }
            merged.pop()
    return merged

def parse_abstract(text: str) -> str:
    m = re.search(r'## Abstract\n\n(.*?)(?=\n---\n\n<!-- RAG_CHUNK)', text, flags=re.S)
    if not m:
        raise ValueError('Could not locate abstract')
    return '## Abstract\n\n' + m.group(1).strip()


def source_domain(source_id: str) -> list[str]:
    num = int(re.match(r'\d+', source_id).group())
    if source_id in {'08A'}:
        return ['affective_science', 'measurement']
    if num <= 6:
        return ['facial_action_coding', 'facial_behavior']
    if num <= 8:
        return ['affective_science']
    if num <= 15:
        return ['facial_generation', 'affective_computing']
    if num <= 21:
        return ['body_behavior', 'laban_movement_analysis']
    if num <= 28:
        return ['character_animation', 'human_body_models']
    if num <= 36:
        return ['human_motion_generation', 'interaction_control']
    if num <= 41:
        return ['controllable_video_generation', 'camera_control']
    if num <= 50:
        return ['evaluation', 'benchmarks', 'human_motion_generation']
    if num <= 61:
        return ['structured_data', 'schema', 'interchange_standards']
    if num <= 66:
        return ['video_generation_api', 'model_adapter', 'provider_documentation']
    if num <= 74:
        return ['multimodal_video_understanding', 'provider_documentation', 'video_retrieval']
    if num <= 77:
        return ['media_forensics', 'shot_detection', 'video_annotation']
    if num <= 83:
        return ['face_analysis', 'pose_estimation', 'human_reconstruction', 'optical_flow', 'camera_reconstruction']
    if num <= 88:
        return ['shot_detection', 'scene_segmentation', 'action_segmentation', 'movie_understanding']
    return ['speech_recognition', 'multiview_activity', 'gaze', 'timeline_interchange']


def evidence_tier_for_source(source_id: str) -> str:
    num = int(re.match(r'\d+', source_id).group())
    if num <= 28 or 51 <= num <= 61 or 75 <= num <= 89 or 91 <= num <= 92:
        return 'established_or_foundational'
    return 'emerging_or_recent_or_current_documentation'


def parse_reference_records(text: str) -> list[dict[str, Any]]:
    ref_start = text.index('# Full Reference List')
    ref_end = text.index('# Document Change Log')
    ref_text = text[ref_start:ref_end]
    pattern = re.compile(
        r'<a id="source-S(?P<id>\d+[A-Z]?)"></a>\n'
        r'\*\*\[S(?P=id)\]\*\*\s+(?P<citation>.*?)(?=\n\n<a id="source-S|\n\n---\n)',
        flags=re.S,
    )
    records: list[dict[str, Any]] = []
    for m in pattern.finditer(ref_text):
        sid = m.group('id')
        citation = normalize_ws(m.group('citation'))
        urls = re.findall(r'https?://[^\s·]+', citation)
        record = {
            'record_id': f'source.S{sid}',
            'record_type': 'source',
            'source_id': f'S{sid}',
            'document_id': 'CPCS-RP-2026-01',
            'citation_text': citation,
            'urls': urls,
            'domains': source_domain(sid),
            'evidence_tier': evidence_tier_for_source(sid),
            'primary_source_preferred': True,
            'anchor': f'source-S{sid}',
            'language': 'en',
            'content_hash': 'sha256:' + sha256_text(citation),
        }
        records.append(record)
    return records


def build_record_schema() -> dict[str, Any]:
    # Flexible schema because JSONL contains document, paper_chunk, and source records.
    return {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://example.invalid/schemas/cpcs-rag-record-1.0.json',
        'title': 'CPCS RAG JSONL Record',
        'type': 'object',
        'required': ['record_id', 'record_type', 'document_id', 'content_hash'],
        'properties': {
            'record_id': {'type': 'string', 'minLength': 1},
            'record_type': {'enum': ['document', 'paper_chunk', 'source']},
            'document_id': {'type': 'string'},
            'document_version': {'type': 'string'},
            'title': {'type': 'string'},
            'heading_path': {'type': 'array', 'items': {'type': 'string'}},
            'heading_paths': {'type': 'array', 'items': {'type': 'array', 'items': {'type': 'string'}}},
            'text': {'type': 'string'},
            'context_before': {'type': 'string'},
            'concepts': {'type': 'array', 'items': {'type': 'string'}},
            'source_ids': {'type': 'array', 'items': {'pattern': '^S\\d+[A-Z]?$'}},
            'evidence_labels': {'type': 'array', 'items': {'type': 'string'}},
            'anchors': {'type': 'array', 'items': {'type': 'string'}},
            'word_count': {'type': 'integer', 'minimum': 0},
            'character_count': {'type': 'integer', 'minimum': 0},
            'approx_token_count': {'type': 'integer', 'minimum': 0},
            'content_hash': {'type': 'string', 'pattern': '^sha256:[0-9a-f]{64}$'},
            'source_id': {'type': 'string', 'pattern': '^S\\d+[A-Z]?$'},
            'citation_text': {'type': 'string'},
            'urls': {'type': 'array', 'items': {'type': 'string', 'format': 'uri'}},
            'domains': {'type': 'array', 'items': {'type': 'string'}},
        },
        'additionalProperties': True,
    }



def write_reference_indices(source_records: list[dict[str, Any]]) -> None:
    """Write the bibliography in human- and machine-readable index formats."""
    REFERENCE_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    md_lines = [
        '# CPCS Reference Index',
        '',
        f'**Reference records:** {len(source_records)}',
        '',
        '| ID | Citation | Domains | URLs |',
        '|---|---|---|---|',
    ]
    for record in source_records:
        citation = record['citation_text'].replace('|', r'\|')
        domains = ', '.join(record.get('domains', []))
        urls = '<br>'.join(record.get('urls', []))
        md_lines.append(f"| {record['source_id']} | {citation} | {domains} | {urls} |")
    REFERENCE_MD_PATH.write_text('\n'.join(md_lines) + '\n', encoding='utf-8', newline='\n')

    REFERENCE_JSON_PATH.write_text(
        json.dumps(source_records, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
        newline='\n',
    )

    with REFERENCE_CSV_PATH.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=['source_id', 'citation_text', 'domains', 'evidence_tier', 'urls', 'anchor'],
        )
        writer.writeheader()
        for record in source_records:
            writer.writerow({
                'source_id': record['source_id'],
                'citation_text': record['citation_text'],
                'domains': ';'.join(record.get('domains', [])),
                'evidence_tier': record.get('evidence_tier', ''),
                'urls': ';'.join(record.get('urls', [])),
                'anchor': record.get('anchor', ''),
            })

    with REFERENCE_URLS_PATH.open('w', encoding='utf-8', newline='') as handle:
        handle.write('source_id\turl\tcitation_text\n')
        for record in source_records:
            for url in record.get('urls', []):
                citation = record['citation_text'].replace('\t', ' ').replace('\n', ' ')
                handle.write(f"{record['source_id']}\t{url}\t{citation}\n")


def markdown_toc_validation(text: str) -> tuple[list[str], list[str]]:
    """Return internal ToC anchors and any missing targets."""
    toc_match = re.search(
        r'<a id="cpcs-toc"></a>.*?<!-- RAG_EXCLUDE_END -->',
        text,
        flags=re.S,
    )
    if not toc_match:
        return [], ['cpcs-toc-region-not-found']
    links = re.findall(r'\]\(#([A-Za-z0-9._:-]+)\)', toc_match.group(0))
    targets = set(re.findall(r'<a id="([^"]+)"></a>', text))
    missing = sorted(set(links) - targets)
    return links, missing


def package_file_stats(root: Path, excluded: set[Path]) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        resolved = path.resolve()
        if resolved in excluded or '__pycache__' in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        item: dict[str, Any] = {
            'bytes': path.stat().st_size,
            'sha256': sha256_file(path),
        }
        if path.suffix.lower() in {'.md', '.json', '.jsonl', '.yaml', '.yml', '.py', '.csv', '.tsv', '.txt'}:
            try:
                item['lines'] = len(path.read_text(encoding='utf-8').splitlines())
            except UnicodeDecodeError:
                pass
        stats[rel] = item
    return stats


def write_checksums(root: Path) -> int:
    lines: list[str] = []
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        if path.resolve() == CHECKSUM_PATH.resolve() or '__pycache__' in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        lines.append(f"{sha256_file(path)}  {rel}")
    CHECKSUM_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    return len(lines)

def main() -> None:
    text = MD_PATH.read_text(encoding='utf-8')
    front, _ = extract_front_matter(text)
    document_title = str(front['title'])
    doc_id = str(front['document_id'])
    doc_version = str(front['version'])

    lines = text.splitlines()
    marker_positions: list[tuple[int, dict[str, Any]]] = []
    for idx, line in enumerate(lines):
        marker = parse_marker(line)
        if marker:
            marker_positions.append((idx, marker))

    reference_heading_idx = next(i for i, line in enumerate(lines) if line.strip() == '# Full Reference List')

    paper_records: list[dict[str, Any]] = []
    previous_text = ''
    global_ordinal = 0

    # Abstract as a first-class retrieval unit.
    abstract = parse_abstract(text)
    global_ordinal += 1
    abstract_record = {
        'record_id': 'cpcs.abstract.001',
        'record_type': 'paper_chunk',
        'parent_record_id': 'cpcs.abstract',
        'document_id': doc_id,
        'document_version': doc_version,
        'title': 'Abstract',
        'heading_path': [document_title, 'Abstract'],
        'concepts': list(front.get('keywords', [])),
        'source_ids': sorted(set(re.findall(r'\[S(\d+[A-Z]?)\]', abstract))),
        'evidence_labels': sorted(set(re.findall(r'\[(ESTABLISHED|EMERGING|PROPOSED|OPERATIONALIZATION|CAUTION)\]', abstract))),
        'anchors': ['cpcs-abstract'],
        'text': abstract,
        'context_before': '',
        'language': front.get('language', 'en'),
        'word_count': word_count(abstract),
        'character_count': len(abstract),
        'approx_token_count': approx_tokens(abstract),
        'contains_code': '```' in abstract,
        'contains_table': re.search(r'^\|', abstract, flags=re.M) is not None,
        'oversize_atomic_block': False,
        'ordinal': global_ordinal,
        'content_hash': 'sha256:' + sha256_text(abstract),
    }
    abstract_record['source_ids'] = [f'S{x}' for x in abstract_record['source_ids']]
    paper_records.append(abstract_record)
    previous_text = abstract

    for pos_idx, (start_idx, marker) in enumerate(marker_positions):
        next_idx = marker_positions[pos_idx + 1][0] if pos_idx + 1 < len(marker_positions) else reference_heading_idx
        end_idx = min(next_idx, reference_heading_idx)
        if start_idx >= reference_heading_idx:
            break
        region = lines[start_idx + 1:end_idx]
        region_text = '\n'.join(region)
        region_text = re.sub(
            r'<!-- RAG_EXCLUDE_START -->.*?<!-- RAG_EXCLUDE_END -->',
            '',
            region_text,
            flags=re.S,
        )
        region = region_text.splitlines()
        sections = split_heading_sections(region, document_title, marker['title'])
        pieces: list[dict[str, Any]] = []
        for section in sections:
            for sub in chunk_heading_section(section):
                pieces.append({
                    'text': sub['text'],
                    'heading_path': section.heading_path,
                    'heading_title': section.heading_title,
                    'oversize_atomic_block': bool(sub['oversize_atomic_block']),
                })
        merged_chunks = merge_section_pieces(pieces)
        marker_chunk_counter = 0
        for sub in merged_chunks:
            marker_chunk_counter += 1
            global_ordinal += 1
            chunk_text = sub['text']
            sid_matches = sorted(
                set(re.findall(r'\[S(\d+[A-Z]?)\]', chunk_text)),
                key=lambda x: (int(re.match(r'\d+', x).group()), x),
            )
            labels = sorted(set(re.findall(
                r'\[(ESTABLISHED|EMERGING|PROPOSED|OPERATIONALIZATION|CAUTION)\]',
                chunk_text,
            )))
            anchors = re.findall(r'<a\s+id="([^"]+)"\s*></a>', chunk_text)
            record_id = f"{marker['id']}.{marker_chunk_counter:03d}"
            titles = sub['heading_titles']
            title = titles[0] if len(titles) == 1 else f"{marker['title']}: {titles[0]} — {titles[-1]}"
            rec = {
                'record_id': record_id,
                'record_type': 'paper_chunk',
                'parent_record_id': marker['id'],
                'document_id': doc_id,
                'document_version': doc_version,
                'title': title,
                'marker_title': marker['title'],
                'heading_path': sub['heading_path'],
                'heading_paths': sub['heading_paths'],
                'concepts': marker['concepts'],
                'source_ids': [f'S{x}' for x in sid_matches],
                'evidence_labels': labels,
                'anchors': anchors,
                'text': chunk_text,
                'context_before': tail_words(previous_text, OVERLAP_WORDS),
                'language': front.get('language', 'en'),
                'word_count': word_count(chunk_text),
                'character_count': len(chunk_text),
                'approx_token_count': approx_tokens(chunk_text),
                'contains_code': '```' in chunk_text,
                'contains_table': re.search(r'^\|', chunk_text, flags=re.M) is not None,
                'oversize_atomic_block': bool(sub['oversize_atomic_block']),
                'ordinal': global_ordinal,
                'content_hash': 'sha256:' + sha256_text(chunk_text),
            }
            paper_records.append(rec)
            previous_text = chunk_text

    source_records = parse_reference_records(text)
    source_ids = {r['source_id'] for r in source_records}

    cited_in: dict[str, list[str]] = defaultdict(list)
    for rec in paper_records:
        for sid in rec.get('source_ids', []):
            cited_in[sid].append(rec['record_id'])
    for rec in source_records:
        rec['cited_in_record_ids'] = cited_in.get(rec['source_id'], [])

    doc_summary_match = re.search(r'<!-- RAG_DOC_SUMMARY:\s*(.*?)\s*-->', text, flags=re.S)
    doc_summary = normalize_ws(doc_summary_match.group(1)) if doc_summary_match else ''
    document_record = {
        'record_id': 'document.CPCS-RP-2026-01',
        'record_type': 'document',
        'document_id': doc_id,
        'document_version': doc_version,
        'title': document_title,
        'subtitle': front.get('subtitle'),
        'summary': doc_summary,
        'date': str(front.get('date')),
        'literature_cutoff': str(front.get('literature_cutoff')),
        'framework_name': front.get('framework_name'),
        'framework_acronym': front.get('framework_acronym'),
        'keywords': front.get('keywords', []),
        'knowledge_domains': front.get('knowledge_domains', []),
        'rag_chunking': front.get('rag_chunking', {}),
        'source_count': len(source_records),
        'paper_chunk_count': len(paper_records),
        'language': front.get('language', 'en'),
        'content_hash': 'sha256:' + sha256_text(doc_summary + '\n' + document_title),
    }

    records = [document_record] + paper_records + source_records

    # Integrity checks before writing.
    ids = [r['record_id'] for r in records]
    duplicate_ids = [x for x, count in Counter(ids).items() if count > 1]
    unresolved_source_ids = sorted(
        {sid for rec in paper_records for sid in rec.get('source_ids', [])} - source_ids
    )
    if duplicate_ids:
        raise ValueError(f'Duplicate record IDs: {duplicate_ids}')
    if unresolved_source_ids:
        raise ValueError(f'Unresolved source IDs: {unresolved_source_ids}')
    if not source_records:
        raise ValueError('No source records were parsed from the bibliography')

    with JSONL_PATH.open('w', encoding='utf-8', newline='\n') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + '\n')

    schema = build_record_schema()
    SCHEMA_PATH.write_text(json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    # Re-read JSONL to guarantee line-level validity.
    parsed_records: list[dict[str, Any]] = []
    with JSONL_PATH.open('r', encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            try:
                parsed_records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f'Invalid JSONL at line {line_no}: {exc}') from exc

    schema_validator = Draft202012Validator(schema)
    schema_errors: list[str] = []
    for line_no, record in enumerate(parsed_records, 1):
        for error in sorted(schema_validator.iter_errors(record), key=lambda item: list(item.absolute_path)):
            path = '/'.join(str(part) for part in error.absolute_path) or '<record>'
            schema_errors.append(
                f'line {line_no} record {record.get("record_id", "<unknown>")} at {path}: {error.message}'
            )
    if schema_errors:
        preview = '\n'.join(schema_errors[:20])
        raise ValueError(f'Generated RAG records failed JSON Schema validation:\n{preview}')

    body = text.split('# Full Reference List', 1)[0]
    cited = {f'S{x}' for x in re.findall(r'\[S(\d+[A-Z]?)\]', body)}
    bibliography_ids = {r['source_id'] for r in source_records}
    marker_ids = [m['id'] for _, m in marker_positions]
    chunk_words = [r['word_count'] for r in paper_records]
    oversize = [r['record_id'] for r in paper_records if r['word_count'] > MAX_WORDS]
    toc_links, missing_toc_anchors = markdown_toc_validation(text)

    code_fences_balanced = text.count('```') % 2 == 0
    marker_ids_unique = len(marker_ids) == len(set(marker_ids))
    citation_sets_equal = cited == bibliography_ids
    source_anchor_count = len(re.findall(r'<a id="source-S\d+[A-Z]?"></a>', text))

    if not code_fences_balanced:
        raise ValueError('Markdown code fences are not balanced')
    if not marker_ids_unique:
        duplicates = sorted(x for x, count in Counter(marker_ids).items() if count > 1)
        raise ValueError(f'Duplicate RAG marker IDs: {duplicates}')
    if missing_toc_anchors:
        raise ValueError(f'Missing Table of Contents anchor targets: {missing_toc_anchors}')
    if not citation_sets_equal:
        missing_bibliography = sorted(cited - bibliography_ids)
        uncited_bibliography = sorted(bibliography_ids - cited)
        raise ValueError(
            'Citation and bibliography source IDs differ. '
            f'Missing bibliography entries: {missing_bibliography}; '
            f'uncited bibliography entries: {uncited_bibliography}'
        )
    if source_anchor_count != len(source_records):
        raise ValueError(
            f'Source anchor count {source_anchor_count} does not match parsed references {len(source_records)}'
        )

    # Companion artifact validation.
    extraction_schema = json.loads(EXTRACTION_SCHEMA_PATH.read_text(encoding='utf-8'))
    extraction_example = json.loads(EXTRACTION_EXAMPLE_PATH.read_text(encoding='utf-8'))
    extraction_validator = Draft202012Validator(extraction_schema)
    extraction_errors = sorted(
        extraction_validator.iter_errors(extraction_example),
        key=lambda item: list(item.absolute_path),
    )
    if extraction_errors:
        preview = '\n'.join(
            f"/{'/'.join(str(x) for x in error.absolute_path)}: {error.message}"
            for error in extraction_errors[:20]
        )
        raise ValueError(f'Video extraction example failed schema validation:\n{preview}')

    semantic_range_errors: list[str] = []
    source_duration = float(extraction_example['source']['duration_s'])
    for collection_name, items, range_key in [
        ('segments', extraction_example.get('segments', []), 'time_range'),
        ('observations', extraction_example.get('observations', []), 'time_range'),
    ]:
        for item in items:
            value = item[range_key]
            if float(value['end_s']) < float(value['start_s']):
                semantic_range_errors.append(f"{collection_name}: end before start in {item}")
            if float(value['end_s']) > source_duration + 1e-6:
                semantic_range_errors.append(f"{collection_name}: interval exceeds source duration in {item}")
    for name, track in extraction_example.get('tracks', {}).items():
        value = track['coverage']
        if float(value['end_s']) < float(value['start_s']) or float(value['end_s']) > source_duration + 1e-6:
            semantic_range_errors.append(f'track {name}: illegal coverage interval')
    if semantic_range_errors:
        raise ValueError('Video extraction example semantic validation failed: ' + '; '.join(semantic_range_errors))

    pipeline_config = yaml.safe_load(PIPELINE_CONFIG_PATH.read_text(encoding='utf-8'))
    if not isinstance(pipeline_config, dict) or pipeline_config.get('schema') != 'cpcs-video-extraction-pipeline/1.0':
        raise ValueError('Pipeline YAML did not parse or has the wrong schema identifier')
    pegasus_prompt = json.loads(PEGASUS_PROMPT_PATH.read_text(encoding='utf-8'))
    definitions = pegasus_prompt.get('response_format', {}).get('segment_definitions', [])
    if pegasus_prompt.get('analysis_mode') != 'time_based_metadata' or not 1 <= len(definitions) <= 10:
        raise ValueError('Pegasus prompt must use time_based_metadata with 1-10 segment definitions')
    gemini_prompt_text = GEMINI_PROMPT_PATH.read_text(encoding='utf-8')
    if word_count(gemini_prompt_text) < 500:
        raise ValueError('Gemini prompt template is unexpectedly short')

    write_reference_indices(source_records)

    md_stats = {
        'bytes': MD_PATH.stat().st_size,
        'lines': len(text.splitlines()),
        'words': word_count(text),
        'sha256': sha256_file(MD_PATH),
    }
    jsonl_stats = {
        'bytes': JSONL_PATH.stat().st_size,
        'lines': len(parsed_records),
        'sha256': sha256_file(JSONL_PATH),
    }
    schema_stats = {
        'bytes': SCHEMA_PATH.stat().st_size,
        'sha256': sha256_file(SCHEMA_PATH),
    }

    package_files = package_file_stats(
        ROOT,
        excluded={MANIFEST_PATH.resolve(), CHECKSUM_PATH.resolve()},
    )

    manifest = {
        'manifest_schema': 'cpcs-artifact-manifest/1.2',
        'document_id': doc_id,
        'document_version': doc_version,
        'generated_date': str(front.get('date', '2026-07-18')),
        'literature_cutoff': str(front.get('literature_cutoff')),
        'package_root_name': ROOT.name,
        'files': package_files,
        'records': {
            'total': len(parsed_records),
            'document_records': 1,
            'paper_chunks': len(paper_records),
            'source_records': len(source_records),
            'rag_marker_count': len(marker_ids),
            'unique_rag_marker_count': len(set(marker_ids)),
        },
        'chunk_statistics': {
            'target_words': TARGET_WORDS,
            'maximum_words_soft_limit': MAX_WORDS,
            'overlap_context_words': OVERLAP_WORDS,
            'minimum_words': min(chunk_words),
            'median_words': statistics.median(chunk_words),
            'mean_words': round(statistics.mean(chunk_words), 2),
            'maximum_words': max(chunk_words),
            'oversize_chunk_ids': oversize,
            'oversize_policy': 'Tables and fenced code blocks are preserved intact.',
        },
        'validation': {
            'yaml_front_matter_parsed': True,
            'markdown_code_fences_balanced': code_fences_balanced,
            'toc_internal_link_count': len(toc_links),
            'toc_missing_anchor_targets': missing_toc_anchors,
            'rag_marker_ids_unique': marker_ids_unique,
            'record_ids_unique': len(ids) == len(set(ids)),
            'jsonl_line_parse_success': len(parsed_records) == len(records),
            'rag_json_schema_draft_2020_12_validation_success': not schema_errors,
            'rag_json_schema_validation_error_count': len(schema_errors),
            'video_extraction_schema_validation_success': not extraction_errors,
            'video_extraction_semantic_range_validation_success': not semantic_range_errors,
            'pipeline_yaml_parse_success': True,
            'pegasus_segment_definition_count': len(definitions),
            'gemini_prompt_word_count': word_count(gemini_prompt_text),
            'in_text_source_ids': sorted(cited),
            'bibliography_source_ids': sorted(bibliography_ids),
            'all_citations_resolve_and_all_sources_are_cited': citation_sets_equal,
            'all_chunk_sources_resolve': not unresolved_source_ids,
            'source_anchor_count': source_anchor_count,
            'reference_entry_count': len(source_records),
        },
        'notes': [
            'Approximate token counts use character_count / 4 and must be recomputed with the deployed tokenizer.',
            'The JSONL includes no embeddings, no source-video frames, and no proprietary FACS manual content.',
            'The source-video extraction example is synthetic and contains placeholder asset hashes and URIs.',
            'Hosted provider capabilities are date-sensitive; adapter profiles must be reverified before production use.',
            'Downstream systems must enforce rights, consent, access, retention, and licensing policies.',
        ],
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
        encoding='utf-8',
        newline='\n',
    )
    checksum_entry_count = write_checksums(ROOT)

    print(json.dumps({
        'markdown': md_stats,
        'jsonl': jsonl_stats,
        'schema': schema_stats,
        'manifest_path': str(MANIFEST_PATH),
        'paper_chunks': len(paper_records),
        'source_records': len(source_records),
        'total_records': len(records),
        'chunk_min_words': min(chunk_words),
        'chunk_median_words': statistics.median(chunk_words),
        'chunk_mean_words': round(statistics.mean(chunk_words), 2),
        'chunk_max_words': max(chunk_words),
        'oversize_chunks': oversize,
        'checksum_entry_count': checksum_entry_count,
        'package_file_count': len(package_files),
    }, indent=2))


if __name__ == '__main__':
    main()
