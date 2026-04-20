# About SAI

SAI, for *Symbolic Automata Inference*, is an algorithm introduced in [citation needed] for learning symbolic automata. An introduction to symbolic automata can be found [here](https://www.microsoft.com/en-us/research/wp-content/uploads/2017/05/cav17tutorial.pdf). 

In a nutshell, symbolic automata are finite-state automata where transitions are labeled by *predicates* that describe which letter can fire them, so as to handle large or infinite alphabets (for example, think reading words from $\mathbb{N}^*$ and having predicates like "the letter is even" or "the letter is above 1000")

### Relevant files

In [aalpy/base/BooleanAlgebra.py](/aalpy/base/BooleanAlgebra.py), Boolean algebras are defined as an abstract class and a concrete one (IntervalAlgebra) is also given.

In [aalpy/automata/Sfa.py](/aalpy/automata/Sfa.py), SFA are defined. Some useful functions like `characteristic_sample` are found here.

In [aalpy/learning_algs/deterministic_passive/SAI.py](aalpy/learning_algs/deterministic_passive/SAI.py), the SAI algorithm is implemented with all its components.

Anything else, e.g. related to testing/benchmarking, is found in folder [SAITesting/](SAITesting/).

### Relevant functions & How-to

#### For Boolean algebras

Predicate and BooleanAlgebra are [abstract classes](https://docs.python.org/3.14/glossary.html#term-abstract-base-class). To define new ones you'll need to first define what your predicates are in an subclass of Predicate, then define operations around them in a subclass of BooleanAlgebra. You will find an example of such an implementation in IntervalPredicate and IntervalAlgebra. Note that not all functions implemented there are necessary to get a Boolean Algebra : it is sufficient to instantiate all abstract methods of ABCs Predicate and BooleanAlgebra.

Classes OrPredicate (representing an OR of a set of Predicates) and AndPredicate (representing... take a guess) can be used agnostically of what the underlying predicates are.

#### For SFA

I have tried to keep SFA syntax close to how other automata handle in AALpy. 
They have an internal value current_state, that can be updated using `sfa.step(letter)`. Be careful to set it back to `sfa.initial_state` when starting a new computation or you'll get incomprehensible errors !
If you only want to make a full computation on a given word and get a Boolean answer, `sfa.accepts(word)` is the wrapper you're looking for.

Equality of two SFA (bisimilarity check) is implemented and can be called using == (so keep in mind this is not a structural equality check !)

In most functions it is assumed that SFA are deterministic and complete. Some functions might raise errors, but some might have undefined or nondeterministic behavior. `sfa.make_input_complete()` is your friend (it adds a sink state). I have not yet thought about non-determinism, so try to guarantee it at the time of creation of the SFA.

Outgoing transitions from a state are stored as a List of (Predicate,State). This is quite different from the dicts AALpy uses usually.

To instantiate a Sfa, call `Sfa(initial_state: SfaState, states: List[SfaState], algebra: BooleanAlgebra)`. algebra is optional, if not given it defaults to IntervalAlgebra().

To instantiate a SfaState, call `SfaState(id, is_accepting: Bool)` and then edit its transitions directly.

#### For SAI
SAI takes in a sample in the form of a set of labeled words. Words are tuples of letter, so this makes the type of a sample `Set[Tuple[Tuple, bool]]`. 
To create an instance of SAI, call `SAI(sample, algebra, print_info)` : algebra is optional and defaults to IntervalAlgebra(), print_info is optional and defaults to False. Then, to execute the algorithm, call instance.run_SAI(). This returns an SFA.

#### Other utilities
function `visualize_automaton` from `aalpy.utils` allows you to print an SFA to PDF.

[SAITesting/utilities.py](SAITesting/utilities.py) contains a few useful functions that should be self-explanatory (and are commented so as to be) :
 `generate_sfa`, `sfa_to_dfa`, `dfa_to_sfa`,`generate_random_sample`.

Other scripts in that folder are benchmarks to test random sampling, test sai on characteristic samples, compare SAI to neural network models. 

If you need a small sfa, one is pickled in test_automaton2.pkl. Running utilities.py by itself will show you what it is.
