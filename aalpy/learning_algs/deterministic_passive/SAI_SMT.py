from itertools import product

from cvc5.pythonic import And, Bool, Implies, Int, Not, Or, Solver, sat

from aalpy.automata.Sfa import Sfa
from aalpy.base.BooleanAlgebra import IntervalAlgebra, IntervalPredicate
from aalpy.learning_algs.deterministic_passive.SAI_SMT_utils import (
    APTA,
    AbstractData,
)


class SfaSmtLearner:
    """
    Using a SMT solver, learns a separating SFA from a sample of labeled words.
    The number of states and intervals per edge of said SFA is bounded.

    This algorithm is outdated and has been replaced by the SAT-based algorithm
    in SAI_SAT.py.

    Args:
        - data: the labeled words to learn from
        - max_states: maximum number of states in the separating SFA
        - interval_num: maximum number of intervals per transition in the
          separating SFA
    """

    def __init__(self, data, max_states, interval_num):
        assert max_states > 0, "The number of states must be positive."
        assert interval_num > 1, (
            "The number of intervals per edge must be greater than 1."
        )

        # The alphabet and sample are abstracted to integers for the encoding.
        self.abstract_data = AbstractData(data)
        self.apta = APTA(self.abstract_data.abstract_data)
        self.alphabet_size = len(self.abstract_data.index_to_integer)

        self.max_states = max_states
        self.interval_num = interval_num

        # The maximum and minimum integers occurring in the sample bounds the
        # possible intervals.
        self.max_value = self.alphabet_size + 1
        self.min_value = -1

        self.n = 1
        self.solver = Solver()
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
                for j in range(self.n)
            ]
            for i in range(self.n)
        ]
        self.u = [
            [
                [Int(f"u_{i},{j},{k}") for k in range(self.interval_num)]
                for j in range(self.n)
            ]
            for i in range(self.n)
        ]

        constraints = []
        for i, j, k in product(
            range(self.n),
            range(self.n),
            range(self.interval_num),
        ):
            lower = self.l[i][j][k]
            upper = self.u[i][j][k]
            # Domain constraints to set up the interval bounds.
            constraints.append(lower >= self.min_value)
            constraints.append(lower <= self.max_value)
            constraints.append(upper >= self.min_value)
            constraints.append(upper <= self.max_value)
            # Enforces a canonical representation of the empty intervals.
            constraints.append(
                Implies(
                    lower > upper,
                    And(lower == self.max_value, upper == self.min_value),
                )
            )
            # Guarantees that the intervals are ordered and non-overlapping.
            if k > 0:
                prev_lower = self.l[i][j][k - 1]
                prev_upper = self.u[i][j][k - 1]
                constraints.append(
                    Or(
                        lower > upper,
                        And(prev_lower <= prev_upper, prev_upper < lower),
                    )
                )

        if constraints:
            self.solver.add(*constraints)

    def apta_variables(self):
        """
        Defines the APTA state variables and their direct domain constraints.
        x[node] = i if the word labelling node reaches state i of the
        separating SFA.
        """

        self.x = [Int(f"x_{node}") for node in range(self.apta.size())]
        # Projects an APTA node unto a state of the separating SFA.
        # Node 0 is the initial state.
        constraints = [self.x[0] == 0]
        for node in range(1, self.apta.size()):
            constraints.append(0 <= self.x[node])
            constraints.append(self.x[node] < self.n)

        if constraints:
            self.solver.add(*constraints)

    def acceptance_variables(self):
        """
        Defines the acceptance variables.
        f[i] is true if state i of the separating SFA is accepting.
        """

        self.f = [Bool(f"f_{i}") for i in range(self.n)]

    def determinism_constraints(self):
        """
        These constraints guarantee that the separating SFA is deterministic,
        i.e. that intervals on different edges cannot intersect.
        """

        constraints = []
        for i, j1, k1, k2 in product(
            range(self.n),
            range(self.n),
            range(self.interval_num),
            range(self.interval_num),
        ):
            # Note that the clauses are symmetric w.r.t. j1 and j2.
            for j2 in range(j1 + 1, self.n):
                # One of the following must hold:
                # 1. The first interval is empty.
                # 2. The second interval is empty.
                # 3. The first interval is to the right of the second.
                # 4. The first interval is to the left of the second.
                constraints.append(
                    Or(
                        self.l[i][j1][k1] > self.u[i][j1][k1],
                        self.l[i][j2][k2] > self.u[i][j2][k2],
                        self.l[i][j1][k1] > self.u[i][j2][k2],
                        self.u[i][j1][k1] < self.l[i][j2][k2],
                    )
                )

        if constraints:
            self.solver.add(*constraints)

    def state_compatibility_constraints(self):
        """
        These constraints guarantee that the separating SFA is compatible with
        the sample, i.e. that it accepts all positive words and rejects all
        negative words in the sample.
        """

        constraints = []
        for node in range(self.apta.size()):
            for i in range(self.n):
                if self.apta.node_list[node].label is True:
                    constraints.append(Implies(self.x[node] == i, self.f[i]))
                elif self.apta.node_list[node].label is False:
                    constraints.append(
                        Implies(self.x[node] == i, Not(self.f[i]))
                    )

        if constraints:
            self.solver.add(*constraints)

    def edge_compatibility_constraints(self):
        """
        These constraints guarantee that the APTA is compatible with the edges
        of the separating SFA. i.e. that if an APTA node reaches state i and
        has a child by letter symbol that reaches state j, then symbol must be
        in the union of the intervals labelling the edge from i to j.
        """

        for node, i, j in product(
            range(self.apta.size()),
            range(self.n),
            range(self.n),
        ):
            constraints = []
            for symbol, child in self.apta.node_list[node].children.items():
                constraints.append(
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
            if constraints:
                self.solver.add(*constraints)

    def encode_and_solve(self):
        """
        Adds all the constraints to the solver and checks for satisfiability.
        """

        print(
            f"* Encoding and solving the SMT problem for {self.n} state(s)..."
        )

        self.interval_variables()
        self.apta_variables()
        self.acceptance_variables()
        self.determinism_constraints()
        self.state_compatibility_constraints()
        self.edge_compatibility_constraints()

        if self.solver.check() == sat:
            model = self.solver.model()
            return model
        return None

    def iterative_solving(self):
        """
        Iteratively increases the number of states in the separating SFA until a
        solution is found or the maximum number of states is reached.
        """
        while self.n <= self.max_states:
            model = self.encode_and_solve()
            # A model is found, return the corresponding SFA.
            if model is not None:
                sfa = self.get_sfa_from_model(model)
                return sfa

            self.n += 1
            # Resets
            self.solver = Solver()
            self.l = []
            self.u = []
            self.f = []
            self.x = []

        raise ValueError(
            f"No separating SFA found with at most {self.max_states} states and {self.interval_num} intervals per edge."
        )

    def display_model(self, model):
        print(f"{self.n} states, {self.interval_num} intervals per edge")
        print(
            f"Accepting states: {[i for i in range(self.n) if model[self.f[i]]]}"
        )
        print("Edges:")
        for i, j in product(range(self.n), range(self.n)):
            edge_str = f"{i} -> {j} :"
            for k in range(self.interval_num):
                edge_str += f" [{self.abstract_data.abstract_to_real(model[self.l[i][j][k]].as_long())}, {self.abstract_data.abstract_to_real(model[self.u[i][j][k]].as_long())}]"
            print(edge_str)

    def get_sfa_from_model(self, model) -> Sfa:
        """
        Returns the (incomplete) separating SFA corresponding to the given model.
        """
        state_dict = {}
        for i in range(self.n):
            transitions = []
            # Builds all the outgoing transitions from state i.
            for j in range(self.n):
                for k in range(self.interval_num):
                    low = int(
                        self.abstract_data.abstract_to_real(
                            model[self.l[i][j][k]].as_long()
                        )
                    )
                    up = int(
                        self.abstract_data.abstract_to_real(
                            model[self.u[i][j][k]].as_long()
                        )
                    )
                    # Only non-empty intervals are added to the SFA.
                    if low <= up:
                        transitions.append(
                            (IntervalPredicate(low, up + 1), f"s{j}")
                        )

            state_dict[f"s{i}"] = (bool(model[self.f[i]]), transitions)

        return Sfa.from_state_setup(state_dict, algebra=IntervalAlgebra())
