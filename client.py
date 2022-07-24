
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

import os
#from win32gui import GetWindowText,GetClassName,ShowWindow,EnumWindows


from webdriver_manager.chrome import ChromeDriverManager

class Client:
    def __init__(self, hidden=True, proxy = None) -> None:
        super().__init__()
        
        self.hidden = hidden
        self.proxy = proxy
    
    
    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.quit()
    
    def quit(self):
        self.browser.quit()
        return True

    def start(self):
        options = Options()

        options.add_argument("--user-data-dir={}/selenium".format(os.getcwd()))

        if self.proxy!=None:
            options.add_argument('--proxy-server=%s' % self.proxy)

        if self.hidden:
            options.add_argument("--headless")
            options.add_argument('--disable-gpu')
            options.add_argument('--log-level=3')

            #loglamayı kapatır
            options.add_experimental_option('excludeSwitches', ['enable-logging'])

        options.add_argument("--lang=en")
        options.add_argument("accept-language=en-US")
        options.add_argument("user-agent=User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")

        self.browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        self.auth()
    
    def wait_loading(self):
        while self.is_loading():
            time.sleep(1)
        return True

    def is_loading(self) -> bool:
        text = self.browser.execute_script("return document.body.innerText")
        langs = [
            "Don't close this window" in text,
            "Bu pencereyi kapatmayın." in text,
            "Bilgisayarınızda aktif" in text
        ]
        return any(langs)
    
    def auth(self):
        self.browser.get("https://web.whatsapp.com/")

        if "UPDATE" in self.browser.execute_script("return document.body.innerText"):
            raise "UPDATE NEEDED"

        while self.browser.execute_script('''return document.querySelector('img[src*="/img"]')'''):
            try:            
                qr_code = self.browser.find_element(By.CSS_SELECTOR, '[data-testid="qrcode"]')
                print("QR Code found, waiting for scan...")
                with open('qr_code.png', 'wb') as file:
                    file.write(qr_code.screenshot_as_png)
                os.open('qr_code.png', os.O_RDONLY)
                time.sleep(600)
            except:
                time.sleep(1)   

        self.wait_loading()
    
    def get_conversation_header(self):
        # like number of person
        try:
            return self.browser.find_element(By.CSS_SELECTOR, '[data-testid="conversation-info-header"]')
        except:
            return False

    def get_dialogs(self):
        return self.browser.execute_script('''return document.querySelectorAll('[data-testid="chat-list"] > div > div')''')
    

    def get_last_message(self):

        return self.get_messages()[-1]
    
    def get_chat_id(self, chat = None):
        """
        Returns unique chat id like this: 120363044603884375
        """
        if chat != None:
            self.get_chat(chat)
        i = self.get_last_message().find_element_by_xpath("..").get_attribute("data-id")
        return i.split("@")[0].split("_")[1]


    def get_messages(self):
        return self.wait_el('[data-testid="msg-container"]')
    
    def get_message_status(self, msg):
        """
        Okundu, Teslim edildi, Gönderildi
        
        """
        # [...document.querySelectorAll('[data-testid="msg-container"]')].slice(-1)[0].querySelector('[data-testid="msg-dblcheck"]').ariaLabel
        while 1:
            try:
                return self.get_messages()[-1].find_element(By.CSS_SELECTOR, '[data-testid*="check"]').accessible_name
            except:
                time.sleep(.1)
    
    def edit_chat_name(self, chat):
        return chat.replace("+", "").replace(" ", "")

    def send_message(self, chat, text):
        if self.get_chat(chat) == False and self.edit_chat_name(self.get_conversation_header()) != self.edit_chat_name(chat):
            self.go_chat_with_no(chat)

        text = str(text)

        while 1:
            try:
                self.browser.find_element(By.CSS_SELECTOR, '''[data-testid="conversation-compose-box-input"]''').send_keys(text + "\n")
                self.get_message_status(self.get_last_message())
                break
            except:
                time.sleep(.1)
    
    def find_el(self, selector):
        try:
            el = self.browser.find_element(By.CSS_SELECTOR, selector)
            return el
        except:
            return False
    
    def wait_el(self, selector, timeout=30):
        for _ in range(round(timeout/.1)):
            el = self.find_el(selector)
            if el == False:
                time.sleep(.1)
            else:
                return el
        return el

    def get_chat_search_results(self, text):
        search_input = self.wait_el('''[data-testid="chat-list-search"]''')
        search_input.clear()
        search_input.send_keys(text)
        
        conclusion = []
        while 1: #timeout
            try:
                conclusion = self.browser.find_elements(By.CSS_SELECTOR, "[data-testid='search-no-chats-or-contacts']")
                if "," in conclusion.text:
                    conclusion = []
                    break
            except:
                pass
            
            try:
                conclusion = self.browser.find_elements(By.CSS_SELECTOR, '''[data-testid="cell-frame-container"]''')
                break
            except:
                pass
                
            time.sleep(.1)
        
        search_input.send_keys(Keys.ESCAPE)
        return conclusion

    def get_chat(self, text):
        count = []

        results = self.get_chat_search_results(text)
        for chat in results:
            split = chat.text.split("\n")
            chat_name = split[0]
            #chat_date = split[1]
            
            if chat_name.lower() == text.lower():
                chat.click()
                return True
            
            if text.lower() in chat_name.lower():
                count.append(chat)
        
        if len(count) == 1:
            count[0].click()
            return True
        return False

    def go_chat_with_no(self, number):
        number = self.edit_chat_name(number)
        self.browser.get("https://web.whatsapp.com/send?phone={}".format(number))
        self.wait_loading()

