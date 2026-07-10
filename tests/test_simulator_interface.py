"""Tests for core.simulator_interface — the domain simulator ABC."""

import inspect

import pytest

from core.simulator_interface import Environment, RunResult, SimulatorInterface


def test_direct_instantiation_raises_type_error():
    # SimulatorInterface is abstract; instantiating it directly must fail.
    with pytest.raises(TypeError):
        SimulatorInterface()  # type: ignore[abstract]


def test_incomplete_subclass_still_abstract():
    class Partial(SimulatorInterface):
        def entity_schema(self):  # only one of five methods
            ...

    with pytest.raises(TypeError):
        Partial()  # type: ignore[abstract]


def test_complete_subclass_instantiates():
    class Env(Environment):
        turn_limit: int = 10

    class Dummy(SimulatorInterface):
        def entity_schema(self):
            ...

        def environment_schema(self):
            return Env

        def run(self, entities, env):
            return RunResult(entities_involved=[], outcome={}, duration_steps=0, seed=env.seed)

        def default_metrics(self):
            return []

        def llm_generation_prompt(self, constraints):
            return ""

    sim = Dummy()
    result = sim.run([], Env(seed=7))
    assert result.seed == 7
    assert issubclass(sim.environment_schema(), Environment)


def test_all_abstract_methods_have_docstrings():
    for name, member in inspect.getmembers(SimulatorInterface, predicate=inspect.isfunction):
        if getattr(member, "__isabstractmethod__", False):
            assert member.__doc__ and member.__doc__.strip(), f"{name} missing docstring"


def test_run_result_and_environment_shape():
    r = RunResult(entities_involved=["a", "b"], outcome={"winner": "a"}, duration_steps=5, seed=1)
    assert r.outcome["winner"] == "a"
    assert Environment(seed=3).seed == 3
