"""
CodeInsight AI - Batch Evaluation Runner

Runs the evaluation dataset against the running CodeInsight AI backend.

Features:
- Uses evaluation/dataset.json
- Runs a limited number of NEW questions per batch
- Saves results after EVERY successful question
- Skips questions already present in results.json
- Reuses repositories that are already analyzed and ready
- Can be safely stopped and resumed later
- Uses the real backend/API results
"""

import json
import time
import sys
import os
import requests


# ============================================================
# Configuration
# ============================================================

API_BASE = os.getenv(
    "CODEINSIGHT_API_BASE",
    "http://localhost:8000"
)

DATASET_PATH = os.path.join(
    os.path.dirname(__file__),
    "dataset.json"
)

RESULTS_PATH = os.path.join(
    os.path.dirname(__file__),
    "results.json"
)

# Number of NEW questions to run in one batch.
# We start with 5 for testing.
# Later you can run:
#   set EVALUATION_BATCH_SIZE=10
# or
#   set EVALUATION_BATCH_SIZE=15
BATCH_SIZE = int(
    os.getenv("EVALUATION_BATCH_SIZE", "5")
)


# ============================================================
# Repository status
# ============================================================

def get_repository_status(repo_id: str):
    """
    Get the current status of an analyzed repository.

    Returns:
        status_data dictionary if successful
        None if the status request fails
    """

    try:
        resp = requests.get(
            f"{API_BASE}/api/repository/{repo_id}/status",
            timeout=120
        )

        resp.raise_for_status()
        return resp.json()

    except requests.RequestException as e:
        print(
            f"  Could not check repository status "
            f"for {repo_id}: {e}"
        )
        return None


def wait_for_ready(repo_id: str, timeout: int = 600) -> bool:
    """
    Wait until repository analysis is complete.
    """

    start = time.time()

    while time.time() - start < timeout:

        data = get_repository_status(repo_id)

        if data is None:
            print("  Status check failed. Retrying in 5 seconds...")
            time.sleep(5)
            continue

        print(
            f"  [{repo_id}] "
            f"{data['status']} "
            f"({data['progress']}%) - "
            f"{data['detail']}"
        )

        if data["status"] == "ready":
            return True

        if data["status"] == "failed":
            return False

        time.sleep(3)

    print(
        f"  Repository did not become ready "
        f"within {timeout} seconds."
    )

    return False


# ============================================================
# Results handling
# ============================================================

def load_results():
    """
    Load previously saved evaluation results.
    """

    if not os.path.exists(RESULTS_PATH):
        return []

    try:

        with open(
            RESULTS_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, list):
            return data

    except (json.JSONDecodeError, OSError):

        print(
            "Warning: Could not read existing results.json."
        )

        print(
            "Starting with an empty result list."
        )

    return []


def save_results(results):
    """
    Save results immediately.

    A temporary file is written first so that an interrupted
    write is less likely to corrupt the existing results file.
    """

    temp_path = RESULTS_PATH + ".tmp"

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False
        )

    os.replace(
        temp_path,
        RESULTS_PATH
    )


def result_key(repo_url, question):
    """
    Create a unique key for a repository/question pair.
    """

    return (
        repo_url.strip(),
        question.strip()
    )


# ============================================================
# Find existing repository
# ============================================================

def find_existing_ready_repository(repo_url: str):
    """
    Try to find an already analyzed repository by asking the
    backend for the repository's deterministic ID.

    The backend currently generates repository IDs using the
    repository name plus a short identifier.

    For the first repository, we already know the repository ID
    from the previous successful analysis.

    If an existing repository cannot be found, return None and
    the normal analysis flow will be used.
    """

    # Known repository from the first test run.
    known_repositories = {
        "https://github.com/tiangolo/full-stack-fastapi-template":
            "full-stack-fastapi-template-db0d11",
        "https://github.com/fastapi/fastapi":
            "fastapi-74a56d"
    }

    repo_id = known_repositories.get(repo_url)

    if repo_id is None:
        return None

    data = get_repository_status(repo_id)

    if data is None:
        return None

    if data.get("status") == "ready":
        print(
            f"Repository already ready. "
            f"Reusing repo_id: {repo_id}"
        )

        return repo_id

    if data.get("status") in {
        "cloning",
        "parsing",
        "indexing",
        "processing"
    }:

        print(
            f"Repository already exists and is still being "
            f"processed: {repo_id}"
        )

        if wait_for_ready(repo_id):
            return repo_id

    return None


