import argparse
import time
import os

import perception
from embedding import get_embedding, recommendations_from_strings
from browserAgent import BrowserAgent

from flask import Flask, request
from typing import Literal, Union, List
import json

from dotenv import load_dotenv

load_dotenv()
is_playbook_recording_enabled = os.getenv("PWDEBUG", "0") == "1"


def do_image_reasoning_work(website: Union[Literal['todoist'], str], objective: str, completion_condition: str = "When the objective seems complete"):
    driver = get_driver(website)
    # input("Press Enter to continue...")
    history: List[str] = []
    playbook_steps = []
    result = None
    while True:
        time.sleep(1)
        print("Capturing the screen...")
        screenshot = driver.capture()
        action_hints = driver.get_x_paths_for_all_hints()
        print("Getting actions for the given objective...")
        current_url = driver.get_current_url()
        action = perception.get_actions(
            screenshot, objective, completion_condition, current_url, action_hints, history)
        addPlaybookStep(driver, action, playbook_steps)
        perform_action_result = driver.perform_action(action)
        if perform_action_result:
            result = perform_action_result
            break
    savePlaybook(playbook_steps, objective)
    close_driver(driver)
    return result


def replay_history(website: Union[Literal['todoist'], Literal['google']], objective: str, completion_condition):
    playbook = get_playbook(objective)
    if not playbook:
        return do_image_reasoning_work(website, objective, completion_condition)
    with open(playbook['playbookFile'], "r") as f:
        playbook_record = json.load(f)
    adjusted_playbook = perception.adjust_playbook(
        playbook_record, playbook['objective'], objective)
    driver = get_driver(website)
    result = None
    print("Adjusted playbook: ", adjusted_playbook)
    for action in adjusted_playbook:
        if "result" in action:
            # wait for the page to be visible before taking a screenshot
            time.sleep(1)
            screenshot = driver.capture(False)
            action = perception.query_screenshot(
                screenshot=screenshot, objective=objective)
        result = driver.perform_action(action)
    close_driver(driver)
    return result


def addPlaybookStep(driver, action, playbook_steps):
    if is_playbook_recording_enabled:
        selector = driver.get_selector(action)
        if selector:
            history_item = action.copy()
            history_item['clicked_element'] = selector
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


def get_playbook(objective):
    # get the playbooks
    with open("playbook_record.json", "r") as f:
        playbook_records = json.load(f)
    # return playbook_records[0]
    playbookIndex = recommendations_from_strings(
        list(map(lambda x: x["embedding"], playbook_records)), objective)
    if playbookIndex is not None:
        return playbook_records[playbookIndex]
    return None


def reset_playbook():
    # if there is no playbook_record.json, then return
    # if there is one, then reset it to an empty array
    if os.path.exists("playbook_record.json"):
        with open("playbook_record.json", "w") as f:
            json.dump([], f)


def get_driver(website: Union[Literal['todoist'], str]):
    print("Initializing the Vimbot driver...")

    init_functions = {
        'todoist': initTodoist,
    }

    # Call the appropriate function
    if website in init_functions:
        driver = init_functions[website]()
    # if website contains http, then it is a custom website and we should start iwth that
    elif "http" in website:
        driver = initCustomWebsite(website)
    else:
        driver = initNoWebsite()
    return driver


def close_driver(driver: BrowserAgent):
    print("Closing the Vimbot driver...")
    time.sleep(2)  # todoist needs a little time to save the changes
    driver.close()

# Opens todoist and performs login


def initTodoistFresh():
    driver = BrowserAgent()
    driver.navigate("https://app.todoist.com/auth/login")
    driver.page.type('input[type="email"]', os.getenv(
        "TODOIST_USER"))  # type: ignore
    driver.page.type('input[type="password"]', os.getenv(
        "TODOIST_PASSWORD"))  # type: ignore
    driver.page.click('button[type="submit"]')
    driver.page.wait_for_selector('button[aria-controls="sidebar"]')
    return driver


def initTodoist():
    driver = BrowserAgent()
    driver.navigate("https://app.todoist.com")
    driver.page.wait_for_selector('header')
    driver.page.wait_for_selector('button[aria-controls="sidebar"]')
    return driver


def initNoWebsite():
    driver = BrowserAgent()
    return driver


def initCustomWebsite(websiteUrl: str):
    driver = BrowserAgent()
    driver.navigate(websiteUrl)
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

    print(
        f"Received request to run the Vimbot with prompt: {prompt} and completion_condition: {completion_condition}")
    # result = do_image_reasoning_work("google", prompt, completion_condition)
    result = replay_history("todoist", prompt, completion_condition)
    # if result is a json, return it as is, otherwise return it as a string
    if isinstance(result, dict):
        return result
    else:
        return {"result": result}


def classic_mode():
    # The classic mode of the Vimbot
    print("Starting the Vimbot in classic mode...")
    objective = input("Please enter your objective: ")
    completion_condition = input(
        "Please enter your the completion condition: ")
    result = do_image_reasoning_work(
        "https://google.com", objective, completion_condition)
    if isinstance(result, dict):
        return result
    else:
        return {"result": result}


def replay_mode():
    # The replay mode of the Vimbot
    print("Starting the Vimbot in replay mode...")
    objective = input("Please enter your objective: ")
    replay_history("todoist", objective, "When the objective seems complete")


if __name__ == "__main__":
    # if classic mode is supplied, then run classic_mode otherwise run the server
    parser = argparse.ArgumentParser()
    parser.add_argument("--classic", action="store_true")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.classic:
        classic_mode()
    elif args.replay:
        replay_mode()
    elif args.reset:
        reset_playbook()
    else:
        print("Starting the Flask server...")
        app.run(host="0.0.0.0", port=8000)
