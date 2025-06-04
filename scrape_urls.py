import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# Ensure output directories exist
os.makedirs("lists", exist_ok=True)
os.makedirs("listsinvalid", exist_ok=True)
os.makedirs("jsons", exist_ok=True)
os.makedirs("jsonsinvalid", exist_ok=True)

BASE_DOMAIN = "https://www.examtopics.com"

def generate_examtopic_urls_from_ranges(ranges):
    base_url_prefix = f"{BASE_DOMAIN}/discussions/databricks/view/"
    return [f"{base_url_prefix}{i}-ponce" for start, end in ranges for i in range(start, end + 1)]

def extract_exam_name(url):
    """
    Extracts 'exam-[...]' part from redirected ExamTopics URL.
    Example: https://www.examtopics.com/discussions/microsoft/view/67502-exam-az-305-topic-1-question-1-discussion/
    Returns: 'exam-az-305'
    """
    match = re.search(r'/view/\d+-(exam-[a-z0-9-]+)-topic-', url)
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
            return {'original_url': url, 'is_valid': False, 'final_url': None, 'message': f"Status {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {'original_url': url, 'is_valid': False, 'final_url': None, 'message': f"Request failed: {e}"}

if __name__ == "__main__":
    ranges_to_check = [(147800, 147830)]
    urls = generate_examtopic_urls_from_ranges(ranges_to_check)
    print(f"🔍 Checking {len(urls)} URLs from ranges: {ranges_to_check}\n")

    max_workers = 50
    valid_redirects = []
    invalid_urls = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_url_follow_redirects, url): url for url in urls}
        for future in as_completed(futures):
            result = future.result()
            print(f"{result['original_url']} → {'✅' if result['is_valid'] else '❌'} | {result['message']}")

            if result['is_valid'] and result['final_url']:
                valid_redirects.append(result['final_url'])
            else:
                invalid_urls.append(result)

    # Save per-exam files
    saved = {}

    # Write valid redirects into per-exam files
    for redirected_url in valid_redirects:
        exam_name = extract_exam_name(redirected_url)
        if exam_name:
            filename = f"lists/{exam_name}.txt"
            with open(filename, "a") as f:
                f.write(redirected_url + "\n")
            saved.setdefault(exam_name, 0)
            saved[exam_name] += 1
        else:
            print(f"⚠️ Couldn't extract exam name from: {redirected_url}")
            invalid_urls.append(redirected_url)  # Push to invalid list

    # Write failed ones into a general failure log
    failure_filename = "listsinvalid/failures.txt"
    for failed_url in invalid_urls:
        filename = f"listsinvalid/failures.txt"
        with open(filename, "a") as f:
            if isinstance(failed_url, dict):
                f.write(f'{failed_url.get("original_url", "UNKNOWN")} — {failed_url.get("reason", "No reason")}\n')
            else:
                f.write(f'{failed_url}\n')

    import json

    def append_unique_json(filepath, new_items):
        existing_items = set()
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                existing_items = set(json.load(f))

        combined_items = list(existing_items.union(new_items))

        with open(filepath, "w") as f:
            json.dump(combined_items, f, indent=2)

    # Save URLs per exam
    for redirected_url in valid_redirects:
        exam_name = extract_exam_name(redirected_url)
        if exam_name:
            filename = f"jsons/{exam_name}.json"
            append_unique_json(filename, [redirected_url])
            saved.setdefault(exam_name, 0)
            saved[exam_name] += 1
        else:
            invalid_urls.append(redirected_url)

    # Save failures to a shared JSON file
    failure_lines = []
    for failed_url in invalid_urls:
        if isinstance(failed_url, dict):
            failure_lines.append(f'{failed_url.get("original_url", "UNKNOWN")} — {failed_url.get("reason", "No reason")}')
        else:
            failure_lines.append(failed_url)

    append_unique_json("jsonsinvalid/failures.json", failure_lines)



    # Optionally print/save summary of valid ones
    for exam, count in saved.items():
        print(f"✅ Saved {count} entries to {exam}.txt")

    print("\n✅ Saved exam redirects to:")
    for exam, count in saved.items():
        print(f" - {exam}.txt: {count} entries")

    print(f"\n📊 Summary:")
    print(f"Checked: {len(urls)} | Valid: {len(valid_redirects)} | Invalid: {len(invalid_urls)}")
