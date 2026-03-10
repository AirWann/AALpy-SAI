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


def test_sai(nb_states=10,nb_runs=100,fixed_seed=None,visualize=False,print_info=False,return_raw=False):
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
    if return_raw:
        return avg_sample, avg_time, sample_sizes, run_times
    return avg_sample, avg_time

def benchmark_and_plot(
    states_list,
    nb_runs=100,
    print_info=False,
    output_path="sai_benchmark.png",
    uncertainty="ci95",  # "ci95", "sem", or "std"
):
    avg_samples, avg_times = [], []
    sample_err, time_err = [], []

    all_sample_sizes = []
    all_run_times = []

    for n in states_list:
        avg_sample, avg_time, samples_raw, times_raw = test_sai(
            nb_states=n,
            nb_runs=nb_runs if n < 50 else nb_runs // 2,
            visualize=False,
            print_info=print_info,
            return_raw=True,
        )
        avg_samples.append(avg_sample)
        avg_times.append(avg_time)
        all_sample_sizes.extend(samples_raw.tolist())
        all_run_times.extend(times_raw.tolist())
        s_std = float(np.std(samples_raw, ddof=1)) if len(samples_raw) > 1 else 0.0
        t_std = float(np.std(times_raw, ddof=1)) if len(times_raw) > 1 else 0.0

        if uncertainty == "std":
            sample_err.append(s_std)
            time_err.append(t_std)
        else:
            s_sem = s_std / np.sqrt(len(samples_raw)) if len(samples_raw) > 0 else 0.0
            t_sem = t_std / np.sqrt(len(times_raw)) if len(times_raw) > 0 else 0.0
            if uncertainty == "sem":
                sample_err.append(s_sem)
                time_err.append(t_sem)
            else:  # ci95
                sample_err.append(1.96 * s_sem)
                time_err.append(1.96 * t_sem)

    fig, ax1 = plt.subplots(figsize=(8, 5))

    color1 = "tab:blue"
    ax1.set_xlabel("Number of states (nb_states)")
    ax1.set_ylabel("Average sample size", color=color1)
    ax1.errorbar(
        states_list, avg_samples, yerr=sample_err,
        fmt="o--", color=color1, capsize=4, elinewidth=1
    )
    ax1.tick_params(axis="y", labelcolor=color1)

    ax2 = ax1.twinx()
    color2 = "tab:red"
    ax2.set_ylabel("Average run time (s)", color=color2)
    ax2.errorbar(
        states_list, avg_times, yerr=time_err,
        fmt="s-", color=color2, capsize=4, elinewidth=1
    )
    ax2.tick_params(axis="y", labelcolor=color2)

    plt.title(f"SAI runtime/sample size vs nb_states ({uncertainty}, on {nb_runs} runs)")
    fig.tight_layout()
    plt.grid(True, axis="x", alpha=0.3)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to: {output_path}")
    plot_runtime_vs_sample_size(
            all_sample_sizes,
            all_run_times,
            output_path=output_path.replace(".png", "_runtime_vs_sample.png"),
        )
def plot_runtime_vs_sample_size(
    sample_sizes,
    run_times,
    output_path="sai_runtime_vs_sample.png",
):
    sample_sizes = np.asarray(sample_sizes, dtype=float)
    run_times = np.asarray(run_times, dtype=float)

    if len(sample_sizes) == 0:
        print("No data to plot for runtime vs sample size.")
        return

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(sample_sizes, run_times, alpha=0.6, s=24, color="tab:purple", label="Runs")
    
    ax.set_xlabel("Sample size")
    ax.set_ylabel("Run time (s)")
    ax.set_title("SAI run time vs sample size")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Runtime vs sample-size plot saved to: {output_path}")

if __name__ == "__main__":
    benchmark_and_plot(
        states_list=[2, 3, 4, 6, 8, 10, 12, 15, 20, 30, 50],
        nb_runs=40,
        print_info=False,
        output_path="sai_benchmark.png"
    )
