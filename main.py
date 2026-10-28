import os
import re
import sys
import shutil
import time
import uuid
import random
import requests
from DrissionPage import ChromiumPage, ChromiumOptions

MAIL_API = 'https://mail.ldjx7.dpdns.org/api'

FIRST_NAMES = ['James', 'David', 'Alex', 'Chris', 'Michael', 'Daniel', 'Robert', 'Emma', 'Olivia', 'Sophia', 'William', 'Lucas', 'Henry']
LAST_NAMES = ['Smith', 'Johnson', 'Brown', 'Taylor', 'Miller', 'Wilson', 'Moore', 'Anderson', 'Thomas', 'Jackson', 'White', 'Harris']

def get_admin_token(email='admin@187425.xyz', password='Tiancai1874@'):
    print(f'[+] 正在登录管理员: {email}')
    res = requests.post(f'{MAIL_API}/login', json={'email': email, 'password': password}).json()
    token = res['data']['token']
    print('[+] 管理员登录成功')
    return token

def create_mail_user(admin_token, email, password):
    print(f'[+] 正在创建临时邮箱: {email}')
    res = requests.post(f'{MAIL_API}/user/add', headers={'Authorization': admin_token}, json={'email': email, 'password': password}).json()
    print(f'[+] 临时邮箱创建结果: {res.get("message")}')

def get_user_token_and_acc(email, password):
    print(f'[+] 正在登录临时邮箱: {email}')
    res = requests.post(f'{MAIL_API}/login', json={'email': email, 'password': password}).json()
    token = res['data']['token']
    acc_res = requests.get(f'{MAIL_API}/account/list', headers={'Authorization': token}).json()
    account_id = acc_res['data'][0]['accountId']
    print(f'[+] 临时邮箱登录成功，accountId: {account_id}')
    return token, account_id

def wait_for_verification_code(token, account_id, timeout=60):
    print('[+] 等待接收验证码邮件...')
    start = time.time()
    while time.time() - start < timeout:
        res = requests.get(f'{MAIL_API}/email/list', headers={'Authorization': token}, params={'accountId': account_id, 'type': 0}).json()
        items = res.get('data', {}).get('list', [])
        if items:
            content = items[0].get('content', '')
            m = re.search(r'>(\d{6})<', content) or re.search(r'(\d{6})', content)
            if m:
                code = m.group(1)
                print(f'[+] 成功获取验证码: {code}')
                return code
        print('[*] 暂未收到邮件，继续轮询...')
        time.sleep(2)
    print('[-] 获取验证码超时')
    return None

def set_react_input(page, element, value):
    page.run_js('''
      const input = arguments[0];
      const value = arguments[1];
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, value);
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    ''', element, value)

def submit_email(page, email, max_retries=5):
    for i in range(max_retries):
        print(f'[+] 正在输入邮箱: {email} (第 {i+1} 次尝试)')
        input_box = page.ele('@autocomplete=username', timeout=3) or page.ele('@placeholder=手机号或邮箱', timeout=2) or page.ele('@inputmode=email', timeout=2)
        if input_box:
            set_react_input(page, input_box, email)
            time.sleep(0.5)
            btn = page.ele('@data-pel-click=login_contact_continue_click', timeout=2) or page.ele('text=继续', timeout=2) or page.ele('@type=submit', timeout=2)
            if btn:
                btn.click(by_js=True)

        for _ in range(6):
            time.sleep(1)
            if page.ele('@autocomplete=one-time-code', timeout=1) or page.ele('text:验证码', timeout=1):
                print('[+] 成功进入验证码页面')
                return True

        print('[*] 未检测到验证码页面，正在重试提交邮箱...')
    return False

def submit_code(page, code, max_retries=5):
    for i in range(max_retries):
        print(f'[+] 正在页面填写验证码: {code} (第 {i+1} 次尝试)')
        code_box = page.ele('@autocomplete=one-time-code', timeout=3)
        if code_box:
            set_react_input(page, code_box, code)
            time.sleep(0.5)
            btn = page.ele('text=确认', timeout=2) or page.ele('@type=submit', timeout=2)
            if btn:
                btn.click(by_js=True)

        for _ in range(6):
            time.sleep(1)
            if page.ele('@autocomplete=given-name', timeout=1) or page.ele('@placeholder=名', timeout=1) or page.ele('text:完成账户创建', timeout=1):
                print('[+] 成功进入个人信息页面')
                return True

        print('[*] 未检测到个人信息页面，正在重试提交验证码...')
    return False

