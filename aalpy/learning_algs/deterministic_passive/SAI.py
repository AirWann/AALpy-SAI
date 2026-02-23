from functools import total_ordering
from typing import List, Set,Tuple

from aalpy.automata.Sfa import Sfa
from aalpy.base.BooleanAlgebra import IntervalPredicate, Predicate, BooleanAlgebra, IntervalAlgebra, OrPredicate

from aalpy.base import BooleanAlgebra

@total_ordering
class SAINode:
    """
        Node in the SAI algorithm.

        - children: list of pairs (predicate, child_node) representing outgoing transitions
        - accepting: whether the node is accepting
        - rejecting: whether the node is rejecting
        - prefix: a single prefix reaching this state
        - sample: the set of labeled suffixes of samples in the dataset after reaching this node
        - algebra: the Boolean algebra used for predicates
    """
    __slots__ = ['accepting','rejecting', 'children', 'prefix', 'sample', 'algebra']
    def __init__(self, children:List[Tuple[Predicate, 'SAINode']]=[], accepting=False, rejecting=False, prefix = (), sample:Set[Tuple[Tuple, bool]]=None, algebra: BooleanAlgebra = IntervalAlgebra()):
        self.children = children
        self.prefix = prefix
        self.accepting = accepting
        self.algebra = algebra
        self.rejecting = rejecting
        self.sample = sample
    def shallow_copy(self):
        return SAINode(list(self.children), self.accepting, self.rejecting, self.prefix, self.sample, self.algebra)

    def __lt__(self, other):
        return len(self.prefix) < len(other.prefix)

    def __eq__(self, other):
        return self.prefix == other.prefix

    def __hash__(self):
        return id(self) 
    def __str__(self) -> str:
        return f"Node(prefix={self.prefix}, accepting={self.accepting}, rejecting={self.rejecting}, children={[(str(p), c.prefix) for p, c in self.children]})"
    
    def __repr__(self):
        return self.__str__()

def check_sequence(root_node, seq, label):
    """
    Checks whether one labeled sequence in the dataset is valid in the current automaton.
    """
    node = root_node
    for symbol in seq:
        trans = [t for t in node.children if t[0].eval(symbol)]
        if not trans:
            raise ValueError(f'No transition for symbol {symbol} from node with prefix {node.prefix}')
        elif len(trans) > 1:
            raise ValueError(f'Non-deterministic automaton after prefix {node.prefix} - Transitions :{node.children}')
        node = trans[0][1]
    return node.accepting if label else node.rejecting


def create_SPTA(data:Set,algebra):
    """
    Create the Symbolic Prefix Tree Acceptor for the given dataset and algebra.

    That is, all transitions are set to True and the "tree" is a linear chain of nodes corresponding to the longest sequence in the dataset. 
    Each node is labeled as accepting, rejecting, or both according to the labels of sequences in the dataset.
    """
    _, longest_seq = max(((len(seq), seq) for seq, _ in data), key=lambda x: x[0])
    def create_SPTA_rec(data:Set, prefix=(),remaining=()):
        empty_word_labels = [l for w, l in data if len(w) == 0]
        is_leaf = all(len(w) == 0 for w, _ in data)
        accepting = True in empty_word_labels
        rejecting = False in empty_word_labels
        if is_leaf:
            node = SAINode(accepting=accepting, rejecting=rejecting, children=[], prefix=prefix, sample=data, algebra=algebra)
            return node
        else:
            child_data = {(w[1:], l) for w, l in data if len(w) > 0}
            child = create_SPTA_rec(child_data, prefix + (remaining[0],), remaining[1:])
            node = SAINode(accepting=accepting, rejecting=rejecting, prefix=prefix, sample=data, algebra=algebra)
            node.children = [(algebra.true(), child)]
            return node

    return create_SPTA_rec(data, (),longest_seq)



