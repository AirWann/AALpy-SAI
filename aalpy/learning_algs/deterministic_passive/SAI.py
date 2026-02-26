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
    def __init__(self, children:List[Tuple[Predicate, 'SAINode']]=[], accepting=False, rejecting=False, prefix:Tuple= (), sample:Set[Tuple[Tuple, bool]]=None, algebra: BooleanAlgebra = IntervalAlgebra()):
        self.children = children
        self.prefix = prefix
        self.accepting = accepting
        self.algebra = algebra
        self.rejecting = rejecting
        self.sample = sample
    def shallow_copy(self):
        return SAINode(list(self.children), self.accepting, self.rejecting, self.prefix, self.sample, self.algebra)

    def __lt__(self, other):
        #smallest means either shorter prefix, or same length but lexicographically smaller
        #TODO this means we need to guarantee that prefix is the actual shortest access word
        if len(self.prefix) < len(other.prefix):
            return True
        elif len(self.prefix) == len(other.prefix):
            return self.prefix < other.prefix
        else:
            return False

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


def create_SPTA(data:Set,algebra,prefix=()):
    """
    Create the Symbolic Prefix Tree Acceptor for the given dataset and algebra.

    That is, all transitions are set to True and the "tree" is a linear chain of nodes corresponding to the longest sequence in the dataset. 
    Each node is labeled as accepting, rejecting, or both according to the labels of sequences in the dataset.
    """
    _, longest_seq = max(((len(seq), seq) for seq, _ in data), key=lambda x: x[0])
    def create_SPTA_rec(data:Set, prefix=(),remaining=()):
        empty_word_labels = [l for w, l in data if len(w) == 0]
        is_leaf = (remaining == ())
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

    return create_SPTA_rec(data, prefix, longest_seq)



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


