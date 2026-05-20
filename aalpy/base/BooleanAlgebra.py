"""
Abstract base classes for Predicates and Boolean Algebras used in Symbolic Automata.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, Hashable, Optional, Protocol, Self, Set, Tuple, TypeVar

Domain = TypeVar('Domain')
class Ordered(Protocol):
    """Protocol for types that support comparison operators."""
    def __lt__(self, other: Self) -> bool: ...
    def __le__(self, other: Self) -> bool: ...
    def __gt__(self, other: Self) -> bool: ...
    def __ge__(self, other: Self) -> bool: ...

OrderedDomain = TypeVar('OrderedDomain', bound=Ordered) 
LetterType = TypeVar('LetterType', bound=Hashable)
class Predicate(ABC, Generic[Domain]):
    """
    Abstract base class for predicates used in symbolic automata
    """

    @abstractmethod
    def eval(self, element: Domain) -> bool:
        """
        Check if the predicate is satisfied by the given element.
        """
        pass

    @abstractmethod
    def negate(self) -> 'Predicate':
        """
        Return the negation of the predicate.
        """
        pass

    @abstractmethod
    def __repr__(self) -> str:
        """Return a string representation of the predicate."""
        pass

    @abstractmethod
    def __eq__(self, other) -> bool:
        """Check equality with another predicate."""
        pass

    @abstractmethod
    def __hash__(self) -> int:
        """Return hash value for use in sets and dictionaries."""
        pass


class BooleanAlgebra(ABC, Generic[Domain]):
    """
    Abstract base class for Boolean Algebras.
    """

    @abstractmethod
    def true(self) -> Predicate:
        """
        Return the True predicate (top).
        """
        pass

    @abstractmethod
    def false(self) -> Predicate:
        """
        Return the False predicate (bottom).
        """
        pass

    @abstractmethod
    def and_op(self, pred1: Predicate, pred2: Predicate) -> Predicate:
        """
        Return the conjunction (AND) of two predicates.
        """
        pass

    @abstractmethod
    def or_op(self, pred1: Predicate, pred2: Predicate) -> Predicate:
        """
        Return the disjunction (OR) of two predicates.
        """
        pass

    @abstractmethod
    def is_satisfiable(self, predicate: Predicate) -> bool:
        """
        Check if the predicate is satisfiable.
        """
        pass

    @abstractmethod
    def is_true(self, predicate: Predicate) -> bool:
        """
        Check if the predicate is always true (tautology).
        """
        pass

    @abstractmethod
    def are_equivalent(self, pred1: Predicate, pred2: Predicate) -> bool:
        """
        Check if two predicates are equivalent.
        """
        pass


    @abstractmethod
    def pick_witness(self, predicate: Predicate) -> Domain:
        """
        Pick a witness (an element that satisfies the predicate).
        """
        pass

    @abstractmethod
    def minimize_predicate(self, predicate: Predicate) -> Predicate:
        """
        Minimize or simplify the predicate.
        """
        pass



class OrPredicate(Predicate):
    def __init__(self,predlist: set[Predicate]):
        self.predlist = predlist
    def eval(self, element: Any) -> bool:
        flag = False
        for pred in self.predlist:
            flag = flag or pred.eval(element)
        return flag
    def negate(self) -> 'Predicate':
        negated_preds = {pred.negate() for pred in self.predlist}
        return AndPredicate(negated_preds)
    def __repr__(self) -> str:
        return " OR ".join(["(" + str(pred) + ")" for pred in self.predlist])
    def __eq__(self, other) -> bool:
        if not isinstance(other, OrPredicate):
            return False
        return self.predlist == other.predlist
    def __hash__(self) -> int:
        return hash(frozenset(self.predlist))
    
class AndPredicate(Predicate):
    def __init__(self,predlist: set[Predicate]):
        self.predlist = predlist
    def eval(self, element: Any) -> bool:
        flag = True
        for pred in self.predlist:
            flag = flag and pred.eval(element)
        return flag
    def negate(self) -> 'Predicate':
        negated_preds = {pred.negate() for pred in self.predlist}
        return OrPredicate(negated_preds)
    def __repr__(self) -> str:
        return " AND ".join(["(" + str(pred) + ")" for pred in self.predlist])
    def __eq__(self, other) -> bool:
        if not isinstance(other, AndPredicate):
            return False
        return self.predlist == other.predlist
    def __hash__(self) -> int:
        return hash(frozenset(self.predlist))
    
class IntervalPredicate(Predicate[int]):
    """
    A predicate representing an interval of integer values between lower (inclusive) and upper (exclusive).

    None for lower or upper bounds indicates +/- infinity.
    """

    def __init__(self, lower: Optional[int], upper: Optional[int]):
        self.lower = lower
        self.upper = upper
    
    def eval(self, element: int) -> bool:
        if element is None:
            raise ValueError("Warning: Evaluating IntervalPredicate on None element.")
        lower_ok = True if (self.lower is None) else element >= self.lower
        upper_ok = True if (self.upper is None) else element < self.upper
        return lower_ok and upper_ok

    def negate(self) -> 'Predicate':
        if self.lower is None and self.upper is None:
            return IntervalPredicate(1, 0)  # Represents false
        elif self.lower is None:
            return IntervalPredicate(self.upper, None)
        elif self.upper is None:
            return IntervalPredicate(None, self.lower)
        else:
            return OrPredicate({IntervalPredicate(None, self.lower), IntervalPredicate(self.upper, None)})
        
    

    def __repr__(self) -> str:
        return f"[{self.lower if self.lower is not None else '-inf'}, {self.upper if self.upper is not None else 'inf'}["

    def __eq__(self, other) -> bool:
        if not isinstance(other, IntervalPredicate):
            return False
        return self.lower == other.lower and self.upper == other.upper

    def __hash__(self) -> int:
        return hash((self.lower, self.upper))


class IntervalAlgebra(BooleanAlgebra[int]):
    #two helper functions for bounds management  
    @staticmethod 
    def max_lower(a: Optional[int], b: Optional[int]) -> Optional[int]:
                if a is None: return b
                if b is None: return a
                return max(a, b)
    @staticmethod
    def min_upper(a: Optional[int], b: Optional[int]) -> Optional[int]:
                if a is None: return b
                if b is None: return a
                return min(a, b)
    

    def true(self) -> Predicate:
        return IntervalPredicate(None, None)
    
    def false(self) -> Predicate:
        return IntervalPredicate(1, 0) # Represents false
    def and_op(self, predicate: 'Predicate', other: 'Predicate') -> 'Predicate':
        if isinstance(predicate, IntervalPredicate) and isinstance(other, IntervalPredicate):
            new_lower = IntervalAlgebra.max_lower(predicate.lower, other.lower)
            new_upper = IntervalAlgebra.min_upper(predicate.upper, other.upper)
            if new_lower is not None and new_upper is not None and new_lower >= new_upper:
                return IntervalPredicate(1, 0)  # Represents false
            return IntervalPredicate(new_lower, new_upper)
        return AndPredicate({predicate, other})
    
    def or_op(self, predicate: 'Predicate', other: 'Predicate') -> 'OrPredicate':
        return OrPredicate({predicate, other})
    
    def is_satisfiable(self, predicate: 'Predicate') -> bool:
        if isinstance(predicate, IntervalPredicate):
            if predicate.lower is not None and predicate.upper is not None:
                return predicate.lower < predicate.upper
            return True
        if isinstance(predicate, OrPredicate): #check if at least one is satisfiable
            for pred in predicate.predlist: 
                if self.is_satisfiable(pred):
                    return True
            return False
        if isinstance(predicate, AndPredicate): #check if all are satisfiable
            for pred in predicate.predlist: 
                if not self.is_satisfiable(pred):
                    return False
            return True
        return False #should never happen
    
    def is_true(self, predicate: 'Predicate') -> bool:
        if isinstance(predicate, OrPredicate): #check if at least one is true
            if len(predicate.predlist) == 0:
                return False 
            for pred in predicate.predlist:
                if self.is_true(pred):
                    return True
            return False
        elif isinstance(predicate, AndPredicate): #check if all are true
            if len(predicate.predlist) == 0:
                return True 
            for pred in predicate.predlist:
                if not self.is_true(pred):
                    return False
            return True
        elif isinstance(predicate, IntervalPredicate):
            return (predicate.lower is None) and (predicate.upper is None)
        return False #should never happen
    
    def are_equivalent(self, pred1: 'Predicate', pred2: 'Predicate') -> bool:
        return self.minimize_predicate(pred1) == self.minimize_predicate(pred2)
    
    
    def pick_witness(self, predicate: 'Predicate') -> Optional[int]:
        if isinstance(predicate, IntervalPredicate):
            if not self.is_satisfiable(predicate):
                print(f"Warning: trying to pick witness from unsatisfiable predicate {predicate}.")
                return None
            if predicate.lower is not None:
                return predicate.lower
            elif predicate.upper is not None:
                return predicate.upper - 1
            else:
                return 0
          # OR : witness from any satisfiable branch
        elif isinstance(predicate, OrPredicate):
            for pred in predicate.predlist:
                witness = self.pick_witness(pred)
                if witness is not None and predicate.eval(witness):
                    return witness
            return None

        # AND : minimize then pick
        elif isinstance(predicate, AndPredicate):
            minimized = self.minimize_predicate(predicate)
            return self.pick_witness(minimized)

        return None
    def pick_witness_random(self, predicate: 'Predicate') -> Optional[int]:
        import numpy as np
        if isinstance(predicate, IntervalPredicate):
            if not self.is_satisfiable(predicate):
                print(f"Warning: trying to pick witness from unsatisfiable predicate {predicate}.")
                return None
            if predicate.lower is not None and predicate.upper is not None:
                return np.random.randint(predicate.lower, predicate.upper)
            elif predicate.lower is not None:
                return np.random.randint(predicate.lower, predicate.lower + 100) 
            elif predicate.upper is not None:
                return np.random.randint(predicate.upper - 100, predicate.upper)  
            else:
                return np.random.randint(-100, 100)  # Arbitrary range for infinite interval
          # OR : witness from any satisfiable branch
        elif isinstance(predicate, OrPredicate):
            for pred in predicate.predlist:
                witness = self.pick_witness_random(pred)
                if witness is not None and predicate.eval(witness):
                    return witness

        # AND : minimize then pick
        elif isinstance(predicate, AndPredicate):
            minimized = self.minimize_predicate(predicate)
            return self.pick_witness_random(minimized)
        
        return None
    # convert bounds to numeric for sorting/merging (-inf/inf for None)
    def to_bounds(self,ip: IntervalPredicate):
        lo = float("-inf") if ip.lower is None else ip.lower
        hi = float("inf") if ip.upper is None else ip.upper
        return (lo, hi)
    
    def minimize_predicate(self, predicate: 'Predicate') -> 'Predicate':
       #guarantee : this returns a OrPredicate of IntervalPredicates, or a single IntervalPredicate
        if isinstance(predicate, IntervalPredicate):
            return predicate
        elif isinstance(predicate, OrPredicate):
            # flatten and collect intervals
            intervals = []
            for pred in predicate.predlist:
                minimized = self.minimize_predicate(pred)
                if isinstance(minimized, IntervalPredicate) and self.is_satisfiable(minimized):
                    intervals.append(minimized)
                elif isinstance(minimized, OrPredicate):
                    intervals.extend(ip for ip in minimized.predlist if self.is_satisfiable(ip))

            if not intervals:
                return self.false()

            
            # sort by lower bounds
            bounds = sorted([self.to_bounds(ip) for ip in intervals], key=lambda x: x[0])

            merged = []
            for lo, hi in bounds:
                if not merged:
                    merged.append((lo, hi))
                    continue
                last_lo, last_hi = merged[-1]
                # merge if overlapping or touching
                if lo <= last_hi:
                    new_hi = max(last_hi, hi)
                    new_lo = last_lo if last_lo <= lo else lo
                    merged[-1] = (new_lo, new_hi)
                else:
                    merged.append((lo, hi))

            # convert back to IntervalPredicate, using None for infinities
            result_intervals = set()
            for lo, hi in merged:
                new_lo = None if lo == float("-inf") else int(lo)
                new_hi = None if hi == float("inf") else int(hi)
                result_intervals.add(IntervalPredicate(new_lo, new_hi))

            if len(result_intervals) == 1:
                return next(iter(result_intervals))
            return OrPredicate(result_intervals)
        elif isinstance(predicate, AndPredicate):
            if predicate.predlist == set():
                return self.true()
            minimized_preds = [self.minimize_predicate(pred) for pred in predicate.predlist]
            acc = minimized_preds[0] if isinstance(minimized_preds[0], OrPredicate) else OrPredicate({minimized_preds[0]})
            for pred in minimized_preds[1:]:
                pred_or = pred if isinstance(pred, OrPredicate) else OrPredicate({pred})
                # Accumulate by intersecting intervals
                intersected = set()
                for interval1 in acc.predlist:
                    for interval2 in pred_or.predlist:
                        # Intersect two intervals
                        intersected_interval = self.and_op(interval1, interval2)
                        if self.is_satisfiable(intersected_interval):
                            intersected.add(intersected_interval)
                
                if not intersected:
                    return self.false()
                acc = OrPredicate(intersected)
            
            # if legth = 0, return false ; if length = 1 return the interval ; else return OrPredicate
            if len(acc.predlist) == 0:
                return self.false()
            if len(acc.predlist) == 1:
                return next(iter(acc.predlist))
            return acc 
        else:
            raise NotImplementedError("Minimization not implemented for this predicate type.")


def _reduce_or(predicates: Set[Predicate]) -> Predicate:
    if not predicates:
        return OrPredicate(set())
    if len(predicates) == 1:
        return next(iter(predicates))
    return OrPredicate(predicates)


def _letter_predicates_for_interval(
    letter: LetterType,
    interval_predicate: Predicate,
    alphabet: Set[LetterType],
    interval_alg: IntervalAlgebra,
) -> Set[Predicate]:
    minimized = interval_alg.minimize_predicate(interval_predicate)
    if isinstance(minimized, IntervalPredicate):
        if not interval_alg.is_satisfiable(minimized):
            return set()
        return {LetterIntervalPredicate(letter, minimized, alphabet)}
    if isinstance(minimized, OrPredicate):
        predicates: Set[Predicate] = set()
        for pred in minimized.predlist:
            if isinstance(pred, IntervalPredicate) and interval_alg.is_satisfiable(pred):
                predicates.add(LetterIntervalPredicate(letter, pred, alphabet))
        return predicates
    return set()


class LetterIntervalPredicate(Predicate[Tuple[LetterType, int]]):
    """
    Predicate over (letter, value) pairs: letter must match and value must satisfy the interval.
    """

    def __init__(
        self,
        letter: LetterType,
        interval: IntervalPredicate,
        alphabet: Optional[Set[LetterType]] = None,
    ):
        self.letter = letter
        self.interval = interval
        self.alphabet = alphabet

    def eval(self, element: Tuple[LetterType, int]) -> bool:
        if element is None or not isinstance(element, tuple) or len(element) != 2:
            raise ValueError("Expected a (letter, value) tuple for LetterIntervalPredicate.")
        letter, value = element
        return letter == self.letter and self.interval.eval(value)

    def negate_same_letter(self) -> Predicate:
        if self.alphabet is None:
            raise ValueError("Alphabet is required to negate LetterIntervalPredicate.")
        interval_alg = IntervalAlgebra()
        predicates = _letter_predicates_for_interval(
            self.letter, self.interval.negate(), self.alphabet, interval_alg
        )
        return _reduce_or(predicates)

    def negate(self) -> Predicate:
        if self.alphabet is None:
            raise ValueError("Alphabet is required to negate LetterIntervalPredicate.")
        interval_alg = IntervalAlgebra()
        predicates = _letter_predicates_for_interval(
            self.letter, self.interval.negate(), self.alphabet, interval_alg
        )
        for letter in self.alphabet:
            if letter == self.letter:
                continue
            predicates.add(LetterIntervalPredicate(letter, IntervalPredicate(None, None), self.alphabet))
        return _reduce_or(predicates)

    def __repr__(self) -> str:
        return f"({self.letter}, {self.interval})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, LetterIntervalPredicate):
            return False
        return self.letter == other.letter and self.interval == other.interval

    def __hash__(self) -> int:
        return hash((self.letter, self.interval))


class LetterIntervalAlgebra(BooleanAlgebra[Tuple[LetterType, int]]):
    """
    Boolean algebra over (letter, value) with a finite alphabet and interval predicates on value.
    """

    def __init__(self, alphabet: Set[LetterType]):
        if not alphabet:
            raise ValueError("Alphabet must be a non-empty set.")
        self.alphabet = set(alphabet)
        self._interval_alg = IntervalAlgebra()

    def _iter_letters(self):
        return list(self.alphabet)

    def _value_predicate_for_letter(self, predicate: Predicate, letter: LetterType) -> Predicate:
        if isinstance(predicate, LetterIntervalPredicate):
            if predicate.letter != letter:
                return self._interval_alg.false()
            return predicate.interval
        if isinstance(predicate, OrPredicate):
            return OrPredicate(
                {self._value_predicate_for_letter(p, letter) for p in predicate.predlist}
            )
        if isinstance(predicate, AndPredicate):
            return AndPredicate(
                {self._value_predicate_for_letter(p, letter) for p in predicate.predlist}
            )
        raise ValueError(f"Unsupported predicate for letter algebra: {predicate}")

    def letter_true(self, letter: LetterType) -> LetterIntervalPredicate:
        return LetterIntervalPredicate(letter, IntervalPredicate(None, None), self.alphabet)

    def letter_interval(self, letter: LetterType, interval: IntervalPredicate) -> LetterIntervalPredicate:
        return LetterIntervalPredicate(letter, interval, self.alphabet)

    def negate_same_letter(self, predicate: Predicate) -> Predicate:
        if not isinstance(predicate, LetterIntervalPredicate):
            raise ValueError("negate_same_letter expects a LetterIntervalPredicate.")
        return predicate.negate_same_letter()

    def true(self) -> Predicate:
        predicates: Set[Predicate] = set()
        for letter in self.alphabet:
            predicates.add(self.letter_true(letter))
        return _reduce_or(predicates)

    def false(self) -> Predicate:
        return OrPredicate(set())

    def and_op(self, pred1: Predicate, pred2: Predicate) -> Predicate:
        if isinstance(pred1, LetterIntervalPredicate) and isinstance(pred2, LetterIntervalPredicate):
            if pred1.letter != pred2.letter:
                return self.false()
            interval = self._interval_alg.and_op(pred1.interval, pred2.interval)
            predicates = _letter_predicates_for_interval(
                pred1.letter, interval, self.alphabet, self._interval_alg
            )
            return _reduce_or(predicates)
        return AndPredicate({pred1, pred2})

    def or_op(self, pred1: Predicate, pred2: Predicate) -> Predicate:
        if isinstance(pred1, LetterIntervalPredicate) and isinstance(pred2, LetterIntervalPredicate):
            if pred1.letter == pred2.letter:
                interval_or = self._interval_alg.or_op(pred1.interval, pred2.interval)
                predicates = _letter_predicates_for_interval(
                    pred1.letter, interval_or, self.alphabet, self._interval_alg
                )
                return _reduce_or(predicates)
        return OrPredicate({pred1, pred2})

    def is_satisfiable(self, predicate: Predicate) -> bool:
        for letter in self._iter_letters():
            value_pred = self._value_predicate_for_letter(predicate, letter)
            minimized = self._interval_alg.minimize_predicate(value_pred)
            if self._interval_alg.is_satisfiable(minimized):
                return True
        return False

    def is_true(self, predicate: Predicate) -> bool:
        for letter in self._iter_letters():
            value_pred = self._value_predicate_for_letter(predicate, letter)
            minimized = self._interval_alg.minimize_predicate(value_pred)
            if not self._interval_alg.is_true(minimized):
                return False
        return True

    def are_equivalent(self, pred1: Predicate, pred2: Predicate) -> bool:
        return self.minimize_predicate(pred1) == self.minimize_predicate(pred2)

    def pick_witness(self, predicate: Predicate) -> Optional[Tuple[LetterType, int]]:
        for letter in self._iter_letters():
            value_pred = self._value_predicate_for_letter(predicate, letter)
            minimized = self._interval_alg.minimize_predicate(value_pred)
            if self._interval_alg.is_satisfiable(minimized):
                value = self._interval_alg.pick_witness(minimized)
                if value is not None:
                    return (letter, value)
        return None

    def minimize_predicate(self, predicate: Predicate) -> Predicate:
        predicates: Set[Predicate] = set()
        for letter in self._iter_letters():
            value_pred = self._value_predicate_for_letter(predicate, letter)
            minimized = self._interval_alg.minimize_predicate(value_pred)
            predicates.update(
                _letter_predicates_for_interval(letter, minimized, self.alphabet, self._interval_alg)
            )
        return _reduce_or(predicates)
        

class GenIntPredicate(Predicate[OrderedDomain]):
    """
    A predicate representing an interval of values, not necessarily integers, between lower (inclusive) and upper (exclusive).
    The type of elements must support comparison operators.
    None for lower or upper bounds indicates +/- infinity or max value of the type.
    _is_empty represents empty predicate (= false)
    """
    def __init__(self, lower: Optional[OrderedDomain], upper: Optional[OrderedDomain], _is_empty: bool = False):
        self.lower = lower
        self.upper = upper
        self._is_empty = _is_empty
    def eval(self, element: OrderedDomain) -> bool:
        if self._is_empty:
            return False
        if element is None:
            raise ValueError("Warning: Evaluating GenIntPredicate on None element.")
        lower_ok = True if (self.lower is None) else element >= self.lower
        upper_ok = True if (self.upper is None) else element < self.upper
        return lower_ok and upper_ok
    def negate(self) -> 'Predicate':
        if self._is_empty:
            return GenIntPredicate(None, None)  # Represents true
        elif self.lower is None and self.upper is None:
            return GenIntPredicate(None, None, _is_empty=True)  # Represents false
        elif self.lower is None:
            return GenIntPredicate(self.upper, None)
        elif self.upper is None:
            return GenIntPredicate(None, self.lower)
        else:
            return OrPredicate({GenIntPredicate(None, self.lower), GenIntPredicate(self.upper, None)})
        
    

    def __repr__(self) -> str:
        if self._is_empty:
            return "FALSE"
        return f"[{self.lower if self.lower is not None else '-inf'}, {self.upper if self.upper is not None else 'inf'}["

    def __eq__(self, other) -> bool:
        if not isinstance(other, GenIntPredicate):
            return False
        if self._is_empty and other._is_empty:
            return True
        if self._is_empty or other._is_empty:
            return False
        return self.lower == other.lower and self.upper == other.upper


    def __hash__(self) -> int:
        if self._is_empty:
            return hash("FALSE")
        return hash((self.lower, self.upper))
    
class MonotonicAlgebra(BooleanAlgebra[OrderedDomain]):
    """
    A Boolean algebra where predicates are represented as intervals of values (GenIntPredicate).

    IMPORTANT: The type of elements must support comparison operators, and either a predecessor function or a min_elt must be given for some functions to work properly (picking witnesses, necessary to obtain characteristic sets).

    """
    def __init__(self, predecessor = None, min_elt: Optional[OrderedDomain] = None):
        self._min_elt = min_elt
        self._predecessor = predecessor
    @staticmethod 
    def max_lower(a: Optional[OrderedDomain], b: Optional[OrderedDomain]) -> Optional[OrderedDomain]:
                if a is None: return b
                if b is None: return a
                return max(a, b)
    @staticmethod
    def min_upper(a: Optional[OrderedDomain], b: Optional[OrderedDomain]) -> Optional[OrderedDomain]:
                if a is None: return b
                if b is None: return a
                return min(a, b)
    
    def true(self) -> Predicate:
        return GenIntPredicate(None, None)
    
    def false(self) -> Predicate:
        return GenIntPredicate(None, None, _is_empty=True) # Represents false
    def and_op(self, predicate: 'Predicate', other: 'Predicate') -> 'Predicate':
        if isinstance(predicate, GenIntPredicate) and isinstance(other, GenIntPredicate):
            if predicate._is_empty or other._is_empty:
                return self.false()
            new_lower = self.max_lower(predicate.lower, other.lower)
            new_upper = self.min_upper(predicate.upper, other.upper)
            if new_lower is not None and new_upper is not None and new_lower >= new_upper:
                return self.false()
            return GenIntPredicate(new_lower, new_upper)
        return AndPredicate({predicate, other})
    
    def or_op(self, predicate: 'Predicate', other: 'Predicate') -> 'OrPredicate':
        return OrPredicate({predicate, other})
    
    def is_satisfiable(self, predicate: 'Predicate') -> bool:
        if isinstance(predicate, GenIntPredicate):
            if predicate._is_empty:
                return False
            if predicate.lower is not None and predicate.upper is not None:
                return predicate.lower < predicate.upper
            return True
        if isinstance(predicate, OrPredicate): #check if at least one is satisfiable
            for pred in predicate.predlist: 
                if self.is_satisfiable(pred):
                    return True
            return False
        if isinstance(predicate, AndPredicate): #check if all are satisfiable
            for pred in predicate.predlist: 
                if not self.is_satisfiable(pred):
                    return False
            #TODO all being satisfiable does not guarantee that the intersection is satisfiable. implement minimization
            return True
        print(f"Warning: is_satisfiable called on unsupported predicate {predicate}")
        return False #should never happen
    
    def is_true(self, predicate: 'Predicate') -> bool:
        if isinstance(predicate, OrPredicate): #check if at least one is true
            if len(predicate.predlist) == 0:
                return False 
            for pred in predicate.predlist:
                if self.is_true(pred):
                    return True
            return False
        elif isinstance(predicate, AndPredicate): #check if all are true
            if len(predicate.predlist) == 0:
                return True 
            for pred in predicate.predlist:
                if not self.is_true(pred):
                    return False
            return True
        elif isinstance(predicate, GenIntPredicate):
            return (predicate.lower is None) and (predicate.upper is None)
        return False
    def are_equivalent(self, pred1: 'Predicate', pred2: 'Predicate') -> bool:
        return self.minimize_predicate(pred1) == self.minimize_predicate(pred2)
    
    def pick_witness(self, predicate: 'Predicate') -> Optional[OrderedDomain]:
        if isinstance(predicate, GenIntPredicate):
            if predicate._is_empty:
                print(f"Warning: trying to pick witness from unsatisfiable predicate {predicate}.")
                return None
            if predicate.lower is not None:
                return predicate.lower
            elif predicate.upper is not None:
                # pick the smallest element of the domain
                if self._min_elt is None and self._predecessor is None:
                    print(f"Warning: trying to pick witness from infinite upper interval {predicate} without min_elt or predecessor defined in the algebra ! \n CHARACTERISTIC SETS WILL NOT WORK !")
                    return None
                if self._predecessor is not None:
                    return self._predecessor(predicate.upper)
                return self._min_elt
            else:
                if self._min_elt is None:
                    raise NotImplementedError("Cannot pick witness from infinite interval without min_elt defined in the algebra ! \n CHARACTERISTIC SETS WILL NOT WORK !")
                return self._min_elt
          # OR : witness from any satisfiable branch
        elif isinstance(predicate, OrPredicate):
            for pred in predicate.predlist:
                witness = self.pick_witness(pred)
                if witness is not None and predicate.eval(witness):
                    return witness
            return None

        # AND : minimize then pick
        elif isinstance(predicate, AndPredicate):
            minimized = self.minimize_predicate(predicate)
            return self.pick_witness(minimized)

        print(f"Warning: pick_witness called on unsupported predicate {predicate}")
        return None
    def minimize_predicate(self, predicate: 'Predicate') -> 'Predicate':
        # Guarantee: returns OrPredicate of GenIntPredicate, or a single GenIntPredicate.
        if isinstance(predicate, GenIntPredicate):
            return self.false() if predicate._is_empty else predicate

        if isinstance(predicate, OrPredicate):
            intervals = []
            for pred in predicate.predlist:
                minimized = self.minimize_predicate(pred)
                if isinstance(minimized, GenIntPredicate):
                    if self.is_satisfiable(minimized):
                        intervals.append(minimized)
                elif isinstance(minimized, OrPredicate):
                    intervals.extend(
                        ip for ip in minimized.predlist if self.is_satisfiable(ip)
                    )

            if not intervals:
                return self.false()

            # Sort by lower bound; None means -inf and sorts first.
            def lower_key(ip: GenIntPredicate):
                return (ip.lower is not None, ip.lower)

            def overlaps_or_touches(left: GenIntPredicate, right: GenIntPredicate) -> bool:
                if left.upper is None or right.lower is None:
                    return True
                return right.lower <= left.upper

            def max_upper(a, b):
                if a is None or b is None:
                    return None
                return max(a, b)

            intervals.sort(key=lower_key)

            merged = []
            for ip in intervals:
                if not merged:
                    merged.append(ip)
                    continue
                last = merged[-1]
                if overlaps_or_touches(last, ip):
                    new_lower = last.lower if last.lower is None or ip.lower is None else min(last.lower, ip.lower)
                    new_upper = max_upper(last.upper, ip.upper)
                    merged[-1] = GenIntPredicate(new_lower, new_upper)
                else:
                    merged.append(ip)

            if len(merged) == 1:
                return merged[0]
            return OrPredicate(set(merged))

        if isinstance(predicate, AndPredicate):
            minimized_preds = [self.minimize_predicate(pred) for pred in predicate.predlist]
            acc = minimized_preds[0] if isinstance(minimized_preds[0], OrPredicate) else OrPredicate({minimized_preds[0]})
            for pred in minimized_preds[1:]:
                pred_or = pred if isinstance(pred, OrPredicate) else OrPredicate({pred})
                intersected = set()
                for interval1 in acc.predlist:
                    for interval2 in pred_or.predlist:
                        intersected_interval = self.and_op(interval1, interval2)
                        if self.is_satisfiable(intersected_interval):
                            intersected.add(intersected_interval)

                if not intersected:
                    return self.false()
                acc = OrPredicate(intersected)

            if len(acc.predlist) == 0:
                return self.false()
            if len(acc.predlist) == 1:
                return next(iter(acc.predlist))
            return acc

        raise NotImplementedError("Minimization not implemented for this predicate type.")
# some adhoc tests      
# alg = IntervalAlgebra()
# print(alg.and_op(IntervalPredicate(1,5), IntervalPredicate(3,7)))
# print(alg.or_op(IntervalPredicate(1,5), IntervalPredicate(3,7)))
# print(alg.is_satisfiable(IntervalPredicate(3,5)))
# print(alg.is_true(IntervalPredicate(None,None)))
# print(alg.minimize_predicate(OrPredicate({OrPredicate({IntervalPredicate(1,2), IntervalPredicate(3,5)}), AndPredicate({OrPredicate({IntervalPredicate(0,4), IntervalPredicate(7,8)}), IntervalPredicate(2,9)})})))