def to_automaton(red: List[SAINode]) -> Sfa:
    """
    Convert a list of SAINodes to an SFA.

    Assumptions:
    - `red` contains all states referenced in transitions.
    - Node with prefix () is the initial state if present, otherwise red[0].
    """
    from aalpy.automata.Sfa import SfaState, Sfa

    if not red:
        raise ValueError("Empty node list given to to_automaton")

    # ensure all nodes referenced by transitions are present
    # node_set = set(red)
    # queue = list(red)
    # while queue:
    #     n = queue.pop(0)
    #     for _, child in n.children:
    #         if child not in node_set:
    #             node_set.add(child)
    #             queue.append(child)
    # nodes = list(node_set)

    # build states
    node_to_state = {}
    for i, n in enumerate(red):
        if n.accepting and n.rejecting:
            raise ValueError(f"Inconsistent node at prefix {n.prefix}")
        sid = f"s{i}" #if n.prefix is None else str(n.prefix)
        st = SfaState(sid, is_accepting=n.accepting)
        st.prefix = n.prefix
        node_to_state[n] = st
    
    # connect transitions
    for n in red:
        src = node_to_state[n]
        for pred, child in n.children:
            if child not in node_to_state:
                raise ValueError(f"Transition target missing from node set for prefix {child.prefix} and predicate {pred}.")
            src.transitions.append((pred, node_to_state[child]))

    # pick initial state
    root_node = next((n for n in red if n.prefix == ()), red[0])
    algebra = getattr(root_node, "algebra", None)

    return Sfa(node_to_state[root_node], list(node_to_state.values()), algebra=algebra)


spta = create_SPTA({((1,2,3), False)}, IntervalAlgebra())
all_nodes = []
while spta.children:
    all_nodes.append(spta)
    spta = spta.children[0][1]
all_nodes.append(spta)
#print(all_nodes)
print(to_automaton(all_nodes))

class SAI:
    def __init__(self, data, algebra = IntervalAlgebra()):
        self.data = data
        self.algebra = algebra
        self.root = create_SPTA(data, algebra)

    def run_SAI(self):
        red = [self.root]
        blue = list(red[0].children)
        #TODO implement SAI learning algorithm 
        pass

    def split_transition(self, node:SAINode, root:SAINode, old_predicate:Predicate, split_predicate:Predicate):
        """
        Split a transition from node guarded with old_predicate into two transitions according to split_predicate and its negation.
        """
        #get suffixes
        sample = node.sample
        #copy irrelevant transitions
        new_transitions = [(p, c) for p, c in node.children if p != old_predicate]
        
        new_predicate1 = self.algebra.and_op(old_predicate, split_predicate)
        new_predicate2 = self.algebra.and_op(old_predicate, split_predicate.negate())
        #sort suffixes appropriately and create new nodes (SPTA)
        child1 = create_SPTA({(s[1:], l) for s, l in sample if new_predicate1.eval(s[0])}, self.algebra)
        child2 = create_SPTA({(s[1:], l) for s, l in sample if new_predicate2.eval(s[0])}, self.algebra)
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
            pos = {w for w, l in node.sample if l}
            neg = {w for w, l in node.sample if not l}
            if pos & neg:  # If there is any word label positively and negatively
                return False
        return True
    
    def _replace_node_reference(self, current: SAINode, old_node: SAINode, new_node: SAINode, visited=None)->bool:
        """
        Replace all transition targets equal to old_node by new_node in the graph rooted at current.
        """
        if visited is None:
            visited = set()
        if current in visited:
            return False
        visited.add(current)

        # Check children
        for i, (pred, child) in enumerate(current.children):
            if child is old_node:
                current.children[i] = (pred, new_node)
                return True

        # Recurse until found once
        for _, child in current.children:
            if self._replace_node_reference(child, old_node, new_node, visited):
                return True
        return False
    def _merge_rec(self, red_node: SAINode, other_node: SAINode):
        """
        Recursive merge of other_node into red_node.
        """
        # Merge labels and samples at current node
        red_node.accepting = red_node.accepting or other_node.accepting
        red_node.rejecting = red_node.rejecting or other_node.rejecting

        red_sample = red_node.sample if red_node.sample is not None else set()
        other_sample = other_node.sample if other_node.sample is not None else set()
        red_node.sample = red_sample | other_sample

        # Nothing to propagate if  no outgoing transitions
        if not red_node.children or not other_node.children:
            return

        # Project other_node's sample through each red predicate and recurse
        for pred, red_child in red_node.children:
            projected = {
                (w[1:], lbl)
                for w, lbl in other_sample
                if len(w) > 0 and pred.eval(w[0])
            }
            if not projected:
                continue

            projected_spta = create_SPTA(projected, self.algebra)
            self._merge_rec(red_child, projected_spta)

    def merge(self, red_node:SAINode, blue_node:SAINode):
        """
        Merge two nodes and return the root node of resulting model.
        No check for compatibility is needed as outgoing transitions from blue are always a single TRUE.
        Samples are merged by union, and the resulting node is accepting (resp rejecting) if either of the merged nodes is.
        """
        if red_node is blue_node:
            print("Warning: trying to merge a node with itself")
            return red_node
        # Merge blue into red
        self._merge_rec(red_node, blue_node)
        # Replace all references to blue_node in the graph by red_node
        self._replace_node_reference(self.root, blue_node, red_node)
        return red_node