from dataclasses import dataclass, field
from typing import List, Optional
from .core import CODEC_NONE

@dataclass(slots=True)
class Field:
    name: str
    type: int
    codec: int = CODEC_NONE
    optional: bool = False

@dataclass(slots=True)
class Schema:
    name: str
    version: int
    fields: List[Field]
