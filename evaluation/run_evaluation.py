"""
Automated evaluation runner for baseline vs enhanced system
"""
import json
from pathlib import Path
from evaluation_engine import EvaluationEngine
from multilingual_analyzer import MultilingualAnalyzer
from vector_storage import VectorStore

def load_test_dataset(filepath: str) -> list:
    """Load annotated test dataset in JSONL format"""
    samples = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    return samples

def evaluate_baseline_analyzer(test_samples: list) -> dict:
    """Evaluate prompt-only baseline (no RAG, no tools)"""
    analyzer = MultilingualAnalyzer()
    engine = EvaluationEngine()
    
    predictions = []
    ground_truth = []
    
    for sample in test_samples:
        # Run baseline analysis
        result = analyzer.analyze_text(sample["text"], sample["stock_code"])
        predictions.append(result["risk_level"])
        ground_truth.append(sample["gold_risk_level"])
    
    # Calculate metrics
    metrics = engine.evaluate_risk_detection(
        [(p, 0.5) for p in predictions],  # (risk_level, confidence)
        ground_truth
    )
    
    return {k: v.value for k, v in metrics.items()}

def main():
    test_set_path = Path("evaluation/test_sets/hk_finance_annotated_v1.jsonl")
    
    if not test_set_path.exists():
        print(f"Test dataset not found: {test_set_path}")
        print("Please create annotated test set first.")
        return
    
    test_samples = load_test_dataset(str(test_set_path))
    print(f"Loaded {len(test_samples)} test samples")
    
    # Evaluate baseline
    baseline_results = evaluate_baseline_analyzer(test_samples)
    print(f"Baseline metrics: {baseline_results}")
    
    # Save results
    output_path = Path("evaluation/results/baseline_v1.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(baseline_results, f, indent=2)
    
    print(f"Results saved to {output_path}")

if __name__ == "__main__":
    main()