from aalpy.automata.Sfa import Sfa, SfaState
from aalpy.base.BooleanAlgebra import IntervalPredicate, Predicate, BooleanAlgebra, IntervalAlgebra, OrPredicate
import numpy as np
from aalpy.learning_algs.deterministic_passive.SAI import SAI

def generate_sfa():
    nb_states = np.random.randint(2, 6)
    states = []
    for i in range(nb_states):
        s = SfaState(i, is_accepting=np.random.choice([True, False])) 
        states.append(s)
    for i in range(nb_states):
        s = states[i]
        nb_trans = np.random.randint(2, 4)
        bounds = sorted(np.random.choice(range(0, 100), nb_trans-1))
        bounds.append(None)
        for i, b in enumerate(bounds):
            pred = IntervalPredicate(int(bounds[i-1]) if i > 0 else None, int(b) if b is not None else None)
            target = np.random.choice(states)
            s.transitions.append((pred, target))
    s0 = states[0]
    sfa = Sfa(s0, states)
    return sfa


try:
    # np.random.seed(5)
    sfa = generate_sfa()
    sample = sfa.characteristic_sample()
    print(f"Sample: {sample}, length: {len(sample)}")
    print("Original SFA:", sfa)
    sai = SAI(sample, algebra=IntervalAlgebra())
    learned_sfa = sai.run_SAI()
    for word,label in sample:
        if learned_sfa.accepts(word) != label:
            print(f"Counterexample found: {word} should be {'accepted' if label else 'rejected'}")
    print("Learned sfa:", learned_sfa)
    print("Original SFA:", sfa)
except Exception as e:
    print(sfa)
    print(e)
# try:
#     sample = sfa.characteristic_sample()
#     sai = SAI(sample, algebra=IntervalAlgebra())
#     learned_sfa = sai.run_SAI()
# except Exception as e:
#     print(sfa)
#     print(e)
