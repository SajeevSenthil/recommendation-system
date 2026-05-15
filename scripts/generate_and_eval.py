import os
import random
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Ensure we have the API key to generate synthetic data
load_dotenv()
from app.llm.gemini import gemini

API_URL = "http://localhost:7860/chat"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

def generate_synthetic_queries(num_queries=10):
    with open("data/shl_product_catalog.json", "r", encoding="utf-8") as f:
        catalog = json.load(f)
    
    # Pick a random sample of assessments
    sample_items = random.sample(catalog, num_queries)
    
    synthetic_data = []
    print(f"Generating {num_queries} synthetic queries via Gemini...")
    for item in sample_items:
        name = item.get("name", "")
        desc = item.get("description", "")[:500]  # Take first 500 chars to save tokens
        
        prompt = f"""
        You are a recruiter. Write a single, complete sentence asking to assess a candidate on these skills. 
        DO NOT use the exact assessment name '{name}'.
        Description to base the request on: {desc}
        """
        
        try:
            query = gemini(prompt, max_tokens=100, temperature=0.7).strip()
            # Clean up quotes if any
            query = query.strip('"\'')
            synthetic_data.append({
                "target_name": name,
                "query": query
            })
            print(f"Target: {name}\nQuery: {query}\n")
            time.sleep(5)  # Respect Gemini Free Tier Quotas
        except Exception as e:
            print(f"Error generating query for {name}: {e}")
            
    return synthetic_data

def evaluate_synthetic_data(synthetic_data):
    print("\nEvaluating against /chat endpoint...")
    
    recall_hits = 0
    total = len(synthetic_data)
    results_md = "# Synthetic Evaluation Results\n\n"
    
    for idx, data in enumerate(synthetic_data, 1):
        target = data["target_name"]
        query = data["query"]
        
        response = requests.post(API_URL, json={
            "messages": [{"role": "user", "content": query}]
        })
        res_json = response.json()
        
        recs = res_json.get("recommendations", [])
        rec_names = [r["name"] for r in recs]
        
        # Check if target is in top 10 recommendations
        hit = target in rec_names
        if hit:
            recall_hits += 1
            
        results_md += f"### Test Case {idx}\n"
        results_md += f"- **Target Assessment:** {target}\n"
        results_md += f"- **Synthetic Query:** {query}\n"
        results_md += f"- **Result:** {'✅ HIT' if hit else '❌ MISS'}\n"
        results_md += f"- **Agent Reply:** {res_json.get('reply')}\n\n"
        
        if recs:
            results_md += "**Top Recommendations Returned:**\n"
            for i, r in enumerate(recs[:3], 1):
                results_md += f"{i}. {r['name']}\n"
            results_md += "\n"

    recall_10 = (recall_hits / total) * 100 if total > 0 else 0
    
    metrics_summary = f"## Final Metrics\n- **Total Queries:** {total}\n- **Recall@10:** {recall_10:.1f}%\n"
    results_md = metrics_summary + "\n---\n" + results_md
    
    out_path = OUTPUT_DIR / "synthetic_results.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(results_md)
        
    print(f"\nSaved results to {out_path}")
    print(f"Final Recall@10: {recall_10:.1f}%")

if __name__ == "__main__":
    try:
        requests.get(API_URL.replace("/chat", "/health"), timeout=5)
        synth_data = generate_synthetic_queries(10)
        if synth_data:
            evaluate_synthetic_data(synth_data)
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is the Uvicorn server running?")
