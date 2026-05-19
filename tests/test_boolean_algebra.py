import pytest

#FULL DISCLOSURE: These tese were written by copilot
from aalpy.base.BooleanAlgebra import (
    AndPredicate,
    IntervalAlgebra,
    IntervalPredicate,
    OrPredicate,
    GenIntPredicate,
    MonotonicAlgebra,
    LetterIntervalAlgebra,
    LetterIntervalPredicate,
)


def test_interval_predicate_eval_and_negate():
    pred = IntervalPredicate(1, 5)
    assert pred.eval(3)
    assert not pred.eval(5)

    neg = pred.negate()
    assert isinstance(neg, OrPredicate)
    neg_parts = neg.predlist
    assert IntervalPredicate(None, 1) in neg_parts
    assert IntervalPredicate(5, None) in neg_parts


def test_zero_width_interval_unsat():
    alg = IntervalAlgebra()
    zero_width = IntervalPredicate(2, 2)

    assert not zero_width.eval(2)
    assert not alg.is_satisfiable(zero_width)


def test_minimize_predicate_merges_or_overlapping_intervals():
    alg = IntervalAlgebra()
    merged = alg.minimize_predicate(
        OrPredicate(
            {
                IntervalPredicate(1, 5),
                IntervalPredicate(3, 7),
                IntervalPredicate(10, 12),
            }
        )
    )

    assert isinstance(merged, OrPredicate)
    assert IntervalPredicate(1, 7) in merged.predlist
    assert IntervalPredicate(10, 12) in merged.predlist
def test_minimize_predicate_and_with_overlapping_intervals():
    alg = IntervalAlgebra()
    merged = alg.minimize_predicate(
        AndPredicate(
            {
                IntervalPredicate(1, 10),
                IntervalPredicate(3, 7),
            }
        )
    )
    assert isinstance(merged, IntervalPredicate)
    assert merged == IntervalPredicate(3, 7)


def test_minimize_predicate_and_non_overlapping_unsatisfiable():
    alg = IntervalAlgebra()
    merged = alg.minimize_predicate(
        AndPredicate(
            {
                IntervalPredicate(1, 3),
                IntervalPredicate(5, 7),
            }
        )
    )
    assert merged == alg.false()


def test_minimize_predicate_and_partial_overlap():
    alg = IntervalAlgebra()
    merged = alg.minimize_predicate(
        AndPredicate(
            {
                IntervalPredicate(1, 5),
                IntervalPredicate(3, 8),
                IntervalPredicate(4, 6),
            }
        )
    )
    assert isinstance(merged, IntervalPredicate)
    assert merged == IntervalPredicate(4, 5)


def test_minimize_predicate_and_single_interval():
    alg = IntervalAlgebra()
    merged = alg.minimize_predicate(
        AndPredicate({IntervalPredicate(2, 8)})
    )
    assert merged == IntervalPredicate(2, 8)


def test_minimize_predicate_nested_and_or_complex():
    alg = IntervalAlgebra()
    or_pred = OrPredicate(
        {IntervalPredicate(1, 3), IntervalPredicate(5, 7)}
    )
    and_pred = AndPredicate(
        {
            or_pred,
            IntervalPredicate(2, 6),
        }
    )
    minimized = alg.minimize_predicate(and_pred)
    # Should result in intersection of (1,3)∪(5,7) with (2,6) = (2,3)∪(5,6)
    assert isinstance(minimized, OrPredicate)
    assert IntervalPredicate(2, 3) in minimized.predlist
    assert IntervalPredicate(5, 6) in minimized.predlist


def test_minimize_predicate_and_unsatisfiable_interval():
    alg = IntervalAlgebra()
    merged = alg.minimize_predicate(
        AndPredicate(
            {
                IntervalPredicate(1, 5),
                IntervalPredicate(5, 8),
            }
        )
    )
    assert merged == alg.false()

def test_de_morgan_negation():
    alg = IntervalAlgebra()
    a = IntervalPredicate(0, 3)
    b = IntervalPredicate(5, 7)
    disj = OrPredicate({a, b})

    neg_disj = disj.negate()
    assert isinstance(neg_disj, AndPredicate)

    for sample in (-1, 1, 4, 6, 8):
        expected = not disj.eval(sample)
        assert neg_disj.eval(sample) == expected


def test_pick_witness_and_false_predicate():
    alg = IntervalAlgebra()
    assert alg.pick_witness(alg.true()) == 0
    assert alg.pick_witness(IntervalPredicate(4, 9)) == 4
    assert alg.pick_witness(alg.false()) is None


def test_letter_interval_predicate_eval_and_negate():
    alg = LetterIntervalAlgebra({"a", "b"})
    pred = alg.letter_interval("a", IntervalPredicate(1, 4))

    assert pred.eval(("a", 2))
    assert not pred.eval(("a", 4))
    assert not pred.eval(("b", 2))

    neg = pred.negate()
    assert neg.eval(("a", 0))
    assert neg.eval(("b", 2))
    assert not neg.eval(("a", 2))


def test_letter_interval_negate_same_letter():
    alg = LetterIntervalAlgebra({"a", "b"})
    pred = alg.letter_interval("a", IntervalPredicate(1, 4))
    neg = alg.negate_same_letter(pred)

    assert neg.eval(("a", 0))
    assert not neg.eval(("b", 0))
    assert not neg.eval(("a", 2))


