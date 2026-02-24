import sys
import argparse
import io
from src.agent import graph

# Ensure UTF-8 output even on Windows terminals
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def run_analysis(pr_url: str):
    """
    Runs the PR review agent up to the human approval checkpoint.
    Uses the PR URL as the thread_id for persistence.
    """
    config = {"configurable": {"thread_id": pr_url}}
    
    # We only run if the thread doesn't already have a state, or if we want to re-run.
    # For automation, we usually want to start fresh or resume.
    # Here we just invoke it. LangGraph will resume from checkpoint if it exists.
    
    print(f"Starting automated analysis for: {pr_url}")
    
    # The graph will run all nodes until 'human_approval' where it hits the interrupt.
    # Note: We pass the pr_url in the initial state if it's the first time.
    initial_state = {
        "pr_url": pr_url,
        "human_approved": False,
        "human_comment": None,
        "footguns": [],
        "security_issues": [],
        "semantic_impacts": [],
        "external_context": {}
    }
    
    # stream returns an iterator of events
    for event in graph.stream(initial_state, config, stream_mode="values"):
        try:
            if "summary" in event and event["summary"]:
                summary_text = str(event["summary"].executive_summary)[:100]
                print(f"Found Summary: {summary_text}...")
            if "footguns" in event:
                print(f"Footguns detected: {len(event['footguns'])}")
        except Exception as e:
            print(f"Error printing event: {e}")

    print(f"\nAnalysis paused at checkpoint. You can now review it in the Streamlit UI.")
    print(f"Thread ID: {pr_url}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PR Review Agent CLI Trigger")
    parser.add_argument("--url", required=True, help="The full URL of the GitHub Pull Request")
    
    args = parser.parse_args()
    
    try:
        run_analysis(args.url)
    except Exception as e:
        print(f"Error during analysis trigger: {e}")
        sys.exit(1)
