"""The label as the API returns it: the rendered PNGs, base64-encoded, plus any warnings."""
import base64
from typing import Literal

from pydantic import BaseModel

from app.labels import render as label_render
from app.labels.data import LabelData


class LabelImage(BaseModel):
    kind: Literal["main", "tracks"]
    name: str  # "main", "tracks", or "tracks-2" when the tracklist needs several labels
    png_base64: str  # 1-bit PNG, 696 px wide (62 mm at 300 dpi): what the Brother QL prints
    width: int
    height: int


class LabelRender(BaseModel):
    images: list[LabelImage]
    warnings: list[str]


def draw(data: LabelData) -> LabelRender:
    images, warnings = label_render.render(data)
    return LabelRender(
        images=[LabelImage(kind=i.kind, name=i.name, png_base64=base64.b64encode(i.png).decode(),
                           width=label_render.W, height=label_render.H) for i in images],
        warnings=warnings)
