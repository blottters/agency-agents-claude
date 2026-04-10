from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


HOME = Path.home()
SOURCE_ROOT = HOME / "Downloads" / "agency-agents-main"
MARKETPLACE_PATH = HOME / ".agents" / "plugins" / "marketplace.json"
PLUGIN_ROOTS = {
    "agency-agents": HOME / "plugins" / "agency-agents",
    "agency-game-development": HOME / "plugins" / "agency-game-development",
}

NON_GAME_DIVISIONS = {
    "academic",
    "design",
    "engineering",
    "marketing",
    "paid-media",
    "product",
    "project-management",
    "sales",
    "spatial-computing",
    "specialized",
    "strategy",
    "support",
    "testing",
}

COLOR_MAP = {
    "blue": "#2563EB",
    "green": "#15803D",
    "yellow": "#CA8A04",
    "red": "#DC2626",
    "purple": "#7C3AED",
    "pink": "#DB2777",
    "orange": "#EA580C",
    "teal": "#0F766E",
    "indigo": "#4F46E5",
    "gray": "#475569",
}

PLUGIN_SPECS = {
    "agency-agents": {
        "display_name": "Agency Agents",
        "short_description": "Browse and trigger specialist skills across engineering, design, product, testing, strategy, and support.",
        "long_description": (
            "A large local Codex plugin built from the Agency agent library. "
            "It exposes specialist skills across engineering, design, product, "
            "strategy, testing, support, and related domains, with descriptions "
            "tuned for both browsing and implicit invocation."
        ),
        "category": "Productivity",
        "brand_color": "#2563EB",
        "keywords": [
            "agency",
            "skills",
            "engineering",
            "design",
            "strategy",
            "testing",
            "product",
        ],
        "default_prompts": [
            "Route this task to the right agency specialist and execute it cleanly.",
            "Find the best skill here for a design, engineering, or testing problem.",
            "Use the relevant agency specialist to turn this brief into deliverables.",
        ],
        "plugin_prompt": (
            "Use Agency Agents to route this task to the strongest local specialist "
            "across engineering, design, product, testing, or strategy."
        ),
    },
    "agency-game-development": {
        "display_name": "Agency Game Development",
        "short_description": "Game design and engine-specific skills for Unity, Unreal, Godot, Roblox, Blender, and technical art.",
        "long_description": (
            "A local Codex plugin built from the Agency game-development roster. "
            "It complements the built-in game tooling with explicit engine-specific "
            "specialists for Unity, Unreal, Godot, Roblox Studio, Blender, game "
            "design, narrative, level design, audio, and technical art."
        ),
        "category": "Coding",
        "brand_color": "#0F766E",
        "keywords": [
            "game-development",
            "unity",
            "unreal",
            "godot",
            "roblox",
            "blender",
            "game-design",
        ],
        "default_prompts": [
            "Use the right game-development specialist for this engine or design task.",
            "Help me choose between the Unity, Unreal, Godot, and design specialists.",
            "Route this gameplay, narrative, or technical-art task to the best skill.",
        ],
        "plugin_prompt": (
            "Use Agency Game Development to choose the right local specialist for "
            "this engine, gameplay, narrative, level, or technical-art task."
        ),
    },
}


def main() -> None:
    ensure_roots()
    configure_marketplace()
    for plugin_name, plugin_root in PLUGIN_ROOTS.items():
        build_plugin(plugin_name, plugin_root)


def ensure_roots() -> None:
    for plugin_root in PLUGIN_ROOTS.values():
        (plugin_root / "skills").mkdir(parents=True, exist_ok=True)
        (plugin_root / "assets").mkdir(parents=True, exist_ok=True)
        (plugin_root / "agents").mkdir(parents=True, exist_ok=True)
        (plugin_root / ".codex-plugin").mkdir(parents=True, exist_ok=True)
        (plugin_root / "references").mkdir(parents=True, exist_ok=True)
    MARKETPLACE_PATH.parent.mkdir(parents=True, exist_ok=True)


