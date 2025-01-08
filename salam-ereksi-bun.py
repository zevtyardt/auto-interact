import json
import os
from tempfile import NamedTemporaryFile
import time
import langdetect
import textwrap
import loguru


from PIL import Image
from PIL.ImageFile import ImageFile
from poe_api_wrapper import PoeApi

import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

loguru.logger.remove()

JS_ADD_TEXT_TO_INPUT = """
  var elm = arguments[0], txt = arguments[1];
  elm.value += txt;
  elm.dispatchEvent(new Event('change'));
  """

with open("configs.json") as fp:
    configs = json.load(fp)

config_index = 0

chatId = None

visited = []
if os.path.isfile("visited.json"):
    with open("visited.json") as fp:
        visited = json.load(fp)

cached = {}
if os.path.isfile("cached.json"):
    with open("cached.json") as fp:
        cached = json.load(fp)


def poe_client() -> PoeApi:
    global config_index, chatId
    print("• Connecting to poe service.. ", end="", flush=True)

    connected = False
    while config_index <= len(configs) - 1:
        token = configs[config_index]["token"]
        client = PoeApi(tokens=token)
        if not token.get("formkey"):
            configs[config_index]["token"]["formkey"] = client.formkey
        point = (
            client.get_settings()
            .get("messagePointInfo", {})
            .get("messagePointBalance", 0)
        )
        if point > 175:
            connected = True
            chatId = configs[config_index].get("chatId")
            break
        config_index += 1
    if not connected:
        print("Failed")
        print(
            "• All balance points in your account have been used up, please try again tomorrow."
        )
        exit()

    print("Ok")
    return client


def generate_comment(
    client: PoeApi, author: str, caption: str, image: ImageFile | None
) -> str:
    global chatId

    history = client.get_chat_history("fbcommenter")
    if str(chatId) not in str(history):
        chatId = None

    print("  • Asking AI to generate comment")

    if chatId:
        print("    • Delete chat context, create new one")
        client.chat_break("fbcommenter", chatId=chatId)

    try:
        lang = langdetect.detect(caption)
        if lang not in ["id", "en", "ja"]:
            lang = "en"
    except Exception:
        lang = "id"

    print("      ==== Input =====")

    print(f"      From: {author}")
    print(
        "      Caption: {}".format(
            textwrap.indent(textwrap.fill(caption, 60), " " * 15).strip()
            if caption != ""
            else "<Empty>"
        )
    )
    print(f"      Lang: {lang}")

    text = f"From: {author}\nCaption: {caption}\nLang: {lang}"
    if image:
        with NamedTemporaryFile("wb", suffix=".png") as temp:
            image.save(temp.name)
            print(
                f"      Image: {temp.name}"
            )
            print("      ==== Output ====")
            for chunk in client.send_message(
                "fbcommenter", text, file_path=[temp.name], chatId=chatId
            ):
                pass
    else:
        print("      Image: <None>")
        print("      ==== Output ====")
        for chunk in client.send_message("fbcommenter", text, chatId=chatId):
            pass

    print(textwrap.indent(textwrap.fill(chunk["text"]), "      "))
    print("      ================")

    msgPrice = chunk["msgPrice"]
    point = (
        client.get_settings().get("messagePointInfo", {}).get("messagePointBalance", 0)
    )
    print(f"    • Remaining point: {point} or {point // msgPrice} message left")

    if not chatId:
        configs[config_index]["chatId"] = chunk["chatId"]
    return chunk["text"]


def initialize_driver():
    print("• Starting headless Chrome")
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36"
    )
    options.add_argument("window-size=400,807")

    mobile_emulation = {"deviceName": "iPhone 12 Pro"}
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    options.add_experimental_option("windowTypes", ["webview"])

    driver = webdriver.Chrome(
        options=options,
    )
    driver.maximize_window()  # Maximize the window for better view

    return driver


def load_cookies(driver, cookie_file):
    """Load cookies from a JSON file and add them to the WebDriver."""
    with open(cookie_file) as f:
        print(f"• Load cookies from: {f.name}")
        cookies = json.load(f)
        for cookie in cookies:
            # Normalize the SameSite attribute
            cookie["sameSite"] = cookie["sameSite"].capitalize()
            if cookie["sameSite"] not in ["Strict", "Lax", "None"]:
                cookie["sameSite"] = "None"
            driver.add_cookie(cookie)

    print("  • Refreshing webpage")
    driver.refresh()


def fetch_post_details(driver):
    print("      • Fetching author post.. ", end="", flush=True)
    try:
        header = (
            driver.find_element(By.XPATH, "//span[contains(text(), 'Postingan')]")
            .text.strip()
            .removeprefix("Postingan ")
        )
        title = driver.find_element(By.XPATH, "//span[@role='link']").text.strip()

        if title.lower().startswith(header.lower()):
            author = title
        else:
            author = None
    except Exception:
        author = None
    print("Ok" if author else "Failed")

    print("      • Fetching caption.. ", end="", flush=True)
    try:
        caption = driver.find_element(
            By.XPATH, "//div[3]/div[4]/div[1]/div[1]"
        ).text.strip()
    except Exception:
        caption = ""
    print("Ok" if caption != "" else "Failed")

    print("      • Fetching image.. ", end="", flush=True)
    image = fetch_post_image(driver)
    print("Ok" if image else "Failed")

    return author, caption, image


