import os
import re
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---- Setup ----
BASE_DOMAIN = "https://www.examtopics.com"
os.makedirs("jsons", exist_ok=True)
os.makedirs("jsonsinvalid", exist_ok=True)

# ---- Utils ----
def normalize_url(line):
    """Extract URL from strings like '<url> — reason' or keep line if clean."""
    if '—' in line:
        return line.split('—')[0].strip()
    return line.strip()

def extract_exam_name(url):
    """
    Extracts the core 'exam-[...]' portion from ExamTopics URLs,
    excluding any trailing '-topic-...' or '-question-...' parts.
    """
    match = re.search(r'/view/\d+-(exam-[a-z0-9-]+?)(?:-topic-|-question-|/|$)', url)
    return match.group(1) if match else None



def check_url_follow_redirects(url, timeout_seconds=10):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=timeout_seconds, allow_redirects=True)
        final_url = response.url

        if response.status_code == 200 and final_url != url:
            return {'original_url': url, 'is_valid': True, 'final_url': final_url, 'message': f"Redirected to {final_url}"}
        elif response.status_code == 200:
            return {'original_url': url, 'is_valid': True, 'final_url': final_url, 'message': "200 OK (no redirect)"}
        else:
            return {'original_url': url, 'is_valid': False, 'message': f"Status {response.status_code}"}
    except requests.RequestException as e:
        return {'original_url': url, 'is_valid': False, 'message': f"Request failed: {e}"}

def append_unique_json(filepath, new_items):
    """Append only unique items to a JSON file."""
    existing = set()
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            try:
                existing = set(json.load(f))
            except json.JSONDecodeError:
                pass
    combined = list(existing.union(new_items))
    with open(filepath, 'w') as f:
        json.dump(sorted(combined), f, indent=2)

# ---- Main Processing ----
def main():
    # Load and clean failed URLs
    with open("jsonsinvalid/failures.json", "r") as f:
        raw_lines = json.load(f)
    all_urls = {normalize_url(line) for line in raw_lines if line.startswith("http")}

    print(f"🔁 Retrying {len(all_urls)} failed URLs...\n")
    valid_redirects = []
    failed_entries = []

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_url_follow_redirects, url): url for url in all_urls}
        for future in as_completed(futures):
            result = future.result()
            url = result['original_url']
            print(f"{url} → {'✅' if result['is_valid'] else '❌'} | {result['message']}")
            if result['is_valid']:
                valid_redirects.append(result['final_url'])
            else:
                failed_entries.append(f"{url} — {result['message']}")

    # Write successful URLs to JSON per exam
    successes_by_exam = {}
    for url in valid_redirects:
        exam = extract_exam_name(url)
        if exam:
            successes_by_exam.setdefault(exam, []).append(url)
        else:
            failed_entries.append(f"{url} — Could not extract exam name")

    for exam, urls in successes_by_exam.items():
        filepath = f"jsons/{exam}.json"
        append_unique_json(filepath, urls)
        print(f"✅ {len(urls)} valid URLs saved to {filepath}")

    # Load old failures
    with open("jsonsinvalid/failures.json", "r") as f:
        original_failures = set(normalize_url(line) for line in json.load(f) if line.startswith("http"))

    # Remove successfully resolved URLs
    remaining_failures = original_failures - set(valid_redirects)

    # Add newly failed entries to the remaining list
    for line in failed_entries:
        url = normalize_url(line)
        remaining_failures.add(f"{url} — {line.split('—')[-1].strip()}")

    # Write back the cleaned failure list
    with open("jsonsinvalid/failures.json", "w") as f:
        json.dump(sorted(remaining_failures), f, indent=2)


    print(f"\n✅ Done. {len(valid_redirects)} valid | {len(failed_entries)} still failed.")

if __name__ == "__main__":
    main()