def configure_marketplace() -> None:
    if MARKETPLACE_PATH.exists():
        data = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
    else:
        data = {"name": "local-plugins", "interface": {"displayName": "Local Plugins"}, "plugins": []}

    data["name"] = "local-plugins"
    data.setdefault("interface", {})
    data["interface"]["displayName"] = "Local Plugins"

    desired_entries = {
        "agency-agents": {
            "name": "agency-agents",
            "source": {"source": "local", "path": "./plugins/agency-agents"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Productivity",
        },
        "agency-game-development": {
            "name": "agency-game-development",
            "source": {"source": "local", "path": "./plugins/agency-game-development"},
            "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
            "category": "Coding",
        },
    }

    existing = {entry.get("name"): entry for entry in data.get("plugins", [])}
    ordered_plugins = []
    seen = set()

    for name in ["agency-agents", "agency-game-development"]:
        ordered_plugins.append(desired_entries[name])
        seen.add(name)

    for entry in data.get("plugins", []):
        name = entry.get("name")
        if name not in seen:
            ordered_plugins.append(entry)

    data["plugins"] = ordered_plugins
    MARKETPLACE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def build_plugin(plugin_name: str, plugin_root: Path) -> None:
    spec = PLUGIN_SPECS[plugin_name]
    write_plugin_manifest(plugin_name, plugin_root, spec)
    write_plugin_openai_yaml(plugin_root, spec)
    write_plugin_assets(plugin_root, spec["brand_color"], spec["display_name"])

    if plugin_name == "agency-agents":
        source_files = gather_agent_files(NON_GAME_DIVISIONS)
        copy_integration_references(plugin_root)
    else:
        source_files = gather_game_agent_files()

    for source_path in source_files:
        build_skill(plugin_name, plugin_root, source_path)


def gather_agent_files(allowed_divisions: set[str]) -> list[Path]:
    files: list[Path] = []
    for path in sorted(SOURCE_ROOT.rglob("*.md")):
        if not path.is_file():
            continue
        rel = path.relative_to(SOURCE_ROOT)
        if rel.parts[0] not in allowed_divisions:
            continue
        if has_valid_frontmatter(path):
            files.append(path)
    return files


def gather_game_agent_files() -> list[Path]:
    game_root = SOURCE_ROOT / "game-development"
    return [path for path in sorted(game_root.rglob("*.md")) if has_valid_frontmatter(path)]


def has_valid_frontmatter(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    metadata, _ = parse_frontmatter(text)
    return "name" in metadata and "description" in metadata


def build_skill(plugin_name: str, plugin_root: Path, source_path: Path) -> None:
    text = source_path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(text)
    slug = source_path.stem
    skill_root = plugin_root / "skills" / slug
    agents_dir = skill_root / "agents"
    references_dir = skill_root / "references"

    agents_dir.mkdir(parents=True, exist_ok=True)
    references_dir.mkdir(parents=True, exist_ok=True)

    relative_source = source_path.relative_to(SOURCE_ROOT).as_posix()
    category = source_path.relative_to(SOURCE_ROOT).parts[0]
    display_name = str(metadata.get("name", titleize(slug))).strip()
    source_description = str(metadata.get("description", "")).strip()
    skill_description = make_skill_description(source_description, display_name, category)

    sections = split_sections(body)
    overview = build_overview(display_name, source_description, category, relative_source)
    responsibilities = format_bullets_or_subsections(
        sections,
        ["core mission", "core responsibilities", "core focus"],
        fallback=["Handle the core responsibilities described in the source role definition."],
    )
    guardrails = format_bullets_or_subsections(
        sections, ["critical rules"], fallback=["Keep the role focused, concrete, and delivery-oriented."]
    )
    deliverables = format_deliverables(sections)
    workflow = format_workflow(sections)
    working_style = format_bullets_or_subsections(sections, ["communication style"], fallback=None)
    quality_bar = format_bullets_or_subsections(sections, ["success metrics"], fallback=None)
    advanced = format_bullets_or_subsections(sections, ["advanced capabilities"], fallback=None)

    skill_md = compose_skill_markdown(
        slug=slug,
        display_name=display_name,
        description=skill_description,
        overview=overview,
        responsibilities=responsibilities,
        guardrails=guardrails,
        deliverables=deliverables,
        workflow=workflow,
        working_style=working_style,
        quality_bar=quality_bar,
        advanced=advanced,
        source_reference=relative_source,
        plugin_name=plugin_name,
    )
    (skill_root / "SKILL.md").write_text(skill_md, encoding="utf-8")

    prompt_target = display_name.lower()
    short_description = truncate_for_ui(source_description or skill_description.removeprefix("Use when "), 64)
    openai_yaml = compose_openai_yaml(
        display_name=display_name,
        short_description=short_description,
        brand_color=COLOR_MAP.get(str(metadata.get("color", "")).strip().lower(), PLUGIN_SPECS[plugin_name]["brand_color"]),
        default_prompt=(
            f"Use ${slug} when you need {prompt_target} guidance, deliverables, and decision rules for this task."
        ),
    )
    (agents_dir / "openai.yaml").write_text(openai_yaml, encoding="utf-8")
    (references_dir / "source.md").write_text(text, encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    raw = match.group(1)
    body = match.group(2)
    metadata: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    for line in raw.splitlines():
        if re.match(r"^[A-Za-z0-9_-]+:\s*", line):
            if current_key is not None:
                metadata[current_key] = clean_yaml_value("\n".join(current_lines))
            key, value = line.split(":", 1)
            current_key = key.strip()
            current_lines = [value.strip()]
        elif current_key is not None:
            current_lines.append(line)
    if current_key is not None:
        metadata[current_key] = clean_yaml_value("\n".join(current_lines))
    return metadata, body


def clean_yaml_value(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("|"):
        cleaned = cleaned[1:].strip()
    cleaned = cleaned.strip("\"'")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return ascii_punctuation(cleaned)


def split_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_title = "intro"
    buffer: list[str] = []
    in_code_block = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            buffer.append(line)
            continue
        if not in_code_block and line.startswith("## "):
            sections[current_title] = "\n".join(buffer).strip()
            current_title = normalize_heading(line[3:])
            buffer = []
        else:
            buffer.append(line)
    sections[current_title] = "\n".join(buffer).strip()
    return sections


def normalize_heading(text: str) -> str:
    text = re.sub(r"[^\w\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def build_overview(display_name: str, source_description: str, category: str, relative_source: str) -> str:
    summary = source_description or f"{display_name} specialist"
    return (
        f"Use this skill when the task matches the {display_name} role from the Agency library. "
        f"It was converted from `{relative_source}` in the `{category}` division and should stay "
        f"focused on concrete outputs, clear constraints, and domain-specific decision support.\n\n"
        f"Source summary: {summary}"
    )


def format_bullets_or_subsections(
    sections: dict[str, str], keys: list[str], fallback: list[str] | None
) -> str | None:
    for key in keys:
        section = find_section(sections, key)
        if not section:
            continue
        subsections = extract_subsections(section)
        if subsections:
            parts = []
            for title, content in subsections[:8]:
                bullets = extract_bullets(content)
                if bullets:
                    parts.append(f"### {title}\n" + "\n".join(f"- {bullet}" for bullet in bullets[:8]))
                else:
                    paragraph = first_meaningful_paragraph(content)
                    if paragraph:
                        parts.append(f"### {title}\n{paragraph}")
            if parts:
                return "\n\n".join(parts)
        bullets = extract_bullets(section)
        if bullets:
            return "\n".join(f"- {bullet}" for bullet in bullets[:10])
        paragraph = first_meaningful_paragraph(section)
        if paragraph:
            return paragraph
    if fallback:
        return "\n".join(f"- {line}" for line in fallback)
    return None


def format_deliverables(sections: dict[str, str]) -> str:
    match = find_section_entry(
        sections,
        "technical deliverables",
        "design system deliverables",
        "deliverables",
        "review checklist",
        "report template",
        "checklist",
    )
    if not match:
        return "- Preserve the role's deliverable shape from the source material and keep outputs implementation-ready."
    section_key, section = match
    subsections = extract_subsections(section)
    if subsections:
        items = [title for title, _ in subsections[:10]]
        return "\n".join(f"- {title}" for title in items)
    bullets = extract_bullets(section)
    if bullets:
        return "\n".join(f"- {bullet}" for bullet in bullets[:10])
    paragraph = first_meaningful_paragraph(section)
    if paragraph and not paragraph.lstrip().startswith("## "):
        return paragraph
    return f"- {clean_heading_title(section_key)}"


def format_workflow(sections: dict[str, str]) -> str:
    section = find_section(
        sections,
        "workflow process",
        "mandatory process",
        "process",
        "methodology",
        "workflow",
    )
    if not section:
        return "- Follow the source role's process in order and keep the output decision-complete."
    subsections = extract_subsections(section)
    if subsections:
        lines = []
        for title, content in subsections[:12]:
            summary = first_meaningful_paragraph(content)
            if summary:
                lines.append(f"- {title}: {summary}")
            else:
                lines.append(f"- {title}")
        return "\n".join(lines)
    numbered = extract_numbered_lines(section)
    if numbered:
        return "\n".join(f"- {line}" for line in numbered[:12])
    bullets = extract_bullets(section)
    if bullets:
        return "\n".join(f"- {bullet}" for bullet in bullets[:12])
    paragraph = first_meaningful_paragraph(section)
    if paragraph:
        return paragraph
    return "- Follow the source role's process in order and keep the output decision-complete."


def compose_skill_markdown(
    *,
    slug: str,
    display_name: str,
    description: str,
    overview: str,
    responsibilities: str | None,
    guardrails: str | None,
    deliverables: str | None,
    workflow: str | None,
    working_style: str | None,
    quality_bar: str | None,
    advanced: str | None,
    source_reference: str,
    plugin_name: str,
) -> str:
    parts = [
        "---",
        f"name: {slug}",
        f"description: {description}",
        "---",
        "",
        f"# {display_name}",
        "",
        "## Overview",
        "",
        overview,
    ]

    for title, content in [
        ("Core Responsibilities", responsibilities),
        ("Guardrails", guardrails),
        ("Deliverables", deliverables),
        ("Workflow", workflow),
        ("Working Style", working_style),
        ("Quality Bar", quality_bar),
        ("Advanced Capabilities", advanced),
    ]:
        if content:
            parts.extend(["", f"## {title}", "", content])

    parts.extend(
        [
            "",
            "## References",
            "",
            f"- Original source: `./references/source.md`",
            f"- Source path: `{source_reference}`",
            f"- Plugin: `{plugin_name}`",
            "",
        ]
    )
    return "\n".join(parts)


def compose_openai_yaml(*, display_name: str, short_description: str, brand_color: str, default_prompt: str) -> str:
    return (
        "interface:\n"
        f'  display_name: "{escape_yaml(display_name)}"\n'
        f'  short_description: "{escape_yaml(short_description)}"\n'
        f'  brand_color: "{brand_color}"\n'
        f'  default_prompt: "{escape_yaml(default_prompt)}"\n'
        "\n"
        "policy:\n"
        "  allow_implicit_invocation: true\n"
    )


def write_plugin_manifest(plugin_name: str, plugin_root: Path, spec: dict[str, object]) -> None:
    icon_name = f"{plugin_name}.svg"
    manifest = {
        "name": plugin_name,
        "version": "0.1.0",
        "description": spec["short_description"],
        "author": {
            "name": "gavin",
            "email": "local@localhost",
            "url": "https://github.com/msitarzewski/agency-agents",
        },
        "homepage": "https://github.com/msitarzewski/agency-agents",
        "repository": "https://github.com/msitarzewski/agency-agents",
        "license": "MIT",
        "keywords": spec["keywords"],
        "skills": "./skills/",
        "interface": {
            "displayName": spec["display_name"],
            "shortDescription": spec["short_description"],
            "longDescription": spec["long_description"],
            "developerName": "gavin",
            "category": spec["category"],
            "capabilities": ["Interactive", "Write"],
            "websiteURL": "https://github.com/msitarzewski/agency-agents",
            "privacyPolicyURL": "https://openai.com/policies/privacy-policy/",
            "termsOfServiceURL": "https://openai.com/policies/terms-of-use/",
            "defaultPrompt": spec["default_prompts"],
            "brandColor": spec["brand_color"],
            "composerIcon": f"./assets/{icon_name}",
            "logo": f"./assets/{icon_name}",
            "screenshots": [],
        },
    }
    path = plugin_root / ".codex-plugin" / "plugin.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def write_plugin_openai_yaml(plugin_root: Path, spec: dict[str, object]) -> None:
    yaml_text = compose_openai_yaml(
        display_name=str(spec["display_name"]),
        short_description=truncate_for_ui(str(spec["short_description"]), 64),
        brand_color=str(spec["brand_color"]),
        default_prompt=str(spec["plugin_prompt"]),
    )
    (plugin_root / "agents" / "openai.yaml").write_text(yaml_text, encoding="utf-8")


def write_plugin_assets(plugin_root: Path, brand_color: str, display_name: str) -> None:
    plugin_name = plugin_root.name
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" role="img" aria-label="'
        + escape_xml(display_name)
        + '">'
        + f'<rect width="128" height="128" rx="24" fill="{brand_color}"/>'
        + '<path d="M28 36h72v12H28zm0 22h72v12H28zm0 22h72v12H28z" fill="#ffffff"/>'
        + "</svg>\n"
    )
    (plugin_root / "assets" / f"{plugin_name}.svg").write_text(svg, encoding="utf-8")


def copy_integration_references(plugin_root: Path) -> None:
    target_root = plugin_root / "references" / "integrations"
    target_root.mkdir(parents=True, exist_ok=True)
    source_root = SOURCE_ROOT / "integrations"
    for source_path in source_root.rglob("*"):
        relative = source_path.relative_to(source_root)
        target_path = target_root / relative
        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, target_path)


def find_section(sections: dict[str, str], *key_fragments: str) -> str | None:
    match = find_section_entry(sections, *key_fragments)
    if match:
        return match[1]
    return None


def find_section_entry(sections: dict[str, str], *key_fragments: str) -> tuple[str, str] | None:
    lowered = [fragment.lower() for fragment in key_fragments]
    for key, value in sections.items():
        if any(fragment in key for fragment in lowered):
            return key, value
    return None


def extract_subsections(section: str) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    current_title: str | None = None
    buffer: list[str] = []
    in_code_block = False
    for line in section.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            buffer.append(line)
            continue
        if not in_code_block and line.startswith("### "):
            if current_title is not None:
                results.append((clean_heading_title(current_title), "\n".join(buffer).strip()))
            current_title = line[4:].strip()
            buffer = []
        else:
            buffer.append(line)
    if current_title is not None:
        results.append((clean_heading_title(current_title), "\n".join(buffer).strip()))
    return results


def clean_heading_title(title: str) -> str:
    title = re.sub(r"^[0-9]+[\.\)]\s*", "", title)
    title = re.sub(r"[^\w\s/&-]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return ascii_punctuation(title)


def extract_bullets(section: str) -> list[str]:
    bullets = []
    in_code_block = False
    for line in section.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            bullets.append(clean_list_item(stripped[2:]))
        elif stripped.startswith("* "):
            bullets.append(clean_list_item(stripped[2:]))
        elif re.match(r"^\d+\.\s+", stripped):
            bullets.append(clean_list_item(re.sub(r"^\d+\.\s+", "", stripped)))
    return [bullet for bullet in bullets if bullet]


def extract_numbered_lines(section: str) -> list[str]:
    lines = []
    in_code_block = False
    for line in section.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        stripped = line.strip()
        if re.match(r"^\d+\.\s+", stripped):
            lines.append(clean_list_item(re.sub(r"^\d+\.\s+", "", stripped)))
    return [line for line in lines if line]


def clean_list_item(text: str) -> str:
    text = re.sub(r"`", "'", text)
    text = re.sub(r"\s+", " ", text).strip()
    return ascii_punctuation(text)


def first_meaningful_paragraph(section: str) -> str | None:
    paragraphs = [re.sub(r"\s+", " ", part).strip() for part in section.split("\n\n")]
    for paragraph in paragraphs:
        if paragraph and not paragraph.startswith("```") and not paragraph.startswith("### "):
            return ascii_punctuation(paragraph)
    return None


def make_skill_description(source_description: str, display_name: str, category: str) -> str:
    description = source_description.strip()
    if " - " in description:
        left, right = description.split(" - ", 1)
        if len(left.split()) <= 6 and re.match(
            r"^(masters|builds|designs|creates|optimizes|delivers|handles|focuses|specializes|architects)\b",
            right,
            flags=re.I,
        ):
            description = right.strip()
    if not description:
        description = f"the user needs {display_name.lower()} support"
    description = re.sub(r"^(masters|builds|designs|creates|optimizes|delivers|handles)\s+", "", description, flags=re.I)
    if description:
        description = description[0].lower() + description[1:]
    if description.endswith("."):
        description = description[:-1]
    first_word = description.split(" ", 1)[0].lower() if description else ""
    verb_starts = {
        "stops",
        "reviews",
        "provides",
        "maps",
        "ensures",
        "routes",
        "enforces",
        "guides",
        "turns",
    }
    if first_word in verb_starts:
        return f"Use when the task calls for a role that {description} in the {category} domain."
    return f"Use when the task calls for {description} in the {category} domain."


def titleize(slug: str) -> str:
    return " ".join(word.capitalize() for word in slug.replace("-", " ").split())


def truncate_for_ui(text: str, max_len: int) -> str:
    text = ascii_punctuation(re.sub(r"\s+", " ", text).strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def escape_yaml(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def ascii_punctuation(text: str) -> str:
    return (
        text.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2026", "...")
        .replace("\u274c", "X")
    )


if __name__ == "__main__":
    main()
