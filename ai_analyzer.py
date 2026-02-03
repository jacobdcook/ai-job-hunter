import os
import json
import re
import time
from groq import Groq, RateLimitError
from dotenv import load_dotenv

# Try to import config, but handle missing config.py gracefully
try:
    from config import YOUR_BACKGROUND
except ImportError:
    YOUR_BACKGROUND = "Configuration not yet set. Run setup wizard first."

load_dotenv()


def _load_groq_keys():
    """Load all Groq API keys from .env and optional keys file. Returns list of keys (no duplicates)."""
    seen = set()
    keys = []

    # 1) GROQ_API_KEYS (comma or newline separated)
    keys_str = os.getenv("GROQ_API_KEYS", "").strip()
    if keys_str:
        for part in keys_str.replace("\n", ",").split(","):
            k = part.strip()
            if k and k not in seen:
                seen.add(k)
                keys.append(k)

    # 2) Numbered: GROQ_API_KEY_1, GROQ_API_KEY_2, ... (up to 50)
    for i in range(1, 51):
        k = os.getenv(f"GROQ_API_KEY_{i}", "").strip()
        if k and k not in seen:
            seen.add(k)
            keys.append(k)

    # 3) Single GROQ_API_KEY
    single = os.getenv("GROQ_API_KEY", "").strip()
    if single and single not in seen:
        seen.add(single)
        keys.append(single)

    # 4) Optional file: GROQ_KEYS_FILE or groq_keys.txt next to this script (one key per line)
    keys_file = os.getenv("GROQ_KEYS_FILE", "").strip()
    if not keys_file:
        _dir = os.path.dirname(os.path.abspath(__file__))
        keys_file = os.path.join(_dir, "groq_keys.txt")
    if keys_file and os.path.isfile(keys_file):
        try:
            with open(keys_file, "r") as f:
                for line in f:
                    k = line.strip()
                    if k and not k.startswith("#") and k not in seen:
                        seen.add(k)
                        keys.append(k)
        except OSError:
            pass

    return keys


class JobAnalyzer:
    def __init__(self):
        self.api_keys = _load_groq_keys()

        # Model: primary + optional fallbacks (each model has its own TPD quota on Groq)
        self.default_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip() or "llama-3.1-8b-instant"
        fallback_str = os.getenv("GROQ_MODEL_FALLBACK", "").strip()
        self.fallback_models = [m.strip() for m in fallback_str.split(",") if m.strip()] if fallback_str else []

        if not self.api_keys:
            print("Warning: No GROQ API keys found. Set GROQ_API_KEYS or GROQ_API_KEY in .env, or put keys in groq_keys.txt (one per line).")
            self.client = None
        else:
            print(f"Using {len(self.api_keys)} Groq API key(s)" + (" (will rotate on rate limit)." if len(self.api_keys) > 1 else "."))
            print(f"Model: {self.default_model}" + (f" (fallbacks: {', '.join(self.fallback_models)})" if self.fallback_models else ""))
            self.current_key_idx = 0
            self.client = Groq(api_key=self.api_keys[0])

        self.last_call_time = 0
        self.rate_limit_delay = 2  # seconds between API calls
        self.max_retries = 3  # max full rotation cycles before giving up

    def _rotate_key(self):
        """Switch to the next API key. Returns True if wrapped around to start."""
        if len(self.api_keys) <= 1:
            return True  # only one key, always "wrapped"
        next_idx = (self.current_key_idx + 1) % len(self.api_keys)
        wrapped = next_idx == 0
        self.current_key_idx = next_idx
        self.client = Groq(api_key=self.api_keys[next_idx])
        return wrapped

    def _parse_retry_after(self, error_msg):
        """Extract wait time from Groq rate limit error message."""
        match = re.search(r'try again in (\d+\.?\d*)s', str(error_msg), re.IGNORECASE)
        if match:
            return int(float(match.group(1))) + 2  # add 2s buffer
        return 60  # default wait

    def _call_api(self, messages, model=None, response_format=None):
        """
        Call Groq API with automatic key rotation and optional model fallback.
        - Primary model from GROQ_MODEL (default llama-3.1-8b-instant).
        - On rate limit (429): tries fallback models from GROQ_MODEL_FALLBACK (each has its own TPD quota).
        - When all models limited: rotates to next key, then retries; waits if all keys limited.
        """
        if not self.client:
            raise RuntimeError("No Groq API keys configured")

        use_model = model or self.default_model
        models_to_try = [use_model] + [m for m in self.fallback_models if m != use_model]

        elapsed = time.time() - self.last_call_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)

        full_rotations = 0
        last_error = None

        while full_rotations < self.max_retries:
            for try_model in models_to_try:
                try:
                    kwargs = {"messages": messages, "model": try_model}
                    if response_format:
                        kwargs["response_format"] = response_format

                    response = self.client.chat.completions.create(**kwargs)
                    self.last_call_time = time.time()
                    return response

                except RateLimitError as e:
                    last_error = e
                    if try_model != models_to_try[-1]:
                        print(f"\n  [Rate limited on {try_model}] Trying fallback model...", flush=True)
                    else:
                        break

            # All models rate limited for current key
            key_label = f"...{self.api_keys[self.current_key_idx][-6:]}"
            print(f"\n  [Rate limited on key {key_label}]", end=" ", flush=True)

            wrapped = self._rotate_key()

            if wrapped:
                full_rotations += 1
                if full_rotations < self.max_retries:
                    retry_after = self._parse_retry_after(last_error or "")
                    if len(self.api_keys) > 1:
                        print(f"All {len(self.api_keys)} keys hit limit.", end=" ", flush=True)
                    print(f"Waiting {retry_after}s before retry ({full_rotations}/{self.max_retries})...", flush=True)
                    time.sleep(retry_after)
                    print(f"  Retrying...", flush=True)
                else:
                    print(f"All retries exhausted after {self.max_retries} cycles.", flush=True)
                    raise last_error or RuntimeError("Rate limit exceeded")
            else:
                new_label = f"...{self.api_keys[self.current_key_idx][-6:]}"
                print(f"Switching to key {new_label}", flush=True)

        raise last_error or RuntimeError("Max retries exceeded for Groq API")

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
            response = self._call_api(
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
                model=self.default_model,
                response_format={"type": "json_object"}
            )

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
            response = self._call_api(
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
                model=self.default_model,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            raw_score = result.get("match_score", 0)
            # Clamp to 1-10; if model returns percentage (e.g. 60), treat as 6/10
            try:
                score_val = float(raw_score) if raw_score is not None else 0
                if score_val > 10 and score_val <= 100:
                    score_val = round(score_val / 10)  # 60 -> 6
                score_val = max(1, min(10, int(round(score_val))))
            except (TypeError, ValueError):
                score_val = 0
            # missing_skills: API may return list of strings or list of dicts; normalize to strings
            raw_missing = result.get("missing_skills", [])
            if isinstance(raw_missing, str):
                missing_list = [raw_missing] if raw_missing else []
            else:
                missing_list = [str(x) if isinstance(x, str) else (x.get("skill", x.get("name", str(x))) if isinstance(x, dict) else str(x)) for x in (raw_missing or [])]
            missing_str = ", ".join(missing_list)
            return (
                score_val,
                missing_str,
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
