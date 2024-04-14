import base64
import json
import os
from io import BytesIO

import openai
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam, ChatCompletionMessageToolCall, ChatCompletionMessageToolCallParam
from openai import _types 

from dotenv import load_dotenv
from PIL.Image import Image
from typing import List

from glom import glom
from termcolor import colored

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
IMG_RES = 760


def resize_image(image: Image):
    W, H = image.size
    image = image.resize((IMG_RES, int(IMG_RES * H / W)))
    return image

# Function to encode the image


def encode_and_resize(image: Image):
    W, H = image.size
    image = image.resize((IMG_RES, int(IMG_RES * H / W)))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return encoded_image

def build_action_hint_str(possible_actions_hints: dict[str, str] | None) -> str:
    if not possible_actions_hints:
        return ""
    hint_details = "\n".join(
        [f"{k}: {v}" for k, v in possible_actions_hints.items()])
    
    return f'''
For this screenshot, here are some details for the possible hints in the image. If the next step is to perform an action, then use these to help you determine which action to take.
{hint_details}
'''

def build_function_calls() -> List[ChatCompletionToolParam]:
    click_tool: ChatCompletionToolParam = {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click on a button or link",
            "parameters": {
                "type": "object",
                "properties": {
                    "click": {
                        "type": "string",
                        "description": "The value for clicks is a 1-2 letter sequence found within a yellow box on top left of the item you want to click",
                    },
                    "description": {
                        "type": "string",
                        "description" : "A terse description of what action is intended to be performed"
                    }
                },
                "required": ["click"],
            },
        },
    }

    type_and_click_tool: ChatCompletionToolParam = {
        "type": "function",
        "function": {
            "name": "type_and_click",
            "description": "Type text in a textbox and then click on a button or link",
            "parameters": {
                "type": "object",
                "properties": {
                    "click": {
                        "type": "string",
                        "description": "The value for clicks is a 1-2 letter sequence found within a yellow box on top left of the item you want to click",
                    },
                    "type": {
                        "type": "string",
                        "description": "The text to type in the input textbox",
                    },
                    "description": {
                        "type": "string",
                        "description" : "A terse description of what action is intended to be performed"
                    }
                },
                "required": ["click", "type"],
            },
        },
    }

    navigation_tool: ChatCompletionToolParam = {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Navigate to a different website",
            "parameters": {
                "type": "object",
                "properties": {
                    "navigate": {
                        "type": "string",
                        "description": "The URL to navigate to",
                    },
                    "description": {
                        "type": "string",
                        "description" : "A terse description of what action is intended to be performed"
                    }
                },
                "required": ["navigate"],
            },
        },
    }

    done_tool: ChatCompletionToolParam = {
        "type": "function",
        "function": {
            "name": "done",
            "description": "Indicate that the objective is complete",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    }

    result_tool: ChatCompletionToolParam = {
        "type": "function",
        "function": {
            "name": "result",
            "description": "Return the result of the objective",
            "parameters": {
                "type": "object",
                "properties": {
                    "result": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "The title of the result"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "The description of the result"
                                }
                            },
                            "required": ["title"]
                        }
                    },
                },
                "required": ["result"],
            }
        }
    }

    scroll_tool: ChatCompletionToolParam = {
        "type": "function",
        "function": {
            "name": "scroll",
            "description": "If you think the interesting part of the website is not visible, you can scroll down or up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scroll": {
                        "type": "string",
                        "description": "The direction to scroll in. Allowed values are 'up' or 'down'"
                    },
                    "description": {
                        "type": "string",
                        "description" : "A terse description of what action is intended to be performed"
                    }
                },
                "required": ["scroll"]
            }
        }
    }

    return [
        click_tool,
        type_and_click_tool,
        navigation_tool,
        scroll_tool,
        done_tool,
        result_tool,
    ]

def build_initial_prompt(
    objective: str, 
    completion_condition: str, 
    current_url: str, 
    possible_actions_hints: dict[str, str]):
    example_click = json.dumps(
        {"click": "A", "description": "click on the A button"})
    example_type_click = json.dumps(
        {"click": "A", "type": "text", "description": "type text in textbox"})
    example_navigation = json.dumps(
        {"navigate": "https://www.example.com", "description": "navigate to example.com"})
    example_done = json.dumps({"done": None})
    example_result = json.dumps(
        {"result": [{"title": "some title"}, {"description": "some description"}]})
    example_scroll = json.dumps(
        {"scroll": "down", "description": "scroll down"})
    return f'''
Given the image of a website, your objective is: {objective} and the completion condition is: {completion_condition}. You are currently on the website: {current_url}.
{build_action_hint_str(possible_actions_hints)}
    '''


def build_subsequent_prompt(current_url, possible_actions_hints: dict[str, str]):
    return f'''What should the next action or result be? You are currently on the website: {current_url}.
{build_action_hint_str(possible_actions_hints)}
'''

