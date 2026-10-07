from __future__ import annotations

from dataclasses import replace

from .navigation import GridRect, Placement


class LayoutError(ValueError):
    pass


class LayoutEngine:
    def __init__(self, cols: int, rows: int, *, allow_overlap: bool = False) -> None:
        if cols <= 0 or rows <= 0:
            raise ValueError("layout dimensions must be positive")
        self.cols = cols
        self.rows = rows
        self.allow_overlap = allow_overlap

    def validate(self, placements: tuple[Placement, ...]) -> None:
        seen: set[str] = set()
        for placement in placements:
            if placement.id in seen:
                raise LayoutError(f"duplicate placement id: {placement.id!r}")
            seen.add(placement.id)
            self._validate_rect(placement.grid)
        if not self.allow_overlap:
            for index, left in enumerate(placements):
                for right in placements[index + 1 :]:
                    if self.overlaps(left.grid, right.grid):
                        raise LayoutError(f"placements overlap: {left.id!r} and {right.id!r}")

    def place(self, placements: tuple[Placement, ...], placement: Placement) -> tuple[Placement, ...]:
        result = (*placements, placement)
        self.validate(result)
        return result

    def move(self, placements: tuple[Placement, ...], placement_id: str, col: int, row: int) -> tuple[Placement, ...]:
        item = self._get(placements, placement_id)
        return self._replace(placements, replace(item, grid=replace(item.grid, col=col, row=row)))

    def resize(
        self,
        placements: tuple[Placement, ...],
        placement_id: str,
        colspan: int,
        rowspan: int,
    ) -> tuple[Placement, ...]:
        item = self._get(placements, placement_id)
        return self._replace(
            placements,
            replace(item, grid=replace(item.grid, colspan=colspan, rowspan=rowspan)),
        )

    def remove(self, placements: tuple[Placement, ...], placement_id: str) -> tuple[Placement, ...]:
        self._get(placements, placement_id)
        return tuple(item for item in placements if item.id != placement_id)

    def duplicate(
        self,
        placements: tuple[Placement, ...],
        placement_id: str,
        new_id: str,
        grid: GridRect,
    ) -> tuple[Placement, ...]:
        if any(item.id == new_id for item in placements):
            raise LayoutError(f"duplicate placement id: {new_id!r}")
        source = self._get(placements, placement_id)
        return self.place(placements, replace(source, id=new_id, grid=grid))

    @staticmethod
    def overlaps(left: GridRect, right: GridRect) -> bool:
        return not (
            left.col + left.colspan <= right.col
            or right.col + right.colspan <= left.col
            or left.row + left.rowspan <= right.row
            or right.row + right.rowspan <= left.row
        )

    def _replace(self, placements: tuple[Placement, ...], replacement: Placement) -> tuple[Placement, ...]:
        result = tuple(replacement if item.id == replacement.id else item for item in placements)
        self.validate(result)
        return result

    def _validate_rect(self, grid: GridRect) -> None:
        if grid.col + grid.colspan > self.cols or grid.row + grid.rowspan > self.rows:
            raise LayoutError("placement is outside layout bounds")

    @staticmethod
    def _get(placements: tuple[Placement, ...], placement_id: str) -> Placement:
        item = next((item for item in placements if item.id == placement_id), None)
        if item is None:
            raise LayoutError(f"unknown placement: {placement_id!r}")
        return item
