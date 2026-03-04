"""
Abstract base classes for Predicates and Boolean Algebras used in Symbolic Automata.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, Set, Tuple, TypeVar


class Predicate(ABC):
    """
    Abstract base class for predicates used in symbolic automata
    """

    @abstractmethod
    def eval(self, element: Any) -> bool:
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

Domain = TypeVar('Domain')
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
    def get_domain(self, predicate: Predicate) -> Set[Domain]:
        """
        Get all elements that satisfy the predicate.
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
    
class IntervalPredicate(Predicate):
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
        return f"[{self.lower}, {self.upper}["

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
    
    def get_domain(self, predicate: 'Predicate') -> Set[int]:
        if isinstance(predicate, IntervalPredicate):
            if predicate.lower is None or predicate.upper is None:
                raise NotImplementedError("Domain is infinite.")
            return set(range(predicate.lower, predicate.upper))
        elif isinstance(predicate, OrPredicate):
            domain = set()
            for pred in predicate.predlist:
                domain.update(self.get_domain(pred))
            return domain
        elif isinstance(predicate, AndPredicate):
            domain = set()
            for pred in predicate.predlist:
                pred_domain = self.get_domain(pred)
                if len(domain) == 0:
                    domain = pred_domain
                else:
                    domain = domain.intersection(pred_domain)
            return domain if domain is not None else set()
    
    def pick_witness(self, predicate: 'IntervalPredicate') -> Optional[int]:
        if isinstance(predicate, IntervalPredicate):
            if not self.is_satisfiable(predicate):
                return None
            return predicate.lower if predicate.lower is not None else ((predicate.upper - 1) if predicate.upper is not None else 0)
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
# some adhoc tests      
# alg = IntervalAlgebra()
# print(alg.and_op(IntervalPredicate(1,5), IntervalPredicate(3,7)))
# print(alg.or_op(IntervalPredicate(1,5), IntervalPredicate(3,7)))
# print(alg.is_satisfiable(IntervalPredicate(3,5)))
# print(alg.is_true(IntervalPredicate(None,None)))
# print(alg.minimize_predicate(OrPredicate({OrPredicate({IntervalPredicate(1,2), IntervalPredicate(3,5)}), AndPredicate({OrPredicate({IntervalPredicate(0,4), IntervalPredicate(7,8)}), IntervalPredicate(2,9)})})))