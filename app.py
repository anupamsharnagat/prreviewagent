import streamlit as st
import asyncio

from src.agent import graph, memory

st.set_page_config(page_title="Autonomous PR Review Agent", layout="wide")

st.title("🤖 AI PR Reviewer: Control Room")

# Sidebar: Browse Pending or Past Reviews
st.sidebar.title("📨 Review Sessions")

if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

checkpoints = list(memory.list(None))
# Extract unique thread IDs from checkpoints
unique_threads = sorted(list(set(cp.config["configurable"]["thread_id"] for cp in checkpoints)))

if not unique_threads:
    st.sidebar.info("No active reviews found in database.")
    selected_thread = "New Review"
else:
    selected_thread = st.sidebar.selectbox(
        "Select a Review Session:", 
        ["New Review"] + unique_threads,
        index=0 if "thread_id" not in st.session_state else (unique_threads.index(st.session_state.thread_id) + 1 if st.session_state.thread_id in unique_threads else 0)
    )

if selected_thread == "New Review":
    if "new_url_id" not in st.session_state:
        st.session_state.new_url_id = f"manual_{len(unique_threads) + 1}"
    st.session_state.thread_id = st.session_state.new_url_id
    pr_url = st.text_input("Enter GitHub PR URL to Start New Analysis:")
else:
    st.session_state.thread_id = selected_thread
    pr_url = selected_thread # By convention in our CLI, thread_id IS the URL

config = {"configurable": {"thread_id": st.session_state.thread_id}}

if st.button("Start Review") and pr_url:
    current_state = graph.get_state(config)
    if not current_state.next:
        initial_state = {"pr_url": pr_url, "human_approved": False}
        with st.status("Running analysis..."):
            for event in graph.stream(initial_state, config, stream_mode="values"):
                if "diff_content" in event:
                    st.write(f"Processing step...")
    st.rerun()

state = graph.get_state(config)

if state.next == ("post_to_github",):
    st.warning("Review paused for human approval. Please review findings below.")
    
    current_values = state.values
    report = current_values.get("final_report")
    
    if report:
        st.subheader("Generated Report")
        if report.summary:
            st.markdown(f"**Summary:** {report.summary.executive_summary}")
        
        if report.footguns:
            st.markdown("### 🚨 Logic Footguns")
            for fg in report.footguns:
                st.error(f"**{fg.file_path}:{fg.line_number}** - {fg.description}")
                st.caption(f"Suggestion: {fg.suggestion}")
        else:
            st.markdown("### 🚨 Logic Footguns")
            st.success("✅ No logic issues or footguns detected.")
                
        if report.security_issues:
            st.markdown("### 🔒 Security Issues")
            for sec in report.security_issues:
                st.error(f"**[{sec.severity}] {sec.file_path}:{sec.line_number}** - {sec.description}")
                st.caption(f"Remediation: {sec.remediation}")
        else:
            st.markdown("### 🔒 Security Issues")
            st.success("✅ No security vulnerabilities detected.")
                
        if report.semantic_impacts:
            st.markdown("### 🌍 Semantic Impacts")
            for imp in report.semantic_impacts:
                st.info(f"Function `{imp.changed_function}` impacted {len(imp.impacted_call_sites)} call sites.")
        else:
            st.markdown("### 🌍 Semantic Impacts")
            st.success("✅ No external semantic impacts found.")
        
    st.divider()
    human_comment = st.text_area("Add your own comment for the PR developer (optional):", placeholder="e.g., Looks good overall, but please check the variable naming in line 42.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Approve & Post to GitHub"):
            graph.update_state(config, {"human_approved": True, "human_comment": human_comment})
            with st.status("Posting to GitHub..."):
                for event in graph.stream(None, config, stream_mode="values"):
                    pass
            st.success("Successfully posted to GitHub!")
    with col2:
        if st.button("Reject"):
            graph.update_state(config, {"human_approved": False, "human_comment": human_comment})
            with st.status("Aborting..."):
                for event in graph.stream(None, config, stream_mode="values"):
                    pass
            st.error("Review rejected. Did not post to GitHub.")
