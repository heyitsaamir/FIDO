import time
from io import BytesIO

from PIL import Image
from playwright.sync_api import sync_playwright

vimium_path = "./vimium-master"


class Vimbot:
    def __init__(self, headless=False):
        self.context = (
            sync_playwright()
            .start()
            .chromium.launch_persistent_context(
                "/Users/aamirjawaid/Library/Application Support/Google/Chrome",
                headless=headless,
                args=[
                    f"--disable-extensions-except={vimium_path}",
                    f"--load-extension={vimium_path}",
                ],
                ignore_https_errors=True,
            )
        )

        self.page = self.context.new_page()
        self.page.set_viewport_size({"width": 760, "height": 844})

    def perform_action(self, action):
        print(f"Performing action: {action}")
        if "done" in action:
            return True
        if "result" in action:
            return action
        if "click" in action and "type" in action:
            if "clicked_element" in action:
                self.page.locator(action["clicked_element"]).click()
            else:
                self.click(text=action["click"])
            self.type(action["type"])
        elif "navigate" in action:
            self.navigate(action["navigate"])
        elif "type" in action:
            self.type(action["type"])
        elif "scroll" in action:
            self.scroll(action["scroll"])
        elif "click" in action:
            if "clicked_element" in action:
                self.page.locator(action["clicked_element"]).click()
            else:
                self.click(text=action["click"])
    
    def focus(self, action):
        if "click" in action:
            self.page.keyboard.press("Escape")
            self.page.keyboard.type("X")
            time.sleep(1)
            print(f"Clicking on {action['click']}")
            self.click(action["click"])
            time.sleep(1)
            focusedElement = self.get_active_element()
            self.page.keyboard.type("f")
            time.sleep(1)
            return focusedElement

    def navigate(self, url):
        self.page.goto(url=url if "://" in url else "https://" + url, timeout=60000)

    def type(self, text):
        time.sleep(1)
        self.page.keyboard.type(text)
        # self.page.keyboard.press("Enter")

    def click(self, text):
        self.page.keyboard.type(text)

    def reset(self, withPause: bool = False):
        self.page.keyboard.press("Escape")
        self.page.keyboard.type("f")
        if withPause:
            time.sleep(1)

    def scroll(self, direction):
        self.page.keyboard.press("Escape")
        if direction == "down":
            self.page.keyboard.type("d")
        elif direction == "up":
            self.page.keyboard.type("u")

    def get_current_url(self):
        return self.page.url
    
    def get_active_element(self):
        return self.page.evaluate("window.playwright.selector(document.activeElement)")

    def capture(self):
        # capture a screenshot with vim bindings on the screen
        self.reset()
        screenshot = Image.open(BytesIO(self.page.screenshot())).convert("RGB")
        return screenshot
