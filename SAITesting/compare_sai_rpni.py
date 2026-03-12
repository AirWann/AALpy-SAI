from aalpy.automata.Sfa import Sfa, SfaState
from aalpy.base.BooleanAlgebra import IntervalPredicate, Predicate, BooleanAlgebra, IntervalAlgebra, OrPredicate
import numpy as np
from aalpy.learning_algs.deterministic_passive.SAI import SAI
from aalpy.utils import save_automaton_to_file, visualize_automaton
from aalpy.automata import Dfa, DfaState
from aalpy.learning_algs import run_RPNI
from aalpy.SAITesting.test_sai import generate_sfa
import time

def sfa_to_dfa(sfa: Sfa) -> Dfa:
    """
    Transform an SFA into a Dfa using the lower bounds of the Intervals as input symbols.
    """
    state_mapping = {}
    for sfa_state in sfa.states:
        dfa_state = DfaState(sfa_state.state_id, is_accepting=sfa_state.is_accepting)
        state_mapping[sfa_state] = dfa_state
    
    for sfa_state in sfa.states:
        dfa_state = state_mapping[sfa_state]
        for predicate, target_sfa_state in sfa_state.transitions:
            assert isinstance(predicate, IntervalPredicate), "Expected Interval in SFA transitions"
            dfa_state.transitions[predicate.lower] = state_mapping[target_sfa_state]


    return Dfa(state_mapping[sfa.initial_state], list(state_mapping.values()))
def dfa_to_sfa(dfa: Dfa, algebra: BooleanAlgebra) -> Sfa:
    """
    Transform a Dfa into an SFA by creating IntervalPredicates for each transition. The intervals are defined as gaps between the input symbols of the Dfa transitions

    for example, if a Dfa state has transitions on input symbols 1, 5, and 10, the corresponding SFA state will have transitions with predicates [1, 5), [5, 10), and [10, None) respectively.
    """
    assert all((lambda i: isinstance(i, int) or i == None) for s in dfa.states for i in s.transitions.keys()), "Expected integer inputs in Dfa transitions"
    state_mapping = {}
    for dfa_state in dfa.states:
        sfa_state = SfaState(dfa_state.state_id, is_accepting=dfa_state.is_accepting)
        state_mapping[dfa_state] = sfa_state
    
    for dfa_state in dfa.states:
        sfa_state = state_mapping[dfa_state]
        # Sort the input symbols to create intervals
        sorted_inputs = sorted(dfa_state.transitions.keys(), key=lambda x: (float('-inf') if x is None else x))
        #make transitions with intervals
        for i, input_symbol in enumerate(sorted_inputs):
            next_input_symbol = sorted_inputs[i + 1] if i + 1 < len(sorted_inputs) else None
            target_dfa_state = dfa_state.transitions[input_symbol]
            predicate = IntervalPredicate(input_symbol, next_input_symbol)
            sfa_state.transitions.append((predicate, state_mapping[target_dfa_state]))

    return Sfa(state_mapping[dfa.initial_state], list(state_mapping.values()), algebra=algebra)

alg = IntervalAlgebra()

testautomaton = Sfa.from_state_setup(
    {
        "s0": (True, [(IntervalPredicate(None, 10), "s1"), (IntervalPredicate(11, 20), "s0")]),
        "s1": (False, [(IntervalPredicate(0, 15), "s0"), (IntervalPredicate(15, 20), "s1")])
    }, algebra=alg)
dfa = sfa_to_dfa(testautomaton)
print(dfa)
reconstructed_sfa = dfa_to_sfa(dfa, algebra=alg)
print(reconstructed_sfa)