# ============================================================
# Analyze repository
# ============================================================

def analyze_repository(repo_url: str):
    """
    Reuse an already-ready repository when possible.
    Otherwise start a new analysis.
    """

    print(
        "\nChecking whether repository is already analyzed..."
    )

    existing_repo_id = find_existing_ready_repository(
        repo_url
    )

    if existing_repo_id:
        return existing_repo_id

    print(
        "No reusable ready repository found."
    )

    print(
        "Starting new repository analysis..."
    )

    try:

        resp = requests.post(
            f"{API_BASE}/api/repository/analyze",
            json={
                "repo_url": repo_url
            },
            timeout=60
        )

        if resp.status_code != 200:

            print(
                f"Failed to start analysis: "
                f"{resp.status_code} - {resp.text}"
            )

            return None

        repo_id = resp.json()["repo_id"]

        print(
            f"Repository ID: {repo_id}"
        )

    except requests.RequestException as e:

        print(
            f"Repository analysis request failed: {e}"
        )

        return None

    print(
        "Waiting for analysis to finish..."
    )

    try:

        ready = wait_for_ready(
            repo_id
        )

    except requests.RequestException as e:

        print(
            f"Status request failed: {e}"
        )

        return None

    if not ready:

        print(
            "Repository analysis did not finish successfully."
        )

        return None

    print(
        "Repository is ready."
    )

    return repo_id


# ============================================================
# Main evaluation
# ============================================================

