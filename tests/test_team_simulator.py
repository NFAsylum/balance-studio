"""Tests for domains.team_composition.simulator — completion behaviour + determinism."""

from core.simulator_interface import Environment, RunResult
from domains.team_composition.schema import SKILLS, get_schema
from domains.team_composition.simulator import TeamCompositionSimulator, WorkloadEnv


def _person(name, seniority="mid", skills=None, prefs=None):
    model = get_schema().build_model()
    return model(
        name=name,
        seniority=seniority,
        skills=skills if skills is not None else list(SKILLS),
        preferred_task_types=prefs or [],
    )


def _team(n, seniority="mid", skills=None):
    return [_person(f"P{i}", seniority=seniority, skills=skills) for i in range(n)]


def test_run_returns_runresult():
    sim = TeamCompositionSimulator()
    assert issubclass(sim.environment_schema(), Environment)
    result = sim.run(_team(5), WorkloadEnv(seed=1, deadline_days=30))
    assert isinstance(result, RunResult)
    assert 0.0 <= result.outcome["completion_rate"] <= 1.0


def test_deterministic():
    sim = TeamCompositionSimulator()
    team = _team(5)
    outs = [sim.run(team, WorkloadEnv(seed=7)).outcome for _ in range(5)]
    assert all(o == outs[0] for o in outs)


def test_capable_team_with_ample_time_completes_everything():
    sim = TeamCompositionSimulator()
    # 8 leads who each have every skill, long deadline -> nothing blocked
    result = sim.run(_team(8, seniority="lead"), WorkloadEnv(seed=1, deadline_days=60))
    assert result.outcome["completion_rate"] == 1.0
    assert result.outcome["blocked_tasks"] == 0


def test_missing_skills_block_tasks():
    sim = TeamCompositionSimulator()
    # nobody has any real skill -> every task is blocked
    team = _team(5, skills=["irrelevant_skill"])
    result = sim.run(team, WorkloadEnv(seed=1, deadline_days=60))
    assert result.outcome["completion_rate"] == 0.0
    assert result.outcome["blocked_tasks"] > 0
    assert result.outcome["coverage"] == 0.0  # team covers none of the required skills


def test_seniority_increases_throughput():
    sim = TeamCompositionSimulator()
    env = WorkloadEnv(seed=3, deadline_days=5)  # tight: capacity binds
    juniors = sim.run(_team(3, seniority="junior"), env).outcome["completion_rate"]
    leads = sim.run(_team(3, seniority="lead"), env).outcome["completion_rate"]
    assert leads > juniors  # leads clear more work per hour
