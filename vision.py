import base64
import json
import os
from io import BytesIO

import openai
from dotenv import load_dotenv
from PIL import Image

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


def get_actions(screenshot, objective, completion_condition, most_recent_action: str | None):
    # raise NotImplementedError("This function is not implemented yet.")
    encoded_screenshot = encode_and_resize(screenshot)
    # if completion condition is not none, then use it other wise use When the page seems satisfactory,
    completion_condition_str = f"When the completion condition ({completion_condition}) seems to be satisfied" if completion_condition else "When the page seems satisfactory, "
    most_recent_action_str = f"the most recent action was: {most_recent_action}" if most_recent_action else ""
    example_click = json.dumps({"click": "A", "description": "click on the A button"})
    example_type_click = json.dumps({"click": "A", "type": "text", "description": "type text in textbox"})
    example_navigation = json.dumps({"navigate": "https://www.example.com", "description": "navigate to example.com"})
    example_done = json.dumps({"done": None})
    prompt = f'''
    Given the image of a website, your objective is: {objective} and the completion condition is: {completion_condition}. You have access to the following schema:
    For navigation: {example_navigation},
    For clicking: {example_click}. The value for clicks is a 1-2 letter sequence found within a yellow box. 
    For typing: {example_type_click}. For text input fields, first click on the input field (described by a 1-2 letter sequence in the yellow box) and then type the text.
    When there are multiple valid options, pick the best one. If the objective is complete, return { example_done }. Remember to only output valid JSON objects. that match the schema. The description field in each example is a simple description of what action is intended to be performed. Do not return the JSON inside a code block. Only return 1 object at a given time.
    '''

    print(f"Prompt: {prompt}")
    response = openai.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
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
                    },
                ],
            },
        ],
        max_tokens=100,
    )

    print(f"Response: {response}")

    try:
        json_response = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        print("Error: Invalid JSON response" + str(response.choices))
        cleaned_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant to fix an invalid JSON response. You need to fix the invalid JSON response to be valid JSON. You must respond in JSON only with no other fluff or bad things will happen. Do not return the JSON inside a code block.",
                },
                {"role": "user", "content": f"The invalid JSON response is: {response.choices[0].message.content}"},
            ],
        )
        try:
            cleaned_json_response = json.loads(cleaned_response.choices[0].message.content)
        except json.JSONDecodeError:
            print("Error: Invalid JSON response" + json.dumps(cleaned_response.choices))
            return {}
        return cleaned_json_response

    return json_response


if __name__ == "__main__":
    image = Image.open("image.png")
    actions = get_actions(image, "upvote the pinterest post")
