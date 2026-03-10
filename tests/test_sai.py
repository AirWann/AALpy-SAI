import time
import matplotlib.pyplot as plt
from aalpy.automata.Sfa import Sfa, SfaState
from aalpy.base.BooleanAlgebra import IntervalPredicate, Predicate, BooleanAlgebra, IntervalAlgebra, OrPredicate
import numpy as np
from aalpy.learning_algs.deterministic_passive.SAI import SAI
from aalpy.utils import save_automaton_to_file, visualize_automaton

def generate_sfa(nb_states):
    states = []
    for i in range(nb_states):
        s = SfaState(f"q{i}", is_accepting=np.random.choice([True, False])) 
        states.append(s)
    for i in range(nb_states):
        s = states[i]
        nb_trans = np.random.randint(nb_states//4, nb_states)
        bounds = sorted(np.random.choice(range(0, nb_trans*200), max(0, nb_trans-1)))
        bounds.append(None)
        for i, b in enumerate(bounds):
            pred = IntervalPredicate(int(bounds[i-1]) if i > 0 else None, int(b) if b is not None else None)
            target = np.random.choice(states)
            s.transitions.append((pred, target))
    s0 = states[0]
    sfa = Sfa(s0, states)
    return sfa


def test_sai(nb_states=10,nb_runs=100,fixed_seed=None,visualize=False,print_info=False):
    sample_sizes = np.zeros(nb_runs)
    run_times = np.zeros(nb_runs)
    for i in range(nb_runs):
        if fixed_seed is not None:
            seed = i+fixed_seed
            np.random.seed(seed)
        if print_info:
            print("seed:", seed)
        sfa = generate_sfa(nb_states)
        if visualize:
            visualize_automaton(sfa, path=f"original_sfa_{seed}_{nb_states}")
        sample = sfa.characteristic_sample()
        sample_sizes[i] = len(sample)
        #print(f"Sample: {sample}, length: {len(sample)}")
        #print("Original SFA:", sfa)
        start_time = time.time()

        sai = SAI(sample, algebra=IntervalAlgebra(),print_info=print_info)
        learned_sfa = sai.run_SAI()

        run_times[i] = time.time() - start_time
        if visualize:     
            visualize_automaton(learned_sfa, path=f"learned_sfa_{seed}_{nb_states}")
        for word,label in sample:
            if learned_sfa.accepts(word) != label:
                print(f"Counterexample found: {word} should be {'accepted' if label else 'rejected'}")
                break
        if not learned_sfa.bisimilar(sfa):
            print(f"Learned SFA is not equivalent to original SFA \n Learned SFA: {learned_sfa} \n Original SFA: {sfa}")
            cex = learned_sfa.bisimilar(sfa, return_cex=True)
            print(f"Counterexample: {cex}, should be {'accepted' if sfa.accepts(cex) else 'rejected'}")
            visualize_automaton(learned_sfa, path=f"learned_sfa_{nb_states}_counterexample")
            visualize_automaton(sfa, path=f"original_sfa_{nb_states}_counterexample")
            print("sample:", sample)
            print("setup of original", sfa.to_state_setup())
            break
        #print("Learned sfa:", learned_sfa)
        #print("Original SFA:", sfa)
        #print("\n\n")
    avg_sample = float(np.mean(sample_sizes))
    avg_time = float(np.mean(run_times))
    print(f"For automaton with {nb_states} states:")
    print(f"Average sample size: {avg_sample}, Average run time: {avg_time}")
    return avg_sample, avg_time

def benchmark_and_plot(states_list, nb_runs=100, print_info=False, output_path="sai_benchmark.png"):
    avg_samples = []
    avg_times = []

    for n in states_list:
        avg_sample, avg_time = test_sai(
            nb_states=n,
            nb_runs=nb_runs,
            visualize=False,
            print_info=print_info,
        )
        avg_samples.append(avg_sample)
        avg_times.append(avg_time)

    fig, ax1 = plt.subplots(figsize=(8, 5))

    color1 = "tab:blue"
    ax1.set_xlabel("Number of states (nb_states)")
    ax1.set_ylabel("Average sample size", color=color1)
    ax1.plot(states_list, avg_samples, marker="o", color=color1)
    ax1.tick_params(axis="y", labelcolor=color1)

    ax2 = ax1.twinx()
    color2 = "tab:red"
    ax2.set_ylabel("Average run time (s)", color=color2)
    ax2.plot(states_list, avg_times, marker="s", linestyle="--", color=color2)
    ax2.tick_params(axis="y", labelcolor=color2)

    plt.title(f"SAI performance vs nb_states ({nb_runs} runs)")
    fig.tight_layout()
    plt.grid(True, axis="x", alpha=0.3)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to: {output_path}")


if __name__ == "__main__":
    benchmark_and_plot(
        states_list=[2, 3, 4, 5, 6, 8, 10, 12, 14, 18, 22, 26, 30],
        nb_runs=10,
        print_info=False,
        output_path="sai_benchmark.png"
    )