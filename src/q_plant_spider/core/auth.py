"""
认证模块，负责处理cookies获取和管理
"""
import sys
import os
import time
import pickle
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    ElementClickInterceptedException
)
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# 添加项目根目录到Python路径
ROOT_DIR = Path(__file__).parents[3]
sys.path.insert(0, str(ROOT_DIR))

logger = logging.getLogger(__name__)

class AuthManager:
    """认证管理器"""
    
    # 浏览器配置
    BROWSER_CONFIG = {
        'window_size': '1920x1080',
        'page_load_timeout': 30,
        'implicit_wait': 20,
        'explicit_wait': 20,
        'retry_count': 3,
        'retry_delay': 5
    }

    # URL配置
    URLS = {
        'login_url': 'https://signin-f2.nio.com/login?service=https%3A%2F%2Fsignin-f2.nio.com%2Foauth2%2FcallbackAuthorize%3Fclient_id%3D100656%26redirect_uri%3Dhttps%253A%252F%252Fqplant.nioint.com%252Fq-plant-admin-front%252Faccount%252Fsso%253Fredirect_to%253D%25252Fq-plant-admin-front%25252F%26sso_region%3Dcn'
    }

    # 页面元素定位
    ELEMENTS = {
        'login': {
            'username_input': '/html/body/section[2]/main/main/form/div[1]/div/p/input',
            'password_input': '/html/body/section[2]/main/main/form/div[2]/div/p/input',
            'login_button': '/html/body/section[2]/main/footer/button',
            'content_wrapper': 'content-wrapper',
            'success_indicators': [
                "//div[contains(@class, 'ant-form')]",
                "//span[contains(text(), '查询')]",
                "//div[contains(@class, 'ant-layout')]"
            ]
        }
    }
    
    def __init__(self, cookies_path='cookies.pkl'):
        """
        初始化认证管理器
        
        Args:
            cookies_path: Cookies保存路径
        """
        self.credentials = {
            'username': os.getenv('NIO_USERNAME'),
            'password': os.getenv('NIO_PASSWORD')
        }
        self.cookies_path = Path(cookies_path)
        
        # 检查凭据
        if not self.credentials['username'] or not self.credentials['password']:
            logger.error("环境变量中未设置NIO_USERNAME或NIO_PASSWORD")
            
    def setup_edge_options(self):
        """配置 Edge 选项"""
        options = webdriver.EdgeOptions()
        
        # 基础配置
        options.add_argument('--headless=new')
        options.add_argument(f'window-size={self.BROWSER_CONFIG["window_size"]}')
        
        # 性能优化
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # 错误日志控制
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        return options
        
    def wait_for_element(self, driver, by, value, timeout=None):
        """等待元素加载"""
        timeout = timeout or self.BROWSER_CONFIG['explicit_wait']
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"等待元素超时: {value}")
            raise
            
    def wait_for_url_change(self, driver, original_url, timeout=None):
        """等待URL变化"""
        timeout = timeout or self.BROWSER_CONFIG['explicit_wait']
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.current_url != original_url
            )
            return True
        except TimeoutException:
            return False
            
    def wait_for_page_load(self, driver, timeout=20):
        """等待页面完全加载"""
        try:
            return WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
        except TimeoutException:
            return False
            
    def wait_for_element_interactable(self, driver, by, value, timeout=None):
        """等待元素可交互"""
        timeout = timeout or self.BROWSER_CONFIG['explicit_wait']
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"等待元素可交互超时: {value}")
            raise
            
    def check_login_success(self, driver, max_wait=20):
        """检查是否登录成功"""
        try:
            # 等待页面加载完成
            if not self.wait_for_page_load(driver, timeout=max_wait):
                logger.error("页面加载超时")
                return False

            current_url = driver.current_url
            if 'q-plant-admin-front' in current_url:
                # 使用WebDriverWait等待任一成功指示器出现
                success = False
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    for indicator in self.ELEMENTS['login']['success_indicators']:
                        try:
                            WebDriverWait(driver, 2).until(
                                EC.presence_of_element_located((By.XPATH, indicator))
                            )
                            success = True
                            break
                        except TimeoutException:
                            continue
                    if success:
                        break
                    time.sleep(0.5)
                
                return success
                    
            return False
        except Exception as e:
            logger.error(f"检查登录状态失败: {str(e)}")
            return False
            
    def get_cookies(self, retry_count=3):
        """获取 cookies 的主函数"""
        retry_count = retry_count or self.BROWSER_CONFIG['retry_count']
        driver = None
        
        try:
            service = Service(EdgeChromiumDriverManager().install())
            options = self.setup_edge_options()
            driver = webdriver.Edge(service=service, options=options)
            
            # 设置页面加载超时
            driver.set_page_load_timeout(self.BROWSER_CONFIG['page_load_timeout'])
            driver.implicitly_wait(self.BROWSER_CONFIG['implicit_wait'])
            
            logger.info('开始获取cookies...')
            driver.get(self.URLS['login_url'])
            
            # 等待页面完全加载
            if not self.wait_for_page_load(driver):
                raise TimeoutException("初始页面加载超时")
            
            # 等待登录表单加载完成
            content_wrapper = self.wait_for_element(
                driver, 
                By.CLASS_NAME, 
                self.ELEMENTS['login']['content_wrapper']
            )
            logger.info('登录页面加载完成')
            
            # 等待输入元素可交互
            username_input = self.wait_for_element_interactable(
                driver,
                By.XPATH,
                self.ELEMENTS['login']['username_input']
            )
            password_input = self.wait_for_element_interactable(
                driver,
                By.XPATH,
                self.ELEMENTS['login']['password_input']
            )
            login_button = self.wait_for_element_interactable(
                driver,
                By.XPATH,
                self.ELEMENTS['login']['login_button']
            )
            
            # 输入凭证（确保元素已清空并输入完成）
            username_input.clear()
            username_input.send_keys(self.credentials['username'])
            WebDriverWait(driver, 5).until(
                lambda d: username_input.get_attribute('value') == self.credentials['username']
            )
            
            password_input.clear()
            password_input.send_keys(self.credentials['password'])
            WebDriverWait(driver, 5).until(
                lambda d: password_input.get_attribute('value') == self.credentials['password']
            )
            
            # 点击登录
            original_url = driver.current_url
            try:
                login_button.click()
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", login_button)
            logger.info('登录中...')
            
            # 等待URL变化和登录成功
            if self.wait_for_url_change(driver, original_url):
                logger.info('URL已变化，检查登录状态...')
                
                if self.check_login_success(driver):
                    logger.info('登录成功')
                    cookies = driver.get_cookies()
                    
                    # 确保目录存在
                    self.cookies_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(self.cookies_path, 'wb') as file:
                        pickle.dump(cookies, file)
                    logger.info('Cookies已保存')
                    
                    return True
                else:
                    logger.error('登录验证失败')
                    return False
            else:
                logger.error('URL未发生预期变化')
                return False
                
        except Exception as e:
            logger.error(f"获取cookies失败: {str(e)}")
            if retry_count > 0:
                logger.info(f"将在 {self.BROWSER_CONFIG['retry_delay']} 秒后重试，剩余重试次数: {retry_count-1}")
                time.sleep(self.BROWSER_CONFIG['retry_delay'])
                return self.get_cookies(retry_count - 1)
            return False
            
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    logger.error(f"关闭浏览器失败: {str(e)}")
                
    def load_cookies(self):
        """加载保存的cookies"""
        try:
            with open(self.cookies_path, 'rb') as file:
                return pickle.load(file)
        except FileNotFoundError:
            logger.info('cookies文件不存在，尝试重新获取')
            if self.get_cookies():
                return self.load_cookies()
            return None

    def cookies_to_dict(self, cookies_list):
        """将cookies列表转换为字典格式"""
        cookies = {}
        for cookie in cookies_list:
            cookies[cookie['name']] = cookie['value']
        return cookies 
    
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 获取 cookies
    auth_manager = AuthManager()
    auth_manager.get_cookies()
    cookies = auth_manager.load_cookies()
    if cookies:
        cookie_dict = auth_manager.cookies_to_dict(cookies)
        print(f"已获取 {len(cookie_dict)} 个cookies")
    else:
        print("无法获取cookies")
