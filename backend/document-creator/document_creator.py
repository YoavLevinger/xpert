import os
import logging
import markdown
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from weasyprint import HTML
from backend.shared.models import DocRequest

logger = logging.getLogger("uvicorn")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "generated-code"
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/create")
async def create_document(req: DocRequest):
    folder_path = os.path.join(OUTPUT_DIR, req.folder_id)
    os.makedirs(folder_path, exist_ok=True)
    logger.info(f"Creating document in {folder_path}")

    md_content = f"""
# 📄 LLM Pipeline Summary

## 🧾 Description
{req.description}

## ✅ Subtasks
"""
    for i, subtask in enumerate(req.subtasks, 1):
        md_content += f"{i}. {subtask}\n"

    md_content += "\n## 💻 Developer Subtasks\n"
    for i, subtask in enumerate(req.dev_subtasks, 1):
        md_content += f"{i}. {subtask}\n"

    md_content += "\n## 📂 Code Files"
    for fname in os.listdir(folder_path):
        if fname.endswith(".py"):
            md_content += f"\n\n### `{fname}`\n"
            try:
                with open(os.path.join(folder_path, fname), "r") as code_file:
                    md_content += "\n```python\n" + code_file.read() + "\n```"
            except Exception as e:
                logger.warning(f"Could not read file {fname}: {e}")

    # Add effort estimation
    effort = req.effort_table or {}
    combined_effort = req.combined_effort or {}

    repos = effort.get("repositories", [])
    avg_time = effort.get("average_time")


    md_content += "\n\n## 🧠 Combined Effort Estimation (SBERT + Code Analysis)\n"

    # GitHub Similar Repositories Analysis
    github_repos = combined_effort.get("github_repositories", [])
    if github_repos:
        md_content += "\n### 🔍 Top Similar GitHub Repositories (Filtered)\n"
        md_content += "\n| Repository | Estimated Effort (hours) | Description |\n"
        md_content += "|------------|--------------------------|-------------|\n"
        for repo in github_repos:
            # name = str(repo.get("name", "N/A")).replace("|", "\\|")
            name = str(repo.get("owner", "N/A")).replace("|", "\\|") + "/" + str(repo.get("name", "N/A")).replace("|", "\\|")
            hours = repo.get("hours", "N/A")
            desc = repo.get("description", "N/A").replace("\n", " ").replace("|", "\\|")
            md_content += f"| {name} | {hours:.2f} | {desc} |\n"

        avg = combined_effort.get("github_average", None)
        if avg is not None:
            md_content += f"\n\n**Average Effort (without outliers):** {avg:.2f} hours\n"
    else:
        md_content += "\nNo GitHub repository effort data available.\n"

    # Local Code Effort Estimation
    local_effort = combined_effort.get("local_effort", {})
    if local_effort:
        md_content += "\n\n### 💻 Estimated Effort for Your Generated Code\n"
        for k, v in local_effort.items():
            md_content += f"- **{k}**: {v}\n"
    else:
        md_content += "\nNo local code estimation data available.\n"

    # Expert advice (optional)
    if req.expert_advice:
        md_content += "\n\n## 🧠 Expert Recommendations\n"
        for advisor, advice in req.expert_advice.items():
            md_content += f"\n### {advisor}\n"
            md_content += f"{advice}\n"

    # Policy analysis
    md_content += "\n\n## 📜 Policy Analysis\n"
    for policy_name, policy_text in req.policy_texts.items():
        md_content += f"\n### {policy_name.capitalize()} Policy\n"
        md_content += policy_text[:3000] + "\n"

    # Write MD
    md_path = os.path.join(folder_path, "summary.md")
    try:
        with open(md_path, "w") as f:
            f.write(md_content)
    except Exception as e:
        logger.error(f"Failed to write Markdown file: {e}")

    # Write HTML
    html_path = os.path.join(folder_path, "summary.html")
    try:
        markdown_body = markdown.markdown(md_content, extensions=['fenced_code', 'tables'])

        html_content = f"""
        <html>
        <head>
          <style>
            table {{
              width: 100%;
              border-collapse: collapse;
              margin-top: 1em;
            }}
            th, td {{
              border: 1px solid #aaa;
              padding: 8px;
              text-align: left;
            }}
            th {{
              background-color: #f2f2f2;
            }}
          </style>
        </head>
        <body>
        {markdown_body}
        </body>
        </html>
        """

        with open(html_path, "w") as f:
            f.write(html_content)
    except Exception as e:
        logger.error(f"Failed to write HTML file: {e}")

    # Write PDF
    pdf_path = os.path.join(folder_path, "summary.pdf")
    try:
        HTML(string=html_content).write_pdf(pdf_path)
        logger.info(f"Generated PDF at {pdf_path}")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")

    return FileResponse(pdf_path, media_type='application/pdf', filename="summary.pdf")

@app.get("/download/{folder_id}")
def download_pdf(folder_id: str):
    pdf_path = os.path.join("generated-code", folder_id, "summary.pdf")
    if not os.path.exists(pdf_path):
        return {"error": "PDF not found"}, 404

    return FileResponse(pdf_path, media_type="application/pdf", filename="summary.pdf")
