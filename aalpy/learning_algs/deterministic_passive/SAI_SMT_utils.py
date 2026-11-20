from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np

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
        # Handling numpy Boolean values.
        if acceptance == np.True_:
            acceptance_bool = True
        elif acceptance == np.False_:
            acceptance_bool = False
        else:
            acceptance_bool = bool(acceptance)

        current_node = 0
        for symbol in word:
            if symbol not in self.node_list[current_node].children:
                # Creates a new node for the prefix extended by the symbol.
                self.node_list.append(
                    APTANode(
                        prefix=self.node_list[current_node].prefix + (symbol,)
                    )
                )
                # Links the current node to the new node via the symbol.
                self.node_list[current_node].children[symbol] = (
                    len(self.node_list) - 1
                )
            current_node = self.node_list[current_node].children[symbol]
        # Does the node already have a label? If so, it must be consistent with
        # the new label.
        if (
            self.node_list[current_node].label is not None
            and self.node_list[current_node].label != acceptance_bool
        ):
            raise ValueError(
                f"Inconsistent sample: word {word} is labeled both True and False."
            )
        self.node_list[current_node].label = acceptance_bool
        return current_node

    def display(self, output_file: Optional[str] = None) -> str:
        """
        Returns the APTA as DOT and optionally save it to a Graphviz file.
        """

        lines = [
            "digraph APTA {",
            "  rankdir=LR;",
            '  __start0 [shape=none,label=""];',
            "  __start0 -> q0;",
        ]

        # Draws the states.
        for index, node in enumerate(self.node_list):
            if node.label is True:
                shape = "doublecircle"
                style = "solid"
            elif node.label is False:
                shape = "circle"
                style = "solid"
            else:
                shape = "circle"
                style = "dotted"

            lines.append(
                f'  q{index} [shape={shape},style={style},label="{index}"];'
            )
        # Draws the edges.
        for index, node in enumerate(self.node_list):
            for symbol, child in sorted(
                node.children.items(), key=lambda t: t[0]
            ):
                lines.append(f'  q{index} -> q{child} [label="{symbol}"];')

        lines.append("}")
        dot_output = "\n".join(lines)

        if output_file is not None:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(dot_output)

        return dot_output


class AbstractData:
    """
    Converts a sample of labeled words of integers into an abstract
    representation where each unique integer is mapped to a unique index
    starting from 0.

    This is useful for reducing the size of the intervals in the SMT encoding
    based on the sample size instead of the maximum and minimum integer values
    in the sample.
    """

    def __init__(self, data: Iterable[LabeledIntWord]):
        assert data, "The sample must not be empty."

        # Lists all unique integers in the sample.
        unique_integers = {symbol for word, _ in data for symbol in word}
        # Then maps them to a unique index starting from 0.
        self.index_to_integer = sorted(unique_integers)
        self.max_index = len(self.index_to_integer) - 1
        self.integer_to_index = {
            int_val: index
            for index, int_val in enumerate(self.index_to_integer)
        }
        self.min_value = self.index_to_integer[0]
        self.max_value = self.index_to_integer[-1]

        # Converts the data to the abstract representation.
        self.abstract_data = []
        for word, label in data:
            abstract_word = tuple(
                self.integer_to_index[symbol] for symbol in word
            )
            self.abstract_data.append((abstract_word, label))

    def abstract_to_real(self, int) -> int:
        if int < 0:
            return self.min_value - 1
        elif int >= len(self.index_to_integer):
            return self.max_value + 1
        else:
            return self.index_to_integer[int]
