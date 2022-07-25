
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
import time

import os
#from win32gui import GetWindowText,GetClassName,ShowWindow,EnumWindows


from webdriver_manager.chrome import ChromeDriverManager

class Client:
    def __init__(self, me, hidden=True, proxy = None) -> None:
        super().__init__()
        
        self.me = me
        self.hidden = hidden
        self.proxy = proxy
        self.loop = asyncio.get_event_loop()
    
    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.quit()
    
    def quit(self):
        self.browser.quit()
        return True

    def start(self, function = None):
        options = Options()

        options.add_argument("--user-data-dir={}/selenium".format(os.getcwd()))

        if self.proxy!=None:
            options.add_argument('--proxy-server=%s' % self.proxy)

        if self.hidden:
            options.add_argument("--headless")
            #options.add_argument('--disable-gpu')
            options.add_argument('--log-level=3')

            #loglamayı kapatır
            options.add_experimental_option('excludeSwitches', ['enable-logging'])

        options.add_argument("--lang=en")
        options.add_argument("accept-language=en-US")
        options.add_argument("user-agent=User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")

        self.browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        self.auth()
    
    def run(self,function):        
        if function != None:                
            loop = asyncio.get_event_loop()
            run = loop.run_until_complete
            run(function())

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
        self.wait_el('[data-testid="chatlist-header"]')
    
    def get_conversation_header(self):
        # like number of person
        return self.find_el('[data-testid="conversation-info-header"]')

    def get_dialogs(self):
        return self.browser.execute_script('''return document.querySelectorAll('[data-testid="chat-list"] > div > div')''')
    
    def get_last_message(self):
        msgs = self.get_messages()
        return msgs[-1]
    
    def get_chat_id(self, chat = None):
        """
        Returns unique chat id like this: 120363044603884375
        """
        if chat != None:
            self.get_chat(chat)
        i = self.get_last_message().find_element_by_xpath("..").get_attribute("data-id")
        id = i.split("@")[0].split("_")[1]
        if "-" in id:
            # owner = id.split("-")[0] 
            return id.split("-")[1]        
        return id

    def get_message_id(self, msg):
        return self.get_last_message().find_element_by_xpath("..").get_attribute("data-id").split("_")[-2]

    def parse_message(self, message):
        ayir = message.text.split("\n")
        if len(ayir) == 4: #replied
            replied_owner = ayir[0]
            replied_msg = ayir[1]
            msg = ayir[2]
            hour = ayir[3]
            return {
                
                "reply_to_message": {
                    "replied_owner": replied_owner,
                    "replied_msg": replied_msg
                },
                "msg": msg,
                "hour": hour
            }
        if len(ayir) == 2:
            msg = ayir[0]
            hour = ayir[1]
            return {
                "msg": msg,
                "hour": hour
            }

    def get_messages(self):
        try:
            self.find_el('[data-testid="down"]').click()
        except:
            pass
        return self.wait_els('[data-testid="msg-container"]')
    
    def get_message_status(self, msg):
        """
        Okundu, Teslim edildi, Gönderildi
        
        """
        # [...document.querySelectorAll('[data-testid="msg-container"]')].slice(-1)[0].querySelector('[data-testid="msg-dblcheck"]').ariaLabel
        while 1:
            try:
                son_msg = self.get_messages()[-1]

                try:
                    return son_msg.find_element(By.CSS_SELECTOR, '[data-testid*="check"]').accessible_name
                except:
                    return False
            except:
                time.sleep(.1)
    
    def edit_chat_name(self, chat):
        return chat.replace("+", "").replace(" ", "")

    def chat_type(self, chat):
        if chat.find_elements(By.CSS_SELECTOR, '[data-testid="default-group"]') != []:
            return "group"
        if chat.find_elements(By.CSS_SELECTOR, '[data-testid="default-user"]') != []:
            return "user"
        
    def send_message(self, chat, text):
        if self.get_chat(chat) == False and self.edit_chat_name(self.get_conversation_header().text) != self.edit_chat_name(chat):
            self.go_chat_with_no(chat)

        text = str(text)

        if text == "":
            return True

        JS_ADD_TEXT_TO_INPUT = """
        var elm = arguments[0], txt = arguments[1];
        elm.value += txt;
        elm.dispatchEvent(new Event('change'));
        """
        time.sleep(2)
        

        while 1:
            try:
                el = self.browser.find_element(By.CSS_SELECTOR, '''[data-testid="conversation-compose-box-input"]''')

                try:
                    el.send_keys(text + "\n")
                except Exception as e:
                    if "only supports characters in the BMP" in str(e):
                        self.browser.execute_script(JS_ADD_TEXT_TO_INPUT, el, text)

                self.get_message_status(self.get_last_message())
                break
            except Exception as e:
                if self.browser.find_elements(By.CSS_SELECTOR, '[data-testid="block-message"]') != []:
                    return False
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

    
    def wait_els(self, selector, timeout=30):
        for _ in range(round(timeout/.1)):
            el = self.browser.find_elements(By.CSS_SELECTOR, selector)
            if el == []:
                time.sleep(.1)
            else:
                return el
        return el

    def get_chat_search_results(self, text):
        search_input = self.wait_el('''[data-testid="chat-list-search"]''')
        search_input.clear()
        search_input.click()
        time.sleep(.2)
        search_input.send_keys(text)
        time.sleep(1)
        
        conclusion = []
        while 1: #timeout
            try:
                conclusion = self.browser.find_elements(By.CSS_SELECTOR, "[data-testid='search-no-chats-or-contacts']")
                if "," in conclusion.text:
                    conclusion = []
                    break
            except:
                pass
            
            conclusion = self.browser.find_elements(By.CSS_SELECTOR, '''[data-testid="cell-frame-container"]''')
            if conclusion != []:
                break
                
            time.sleep(.1)
        
        
        return conclusion

    def close_search(self):
        try:
            #search_input.send_keys(Keys.ESCAPE)
            self.browser.find_element(By.CSS_SELECTOR, '[data-testid="x-alt"]').click()
        except:
            pass

    def get_chat(self, text):
        count = []

        if text == "me":
            text = self.me
        
        conv_hd = self.get_conversation_header()
        if conv_hd != False:
            if self.edit_chat_name(conv_hd.text) == text:
                return True

        while 1:
            try:
                results = self.get_chat_search_results(text)
                for chat in results:
                    split = chat.text.split("\n")
                    chat_name = split[0]
                    #chat_date = split[1]

                    
                    
                    if self.edit_chat_name(chat_name.lower()) == self.edit_chat_name(text.lower()):
                        chat.click()
                        self.close_search()
                        return True
                    
                    if self.edit_chat_name(text.lower()) in self.edit_chat_name(chat_name.lower()):
                        count.append(chat)
                break
            except:
                time.sleep(.1)
        
        if len(count) == 1:
            count[0].click()
            self.close_search()
            return True
        return False

    def go_chat_with_no(self, number):
        number = self.edit_chat_name(number)
        if number.isdigit() == False:
            return False
        self.browser.get("https://web.whatsapp.com/send?phone={}".format(number))
        self.wait_loading()
    
    def get_group_participant_count(self, group):
        self.get_chat(group)
        self.get_conversation_header().click()
        # document.querySelector('[data-testid="popup-contents"]').querySelectorAll('[data-testid="cell-frame-container"]')
        #time.sleep(2)
        while 1:
            try:
                katilimci = self.browser.find_element(By.CSS_SELECTOR, '[data-testid="section-participants"]').text.split(" ")[0]
            except:
                return 0
            if katilimci != "":
                return katilimci
            time.sleep(.1)

    def get_group_participants(self, group):
        self.get_chat(group)
        self.get_conversation_header().click()
        self.wait_el('[data-icon="search"]').click()
        popup = self.wait_el('[data-testid="popup-contents"]')
        # document.querySelector('[data-testid="popup-contents"]').querySelectorAll('[data-testid="cell-frame-container"]')

        while 1:
            participants_count = self.browser.find_element(By.CSS_SELECTOR, '[data-testid="section-participants"]').text.split(" ")[0]
            try:
                participants_count = int(participants_count)
                break
            except:
                time.sleep(.1)
        participants = []
        while 1:
            participants_part = popup.find_elements(By.CSS_SELECTOR, '[data-testid="cell-frame-container"]')

            done = True
            for i in participants_part:
                try:
                    if i.text.endswith("..."):
                        done = False
                        time.sleep(1)
                        break
                    if "" == i.text:
                        done = False
                        time.sleep(1)
                        break
                except Exception as e:
                    done = False
                    break
            if not done:
                continue

            for participant in participants_part:
                if not participant.text in participants:
                    participants.append(participant.text)

            if len(participants) != participants_count:
                self.browser.execute_script('''document.querySelector('[data-testid="popup-contents"] > [class] > div[class]').scrollTop += 500''')
                continue

            break

        while 1:
            try:
                self.find_el('[data-testid="btn-closer-drawer"]').click()
                break
            except:
                time.sleep(.1)
        return participants
    def right_click(self, el):
        ActionChains(self.browser).context_click(el).perform()

    def right_click_css(self, selector):
        ActionChains(self.browser).context_click(self.browser.execute_script(f'return document.querySelector("{selector}")')).perform()

    def archive_chat(self, chat):
        self.right_click(chat)
        time.sleep(.5)
        self.find_el('[aria-label*="arşiv"]').click()
        return True
    
    def send_document(self, chat, img_location):
        self.get_chat(chat)
        time.sleep(2)
        try:
            self.browser.find_element(By.CSS_SELECTOR, '[data-testid="clip"]').click()
            self.wait_el('input[accept*=image]').send_keys(img_location)
            self.wait_el('[data-icon="send"]').find_element_by_xpath("..").click()
            return True
        except Exception as e:
            return False
    async def message_handler_async(self, group):
        while True:
            try:
                not_readed = [i.find_element_by_xpath("..").find_element_by_xpath("..").find_element_by_xpath("..").find_element_by_xpath("..").find_element_by_xpath("..").find_element_by_xpath("..") for i in self.browser.find_elements(By.CSS_SELECTOR, '[aria-label*="okunmamış mesaj"]')]

                if not_readed != []:
                    for i in not_readed:
                        class datas:
                            def __init__(self, i):
                                self.i = i
                            def __repr__(self):
                                return self.i
                        
                        datas = datas(i)
                        datas.raw_text = i.text

                        ayir = i.text.split("\n")
                                            
                        datas.sender = ayir[0]
                        datas.msg_date = ayir[1]
                        datas.msg_count = ayir[-1]
                        if len(ayir) == 4:
                            datas.last_msg = ayir[2]
                        else:
                            datas.sender = ayir[2]
                            datas.group_name = ayir[0]
                            datas.last_msg = ayir[-2]
                        
                        datas.type = self.chat_type(i)
                        self.loop.create_task(group(datas))
                
                await asyncio.sleep(2)
            except Exception as e:
                print(e)
                await asyncio.sleep(1)

    def message_handler(self, func):
       asyncio.create_task(self.message_handler_async(func))


# '[aria-label*="okunmamış mesaj"]'