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
        "id": "convo_1_clarification",
        "description": "Missing Seniority (Tests the new AI Engineer clarification logic)",
        "target_names": [],
        "messages": [
            {"role": "user", "content": "I want to hire AI engineer."}
        ],
        "subsequent_messages": [
            {"role": "user", "content": "Senior level."}
        ]
    },
    {
        "id": "convo_2_comparison",
        "description": "Comparison (Tests the fixed Gemini intent extraction)",
        "target_names": ["Automata Pro", "AI Skills"],
        "messages": [
            {"role": "user", "content": "what is the difference between automata and ai-skills catalog"}
        ],
        "subsequent_messages": []
    },
    {
        "id": "convo_3_standard",
        "description": "Standard Flow (Vague -> Refined)",
        "target_names": ["OPQ Leadership Report"],
        "messages": [
            {"role": "user", "content": "We need a solution for senior leadership."}
        ],
        "subsequent_messages": [
            {"role": "user", "content": "The pool consists of CXOs and directors."}
        ]
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
            for idx, r in enumerate(recommendations, 1):
                convo_md += f"{idx}. **{r['name']}** [{r['test_type']}] - [Link]({r['url']})\n"
        else:
            convo_md += "*No recommendations provided.*\n"
            
        # Save Conversation MD
        file_path = OUTPUT_DIR / f"{tc['id']}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(convo_md)
        print(f"Saved {file_path}")

    # Compute Final Metrics
    avg_latency = total_latency / queries_run if queries_run else 0
    
    metrics_md = "# Evaluation Metrics\n\n"
    metrics_md += f"- **Total Queries Executed:** {queries_run}\n"
    metrics_md += f"- **Average Latency:** {avg_latency:.2f} seconds\n"
    metrics_md += f"- **Max Latency Constraint:** 30.0 seconds\n"
    metrics_md += f"- **Latency Status:** {'✅ PASS' if avg_latency < 30 else '❌ FAIL'}\n\n"
    
    metrics_path = OUTPUT_DIR / "metrics.md"
    with open(metrics_path, "w", encoding="utf-8") as f:
        f.write(metrics_md)
    print(f"\nSaved metrics to {metrics_path}")
    print(f"Average Latency: {avg_latency:.2f}s")

if __name__ == "__main__":
    try:
        requests.get(API_URL.replace("/chat", "/health"), timeout=5)
        run_evaluations()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is the Uvicorn server running?")
