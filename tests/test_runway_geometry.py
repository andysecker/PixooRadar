from pixoo_radar.render.weather_view import choose_runway_label_position, resolve_active_runway_heading


def test_active_runway_heading_selects_reciprocal_when_needed():
    assert resolve_active_runway_heading(wind_dir_deg=280, runway_heading_deg=110) == 290


def test_active_runway_heading_handles_none_wind():
    assert resolve_active_runway_heading(wind_dir_deg=None, runway_heading_deg=110) is None


def test_choose_runway_label_position_stays_on_screen():
    tx, ty = choose_runway_label_position(label_w=11, label_h=7, runway_heading_deg=110, anchor_x=32, anchor_y=32)
    assert 0 <= tx <= 53
    assert 0 <= ty <= 57