def fetch_post_image(driver):
    try:
        image_src = driver.find_element(
            By.XPATH, "//div[contains(@aria-label, 'gambar')]/img"
        ).get_attribute("src")
        return Image.open(requests.get(image_src, stream=True).raw)
    except Exception:
        return None


def is_video_post(driver):
    try:
        driver.find_element(By.XPATH, "//div[contains(@aria-label, 'Pemutar')]")
        return True
    except Exception:
        return False


def has_follow_button(post: WebElement):
    try:
        post.find_element(By.XPATH, "//span[text()='Ikuti']")
        return True
    except Exception:
        return False


def iter_posts(driver: WebDriver):
    print("• Collecting public posts")
    post_xpath = (
        '//div[@aria-label="Lainnya"]/parent::*/parent::*/parent::div/parent::*'
    )

    url = driver.current_url

    first_run = True
    while True:
        try:
            if not first_run:
                print("  • Refreshing webpage.. ", end="", flush=True)
                driver.get(url)
            else:
                print("  • Waiting for post to appear.. ", end="", flush=True)
                first_run = False
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@aria-label='Lainnya']")
                )
            )

            total_height = int(
                driver.execute_script("return document.body.scrollHeight")
            )
            for i in range(1, total_height, 10):
                driver.execute_script(f"window.scrollTo(0, {i});")
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.HOME)
            time.sleep(0.5)

            posts = driver.find_elements(By.XPATH, post_xpath)
            print(f"Ok ({len(posts)})")

            while len(posts) > 0:
                is_flushed = True
                post = posts.pop(0)
                if post.id in visited:
                    continue
                visited.append(post.id)

                ActionChains(driver).move_to_element(post).perform()
                if has_follow_button(post) and "Bersponsor" not in post.text:
                    print("    • Fetching source posts.. ", end="", flush=True)
                    is_flushed = False
                    try:
                        from_ = post.find_element(By.XPATH, "//span[@role='link']")
                    except Exception:
                        print("Error")

                        continue

                    author = from_.text.strip()
                    print(author, end=" ", flush=True)

                    post_type = cached.get(author)

                    is_ok = False
                    need_back = False
                    if not post_type or not is_ok:
                        ActionChains(driver).move_to_element(from_).click().perform()

                        xpath = '//span[contains(text(), "Halaman") or contains(text(), "Profil") or contains(text(), "Grup") or contains(text(), "Teman")]'
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        post_type = driver.find_element(By.XPATH, xpath).text.strip()
                        cached[author] = post_type
                        need_back = True

                    print("(", end="")
                    if "Profil" in post_type:
                        print("Public", end="", flush=True)
                        is_ok = True
                    elif "Halaman" in post_type:
                        print("Page", end="", flush=True)
                    elif "Grup" in post_type:
                        print("Group", end="", flush=True)
                    else:
                        print("Friend List", end="", flush=True)
                    print(")")
                    is_flushed = True

                    if need_back:
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.XPATH, "//span[@role='link']")
                            )
                        )

                    if is_ok:
                        element = post.find_element(
                            By.XPATH, "//div[contains(@aria-label, 'comment')]"
                        )
                        ActionChains(driver).move_to_element(element).click().perform()

                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.XPATH, '//*[contains(text(), "Postingan")]')
                            )
                        )

                        print(
                            f"      • Target post: {driver.current_url.split('?', 1)[-1]}"
                        )
                        data = fetch_post_details(driver)

                        if is_video_post(driver):
                            print("        • Post contain video. Skipping")
                        else:
                            textarea = driver.find_element(By.TAG_NAME, "textarea")
                            yield data, textarea
                            yield  # Add another yield as a breakpoint

                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located(
                                (By.XPATH, "//span[@role='link']")
                            )
                        )

                driver.execute_script(
                    "var element = arguments[0]; element.parentNode.removeChild(element);",
                    post,
                )
        except Exception:
            if not is_flushed:
                print("(Unknown Error)")


def post_comment(driver: WebDriver, textarea: WebElement, text: str):
    print("  • Adding a new comment")

    driver.execute_script(JS_ADD_TEXT_TO_INPUT, textarea, text)
    textarea.click()
    time.sleep(1)

    driver.find_element(By.XPATH, "//div[@aria-label='Posting komentar']").click()
    time.sleep(1)
    print("  • Done")


def main():
    max = int(__import__("sys").argv[1])

    print("\n  Tool Auto `Salam Injeksi Bun` with AI 🚀\n")

    client = poe_client()
    driver = initialize_driver()
    try:
        print("• Opening url: m.facebook.com")
        driver.get("https://m.facebook.com")
        driver.delete_all_cookies()
        load_cookies(driver, "./session.json")

        results = iter_posts(driver)

        n = 0
        for data, textarea in results:
            comment = generate_comment(client, *data)
            next(results)

            post_comment(driver, textarea, comment)

            n += 1
            if n == max:
                break
    finally:
        driver.quit()

    print("• Bot finished")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

    with open("configs.json", "w") as fp:
        json.dump(configs, fp, indent=2)
    with open("cached.json", "w") as fp:
        json.dump(cached, fp, indent=2)
    with open("visited.json", "w") as fp:
        json.dump(visited, fp, indent=2)
