from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

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

def parse_exam_page(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Extract main question from the first <p class="card-text">
    question_elem = soup.find("p", class_="card-text")
    question_text = question_elem.get_text(separator="\n", strip=True) if question_elem else ""

    # 2. Extract image from inside the question block, if any
    image_data = []
    if question_elem:
        for img in question_elem.find_all("img"):
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
                except requests.RequestException as e:
                    print(f"Failed to fetch image: {full_img_url}\nError: {e}")
    
    # 3. Extract discussion content from the ".discussion-container"
    discussion_elem = soup.select_one("div.discussion-container")
    discussion_text = discussion_elem.get_text(separator="\n", strip=True) if discussion_elem else ""

    # 4. Combine everything into a single text blob for the LLM
    full_text = (
        "MAIN QUESTION:\n" + question_text + "\n\n" +
        "COMMUNITY DISCUSSION:\n" + discussion_text
    )

    return full_text, image_data


import openai

openai.api_key = api_key

import openai

client = openai.OpenAI()  # assumes OPENAI_API_KEY is in env vars

def generate_question_answer(text, images):
    # Construct markdown-like image references
    image_notes = "\n".join([f"![Image]({img['url']})" for img in images])

    prompt = f"""
You are an expert exam tutor. Based ONLY on the content below, generate a single insightful QUESTION and a clear, concise ANSWER. If images are relevant, include their text extraction or reference using markdown image links or describe them.

CONTENT:
{text}

{image_notes}

FORMAT:
QUESTION: ...
ANSWER: ...
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-4-turbo"
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )

        answer = response.choices[0].message.content
        if "QUESTION:" in answer and "ANSWER:" in answer:
            parts = answer.split("ANSWER:")
            question = parts[0].replace("QUESTION:", "").strip()
            answer = parts[1].strip()
            return {"QUESTION": question, "ANSWER": answer}
        else:
            return {"QUESTION": "", "ANSWER": f"[Parsing error] Full response:\n{answer}"}
    except Exception as e:
        print(f"[ERROR] LLM request failed: {e}")
        return {"QUESTION": "", "ANSWER": "[LLM error]"}


import pandas as pd

def save_to_csv(data, filename='exam_q_and_a.csv'):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"[INFO] Saved {len(data)} entries to {filename}")


import time

def main():
    load_dotenv()
    urls = [
        "https://www.examtopics.com/discussions/microsoft/view/38544-exam-ai-900-topic-1-question-26-discussion/",
        # Add more URLs here
    ]

    qa_list = []

    for url in urls:
        print(f"[INFO] Processing: {url}")
        html = fetch_html(url)
        if not html:
            continue

        base_url = '/'.join(url.split('/')[:3])
        text, images = parse_exam_page(html, base_url)

        qa_pair = generate_question_answer(text, images)
        qa_list.append(qa_pair)

        time.sleep(5)  # Be respectful to servers

    save_to_csv(qa_list)

if __name__ == "__main__":
    main()
    
