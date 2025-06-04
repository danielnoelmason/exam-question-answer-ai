import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def generate_examtopic_urls_from_ranges(ranges):
    base_url_part1 = "https://www.examtopics.com/discussions/databricks/view/"
    base_url_part2 = "-exam-certified-generative-ai-engineer-associate-topic-1/"
    urls = []

    for start, end in ranges:
        urls += [f"{base_url_part1}{i}{base_url_part2}" for i in range(start, end + 1)]
    
    return urls

def check_url_validity(url, timeout_seconds=10):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        response = requests.get(url, headers=headers, timeout=timeout_seconds, allow_redirects=False)

        if response.status_code == 200:
            return url, True, f"Status: {response.status_code} (OK)"
        elif 300 <= response.status_code < 400:
            return url, False, f"Redirect detected (Status: {response.status_code}, Location: {response.headers.get('Location')})"
        else:
            return url, False, f"Status: {response.status_code}"

    except requests.exceptions.Timeout:
        return url, False, "Error: Request timed out"
    except requests.exceptions.ConnectionError:
        return url, False, "Error: Connection refused or DNS failure"
    except requests.exceptions.RequestException as e:
        return url, False, f"Error: {str(e)}"

if __name__ == "__main__":
    # --- Define the ranges to check ---
    # ranges_to_check = [
    #     (148594, 155675),
    #     (270000, 273000),
    #     (303000, 303400)
    # ]
    ranges_to_check = [
        (148594-1000, 148594-1),
        (155675+1, 155675+1000),
        (270000-1000, 270000-1),
        (273000+1, 273000+1000),
        (303000-1000, 303000-1),
        (303400+1, 303400+1000)
    ] 
    # ABOVE RESULTED IN: 302723 AND 304026

    ranges_to_check = [
        (303000-10000, 303000-1001),
        (303400+1001, 303400+10000)
    ]
    # RESULTED IN NONE - 400 and 503s

    ranges_to_check = [
        (270000-5000, 270000-1001),
        (273000+1001, 273000+5000)
    ]
    # RESULTED IN NONE - 503 tho

    max_workers = 50
    timeout = 10

    # --- Generate URLs ---
    urls = generate_examtopic_urls_from_ranges(ranges_to_check)
    print(f"Checking {len(urls)} URLs from ranges: {ranges_to_check}\n")

    valid_urls = []
    invalid_urls = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(check_url_validity, url, timeout): url for url in urls}
        
        for future in as_completed(future_to_url):
            url, is_valid, message = future.result()
            print(f"{url} -> {'VALID' if is_valid else 'INVALID'} | {message}")
            if is_valid:
                valid_urls.append(url)
            else:
                invalid_urls.append({"url": url, "reason": message})

    # --- Save results ---
    if valid_urls:
        with open(f"{base_url_part2}.txt", "a") as f:  # Append mode
            for url in valid_urls:
                f.write(url + "\n")
        print(f"\n✅ Appended {len(valid_urls)} valid URLs to 'valid_examtopic_urls.txt'")


    print(f"\nTotal checked: {len(urls)}")
    print(f"Valid: {len(valid_urls)} | Invalid: {len(invalid_urls)}")
