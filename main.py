import argparse
import time
import os

import vision
from embedding import get_embedding, recommendations_from_strings
from vimbot import Vimbot

from flask import Flask, request
from typing import Literal, Union, List
import json

from dotenv import load_dotenv

load_dotenv()
is_playbook_recording_enabled = os.getenv("PWDEBUG", "0") == "1"

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
        addPlaybookStep(driver, action, playbook_steps)
        perform_action_result = driver.perform_action(action)
        if perform_action_result:
            result = perform_action_result
            break
    savePlaybook(playbook_steps, objective)
    return result

def addPlaybookStep(driver, action, playbook_steps):
    if is_playbook_recording_enabled:
        focused_element = driver.focus(action)
        if focused_element:
            history_item = action.copy()
            history_item['clicked_element'] = focused_element
            playbook_steps.append(history_item)
        else:
            playbook_steps.append(action)

def savePlaybook(playbook_steps, objective):
    playbookFileName = "playbook_" + str(int(time.time())) + ".json"
    with open(playbookFileName, "w") as f:
        json.dump(playbook_steps, f)
    playbook_record = "playbook_record.json"
    # get the playbook record if it exists
    if os.path.exists(playbook_record):
        with open(playbook_record, "r") as f:
            playbook_records = json.load(f)
    else:
        playbook_records = []
    embedding = get_embedding(objective)
    playbook_records.append({
        "objective": objective,
        "playbookFile": playbookFileName,
        "embedding": embedding,
    })
    with open(playbook_record, "w") as f:
        json.dump(playbook_records, f)

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
    completion_condition = input("Please enter your the completion condition: ")
    result = main("todoist", objective, completion_condition)
    if isinstance(result, dict):
        return result
    else:
        return {"result": result}
    
def replay_history():
    # replay the history
    objective = input("Please enter your objective: ")
    playbook = get_play_book(objective)
    if not playbook:
        print("No playbook found for the given objective")
        return
    with open(playbook['playbookFile'], "r") as f:
        playbook_record = json.load(f)
    adjusted_playbook = vision.adjust_playbook(playbook_record, playbook['objective'], objective)
    driver = initTodoist()
    for action in adjusted_playbook:
        driver.perform_action(action)
        
def get_play_book(objective):
    # get the playbooks
    with open("playbook_record.json", "r") as f:
        playbook_records = json.load(f)
    # return playbook_records[0]
    playbookIndex = recommendations_from_strings(list(map(lambda x: x["embedding"], playbook_records)), objective)
    if playbookIndex is not None:
        return playbook_records[playbookIndex]
    return None


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