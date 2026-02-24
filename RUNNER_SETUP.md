# 🏃 Self-Hosted Runner Setup Guide

This guide explains how to register your local machine as a GitHub Action runner so it can automatically trigger the AI PR Review Agent.

## 1. Create a Self-Hosted Runner on GitHub
1.  Navigate to your repository on GitHub.
2.  Go to **Settings** -> **Actions** -> **Runners**.
3.  Click **New self-hosted runner**.
4.  Select your Operating System (**Windows**).
5.  Follow the **Download** and **Configure** instructions provided by GitHub exactly:
    -   Download the runner package.
    -   Extract it to a folder (e.g., `C:\actions-runner`).
    -   Run `./config.cmd` and provide the token shown on the GitHub page.
    -   When asked for a name, you can use `local-ai-runner`.
    -   When asked for labels, the default `self-hosted` is perfect.

## 2. Start the Runner
After configuration, start the runner application:
```powershell
./run.cmd
```
*Your runner is now "listening" for jobs.*

## 3. How it Works
1.  When you raise a PR, GitHub sees the `.github/workflows/pr-review.yml` file.
2.  Because the workflow specifies `runs-on: self-hosted`, GitHub sends the job to your running `run.cmd` process.
3.  The runner executes `src/cli.py` which:
    -   Analyzes the PR using your local Ollama.
    -   Saves the findings into `checkpoints.db`.
    -   Pauses for approval.
4.  You then open the **Streamlit UI** and see the PR waiting for your review.

## ⚠️ Important Notes
- **Ollama**: Ensure Ollama is running on your machine before the runner starts a job.
- **Python**: Ensure the runner has access to your Python environment (the `pip install -r requirements.txt` step in the workflow handles this).
- **Security**: Self-hosted runners should only be used on private repositories or repositories where you trust the contributors, as they run code on your local machine.

## 4. Using with Other Repositories
You can use this same agent to review any of your GitHub projects without moving any code:

1.  **Register the Runner at Account Level**:
    -   Go to your personal GitHub **Settings** -> **Actions** -> **Runners**.
    -   Register your PC there. This makes the runner available to **all** your repositories.
2.  **Add the Workflow to your other Project**:
    -   In your other repository, create a folder `.github/workflows/`.
    -   Create a file named `pr-review.yml`.
    -   Copy the contents from [EXTERNAL_REPO_WORKFLOW.yml.example](EXTERNAL_REPO_WORKFLOW.yml.example) into that file.
3.  **Update the path**:
    -   Open the new `pr-review.yml` and make sure the `cd` command points to your local `prreviewsystem` directory:
        ```yaml
        cd "E:\rnd\antigravity\prreviewsystem"
        ```

That's it! Now, whenever you open a PR in that project, your local agent will wake up, analyze it, and wait for you in the Streamlit "Control Room."
