from typing import Any, Dict, Iterable, List, Optional, Tuple


def _normalize_span(size: Any, cols: int) -> Tuple[int, int]:
    try:
        width, height = size
        width = int(width)
        height = int(height)
    except (TypeError, ValueError):
        return 1, 1

    width = max(1, min(width, cols))
    height = max(1, height)
    return width, height


def compute_group_layout(apps: Iterable[Dict[str, Any]], cols: int = 10) -> Tuple[List[Dict[str, Any]], int, int]:
    if cols < 1:
        raise ValueError("cols must be at least 1")

    occupancy: List[List[int]] = []
    items: List[Dict[str, Any]] = []

    def ensure(rows: int) -> None:
        while len(occupancy) < rows:
            occupancy.append([0] * cols)

    def can_place(row: int, col: int, width: int, height: int) -> bool:
        if row < 0 or col < 0 or col + width > cols:
            return False
        ensure(row + height)
        for current_row in range(row, row + height):
            for current_col in range(col, col + width):
                if occupancy[current_row][current_col]:
                    return False
        return True

    def occupy(row: int, col: int, width: int, height: int) -> None:
        ensure(row + height)
        for current_row in range(row, row + height):
            for current_col in range(col, col + width):
                occupancy[current_row][current_col] = 1

    def place_tile(width: int, height: int) -> Tuple[int, int]:
        row = 0
        while True:
            ensure(row + height)
            for col in range(cols - width + 1):
                if can_place(row, col, width, height):
                    occupy(row, col, width, height)
                    return row, col
            row += 1

    for app in apps:
        width, height = _normalize_span(app.get("size", (1, 1)), cols)
        row = app.get("row", -1)
        col = app.get("col", -1)

        if row >= 0 and col >= 0 and can_place(row, col, width, height):
            tile_row, tile_col = row, col
            occupy(tile_row, tile_col, width, height)
        else:
            tile_row, tile_col = place_tile(width, height)

        items.append(
            {
                "kind": "tile",
                "app": {**app, "size": (width, height)},
                "row": tile_row,
                "col": tile_col,
                "row_span": height,
                "col_span": width,
            }
        )

    rows = len(occupancy)
    used_cols = max((item["col"] + item["col_span"] for item in items), default=1)
    return items, rows, used_cols


def compute_explicit_group_layout(apps: Iterable[Dict[str, Any]]) -> Optional[Tuple[List[Dict[str, Any]], int, int]]:
    apps = list(apps)
    if not apps:
        return [], 0, 1

    explicit_width = 1
    for app in apps:
        row = app.get("row", -1)
        col = app.get("col", -1)
        if row < 0 or col < 0:
            return None
        width, _ = _normalize_span(app.get("size", (1, 1)), 10_000)
        explicit_width = max(explicit_width, col + width)

    return compute_group_layout(apps, cols=explicit_width)


def _score_compact_layout(candidate: Tuple[List[Dict[str, Any]], int, int]) -> Tuple[float, float, int, int]:
    items, rows, used_cols = candidate
    filled_cells = sum(item["row_span"] * item["col_span"] for item in items)
    total_cells = max(1, rows * used_cols)
    wasted_cells = total_cells - filled_cells
    aspect_ratio = max(rows, used_cols) / max(1, min(rows, used_cols))
    single_column_penalty = 1 if used_cols == 1 and len(items) > 2 else 0
    return (aspect_ratio + (wasted_cells * 0.35) + single_column_penalty, aspect_ratio, wasted_cells, used_cols)


def compute_compact_group_layout(apps: Iterable[Dict[str, Any]], max_rows: int, max_cols: int = 10) -> Tuple[List[Dict[str, Any]], int, int]:
    if max_rows < 1:
        raise ValueError("max_rows must be at least 1")

    apps = list(apps)
    explicit = compute_explicit_group_layout(apps)
    if explicit is not None and explicit[1] <= max_rows:
        return explicit

    fitting = []
    fallback = compute_group_layout(apps, cols=max_cols)
    for cols in range(1, max_cols + 1):
        candidate = compute_group_layout(apps, cols=cols)
        fallback = candidate
        if candidate[1] <= max_rows:
            fitting.append(candidate)

    if fitting:
        return min(fitting, key=_score_compact_layout)
    return fallback


