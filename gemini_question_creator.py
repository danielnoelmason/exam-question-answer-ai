from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
api_model = "gemini-2.0-flash"
json_input_file="exam-az-900"
import requests

def fetch_html(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch {url}: {e}")
        return None

from bs4 import BeautifulSoup
import mimetypes

from bs4 import BeautifulSoup
import requests
import mimetypes
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import mimetypes

def parse_exam_page(html, base_url):
    soup = BeautifulSoup(html, "html.parser")

    # 1. Extract full question content from the "question-body" div
    question_div = soup.find("div", class_="question-body")
    image_data = []
    question_text = ""

    if question_div:
        # Clone the div so we can safely mutate it
        cloned_div = BeautifulSoup(str(question_div), "html.parser")
        
        # Handle any <img> elements: download, and replace with markdown-style links
        for img in cloned_div.find_all("img"):
            img_src = img.get("src")
            if img_src:
                full_img_url = urljoin(base_url, img_src)
                try:
                    img_response = requests.get(full_img_url)
                    img_response.raise_for_status()
                    mime_type = img_response.headers.get("Content-Type") or mimetypes.guess_type(full_img_url)[0]
                    image_data.append({
                        "url": full_img_url,
                        "bytes": img_response.content,
                        "mime_type": mime_type
                    })
                    # Replace the image tag with a markdown image tag in the HTML
                    img.replace_with(f"\n![Image]({full_img_url})\n")
                except requests.RequestException as e:
                    print(f"Failed to fetch image: {full_img_url}\nError: {e}")
        
        # Get clean text, preserving newlines from <br> tags
        for br in cloned_div.find_all("br"):
            br.replace_with("\n")

        question_text = cloned_div.get_text(separator="\n", strip=True)

    # 2. Extract discussion content from the ".discussion-container"
    discussion_elem = soup.select_one("div.discussion-container")
    discussion_text = discussion_elem.get_text(separator="\n", strip=True) if discussion_elem else ""

    return question_text, discussion_text, image_data

from google import genai

client = genai.Client(api_key=api_key)  # assumes GEMINI_API_KEY is in env vars
from prompts.prompt_manager import PromptManager
prompt_manager = PromptManager()

def generate_question_answer(url, text, discussion, images):

    prompt_template = prompt_manager.get("standard")
    prompt = prompt_template.format(url=url, text=text, discussion=discussion)
    try:
        response = client.models.generate_content(
            model=api_model,
            contents=prompt,
        )
        print("\n\n******** PROMPT + EXTRACTION START ********\n"+prompt+"\n******** PROMPT + EXTRACTION END ********\n\n")
        print("\n\n******** LLM RESPONSE START ********\n" + response.text + "\n******** LLM RESPONSE END ********\n\n")
        answer = response.text

        if "QUESTION:" in answer and "ANSWER:" in answer:
            parts = answer.split("ANSWER:")
            question = parts[0].replace("QUESTION:", "").strip()
            answer_text = parts[1].strip()
            return {"QUESTION": question, "ANSWER": answer_text}
        else:
            return {"QUESTION": prompt, "ANSWER": f"[Parsing error] Full response:\n{answer}"}
    except Exception as e:
        print(f"[ERROR] LLM request failed: {e}")
        return {"QUESTION": "", "ANSWER": "[LLM error]"}


import pandas as pd

def save_to_csv(data, filename=f'Practice Questions - {json_input_file}.csv'):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"[INFO] Saved {len(data)} entries to {filename}")


import time
def read_urls_from_file(file_path):
    with open(file_path, "r") as file:
        return [line.strip() for line in file if line.strip()]

import json
def read_urls_from_json(file_path):
    """Read list of URLs from a JSON file."""
    with open(file_path, "r") as file:
        return json.load(file)

def main():
    load_dotenv()
    url_file = f"jsons/{json_input_file}.json"
    urls = read_urls_from_json(url_file)

    qa_list = []

    total_urls = len(urls)
    for index, url in enumerate(urls, start=1):
        print(f"[INFO] Processing: {url} ({index}/{total_urls})")
        html = fetch_html(url)
        if not html:
            continue

        base_url = '/'.join(url.split('/')[:3])
        question, discussion, images = parse_exam_page(html, base_url)

        qa_pair = generate_question_answer(url, question, discussion, images)
        qa_list.append(qa_pair)

        time.sleep(2.5)  # Be respectful to servers

    save_to_csv(qa_list)



if __name__ == "__main__":
    main()
    
