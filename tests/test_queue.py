import pytest
import yaml

from autopilot.config import DEFAULT_ACTIONS
from autopilot.errors import ConfigError
from autopilot.queue import load_queue
from conftest import make_item


def test_loads_in_priority_order(tmp_path):
    make_item(tmp_path, "b", priority=5)
    make_item(tmp_path, "a", priority=50)
    assert [i.slug for i in load_queue(tmp_path, DEFAULT_ACTIONS)] == ["b", "a"]


def test_default_actions_come_from_kind(tmp_path):
    make_item(tmp_path, "s", kind="short")
    assert "youtube.short" in load_queue(tmp_path, DEFAULT_ACTIONS)[0].actions


def test_missing_file_is_refused_at_load(tmp_path):
    d = make_item(tmp_path, "s")
    (d / "v.mp4").unlink()
    with pytest.raises(ConfigError, match="file not found"):
        load_queue(tmp_path, DEFAULT_ACTIONS)


def test_unknown_action_and_bad_kind(tmp_path):
    make_item(tmp_path, "x", actions=["tiktok.reel"])
    with pytest.raises(ConfigError, match="unknown action"):
        load_queue(tmp_path, DEFAULT_ACTIONS)
    (tmp_path / "x" / "item.yml").write_text(yaml.safe_dump({"kind": "podcast"}))
    with pytest.raises(ConfigError, match="kind must be"):
        load_queue(tmp_path, DEFAULT_ACTIONS)


def test_post_needs_text_or_link(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    (d / "item.yml").write_text(yaml.safe_dump({"kind": "post"}))
    with pytest.raises(ConfigError, match="facebook.post needs"):
        load_queue(tmp_path, DEFAULT_ACTIONS)
