import pytest
import yaml

from autopilot.errors import ConfigError
from autopilot.maker import spec as specmod, template

BASE = {"slug": "demo", "kind": "short", "scenes": [{"id": "a", "headline": "Hi *there*", "say": ["Hello."]}]}


def write(tmp_path, **over):
    d = {**BASE, **over}
    p = tmp_path / "video.yml"
    p.write_text(yaml.safe_dump(d))
    return p


def test_valid_spec_loads_with_sizes_and_theme(tmp_path):
    s = specmod.load(write(tmp_path, theme={"preset": "bold", "accent": "#ff0000"}))
    assert s.size == (1080, 1920) and s.theme["accent"] == "#ff0000" and s.theme["bg"] == specmod.PRESETS["bold"]["bg"]


@pytest.mark.parametrize("over,msg", [
    ({"kind": "movie"}, "kind must be"),
    ({"slug": "Bad Slug"}, "slug must be"),
    ({"theme": {"accent": "red"}}, "#rrggbb"),
    ({"theme": {"preset": "neon"}}, "preset"),
    ({"scenes": [{"id": "a", "headline": "x"}]}, "needs `say`"),
    ({"scenes": [{"id": "a", "say": ["x"]}]}, "shows nothing"),
    ({"scenes": [{"id": "a", "headline": "x", "say": ["y"]}, {"id": "a", "headline": "z", "say": ["w"]}]}, "unique id"),
    ({"music": "missing.mp3"}, "music not found"),
])
def test_bad_specs_are_refused(tmp_path, over, msg):
    with pytest.raises(ConfigError, match=msg):
        specmod.load(write(tmp_path, **over))


def test_outro_is_a_scene(tmp_path):
    s = specmod.load(write(tmp_path, outro={"headline": "Bye", "say": ["Bye."]}))
    assert [x["id"] for x in s.all_scenes()] == ["a", "outro"]


def test_template_embeds_timing_theme_and_size(tmp_path):
    s = specmod.load(write(tmp_path))
    timing = {"total": 5.0, "scenes": {"a": [0, 4]}, "beats": {"a": [{"t0": 1, "t1": 2, "text": "Hello."}]}}
    html = template.build(s, timing)
    assert 'content="1080x1920"' in html and s.theme["accent"] in html and '"total": 5.0' in html
    assert "__" not in html.replace("__proto__", "")      # every placeholder was filled


def test_script_tags_in_text_cannot_break_the_page(tmp_path):
    s = specmod.load(write(tmp_path, scenes=[{"id": "a", "headline": "</script><b>x", "say": ["Hi."]}]))
    html = template.build(s, {"total": 3, "scenes": {"a": [0, 2]}, "beats": {"a": [{"t0": 1, "t1": 2, "text": "Hi."}]}})
    assert html.count("</script>") == 1


def test_logo_is_embedded_and_must_exist(tmp_path):
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    s = specmod.load(write(tmp_path, logo="logo.png"))
    html = template.build(s, {"total": 3, "scenes": {"a": [0, 2]}, "beats": {"a": [{"t0": 1, "t1": 2, "text": "Hi."}]}})
    assert 'id="logo" src="data:image/png;base64,' in html
    with pytest.raises(ConfigError, match="logo not found"):
        specmod.load(write(tmp_path, logo="nope.png"))


def test_say_lines_may_carry_a_pause(tmp_path):
    s = specmod.load(write(tmp_path, scenes=[{"id": "a", "headline": "x", "say": ["One.", {"text": "Two.", "pause": 4}]}]))
    assert s.scenes[0]["say"][1]["pause"] == 4
    with pytest.raises(ConfigError, match="needs `say`"):
        specmod.load(write(tmp_path, scenes=[{"id": "a", "headline": "x", "say": [{"pause": 3}]}]))
