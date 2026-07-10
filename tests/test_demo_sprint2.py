"""Guards the Sprint 2 end-to-end verification: the Fake-LLM demo is reproducible + persisted."""

from pathlib import Path

from scripts.demo_sprint2 import run_demo


def test_demo_is_reproducible(tmp_path):
    a = run_demo("aggro deck", n=5, domain="card_game", seed=42, base_dir=str(tmp_path / "a"))
    b = run_demo("aggro deck", n=5, domain="card_game", seed=42, base_dir=str(tmp_path / "b"))
    assert a == b


def test_demo_runs_full_flow_and_persists(tmp_path):
    summary = run_demo("aggro deck", n=5, domain="card_game", seed=42, base_dir=str(tmp_path))

    assert len(summary["entities"]) == 5
    assert summary["matches"] == 100  # C(5,2)=10 pairs * 10 matches
    assert set(summary["winrate"]) == set(summary["entities"])
    assert 0.0 <= summary["judge"]["score"] <= 1.0
    assert summary["modifications"]  # FakeIterator proposed at least one change

    scenario_dir = tmp_path / summary["scenario_id"]
    assert (scenario_dir / "events.jsonl").exists()
    assert (scenario_dir / "manifest.json").exists()
    snapshots = list((scenario_dir / "snapshots").glob("*.json.zst"))
    assert len(snapshots) == 1
    # one create per unit + simulate + judge + one note per modification
    expected_events = 5 + 1 + 1 + len(summary["modifications"])
    assert summary["events_persisted"] == expected_events
    event_lines = Path(scenario_dir / "events.jsonl").read_text().strip().splitlines()
    assert len(event_lines) == expected_events
