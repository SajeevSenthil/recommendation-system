import os
import time
import json
import requests
from pathlib import Path

API_URL = "http://localhost:7860/chat"
OUTPUT_DIR = Path("output")

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)

# Define test cases for evaluation (Recall and Latency)
TEST_CASES = [
    {
        "id": "convo_1",
        "description": "Senior Leadership (Expects OPQ32r or Leadership Report)",
        "target_names": ["Occupational Personality Questionnaire OPQ32r", "OPQ Leadership Report"],
        "messages": [
            {"role": "user", "content": "We need a solution for senior leadership."}
        ],
        "subsequent_messages": [
            {"role": "user", "content": "The pool consists of CXOs, director-level positions; people with more than 15 years of experience."}
        ]
    },
    {
        "id": "convo_2",
        "description": "Rust Engineer (Expects Smart Interview Live Coding & Verify G+)",
        "target_names": ["Smart Interview Live Coding", "SHL Verify Interactive G+"],
        "messages": [
            {"role": "user", "content": "I'm hiring a senior Rust engineer for high-performance networking infrastructure. What assessments should I use?"}
        ],
        "subsequent_messages": []
    },
    {
        "id": "convo_3",
        "description": "Entry Level Sales (Expects Sales assessments)",
        "target_names": ["Sales Scenarios", "OPQ Sales Report"],
        "messages": [
            {"role": "user", "content": "I need to hire entry-level sales reps."}
        ],
        "subsequent_messages": []
    }
]

def run_evaluations():
    print("Starting evaluations...")
    
    total_latency = 0.0
    queries_run = 0
    recall_hits = 0
    total_targets = 0
    
    for tc in TEST_CASES:
        print(f"\nRunning {tc['id']}...")
        convo_md = f"# Evaluation: {tc['description']}\n\n"
        
        current_messages = tc["messages"].copy()
        
        # Turn 1
        start_time = time.time()
        response = requests.post(API_URL, json={"messages": current_messages})
        latency = time.time() - start_time
        
        total_latency += latency
        queries_run += 1
        
        data = response.json()
        convo_md += f"**User:** {current_messages[-1]['content']}\n\n"
        convo_md += f"**Agent:** {data.get('reply', '')}\n\n"
        
        # If there are subsequent messages, do Turn 2
        if tc["subsequent_messages"]:
            current_messages.append({"role": "assistant", "content": data.get("reply", "")})
            current_messages.extend(tc["subsequent_messages"])
            
            start_time = time.time()
            response = requests.post(API_URL, json={"messages": current_messages})
            latency = time.time() - start_time
            
            total_latency += latency
            queries_run += 1
            
            data = response.json()
            convo_md += f"**User:** {current_messages[-1]['content']}\n\n"
            convo_md += f"**Agent:** {data.get('reply', '')}\n\n"
        
        # Check Recall
        recommendations = data.get("recommendations", [])
        if recommendations:
            convo_md += "### Recommendations\n"
            rec_names = [r["name"] for r in recommendations]
            for idx, r in enumerate(recommendations, 1):
                convo_md += f"{idx}. **{r['name']}** [{r['test_type']}] - [Link]({r['url']})\n"
            
            # Calculate Recall for this test case
            hits = sum(1 for target in tc["target_names"] if any(target.lower() in name.lower() for name in rec_names))
            recall_hits += hits
            total_targets += len(tc["target_names"])
            convo_md += f"\n*Recall Hits:* {hits} / {len(tc['target_names'])}\n"
        else:
            convo_md += "*No recommendations provided.*\n"
            total_targets += len(tc["target_names"])
            convo_md += f"\n*Recall Hits:* 0 / {len(tc['target_names'])}\n"
            
        # Save Conversation MD
        file_path = OUTPUT_DIR / f"{tc['id']}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(convo_md)
        print(f"Saved {file_path}")

    # Compute Final Metrics
    avg_latency = total_latency / queries_run if queries_run else 0
    recall_percentage = (recall_hits / total_targets * 100) if total_targets else 0
    
    metrics_md = "# Evaluation Metrics\n\n"
    metrics_md += f"- **Total Queries Executed:** {queries_run}\n"
    metrics_md += f"- **Average Latency:** {avg_latency:.2f} seconds\n"
    metrics_md += f"- **Max Latency Constraint:** 30.0 seconds\n"
    metrics_md += f"- **Latency Status:** {'✅ PASS' if avg_latency < 30 else '❌ FAIL'}\n\n"
    metrics_md += f"### Recall Metrics\n"
    metrics_md += f"- **Recall@10:** {recall_percentage:.1f}% ({recall_hits} hits out of {total_targets} expected targets)\n"
    
    metrics_path = OUTPUT_DIR / "metrics.md"
    with open(metrics_path, "w", encoding="utf-8") as f:
        f.write(metrics_md)
    print(f"\nSaved metrics to {metrics_path}")
    print(f"Average Latency: {avg_latency:.2f}s | Recall: {recall_percentage:.1f}%")

if __name__ == "__main__":
    try:
        requests.get(API_URL.replace("/chat", "/health"), timeout=5)
        run_evaluations()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is the Uvicorn server running?")
