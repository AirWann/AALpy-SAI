from aalpy.base.BooleanAlgebra import LetterIntervalAlgebra, LetterIntervalPredicate
from aalpy.learning_algs.deterministic_passive.SAI import create_SPTA


def test_spta_branches_by_letter():
    alg = LetterIntervalAlgebra({"a", "b"})
    sample = {
        ((), False),
        ((("a", 1),), True),
        ((("b", 2),), False),
        ((("a", 3), ("b", 1)), True),
    }

    root = create_SPTA(sample, alg)
    letters = {p.letter for p, _ in root.children if isinstance(p, LetterIntervalPredicate)}

    assert letters == {"a", "b"}
    assert len(root.children) == 2
