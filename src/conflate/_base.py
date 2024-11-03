import abc
from typing import List

from src.types import Match, ConflationResult


class Conflater(abc.ABC):
    def __init__(self, graph_a, graph_b, matches: List[Match]):
        self.graph_a = graph_a
        self.graph_b = graph_b
        self.matches = matches

    @abc.abstractmethod
    def conflate(self) -> List[ConflationResult]:
        raise NotImplementedError()
