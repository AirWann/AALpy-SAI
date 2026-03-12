from typing import List, Set, Tuple, Dict

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

    def __str__(self):
         return f"Sfa(initial_state={self.initial_state.state_id}, states={[s.state_id for s in self.states]}, final states={[s.state_id for s in self.states if s.is_accepting]}, transitions={{ {', '.join([f'\n{s.state_id}: [{', '.join([f'({str(p)}, {t.state_id})' for p, t in s.transitions])}]' for s in self.states])} }})"
    
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

    def bisimilar(self, other: 'Sfa', return_cex: bool = False) -> bool | None | Tuple:
        """
        Check bisimilarity with another SFA.

        If return_cex is False:
            returns True/False.
        If return_cex is True:
            returns None if bisimilar, otherwise a concrete counterexample input tuple.
        """
        if not isinstance(other, Sfa):
            raise ValueError("tried to check bisimilarity of different automaton types")

        if self is other:
            other = self.copy()

        def _extend_with_witness(prefix: Tuple, pred: Predicate) -> Tuple:
            w = self.algebra.pick_witness(pred)
            if w is None:
                w = self.algebra.pick_witness(self.algebra.minimize_predicate(pred))
            return prefix if w is None else prefix + (w,)
        
        to_check = [(self.initial_state, other.initial_state)]
        requirements = {(self.initial_state, other.initial_state): ()}
        visited = set()
        if not self.is_input_complete() or not other.is_input_complete():
            print("Warning: bisimilarity check between incomplete automata")
            new_self = self.copy()
            new_self.make_input_complete()
            new_other = other.copy()
            new_other.make_input_complete()
            return new_self.bisimilar(new_other, return_cex)
        
        while to_check:
            s1, s2 = to_check.pop(0)
            if (s1, s2) in visited:
                continue
            visited.add((s1, s2))

            # accepting status must match
            if s1.output != s2.output:
                return requirements[(s1, s2)] if return_cex else False

            # Enabled input regions must match not needed for complete automata
            # disj1 = self.algebra.false()
            # for p1, _ in s1.transitions:
            #     disj1 = self.algebra.or_op(disj1, p1)

            # disj2 = self.algebra.false()
            # for p2, _ in s2.transitions:
            #     disj2 = self.algebra.or_op(disj2, p2)

            # only_1 = self.algebra.and_op(disj1, disj2.negate())
            # if self.algebra.is_satisfiable(only_1):
            #     cex = _extend_with_witness(requirements[(s1, s2)], only_1)
            #     return cex if return_cex else False

            # only_2 = self.algebra.and_op(disj2, disj1.negate())
            # if self.algebra.is_satisfiable(only_2):
            #     cex = _extend_with_witness(requirements[(s1, s2)], only_2)
            #     return cex if return_cex else False

            # Successor compatibility for overlapping guards
            for p1, n1 in s1.transitions:
                for p2, n2 in s2.transitions:
                    inter = self.algebra.and_op(p1, p2)
                    if self.algebra.is_satisfiable(inter):
                        if (n1, n2) not in requirements:
                            requirements[(n1, n2)] = _extend_with_witness(requirements[(s1, s2)], inter)
                            to_check.append((n1, n2))

        return None if return_cex else True

    def get_shortest_path(self, origin_state: SfaState, target_state: SfaState) -> Tuple | None:
        if origin_state not in self.states or target_state not in self.states:
            raise ValueError('Origin or target state not in automaton. Returning None.')
            

        explored = []
        queue = [[origin_state]]

        if origin_state == target_state:
            return ()

        while queue:
            path = queue.pop(0)
            node = path[-1]
            if node not in explored:
                neighbours = [t[1] for t in node.transitions if self.algebra.is_satisfiable(t[0])]
                for neighbour in neighbours:
                    new_path = list(path)
                    new_path.append(neighbour)
                    queue.append(new_path)
                    # return path if neighbour is goal
                    if neighbour == target_state:
                        acc_seq = new_path[:-1]
                        inputs = []
                        for ind, state in enumerate(acc_seq):
                            preds = [pred for pred, tgt in state.transitions if tgt == new_path[ind + 1] and self.algebra.is_satisfiable(pred)]
                            if preds:
                                inputs.append(self.algebra.pick_witness(preds[0]))
                            else:
                                print(f"WARNING: no transition from state {state.state_id} to state {new_path[ind + 1].state_id} found during path reconstruction. Returning None.")
                                return None
                        return tuple(inputs)

                # mark node as explored
                explored.append(node)
        #print(f"WARNING: No path found from state {origin_state.state_id} to state {target_state.state_id}. Returning None.")
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
        if state1 not in self.states or state2 not in self.states:
            raise ValueError('One or both states not in automaton.')
        if state1 == state2:
            return None
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
                            to_explore.append(
                                (next_s1, next_s2, prefix + [self.algebra.pick_witness(and_pred)])
                                )
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
    def from_state_setup(state_setup: Dict[str, Tuple[bool, List[Tuple[Predicate, str]]]],
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
        
        states_dict = {key: SfaState(key, val[0]) for key, val in state_setup.items()}
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
        For each transition add a word with prefix leading to the source state, a letter firing the transition, 
        duplicate with distinguishing suffixes to every other state.
        """
        def _extend_with_witness(prefix: Tuple, pred: Predicate) -> Tuple:
            w = self.algebra.pick_witness(pred)
            return prefix if w is None else prefix + (w,)

        sample_no_label = set()
        #keep distinguishing seqs stored for all pairs of states to avoid recomputation 
        prefix_cache = {}
        for s in self.states:
            path = self.get_shortest_path(self.initial_state, s)
            if path is not None:
                prefix_cache[s] = path
            else:
                prefix_cache[s] = ()
        

        suffix_cache = {}
        for s1 in self.states:
            for s2 in self.states:
                distinguish = self.find_distinguishing_seq(s1, s2)
                if distinguish is not None:
                    suffix_cache[(s1, s2)] = distinguish
                else:
                    if s1 != s2:
                        pass
                        #print(f"WARNING: states {s1.state_id} and {s2.state_id} are not distinguishable")
                    suffix_cache[(s1, s2)] = ()
        #distinguish pairs of states
        for s1 in self.states:
            for s2 in self.states:
                    prefix1 = prefix_cache[s1]
                    prefix2 = prefix_cache[s2]
                    suffix = suffix_cache[(s1, s2)]
                    if suffix is None:
                        suffix = ()
                    if prefix1 is None:
                        prefix1 = ()
                    if prefix2 is None:
                        prefix2 = ()
                    sample_no_label.add((prefix1 + suffix))
                    sample_no_label.add((prefix2 + suffix))
        #distinguish transitions
        for s in self.states:
            prefix = prefix_cache[s]
            if prefix is None:
                prefix = ()
            for pred, next_s in s.transitions:
                if not self.algebra.is_satisfiable(pred):
                    continue
                #word firing the transition
                word = _extend_with_witness(prefix, pred)
                #distinguish target state from other states
                suffixes = [suffix_cache[(next_s, other_s)] for other_s in self.states if other_s != next_s]
                for suffix in suffixes:
                    if suffix is None:
                        suffix = ()
                    sample_no_label.add((word + suffix))
        sample = set()
        for word in {w for w in sample_no_label if w is not None and None not in w}:
            sample.add((word, self.accepts(word)))
        return sample


"""Example SFA"""


# alg = IntervalAlgebra()

# testautomaton = Sfa.from_state_setup(
#     {
#         0: (True, [(IntervalPredicate(0, 10), 1), (IntervalPredicate(11, 20), 0)]),
#         1: (False, [(IntervalPredicate(0, 10), 0), (IntervalPredicate(11, 20), 1)])
#     }, algebra=alg)
# new = Sfa.from_state_setup(testautomaton.to_state_setup(), algebra=alg)

# print(testautomaton.get_shortest_path(testautomaton.initial_state, testautomaton.states[1]))
# print( [state.prefix for state in testautomaton.states])
# print(testautomaton.characteristic_sample())