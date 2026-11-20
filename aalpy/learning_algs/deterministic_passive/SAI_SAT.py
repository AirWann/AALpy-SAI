from itertools import combinations

from pysat.card import CardEnc
from pysat.formula import CNF, IDPool
from pysat.solvers import Solver

from aalpy.automata.Sfa import Sfa
from aalpy.base.BooleanAlgebra import IntervalAlgebra, IntervalPredicate
from aalpy.learning_algs.deterministic_passive.SAI_SMT import APTA, AbstractData


class SATIntervalEncoding:
    """
    Initializes the SAT encoding for learning a separating SFA from a sample of
    labeled words. The number of states and intervals per edge of said SFA is
    bounded.

    The encoding is similar to the encoding of a DFA, but additional constraints
    guarantee that each edge of the SFA has at most ``interval_num`` intervals.

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

        self.n = 1
        self.cnf = None
        self.x = []
        self.f = []
        self.edge = []

    def init_variables(self):
        """
        Initializes variables and returns their ID pool for the encoding.
        """

        pool = IDPool()
        # Invalidate any previous CNF because its literals refer to old variables.
        self.cnf = None

        # x[q][i]: the APTA prefix at q reaches SFA state i.
        self.x = [
            [pool.id(("x", q, i)) for i in range(self.n)]
            for q in range(self.apta.size())
        ]
        # f[i]: state i is accepting.
        self.f = [pool.id(("f", i)) for i in range(self.n)]
        # coverage[i][j][s]: the sampled symbol s labels an edge i -> j.
        self.edge = [
            [
                [
                    pool.id(("coverage", i, j, s))
                    for s in range(self.alphabet_size)
                ]
                for j in range(self.n)
            ]
            for i in range(self.n)
        ]

        return pool

    def encode(self):
        """
        Constructs CNF for ``state_num`` and stores its variables for decoding.
        """
        pool = self.init_variables()
        cnf = CNF()

        # Each APTA node reaches exactly one state.
        for q_choices in self.x:
            # At least one state is reached.
            cnf.append(q_choices)
            # At most one state is reached.
            cnf.extend([[-i, -j] for i, j in combinations(q_choices, 2)])
        # The root reaches state 0
        cnf.append([self.x[0][0]])

        for q, q_actual_node in enumerate(self.apta.node_list):
            # For each APTA node q related to a word in the sample...
            if q_actual_node.label is not None:
                # The reached state's acceptance must match the sample label.
                for i in range(self.n):
                    cnf.append(
                        [
                            -self.x[q][i],
                            self.f[i] if q_actual_node.label else -self.f[i],
                        ]
                    )

            # The edges of the SFA and the APTA's simulation must be
            # compatible.
            for symbol, child in q_actual_node.children.items():
                for i in range(self.n):
                    for j in range(self.n):
                        # x[node][i] and x[child][j] imply coverage[i][j][symbol].
                        cnf.append(
                            [
                                -self.x[q][i],
                                -self.x[child][j],
                                self.edge[i][j][symbol],
                            ]
                        )

        for i in range(self.n):
            # Each state i of the SFA has at most one outgoing edge for each
            # symbol.
            for symbol in range(self.alphabet_size):
                # A symbol may have no destination, but never two.
                q_choices = [self.edge[i][j][symbol] for j in range(self.n)]
                cnf.extend([[-a, -b] for a, b in combinations(q_choices, 2)])

            for j in range(self.n):
                # Each edge i -> j features at most ``interval_num`` intervals.
                # To count the intervals, we record consecutive sequences of
                # sample symbols covered by an edge.
                # Variables for the symbols occuring on edge i -> j.
                symbols_on_edge = self.edge[i][j]
                # These variables denote the starting points of consecutive sequences.
                sequence_starts = [symbols_on_edge[0]]
                for symbol in range(1, self.alphabet_size):
                    start = pool.id(("start", i, j, symbol))
                    # A transition from a 0 to a 1 forces the start of a new
                    # sequence; the converse is not needed for an at-most
                    # constraint.
                    cnf.append(
                        [
                            -symbols_on_edge[symbol],
                            symbols_on_edge[symbol - 1],
                            start,
                        ]
                    )
                    sequence_starts.append(start)
                # No need to encode this constraint if there are more invervals
                # allowed than symbols.
                if len(sequence_starts) > self.interval_num:
                    cnf.extend(
                        CardEnc.atmost(
                            lits=sequence_starts,
                            bound=self.interval_num,
                            vpool=pool,
                        ).clauses
                    )

        self.cnf = cnf
        return cnf

    def solve(self):
        """
        Solves an already constructed CNF; returns positive literals or None.
        """

        if self.cnf is None:
            raise RuntimeError("Call encode() before solve().")
        with Solver(
            name="cadical300", bootstrap_with=self.cnf.clauses
        ) as solver:
            result = solver.solve()
            if result is None:
                raise RuntimeError("SAT solver returned an unknown result.")
            if result is False:
                return None
            model = solver.get_model()
            if model is None:
                raise RuntimeError("SAT solver returned SAT without a model.")
            return frozenset(lit for lit in model if lit > 0)

    def encode_and_solve(self):
        """
        Builds and solves the CNF for the current number of states.
        """

        self.encode()
        return self.solve()

    def iterative_solving(self):
        """
        Returns a separating SFA with the first satisfiable state count.
        """

        while self.n <= self.max_states:
            model = self.encode_and_solve()
            if model is not None:
                return self.get_sfa_from_model(model)
            self.n += 1
        raise ValueError(
            f"No separating SFA found with at most {self.max_states} states "
            f"and {self.interval_num} intervals per edge."
        )

    def get_sfa_from_model(self, model):
        """
        Reconstructs an incomplete SFA from runs of covered sample symbols.

        ``model`` contains the positive literals returned by solve().
        """

        alphabet = self.abstract_data.index_to_integer
        state_dict = {}

        for i in range(self.n):
            # Building the edges...
            transitions = []
            for j in range(self.n):
                # Each consecutive sequence of covered symbols on an edge i -> j
                # in the model becomes a half-open interval from its first
                # symbol to one past its last.
                # This also covers any unobserved integers between those
                # symbols.
                symbols_on_edge = self.edge[i][j]
                sequence_starts = None

                # The extra iteration closes a run ending at the last symbol.
                for symbol in range(len(symbols_on_edge) + 1):
                    is_included = (
                        symbol < len(symbols_on_edge)
                        and symbols_on_edge[symbol] in model
                    )
                    # A 0-to-1 transition starts a new sequence.
                    if is_included and sequence_starts is None:
                        sequence_starts = symbol
                    # A 1-to-0 transition ends a sequence, and an interval is
                    # built.
                    elif not is_included and sequence_starts is not None:
                        transitions.append(
                            (
                                IntervalPredicate(
                                    alphabet[sequence_starts],
                                    alphabet[symbol - 1] + 1,
                                ),
                                f"s{j}",
                            )
                        )
                        sequence_starts = None

            # Builds the states
            state_dict[f"s{i}"] = (self.f[i] in model, transitions)

        return Sfa.from_state_setup(state_dict, algebra=IntervalAlgebra())
