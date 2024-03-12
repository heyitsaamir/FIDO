import argparse
import time
import os

import vision
from vimbot import Vimbot

from flask import Flask, request
from typing import Literal, Union, List
from PIL import Image
import json


def main(website: Union[Literal['todoist'], Literal['google']], objective: str, completion_condition: str = "When the objective seems complete"):
    print("Initializing the Vimbot driver...")

    init_functions = {
        'todoist': initTodoist,
        'google': initGoogle
    }

    # Call the appropriate function
    if website in init_functions:
        driver = init_functions[website]()
    else:
        driver = initNoWebsite()

    input("Press Enter to continue...")
    history: List[str] = []
    playbook_steps = []
    result = None
    while True:
        time.sleep(1)
        print("Capturing the screen...")
        screenshot = driver.capture()
        print("Getting actions for the given objective...")
        current_url = driver.get_current_url()
        action = vision.get_actions(screenshot, objective, completion_condition, current_url, history)
        focused_element = driver.focus(action)
        print(f"Focused element: {focused_element}")
        if focused_element:
            history_item = action.copy()
            history_item['clicked_element'] = focused_element
            playbook_steps.append(history_item)
        else:
            playbook_steps.append(action)
        perform_action_result = driver.perform_action(action)
        input("Press Enter to continue...")
        if perform_action_result:
            result = perform_action_result
            break
    print(history, playbook_steps)
    with open("playbook.json", "w") as f:
        json.dump(playbook_steps, f)
    return result

# Opens todoist and performs login
def initTodoistFresh(): 
    driver = Vimbot()
    driver.navigate("https://app.todoist.com/auth/login")
    driver.page.type('input[type="email"]', os.getenv("TODOIST_USER")) # type: ignore
    driver.page.type('input[type="password"]', os.getenv("TODOIST_PASSWORD")) # type: ignore
    driver.page.click('button[type="submit"]')
    driver.page.wait_for_selector('button[aria-controls="sidebar"]')
    return driver

def initTodoist(): 
    driver = Vimbot()
    driver.navigate("https://app.todoist.com")
    driver.page.wait_for_selector('button[aria-controls="sidebar"]')
    driver.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    return driver

def initNoWebsite(): 
    driver = Vimbot()
    return driver


def initGoogle():
    driver = Vimbot()
    driver.navigate("https://www.google.com")
    return driver


app = Flask(__name__)

@app.route("/ping", methods=["POST"])
def ping():
    # dummy function to test the Flask server
    print("Received request to ping the Vimbot")
    # return some dummy response as json
    return {"status": "success"}

@app.route("/run", methods=["POST"])
def run():
    data = request.get_json()
    prompt = data.get("prompt")
    completion_condition = data.get("completion_condition")
    # website = data.get("website")

    print(f"Received request to run the Vimbot with prompt: {prompt} and completion_condition: {completion_condition}")
    result = main("google", prompt, completion_condition)
    # if result is a json, return it as is, otherwise return it as a string
    if isinstance(result, dict):
        return result
    else:
        return {"result": result}

def classicMode():
    # The classic mode of the Vimbot
    print("Starting the Vimbot in classic mode...")
    objective = input("Please enter your objective: ")
    result = main("todoist", objective)
    if isinstance(result, dict):
        return result
    else:
        return {"result": result}
    
def replay_history():
    # replay the history
    with open("playbook.json", "r") as f:
        playbook_steps = json.load(f)
    driver = initTodoist()
    for action in playbook_steps:
        driver.perform_action(action)


if __name__ == "__main__":
    # if classic mode is supplied, then run classicMode otherwise run the server
    parser = argparse.ArgumentParser()
    parser.add_argument("--classic", action="store_true")
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    if args.classic:
        classicMode()
    elif args.replay:
        replay_history()
    else:
        print("Starting the Flask server...")
        app.run(host="0.0.0.0", port=8000)