def map_tool_call_to_param(tool_call: ChatCompletionMessageToolCall) -> ChatCompletionMessageToolCallParam:
    return {
        "id": tool_call.id,
        "function": {
            "arguments": tool_call.function.arguments,
            "name": tool_call.function.name
        },
        "type": "function"
    }


def get_actions(screenshot: Image,
                objective: str, 
                completion_condition: str, 
                current_url: str, 
                possible_actions_hints: dict[str, str], 
                prompt_history: List[str | List[ChatCompletionMessageToolCall]]):
    encoded_screenshot = encode_and_resize(screenshot)
    # if prompt_history is empty
    if not prompt_history:
        next_prompt = build_initial_prompt(
            objective, completion_condition, current_url, possible_actions_hints)
    else:
        next_prompt = build_subsequent_prompt(current_url, possible_actions_hints)

    tools = build_function_calls()

    next_message: ChatCompletionMessageParam = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": next_prompt,
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
            message: ChatCompletionMessageParam
            if isinstance(prompt, str):
                messages.append({
                    "role": "assistant",
                    "content": prompt,
                })
            else:
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": map(map_tool_call_to_param, prompt)
                })
                for tool_call in prompt:
                    messages.append({
                        "role": "tool",
                        "content": "Succeeded",
                        "tool_call_id": tool_call.id
                    })

        messages.append(next_message)

    tool_calls, json_response = query_open_ai_for_json(
        messages, "gpt-4-vision-preview", tools)

    if not prompt_history:
        prompt_history.append(next_prompt)

    prompt_history.append(tool_calls)
    return json_response


def adjust_playbook(playbook, original_objective, incoming_objective):
    prompt = f'''
    This playbook was generated for the following objective {original_objective}.
    The playbook is: {playbook}.
    Adjust the playbook for the new objective: {incoming_objective}.
    You are not allowed to add or remove any new actions to the playbook.
    You may not change any of the keys in the playbook, only the values.
    Return it as a valid JSON array.
    '''
    _, json_response = query_open_ai_for_json([{
        "role": "user",
        "content": prompt,
    }], "gpt-3.5-turbo")

    return json_response


def query_screenshot(screenshot: Image, objective):
    encoded_screenshot = encode_and_resize(screenshot)
    example_result = json.dumps(
        {"result": [{"title": "some title"}, {"description": "some description"}]})
    prompt = f'''
    Given the image of this website, your objective is to: {objective}.
    Return the result in {example_result}. The title and description are strings. Description is optional.
    If you have no results, return null for the result field.
    The result I want from you is a valid JSON object.
    Do not return the JSON inside a code block. Only return 1 object with an array of "result" objects.
    '''
    _, json_response = query_open_ai_for_json([{
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
    }], "gpt-4-vision-preview")

    if ("result" in json_response and not json_response["result"]) \
            or ("message" in json_response):
        # save screenshot
        screenshot.save("screenshot.png")

    return json_response


def query_open_ai_for_json(messages: List[ChatCompletionMessageParam], model, tools: List[ChatCompletionToolParam] | _types.NotGiven = _types.NotGiven(), max_tokens=130) -> tuple[List[ChatCompletionMessageToolCall], dict]:
    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        max_tokens=max_tokens,
    )

    print(f"Response: {response}")
    
    tool_calls = glom(response, "choices.0.message.tool_calls", default=None)
    value: ChatCompletionMessageToolCall | None  = glom(response, "choices.0.message.tool_calls.0", default=None)
    if value == None:
        print("No tool calls found in response")
        raise Exception("No tool calls found in response")
    
    function = value.function
    if function == None:
        print("No function found in tool call")
        raise Exception("No function found in tool call")
    

    try:
        json_response = json.loads(function.arguments)
    except json.JSONDecodeError:
        print("Error: Invalid JSON response" + str(response.choices))
        raise Exception("Error: Invalid JSON response" + str(response.choices))

    return tool_calls, json_response

def pretty_print_conversation(messages: List[ChatCompletionMessageParam]):
    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
    }
    
    for message in messages:
        if message["role"] == "system":
            print(colored(f"system: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "user":
            print(colored(f"user: {list(filter(lambda content: True if isinstance(content, str) else content["type"] != 'image_url', message["content"]))}\n", role_to_color[message["role"]]))
        elif message["role"] == "assistant" and message.get("tool_calls"):
            print(colored(f"assistant: {glom(message, 'tool_calls')}\n", role_to_color[message["role"]]))
        elif message["role"] == "assistant" and not message.get("tool_calls"):
            print(colored(f"assistant: {glom(message, 'content')}\n", role_to_color[message["role"]]))
        elif message["role"] == "function":
            print(colored(f"function ({message['name']}): {message['content']}\n", role_to_color[message["role"]]))