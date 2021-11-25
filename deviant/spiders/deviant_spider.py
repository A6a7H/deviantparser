# -*- coding: utf-8 -*-

from urllib.request import urlretrieve
import errno
import os
import scrapy
import pickle
from deviant.config import *

class DeviantSpider(scrapy.Spider):
    name = "deviant"

    cookies = {}

    def __init__(self):
        self.start_urls = URLS
        self.total_deviations_scraped = 0

        with open("deviant/cookies.pkl", "rb") as f:
            cookies_data = pickle.load(f)
            for i in cookies_data:
                self.cookies[i['name']] = i['value']
            print("Cookies loaded successfully")

        print(self.start_urls)

    def __exit__(self):
        print("Total deviations scraped: %d" % self.total_deviations_scraped)

    def start_requests(self):
        for url in self.start_urls:
            request = scrapy.Request(
                    url.format(0),
                    cookies = self.cookies,
                    callback=self.parse
                    )
            yield request

    def parse(self, response):
        data = response.json()

        keys = response.url.split('?')[1].strip('&').split('&')
        folder_name = f"{keys[0].split('=')[1]}_{keys[-1].split('=')[1]}"
        folder = os.path.join(OUTPUT_FOLDER, folder_name)

        has_more = data["hasMore"]
        next_offset = data["nextOffset"]

        for result in data["results"]:
            url = result["deviation"]["url"]
            yield scrapy.Request(url, cookies=self.cookies, callback=self.parse_deviation, meta={'folder': folder}, dont_filter=False)

        if has_more:
            next_page = response.url.replace(f"offset={next_offset - 24}", f"offset={next_offset}")
            yield scrapy.Request(next_page, cookies=self.cookies)


    def parse_deviation(self, response):
        print ("Parsing deviation:" + response.url)

        folder = response.meta.get('folder', OUTPUT_FOLDER)
        download = response.xpath('//img[@aria-hidden]')

        if not download and "Mature Content" in str(response.body):
            print (response.url + ": Mature Content detected, gonna try to bypass")
            download = response.xpath('//img[@aria-hidden]')
        
        if download:
            download = download[-1].xpath('@src')[0].extract()

            extension = download.split('/')[-1].split('?')[0].split('.')[-1]
            author = response.url.split('deviantart.com/')[-1].split('/')[0]
            filename = author + '_' + response.url.split('/')[-1] + '.' + extension

            try:
                os.makedirs(folder)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

            filepath = os.path.join(folder, filename)

            if not os.path.isfile(filepath):
                urlretrieve(download, filepath)

