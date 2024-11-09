# coding: utf-8

from dataclasses import dataclass, field
from typing import List


@dataclass
class Shawarma:
    no_cucumber: bool = False
    no_fries: bool = False
    no_molasses: bool = False
    no_sauce: bool = False


@dataclass
class Order:
    swm: List[Shawarma] = field(default_factory=list)
    fries: int = 0
    cola1: int = 0
    cola2: int = 0
    juice: int = 0
    kibbeh: int = 0
    beggar: bool = False
