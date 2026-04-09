from aalpy.automata.Sfa import Sfa, SfaState
from aalpy.base.BooleanAlgebra import IntervalPredicate, Predicate, BooleanAlgebra, IntervalAlgebra, OrPredicate
import numpy as np
from aalpy.learning_algs.deterministic_passive.SAI import SAI
from aalpy.utils import save_automaton_to_file, visualize_automaton
from aalpy.automata import Dfa, DfaState
from aalpy.learning_algs import run_RPNI
from test_sai_characteristic import generate_sfa
import time
from pickle import load,dump
from typing import Set, Tuple
import matplotlib.pyplot as plt
from wakepy import keep
from aalpy.learning_algs import run_RPNI
from utilities import dfa_to_sfa,generate_random_sample, generate_sfa




def test_random_sampling(
        fixed_automaton=None,
        fixed_test_sample=None,
        nb_states=5,
        nb_runs=10,
        nb_samples=1000,
        learning_part=0.1,
        stop_prob=0.1,
        mode=0,
        print_info=False
    ):
    """
    Generate a random sample from an SFA and learn an SFA using SAI a part of the sample, then test the learned SFA on the rest of the sample.
    
    """
    accuracies = np.zeros(nb_runs)
    learn_times = np.zeros(nb_runs)
    learn_samples = np.zeros(nb_runs)
    result_sizes = np.zeros(nb_runs)
    for i in range(nb_runs):
        if fixed_automaton is None:
            testautomaton = generate_sfa(nb_states)
        else:
            testautomaton = fixed_automaton

        start_time = time.time()
        if mode == -1:
            sample = generate_random_sample(testautomaton, num_samples=nb_samples//3, stop_prob=stop_prob, mode=0).union(
                generate_random_sample(testautomaton, num_samples=nb_samples//3, stop_prob=stop_prob, mode=1),
                generate_random_sample(testautomaton, num_samples=nb_samples//3, stop_prob=stop_prob, mode=2),
            )
        else:
            sample = generate_random_sample(testautomaton, num_samples=nb_samples, stop_prob=stop_prob, mode=mode)
        sampling_time = time.time() - start_time
        learning_sample = set(list(sample)[:int(len(sample)*learning_part)])
        #print(learning_sample)
        if fixed_test_sample is not None:
            testing_sample = fixed_test_sample
        else:
            testing_sample = sample - learning_sample
        
        if mode == -1:
            learned_dfa = run_RPNI(list(learning_sample), 'dfa', 'classic',print_info=False)
            learned_sfa = dfa_to_sfa(learned_dfa,IntervalAlgebra())
        else:
            learned_sfa = SAI(learning_sample).run_SAI()
        learning_time = time.time() - start_time - sampling_time
        result_sizes[i] = len(learned_sfa.states)
        if print_info:
            print(f"Learned SFA has {len(learned_sfa.states)} states.")
            print(f"Sampling time: {sampling_time}")
            print(f"Learning time: {learning_time}")
            visualize_automaton(testautomaton, path="./SAITesting/test_automaton_random_sample")
            visualize_automaton(learned_sfa, path="./SAITesting/learned_automaton_random_sample")
        correct = 0
        for word, label in testing_sample:
            if learned_sfa.accepts(word) == label:
                correct += 1
        if len(testing_sample) == 0:
            print("Warning: testing sample is empty, cannot compute accuracy.")
            accuracy = 0.0
        else:
            accuracy = correct / len(testing_sample)
        if print_info:
            print(f"Accuracy: {correct}/{len(testing_sample)} = {accuracy:.2f}")
        accuracies[i] = accuracy
        learn_times[i] = learning_time
        learn_samples[i] = len(learning_sample)
    return accuracies, learn_times, learn_samples, result_sizes



def benchmark_random_sampling_vs_learning_part(
    fixed_automaton,
    fixed_test_sample,
    learning_parts,
    nb_states=10,
    nb_runs=30,
    nb_samples=2000,
    stop_prob=0.1,
    modes=[0],
    uncertainty="ci95",  # "ci95", "sem", "std"
    output_prefix="random_sampling_benchmark",
    print_info=False,
):
    if isinstance(modes, int):
        modes = [modes]
    mean_acc, err_acc = [], []
    all_acc = []
    all_times, all_learn_sizes, all_parts, all_result_sizes = [], [], [], []
    accuracy_by_mode = np.zeros((len(modes), len(learning_parts)))
    error_by_mode = np.zeros((len(modes), len(learning_parts)))
    for mode in modes:
        print(f"\n\n--- Mode {mode} ---")
        print(f"==Starting benchmark with nb_states={nb_states}, nb_runs={nb_runs}, nb_samples={nb_samples}, stop_prob={stop_prob}, mode={mode}==")
        mean_acc.clear()
        err_acc.clear()
        all_acc.clear()
        all_times.clear()
        all_learn_sizes.clear()
        all_parts.clear()
        all_result_sizes.clear()
        for lp in learning_parts:
            print(f"Running benchmark for learning_part={lp:.2f}...")
            acc, learn_times, learn_samples, result_sizes = test_random_sampling(
                fixed_automaton=fixed_automaton,
                fixed_test_sample=fixed_test_sample,
                nb_states=nb_states,
                nb_runs=nb_runs,
                nb_samples=nb_samples,
                learning_part=lp,
                stop_prob=stop_prob,
                mode=mode,
                print_info=print_info,
            )

            # 1) accuracy vs learning_part
            all_acc.extend(acc.tolist())
            m = float(np.mean(acc))
            s = float(np.std(acc, ddof=1)) if len(acc) > 1 else 0.0
            sem = s / np.sqrt(len(acc)) if len(acc) > 0 else 0.0

            if uncertainty == "std":
                e = s
            elif uncertainty == "sem":
                e = sem
            else:
                e = 1.96 * sem  # ci95

            mean_acc.append(m)
            err_acc.append(e)
            accuracy_by_mode[modes.index(mode), learning_parts.tolist().index(lp)] = m
            error_by_mode[modes.index(mode), learning_parts.tolist().index(lp)] = e
            # 2) learning time vs learning sample size (raw points)
            all_times.extend(learn_times.tolist())
            all_learn_sizes.extend(learn_samples.tolist())
            all_parts.extend([lp] * len(learn_times))
            all_result_sizes.extend(result_sizes.tolist())
            print(f"learning_part={lp:.2f}: mean_acc={m:.4f}, err_acc={e:.4f}, mean_time={np.mean(learn_times):.2f}s")

        plot_accuracy_vs_learning_part(
            learning_parts=learning_parts,
            mean_acc=mean_acc,
            err_acc=err_acc,
            output_path=f"{output_prefix}_mode_{mode}_accuracy_vs_learning_part.png",
            uncertainty=uncertainty,
            nb_runs=nb_runs,
        )

        plot_learning_time_vs_learning_sample_size(
            learn_sample_sizes=all_learn_sizes,
            learn_times=all_times,
            output_path=f"{output_prefix}_mode_{mode}_time_vs_learning_sample_size.png",
            log_scale=True,
        )
        goal_size = len(fixed_automaton.states) if fixed_automaton is not None else nb_states
        # Plot accuracy versus learning sample size and resulting automaton size, colored by learning_part
        plot_accuracy_versus_sample_and_result_size(
            learn_sample_sizes=all_learn_sizes,
            acc=all_acc,
            goal_size=goal_size,
            result_sizes=all_result_sizes,
            output_path=f"{output_prefix}_mode_{mode}_time_vs_size_colored_by_part.png",
            log_scale=True,
        )
    plot_accuracies(
        learning_parts=learning_parts,
        mean_acc=accuracy_by_mode,
        err_acc=error_by_mode,
        mode=modes,
        output_path=f"modes_comparison.png",
        uncertainty=uncertainty,
        nb_runs=nb_runs,
    )


def plot_accuracies(
    learning_parts,
    mean_acc,
    err_acc,
    mode,
    output_path="accuracy_comparison.png",
    uncertainty="ci95",
    nb_runs=30,
):
    fig, ax = plt.subplots(figsize=(8, 5))
    for i in range(mean_acc.shape[0]):
        ax.errorbar(
            learning_parts,
            mean_acc[i],
            yerr=err_acc[i],
            fmt="o-",
            label=f"Mode {mode[i]}",
            capsize=4,
            elinewidth=1,
        )
    ax.set_xlabel("learning_part")
    ax.set_ylabel("Accuracy")
    ax.set_title(f"Accuracy vs proportion of the sample given ({uncertainty}, {nb_runs} runs) for different modes")
    ax.set_ylim(0.0, 1.02)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to: {output_path}")

def plot_accuracy_vs_learning_part(
    learning_parts,
    mean_acc,
    err_acc,
    output_path="accuracy_vs_learning_part.png",
    uncertainty="ci95",
    nb_runs=30,
):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        learning_parts,
        mean_acc,
        yerr=err_acc,
        fmt="o-",
        color="tab:blue",
        capsize=4,
        elinewidth=1,
    )
    ax.set_xlabel("learning_part")
    ax.set_ylabel("Accuracy")
    ax.set_title(f"Accuracy vs proportion of the sample given ({uncertainty}, {nb_runs} runs)")
    ax.set_ylim(0.0, 1.02)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to: {output_path}")


def plot_learning_time_vs_learning_sample_size(
    learn_sample_sizes,
    learn_times,
    output_path="time_vs_learning_sample_size.png",
    log_scale=True,
):
    x = np.asarray(learn_sample_sizes, dtype=float)
    y = np.asarray(learn_times, dtype=float)

    if len(x) == 0:
        print("No data to plot for learning time vs learning sample size.")
        return

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(x, y, alpha=0.6, s=24, color="tab:red", label="Runs")

    if log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")
        mask = (x > 0) & (y > 0)
        xf, yf = x[mask], y[mask]
        if len(xf) >= 2:
            lx, ly = np.log10(xf), np.log10(yf)
            k, b = np.polyfit(lx, ly, 1)
            C = 10 ** b
            x_fit = np.linspace(xf.min(), xf.max(), 300)
            y_fit = C * (x_fit ** k)
            ax.plot(x_fit, y_fit, color="tab:orange", lw=2, label=f"Fit: t ≈ {C:.2e}·n^{k:.2f}")

    ax.set_xlabel("Learning sample size (#words)")
    ax.set_ylabel("Learning time (s)")
    ax.set_title("Learning time vs learning sample size" + (" (log-log)" if log_scale else ""))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to: {output_path}")


def plot_accuracy_versus_sample_and_result_size(
    learn_sample_sizes,
    acc,
    goal_size,
    result_sizes,
    output_path="accuracy_vs_sample_and_result_size.png",
    log_scale=True,
):
    x = np.asarray(learn_sample_sizes, dtype=float)
    y = np.asarray(acc, dtype=float)
    s = np.asarray(result_sizes, dtype=float)

    if len(x) == 0:
        print("No data to plot for accuracy vs sample and result size.")
        return
    fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(x, y, s=50, c=s, cmap="viridis", alpha=0.7, edgecolors="w", linewidth=0.5)
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Learned automaton #states")
    if log_scale:
        ax.set_xscale("log")
    ax.set_xlabel("Learning sample size (#words)")
    ax.set_ylabel("Accuracy")
    ax.set_ylim(0.0, 1.02)
    plt.suptitle("Accuracy vs learning sample size (⚠️ log scale) colored by learned automaton size") 
    plt.title(f"target automaton has {goal_size} states")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to: {output_path}")

if __name__ == "__main__":
    with keep.running():

        smallparts = np.linspace(0.01, 0.1, 5, endpoint=False)
        parts = np.linspace(0.1, 1, 5)
        allparts = np.concatenate((smallparts, parts))
        testautomaton = generate_sfa(nb_states=8)
        sample0 = generate_random_sample(testautomaton, num_samples=2000, stop_prob=0.1, mode=0)
        sample1 = generate_random_sample(testautomaton, num_samples=2000, stop_prob=0.1, mode=1)
        sample2 = generate_random_sample(testautomaton, num_samples=2000, stop_prob=0.1, mode=2)
        fixed_test_sample = sample0.union(sample1).union(sample2)
        visualize_automaton(testautomaton, path="./SAITesting/test_automaton2")
    
        benchmark_random_sampling_vs_learning_part(
            fixed_automaton=testautomaton,
            fixed_test_sample=fixed_test_sample,
            learning_parts=allparts,
            nb_states=8,
            nb_runs=15,
            nb_samples=2000,
            stop_prob=0.15,
            modes=[-1],
            uncertainty="ci95",
            output_prefix=f"sai+rpni",
        )