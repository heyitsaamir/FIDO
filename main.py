import argparse
import time
import os

from whisper_mic import WhisperMic

import vision
from vimbot import Vimbot


def main(voice_mode):
    print("Initializing the Vimbot driver...")
    driver = Vimbot()

    # print("Navigating to Google...")
    # driver.navigate("https://www.google.com")
    initTodoist(driver)

    if voice_mode:
        print("Voice mode enabled. Listening for your command...")
        mic = WhisperMic()
        try:
            objective = mic.listen()
        except Exception as e:
            print(f"Error in capturing voice input: {e}")
            return  # Exit if voice input fails
        print(f"Objective received: {objective}")
    else:
        objective = input("Please enter your objective: ")

    while True:
        time.sleep(1)
        print("Capturing the screen...")
        screenshot = driver.capture()

        print("Getting actions for the given objective...")
        action = vision.get_actions(screenshot, objective)
        print(f"JSON Response: {action}")
        if driver.perform_action(action):  # returns True if done
            break

def initTodoist(driver):
    driver.navigate("https://app.todoist.com/auth/login")
    driver.page.type('input[type="email"]', os.getenv("TODOIST_USER"))
    driver.page.type('input[type="password"]', os.getenv("TODOIST_PASSWORD"))
    driver.page.click('button[type="submit"]')

def main_entry():
    parser = argparse.ArgumentParser(description="Run the Vimbot with optional voice input.")
    parser.add_argument(
        "--voice",
        help="Enable voice input mode",
        action="store_true",
    )
    args = parser.parse_args()
    main(args.voice)


if __name__ == "__main__":
    try:
        main_entry()
    except KeyboardInterrupt:
        print("Exiting...")
