from typing import List

from loguru import logger
from notion_client.helpers import async_collect_paginated_api as get_paginated

from inventory.container import Container, NotionClient, Provide

SUPPORTED_BLOCKS = (
    "embed",
    "bookmark",
    "image",
    "video",
    "pdf",
    "file",
    "audio",
    "code",
    "equation",
    "divider",
    "breadcrumb",
    "table_of_contents",
    "link_to_page",
    "table_row",
    "column_list",
    "column",
    "table",
    "heading_1",
    "heading_2",
    "heading_3",
    "paragraph",
    "bulleted_list_item",
    "numbered_list_item",
    "quote",
    "to_do",
    "toggle",
    "template",
    "callout",
    "synced_block",
)


async def get_full_notion_page(
    page_id: str,
    strip_for_creation: bool = False,
    notion: NotionClient = Provide[Container.notion],
):
    async def _fetch_block_children(block_id: str):
        blocks = []
        res = await get_paginated(notion.blocks.children.list, block_id=block_id)
        for block in res:
            if block["has_children"]:
                block["children"] = await _fetch_block_children(block["id"])
            else:
                block["children"] = []
            if strip_for_creation:
                block_type = block["type"]
                if block_type not in SUPPORTED_BLOCKS:
                    continue
                block = {
                    "type": block_type,
                    block_type: block[block_type],
                    "children": block["children"],
                }
            blocks.append(block)
        return blocks

    return await _fetch_block_children(page_id)


async def create_page_nested(
    children: List[dict],
    notion: NotionClient = Provide[Container.notion],
    **kwargs,
):
    logger.info("Creating page with nested blocks")
    logger.info(f"All children: {children}")
    created_page = None

    async def _commit_page(_, children):
        nonlocal created_page
        created_page = await notion.pages.create(children=children, **kwargs)
        return await get_full_notion_page(created_page["id"])

    async def _commit_block(block_id, children):
        response = await notion.blocks.children.append(block_id, children=children)
        return response["results"]

    async def _update_block_children(block_id, children, commit_func=_commit_block):
        logger.info(f"Updating children of {block_id}")
        top_level_blocks = []
        for block in children:
            block = block.copy()
            block.pop("children", [])
            top_level_blocks.append(block)
        logger.info(f"Top level blocks: {top_level_blocks}")
        populated_blocks = await commit_func(block_id, top_level_blocks)
        for block, populated_block in zip(children, populated_blocks):
            nested_children = block.get("children", [])
            if nested_children:
                await _update_block_children(populated_block["id"], nested_children)

    await _update_block_children(None, children, _commit_page)
    return created_page


def extract_plain_text(block: dict):
    result = ""
    for tok in block["rich_text"]:
        result += tok["plain_text"]
    return result


class BasePageTemplate:
    notion: NotionClient = Provide[Container.notion]
    template_id: str = None  # Override in subclasses

    def __init__(self):
        self._context: dict = None
        self._blocks: list = None

    async def render(self, context: dict):
        assert self.template_id is not None
        self._context = context
        self._blocks = await get_full_notion_page(
            self.template_id,
            strip_for_creation=True,
        )
        await self._transform()
        return self._blocks

    async def _transform(self):
        # Default implementation just inserts images (extend in subclasses)
        images_block = self._find_block_by_title("images")
        target = images_block["children"] if images_block is not None else self._blocks
        for url in reversed(self._context.get("images", [])):
            target.insert(0, self._image_block(url))

    def _find_block_by_title(self, title: str):
        for block in self._blocks:
            payload = block[block["type"]]
            if "rich_text" not in payload:
                continue
            text = extract_plain_text(payload)
            if text.lower() == title.lower():
                return block

    def _image_block(self, url: str):
        return {
            "type": "image",
            "image": {"type": "external", "external": {"url": url}},
        }


class GenericItemTemplate(BasePageTemplate):
    template_id = Provide[Container.settings.template_pages["default"]]


class CollectionItemTemplate(BasePageTemplate):
    template_id = Provide[Container.settings.template_pages["collection"]]


class StressTestTemplate(BasePageTemplate):
    template_id = Provide[Container.settings.template_pages["stress"]]


# FIXME
PAGE_TEMPLATES = {
    "default": GenericItemTemplate,
    "collection": CollectionItemTemplate,
    "stress": StressTestTemplate,
}
