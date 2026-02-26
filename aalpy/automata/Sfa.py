from typing import List, Set, Tuple, Dict

from aalpy.base import AutomatonState, DeterministicAutomaton
from aalpy.base.Automaton import InputType
from aalpy.base.BooleanAlgebra import IntervalPredicate, Predicate, BooleanAlgebra, IntervalAlgebra, OrPredicate
import warnings

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

    def __str__(self):
        return f"Sfa(initial_state={self.initial_state.state_id}, states={[s.state_id for s in self.states]}, final states={[s.state_id for s in self.states if s.is_accepting]}, transitions={{ {', '.join([f'{s.state_id}: [{', '.join([f'({str(p)}, {t.state_id})' for p, t in s.transitions])}]' for s in self.states])} }})"

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

    def accepts(self, word):
        if len(word) == 0:
            return self.initial_state.is_accepting
        else:
            return self.compute_output_seq(self.initial_state, word)[-1]

    def get_shortest_path(self, origin_state: SfaState, target_state: SfaState) -> Tuple | None:
        if origin_state not in self.states or target_state not in self.states:
            warnings.warn('Origin or target state not in automaton. Returning None.')
            return None

        explored = []
        queue = [[origin_state]]

        if origin_state == target_state:
            return ()

        while queue:
            path = queue.pop(0)
            node = path[-1]
            if node not in explored:
                neighbours = [t[1] for t in node.transitions]
                for neighbour in neighbours:
                    new_path = list(path)
                    new_path.append(neighbour)
                    queue.append(new_path)
                    # return path if neighbour is goal
                    if neighbour == target_state:
                        acc_seq = new_path[:-1]
                        inputs = []
                        for ind, state in enumerate(acc_seq):
                            inputs.append(self.algebra.pick_witness(next(pred for pred, tgt in state.transitions if tgt == new_path[ind + 1])))
                        return tuple(inputs)

                # mark node as explored
                explored.append(node)

        return None
    def find_distinguishing_seq(self, state1, state2):
        """
        A BFS to determine an input sequence that distinguishes two states in the automaton, i.e., a sequence such that
        the output response from the given states is different. In a minimal automaton, this function always returns a
        sequence different from None
        Args:
            state1: first state
            state2: second state to distinguish

        Returns: an input sequence distinguishing two states, or None if the states are equivalent

        """
        visited = set()
        to_explore = [(state1, state2, [])]
        while to_explore:
            (curr_s1, curr_s2, prefix) = to_explore.pop(0)
            visited.add((curr_s1, curr_s2))
            if curr_s1.is_accepting != curr_s2.is_accepting:
                return tuple(prefix)
            for (pred1, next_s1) in curr_s1.transitions:
                for (pred2, next_s2) in curr_s2.transitions:
                    and_pred = self.algebra.and_op(pred1, pred2)
                    if self.algebra.is_satisfiable(and_pred):
                        if (next_s1, next_s2) not in visited:
                            to_explore.append((next_s1, next_s2, prefix + [self.algebra.pick_witness(and_pred)]))
        return None
    
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
    
    def to_state_setup(self) -> Dict[int, Tuple[bool, List[Tuple[Predicate, int]]]]:
        """
        Convert SFA to state setup dict:
            {
                state_id: (is_accepting, [(predicate, target_state_id), ...]),
                ...
            }
        """
        state_setup = {}
        for s in self.states:
            transitions = [(pred, tgt.state_id) for pred, tgt in s.transitions]
            state_setup[s.state_id] = (s.is_accepting, transitions)
        return state_setup
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
        states =[state for state in states_dict.values()] 
        for state in states:
            state.prefix = sfa.get_shortest_path(sfa.initial_state, state)

        return sfa
    
    def __repr__(self):
        return self.to_state_setup()
    def characteristic_sample(self) -> Set[Tuple[Tuple, bool]]:
        """
        Generate a characteristic sample for the SFA.
        For each pair of states, add two words with prefix leading to each of the states and a distinguishing suffix if they are not equivalent.
        For each transition add a word with prefix leading to the source state, a letter firing the transition, duplicate with distinguishing suffixes to every other state.
        """
        sample_no_label = set()
        for s1 in self.states:
            for s2 in self.states:
                    prefix1 = self.get_shortest_path(self.initial_state, s1)
                    prefix2 = self.get_shortest_path(self.initial_state, s2)
                    suffix = self.find_distinguishing_seq(s1, s2)
                    if suffix is None:
                        suffix = ()
                    if prefix1 is None:
                        prefix1 = ()
                    if prefix2 is None:
                        prefix2 = ()
                    sample_no_label.add((prefix1 + suffix))
                    sample_no_label.add((prefix2 + suffix))
        for s in self.states:

            prefix = self.get_shortest_path(self.initial_state, s)
            if prefix is None:
                prefix = ()
            for pred, next_s in s.transitions:
                word = prefix + (self.algebra.pick_witness(pred),)
                suffixes = [self.find_distinguishing_seq(s, other_s) for other_s in self.states if other_s != s]
                for suffix in suffixes:
                    if suffix is None:
                        suffix = ()
                    sample_no_label.add((word + suffix))
        sample = set()
        for word in sample_no_label.copy():
            if word == ():
                sample.add((word, self.initial_state.output))
            else:
                sample.add((word, self.compute_output_seq(self.initial_state, word)[-1]))
        return sample


"""Example SFA"""


# alg = IntervalAlgebra()

# testautomaton = Sfa.from_state_setup(
#     {
#         0: (True, [(IntervalPredicate(0, 10), 1), (IntervalPredicate(11, 20), 0)]),
#         1: (False, [(IntervalPredicate(0, 10), 0), (IntervalPredicate(11, 20), 1)])
#     }, algebra=alg)
# print(testautomaton.execute_sequence(testautomaton.initial_state, [5, 7, 15, 3, 12]))  
# print(testautomaton.get_shortest_path(testautomaton.initial_state, testautomaton.states[1]))
# print( [state.prefix for state in testautomaton.states])
# print(testautomaton.characteristic_sample())