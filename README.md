# 🤖 Stateful PR Review Agent

A fully functional, autonomous PR Review Agent built with **LangGraph** and **PydanticAI**. It analyzes GitHub pull requests using a local Ollama model and provides a Human-in-the-Loop interface for review before posting findings back to GitHub.

---

## ✨ Key Features
- **Real GitHub Integration**: Fetches actual diffs and files using `PyGithub`.
- **Automatic Triggers**: Integrated with **GitHub Actions** via self-hosted runners.
- **Local LLM Intelligence**: Uses Ollama (`kimi-k2.5`) for deep semantic analysis.
- **Security & Logic Scans**: Orchestrates `bandit` for security and custom LLM prompts for logic flaws.
- **Semantic Impact Analysis**: Uses `ripgrep` to find call sites affected by source changes.
- **Persistent Control Room**: A **Streamlit** dashboard that stores and manages pending reviews in a SQLite database.

---

## 🏗️ Architecture & Logic
For a deep dive into the state machine, schemas, and node logic, see [AGENTS.md](AGENTS.md).

---

## 🚀 Setup & Execution

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) installed and running locally.
- A GitHub Personal Access Token (PAT).

### 2. Environment Configuration
Create a `.env` file in the root directory (use `.env.example` as a template):
```env
GITHUB_TOKEN=your_gh_token_here
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Automatic Triggers (Optional but Recommended)
To allow GitHub to automatically send PRs to your local machine for analysis, follow the [RUNNER_SETUP.md](RUNNER_SETUP.md) guide.

### 5. Run the Application
The primary interface for the agent is the Streamlit UI.
```bash
streamlit run app.py
```
**Usage Flow:**
1. **Automated**: When a PR is raised, your PC automatically analyzes it.
2. **Review**: Open the Streamlit UI and select the PR from the "Review Sessions" sidebar.
3. **Approve**: Review findings, add a comment, and click **Approve & Post**.
4. **Manual**: You can still paste a URL manually in the "New Review" section.

---

## 🧪 Testing
Run the pytest suite to verify graph checkpointing and memory:
```bash
$env:PYTHONPATH="src"
pytest tests/ -v
```

---

## 🛠️ Tech Stack
- **LangGraph**: State management and HIL checkpoints.
- **PydanticAI**: Structured LLM communication.
- **Ollama**: Local model hosting (`kimi-k2.5:cloud`).
- **Streamlit**: Human-in-the-loop dashboard.
- **PyGithub**: API interaction.
- **Bandit & Ripgrep**: Local analysis tools.
