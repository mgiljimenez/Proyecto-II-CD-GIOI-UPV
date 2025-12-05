from curl_cffi import requests
import re
import json
import html
import logging
from time import sleep
from urllib.parse import urljoin
from camoufox.sync_api import Camoufox
from parsel import Selector
import os

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S', filename=os.path.join(os.path.dirname(__file__), "log6.log"
    ))

class InfoJobs:
    def __init__(self, job_type_search=None):
        self.base_url = "https://www.infojobs.net/jobsearch/search-results/list.xhtml"
        self.api_base_url = "https://www.infojobs.net/webapp/offers/search?keyword=KEYWORD&searchByType=country&segmentId=&page=PAGE_ID&sortBy=PUBLICATION_DATE&onlyForeignCountry=false&countryIds=17&sinceDate=ANY"
        self.cookie = None
        self.session = requests.Session()
        self._max_page_id = 3350 # máximo de páginas harcodeado por si extracción falla
        self._general_jobs = []
        self._general_jobs_failed = [] # Lista para guardar las ofertas que den error al extraer
        self._specific_job = {}
        self.max_retry_limit = 5

        # 1. Extraer todas las ofertas
        # self.extract_general_jobs(job_type_search)
        # 2. Para cada oferta extraída: extraer detalles de oferta
        # self.extract_specific_job()

    def extract_general_jobs(self, job_type_search):
        """Extraer todas las ofertas: append en self._general_jobs la información general de cada puesto incluyendo su URL"""
        if not job_type_search:
            job_type_search = ""

        url = self.api_base_url.replace('KEYWORD', job_type_search).replace("PAGE_ID", "0")
        response = self.get_response(url)
        # Exraer ofertas de la primer página
        try:
            jobs = response.json()['offers']
        except Exception as e:
            jobs = []
            logger.warning(f"Error en extracción General de ofertas página 1: {str(e)}")
        for job in jobs:
            job['link'] = urljoin(self.base_url, job['link'])
            self._general_jobs.append(job)

        # Sacar el número total de páginas existentes
        try:
            max_page_id = response.json()['navigation']['totalPages']
            # max_page_id = 3000 # Para harcodear
            logger.info(f"totalPages: {max_page_id}")
        except Exception as e:
            max_page_id = self._max_page_id
            logger.warning(f"extracción de totalPages error: {str(e)}. using _max_page_id: {self._max_page_id}")

        # Extraer todas las ofertas
        for i in range(1, max_page_id+1):
            url = self.api_base_url.replace('KEYWORD', job_type_search).replace("PAGE_ID", str(i))
            response = self.get_response(url)
            try:
                jobs = response.json()['offers']
            except Exception as e:
                jobs = []
                logger.warning(f"Error en extracción General de ofertas página {i}. error: {str(e)}")

            for job in jobs:
                # Update Link a URL absoluta
                job['link'] = urljoin(self.base_url, job['link'])
                self._general_jobs.append(job)

    def extract_specific_job(self):
        # Obtener y usar cookies 
        self.set_cookies()
        """Para cada oferta, extraer información adicional de cada JobUrl: html que contiene JSON estructurado en window.__INITIAL_PROPS__"""
        n = 0
        total = len(self._general_jobs)
        for job in self._general_jobs:
            logger.info(f"{n} de {total}")
            job_url = job.get("link")
            try:
                response = self.get_response(job_url)
                if response:
                    sel = Selector(text=response.text)
                    # Sacar el JSON con los datos de la oferta
                    initial_props = sel.xpath('//script[starts-with(text(), "window.__INITIAL_PROPS__ = JSON.parse")]').extract_first("")
                    if initial_props:
                        try:
                        # Extraer JSON contenido en:
                            match = re.search(r'JSON\.parse\("(.+?)"\)\s*;', initial_props, re.DOTALL)
                            raw_json = html.unescape(match.group(1))
                            json_data = json.loads(json.loads(f'"{raw_json}"'))
                            self._specific_job[job.get("code")] = json_data
                            n+=1
                        except Exception as e:
                            self._general_jobs_failed
                            logger.warning(f"Error en extracción del JSON para oferta: {job_url} con error: {str(e)}")
                    else:
                        self._general_jobs_failed
                        logger.warning(f"Error en extracción del JSON para oferta: {job_url}")
            except:
                continue
        return self._specific_job

    def set_cookies(self):
        """Extraer cookies necesarias de infojobs haciendo uso de Camoufox"""
        self.session = requests.Session()
        with Camoufox(headless=True, os=["windows", "macos", "linux"], geoip=True) as browser:
            context = browser.new_context()
            page = context.new_page()
            def get_cookies(response):
                cookies = context.cookies()
                if 'reese84' in [cookie['name'] for cookie in cookies]:
                    self.cookie = next((c['value'] for c in cookies if c.get('name') == 'reese84'), None)

                    for c in cookies:
                        if "infojobs.net" in c.get("domain", ""):
                            name, value, domain, path = (
                                c.get("name"), c.get("value"),
                                c.get("domain", ".infojobs.net").lstrip("."), c.get("path", "/")
                            )
                            self.session.cookies.set(name, value, domain=domain, path=path)

            page.on("response", get_cookies)
            page.goto(self.base_url)
            if self.cookie:
                logger.info(f"Encontrado reese84: {self.cookie} cookie de infojobs")
            browser.close()

    def get_response(self, url):
        # Headers for general job requests
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'portalid': '0',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'x-adevinta-channel': 'web',
            'x-schibsted-tenant': 'infojobs'
        }

        # Headers for specific job requests
        headers1 = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-GB,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'upgrade-insecure-requests': '1',
            # 'cookie': f"reese84={self.cookie}",
            # 'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }
        if "/webapp/offers/search" not in url:
            headers = headers1

        proxies = {
            # sustituir por proxie válido
        }
        
        """Bucle para reintentar extracción self.max_retry_limit veces"""
        failure_counter = 0
        while True:
            logger.info(f"Procesando: {url}")
            try:
                response = self.session.get(url, headers=headers, proxies=proxies, impersonate="chrome120",)
                if response.status_code == 200:
                    if 'No podemos identificar tu navegador' in response.text:
                        logger.warning(f"Request Error: {failure_counter} vecez con error: cookie falló. Reintentando...")
                        failure_counter += 1
                        self.set_cookies()
                        if failure_counter == self.max_retry_limit:
                            response = None
                            break
                    else:
                        return response
                else:
                    logger.warning(f"Request Error: {failure_counter} vecez con error: {response.status_code}. Reintentando...")
                    failure_counter += 1
                    self.set_cookies()
            except Exception as e:
                logger.warning(f"Request Error: {failure_counter} vecez con error: {str(e)}. Reintentando...")
                response = None
                failure_counter += 1
                self.set_cookies()
            if failure_counter == self.max_retry_limit:
                break
        return response