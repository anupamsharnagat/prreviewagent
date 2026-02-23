import pytest
from src.agent import graph

def test_agent_graph_pauses_at_human_approval():
    config = {"configurable": {"thread_id": "test_thread_1"}}
    input_state = {"pr_url": "https://github.com/mock/repo/pull/123"}
    
    # Run the graph until the interrupt
    events = graph.stream(input_state, config, stream_mode="values")
    
    final_event = None
    for event in events:
        final_event = event
        
    # The graph should have paused BEFORE 'post_to_github'
    state_snapshot = graph.get_state(config)
    
    # The next node should be 'post_to_github'
    assert state_snapshot.next == ('post_to_github',)
    
    # Check that findings were populated
    assert state_snapshot.values["summary"] is not None
    assert len(state_snapshot.values["footguns"]) > 0
    assert len(state_snapshot.values["security_issues"]) > 0
    
    # Resume the graph with a manual override (simulating human approval)
    graph.update_state(config, {"human_approved": True})
    
    # Continue execution
    resume_events = graph.stream(None, config, stream_mode="values")
    
    last_resume_event = None
    for event in resume_events:
        last_resume_event = event
        
    # It should finish execution
    final_state = graph.get_state(config)
    assert not final_state.next # empty tuple means it reached END

if __name__ == "__main__":
    test_agent_graph_pauses_at_human_approval()
    print("All tests passed successfully!")
