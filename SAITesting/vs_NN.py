import torch
from torch import nn
import torch.utils.data as data
from torch.nn.utils.rnn import pad_sequence
from aalpy.utils import save_automaton_to_file, visualize_automaton
from aalpy.learning_algs.deterministic_passive.SAI import SAI
from utilities import generate_random_sample, generate_sfa
from typing import List, Tuple, Set

class WordDataset(data.Dataset):
    def __init__(self, samples: List[Tuple[Tuple[int, ...], bool]], pad_value: int = 0, offset: int = 0, vocab_size: int = None):
        self.pad_value = pad_value
        self.words = [torch.tensor(w, dtype=torch.long) for w, _ in samples]
        self.labels = [torch.tensor(float(y), dtype=torch.float32) for _, y in samples]

        # raw symbols may be negative
        if offset == 0:
            min_symbol = min((int(w.min()) for w in self.words if len(w) > 0), default=0)
            self.offset = 1 - min_symbol            # min raw symbol -> 1
        else:
            self.offset = offset
        max_symbol = max((int(w.max()) for w in self.words if len(w) > 0), default=0)
        

        self.pad_value = 0
        if vocab_size is not None:
            self.vocab_size = vocab_size
        else:
            self.vocab_size = (max_symbol + self.offset) + 1  # +1 because indices are inclusive

        self.words = [w + self.offset for w in self.words]
        self.words = pad_sequence(self.words, batch_first=True, padding_value=self.pad_value)

    def __len__(self):
        return len(self.words)

    def __getitem__(self, idx):
        return self.words[idx], self.labels[idx]
    


class GRUModel(nn.Module):
    def __init__(self, vocab_size: int,padding_value: int, embedding_dim: int, hidden_dim: int):
        super(GRUModel, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=padding_value)
        self.gru = nn.GRU(embedding_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x):

        embedded = self.embedding(x)                # [B, T, E]
        out, h_n = self.gru(embedded)               # out: [B, T, H], h_n: [1, B, H]
        last_hidden = h_n[-1]                       # [B, H]
        logits = self.fc(last_hidden).squeeze(-1)   # [B]
        return logits
    
def train_one_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for x, y in loader:
        x, y = x.to(device),  y.to(device)

        optimizer.zero_grad()
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * x.size(0)
        preds = (torch.sigmoid(logits) >= 0.5).float()
        correct += (preds == y).sum().item()
        total += x.size(0)

    return total_loss / total, correct / total


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)

            logits = model(x)
            loss = criterion(logits, y)

            total_loss += loss.item() * x.size(0)
            preds = (torch.sigmoid(logits) >= 0.5).float()
            correct += (preds == y).sum().item()
            total += x.size(0)

    return total_loss / total, correct / total

def learn_from_sample(dataset: WordDataset, criterion, device, epochs=20):
    
    n = len(dataset)
    train_size = int(0.8 * n)
    val_size = n - train_size
    train_dataset, val_dataset= data.random_split(
        dataset, [train_size, val_size])
    print(f"Vocabulary size: {dataset.vocab_size}")
    print(f"Total number of samples: {len(dataset)}")
    print(f"Training samples: {len(train_dataset)}")
    print(f"Validation samples: {len(val_dataset)}")
    train_loader = data.DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = data.DataLoader(val_dataset, batch_size=32)

    
    model = GRUModel(vocab_size=dataset.vocab_size, padding_value=dataset.pad_value, embedding_dim=64, hidden_dim=128).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    best_acc = 0.0
    best_state = None
    for epoch in range(epochs):
        train_loss, train_acc = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        print(f"Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}, Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")
        if val_acc > best_acc:
            best_acc = val_acc
            best_state = model.state_dict()
    if best_state is not None:
        model.load_state_dict(best_state)
    return model



