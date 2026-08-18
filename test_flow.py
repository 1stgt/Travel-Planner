import sys
import os

# Add the current directory to sys.path so we can import travel_planner
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from travel_planner.app.main import app


def run_verification_test():
    print("=" * 70)
    print("STARTING END-TO-END WORKFLOW VERIFICATION TEST")
    print("=" * 70)

    client = TestClient(app)

    # ============================================================
    # STEP 1: CREATE TRAVEL PLAN
    # ============================================================

    plan_payload = {
        "destination": " India",
        "travel_dates": "2026-11-01 to 2026-11-10",
        "budget_range": "Moderate",
        "travelers_count": 2,
        "interests": [
            "historical monuments",
            "royal palaces",
            "local bazaars",
            "street food",
        ],
    }

    print("\n[Step 1] Submitting travel plan request...")

    response = client.post("/plan", json=plan_payload)

    assert response.status_code == 201, (
        f"Failed to submit plan request: {response.text}"
    )

    plan_data = response.json()

    plan_id = plan_data["plan_id"]
    status = plan_data["status"]

    print(f"-> SUCCESS: Plan created with ID: {plan_id}")
    print(f"-> Current Status: {status} (Expected: pending_review)")

    assert status == "pending_review", (
        "Workflow did not pause at HITL breakpoint."
    )

    # ============================================================
    # STEP 2: FETCH DRAFT PLAN
    # ============================================================

    print("\n[Step 2] Fetching draft plan status...")

    response = client.get(f"/plan/{plan_id}")

    assert response.status_code == 200, (
        f"Failed to get plan status: {response.text}"
    )

    status_data = response.json()

    print(f"-> Destination: {status_data['destination']}")
    print(f"-> Dates: {status_data['travel_dates']}")

    draft_itinerary = status_data.get("draft_itinerary", "")

    print(
        f"-> Draft Itinerary length: "
        f"{len(draft_itinerary)} characters"
    )

    assert status_data["status"] == "pending_review", (
        "Initial plan status should be pending_review."
    )

    assert len(draft_itinerary.strip()) > 100, (
        "Draft itinerary is empty or too short."
    )

    # ============================================================
    # STEP 3: FINAL PLAN SHOULD NOT BE AVAILABLE YET
    # ============================================================

    print(
        "\n[Step 3] Fetching final plan before approval "
        "(Should Fail)..."
    )

    # Now request final itinerary before approval
    response = client.get(f"/plan/{plan_id}/final")

    print(
        f"-> Response Code: {response.status_code} "
        f"(Expected: 400)"
    )

    assert response.status_code == 400, (
        "Final itinerary should not be accessible before approval."
    )

    error_detail = response.json().get("detail", "")

    print(f"-> Error Detail: {error_detail}")

    assert "not finalized" in error_detail.lower(), (
        "Unexpected error message for unfinalized plan."
    )

    # ============================================================
    # STEP 4: MODIFY THE DRAFT
    # ============================================================

    review_payload_modify = {
        "action": "modify",
        "feedback": (
            "Please improve the itinerary by including a sunrise "
            "visit to the Taj Mahal on the Agra day, more time for "
            "Amber Fort in Jaipur, local bazaars, and weather-aware "
            "scheduling for outdoor activities."
        ),
    }

    print(
        "\n[Step 4] Submitting modification feedback "
        "(Action: modify)..."
    )

    response = client.post(
        f"/plan/{plan_id}/review",
        json=review_payload_modify,
    )

    assert response.status_code == 200, (
        f"Failed to submit modification: {response.text}"
    )

    modify_data = response.json()

    print(
        f"-> New status after modification request: "
        f"{modify_data['status']}"
    )

    # The workflow should execute research/planner again
    # and pause at HITL review.
    assert modify_data["status"] == "pending_review", (
        "Workflow did not return to pending_review "
        "after modification."
    )

    # ------------------------------------------------------------
    # Verify that the draft was updated
    # ------------------------------------------------------------

    response = client.get(f"/plan/{plan_id}")

    assert response.status_code == 200, (
        f"Failed to fetch updated plan: {response.text}"
    )

    updated_data = response.json()

    updated_draft = updated_data.get("draft_itinerary", "")

    print(
        f"-> Updated draft length: "
        f"{len(updated_draft)} characters"
    )

    assert len(updated_draft.strip()) > 100, (
        "Updated draft itinerary is empty."
    )

    # ============================================================
    # STEP 5: APPROVE THE PLAN
    # ============================================================

    review_payload_approve = {
        "action": "approve",
        "feedback": (
            "The revised itinerary looks good. "
            "Approve and finalize the travel plan."
        ),
    }

    print("\n[Step 5] Submitting approval (Action: approve)...")

    response = client.post(
        f"/plan/{plan_id}/review",
        json=review_payload_approve,
    )

    assert response.status_code == 200, (
        f"Failed to approve plan: {response.text}"
    )

    approve_data = response.json()

    print(f"-> Status after approval: {approve_data['status']}")

    assert approve_data["status"] == "completed", (
        "Plan status is not 'completed' after approval."
    )

    # ============================================================
    # STEP 6: RETRIEVE FINAL TRAVEL PACKAGE
    # ============================================================

    print("\n[Step 6] Retrieving finalized travel package...")

    response = client.get(f"/plan/{plan_id}/final")

    assert response.status_code == 200, (
        f"Failed to fetch final itinerary: {response.text}"
    )

    final_data = response.json()

    print(f"-> Final Itinerary ID: {final_data['plan_id']}")

    final_itinerary = final_data.get("final_itinerary", "")

    try:
        print(final_itinerary)
    except UnicodeEncodeError:
        print(
            final_itinerary
            .encode("ascii", "ignore")
            .decode("ascii")
        )

    print("-" * 70)

    # ============================================================
    # FINAL VALIDATIONS
    # ============================================================

    assert final_data["plan_id"] == plan_id, (
        "Final itinerary plan ID does not match original plan ID."
    )

    assert len(final_itinerary.strip()) > 100, (
        "Final itinerary is empty or too short."
    )

    assert "FINAL TRIP PLAN" in final_itinerary, (
        "Final plan header missing."
    )

    assert "Budget Summary" in final_itinerary, (
        "Final budget breakdown missing."
    )

    print("\n" + "=" * 70)
    print("ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_verification_test()