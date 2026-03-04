import time

from aalpy.automata.Sfa import Sfa, SfaState
from aalpy.base.BooleanAlgebra import IntervalPredicate, Predicate, BooleanAlgebra, IntervalAlgebra, OrPredicate
import numpy as np
from aalpy.learning_algs.deterministic_passive.SAI import SAI

def generate_sfa():
    nb_states = np.random.randint(2, 10)
    states = []
    for i in range(nb_states):
        s = SfaState(i, is_accepting=np.random.choice([True, False])) 
        states.append(s)
    for i in range(nb_states):
        s = states[i]
        nb_trans = np.random.randint(nb_states//4, nb_states)
        bounds = sorted(np.random.choice(range(0, 1000), max(0, nb_trans-1)))
        bounds.append(None)
        for i, b in enumerate(bounds):
            pred = IntervalPredicate(int(bounds[i-1]) if i > 0 else None, int(b) if b is not None else None)
            target = np.random.choice(states)
            s.transitions.append((pred, target))
    s0 = states[0]
    sfa = Sfa(s0, states)
    return sfa



for i in range(100):
    np.random.seed(i)
    print("seed:", i)
    sfa = generate_sfa()
    print(f"Original SFA has {len(sfa.states)} states")
    sample = sfa.characteristic_sample()
    print(f"Sample size: {len(sample)}")
    #print(f"Sample: {sample}, length: {len(sample)}")
    #print("Original SFA:", sfa)*
    start_time = time.time()
    sai = SAI(sample, algebra=IntervalAlgebra())
    learned_sfa = sai.run_SAI()
    end_time = time.time()
    print(f"Time to learn SFA: {end_time - start_time}")
    
    for word,label in sample:
        if learned_sfa.accepts(word) != label:
            print(f"Counterexample found: {word} should be {'accepted' if label else 'rejected'}")
            break
    if not learned_sfa.bisimilar(sfa):
        print(f"Learned SFA is not equivalent to original SFA \n Learned SFA: {learned_sfa} \n Original SFA: {sfa}")
        cex = learned_sfa.bisimilar(sfa, return_cex=True)
        print(f"Counterexample: {cex}, should be {'accepted' if sfa.accepts(cex) else 'rejected'}")
        break
    #print("Learned sfa:", learned_sfa)
    #print("Original SFA:", sfa)
    #print("\n\n")