def test_letter_interval_minimize_merges_same_letter():
    alg = LetterIntervalAlgebra({"a"})
    p1 = alg.letter_interval("a", IntervalPredicate(1, 3))
    p2 = alg.letter_interval("a", IntervalPredicate(3, 5))
    merged = alg.minimize_predicate(OrPredicate({p1, p2}))

    assert isinstance(merged, LetterIntervalPredicate)
    assert merged.interval == IntervalPredicate(1, 5)


def test_letter_interval_true_requires_all_letters():
    alg = LetterIntervalAlgebra({"a", "b"})
    pred = alg.or_op(alg.letter_true("a"), alg.letter_true("b"))
    assert alg.is_true(pred)
    assert not alg.is_true(alg.letter_true("a"))


def test_are_equivalent_merges_touching_intervals():
    alg = IntervalAlgebra()
    pred1 = OrPredicate({IntervalPredicate(1, 5), IntervalPredicate(5, 10)})
    pred2 = IntervalPredicate(1, 10)

    assert alg.are_equivalent(pred1, pred2)

def test_genint_predicate_eval_and_negate_strings():
    pred = GenIntPredicate("b", "f")
    assert pred.eval("b")
    assert pred.eval("e")
    assert not pred.eval("f")

    neg = pred.negate()
    assert isinstance(neg, OrPredicate)
    assert GenIntPredicate(None, "b") in neg.predlist
    assert GenIntPredicate("f", None) in neg.predlist


def test_monotonic_and_op_strings():
    alg = MonotonicAlgebra()
    res = alg.and_op(GenIntPredicate("b", "f"), GenIntPredicate("d", "h"))
    assert res == GenIntPredicate("d", "f")


def test_monotonic_minimize_or_merges_overlapping_strings():
    alg = MonotonicAlgebra()
    merged = alg.minimize_predicate(
        OrPredicate({GenIntPredicate("b", "f"), GenIntPredicate("d", "h")})
    )
    assert isinstance(merged, GenIntPredicate)
    assert merged == GenIntPredicate("b", "h")


def test_monotonic_minimize_or_merges_touching_strings():
    alg = MonotonicAlgebra()
    merged = alg.minimize_predicate(
        OrPredicate({GenIntPredicate("b", "d"), GenIntPredicate("d", "g")})
    )
    assert isinstance(merged, GenIntPredicate)
    assert merged == GenIntPredicate("b", "g")


def test_monotonic_minimize_and_or_mix_strings():
    alg = MonotonicAlgebra()
    or_pred = OrPredicate({GenIntPredicate("a", "c"), GenIntPredicate("e", "g")})
    and_pred = AndPredicate({or_pred, GenIntPredicate("b", "f")})
    minimized = alg.minimize_predicate(and_pred)
    assert isinstance(minimized, OrPredicate)
    assert GenIntPredicate("b", "c") in minimized.predlist
    assert GenIntPredicate("e", "f") in minimized.predlist


def test_monotonic_minimize_unsatisfiable_strings():
    alg = MonotonicAlgebra()
    merged = alg.minimize_predicate(
        AndPredicate({GenIntPredicate("b", "c"), GenIntPredicate("d", "e")})
    )
    assert merged == alg.false()


def test_monotonic_minimize_none_bounds_merge_to_true():
    alg = MonotonicAlgebra()
    merged = alg.minimize_predicate(
        OrPredicate({GenIntPredicate(None, "c"), GenIntPredicate("b", None)})
    )
    assert merged == alg.true()


def test_monotonic_minimize_empty_predicate():
    alg = MonotonicAlgebra()
    empty = GenIntPredicate(None, None, _is_empty=True)
    minimized = alg.minimize_predicate(empty)
    assert minimized == alg.false()

from dataclasses import dataclass

@dataclass(frozen=True, order=True)
class SymNum:
    symbol: str
    number: int


def test_monotonic_minimize_custom_ordered_type():
    alg = MonotonicAlgebra[SymNum](min_elt=SymNum("a", 0))
    a1 = SymNum("a", 1)
    a3 = SymNum("a", 3)
    b1 = SymNum("b", 1)
    b4 = SymNum("b", 4)

    # Interval [a1, b1) includes a1, a3 but not b1
    pred1 = GenIntPredicate(a1, b1)
    pred2 = GenIntPredicate(a3, b4)

    assert pred1.eval(a1)
    assert pred1.eval(a3)
    assert not pred1.eval(b1)
    assert pred2.eval(a3)
    assert not pred2.eval(b4)
    merged = alg.minimize_predicate(OrPredicate({pred1, pred2}))

    assert isinstance(merged, GenIntPredicate)
    assert merged == GenIntPredicate(a1, b4)

    # Intersection: (a1, b4) AND (a3, b1) = (a3, b1)
    inter = alg.minimize_predicate(AndPredicate({GenIntPredicate(a1, b4), GenIntPredicate(a3, b1)}))
    assert inter == GenIntPredicate(a3, b1)

def gen_symnums():
    return SymNum("a", np.random.randint(0, 100))