def benchmark_SAI_vs_NN(testautomaton, sample_sizes: List[int], test_sample : Set[tuple[tuple[int,...],bool]], epochs=20):
    device = torch.device("cpu")
    print(f"Using device: {device}")
    criterion = nn.BCEWithLogitsLoss()

    test_size = len(test_sample)
    test_min = min((int(min(w)) for w, _ in test_sample if len(w) > 0), default=0)
    test_max = max((int(max(w)) for w, _ in test_sample if len(w) > 0), default=0)
    SFA_accs = []
    NN_accs = []
    for size in sample_sizes:
        learn_sample = generate_random_sample(testautomaton, size, 0.5, mode=2)
        learn_min = min((int(min(w)) for w, _ in learn_sample if len(w) > 0), default=0)
        learn_max = max((int(max(w)) for w, _ in learn_sample if len(w) > 0), default=0)
        globalmin = min(test_min, learn_min)
        globalmax = max(test_max, learn_max)
        offset = 1 - globalmin
        vocab_size = globalmax + offset + 1 
        learn_dataset = WordDataset(list(learn_sample), offset=offset, vocab_size=vocab_size)
        test_dataset = WordDataset(list(test_sample), pad_value=learn_dataset.pad_value, offset=offset, vocab_size=vocab_size)
        test_loader = data.DataLoader(test_dataset, batch_size=32)
        epochs = 20
        NN_model = learn_from_sample(learn_dataset, criterion, device, epochs)
        SFA_model = SAI(learn_sample, testautomaton.algebra).run_SAI()
        NN_acc = 0
        SFA_acc = 0
        for x, y in test_loader:
            x, y = x.to(device), y.to(device)
            with torch.no_grad():
                logits = NN_model(x)
                preds = (torch.sigmoid(logits) >= 0.5).float()
                NN_acc += (preds == y).sum().item()
                pad = learn_dataset.pad_value
            for word, label in zip(x.cpu().numpy(), y.cpu().numpy()):
                end = len(word)
                while end > 0 and word[end - 1] == pad:
                    end -= 1

                unpadded = word[:end]  # keeps internal zeros, removes only right padding
                word_tuple = tuple((unpadded - learn_dataset.offset).tolist())
                true_label = bool(label)
                sfa_pred = SFA_model.accepts(word_tuple)
                if sfa_pred == true_label:
                    SFA_acc += 1
        SFA_acc /= test_size
        NN_acc /= test_size
        print(f"Sample size: {size} - SFA Accuracy: {SFA_acc:.4f}, NN Accuracy: {NN_acc:.4f}")
        SFA_accs.append(SFA_acc)
        NN_accs.append(NN_acc)
    graph_data = {
        "sample_sizes": sample_sizes,
        "SFA_accuracies": SFA_accs,
        "NN_accuracies": NN_accs
    }
    return graph_data


def plot_benchmark_results(graph_data):
    import matplotlib.pyplot as plt

    sample_sizes = graph_data["sample_sizes"]
    SFA_accuracies = graph_data["SFA_accuracies"]
    NN_accuracies = graph_data["NN_accuracies"]

    plt.figure(figsize=(10, 6))
    plt.plot(sample_sizes, SFA_accuracies, marker='o', label='SAI Learned SFA')
    plt.plot(sample_sizes, NN_accuracies, marker='o', label='Neural Network')
    plt.xscale('log')
    plt.xlabel('Sample Size (log scale)')
    plt.ylim(0, 1.02)
    plt.ylabel('Accuracy')
    plt.title('Benchmark: SAI Learned SFA vs Neural Network')
    plt.legend()
    plt.grid(True)
    plt.savefig("./SAITesting/benchmark_results.png")


if __name__ == "__main__":
    
    testautomaton = generate_sfa(10)
    visualize_automaton(testautomaton, path="./SAITesting/test_automatonNN")
    test_sample = generate_random_sample(testautomaton, 1000, 0.5, mode=2)
    graph_data = benchmark_SAI_vs_NN(testautomaton, sample_sizes=[ 50, 100, 500, 1000, 5000 ], test_sample=test_sample, epochs=20)
    plot_benchmark_results(graph_data)
    
    
    