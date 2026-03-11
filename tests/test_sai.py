import time
import csv
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


def test_sai_characteristic(nb_states=10,nb_runs=100,fixed_seed=None,visualize=False,print_info=False,return_raw=False):
    sample_sizes = np.zeros(nb_runs)
    sample_true_sizes = np.zeros(nb_runs)
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
        sample_true_sizes[i] = sum(len(word) for word, _ in sample)
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
    avg_sample_true = float(np.mean(sample_true_sizes))
    print(f"For automaton with {nb_states} states:")
    print(f"Average sample size: {avg_sample}, Average run time: {avg_time}, Average true sample size: {avg_sample_true}")
    if return_raw:
        return avg_sample, avg_time, avg_sample_true, sample_sizes, run_times, sample_true_sizes
    return avg_sample, avg_time, avg_sample_true

def save_raw_benchmark_data(output_prefix, records):
    csv_path = f"{output_prefix}_raw_runs.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["nb_states", "run_idx", "sample_size_words", "sample_true_size_letters", "runtime_s"],
        )
        writer.writeheader()
        writer.writerows(records)
    print(f"Raw benchmark data saved to: {csv_path}")

def benchmark_and_plot(
    states_list,
    nb_runs=50,
    print_info=False,
    write_csv=False,
    output_prefix="sai_benchmark",
    uncertainty="ci95",  # "ci95", "sem", or "std"
):
    avg_samples, avg_samples_true, avg_times = [], [], []
    sample_err, sample_true_err, time_err = [], [], []

    all_sample_sizes = []
    all_run_times = []
    if write_csv:
        raw_records = []

    for n in states_list:
        avg_sample, avg_time, avg_sample_true, samples_raw, times_raw, sample_true_sizes = test_sai_characteristic(
            nb_states=n,
            nb_runs=nb_runs, # if n < 40 else nb_runs // 2,
            visualize=False,
            print_info=print_info,
            return_raw=True,
        )

        avg_samples.append(avg_sample)
        avg_samples_true.append(avg_sample_true)
        avg_times.append(avg_time)

        all_sample_sizes.extend(samples_raw.tolist())
        all_run_times.extend(times_raw.tolist())

        s_std = float(np.std(samples_raw, ddof=1)) if len(samples_raw) > 1 else 0.0
        st_std = float(np.std(sample_true_sizes, ddof=1)) if len(sample_true_sizes) > 1 else 0.0
        t_std = float(np.std(times_raw, ddof=1)) if len(times_raw) > 1 else 0.0

        if uncertainty == "std":
            sample_err.append(s_std)
            sample_true_err.append(st_std)
            time_err.append(t_std)
        else:
            s_sem = s_std / np.sqrt(len(samples_raw)) if len(samples_raw) > 0 else 0.0
            st_sem = st_std / np.sqrt(len(sample_true_sizes)) if len(sample_true_sizes) > 0 else 0.0
            t_sem = t_std / np.sqrt(len(times_raw)) if len(times_raw) > 0 else 0.0

            if uncertainty == "sem":
                sample_err.append(s_sem)
                sample_true_err.append(st_sem)
                time_err.append(t_sem)
            else:  # ci95
                sample_err.append(1.96 * s_sem)
                sample_true_err.append(1.96 * st_sem)
                time_err.append(1.96 * t_sem)

    if write_csv:
        for run_idx, (sw, sl, rt) in enumerate(
            zip(samples_raw.tolist(), sample_true_sizes.tolist(), times_raw.tolist()), start=1
        ):
            raw_records.append(
                {
                    "nb_states": n,
                    "run_idx": run_idx,
                    "sample_size_words": sw,
                    "sample_true_size_letters": sl,
                    "runtime_s": rt,
                }
            )
        save_raw_benchmark_data(output_prefix, raw_records)
    # 1) sample size + sample true size vs states
    plot_samples_vs_states(
        states_list=states_list,
        avg_samples=avg_samples,
        avg_samples_true=avg_samples_true,
        sample_err=sample_err,
        sample_true_err=sample_true_err,
        output_path=f"{output_prefix}_samples_vs_states.png",
        uncertainty=uncertainty,
        nb_runs=nb_runs,
    )

    # 2) runtime vs states
    plot_runtime_vs_states(
        states_list=states_list,
        avg_times=avg_times,
        time_err=time_err,
        output_path=f"{output_prefix}_runtime_vs_states.png",
        uncertainty=uncertainty,
        nb_runs=nb_runs,
    )

    # 3) runtime vs sample size
    plot_runtime_vs_sample_size(
        sample_sizes=all_sample_sizes,
        run_times=all_run_times,
        output_path=f"{output_prefix}_runtime_vs_sample.png",
        log_scale=True,
    )


