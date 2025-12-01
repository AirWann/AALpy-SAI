"""
Abstract base classes for Predicates and Boolean Algebras used in Symbolic Automata.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Set, Tuple


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


class BooleanAlgebra(ABC):
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
    def get_domain(self, predicate: Predicate) -> Set[Any]:
        """
        Get all elements that satisfy the predicate.
        """
        pass

    @abstractmethod
    def pick_witness(self, predicate: Predicate) -> Any:
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
        return " OR ".join([str(pred) for pred in self.predlist])
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
        return " AND ".join([str(pred) for pred in self.predlist])
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
    
    def eval(self, element: Any) -> bool:
        return self.lower <= element <= self.upper

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


class IntervalAlgebra(BooleanAlgebra):
    def true(self) -> Predicate:
        return IntervalPredicate(None, None)
    
    def false(self) -> Predicate:
        return IntervalPredicate(1, 0) # Represents false
    
    def and_op(self, predicate: 'Predicate', other: 'Predicate') -> 'Predicate':
        if isinstance(predicate, IntervalPredicate) and isinstance(other, IntervalPredicate):
            new_lower = max(predicate.lower, other.lower) if (predicate.lower is not None and other.lower is not None) else (predicate.lower or other.lower)
            new_upper = min(predicate.upper, other.upper) if (predicate.upper is not None and other.upper is not None) else (predicate.upper or other.upper)
            if new_lower is not None and new_upper is not None and new_lower > new_upper:
                return IntervalPredicate(1, 0)  # Represents false
            return IntervalPredicate(new_lower, new_upper)
        return AndPredicate({predicate, other})
    
    def or_op(self, predicate: 'Predicate', other: 'Predicate') -> 'OrPredicate':
        return OrPredicate({predicate, other})
    
    def is_satisfiable(self, predicate: 'Predicate') -> bool:
        if isinstance(predicate, IntervalPredicate):
            if predicate.lower is not None and predicate.upper is not None:
                return predicate.lower <= predicate.upper
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
    
    def get_domain(self, predicate: 'Predicate') -> Set[Any]:
        if isinstance(predicate, IntervalPredicate):
            if predicate.lower is None or predicate.upper is None:
                raise NotImplementedError("Domain is infinite.")
            return set(range(predicate.lower, predicate.upper + 1))
        elif isinstance(predicate, OrPredicate):
            domain = set()
            for pred in predicate.predlist:
                domain.update(self.get_domain(pred))
            return domain
        elif isinstance(predicate, AndPredicate):
            domain = None
            for pred in predicate.predlist:
                pred_domain = self.get_domain(pred)
                if domain is None:
                    domain = pred_domain
                else:
                    domain = domain.intersection(pred_domain)
            return domain if domain is not None else set()
    
    def pick_witness(self, predicate: 'IntervalPredicate') -> Any:
        if not self.is_satisfiable(predicate):
            return None
        return predicate.lower if predicate.lower is not None else (predicate.upper if predicate.upper is not None else 0)
    
    # convert bounds to numeric for sorting/merging (-inf/inf for None)
    def to_bounds(self,ip: IntervalPredicate):
        lo = float("-inf") if ip.lower is None else ip.lower
        hi = float("inf") if ip.upper is None else ip.upper
        return (lo, hi, ip)
    
    def minimize_predicate(self, predicate: 'Predicate') -> 'Predicate':
       #guarantee : this returns a OrPredicate of IntervalPredicates, or a single IntervalPredicate
        if isinstance(predicate, IntervalPredicate):
            return predicate
        elif isinstance(predicate, OrPredicate):
            # flatten and collect intervals
            intervals = []
            for pred in predicate.predlist:
                minimized = self.minimize_predicate(pred)
                if isinstance(minimized, IntervalPredicate):
                    intervals.append(minimized)
                elif isinstance(minimized, OrPredicate):
                    intervals.extend(minimized.predlist)

            if not intervals:
                return self.false()

            

            bounds = sorted([self.to_bounds(ip) for ip in intervals], key=lambda x: (x[0], x[1]))

            merged = []
            for lo, hi, _ in bounds:
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
            #TODO
            minimized_preds = {self.minimize_predicate(pred) for pred in predicate.predlist}
            return AndPredicate(minimized_preds)
        else:
            raise NotImplementedError("Minimization not implemented for this predicate type.")
        
alg = IntervalAlgebra()
print(alg.and_op(IntervalPredicate(1,5), IntervalPredicate(3,7)))
print(alg.or_op(IntervalPredicate(1,5), IntervalPredicate(3,7)))
print(alg.is_satisfiable(IntervalPredicate(3,5)))
print(alg.is_true(IntervalPredicate(None,None)))
print(alg.minimize_predicate(OrPredicate({OrPredicate({IntervalPredicate(1,2), IntervalPredicate(3,5)}), OrPredicate({IntervalPredicate(0,4), IntervalPredicate(7,8)})})))