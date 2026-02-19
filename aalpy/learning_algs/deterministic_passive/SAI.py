from functools import total_ordering
from typing import List,Tuple
from aalpy.base.BooleanAlgebra import IntervalPredicate, Predicate, BooleanAlgebra, IntervalAlgebra, OrPredicate

from aalpy.base import BooleanAlgebra

@total_ordering
class SAINode:
    __slots__ = ['accepting','rejecting', 'children', 'prefix', 'algebra']

    def __init__(self, children:List[Tuple[Predicate, 'SAINode']]=[], accepting=False, rejecting=False, algebra: BooleanAlgebra = IntervalAlgebra()):
        self.children = children
        self.prefix = ()
        self.accepting = accepting
        self.algebra = algebra
        self.rejecting = rejecting
    def shallow_copy(self):
        return SAINode(list(self.children), self.accepting, self.rejecting, self.algebra)

    def __lt__(self, other):
        return len(self.prefix) < len(other.prefix)

    def __eq__(self, other):
        return self.prefix == other.prefix

    def __hash__(self):
        return id(self) 
    
def check_sequence(root_node, seq, label):
    """
    Checks whether one labeled sequence in the dataset is valid in the current automaton.
    """
    node = root_node
    for symbol in seq:
        trans = [t for t in node.children if t[0].eval(symbol)]
        if not trans:
            raise ValueError('No transition for symbol ' + str(symbol) + ' from node with prefix ' + str(node.prefix))
        elif len(trans) > 1:
            raise ValueError('Non-deterministic automaton after prefix '+ str(node.prefix) + ' - Transitions :'+str(node.children))
        node = trans[0][1]
    return node.accepting if label else node.rejecting

def create_SPTA(data,algebra):
    max_len, longest_seq = max(((len(seq), seq) for seq, _ in data), key=lambda x: x[0])
    # Track which lengths have accepting and rejecting words
    accepting_lengths = set()
    rejecting_lengths = set()
    
    for seq, label in data:
        length = len(seq)
        if label:
            accepting_lengths.add(length)
        else:
            rejecting_lengths.add(length)
    if 0 in accepting_lengths and 0 in rejecting_lengths:
        raise ValueError('Data is inconsistent: empty sequence is both accepted and rejected.')
    # Build the linear chain from the end backwards
    current_node = None
    for length in range(max_len, 0, -1):
        is_accepting = length in accepting_lengths
        is_rejecting = length in rejecting_lengths

        # Create transition with True predicate
        if current_node is not None:
            children = [(algebra.true(), current_node)]
        else:
            children = []
        
        current_node = SAINode(children, is_accepting, is_rejecting, algebra)
    
    # Create root node
    if current_node is not None:
        root = SAINode([(algebra.true(), current_node)], 
                      0 in accepting_lengths, 
                      0 in rejecting_lengths, algebra)
    else:
        root = SAINode([], False, False, algebra)
    
    # Set prefixes for all nodes
    def set_prefixes(node, prefix=(),seq=()):
        node.prefix = prefix
        for _, child in node.children:
            set_prefixes(child, prefix + (seq[0],),seq[1:])
    
    set_prefixes(root,(),longest_seq)
    
    return root

print(create_SPTA([((), False)], IntervalAlgebra()))

def to_automaton(red:List[SAINode], automaton_type):
    from aalpy.automata import Sfa
    pass

class SAI:
    def __init__(self, data, algebra = IntervalAlgebra()):
        self.data = data
        self.algebra = algebra
        self.root = create_SPTA(data, algebra)

    def run_SAI(self):
        create_SPTA(self.data, self.algebra)
        red = [self.root]
        blue = list(red[0].children)
        #TODO implement SAI learning algorithm 
        pass
    def get_sample_at_state(self, node:SAINode, root:SAINode=None):
        """
        get all the suffixes of words passing through given node
        """
        #TODO seeing how much this is used, we might want to precompute this for all nodes and store it in the node itself
        sample = []
        for seq, label in self.data:
            curr_node = root if root is not None else self.root
            it = iter(seq)
            for symbol in it:
                trans = [t for t in curr_node.children if t[0].eval(symbol)]
                if not trans:
                    raise ValueError('No transition for symbol ' + str(symbol) +' from node with prefix ' + str(curr_node.prefix))
                if len(trans) > 1:
                    raise ValueError('Non-deterministic automaton after prefix ' + str(curr_node.prefix))
                curr_node = trans[0][1]

                if curr_node == node:
                    sample.append((tuple(it), label))
                    break
        return sample

    def split_transition(self, node:SAINode, root:SAINode, old_predicate:Predicate, split_predicate:Predicate,sample=None):
        """
        Split a transition from node guarded with old_predicate into two transitions according to split_predicate and its negation.
        """
        #get suffixes
        if sample is None:
            sample = self.get_sample_at_state(node, root)
        #copy irrelevant transitions
        new_transitions = [(p, c) for p, c in node.children if p != old_predicate]
        
        new_predicate1 = self.algebra.and_op(old_predicate, split_predicate)
        new_predicate2 = self.algebra.and_op(old_predicate, split_predicate.negate())
        #sort suffixes appropriately and create new nodes (SPTA)
        child1 = create_SPTA([(s[1:], l) for s, l in sample if new_predicate1.eval(s[0])], self.algebra)
        child2 = create_SPTA([(s[1:], l) for s, l in sample if new_predicate2.eval(s[0])], self.algebra)
        new_transitions.append((new_predicate1, child1))
        new_transitions.append((new_predicate2, child2))
        node.children = new_transitions

    def is_consistent(self,red:List[SAINode]):
        """
        Check if the current automaton is consistent with the data.
        """
        for node in red:
            if node.accepting and node.rejecting:
                return False
            sample = self.get_sample_at_state(node, red[0])
            if not set(s[0] for s in sample if s[1]).isdisjoint(set(s[0] for s in sample if not s[1])):
                return False
        
        return True
    def merge(self, red_node:SAINode, blue_node:SAINode):
        """
        Merge two nodes and return the root node of resulting model.
        No check for compatibility is needed as outgoing transitions from blue are always a single TRUE.
        """
        #TODO implement merge operation
        pass