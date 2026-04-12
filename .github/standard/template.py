"""Module summary."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExampleService:
    """Small, testable service example."""

    name: str

    def run(self, value: int) -> str:
        if value < 0:
            raise ValueError("value must be non-negative")
        return f"{self.name}:{value}"