def run():

    print(
        "=========================================="
    )

    print(
        " CodeInsight AI - Batch Evaluation"
    )

    print(
        "=========================================="
    )

    print(
        f"Backend:     {API_BASE}"
    )

    print(
        f"Dataset:     {DATASET_PATH}"
    )

    print(
        f"Results:     {RESULTS_PATH}"
    )

    print(
        f"Batch size:  {BATCH_SIZE}"
    )

    print(
        "=========================================="
    )


    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    with open(
        DATASET_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        dataset = json.load(f)


    # --------------------------------------------------------
    # Load previous results
    # --------------------------------------------------------

    all_results = load_results()

    completed = {
        result_key(
            r["repo_url"],
            r["question"]
        )
        for r in all_results
        if (
            "repo_url" in r
            and "question" in r
        )
    }

    print(
        f"\nPreviously completed questions: "
        f"{len(completed)}"
    )


    # --------------------------------------------------------
    # Find pending questions
    # --------------------------------------------------------

    pending_questions = []

    for repo in dataset["repositories"]:

        repo_url = repo["repo_url"]

        for q in repo["questions"]:

            key = result_key(
                repo_url,
                q["question"]
            )

            if key not in completed:

                pending_questions.append(
                    {
                        "repo_url": repo_url,
                        "question_data": q
                    }
                )


    print(
        f"Remaining questions: "
        f"{len(pending_questions)}"
    )


    if not pending_questions:

        print(
            "\nAll questions in the dataset "
            "have already been evaluated."
        )

        return


    # --------------------------------------------------------
    # Select only this batch
    # --------------------------------------------------------

    batch = pending_questions[
        :BATCH_SIZE
    ]

    print(
        f"\nRunning {len(batch)} "
        f"new questions in this batch."
    )


    # --------------------------------------------------------
    # Group selected questions by repository
    # --------------------------------------------------------

    repos_to_questions = {}

    for item in batch:

        repo_url = item["repo_url"]

        if repo_url not in repos_to_questions:

            repos_to_questions[
                repo_url
            ] = []

        repos_to_questions[
            repo_url
        ].append(
            item["question_data"]
        )


    # --------------------------------------------------------
    # Process repositories
    # --------------------------------------------------------

    for repo_url, questions in repos_to_questions.items():

        print(
            "\n=========================================="
        )

        print(
            f"Repository: {repo_url}"
        )

        print(
            "=========================================="
        )


        # ----------------------------------------------------
        # Analyze or reuse repository
        # ----------------------------------------------------

        repo_id = analyze_repository(
            repo_url
        )

        if repo_id is None:

            print(
                "Skipping this repository because "
                "analysis could not be completed."
            )

            continue


        # ----------------------------------------------------
        # Ask selected questions
        # ----------------------------------------------------

        for q in questions:

            category = q["category"]
            question = q["question"]

            key = result_key(
                repo_url,
                question
            )

            # Extra protection against duplicates.
            if key in completed:

                print(
                    "\nQuestion already completed. Skipping."
                )

                continue


            print(
                "\n------------------------------------------"
            )

            print(
                f"Category: {category}"
            )

            print(
                f"Question: {question}"
            )

            print(
                "------------------------------------------"
            )


            # ------------------------------------------------
            # Ask question
            # ------------------------------------------------

            try:

                resp = requests.post(
                    f"{API_BASE}/api/qa/ask",

                    json={
                        "repo_id": repo_id,
                        "question": question
                    },

                    timeout=300
                )

                if resp.status_code != 200:

                    print(
                        f"Failed: "
                        f"{resp.status_code} - "
                        f"{resp.text}"
                    )

                    continue

                data = resp.json()


            except requests.Timeout:

                print(
                    "Question request timed out. "
                    "This question was NOT saved."
                )

                continue


            except requests.RequestException as e:

                print(
                    f"Question request failed: {e}"
                )

                continue


            # ------------------------------------------------
            # Extract verification
            # ------------------------------------------------

            v = data["verification"]


            # ------------------------------------------------
            # Build result
            # ------------------------------------------------

            result = {

                "repo_url": repo_url,

                "repo_id": repo_id,

                "category": category,

                "question": question,

                "answer": data["answer"],

                "faithfulness": v[
                    "faithfulness"
                ],

                "answer_relevancy": v[
                    "answer_relevancy"
                ],

                "response_time_seconds": v[
                    "response_time_seconds"
                ],

                "faithfulness_method": v.get(
                    "faithfulness_method"
                ),

                "relevancy_method": v.get(
                    "relevancy_method"
                )
            }


            # ------------------------------------------------
            # Add result
            # ------------------------------------------------

            all_results.append(
                result
            )

            completed.add(
                key
            )


            # ------------------------------------------------
            # SAVE IMMEDIATELY
            # ------------------------------------------------

            save_results(
                all_results
            )


            # ------------------------------------------------
            # Print result
            # ------------------------------------------------

            print(
                f"Faithfulness = "
                f"{v['faithfulness']:.4f}"
            )

            print(
                f"Answer Relevancy = "
                f"{v['answer_relevancy']:.4f}"
            )

            print(
                f"Response Time = "
                f"{v['response_time_seconds']:.2f}s"
            )

            print(
                f"Verification method:"
            )

            print(
                f"  Faithfulness: "
                f"{v.get('faithfulness_method')}"
            )

            print(
                f"  Relevancy: "
                f"{v.get('relevancy_method')}"
            )

            print(
                f"Saved successfully. "
                f"Total saved = "
                f"{len(all_results)}"
            )


    # --------------------------------------------------------
    # Batch summary
    # --------------------------------------------------------

    remaining_after_batch = max(
        0,
        len(pending_questions) - len(batch)
    )


    print(
        "\n=========================================="
    )

    print(
        " Batch Complete"
    )

    print(
        "=========================================="
    )

    print(
        f"Total saved results: "
        f"{len(all_results)}"
    )

    print(
        f"Remaining questions: "
        f"{remaining_after_batch}"
    )

    print(
        f"Results file: "
        f"{RESULTS_PATH}"
    )

    print(
        "=========================================="
    )

    print(
        "\nTo continue later, simply run "
        "the same command again."
    )


# ============================================================
# Program entry point
# ============================================================

if __name__ == "__main__":

    try:

        run()

    except requests.exceptions.ConnectionError:

        print(
            f"\nCould not reach the CodeInsight AI backend "
            f"at {API_BASE}."
        )

        print(
            "Make sure the backend is running "
            "on port 8000."
        )

        sys.exit(1)