class SAI:
    def __init__(self, data, algebra = IntervalAlgebra()):
        self.data = data
        self.algebra = algebra
        self.root = create_SPTA(data, algebra)

    def run_SAI(self):
        if self.root.accepting and self.root.rejecting:
            raise ValueError("Inconsistent root node in SPTA - cannot run SAI")
        red = [self.root]
        blue = [s for _,s in self.root.children]
        print(f"Initial red set: {red},\nInitial blue set: {blue}")
        while blue:
            qb = min(blue)
            pred, father = self.find_transition_to(qb)
            assert father in red, f"Father node {father.prefix} of min blue node {qb.prefix} not in red"
            became_red_flag = False
            for r in red:
               #try merges and check consistency with data 
                if r.accepting and qb.rejecting or r.rejecting and qb.accepting:
                    #don't even try
                    continue
                merged = self.merge(r, qb.shallow_copy(), father)
                if self.is_consistent(red + [merged]):
                    #merge is accepted
                    became_red_flag = True
                    if merged not in red:
                        red.append(merged)
                    blue.remove(qb)
                    new_blue = [s for _,s in merged.children if s not in red and s not in blue]
                    blue.extend(new_blue)
                    print(f"\nMerged {qb.prefix} into {r.prefix} to create {merged}")
                    
                    break
                else:
                    # undo merge by redirecting back transitions
                    if father is not None:
                        father.children = [((p, r) if c is merged else (p,c)) for (p, c) in father.children]
            if not became_red_flag:
                #try coloring red if consistent with data
                if self.is_consistent(red + [qb]):
                    became_red_flag = True
                    if qb not in red:
                        red.append(qb)
                    blue.remove(qb)
                    new_blue = [s for _,s in qb.children if s not in red and s not in blue]
                    blue.extend(new_blue)
                    print(f"\nColored {qb.prefix} red")
            if not became_red_flag:
                #split so the new qb can become red
                
                split_pred = self._find_split_predicate(red, qb,father)
                if split_pred is None:
                    raise ValueError(f"Could not find a split predicate for node with prefix {qb.prefix}")
                new_nodes = self.split_transition(qb, father, split_pred)
                blue.remove(qb)
                #find prefixes of new nodes to label them correctly
                for n in new_nodes:
                    pred_n = [p for p, c in father.children if c is n][0]
                    n.prefix = father.prefix + (self.algebra.pick_witness(pred_n),)
                    #TODO this is a hack
                blue.extend(new_nodes)
            print(f"Red: {red},\nBlue: {blue}")
        print ("Final red set:", red)
        return to_automaton(red)
        
    def _find_split_predicate(self,red:list[SAINode], node:SAINode,father:SAINode):
        old_pred = [p for p, c in father.children if c is node][0]
        relevant_letters = sorted({
            s[0][0]
            for s in father.sample
            if len(s[0]) > 0 and old_pred.eval(s[0][0])
        })

        # Need at least 2 distinct letters to create a non-trivial split.
        if len(relevant_letters) < 2:
            raise ValueError(f"Only one word coming to node {node.prefix} - cannot split")

        original_children = list(father.children)
        best_predicate = None

        # Try increasingly larger intervals: (-inf, letter[
        # Keep the largest consistent one; stop at first inconsistent.
        for letter in relevant_letters:
            print(f"Trying split at {letter}")
            candidate = IntervalPredicate(None, letter)
            try:
                split_nodes = self.split_transition(node, father, candidate)
                is_ok = self.is_consistent(red + [split_nodes[0]])
            except AssertionError:
                is_ok = False
            finally:
                # Undo tentative split before trying next candidate.
                father.children = list(original_children)

            if is_ok:
                best_predicate = candidate
        return best_predicate
    def split_transition(self, node:SAINode, father:SAINode, split_predicate:Predicate):
        """
        Split the transition from father to node by split_predicate, and return the two new child nodes created by the split.
        """
        #get the only transition leading to node
        old_predicate = [p for p, c in father.children if c is node][0]
        #get suffixes
        sample = father.sample
        #copy irrelevant transitions
        new_transitions = [(p, c) for p, c in father.children if p != old_predicate]
        
        new_predicate1 = self.algebra.and_op(old_predicate, split_predicate)
        new_predicate2 = self.algebra.and_op(old_predicate, split_predicate.negate())
        #sort suffixes appropriately and create new nodes (SPTA)
        data1 = {(s[1:], l) for s, l in sample if (len(s) > 0 and new_predicate1.eval(s[0]))}
        data2 = {(s[1:], l) for s, l in sample if (len(s) > 0 and new_predicate2.eval(s[0]))}
        assert data1 != set() and data2 != set(), f"Split on {split_predicate} does not partition the sample at node with prefix {node.prefix}"
        child1 = create_SPTA(data1, self.algebra, prefix=father.prefix + (self.algebra.pick_witness(new_predicate1),))
        child2 = create_SPTA(data2, self.algebra, prefix=father.prefix + (self.algebra.pick_witness(new_predicate2),))
        new_transitions.append((new_predicate1, child1))
        new_transitions.append((new_predicate2, child2))
        father.children = new_transitions
        return child1, child2

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

    def merge(self, red_node:SAINode, blue_node:SAINode, blue_father:SAINode=None):
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
        # Replace reference to blue_node in the graph by red_node
        if blue_father is not None:
            # Remove blue_node's transition
            blue_father.children = [((p, red_node) if c == blue_node else (p,c)) for (p, c) in blue_father.children]
        return red_node
    def find_transition_to(self, target: SAINode, current: SAINode=None, visited=None):
        """
        Find a transition to "target" in the graph
        """
        if current is None:
            current = self.root
        if visited is None:
            visited = set()
        if current in visited:
            return None
        visited.add(current)

        for pred, child in current.children:
            if child is target:
                return pred, current

        for _, child in current.children:
            res = self.find_transition_to(target, child, visited)
            if res is not None:
                return res
        raise ValueError(f"Transition to target node {target} not found")


#(ε, −), (0, +), (100, −), (0 · 0, −),(0 · 100, +)
#should learn automaton recognizing words with odd numbers of letters below 100
sample = {
    ((), False),
    ((0,), True),
    ((100,), False),
    ((0, 0), False),
    ((0, 100), True),
    ((0,0,0,0,0,0,0,0,0,0), False),
    ((0,0,0,0,0,0,0,100), True),
}
sai = SAI(sample, algebra=IntervalAlgebra())
automaton = sai.run_SAI()
print(automaton)