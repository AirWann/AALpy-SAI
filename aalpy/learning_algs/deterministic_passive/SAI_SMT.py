from itertools import product
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from aalpy.automata.Sfa import Sfa
from aalpy.base.BooleanAlgebra import IntervalPredicate
from SAI import create_SPTA

from cvc5.pythonic import *


IntWord = Tuple[int, ...]
LabeledIntWord = Tuple[Sequence[int], bool]


@dataclass
class SAPTANode:
    prefix: IntWord
    children: Dict[int, int] = field(default_factory=dict)
    label: Optional[bool] = None


class SAPTA:
    def __init__(self, data: Iterable[LabeledIntWord]):
        self.node_list = [SAPTANode(prefix=())]
        for word, acceptance in data:
            self.insert(word, acceptance)

    def size(self) -> int:
        return len(self.node_list)

    def insert(self, word: Sequence[int], acceptance: bool) -> int:
        current_node = 0
        for symbol in word:
            if symbol not in self.node_list[current_node].children:
                # Create a new node for the prefix extended by the symbol
                self.node_list.append(
                    SAPTANode(
                        prefix=self.node_list[current_node].prefix + (symbol,)
                    )
                )
                # Link the current node to the new node via the symbol
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
    Args:
        - state_num: number of states in the separating SFA
        - interval_num: maximum number of intervals per transition in the
          separating SFA
        - max_value: maximum value for the interval bounds
    """

    def __init__(self, data, state_num, interval_num, max_value):
        self.state_num = state_num
        self.interval_num = interval_num
        self.max_value = max_value
        # Create the SPTA from the data.
        self.sapta = SAPTA(data)
        # Initialize the SMT solver
        self.solver = Solver()
        # Initialize the various variable lists
        self.l = []
        self.u = []
        self.f = []
        self.x = []

    def encode_state_variables(self):
        self.f = [Bool(f"acc_{i}") for i in range(self.state_num)]

    def encode_interval_variables(self):
        # Initialize the interval variables: l[i][j][k] and u[i][j][k] represent
        # the lower and upper bounds of the k-th interval on the edge from state
        # i to state j.
        # Note that the encoding is lazy: it may be that the lower bound is
        # bigger than the upper bound. The interval is then meant to be empty.
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
        # Constraint: set up the interval bounds
        for i, j1, k1 in product(
            range(self.state_num),
            range(self.state_num),
            range(self.interval_num),
        ):
            self.solver.add(
                self.l[i][j1][k1] >= 0,
                self.l[i][j1][k1] <= self.max_value,
            )
            self.solver.add(
                self.u[i][j1][k1] >= 0,
                self.u[i][j1][k1] <= self.max_value,
            )
            # Constraint: guarantee determinism, i.e. intervals on different
            # edges cannot intersect.
            for j2 in range(j1 + 1, self.state_num):
                for k2 in range(self.interval_num):
                    # One of the following must hold:
                    # 1. The first interval is empty
                    # 2. The second interval is empty
                    # 3. The first interval is completely to the right of the
                    #    second
                    # 4. The first interval is completely to the left of the
                    #    second
                    self.solver.add(
                        Or(
                            self.l[i][j1][k1] > self.u[i][j1][k1],
                            self.l[i][j2][k2] > self.u[i][j2][k2],
                            self.l[i][j1][k1] > self.u[i][j2][k2],
                            self.u[i][j1][k1] < self.l[i][j2][k2],
                        )
                    )

    def encode_compatibility_constraints(self):
        x = [Int(f"x_{node}") for node in range(self.sapta.size())]
        
        for node, i in product(range(self.sapta.size()), range(self.state_num)):

            # For each node and state, we have a variable x[node][state] which is
            # true if the node is compatible with the state.
            self.x.append(
                [Bool(f"x_{node}_{i}") for i in range(self.state_num)]
            )

        return 0
