## Plan: Letter+Interval SFA Support

Add a new letter+interval predicate and algebra over input symbols (letter, value), adapt SAI’s SPTA and splitting to branch by letter and split on values, and add tests while keeping existing Sfa behavior unchanged.

**Steps**
1. Define a new predicate/algebra in aalpy/base/BooleanAlgebra.py for a finite alphabet, using input symbols as (letter, value) tuples and IntervalPredicate on the value component.
2. Implement core algebra operations (true/false/and/or/negate/is_satisfiable/is_true/are_equivalent/pick_witness/minimize_predicate) to support SFA completeness checks and SAI splitting for the new predicate type. Another useful operation is negate_same_letter that negates the interval but keeps the same letter.
3. Update create_SPTA in aalpy/learning_algs/deterministic_passive/SAI.py to build a branching tree by first letter, using letter-specific “true interval” predicates and representative symbols for prefixes.
4. Update SAI splitting logic in aalpy/learning_algs/deterministic_passive/SAI.py to compute split candidates on the value component while preserving the letter constraint from the parent transition. negate_same_letter is useful here.
5. Keep Sfa unchanged, but confirm SFA methods relying on pick_witness and predicate eval work with (letter, value) tuples in aalpy/automata/Sfa.py.
6. Add tests in tests/ to cover the new predicate/algebra behavior and one small SAI integration test with letter+interval inputs.
7. Optional: extend SAITesting/utilities.py to generate random letter+interval SFA samples if you want benchmarks.

**Relevant files**
- aalpy/base/BooleanAlgebra.py — add new predicate and algebra for (letter, value)
- aalpy/learning_algs/deterministic_passive/SAI.py — update SPTA and split logic
- aalpy/automata/Sfa.py — verify compatibility with new algebra
- tests/test_boolean_algebra.py — add predicate/algebra unit tests
- SAITesting/utilities.py — optional sample generation helpers
- about_SAI.md — optional documentation update

**Verification**
1. Run pytest for tests/test_boolean_algebra.py and the new SAI test.
2. Run a small SAI sample with letter+interval inputs to confirm the learned SFA is input-complete and consistent with the sample.

**Decisions**
- Input symbols are tuples (letter, value) and predicates are letter-specific intervals.
- The alphabet is finite and provided to the new LetterIntervalAlgebra.
- Existing Sfa API remains unchanged.

**Further Considerations**
1. Confirm the concrete letter type (str, int, enum) and whether a stable ordering is needed for prefix comparisons.
