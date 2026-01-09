import pytest

from aalpy.base.BooleanAlgebra import (
    AndPredicate,
    IntervalAlgebra,
    IntervalPredicate,
    OrPredicate,
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


def test_minimize_predicate_merges_overlapping_intervals():
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


def test_are_equivalent_merges_touching_intervals():
    alg = IntervalAlgebra()
    pred1 = OrPredicate({IntervalPredicate(1, 5), IntervalPredicate(5, 10)})
    pred2 = IntervalPredicate(1, 10)

    assert alg.are_equivalent(pred1, pred2)
