import os
import re
import unittest
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import unquote, urlsplit


REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_FILES = (
    "index.html",
    "styles.css",
    "script.js",
    ".nojekyll",
    "README.md",
)
TITLE = "MirrorWorld: Taming Video Diffusion Models for Mirror Reflection Generation"
SUBTITLE = "Taming Video Diffusion Models for Mirror Reflection Generation"
AUTHORS = (
    "Youjun Zhao",
    "Alex Warren",
    "Gary K.L. Tam",
    "Rynson W.H. Lau",
)
SECTION_IDS = ("overview", "method", "results", "bibtex")
CODE_URL = "https://github.com/YoujunZhao/MirrorWorld"
PROJECT_URL = "https://youjunzhao.github.io/MirrorWorld/"
MAX_FILE_BYTES = 100 * 1024 * 1024


@dataclass
class ParsedElement:
    index: int
    tag: str
    attrs: Dict[str, str | None]
    ancestor_indices: Tuple[int, ...] = ()
    ancestor_class_tokens: Tuple[str, ...] = ()
    text_parts: List[str] = field(default_factory=list)

    @property
    def normalized_text(self) -> str:
        return normalize_whitespace("".join(self.text_parts))


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class SiteHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: List[ParsedElement] = []
        self._stack: List[ParsedElement] = []
        self.section_ids: set[str] = set()
        self.local_src_refs: List[Tuple[str, str]] = []
        self.video_attrs: List[Dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]) -> None:
        self._register_element(tag, attrs, push=True)

    def handle_startendtag(self, tag: str, attrs: List[Tuple[str, str | None]]) -> None:
        self._register_element(tag, attrs, push=False)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                break

    def handle_data(self, data: str) -> None:
        for element in self._stack:
            element.text_parts.append(data)

    def _register_element(
        self,
        tag: str,
        attrs: List[Tuple[str, str | None]],
        *,
        push: bool,
    ) -> None:
        attr_map = dict(attrs)
        element_index = len(self.elements)
        ancestor_indices = tuple(ancestor.index for ancestor in self._stack)
        ancestor_class_tokens = tuple(
            class_name
            for ancestor in self._stack
            for class_name in (ancestor.attrs.get("class") or "").split()
        )
        element = ParsedElement(
            index=element_index,
            tag=tag,
            attrs=attr_map,
            ancestor_indices=ancestor_indices,
            ancestor_class_tokens=ancestor_class_tokens,
        )
        self.elements.append(element)
        if push:
            self._stack.append(element)
        element_id = attr_map.get("id")
        if element_id:
            self.section_ids.add(element_id)
        src_value = attr_map.get("src")
        if src_value and is_local_reference(src_value):
            self.local_src_refs.append((tag, src_value))
        if tag == "video":
            self.video_attrs.append(attr_map)


def is_local_reference(value: str) -> bool:
    if not value:
        return False
    if value.startswith(("#", "data:", "javascript:", "mailto:", "tel:")):
        return False
    parsed = urlsplit(value)
    return not parsed.scheme and not parsed.netloc and bool(parsed.path)


def resolve_local_reference(reference: str) -> Path:
    parsed = urlsplit(reference)
    relative_path = unquote(parsed.path.lstrip("/"))
    resolved = (REPO_ROOT / relative_path).resolve()
    repo_root = REPO_ROOT.resolve()
    resolved.relative_to(repo_root)
    return resolved


