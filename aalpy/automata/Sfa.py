from typing import List, Tuple, Dict

from aalpy.base import AutomatonState, DeterministicAutomaton
from aalpy.base.Automaton import InputType
from aalpy.base.BooleanAlgebra import IntervalPredicate, Predicate, BooleanAlgebra, IntervalAlgebra, OrPredicate


class SfaState(AutomatonState):
    """
    Single state of a symbolic finite automaton.
    Many methods are overridden from Dfa to account for predicates in transitions.
    """

    def __init__(self, state_id, is_accepting=False):
        super().__init__(state_id)
        self.transitions : List[Tuple[Predicate, 'SfaState']] = []
        self.is_accepting = is_accepting

    def get_diff_state_transitions(self) -> list:
        transitions = []
        for pred, state in self.transitions:
            if state != self:
                transitions.append((pred, state))
        return transitions
    def get_same_state_transitions(self) -> List:
        return [(p,s) for p,s in self.transitions if s == self]

    @property
    def output(self):
        return self.is_accepting
    
class Sfa(DeterministicAutomaton[SfaState]):
    """
    Symbolic finite automaton.
    """

    def __init__(self, initial_state: SfaState, states: List[SfaState], algebra: BooleanAlgebra | None = None):
        super().__init__(initial_state, states)
        self.algebra: BooleanAlgebra = algebra or IntervalAlgebra()


    def step(self, letter):
        """
        Args:

            letter: single input that is looked up in the transition table of the DfaState

        Returns:

            True if the reached state is an accepting state, False otherwise
        """
        for pred, next in self.current_state.transitions:
            if pred.eval(letter):
                self.current_state = next
                return self.current_state.is_accepting
        raise KeyError(f"No transition for input {letter} from state {self.current_state.state_id}.")

    def is_input_complete(self) -> bool:
        # disjunction of all outgoing predicates must be True
        for s in self.states:
            if not s.transitions:
                return False
            disj = self.algebra.false()
            for pred, _ in s.transitions:
                disj = self.algebra.or_op(disj, pred)
            if not self.algebra.is_true(self.algebra.minimize_predicate(disj)):
                return False
        return True
    def make_input_complete(self):
        # add a sink with guard = negation of current disjunction
        sink = SfaState('sink', is_accepting=False)
        sink.transitions.append((self.algebra.true(), sink))
        for s in self.states:
            disj = self.algebra.false()
            for pred, _ in s.transitions:
                disj = self.algebra.or_op(disj, pred)
            missing = self.algebra.minimize_predicate(disj.negate())
            s.transitions.append((missing, sink))
        if sink not in self.states:
            self.states.append(sink)

    @staticmethod
    def from_state_setup(state_setup: Dict[int, Tuple[bool, List[Tuple[Predicate, int]]]],
                         algebra: BooleanAlgebra) -> 'Sfa':
        """
        Build an SFA from:
            {
                state_id: (is_accepting, [(predicate, target_state_id), ...]),
                ...
            }
        First state in the state setup is the initial state.
        """
        # build states
        states_dict: Dict[int, SfaState] = {state_id: SfaState(state_id, is_acc) for state_id, (is_acc, _) in state_setup.items()}

        # add transitions
        for state_id, (_, transitions) in state_setup.items():
            s = states_dict[state_id]
            for pred, tgt_id in transitions:
                s.transitions.append((pred, states_dict[tgt_id]))

        # initial is the first key by insertion order
        initial_id = next(iter(state_setup))
        sfa = Sfa(states_dict[initial_id], list(states_dict.values()), algebra)


        return sfa
    @staticmethod
    def to_state_setup(sfa: 'Sfa') -> Dict[int, Tuple[bool, List[Tuple[Predicate, int]]]]:
        """
        Convert SFA to state setup dict:
            {
                state_id: (is_accepting, [(predicate, target_state_id), ...]),
                ...
            }
        """
        state_setup = {}
        for s in sfa.states:
            transitions = [(pred, tgt.state_id) for pred, tgt in s.transitions]
            state_setup[s.state_id] = (s.is_accepting, transitions)
        return state_setup



"""Example SFA"""


alg = IntervalAlgebra()

testautomaton = Sfa.from_state_setup(
    {
        0: (True, [(IntervalPredicate(0, 10), 1), (IntervalPredicate(11, 20), 0)]),
        1: (False, [(IntervalPredicate(0, 10), 0), (IntervalPredicate(11, 20), 1)])
    }, algebra=alg)
print(testautomaton.execute_sequence(testautomaton.initial_state, [5, 7, 15, 3, 12]))  