def compute_board_layout(
    groups: Iterable[Dict[str, Any]],
    rows: int = 2,
    gap: int = 0,
    max_height: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], int, int]:
    if rows < 1:
        raise ValueError("rows must be at least 1")

    prepared = [{**dict(group), "_index": index} for index, group in enumerate(groups)]
    columns: Dict[int, List[Dict[str, Any]]] = {}
    auto: List[Dict[str, Any]] = []

    for group in prepared:
        col = group.get("board_col", -1)
        if col >= 0:
            columns.setdefault(col, []).append(group)
        else:
            auto.append(group)

    for col, items in columns.items():
        items.sort(key=lambda item: (item.get("board_row", -1) if item.get("board_row", -1) >= 0 else 10**6, item["_index"]))
        for order, item in enumerate(items):
            item["board_row"] = order
            item["board_col"] = col

    def column_height(col: int) -> int:
        total = 0
        for item in columns.get(col, []):
            if total:
                total += gap
            total += int(item.get("height", 0))
        return total

    def can_fit(col: int, item: Dict[str, Any]) -> bool:
        if max_height is None or max_height <= 0:
            return len(columns.get(col, [])) < rows or rows < 1
        projected = column_height(col)
        if projected:
            projected += gap
        projected += int(item.get("height", 0))
        return projected <= max_height

    def next_auto_col() -> int:
        used = set(columns)
        col = 0
        while col in used:
            col += 1
        return col

    for item in auto:
        placed = False
        for col in sorted(columns):
            if can_fit(col, item):
                item["board_col"] = col
                item["board_row"] = len(columns[col])
                columns[col].append(item)
                placed = True
                break
        if placed:
            continue

        col = next_auto_col()
        item["board_col"] = col
        item["board_row"] = 0
        columns[col] = [item]

    used_cols = max(columns.keys(), default=-1) + 1
    col_widths = [0] * max(used_cols, 1)
    col_heights = [0] * max(used_cols, 1)
    items = []

    for col, groups_in_col in columns.items():
        y_cursor = 0
        for item in groups_in_col:
            items.append({**item, "x": 0, "y": y_cursor})
            col_widths[col] = max(col_widths[col], int(item.get("width", 0)))
            y_cursor += int(item.get("height", 0)) + gap
        if groups_in_col:
            col_heights[col] = y_cursor - gap

    x_offsets: List[int] = []
    cursor = 0
    for width in col_widths:
        x_offsets.append(cursor)
        cursor += width + gap
    total_width = max(0, cursor - gap) if items else 0
    total_height = max(col_heights, default=0)

    placed_items = []
    for item in items:
        placed_items.append({**item, "x": x_offsets[item["board_col"]]})

    return placed_items, total_height, total_width


def compute_grid_layout(apps: Iterable[Dict[str, Any]], cols: int = 10) -> Tuple[List[Dict[str, Any]], int]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for app in apps:
        groups.setdefault(app.get("group", "Apps"), []).append(app)

    items: List[Dict[str, Any]] = []
    row_cursor = 0

    for group_name, group_apps in groups.items():
        items.append(
            {
                "kind": "label",
                "text": group_name.upper(),
                "row": row_cursor,
                "col": 0,
                "row_span": 1,
                "col_span": cols,
            }
        )
        row_cursor += 1

        group_items, group_rows, _ = compute_group_layout(group_apps, cols=cols)
        for item in group_items:
            items.append({**item, "row": item["row"] + row_cursor})
        row_cursor += group_rows

    return items, row_cursor
