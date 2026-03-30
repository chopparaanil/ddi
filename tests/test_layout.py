from layout import compute_board_layout, compute_compact_group_layout, compute_explicit_group_layout, compute_grid_layout, compute_group_layout


def test_group_layout_honors_explicit_positions():
    apps = [
        {"name": "One", "group": "Alpha", "size": (1, 1), "row": 0, "col": 0, "color": "#111111"},
        {"name": "Two", "group": "Alpha", "size": (2, 1), "row": 0, "col": 1, "color": "#222222"},
    ]

    items, total_rows, used_cols = compute_group_layout(apps, cols=4)

    assert items[0]["row"] == 0
    assert items[0]["col"] == 0
    assert items[1]["row"] == 0
    assert items[1]["col"] == 1
    assert total_rows == 1
    assert used_cols == 3


def test_group_layout_collisions_fall_back_to_next_available_slot():
    apps = [
        {"name": "One", "group": "Alpha", "size": (1, 1), "row": 0, "col": 0, "color": "#111111"},
        {"name": "Two", "group": "Alpha", "size": (1, 1), "row": 0, "col": 0, "color": "#222222"},
    ]

    items, _, _ = compute_group_layout(apps, cols=4)

    assert (items[0]["row"], items[0]["col"]) == (0, 0)
    assert (items[1]["row"], items[1]["col"]) == (0, 1)


def test_compact_group_layout_reduces_width_when_more_rows_are_allowed():
    apps = [
        {"name": "Wide", "group": "Alpha", "size": (2, 2), "row": -1, "col": -1, "color": "#111111"},
        {"name": "One", "group": "Alpha", "size": (1, 1), "row": -1, "col": -1, "color": "#222222"},
        {"name": "Two", "group": "Alpha", "size": (1, 1), "row": -1, "col": -1, "color": "#333333"},
        {"name": "Three", "group": "Alpha", "size": (1, 1), "row": -1, "col": -1, "color": "#444444"},
        {"name": "Four", "group": "Alpha", "size": (1, 1), "row": -1, "col": -1, "color": "#555555"},
    ]

    items, rows, used_cols = compute_compact_group_layout(apps, max_rows=4, max_cols=10)

    assert rows <= 4
    assert used_cols <= 3


def test_grid_layout_stacks_group_labels_and_relative_tiles():
    apps = [
        {"name": "One", "group": "Alpha", "size": (1, 1), "row": 0, "col": 0, "color": "#111111"},
        {"name": "Two", "group": "Beta", "size": (1, 1), "row": 0, "col": 0, "color": "#222222"},
    ]

    items, total_rows = compute_grid_layout(apps, cols=4)
    alpha_label, first_tile, beta_label, second_tile = items

    assert alpha_label["row"] == 0
    assert first_tile["row"] == 1
    assert beta_label["row"] == 2
    assert second_tile["row"] == 3
    assert total_rows == 4


def test_board_layout_fills_down_before_expanding_right():
    groups = [
        {"name": "One", "width": 100, "height": 100, "board_row": -1, "board_col": -1},
        {"name": "Two", "width": 120, "height": 100, "board_row": -1, "board_col": -1},
        {"name": "Three", "width": 140, "height": 100, "board_row": -1, "board_col": -1},
    ]

    items, total_height, total_width = compute_board_layout(groups, gap=30, max_height=250)
    positions = {item["name"]: (item["board_row"], item["board_col"]) for item in items}

    assert positions["One"] == (0, 0)
    assert positions["Two"] == (1, 0)
    assert positions["Three"] == (0, 1)
    assert total_height == 230
    assert total_width == 290


def test_board_layout_honors_explicit_group_positions_in_columns():
    groups = [
        {"name": "IO Tools", "width": 400, "height": 220, "board_row": 0, "board_col": 0},
        {"name": "Pipeline", "width": 260, "height": 220, "board_row": 0, "board_col": 1},
        {"name": "Media", "width": 260, "height": 180, "board_row": 1, "board_col": 1},
    ]

    items, total_height, total_width = compute_board_layout(groups, gap=30, max_height=500)
    positions = {item["name"]: (item["x"], item["y"]) for item in items}

    assert positions["IO Tools"] == (0, 0)
    assert positions["Pipeline"] == (430, 0)
    assert positions["Media"] == (430, 250)
    assert total_height == 430
    assert total_width == 690


def test_compact_group_layout_avoids_needlessly_skinny_columns():
    apps = [
        {"name": "One", "group": "Utility", "size": (1, 1), "row": 0, "col": 0, "color": "#111111"},
        {"name": "Two", "group": "Utility", "size": (1, 1), "row": 0, "col": 1, "color": "#222222"},
        {"name": "Three", "group": "Utility", "size": (1, 1), "row": 1, "col": 0, "color": "#333333"},
    ]

    _, rows, used_cols = compute_compact_group_layout(apps, max_rows=4, max_cols=5)

    assert rows == 2
    assert used_cols == 2


def test_explicit_group_layout_preserves_env_mapping_when_complete():
    apps = [
        {"name": "One", "group": "Alpha", "size": (2, 1), "row": 0, "col": 0, "color": "#111111"},
        {"name": "Two", "group": "Alpha", "size": (1, 2), "row": 1, "col": 2, "color": "#222222"},
        {"name": "Three", "group": "Alpha", "size": (2, 1), "row": 3, "col": 0, "color": "#333333"},
    ]

    items, rows, used_cols = compute_explicit_group_layout(apps)

    assert rows == 4
    assert used_cols == 3
    positions = {item["app"]["name"]: (item["row"], item["col"]) for item in items}
    assert positions == {"One": (0, 0), "Two": (1, 2), "Three": (3, 0)}
