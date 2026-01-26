import os
import json
import time
from groq import Groq
from dotenv import load_dotenv
from config import YOUR_BACKGROUND

load_dotenv()

class JobAnalyzer:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("Warning: GROQ_API_KEY not found in .env file.")
        self.client = Groq(api_key=api_key) if api_key else None
        self.last_call_time = 0
        self.rate_limit_delay = 2  # seconds between API calls

    def filter_titles_with_ai(self, jobs):
        """
        Takes a list of job dicts and returns only the ones that are relevant based on title.
        This is a 'pre-filter' to avoid fetching descriptions for irrelevant jobs.
        """
        if not self.client or not jobs:
            return jobs

        # Prepare the list of titles for the AI
        titles_list = "\n".join([f"{i}. {j['title']} (Source: {j['source']})" for i, j in enumerate(jobs)])
        
        prompt = f"""
Given this candidate's background:
{YOUR_BACKGROUND}

I have a list of job titles from various companies. Please identify ALL jobs that are even SLIGHTLY relevant to my background (IT, Cyber, CS, Tech, Ops, Support, Customer Service, etc.) and exclude ONLY the ones that are totally irrelevant (Medical, Clinical, Nursing, Housekeeping, etc.).

IMPORTANT: Return ALL relevant jobs - do not limit the number. If 50 out of 100 are relevant, return all 50 indices.

List of Jobs:
{titles_list}

Return a JSON object with a single key 'relevant_indices' containing a list of ALL integers (indices) of the jobs that are relevant to this candidate's background.

Example (if jobs 0, 2, 5, 7, 9, 12 are all relevant):
{{
  "relevant_indices": [0, 2, 5, 7, 9, 12]
}}
"""

        try:
            # Rate limiting - wait if needed
            elapsed = time.time() - self.last_call_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a technical recruiter filtering job titles for a CS/Cybersecurity candidate."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"}
            )
            
            self.last_call_time = time.time()
            
            result = json.loads(response.choices[0].message.content)
            indices = result.get("relevant_indices", [])
            
            filtered_jobs = []
            for idx in indices:
                try:
                    # Force to int to avoid crash if AI returns strings
                    idx_int = int(idx)
                    if 0 <= idx_int < len(jobs):
                        filtered_jobs.append(jobs[idx_int])
                except (ValueError, TypeError):
                    continue
            
            return filtered_jobs
        except Exception as e:
            print(f"Error calling Groq API for title filtering: {e}")
            return jobs # Return all if AI filtering fails

    def analyze_job(self, job_title, job_description):
        if not self.client:
            return 0, "GROQ API key missing", "N/A"

        # Rate limiting - wait if needed
        elapsed = time.time() - self.last_call_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

        prompt = f"""
Given this candidate's background:
{YOUR_BACKGROUND}

And this job posting:
Title: {job_title}
Description: {job_description}

Please analyze how well this candidate matches this role.
Provide your response in JSON format with the following keys:
1. match_score: A score from 1-10.
2. missing_skills: A list of 'must-have' skills or certifications the candidate is missing for this specific role.
3. brief_analysis: A 2-3 sentence summary of why this score was given.

Format:
{{
  "match_score": 8,
  "missing_skills": ["Skill A", "Skill B"],
  "brief_analysis": "The candidate has X and Y which are great, but lacks Z."
}}
"""

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a specialized technical recruiter helping a candidate find the best job matches."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",  # Updated from deprecated llama3-8b-8192
                response_format={"type": "json_object"}
            )
            
            self.last_call_time = time.time()
            
            result = json.loads(response.choices[0].message.content)
            return (
                result.get("match_score", 0),
                ", ".join(result.get("missing_skills", [])),
                result.get("brief_analysis", "No analysis provided.")
            )
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            self.last_call_time = time.time()
            return 0, "Error during analysis", str(e)

if __name__ == "__main__":
    # Test with a dummy job
    analyzer = JobAnalyzer()
    score, missing, analysis = analyzer.analyze_job(
        "Junior SOC Analyst", 
        "We need someone with CompTIA Security+ and experience with SIEM tools like Wazuh."
    )
    print(f"Score: {score}")
    print(f"Missing: {missing}")
    print(f"Analysis: {analysis}")