class SiteContractTests(unittest.TestCase):
    maxDiff = None

    def extract_css_block(self, source: str, selector_pattern: str) -> str:
        selector_match = re.search(selector_pattern, source, flags=re.DOTALL)
        self.assertIsNotNone(selector_match, f"Could not find CSS selector: {selector_pattern}")

        opening_brace_index = source.find("{", selector_match.end())
        self.assertNotEqual(opening_brace_index, -1, f"Missing opening brace for selector: {selector_pattern}")

        depth = 0
        for index in range(opening_brace_index, len(source)):
            character = source[index]
            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    return source[opening_brace_index + 1:index]

        self.fail(f"Missing closing brace for selector: {selector_pattern}")

    def read_required_text(self, relative_path: str) -> str:
        path = REPO_ROOT / relative_path
        if not path.is_file():
            self.skipTest(f"{relative_path} is missing; content checks run after the page files exist")
        return path.read_text(encoding="utf-8")

    def parse_index(self) -> tuple[str, SiteHTMLParser]:
        html = self.read_required_text("index.html")
        parser = SiteHTMLParser()
        parser.feed(html)
        parser.close()
        return html, parser

    def descendants_of(self, parser: SiteHTMLParser, ancestor: ParsedElement) -> List[ParsedElement]:
        return [
            element
            for element in parser.elements
            if ancestor.index in element.ancestor_indices
        ]

    def find_overview_task_article(self, parser: SiteHTMLParser) -> ParsedElement:
        overview_sections = [
            element
            for element in parser.elements
            if element.tag == "section" and element.attrs.get("id") == "overview"
        ]
        self.assertEqual(len(overview_sections), 1, "Expected exactly one #overview section")
        overview_section = overview_sections[0]

        overview_task_articles = [
            element
            for element in parser.elements
            if element.tag == "article"
            and "overview-task" in (element.attrs.get("class") or "").split()
            and overview_section.index in element.ancestor_indices
        ]
        self.assertEqual(
            len(overview_task_articles),
            1,
            "Expected exactly one article.overview-task inside #overview",
        )
        return overview_task_articles[0]

    def test_required_production_files_exist(self) -> None:
        missing_files = [path for path in PRODUCTION_FILES if not (REPO_ROOT / path).is_file()]
        self.assertEqual(
            missing_files,
            [],
            f"Missing required production files: {', '.join(missing_files)}",
        )

    def test_index_includes_required_metadata_and_sections(self) -> None:
        html, parser = self.parse_index()

        self.assertRegex(
            html,
            re.compile(rf"<title>\s*{re.escape(TITLE)}\s*</title>", re.IGNORECASE),
        )
        self.assertIn(TITLE, html)
        for author in AUTHORS:
            self.assertIn(author, html, f"Missing author in index.html: {author}")
        missing_section_ids = [section_id for section_id in SECTION_IDS if section_id not in parser.section_ids]
        self.assertEqual(
            missing_section_ids,
            [],
            f"Missing required section ids: {', '.join(missing_section_ids)}",
        )
        self.assertIn(CODE_URL, html)

    def test_centered_hero_exposes_research_links_in_order(self) -> None:
        html, parser = self.parse_index()

        hero_sections = [
            element
            for element in parser.elements
            if element.tag == "section"
            and {"hero", "hero-stage"}.issubset(set((element.attrs.get("class") or "").split()))
        ]
        self.assertEqual(len(hero_sections), 1, "Expected exactly one hero section with hero and hero-stage classes")
        hero_section = hero_sections[0]
        hero_descendants = self.descendants_of(parser, hero_section)
        self.assertNotIn("id", hero_section.attrs)
        self.assertNotIn("data-section", hero_section.attrs)

        subtitles = [
            element
            for element in hero_descendants
            if "title-subtitle" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(subtitles), 1, "Expected one unbroken subtitle element")
        self.assertEqual(subtitles[0].normalized_text, SUBTITLE)
        self.assertNotIn("Video mirror reflection generation", html)

        hero_links = [
            element
            for element in hero_descendants
            if element.tag == "a"
            and "button" in (element.attrs.get("class") or "").split()
        ]
        self.assertGreaterEqual(len(hero_links), 3)
        self.assertEqual(
            [item.normalized_text for item in hero_links[:3]],
            ["Arxiv", "Code", "Hugging Face"],
        )
        self.assertEqual(
            [item.attrs.get("href") for item in hero_links[:3]],
            ["https://arxiv.org/abs/2608.07463", CODE_URL, PROJECT_URL],
        )
        self.assertTrue(
            all("button-primary" in (item.attrs.get("class") or "").split() for item in hero_links[:3]),
            "Arxiv, Code, and Hugging Face must share the same bordered button treatment",
        )

        hero_videos = [
            element
            for element in hero_descendants
            if element.tag == "video"
            and {"hero-background-video", "ambient-video"}.issubset(
                set((element.attrs.get("class") or "").split())
            )
        ]
        self.assertEqual(len(hero_videos), 1, "Expected exactly one ambient hero background video")
        hero_video = hero_videos[0]
        self.assertEqual(hero_video.attrs.get("src"), "static/videos/hero/mirrorworld-hero-mosaic.mp4")
        for attr_name in ("muted", "loop", "playsinline"):
            self.assertIn(attr_name, hero_video.attrs, f"Hero background video must include {attr_name}")
        self.assertNotIn(
            "autoplay",
            hero_video.attrs,
            "Hero autoplay must be gated by the initial reduced-motion preference in JavaScript",
        )
        self.assertEqual(hero_video.attrs.get("preload"), "auto")
        self.assertEqual(hero_video.attrs.get("aria-hidden"), "true")
        self.assertNotIn("controls", hero_video.attrs)

        hero_scrims = [
            element
            for element in hero_descendants
            if "hero-video-scrim" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(hero_scrims), 1, "Expected exactly one hero-video-scrim inside the hero")
        hero_scrim = hero_scrims[0]
        self.assertEqual(hero_scrim.attrs.get("aria-hidden"), "true")

        hero_copies = [
            element
            for element in hero_descendants
            if "hero-copy" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(hero_copies), 1, "Expected exactly one hero-copy inside the hero")
        hero_copy = hero_copies[0]
        self.assertLess(
            hero_video.index,
            hero_scrim.index,
            "Hero background video must come before the scrim",
        )
        self.assertLess(
            hero_scrim.index,
            hero_copy.index,
            "Hero scrim must come before the hero copy block",
        )

    def test_hero_video_uses_approved_glass_and_opacity_contract(self) -> None:
        css = self.read_required_text("styles.css")
        script = self.read_required_text("script.js")

        hero_rule = self.extract_css_block(css, r"(?m)^\s*\.hero-stage\s*(?=\{)")
        self.assertRegex(
            hero_rule,
            re.compile(r"min-height:\s*calc\(100svh\s*-\s*var\(--header-height\)\)\s*;"),
        )
        self.assertRegex(hero_rule, re.compile(r"overflow:\s*hidden\s*;"))

        video_rule = self.extract_css_block(css, r"(?m)^\s*\.hero-background-video\s*(?=\{)")
        self.assertRegex(video_rule, re.compile(r"object-fit:\s*cover\s*;"))
        self.assertRegex(video_rule, re.compile(r"opacity:\s*0\.34\s*;"))

        copy_rule = self.extract_css_block(css, r"(?m)^\s*\.hero-copy\s*(?=\{)")
        self.assertRegex(
            copy_rule,
            re.compile(r"background:\s*rgba\(8,\s*8,\s*12,\s*0\.64\)\s*;"),
        )
        self.assertRegex(copy_rule, re.compile(r"backdrop-filter:\s*blur\(15px\)"))

        reduced_motion_block = self.extract_css_block(
            css,
            r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*",
        )
        reduced_motion_video_rule = re.search(
            r"\.hero-background-video\s*\{(?P<body>.*?)\}",
            reduced_motion_block,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(reduced_motion_video_rule)
        self.assertRegex(
            reduced_motion_video_rule.group("body"),
            re.compile(r"opacity:\s*0\.28\s*;"),
        )

        reduced_motion_listener = re.search(
            r"reducedMotion\.addEventListener\(\s*['\"]change['\"]\s*,\s*"
            r"(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>\s*\{(?P<body>.*?)\}\s*\)",
            script,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(reduced_motion_listener)
        listener_body = reduced_motion_listener.group("body")
        self.assertRegex(
            listener_body,
            re.compile(r"document\.querySelectorAll\(\s*['\"]\.ambient-video['\"]\s*\)"),
        )
        self.assertRegex(
            listener_body,
            re.compile(r"pauseVideos\(\s*[A-Za-z_$][\w$]*\s*\)"),
        )
        self.assertRegex(
            script,
            re.compile(
                r"syncAmbientPlayback\(\s*ambientVideos\s*\)\s*;\s*"
                r"reducedMotion\.addEventListener",
                re.DOTALL,
            ),
        )

    def test_hero_title_uses_original_gradient_without_artistic_reflection(self) -> None:
        css = self.read_required_text("styles.css")

        hero_rule = self.extract_css_block(css, r"(?m)^\s*\.hero h1\s*(?=\{)")
        self.assertRegex(
            hero_rule,
            re.compile(r"font-family:\s*Georgia[^;]*;")
        )
        self.assertRegex(hero_rule, re.compile(r"font-size:\s*clamp\(\s*48px\s*,\s*7vw\s*,\s*78px\s*\)"))
        self.assertRegex(hero_rule, re.compile(r"font-weight:\s*500\s*;"))

        title_mirror_rule = self.extract_css_block(css, r"(?m)^\s*\.title-mirror\s*(?=\{)")
        self.assertRegex(title_mirror_rule, re.compile(r"display:\s*block\s*;"))
        self.assertRegex(title_mirror_rule, re.compile(r"padding-bottom:\s*6px\s*;"))
        self.assertRegex(
            title_mirror_rule,
            re.compile(
                r"background:\s*linear-gradient\(\s*100deg\s*,\s*#fff\s+6%\s*,\s*"
                r"#b9bec8\s+30%\s*,\s*#d8cdfd\s+55%\s*,\s*#b9f2f7\s+75%\s*,\s*#fff\s+94%\s*\)\s*;"
            ),
        )
        self.assertRegex(
            title_mirror_rule,
            re.compile(r"filter:\s*drop-shadow\(\s*0\s+10px\s+42px\s+rgba\(\s*167\s*,\s*139\s*,\s*250\s*,\s*0\.24\s*\)\s*\)\s*;"),
        )
        self.assertNotRegex(title_mirror_rule, re.compile(r"font-style:\s*italic"))
        self.assertNotRegex(title_mirror_rule, re.compile(r"-webkit-text-stroke\s*:"))
        self.assertNotRegex(title_mirror_rule, re.compile(r"text-shadow\s*:"))
        self.assertNotRegex(title_mirror_rule, re.compile(r"transform:\s*skewY\("))
        self.assertNotRegex(css, re.compile(r"\.title-mirror::after\s*\{"))

        mobile_block = self.extract_css_block(
            css,
            r"@media\s*\(max-width:\s*620px\)\s*",
        )
        self.assertRegex(
            mobile_block,
            re.compile(r"\.hero h1\s*\{[^}]*font-size:\s*clamp\(\s*44px\s*,\s*13vw\s*,\s*64px\s*\)", re.DOTALL),
        )
        self.assertNotRegex(mobile_block, re.compile(r"\.title-mirror(?:::after)?\s*\{"))

    def test_compact_mobile_navigation_fits_without_initial_horizontal_clipping(self) -> None:
        css = self.read_required_text("styles.css")
        compact_block = self.extract_css_block(
            css,
            r"@media\s*\(max-width:\s*420px\)\s*",
        )
        self.assertRegex(compact_block, re.compile(r"\.nav-shell\s*\{[^}]*gap:\s*4px", re.DOTALL))
        self.assertRegex(
            compact_block,
            re.compile(
                r"\.nav-links\s*\{[^}]*flex:\s*1[^}]*justify-content:\s*flex-end[^}]*gap:\s*0",
                re.DOTALL,
            ),
        )
        self.assertRegex(
            compact_block,
            re.compile(
                r"\.nav-links\s+a\s*\{[^}]*padding-inline:\s*3px[^}]*font-size:\s*10px",
                re.DOTALL,
            ),
        )

    def test_home_and_back_to_top_links_target_dedicated_top_anchor(self) -> None:
        _, parser = self.parse_index()

        top_targets = [
            element
            for element in parser.elements
            if element.tag == "body" and element.attrs.get("id") == "top"
        ]
        self.assertEqual(len(top_targets), 1, "Expected the page to expose a dedicated #top anchor")

        home_wordmarks = [
            element
            for element in parser.elements
            if element.tag == "a"
            and "wordmark" in (element.attrs.get("class") or "").split()
        ]
        self.assertGreaterEqual(len(home_wordmarks), 2)

        header_wordmark = next(
            (
                element
                for element in home_wordmarks
                if "footer-mark" not in (element.attrs.get("class") or "").split()
            ),
            None,
        )
        self.assertIsNotNone(header_wordmark)
        self.assertEqual(header_wordmark.attrs.get("href"), "#top")
        self.assertEqual(header_wordmark.attrs.get("aria-label"), "MirrorWorld home")

        footer_wordmark = next(
            (
                element
                for element in home_wordmarks
                if "footer-mark" in (element.attrs.get("class") or "").split()
            ),
            None,
        )
        self.assertIsNotNone(footer_wordmark)
        self.assertEqual(footer_wordmark.attrs.get("href"), "#top")

        back_to_top_links = [
            element
            for element in parser.elements
            if element.tag == "a"
            and "back-to-top" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(back_to_top_links), 1)
        self.assertEqual(back_to_top_links[0].attrs.get("href"), "#top")

        overview_nav_links = [
            element
            for element in parser.elements
            if element.tag == "a"
            and "data-nav-link" in element.attrs
            and element.normalized_text == "Overview"
        ]
        self.assertEqual(len(overview_nav_links), 1)
        self.assertEqual(overview_nav_links[0].attrs.get("href"), "#overview")

    def test_index_exposes_bibtex_entry(self) -> None:
        _, parser = self.parse_index()

        bibtex_sections = [
            element for element in parser.elements if element.attrs.get("id") == "bibtex"
        ]
        self.assertTrue(bibtex_sections, "Expected an element with id='bibtex'")
        self.assertTrue(
            any("arXiv" in element.normalized_text for element in bibtex_sections),
            "Expected the BibTeX section to contain the arXiv entry",
        )
        bibtex_text = " ".join(element.normalized_text for element in bibtex_sections)
        self.assertIn("@article{zhao2026mirrorworld,", bibtex_text)
        self.assertIn("journal={arXiv preprint arXiv:2608.07463}", bibtex_text)

    def test_overview_pairs_abstract_before_task_demo(self) -> None:
        _, parser = self.parse_index()

        overview_sections = [
            element
            for element in parser.elements
            if element.tag == "section" and element.attrs.get("id") == "overview"
        ]
        self.assertEqual(len(overview_sections), 1)

        overview_classes = (overview_sections[0].attrs.get("class") or "").split()
        self.assertIn("project-overview", overview_classes)

        overview_text = overview_sections[0].normalized_text
        self.assertIn("Abstract", overview_text)
        self.assertIn("The task", overview_text)
        self.assertIn("From a masked mirror to a faithful reflection.", overview_text)
        self.assertLess(overview_text.find("Abstract"), overview_text.find("The task"))
        self.assertLess(
            overview_text.find("The task"),
            overview_text.find("From a masked mirror to a faithful reflection."),
        )

        legacy_section_classes = [
            element.attrs.get("class") or ""
            for element in parser.elements
            if element.tag == "section"
        ]
        self.assertFalse(
            any("abstract" in classes.split() for classes in legacy_section_classes),
            "Abstract must live inside the overview section rather than a standalone .abstract section",
        )
        self.assertFalse(
            any("task-demo" in classes.split() for classes in legacy_section_classes),
            "The task demo must move into the overview section instead of a standalone .task-demo section",
        )

    def test_complete_abstract_is_highlighted(self) -> None:
        _, parser = self.parse_index()

        abstract_sections = [
            element
            for element in parser.elements
            if "overview-abstract" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(abstract_sections), 1)
        abstract_text = abstract_sections[0].normalized_text
        self.assertIn(
            "Recent advances in video diffusion models (VDMs) have enabled high-fidelity video synthesis.",
            abstract_text,
        )
        self.assertIn(
            "Experimental results show that MirrorWorld achieves improved reflection reconstruction quality over representative image-based reflection generation methods and strong video inpainting baselines.",
            abstract_text,
        )

        highlighted = [
            element.normalized_text
            for element in parser.elements
            if element.tag == "mark"
            and "overview-abstract" in element.ancestor_class_tokens
        ]
        self.assertGreaterEqual(len(highlighted), 5)
        for phrase in (
            "MirrorWorld",
            "Semantic Relation Distillation (SRD)",
            "what should be reflected",
            "Geometric Transformation Alignment (GTA)",
            "how it should be arranged",
        ):
            self.assertTrue(
                any(phrase in item for item in highlighted),
                f"Expected highlighted abstract phrase: {phrase}",
            )
        self.assertFalse(
            any("benchmark for video mirror reflection generation" in item for item in highlighted),
            "The benchmark sentence should remain regular-weight text",
        )
        self.assertFalse(
            any("Experimental results show that MirrorWorld achieves improved reflection reconstruction quality" in item for item in highlighted),
            "The experimental-results sentence should remain regular-weight text",
        )

    def test_qualitative_comparison_uses_method_columns_and_scene_rows(self) -> None:
        _, parser = self.parse_index()
        results_sections = [
            element
            for element in parser.elements
            if element.tag == "section" and element.attrs.get("id") == "results"
        ]
        self.assertEqual(len(results_sections), 1)
        results_section = results_sections[0]
        results_text = results_section.normalized_text

        self.assertIn("From Implausible to Plausible", results_text)
        self.assertNotIn("Wan2.2-A14B", results_text)
        self.assertNotIn("Hover an input frame to read its full prompt.", results_text)
        self.assertNotIn("Case 01", results_text)
        self.assertNotIn("Case 02", results_text)
        self.assertNotIn("Figure 2", results_text)
        self.assertNotIn("Scene 0232", results_text)
        self.assertNotIn("Scene 0084", results_text)
        self.assertNotIn("Example A", results_text)
        self.assertNotIn("Example B", results_text)

        result_descendants = self.descendants_of(parser, results_section)
        boards = [
            element
            for element in result_descendants
            if element.tag == "article"
            and "comparison-board" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(boards), 1)
        board_descendants = self.descendants_of(parser, boards[0])

        method_rows = [
            element
            for element in board_descendants
            if element.tag == "div" and "comparison-method-row" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(method_rows), 6)
        self.assertEqual(
            [
                len([
                    element
                    for element in self.descendants_of(parser, method_row)
                    if element.tag == "video"
                ])
                for method_row in method_rows
            ],
            [2, 2, 2, 2, 2, 2],
        )

        method_labels = [
            element
            for element in board_descendants
            if element.tag == "div"
            and "comparison-method-label" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(
            [element.normalized_text for element in method_labels],
            [
                "Input videowith mask",
                "MirrorFusionImage-based",
                "MirrorVerseImage-based",
                "VideoPainterVideo inpainting",
                "VACEVideo inpainting",
                "MirrorWorldOurs",
            ],
        )

        css = self.read_required_text("styles.css")
        self.assertNotIn("prompt-tooltip", css)
        self.assertNotIn("vace-box", css)
        self.assertIn("border-width: 3px;", css)

    def test_task_demo_uses_four_captioned_independent_videos(self) -> None:
        _, parser = self.parse_index()
        overview_task_article = self.find_overview_task_article(parser)
        overview_task_descendants = self.descendants_of(parser, overview_task_article)

        task_video_grids = [
            element
            for element in overview_task_descendants
            if element.tag == "div"
            and "task-video-grid" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(task_video_grids), 1, "Expected one task-video-grid inside the overview task article")
        task_video_grid = task_video_grids[0]
        self.assertEqual(task_video_grid.attrs.get("data-video-group"), "overview-task")
        self.assertEqual(task_video_grid.attrs.get("role"), "group")
        self.assertEqual(
            task_video_grid.attrs.get("aria-label"),
            "Two task examples comparing masked inputs and generated videos",
        )
        task_video_grid_descendants = self.descendants_of(parser, task_video_grid)

        task_video_cards = [
            element
            for element in task_video_grid_descendants
            if element.tag == "figure"
            and "task-video-card" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(task_video_cards), 4)

        task_captions = [
            element
            for element in task_video_grid_descendants
            if element.tag == "figcaption"
            and any(card.index in element.ancestor_indices for card in task_video_cards)
        ]
        self.assertEqual(
            [element.normalized_text for element in task_captions],
            [
                "Input video with mask",
                "Generated Reflection",
                "Input video with mask",
                "Generated Reflection",
            ],
        )

        task_videos = [
            element
            for element in task_video_grid_descendants
            if element.tag == "video"
            and any(card.index in element.ancestor_indices for card in task_video_cards)
        ]
        self.assertEqual(
            [element.attrs.get("src") for element in task_videos],
            [
                "static/videos/task/vmdd-080-mask.mp4",
                "static/videos/showcase/figure-g-vmdd-080.mp4",
                "static/videos/task/scene0084-01-mask.mp4",
                "static/videos/showcase/figure-d-scene0084-01.mp4",
            ],
        )
        self.assertEqual(
            [element.attrs.get("aria-label") for element in task_videos],
            [
                "Masked input video for the first task example",
                "Generated video for the first task example",
                "Masked input video for the second task example",
                "Generated video for the second task example",
            ],
        )
        for element in task_videos:
            for attr_name in ("controls", "autoplay", "muted", "loop", "playsinline"):
                self.assertIn(
                    attr_name,
                    element.attrs,
                    f"Expected every overview task video to include {attr_name}",
                )

        for task_video_card in task_video_cards:
            scoped_elements = self.descendants_of(parser, task_video_card)
            figure_captions = [element for element in scoped_elements if element.tag == "figcaption"]
            figure_videos = [element for element in scoped_elements if element.tag == "video"]
            self.assertEqual(len(figure_captions), 1, "Each task video card must contain one figcaption")
            self.assertEqual(len(figure_videos), 1, "Each task video card must contain one video")
            self.assertLess(
                scoped_elements.index(figure_captions[0]),
                scoped_elements.index(figure_videos[0]),
                "Each task video card must place its figcaption before its video",
            )

        mosaic_sources = [
            element.attrs.get("src")
            for element in overview_task_descendants
            if element.tag == "video"
        ]
        self.assertNotIn("static/videos/task/task-mosaic.mp4", mosaic_sources)
        self.assertFalse(
            any("mosaic-label" in (element.attrs.get("class") or "").split() for element in overview_task_descendants),
            "The overview task subtree must not contain any .mosaic-label elements",
        )

    def test_key_demo_pairs_are_user_controllable(self) -> None:
        _, parser = self.parse_index()

        paired_sources = (
            "static/videos/task/scene0268-mask.mp4",
            "static/videos/showcase/figure-e-scene0268.mp4",
            "static/videos/task/bathroom-0002-mask.mp4",
            "static/videos/showcase/figure-f-bathroom.mp4",
            "static/videos/task/zoom-vid42-mask.mp4",
            "static/videos/showcase/figure-g-zoom-vid42.mp4",
            "static/videos/task/scene0083-mask.mp4",
            "static/videos/showcase/figure-f-scene0083.mp4",
            "static/videos/task/scene0165-mask.mp4",
            "static/videos/showcase/figure-f-scene0165.mp4",
            "static/videos/task/vmdd-015-mask.mp4",
            "static/videos/showcase/figure-g-vmdd-015.mp4",
        )
        paired_videos = [
            attrs
            for attrs in parser.video_attrs
            if any((attrs.get("src") or "").startswith(source) for source in paired_sources)
        ]
        self.assertEqual(len(paired_videos), len(paired_sources))
        self.assertTrue(
            all(
                {
                    "muted",
                    "loop",
                    "playsinline",
                }.issubset(attrs)
                and "video-slider-video" in (attrs.get("class") or "").split()
                for attrs in paired_videos
            ),
            "Every paired demo video must be a muted looping slider layer",
        )

        slider_handles = [
            element
            for element in parser.elements
            if element.tag == "button"
            and "video-slider-handle" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(slider_handles), 9)

    def test_result_tiers_use_caption_free_uniform_media(self) -> None:
        html, parser = self.parse_index()

        comparison_labels = [
            element.normalized_text
            for element in parser.elements
            if element.tag == "span"
            and "video-slider-label" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(comparison_labels, ["Input", "Reflection"] * 9)
        self.assertNotIn("Input video with mask", comparison_labels)
        self.assertNotIn("Generated video", comparison_labels)

        css = self.read_required_text("styles.css")
        self.assertRegex(css, re.compile(r"\.video-slider-stage:hover \.video-slider-label"))
        self.assertRegex(css, re.compile(r"\.video-slider-stage:hover::after"))
        self.assertRegex(css, re.compile(r"background:\s*rgba\(0,\s*0,\s*0,\s*0\.5\)"))
        self.assertRegex(css, re.compile(r"background:\s*rgba\(255,\s*255,\s*255,\s*0\.2\)"))
        self.assertRegex(css, re.compile(r"border-radius:\s*2px;"))
        self.assertNotRegex(css, re.compile(r"\.video-slider-label\s*\{[^}]*text-transform", flags=re.DOTALL))

        generated_pairs = [
            element
            for element in parser.elements
            if "generated-pair" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(generated_pairs), 6)
        for path in (
            "static/videos/task/scene0268-mask.mp4",
            "static/videos/showcase/figure-e-scene0268.mp4",
            "static/videos/task/bathroom-0002-mask.mp4",
            "static/videos/showcase/figure-f-bathroom.mp4",
            "static/videos/task/zoom-vid42-mask.mp4",
            "static/videos/showcase/figure-g-zoom-vid42.mp4",
            "static/videos/task/more-mirrorworld/bedroom-0096-part001-mask.mp4",
            "static/videos/showcase/more-mirrorworld/bedroom-0096-part001.mp4",
            "static/videos/task/more-mirrorworld/scene-0268-01-01-part001-mask.mp4",
            "static/videos/showcase/more-mirrorworld/scene-0268-01-01-part001.mp4",
            "static/videos/task/more-mirrorworld/scene-0051-03-00-mask.mp4",
            "static/videos/showcase/more-mirrorworld/scene-0051-03-00.mp4",
        ):
            self.assertIn(path, html)

        mirror_pairs = [
            element
            for element in parser.elements
            if "mirror-pair" in (element.attrs.get("class") or "").split()
        ]
        self.assertEqual(len(mirror_pairs), 3)
        for path in (
            "static/videos/task/scene0083-mask.mp4",
            "static/videos/showcase/figure-f-scene0083.mp4",
            "static/videos/task/scene0165-mask.mp4",
            "static/videos/showcase/figure-f-scene0165.mp4",
            "static/videos/task/vmdd-015-mask.mp4",
            "static/videos/showcase/figure-g-vmdd-015.mp4",
        ):
            self.assertIn(path, html)

    def test_worldwarp_spacing_and_paper_abstract_typography(self) -> None:
        css = self.read_required_text("styles.css")

        self.assertRegex(css, re.compile(r"--max:\s*1040px\s*;"))
        self.assertRegex(css, re.compile(r"--max-wide:\s*1140px\s*;"))
        html_rule = re.search(
            r"html\s*\{(?P<body>.*?)\}",
            css,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(html_rule)
        self.assertRegex(html_rule.group("body"), re.compile(r"overflow-x:\s*clip\s*;"))
        abstract_rule = re.search(
            r"\.full-abstract\s*\{(?P<body>.*?)\}",
            css,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(abstract_rule)
        abstract_body = abstract_rule.group("body")
        self.assertRegex(abstract_body, re.compile(r"text-align:\s*left\s*;"))
        self.assertRegex(abstract_body, re.compile(r"font-size:\s*16px\s*;"))

    def test_overview_uses_reference_style_grid_and_mobile_stack(self) -> None:
        css = self.read_required_text("styles.css")

        project_overview_rule = re.search(
            r"\.project-overview\s*\{(?P<body>.*?)\}",
            css,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(project_overview_rule)
        project_overview_body = project_overview_rule.group("body")
        self.assertRegex(project_overview_body, re.compile(r"position:\s*relative\s*;"))
        self.assertRegex(
            project_overview_body,
            re.compile(r"padding-block:\s*clamp\(88px,\s*10vw,\s*132px\)\s*;"),
        )
        self.assertRegex(project_overview_body, re.compile(r"border-top:\s*1px\s+solid\s+var\(--line\)\s*;"))
        self.assertNotRegex(project_overview_body, re.compile(r"\bborder-radius\s*:"))
        self.assertNotRegex(project_overview_body, re.compile(r"\bbox-shadow\s*:"))
        self.assertNotRegex(project_overview_body, re.compile(r"\bbackground\s*:"))
        self.assertNotRegex(project_overview_body, re.compile(r"\bpadding\s*:"))

        project_overview_before_rule = re.search(
            r"\.project-overview::before\s*\{(?P<body>.*?)\}",
            css,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(project_overview_before_rule)
        self.assertRegex(
            project_overview_before_rule.group("body"),
            re.compile(
                r"inset:\s*0\s+calc\(50%\s*-\s*50vw\)\s*;.*background:\s*radial-gradient\(circle\s+at\s+72%\s+42%,\s*rgba\(167,\s*139,\s*250,\s*\.09\),\s*transparent\s+34rem\)\s*;",
                re.DOTALL,
            ),
        )

        overview_columns_rule = re.search(
            r"\.overview-columns\s*\{(?P<body>.*?)\}",
            css,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(overview_columns_rule)
        self.assertRegex(
            overview_columns_rule.group("body"),
            re.compile(
                r"grid-template-columns:\s*minmax\(0,\s*3fr\)\s+minmax\(0,\s*2fr\)\s*;"
            ),
        )

        tablet_block = self.extract_css_block(
            css,
            r"@media\s*\(max-width:\s*820px\)\s*",
        )
        tablet_overview_columns_rule = re.search(
            r"\.overview-columns\s*\{(?P<body>.*?)\}",
            tablet_block,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(tablet_overview_columns_rule)
        self.assertRegex(
            tablet_overview_columns_rule.group("body"),
            re.compile(r"grid-template-columns:\s*1fr\s*;"),
        )

        task_video_grid_rule = re.search(
            r"\.task-video-grid\s*\{(?P<body>.*?)\}",
            css,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(task_video_grid_rule)
        self.assertRegex(
            task_video_grid_rule.group("body"),
            re.compile(r"grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)\s*;"),
        )

        task_video_card_video_rule = re.search(
            r"\.task-video-card video\s*\{(?P<body>.*?)\}",
            css,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(task_video_card_video_rule)
        self.assertRegex(
            task_video_card_video_rule.group("body"),
            re.compile(r"aspect-ratio:\s*16\s*/\s*9\s*;"),
        )
        self.assertRegex(
            task_video_card_video_rule.group("body"),
            re.compile(r"object-fit:\s*fill\s*;"),
        )

        mobile_block = self.extract_css_block(
            css,
            r"@media\s*\(max-width:\s*620px\)\s*",
        )
        mobile_task_video_grid_rule = re.search(
            r"\.task-video-grid\s*\{(?P<body>.*?)\}",
            mobile_block,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(mobile_task_video_grid_rule)
        self.assertRegex(
            mobile_task_video_grid_rule.group("body"),
            re.compile(r"grid-template-columns:\s*1fr\s*;"),
        )

    def test_local_html_src_references_resolve_within_repo(self) -> None:
        _, parser = self.parse_index()

        self.assertTrue(parser.local_src_refs, "Expected index.html to reference at least one local src asset")
        missing_assets = []
        escaped_assets = []
        for tag, reference in parser.local_src_refs:
            try:
                asset_path = resolve_local_reference(reference)
            except ValueError:
                escaped_assets.append(f"{tag}:{reference}")
                continue
            if not asset_path.is_file():
                missing_assets.append(f"{tag}:{reference}")
        self.assertEqual(
            escaped_assets,
            [],
            f"Local src references must stay within the repository root: {', '.join(escaped_assets)}",
        )
        self.assertEqual(
            missing_assets,
            [],
            f"Missing local src assets referenced by index.html: {', '.join(missing_assets)}",
        )

    def test_every_video_is_muted_looping_and_inline(self) -> None:
        _, parser = self.parse_index()

        self.assertGreater(len(parser.video_attrs), 0, "Expected at least one <video> on the project page")
        missing_attributes = []
        required_attrs = {"muted", "loop", "playsinline"}
        for index, attrs in enumerate(parser.video_attrs, start=1):
            absent = sorted(required_attrs - set(attrs))
            if absent:
                missing_attributes.append(f"video #{index}: missing {', '.join(absent)}")
        self.assertEqual(
            missing_attributes,
            [],
            "Every video must include muted, loop, and playsinline: "
            + "; ".join(missing_attributes),
        )

    def test_no_repo_file_reaches_github_size_limit(self) -> None:
        oversize_files = []
        for current_root, dirnames, filenames in os.walk(REPO_ROOT):
            dirnames[:] = [name for name in dirnames if name != ".git" and name != "__pycache__"]
            for filename in filenames:
                path = Path(current_root, filename)
                if path.stat().st_size >= MAX_FILE_BYTES:
                    oversize_files.append(
                        f"{path.relative_to(REPO_ROOT)} ({path.stat().st_size} bytes)"
                    )
        self.assertEqual(
            oversize_files,
            [],
            "Repository files must stay below GitHub's 100 MB limit: " + "; ".join(oversize_files),
        )

    def test_readme_core_metadata_matches_project_contract(self) -> None:
        readme = self.read_required_text("README.md")

        self.assertIn(TITLE, readme)
        for author in AUTHORS:
            self.assertIn(author, readme, f"Missing author in README.md: {author}")
        self.assertIn(CODE_URL, readme)
        self.assertRegex(readme, re.compile(r"Paper.*Coming soon", re.IGNORECASE))
        self.assertIn("@article{zhao2026mirrorworld,", readme)
        self.assertIn("journal={arXiv preprint arXiv:2608.07463}", readme)


if __name__ == "__main__":
    unittest.main()
