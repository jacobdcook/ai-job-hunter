#!/usr/bin/env python3
"""
Test/Verify SOC Feeder Classifier
Validates taxonomy classification on sample job titles to ensure categorization works correctly.
"""

from taxonomy import classify_job
from job_classifier import classify_and_score_job

# Test cases: (title, description_snippet, expected_category)
TEST_CASES = [
    # SOC_DIRECT
    ("SOC Analyst", "", "SOC_DIRECT"),
    ("Security Operations Analyst", "", "SOC_DIRECT"),
    ("Incident Response Engineer", "", "SOC_DIRECT"),
    ("Threat Hunter", "", "SOC_DIRECT"),

    # SOC_ADJACENT - SIEM
    ("Splunk Administrator", "", "SOC_ADJACENT"),
    ("Elasticsearch Engineer", "", "SOC_ADJACENT"),
    ("SIEM Analyst", "", "SOC_ADJACENT"),

    # SOC_ADJACENT - NOC
    ("Network Operations Center Analyst", "", "SOC_ADJACENT"),
    ("NOC Technician", "", "SOC_ADJACENT"),
    ("24x7 Monitoring Specialist", "", "SOC_ADJACENT"),

    # SOC_ADJACENT - Endpoint/EDR
    ("Crowdstrike Engineer", "", "SOC_ADJACENT"),
    ("Endpoint Detection Engineer", "", "SOC_ADJACENT"),
    ("Intune Administrator", "", "SOC_ADJACENT"),

    # SOC_ADJACENT - IAM
    ("Active Directory Administrator", "", "SOC_ADJACENT"),
    ("IAM Specialist", "", "SOC_ADJACENT"),
    ("Okta Administrator", "", "SOC_ADJACENT"),

    # SOC_ADJACENT - Firewall/Network
    ("Palo Alto Networks Engineer", "", "SOC_ADJACENT"),
    ("Network Security Engineer", "", "SOC_ADJACENT"),

    # SOC_ADJACENT - Help Desk with IT Context
    ("Help Desk Technician", "experience with Active Directory and security tickets", "SOC_ADJACENT"),
    ("IT Support Specialist", "knowledge of Azure, M365, and endpoint security", "SOC_ADJACENT"),

    # IT_FEEDER
    ("Junior Systems Administrator", "", "IT_FEEDER"),
    ("IT Support Technician", "", "IT_FEEDER"),
    ("Network Technician", "", "IT_FEEDER"),
    ("Systems Engineer", "", "IT_FEEDER"),

    # AVOID - Hard excludes
    ("Customer Service Representative", "", "AVOID"),
    ("Retail Associate", "", "AVOID"),
    ("Registered Nurse", "", "AVOID"),
    ("Bank Teller", "", "AVOID"),
    ("Warehouse Worker", "", "AVOID"),

    # AVOID - No IT context
    ("Help Desk Support", "general computer support, no security or infrastructure focus", "AVOID"),
]


def test_classification():
    """Run all test cases and report results."""
    print("=" * 80)
    print("SOC FEEDER CLASSIFIER VERIFICATION")
    print("=" * 80)

    passed = 0
    failed = 0
    errors = []

    for title, description, expected_category in TEST_CASES:
        result = classify_job(title, description)
        category = result['category']
        feeder_score = result['feeder_score']
        reasons = result['reasons']

        status = "✅" if category == expected_category else "❌"
        print(f"\n{status} Title: {title}")
        print(f"   Expected: {expected_category:<12} | Got: {category:<12} | Score: {feeder_score:>3}")
        print(f"   Reasons: {' | '.join(reasons)}")

        if category == expected_category:
            passed += 1
        else:
            failed += 1
            errors.append({
                'title': title,
                'expected': expected_category,
                'got': category,
                'reasons': reasons
            })

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print("=" * 80)

    if errors:
        print("\n❌ FAILURES:")
        for error in errors:
            print(f"\n  Title: {error['title']}")
            print(f"    Expected: {error['expected']}")
            print(f"    Got: {error['got']}")
            print(f"    Reasons: {error['reasons']}")

    return failed == 0


def test_priority_scoring():
    """Test priority score calculation with various combinations."""
    print("\n" + "=" * 80)
    print("PRIORITY SCORE CALCULATION")
    print("=" * 80)

    test_scores = [
        ("SOC Analyst", "", 9, True, True),  # Direct SOC, internship, shift
        ("Splunk Engineer", "", 8, False, False),  # SIEM, no internship
        ("Help Desk (no IT context)", "general support", 5, True, False),  # Should be AVOID
        ("Junior Sysadmin", "", 6, True, False),  # IT feeder + internship
    ]

    for title, desc, groq_score, is_intern, is_shift in test_scores:
        result = classify_and_score_job(title, desc, groq_score)
        priority = result['priority_score']
        category = result['category']

        print(f"\nTitle: {title}")
        print(f"  Category: {category}")
        print(f"  Groq Score: {groq_score}/10 | Feeder Score: {result['feeder_score']}/100")
        print(f"  Is Internship: {is_intern} | Is Shift-based: {is_shift}")
        print(f"  Combined Priority Score: {priority:.1f}/100")


def test_internship_detection():
    """Test that internship/apprenticeship/rotation keywords are detected."""
    print("\n" + "=" * 80)
    print("INTERNSHIP/APPRENTICESHIP/ROTATION DETECTION")
    print("=" * 80)

    internship_titles = [
        "SOC Analyst Internship",
        "Security Engineering Apprentice",
        "IT Support Rotational Program",
        "Help Desk Trainee",
        "Network Engineering Co-op",
    ]

    for title in internship_titles:
        result = classify_job(title, "")
        is_internship = result['is_internship']
        print(f"\n{'✅' if is_internship else '❌'} {title}: is_internship={is_internship}")


if __name__ == "__main__":
    all_pass = test_classification()
    test_priority_scoring()
    test_internship_detection()

    print("\n" + "=" * 80)
    if all_pass:
        print("✅ All classification tests passed!")
    else:
        print("❌ Some tests failed. Review output above.")
    print("=" * 80)
