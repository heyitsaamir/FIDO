import time
from io import BytesIO

from PIL import Image
from playwright.sync_api import sync_playwright, Locator
from dataclasses import dataclass

vimium_path = "./vimium-master"


@dataclass
class PlaywrightLocatorResult:
    locator: Locator
    selector: str

    def __getitem__(self, item):
        return getattr(self, item)


class BrowserAgent:
    def __init__(self, headless=False):
        self.playwright = sync_playwright().start()
        self.context = (
            self.playwright
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

    def close(self):
        self.playwright.stop()

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

    def get_selector(self, action) -> str | None:
        if "click" in action:
            xpath = self.get_x_path(action["click"])
            locator = self.page.locator(f"xpath={xpath}")
            handle = locator.element_handle()
            res: PlaywrightLocatorResult = self.page.evaluate('''
                (handle) => {
                    return {
                        selector: window.playwright.selector(handle),
                        locator: window.playwright.generateLocator(handle),
                    }
                }''', handle)

            return res['selector']

    def navigate(self, url):
        self.page.goto(
            url=url if "://" in url else "https://" + url, timeout=60000)

    def type(self, text):
        time.sleep(1)
        self.page.keyboard.type(text)

    def click(self, text):
        xpath = self.get_x_path(text)
        self.hideHints()
        locator = self.page.locator(f"xpath={xpath}")
        locator.click(force=True)
        self.page = self.context.pages[-1]

    def showHints(self, withVimBindings: bool = True):
        self.page.evaluate('''
                           () => {
                               const data = { type: "ACTIVATE_VIMIUM", text: "Activate_Vimium" };
                               window.postMessage(data, "*");
                           }
                           ''')
        
    def hideHints(self, withVimBindings: bool = True):
        self.page.evaluate('''
                           () => {
                               const data = { type: "DEACTIVATE_VIMIUM", text: "Deactivate_Vimium" };
                               window.postMessage(data, "*");
                           }
                           ''')

    def scroll(self, direction):
        self.page.keyboard.press("Escape")
        if direction == "down":
            self.page.keyboard.type("d")
        elif direction == "up":
            self.page.keyboard.type("u")
            
    def get_x_paths_for_all_hints(self) -> dict[str, str]:
        return self.page.evaluate('''
            () => {
                const container = document.getElementById('vimiumHintMarkerContainer')
                if (!container) {
                    return null
                }
                var xPaths = {};
                for (let i = 0; i < container.children.length; i++) {
                    const hint = container.children[i]
                    if (!hint.getAttribute('data-xpath')) {
                        continue;
                    }
                    const xPathResult = document.evaluate(hint.getAttribute('data-xpath'), document, null, XPathResult.ANY_TYPE, null);
                    if (!xPathResult) {
                        continue;
                    }
                    const element = xPathResult.iterateNext()
                    if (!element) {
                        continue;
                    }
                    const tagName = element.tagName.toLowerCase()
                    const innerText = element.innerText
                    let hintStrs = []
                    if (tagName) {
                        hintStrs.push(`type="${tagName}"`)
                    }
                    if (innerText) {
                        switch (tagName) {
                            case 'body':
                            case 'html':
                                continue;
                            case 'select': {
                                const name = element.getAttribute('name');
                                const optionText = [];
                                for (let i = 0; i < element.options.length; i++) {
                                    optionText.push(element.options[i].text);
                                }
                                const options = optionText.join(', ');
                                if (name) {
                                    hintStrs.push(`name="${name}"`)
                                }
                                if (options) {
                                    hintStrs.push(`options="${options}"`)
                                }
                            }
                            break;
                            case 'input': {
                                const type = element.getAttribute('type');
                                const name = element.getAttribute('name');
                                hintStrs.push(`inputType="${type ?? 'Unknown'}"`)
                                if (name) {
                                    hintStrs.push(`name="${name}"`)
                                }
                            }
                            default:
                                hintStrs.push(`text="${innerText}"`)
                        }
                    }
                    xPaths[hint.innerText] = hintStrs.join(' ');
                }
                return xPaths;
            }
            ''')

    def get_x_path(self, shortcut) -> str:
        return self.page.evaluate('''
            (shortcut) => {
                function findXPath(hintText) {
                    const container = document.getElementById('vimiumHintMarkerContainer')
                    if (!container) {
                        return null
                    }
                    for (let i = 0; i < container.children.length; i++) {
                        const hint = container.children[i]
                        if (hint.innerText === hintText) {
                            return hint.getAttribute('data-xpath')
                        }
                    }
                }
                
                return findXPath(shortcut)
            }            
            ''', shortcut)

    def get_current_url(self):
        return self.page.url

    def capture(self, withVimBindings: bool = True):
        # capture a screenshot with vim bindings on the screen
        self.showHints(withVimBindings)
        screenshot = Image.open(BytesIO(self.page.screenshot())).convert("RGB")
        return screenshot