def plot_samples_vs_states(
    states_list,
    avg_samples,
    avg_samples_true,
    sample_err,
    sample_true_err,
    output_path="sai_benchmark_samples_vs_states.png",
    uncertainty="ci95",
    nb_runs=100,
):
    fig, ax1 = plt.subplots(figsize=(8, 5))

    color1 = "tab:blue"
    ax1.set_xlabel("Number of states")
    ax1.set_ylabel("Average sample size (#words)", color=color1)
    ax1.errorbar(
        states_list, avg_samples, yerr=sample_err,
        fmt="o--", color=color1, capsize=4, elinewidth=1, label="Sample size (#words)"
    )
    ax1.tick_params(axis="y", labelcolor=color1)

    ax2 = ax1.twinx()
    color2 = "tab:green"
    ax2.set_ylabel('Average sample "true" size (#letters)', color=color2)
    ax2.errorbar(
        states_list, avg_samples_true, yerr=sample_true_err,
        fmt="s-", color=color2, capsize=4, elinewidth=1, label='Sample "true" size (#letters)'
    )
    ax2.tick_params(axis="y", labelcolor=color2)

    #factors = #letters/#words
    factors = [
        (t / s) if s and s > 0 else np.nan
        for s, t in zip(avg_samples, avg_samples_true)
    ]
    for x, y, f in zip(states_list, avg_samples_true, factors):
        if np.isfinite(f):
            ax2.annotate(
                f"×{f:.2f}",
                xy=(x, 0),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color="black"
            )


    plt.suptitle(f"Sample metrics vs number of states ({uncertainty}, {nb_runs} runs)")
    plt.title("Factors indicate how many letters per word on average",fontsize=9)
    fig.tight_layout()
    plt.grid(True, axis="x", alpha=0.3)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to: {output_path}")


def plot_runtime_vs_states(
    states_list,
    avg_times,
    time_err,
    output_path="sai_benchmark_runtime_vs_states.png",
    uncertainty="ci95",
    nb_runs=100,
):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        states_list, avg_times, yerr=time_err,
        fmt="o-", color="tab:red", capsize=4, elinewidth=1
    )
    ax.set_xlabel("Number of states")
    ax.set_ylabel("Average run time (s)")
    ax.set_title(f"Runtime vs number of states ({uncertainty}, {nb_runs} runs)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to: {output_path}")


def plot_runtime_vs_sample_size(
    sample_sizes,
    run_times,
    output_path="sai_runtime_vs_sample.png",
    log_scale=False
):
    sample_sizes = np.asarray(sample_sizes, dtype=float)
    run_times = np.asarray(run_times, dtype=float)

    if len(sample_sizes) == 0:
        print("No data to plot for runtime vs sample size.")
        return

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(sample_sizes, run_times, alpha=0.6, s=24, color="tab:purple", label="Runs")
    if log_scale:
        ax.set_xscale("log")
        ax.set_yscale("log")
        mask = (sample_sizes > 0) & (run_times > 0)
        x = sample_sizes[mask]
        y = run_times[mask]

        if len(x) >= 2:
            lx = np.log10(x)
            ly = np.log10(y)

            k, b = np.polyfit(lx, ly, 1)   # ly = k*lx + b
            C = 10 ** b

            x_fit = np.linspace(x.min(), x.max(), 300)
            y_fit = C * (x_fit ** k)
            ax.plot(x_fit, y_fit, color="tab:orange", lw=2,
                    label=f"Fit: t ≈ {C:.2e}·n^{k:.2f}")

            # R² in log space
            ly_pred = k * lx + b
            ss_res = np.sum((ly - ly_pred) ** 2)
            ss_tot = np.sum((ly - np.mean(ly)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan

            ax.text(
                0.02, 0.98,
                f"log10(t) = {k:.2f}·log10(n) + {b:.2f}\nR² = {r2:.3f}",
                transform=ax.transAxes,
                va="top",
                fontsize=8,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.85),
            )

            print(f"log-log linear fit: log10(t) = {k:.4f}*log10(n) + {b:.4f}  (R²={r2:.4f})")

    ax.set_xlabel("Sample size (#words)")
    ax.set_ylabel("Run time (s)")
    ax.set_title("Runtime vs sample size" + (" (log-log)" if log_scale else ""))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to: {output_path}")

if __name__ == "__main__":
    benchmark_and_plot(
        states_list=[5, 10, 15, 20, 30, 50, 75, 100, 150],
        nb_runs=20,
        print_info=False,
        write_csv=False,
        output_prefix="sai_benchmark"
    )
