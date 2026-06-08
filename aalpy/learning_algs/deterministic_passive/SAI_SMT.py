from itertools import product
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from aalpy.automata.Sfa import Sfa
from aalpy.base.BooleanAlgebra import IntervalPredicate

from cvc5.pythonic import Int, Bool, Solver, Or, Implies, Not, And


IntWord = Tuple[int, ...]
LabeledIntWord = Tuple[Sequence[int], bool]


@dataclass
class APTANode:
    prefix: IntWord
    children: Dict[int, int] = field(default_factory=dict)
    label: Optional[bool] = None


class APTA:
    def __init__(self, data: Iterable[LabeledIntWord]):
        self.node_list = [APTANode(prefix=())]
        for word, acceptance in data:
            self.insert(word, acceptance)

    def size(self) -> int:
        return len(self.node_list)

    def insert(self, word: Sequence[int], acceptance: bool) -> int:
        current_node = 0
        for symbol in word:
            if symbol not in self.node_list[current_node].children:
                # Create a new node for the prefix extended by the symbol.
                self.node_list.append(
                    APTANode(
                        prefix=self.node_list[current_node].prefix + (symbol,)
                    )
                )
                # Link the current node to the new node via the symbol.
                self.node_list[current_node].children[symbol] = (
                    len(self.node_list) - 1
                )
            current_node = self.node_list[current_node].children[symbol]
        # Does the node already have a label? If so, it must be consistent with
        # the new label.
        if (
            self.node_list[current_node].label is not None
            and self.node_list[current_node].label != acceptance
        ):
            raise ValueError(
                f"Inconsistent sample: word {word} is labeled both True and False."
            )
        self.node_list[current_node].label = acceptance
        return current_node


class SMTIntervalEncoding:
    """
    Initializes the SMT encoding for learning a separating SFA from a sample of
    labeled words. The number of states and intervals per edge of said SFA is
    bounded.

    Args:
        - data: the labeled words to learn from
        - state_num: number of states in the separating SFA
        - interval_num: maximum number of intervals per transition in the
          separating SFA
    """

    def __init__(self, data, state_num, interval_num):
        self.state_num = state_num
        self.interval_num = interval_num
        # The maximum integer in the sample bounds the possible intervals.
        self.max_value = max([symbol for word, _ in data for symbol in word])
        # Create the APTA from the data.
        self.apta = APTA(data)
        # Initialize the SMT solver.
        self.solver = Solver()
        # Initialize the various variable lists.
        self.l = []
        self.u = []
        self.f = []
        self.x = []

    def interval_variables(self):
        """
        Defines the interval variables and their direct domain constraints.
        l[i][j][k] and u[i][j][k] represent the lower and upper bounds of
        the k-th interval on the edge from state i to state j.

        Note that the encoding is lazy: it may be that the lower bound is
        bigger than the upper bound; the interval is then meant to be empty.
        """
        self.l = [
            [
                [Int(f"l_{i},{j},{k}") for k in range(self.interval_num)]
                for j in range(self.state_num)
            ]
            for i in range(self.state_num)
        ]
        self.u = [
            [
                [Int(f"u_{i},{j},{k}") for k in range(self.interval_num)]
                for j in range(self.state_num)
            ]
            for i in range(self.state_num)
        ]
        # Domain constraints to set up the interval bounds.
        for i, j, k in product(
            range(self.state_num),
            range(self.state_num),
            range(self.interval_num),
        ):
            self.solver.add(
                self.l[i][j][k] >= 0,
                self.l[i][j][k] <= self.max_value,
            )
            self.solver.add(
                self.u[i][j][k] >= 0,
                self.u[i][j][k] <= self.max_value,
            )

    def apta_variables(self):
        """
        Defines the APTA state variables and their direct domain constraints.
        x[node] = i if the word labelling node reaches state i of the
        separating SFA.
        """
        self.x = [Int(f"x_{node}") for node in range(self.apta.size())]
        # Projects an APTA node unto a state of the separating SFA.
        for node in range(self.apta.size()):
            self.solver.add(0 <= self.x[node], self.x[node] < self.state_num)

    def acceptance_variables(self):
        """
        Defines the acceptance variables.
        f[i] is true if state i of the separating SFA is accepting.
        """
        self.f = [Bool(f"f_{i}") for i in range(self.state_num)]

    def determinism_constraints(self):
        """
        These constraints guarantee that the separating SFA is deterministic,
        i.e. that intervals on different edges cannot intersect.
        """
        for i, j1, k1, k2 in product(
            range(self.state_num),
            range(self.state_num),
            range(self.interval_num),
            range(self.interval_num),
        ):
            # Note that the clauses are symmetric w.r.t. j1 and j2.
            for j2 in range(j1 + 1, self.state_num):
                # One of the following must hold:
                # 1. The first interval is empty.
                # 2. The second interval is empty.
                # 3. The first interval is to the right of the second.
                # 4. The first interval is to the left of the second.
                self.solver.add(
                    Or(
                        self.l[i][j1][k1] > self.u[i][j1][k1],
                        self.l[i][j2][k2] > self.u[i][j2][k2],
                        self.l[i][j1][k1] > self.u[i][j2][k2],
                        self.u[i][j1][k1] < self.l[i][j2][k2],
                    )
                )

    def state_compatibility_constraints(self):
        """
        These constraints guarantee that the separating SFA is compatible with
        the sample, i.e. that it accepts all positive words and rejects all
        negative words in the sample.
        """
        for node in range(self.apta.size()):
            for i in range(self.state_num):
                if self.apta.node_list[node].label is True:
                    self.solver.add(Implies(self.x[node] == i, self.f[i]))
                elif self.apta.node_list[node].label is False:
                    self.solver.add(Implies(self.x[node] == i, Not(self.f[i])))

    def edge_compatibility_constraints(self):
        """
        These constraints guarantee that the APTA is compatible with the edges
        of the separating SFA. i.e. that if an APTA node reaches state i and
        has a child by letter symbol that reaches state j, then symbol must be
        in the union of the intervals labelling the edge from i to j.
        """
        for node, i, j in product(
            range(self.apta.size()),
            range(self.state_num),
            range(self.state_num),
        ):
            for symbol, child in self.apta.node_list[node].children.items():
                self.solver.add(
                    Implies(
                        And(self.x[node] == i, self.x[child] == j),
                        Or(
                            [
                                And(
                                    self.l[i][j][k] <= symbol,
                                    symbol <= self.u[i][j][k],
                                )
                                for k in range(self.interval_num)
                            ]
                        ),
                    )
                )

    def encode_and_solve(self):
        """
        Adds all the constraints to the solver and checks for satisfiability.
        """
        self.interval_variables()
        self.apta_variables()
        self.acceptance_variables()
        self.determinism_constraints()
        self.state_compatibility_constraints()
        self.edge_compatibility_constraints()

        if self.solver.check():
            model = self.solver.model()
            return model
        return None


if __name__ == "__main__":
    sample = {
        (tuple([]), False),
        ((5,), False),
        ((10,), False),
        ((24,), True),
        ((15,), True),
        ((15, 2), True),
        ((18, 7), True),
        ((11, 30), True),
    }
    encoding = SMTIntervalEncoding(sample, state_num=2, interval_num=2)
    print(encoding.encode_and_solve())