def fill_profile(page, max_retries=5):
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    year = random.randint(1990, 2002)
    month = random.randint(1, 12)
    day = random.randint(1, 28)

    print(f'[+] 正在填写英文姓名: {first_name} {last_name}')
    fn_box = page.ele('@autocomplete=given-name', timeout=3) or page.ele('@placeholder=名', timeout=2)
    if fn_box:
        set_react_input(page, fn_box, first_name)
    time.sleep(0.3)

    ln_box = page.ele('@autocomplete=family-name', timeout=3) or page.ele('@placeholder=姓', timeout=2)
    if ln_box:
        set_react_input(page, ln_box, last_name)
    time.sleep(0.3)

    print(f'[+] 正在选择出生日期: {year}年 {month}月 {day}日')
    year_btn = page.ele('@aria-label=年', timeout=3) or page.ele('@aria-label=Year', timeout=2)
    if year_btn:
        year_btn.click()
        time.sleep(0.5)
        opt = page.ele(f'text={year}', timeout=2)
        if opt:
            opt.click()
        time.sleep(0.5)

    month_btn = page.ele('@aria-label=月', timeout=3) or page.ele('@aria-label=Month', timeout=2)
    if month_btn:
        month_btn.click()
        time.sleep(0.5)
        opt = page.ele(f'text={month} 月', timeout=2) or page.ele(f'text={month}', timeout=2)
        if opt:
            opt.click()
        time.sleep(0.5)

    day_btn = page.ele('@aria-label=日', timeout=3) or page.ele('@aria-label=Day', timeout=2)
    if day_btn:
        day_btn.click()
        time.sleep(0.5)
        opt = page.ele(f'text={day}', timeout=2)
        if opt:
            opt.click()
        time.sleep(1)

    print('[+] 点击“确认”按钮提交个人信息')
    for i in range(max_retries):
        confirm_btn = page.ele('@data-pel-click=login_birthday_continue_click', timeout=2) or page.ele('text=确认', timeout=2) or page.ele('@type=submit', timeout=2)
        if confirm_btn:
            confirm_btn.click(by_js=True)
        time.sleep(2)
        if not (page.ele('@autocomplete=given-name', timeout=1) or page.ele('@placeholder=名', timeout=1)):
            print('[+] 个人信息提交成功，已完成创建')
            time.sleep(2)
            body_text = page.ele('tag:body', timeout=3).text
            print(f'[+] 页面内容:\n{body_text}')
            return True
        print(f'[*] 个人信息页面未跳转，正在重新点击确认 (第 {i+1} 次重试)...')
    return False

def run(headless=False):
    admin_token = get_admin_token()
    uid = uuid.uuid4().hex[:8]
    email = f'muse{uid}@187425.xyz'
    password = f'Pwd_{uid}!'
    create_mail_user(admin_token, email, password)

    print('[+] 正在启动浏览器...')
    co = ChromiumOptions()
    if headless:
        co.set_argument('--headless=new')
    co.auto_port()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-software-rasterizer')
    co.set_argument('--test-type')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--lang=zh-CN')
    co.set_pref('intl.accept_languages', 'zh-CN,zh')
    co.set_user_agent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')

    for b in ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']:
        p = shutil.which(b)
        if p:
            co.set_browser_path(p)
            break

    page = ChromiumPage(co)

    print('[+] 正在打开 https://muse.ai')
    page.get('https://muse.ai')

    if not submit_email(page, email):
        print('[-] 邮箱提交失败，未能进入验证码页面')
        return page

    user_token, acc_id = get_user_token_and_acc(email, password)
    code = wait_for_verification_code(user_token, acc_id)
    if not code:
        print('[-] 未能获取验证码')
        return page

    if not submit_code(page, code):
        print('[-] 验证码提交失败，未能进入个人信息页面')
        return page

    fill_profile(page)
    return page

if __name__ == '__main__':
    headless = os.getenv('CI') is not None or os.getenv('HEADLESS') == 'true' or (sys.platform == 'linux' and not os.getenv('DISPLAY'))
    page = run(headless=headless)
    if headless and page:
        page.quit()
