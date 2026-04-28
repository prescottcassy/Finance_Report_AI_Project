import re


def summarize_verification_results(results: list[dict]) -> str:
    number_re = re.compile(r"\$?\d[\d,\.]*\s*(?:%|billion|million|k|thousand)?", flags=re.IGNORECASE)
    lines = []

    for result in results:
        fname = result.get('file_name', 'analysis document')
        overall = result.get('overall_status', 'review')

        verdict_counts = {}
        for f in result.get('findings', []):
            v = f.get('verdict', 'Unclear')
            verdict_counts[v] = verdict_counts.get(v, 0) + 1

        sup = verdict_counts.get('Supported', 0)
        part = verdict_counts.get('Partially Supported', 0)
        uns = verdict_counts.get('Unsupported', 0)
        unc = verdict_counts.get('Unclear', 0)

        lines.append(f"{fname}: {str(overall).replace('_', ' ').capitalize()} — Supported: {sup}, Partially: {part}, Unsupported: {uns}, Unclear: {unc}")

        if uns > 0:
            numeric_examples = []
            non_numeric_examples = []
            for f in result.get('findings', []):
                if f.get('verdict') != 'Unsupported':
                    continue
                claim = (f.get('claim') or '').replace('\n', ' ').strip()
                evidence = (f.get('evidence') or '').replace('\n', ' ').strip()

                if number_re.search(claim) or number_re.search(evidence):
                    num_match = number_re.search(evidence) or number_re.search(claim)
                    num_snip = num_match.group(0) if num_match else ''
                    numeric_examples.append((claim[:180], num_snip))
                else:
                    non_numeric_examples.append(claim[:180])

            lines.append("  Top unsupported numeric examples:")
            shown = 0
            for claim_snip, num_snip in numeric_examples:
                if shown >= 3:
                    break
                if num_snip:
                    lines.append(f"  - {claim_snip}  ({num_snip})")
                else:
                    lines.append(f"  - {claim_snip}")
                shown += 1

            if shown == 0:
                lines.append("  (no numeric examples found — listing unsupported claims)")
                for claim_snip in non_numeric_examples[:3]:
                    lines.append(f"  - {claim_snip}")

        lines.append("")

    return "\n".join(lines).strip()


# Mocked results similar to screenshot counts
results = [
    {
        'file_name': 'Financial Story, Walmart.pdf',
        'overall_status': 'needs_review',
        'findings': [
            {'claim': 'In the last year, the constant sound mentioned amounted to an impressive sum of $713.2 billion of income.', 'verdict': 'Unsupported', 'reason': '', 'evidence': '$713.2 billion'},
            {'claim': 'The store is visited by 280 million consumers each week while there are 10,900 Walmart locations in 19 countries.', 'verdict': 'Unsupported', 'reason': '', 'evidence': '280 million'},
            {'claim': "Because of the $285.5 billion that it brings into the picture, Walmart has become known as the king of American food retail.", 'verdict': 'Unsupported', 'reason': '', 'evidence': '$285.5 billion'},
            {'claim': 'Sample supported numeric claim: revenue was $150.2 billion.', 'verdict': 'Supported', 'reason': '', 'evidence': '$150.2 billion'},
            {'claim': 'Another supported numeric claim: net income $20.5B.', 'verdict': 'Supported', 'reason': '', 'evidence': '$20.5B'},
            {'claim': 'Partially supported claim: revenue ~ $100B (source reports $99.8B).', 'verdict': 'Partially Supported', 'reason': '', 'evidence': '$99.8B'},
            {'claim': 'Unclear claim with numbers 123', 'verdict': 'Unclear', 'reason': '', 'evidence': ''},
            {'claim': 'Extra unsupported qualitative statement with no numbers but flagged', 'verdict': 'Unsupported', 'reason': '', 'evidence': ''},
            {'claim': 'Yet another supported: EPS $3.10', 'verdict': 'Supported', 'reason': '', 'evidence': '$3.10'},
            {'claim': 'Partially supported numeric: 5% growth claimed vs 4.6% in source', 'verdict': 'Partially Supported', 'reason': '', 'evidence': '4.6%'},
            {'claim': 'Unsupported numeric: $999.9M claim', 'verdict': 'Unsupported', 'reason': '', 'evidence': '$999.9M'},
        ]
    }
]


print(summarize_verification_results(results))
