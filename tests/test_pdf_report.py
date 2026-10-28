from frontend.pdf_report import build_investment_pdf


def example():
    return {
        "thesis": "Seed-stage healthcare AI",
        "results": [{
            "company": {
                "name": "Demo Startup",
                "funding_stage": "Seed",
                "description": "Fictional startup",
                "source_url": "https://example.com",
            },
            "stage_status": "match",
            "stage_reason": "Seed matches",
            "attributes": [{
                "name": "Founders",
                "value": "Demo Founder",
                "source_url": "https://example.com",
            }],
            "analyst_review": {
                "summary": "Demo summary",
                "red_flags": [],
                "follow_up_questions": ["Verify revenue?"],
            },
            "error": None,
        }],
    }


def test_pdf_contains_valid_header():
    assert build_investment_pdf(example()).startswith(b"%PDF-")


def test_pdf_handles_empty_results():
    assert build_investment_pdf(
        {"results": []}
    ).startswith(b"%PDF-")


def test_pdf_escapes_untrusted_text():
    sample = example()
    sample["results"][0]["company"]["name"] = "<script> & Demo"
    assert len(build_investment_pdf(sample)) > 1000
