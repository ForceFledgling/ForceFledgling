# ----------------------------------------------------------------------
# Documentation macroses
# ----------------------------------------------------------------------

# Python modules
import os
from collections import defaultdict
import json
import glob
import logging
from typing import List, Dict

ROOT = os.getcwd()
PROFILES_ROOT = os.path.join(ROOT, "sa", "profiles")
DOC_ROOT = os.path.join(ROOT, "docs")
COLLECTIONS_ROOT = os.path.join(ROOT, "collections")

logger = logging.getLogger("mkdocs")
logger.info("[NotiLog] - Initializing NotiLog macroses")
logger.info("[NotiLog] - Current directory: %s", ROOT)
logger.info("[NotiLog] - Profiles root: %s", PROFILES_ROOT)
logger.info("[NotiLog] - Docs root: %s", DOC_ROOT)
logger.info("[NotiLog] - Collections root: %s", COLLECTIONS_ROOT)


def define_env(env):
    YES = ":material-check:"
    NO = ":material-close:"

    def load_scripts() -> None:
        nonlocal scripts
        if scripts:
            return
        # Load list of all scripts
        scripts = list(
            sorted(
                x.split(".", 1)[0]
                for x in os.listdir(os.path.join(DOC_ROOT, "scripts-reference"))
                if x.endswith(".md") and not x.startswith(".") and not x.startswith("index.")
            )
        )

    def check_exists(path: str):
        if os.path.exists(path):
            return
        cwd = os.getcwd()
        logger.error("[NotiLog] Path doesn't exists: %s", path)
        logger.error("[NotiLog] Current directory: %s", cwd)
        logger.error("[NotiLog] Current directory list: %s", ", ".join(os.listdir(cwd)))
        raise FileNotFoundError(path)

    @env.macro
    def show_highlights(items: List[Dict[str, str]]) -> str:
        r = [
            "<section class='notilog-highlights-section'>",
            # "<div class='dark-mask'></div>",
            "<div class='notilog-highlights'>",
        ]
        for item in items:
            r += [
                "<div class='item'>",
                f"<div class='title'>{item['title']}</div>",
                f"<div class='text'>{item['description']}</div>",
                f"<div class='link'><a href='highlights/{item['link']}/'>Подробнее</a></div>",
                "</div>",
            ]
        r += ["</div>", "</section>"]
        return "\n".join(r)

    @env.macro
    def ui_path(*args: List[str]) -> str:
        """
        Renders neat UI path in form `ARG1 > ARG2 > ARG3`
        """
        return " > ".join(f"`{x}`" for x in args)

    @env.macro
    def ui_button(title: str) -> str:
        """
        Renders neat UI button.
        """
        return f"`{title}`"

    scripts = []  # Ordered list of scripts
    platforms = defaultdict(set)  # vendor -> {platform}
    script_profiles = defaultdict(set)  # script -> {profile}