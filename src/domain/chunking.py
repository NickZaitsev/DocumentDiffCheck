from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import ceil
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class TokenBudget:
    max_input_tokens: int
    reserved_prompt_tokens: int = 2_000
    chars_per_token: int = 4

    @property
    def available_tokens(self) -> int:
        return max(1, self.max_input_tokens - self.reserved_prompt_tokens)

    @property
    def available_chars(self) -> int:
        return self.available_tokens * self.chars_per_token


def estimate_tokens(text: str, *, chars_per_token: int = 4) -> int:
    if not text:
        return 0
    return max(1, ceil(len(text) / chars_per_token))


def chunk_sequence(
    items: Sequence[T],
    *,
    budget: TokenBudget,
    text_for_item: Callable[[T], str],
) -> list[list[T]]:
    batches: list[list[T]] = []
    current_batch: list[T] = []
    current_tokens = 0

    for item in items:
        item_tokens = estimate_tokens(
            text_for_item(item),
            chars_per_token=budget.chars_per_token,
        )
        if current_batch and current_tokens + item_tokens > budget.available_tokens:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0

        current_batch.append(item)
        current_tokens += item_tokens

    if current_batch:
        batches.append(current_batch)
    return batches
