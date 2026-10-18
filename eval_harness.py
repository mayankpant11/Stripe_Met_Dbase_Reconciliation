"""Four-case runbook retrieval check using the same code as the API."""

from retrieval import retrieve_top3


GOLDEN_SET = [
    {
        "query": "Why is invoice in_123 amount 0 but Metronome shows 1200?",
        "should_cite": "doc_metronome_delay",
        "should_be_indeterminable": False,
    },
    {
        "query": "Why invoice in_456 charged 1200 when commit 4000 remaining?",
        "should_cite": "doc_commit_trueup",
        "should_be_indeterminable": False,
    },
    {
        "query": "Invoice in_789 currency EUR vs USD mismatch",
        "should_cite": "doc_currency_mismatch",
        "should_be_indeterminable": False,
    },
    {
        "query": "Why invoice in_999 amount 200 unknown fee?",
        "should_cite": None,
        "should_be_indeterminable": True,
    },
]


def evaluate() -> None:
    print("=== Eval: Stripe–Metronome Reconciliation Demo ===")
    passed = 0
    hallucinated = 0

    for case in GOLDEN_SET:
        top_docs = retrieve_top3(case["query"])
        predicted_citation = top_docs[0][0]["id"] if top_docs else None
        is_hallucination = (
            case["should_be_indeterminable"] and predicted_citation is not None
        )
        correct = (
            predicted_citation is None
            if case["should_be_indeterminable"]
            else predicted_citation == case["should_cite"]
        )

        passed += int(correct and not is_hallucination)
        hallucinated += int(is_hallucination)
        print(f"\nQuery: {case['query']}")
        print(
            f"Expected cite: {case['should_cite']} | Predicted: {predicted_citation} | "
            f"Top docs: {[(doc['id'], round(score, 2)) for doc, score in top_docs]}"
        )
        print(
            f"Correct: {correct} | Hallucinated: {is_hallucination} | "
            f"{'PASS' if correct and not is_hallucination else 'FAIL'}"
        )

    total = len(GOLDEN_SET)
    print("\n=== SUMMARY ===")
    print(f"Accuracy: {passed}/{total} = {passed / total * 100:.0f}%")
    print(f"Hallucination: {hallucinated}/{total} = {hallucinated / total * 100:.0f}%")
    print("Verdict: SHIPPABLE" if hallucinated == 0 and passed >= 3 else "Needs fix")


if __name__ == "__main__":
    evaluate()
