import re
import time
import json
import os
import random

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException


class Scraper(object):
    """Able to start up a browser, to authenticate to Instagram and get
    followers and people following a specific user."""

    @staticmethod
    def create_driver(chromedriver_path):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            },
        )
        return driver

    @staticmethod
    def load_simple_cookies_and_auth(driver, cookies_simple_json_path="cookies.json"):
        """
        Lee un JSON con una lista de cookies completas o un formato simple (dict).
        Intenta añadirlas y verifica si la sesión se activa.
        """
        if not os.path.exists(cookies_simple_json_path):
            return False

        driver.get("https://www.instagram.com/")
        time.sleep(2)

        with open(cookies_simple_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            cookies = []
            for name, value in data.items():
                cookies.append(
                    {
                        "name": name,
                        "value": value,
                        "domain": ".instagram.com",
                        "path": "/",
                    }
                )
        elif isinstance(data, list):
            cookies = data
        else:
            return False

        for c in cookies:
            try:
                driver.add_cookie(c)
            except Exception as e:
                print(f"No se pudo añadir cookie {c.get('name')}: {e}")

        driver.refresh()
        time.sleep(3)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//nav"))
            )
            return True
        except Exception:
            return False

    def __init__(self, target, chromedriver_path=None, cookies_path="cookies.json"):
        self.target = target

        self.driver = self.create_driver(chromedriver_path)

        cookies_loaded = False
        try:
            cookies_loaded = self.load_simple_cookies_and_auth(
                self.driver, cookies_path
            )
        except Exception as e:
            cookies_loaded = False

        self._cookies_loaded = cookies_loaded

    def close(self):
        """Close the browser."""

        self.driver.close()

    def authenticate(self, username, password):
        """Log in to Instagram with the provided credentials."""

        print("\nLogging in…")
        self.driver.get("https://www.instagram.com")

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )

        username_input = self.driver.find_element(By.NAME, "username")
        password_input = self.driver.find_element(By.NAME, "password")

        username_input.send_keys(username)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        time.sleep(1)

    def get_users(self, group="following", limit=5, verbose=False):
        import re
        import time
        import random
        from selenium.webdriver.common.by import By

        USERNAME_RE = re.compile(r"^[a-zA-Z0-9._]{1,30}$")

        link = self._get_link("following")
        self._open_dialog(link)

        print("Scrolleando seguidos (máx 100)...")

        users = []

        # 🔑 localizar el DIV que realmente scrollea
        scroll_div = None
        for _ in range(5):
            try:
                scroll_div = self.driver.find_element(
                    By.XPATH,
                    "//div[@role='dialog']//div[contains(@style,'overflow') or contains(@class,'scroll')]"
                )
                if scroll_div:
                    break
            except:
                time.sleep(1)

        if not scroll_div:
            raise Exception("No se encontró el contenedor scrolleable real.")

        while len(users) < limit:
            links = scroll_div.find_elements(
                By.XPATH,
                ".//a[starts-with(@href,'/') and not(contains(@href,'/explore'))]"
            )

            for link in links:
                username = link.text.strip()

                if not USERNAME_RE.match(username):
                    continue

                if username not in users:
                    users.append(username)
                    if verbose:
                        print(f"{len(users)} → {username}")

                if len(users) >= limit:
                    break

            # 🔑 SCROLL REAL
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight",
                scroll_div
            )

            time.sleep(random.uniform(2.5, 3.5))

        return users

    def _get_link(self, group):
        """Return the element linking to the users list dialog (layout 2025)."""
        print(f"\nNavigating to {self.target} profile…")
        self.driver.get(f"https://www.instagram.com/{self.target}/")

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//header"))
            )

            possible_links = self.driver.find_elements(
                By.XPATH,
                "//header//a[contains(@href,'/followers') or contains(@href,'/following') or contains(@href,'/seguidos') or contains(@href,'/seguidores')]",
            )

            if not possible_links:
                possible_links = self.driver.find_elements(
                    By.XPATH,
                    "//header//div[@role='link' or @role='button'] | //header//span",
                )

            if not possible_links:
                raise Exception(
                    "No se encontraron elementos clicables para seguidores/seguidos."
                )

            group = group.lower()
            target_el = None

            for el in possible_links:
                text = el.text.strip().lower()
                if (
                    ("followers" in text and group == "followers")
                    or ("following" in text and group == "following")
                    or ("seguidores" in text and group == "followers")
                    or ("seguidos" in text and group == "following")
                ):
                    target_el = el
                    break

            if not target_el:
                for el in possible_links:
                    href = el.get_attribute("href") or ""
                    if ("/followers" in href and group == "followers") or (
                        "/following" in href and group == "following"
                    ):
                        target_el = el
                        break

            if not target_el:
                raise Exception(
                    f"No se encontró enlace de '{group}' en el perfil actual."
                )

            return target_el

        except Exception as e:
            print(f"Error buscando el enlace de '{group}': {e}")
            return None

    def _open_dialog(self, link):
        if link is None:
            raise Exception("No se pudo abrir el diálogo: enlace no encontrado.")

        self.driver.execute_script("arguments[0].click();", link)
        time.sleep(3)

        # Detectar cualquier contenedor tipo modal
        possible_containers = [
            "//div[@role='dialog']",
            "//section",
            "//div[contains(@style,'overflow')]"
        ]

        container = None
        for xpath in possible_containers:
            try:
                container = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                if container:
                    break
            except:
                pass

        if not container:
            raise Exception("No se detectó ningún contenedor modal de seguidores.")

        # Buscar lista scrolleable interna
        try:
            self.users_list_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    ".//div[.//a[contains(@href,'/')]]"
                ))
            )
        except:
            self.users_list_container = container

    def get_followers_count(self, usernames, delay_range=(2, 4)):
        results = {}
        number_re = re.compile(r"([\d,.]+)")

        for i, username in enumerate(usernames, 1):
            url = f"https://www.instagram.com/{username}/"
            try:
                self.driver.get(url)
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//header"))
                )
            except Exception as e:
                print(f"{username}: header no cargó: {e}")
                results[username] = "N/A"
                time.sleep(random.uniform(*delay_range))
                continue

            followers_count = None

            try:
                follower_link = self.driver.find_element(
                    By.XPATH, "//a[contains(@href,'/followers')]"
                )
                raw = (
                    follower_link.get_attribute("title")
                    or follower_link.get_attribute("aria-label")
                    or follower_link.text
                )
                if raw:
                    m = number_re.search(raw)
                    if m:
                        followers_count = m.group(1).replace(",", "").replace(".", "")
            except NoSuchElementException:
                pass
            except Exception:
                pass

            if not followers_count:
                try:
                    meta = self.driver.find_element(
                        By.XPATH, "//meta[@name='description']"
                    )
                    content = meta.get_attribute("content") or ""
                    m = number_re.search(content)
                    if m:
                        followers_count = m.group(1).replace(",", "").replace(".", "")
                except Exception:
                    pass

            if not followers_count:
                try:
                    raw_json = self.driver.execute_script(
                        "return (window._sharedData || window.__initialData || null);"
                    )
                    if raw_json:
                        js_str = str(raw_json)
                        idx = js_str.lower().find("followers")
                        if idx != -1:
                            snippet = js_str[max(0, idx - 120) : idx + 120]
                            m = number_re.search(snippet)
                            if m:
                                followers_count = (
                                    m.group(1).replace(",", "").replace(".", "")
                                )
                    if not followers_count:
                        try:
                            ld = self.driver.find_element(
                                By.XPATH, "//script[@type='application/ld+json']"
                            )
                            ld_text = ld.get_attribute("innerText") or ""
                            m = number_re.search(ld_text)
                            if m:
                                followers_count = (
                                    m.group(1).replace(",", "").replace(".", "")
                                )
                        except Exception:
                            pass
                except Exception:
                    pass

            if not followers_count:
                try:
                    time.sleep(1)
                    follower_link = self.driver.find_element(
                        By.XPATH, "//a[contains(@href,'/followers')]"
                    )
                    raw = (
                        follower_link.get_attribute("title")
                        or follower_link.get_attribute("aria-label")
                        or follower_link.text
                    )
                    if raw:
                        m = number_re.search(raw)
                        if m:
                            followers_count = (
                                m.group(1).replace(",", "").replace(".", "")
                            )
                except Exception:
                    pass

            results[username] = followers_count or "N/A"

            time.sleep(random.uniform(1.5, 2.5))

        return results
    
    def get_profile_info(self, username):
        
        data = {
            "username": username,
            "nombre": None,
            "bio": None,
            "posts": None,
            "seguidores": None,
            "seguidos": None,
            "verificada": False,
            "privada": False,
        }

        self.driver.get(f"https://www.instagram.com/{username}/")

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )
        except:
            return data

        # =========================
        # 1️⃣ CUENTA PRIVADA
        # =========================
        if self.driver.find_elements(
            By.XPATH, "//*[contains(text(),'This Account is Private')]"
        ):
            data["privada"] = True
            return data

        # =========================
        # 2️⃣ META DESCRIPTION (CLAVE)
        # =========================
        try:
            meta = self.driver.find_element(By.XPATH, "//meta[@name='description']")
            content = meta.get_attribute("content")

            # Ejemplo:
            # "396M Followers, 700 Following, 7,600 Posts - Dwayne Johnson (@therock) on Instagram: “Founder of Seven Bucks...”"

            if content:
                # Seguidores
                m = re.search(r"([\d,.]+)\s+Followers", content, re.I)
                if m:
                    data["seguidores"] = m.group(1)

                # Seguidos
                m = re.search(r"([\d,.]+)\s+Following", content, re.I)
                if m:
                    data["seguidos"] = m.group(1)

                # Posts
                m = re.search(r"([\d,.]+)\s+Posts", content, re.I)
                if m:
                    data["posts"] = m.group(1)

                # Nombre
                m = re.search(r"-\s+(.*?)\s+\(@", content)
                if m:
                    data["nombre"] = m.group(1).strip()

                # Bio
                m = re.search(r"Instagram:\s+“(.+?)”", content)
                if m:
                    data["bio"] = m.group(1).strip()

        except:
            pass

        # =========================
        # 3️⃣ VERIFICADA (SVG)
        # =========================
        data["verificada"] = bool(
            self.driver.find_elements(
                By.XPATH,
                "//*[local-name()='svg' and @aria-label='Verified']"
            )
        )

        time.sleep(1.2)
        return data