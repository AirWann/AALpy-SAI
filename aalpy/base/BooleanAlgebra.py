"""
Abstract base classes for Predicates and Boolean Algebras used in Symbolic Automata.

This module provides the foundation for implementing symbolic automata,
which use predicates over an alphabet instead of concrete symbols.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Set, Tuple


class Predicate(ABC):
    """
    Abstract base class for predicates used in symbolic automata.
    
    A predicate is a function that evaluates to True or False for a given input.
    Predicates can be combined using boolean operations to form more complex predicates.
    """

    @abstractmethod
    def eval(self, element: Any) -> bool:
        """
        Check if the predicate is satisfied by the given element.
        
        Args:
            element: The element to test against the predicate.
            
        Returns:
            True if the predicate is satisfied, False otherwise.
        """
        pass

    @abstractmethod
    def negate(self) -> 'Predicate':
        """
        Return the negation of this predicate.
        
        Returns:
            A new Predicate that represents the negation of this predicate.
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
    Abstract base class for Boolean Algebras used in symbolic automata.
    
    A Boolean Algebra defines the set of predicates and operations over them,
    providing means to test equivalence, check satisfiability, and perform
    set operations on predicates.
    """

    @abstractmethod
    def true(self) -> Predicate:
        """
        Return the True predicate (always satisfied).
        
        Returns:
            A Predicate that is satisfied by all elements.
        """
        pass

    @abstractmethod
    def false(self) -> Predicate:
        """
        Return the False predicate (never satisfied).
        
        Returns:
            A Predicate that is satisfied by no elements.
        """
        pass

    @abstractmethod
    def and_op(self, pred1: Predicate, pred2: Predicate) -> Predicate:
        """
        Return the conjunction (AND) of two predicates.
        
        Args:
            pred1: The first predicate.
            pred2: The second predicate.
            
        Returns:
            A new Predicate representing (pred1 AND pred2).
        """
        pass

    @abstractmethod
    def or_op(self, pred1: Predicate, pred2: Predicate) -> Predicate:
        """
        Return the disjunction (OR) of two predicates.
        
        Args:
            pred1: The first predicate.
            pred2: The second predicate.
            
        Returns:
            A new Predicate representing (pred1 OR pred2).
        """
        pass

    @abstractmethod
    def is_satisfiable(self, predicate: Predicate) -> bool:
        """
        Check if the predicate is satisfiable.
        
        A predicate is satisfiable if there exists at least one element
        that satisfies it.
        
        Args:
            predicate: The predicate to check.
            
        Returns:
            True if the predicate is satisfiable, False otherwise.
        """
        pass

    @abstractmethod
    def is_true(self, predicate: Predicate) -> bool:
        """
        Check if the predicate is always true.
        
        Args:
            predicate: The predicate to check.
            
        Returns:
            True if the predicate is always true, False otherwise.
        """
        pass

    @abstractmethod
    def are_equivalent(self, pred1: Predicate, pred2: Predicate) -> bool:
        """
        Check if two predicates are logically equivalent.
        
        Two predicates are equivalent if they are satisfied by exactly the same elements.
        
        Args:
            pred1: The first predicate.
            pred2: The second predicate.
            
        Returns:
            True if the predicates are equivalent, False otherwise.
        """
        pass

    @abstractmethod
    def get_domain(self, predicate: Predicate) -> Set[Any]:
        """
        Get all elements that satisfy the predicate.
        
        This method is optional for some implementations, particularly when
        the domain is infinite.
        
        Args:
            predicate: The predicate to evaluate.
            
        Returns:
            A set of all elements that satisfy the predicate.
            
        Raises:
            NotImplementedError: If the domain is infinite or enumeration is not supported.
        """
        pass

    @abstractmethod
    def pick_witness(self, predicate: Predicate) -> Any:
        """
        Pick a witness (an element that satisfies the predicate).
        
        Args:
            predicate: The predicate to find a witness for.
            
        Returns:
            An element that satisfies the predicate, or None if no element exists.
        """
        pass

    @abstractmethod
    def minimize_predicate(self, predicate: Predicate) -> Predicate:
        """
        Minimize or simplify the predicate.
        
        This method may perform simplifications such as removing redundant clauses.
        
        Args:
            predicate: The predicate to minimize.
            
        Returns:
            A simplified predicate equivalent to the input.
        """
        pass

class IntervalPredicate(Predicate):
    """
    A predicate representing an interval of numeric values.

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
            return IntervalPredicate(None, self.lower).or_op(IntervalPredicate(self.upper, None))
        
    

    def __repr__(self) -> str:
        return f"[{self.lower}, {self.upper}]"

    def __eq__(self, other) -> bool:
        if not isinstance(other, IntervalPredicate):
            return False
        return self.lower == other.lower and self.upper == other.upper

    def __hash__(self) -> int:
        return hash((self.lower, self.upper))


class UnionPredicate(Predicate):
    pass
class IntervalAlgebra(BooleanAlgebra):
    def true(self) -> Predicate:
        return IntervalPredicate(None, None)
    
    def false(self) -> Predicate:
        return IntervalPredicate(1, 0) 
    
    def and_op(self, predicate: 'IntervalPredicate', other: 'IntervalPredicate') -> 'IntervalPredicate':
        new_lower = max(predicate.lower, other.lower) if predicate.lower is not None and other.lower is not None else predicate.lower or other.lower
        new_upper = min(predicate.upper, other.upper) if predicate.upper is not None and other.upper is not None else predicate.upper or other.upper
        if new_lower is not None and new_upper is not None and new_lower > new_upper:
            return IntervalPredicate(1, 0)  # Represents false
        return IntervalPredicate(new_lower, new_upper)
    
    def or_op(self, predicate: 'IntervalPredicate', other: 'IntervalPredicate') -> 'IntervalPredicate':
        new_lower = min(predicate.lower, other.lower) if predicate.lower is not None and other.lower is not None else None
        new_upper = max(predicate.upper, other.upper) if predicate.upper is not None and other.upper is not None else None
        return IntervalPredicate(new_lower, new_upper)
    
    def is_satisfiable(self, predicate: 'IntervalPredicate') -> bool:
        if predicate.lower is not None and predicate.upper is not None:
            return predicate.lower <= predicate.upper
        return True
    
    def is_true(self, predicate: 'IntervalPredicate') -> bool:
        return predicate.lower is None and predicate.upper is None
    
    def are_equivalent(self, pred1: 'IntervalPredicate', pred2: 'IntervalPredicate') -> bool:
        return pred1 == pred2
    
    def get_domain(self, predicate: 'IntervalPredicate') -> Set[Any]:
        if predicate.lower is None or predicate.upper is None:
            raise NotImplementedError("Domain is infinite.")
        return set(range(predicate.lower, predicate.upper + 1))
    
    def pick_witness(self, predicate: 'IntervalPredicate') -> Any:
        if not self.is_satisfiable(predicate):
            return None
        return predicate.lower if predicate.lower is not None else (predicate.upper if predicate.upper is not None else 0)
    
    def minimize_predicate(self, predicate: 'IntervalPredicate') -> 'IntervalPredicate':
        return predicate  # Interval predicates are already minimal