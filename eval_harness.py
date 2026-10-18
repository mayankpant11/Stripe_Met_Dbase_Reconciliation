
import json, pathlib
BASE = pathlib.Path(__file__).parent
from tools import get_stripe_invoice, get_metronome_contract, get_docs
import math

def cosine_sim(query, doc_content):
    q_words = set(query.lower().split())
    d_words = set(doc_content.lower().split())
    overlap = len(q_words & d_words)
    return overlap / (math.sqrt(len(q_words))*math.sqrt(len(d_words)) + 1e-6)

def retrieve_top3(query, threshold=0.2):
    docs = json.loads((BASE / "docs.json").read_text())
    scored = [(doc, cosine_sim(query, doc["content"] + " " + doc["title"])) for doc in docs]
    scored = sorted(scored, key=lambda x: x[1], reverse=True)[:3]
    return [(d,s) for d,s in scored if s >= threshold]

GOLDEN_SET = [
    {"query": "Why is invoice in_123 amount 0 but Metronome shows 1200?", "expected": "delayed_metronome_rating", "should_cite": "doc_metronome_delay", "should_be_indeterminable": False},
    {"query": "Why invoice in_456 charged 1200 when commit 4000 remaining?", "expected": "commit_trueup", "should_cite": "doc_commit_trueup", "should_be_indeterminable": False},
    {"query": "Invoice in_789 currency EUR vs USD mismatch", "expected": "currency_mismatch", "should_cite": "doc_currency_mismatch", "should_be_indeterminable": False},
    {"query": "Why invoice in_999 amount 200 unknown fee?", "expected": "indeterminable", "should_cite": None, "should_be_indeterminable": True},
]

def evaluate():
    print("=== Eval: Stripe + Metronome Reconciliation (No GL) ===")
    passed = 0
    hallucinated = 0
    for case in GOLDEN_SET:
        top_docs = retrieve_top3(case["query"])
        # Determine prediction
        if not top_docs and case["should_be_indeterminable"]:
            pred_cite = None
            is_indeterminable = True
        elif top_docs:
            pred_cite = top_docs[0][0]["id"]
            is_indeterminable = False
        else:
            pred_cite = "none"
            is_indeterminable = False
        
        correct = False
        if case["should_be_indeterminable"]:
            correct = len(top_docs) == 0
        else:
            correct = pred_cite == case["should_cite"]
        
        is_halluc = False
        if case["should_be_indeterminable"] and pred_cite is not None and not is_indeterminable:
            is_halluc = True
            hallucinated += 1
        
        if correct and not is_halluc:
            passed += 1
        
        print(f"\nQuery: {case['query']}")
        print(f"Expected cite: {case['should_cite']} | Predicted: {pred_cite} | Top docs: {[(d['id'], round(s,2)) for d,s in top_docs]}")
        print(f"Correct: {correct} | Hallucinated: {is_halluc} | {'PASS' if correct and not is_halluc else 'FAIL'}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Accuracy: {passed}/{len(GOLDEN_SET)} = {passed/len(GOLDEN_SET)*100:.0f}%")
    print(f"Hallucination: {hallucinated}/{len(GOLDEN_SET)} = {hallucinated/len(GOLDEN_SET)*100:.0f}%")
    print("Verdict: SHIPPABLE" if hallucinated==0 and passed>=3 else "Needs fix")

if __name__ == "__main__":
    evaluate()
