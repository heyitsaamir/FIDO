import base64
import json
import os
from io import BytesIO

import openai
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionAssistantMessageParam
from dotenv import load_dotenv
from PIL import Image
from typing import List

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
IMG_RES = 1080


# Function to encode the image
def encode_and_resize(image):
    W, H = image.size
    image = image.resize((IMG_RES, int(IMG_RES * H / W)))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return encoded_image

def build_initial_prompt(objective, completion_condition):
    example_click = json.dumps({"click": "A", "description": "click on the A button"})
    example_type_click = json.dumps({"click": "A", "type": "text", "description": "type text in textbox"})
    example_navigation = json.dumps({"navigate": "https://www.example.com", "description": "navigate to example.com"})
    example_done = json.dumps({"done": None})
    example_result = json.dumps({"result": [{"title": "some title"}, {"description": "some description"}]})
    example_scroll = json.dumps({"scroll": "down", "description": "scroll down"})
    return f'''
    Given the image of a website, your objective is: {objective} and the completion condition is: {completion_condition}. You have access to the following schema:
    For navigation: {example_navigation}.
    For clicking: {example_click}. The value for clicks is a 1-2 letter sequence found within a yellow box. 
    For typing: {example_type_click}. For text input fields, first click on the input field (described by a 1-2 letter sequence in the yellow box) and then type the text.
    If you think the interesting part of the website is not visible, you can scroll down or up. For scrolling: {example_scroll}.
    For results: {example_result}. The title and description are strings. Description is optional.
    When there are multiple valid options, pick the best one. If the objective is complete, return { example_done } if the original objective was an action or return { example_result } if the original objective was a query. Remember to only output valid JSON objects. that match the schema. The description field in each example is a simple description of what action is intended to be performed. 
    The result I want from you is a valid JSON object.
    Do not return the JSON inside a code block. Only return 1 object at a given time.
    '''

def build_subsequent_prompt():
    return f'What should the next action be?'

def get_actions(screenshot, objective, completion_condition, prompt_history: List[str]):
    encoded_screenshot = encode_and_resize(screenshot)
    # if prompt_history is empty
    if not prompt_history:
        prompt = build_initial_prompt(objective, completion_condition)
    else:
        prompt = build_subsequent_prompt()

    next_message: ChatCompletionMessageParam = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": prompt,
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded_screenshot}",
                },
            }
        ],          
    }

    messages: List[ChatCompletionMessageParam] = []
    if not prompt_history:
        messages.append(next_message)
    else:
        messages = []
        for prompt in prompt_history:
            message: ChatCompletionAssistantMessageParam = {
                "role": "assistant",
                "content": prompt,
            }
            messages.append(message)
        messages.append(next_message)

    print(f"Prompt: {prompt}")
    response = openai.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=messages,
        max_tokens=100,
    )

    print(f"Response: {response}")

    try:
        json_response = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        print("Error: Invalid JSON response" + str(response.choices))
        json_response = fix_response(response.choices[0].message.content)

    if not prompt_history:
        prompt_history.append(prompt)

    prompt_history.append(response.choices[0].message.content)
    return json_response

def fix_response(badResponse):
    cleaned_response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant to fix an invalid JSON response. You need to fix the invalid JSON response to be valid JSON. You must respond in JSON only with no other fluff or bad things will happen. Do not return the JSON inside a code block.",
            },
            {"role": "user", "content": f"The invalid JSON response is: {badResponse}"},
        ],
    )
    try:
        cleaned_json_response = json.loads(cleaned_response.choices[0].message.content)
    except json.JSONDecodeError:
        print("Error: Invalid JSON response" + json.dumps(cleaned_response.choices))
        return {}
    return cleaned_json_response

if __name__ == "__main__":
    image = Image.open("image.png")
    actions = get_actions(image, "upvote the pinterest post")
