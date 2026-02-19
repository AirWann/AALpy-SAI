import pytest

from aalpy.automata.Sfa import Sfa, SfaState
from aalpy.base.BooleanAlgebra import IntervalAlgebra, IntervalPredicate

#FULL DISCLOSURE: These tese were written by copilot
def build_two_state_sfa():
    alg = IntervalAlgebra()
    s0 = SfaState(0, is_accepting=True)
    s1 = SfaState(1, is_accepting=False)
    s0.transitions = [
        (IntervalPredicate(0, 10), s1),
        (IntervalPredicate(0, 20), s0),
    ]
    s1.transitions = [(IntervalPredicate(0, 30), s1)]
    return Sfa(s0, [s0, s1], algebra=alg)


def test_step_respects_transition_order_and_raises_on_missing():
    sfa = build_two_state_sfa()

    assert sfa.step(5) is False
    assert sfa.current_state.state_id == 1

    sfa.reset_to_initial()
    with pytest.raises(KeyError):
        sfa.step(50)


def test_get_shortest_path_returns_witness_inputs():
    alg = IntervalAlgebra()
    sfa = Sfa.from_state_setup(
        {
            0: (True, [(IntervalPredicate(0, 10), 1)]),
            1: (False, [(IntervalPredicate(0, 10), 1)]),
        },
        algebra=alg,
    )

    target = next(s for s in sfa.states if s.state_id == 1)
    path = sfa.get_shortest_path(sfa.initial_state, target)
    assert path == (0,)


def test_make_input_complete_adds_sink_and_covers_all_inputs():
    alg = IntervalAlgebra()
    s0 = SfaState("a", is_accepting=False)
    s1 = SfaState("b", is_accepting=True)
    s0.transitions = [(IntervalPredicate(0, 5), s1)]
    s1.transitions = []
    sfa = Sfa(s0, [s0, s1], algebra=alg)

    assert not sfa.is_input_complete()
    sfa.make_input_complete()
    print (Sfa.to_state_setup(sfa))
    assert sfa.is_input_complete()

    sink_states = [s for s in sfa.states if s.state_id == "sink"]
    assert len(sink_states) == 1
    sink = sink_states[0]
    assert sink.transitions[0][1] == sink
    assert alg.is_true(alg.minimize_predicate(sink.transitions[0][0]))

    for state in sfa.states:
        disj = alg.false()
        for pred, _ in state.transitions:
            disj = alg.or_op(disj, pred)
        assert alg.is_true(alg.minimize_predicate(disj))


def test_state_setup_round_trip_preserves_structure_and_prefixes():
    alg = IntervalAlgebra()
    original = {
        0: (True, [(IntervalPredicate(0, 10), 1), (IntervalPredicate(10, 20), 0)]),
        1: (False, [(IntervalPredicate(0, 10), 0), (IntervalPredicate(10, 20), 1)]),
    }

    sfa = Sfa.from_state_setup(original, algebra=alg)
    round_trip = Sfa.to_state_setup(sfa)

    assert round_trip == original
    assert sfa.initial_state.prefix == ()
    target = next(s for s in sfa.states if s.state_id == 1)
    assert target.prefix == (0,)
