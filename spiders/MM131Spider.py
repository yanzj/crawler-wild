# -*- coding: utf-8 -*-

"""
基于 https://github.com/cuanboy/ScrapyProject/tree/master/AoiSolas 二次开发学习实践

"""
import logging
import os
import re
from distutils.log import warn as printf
import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.http import Request, Headers
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exceptions import DropItem, IgnoreRequest
from scrapy.settings import Settings
from scrapy.utils.log import configure_logging
from twisted.internet import reactor

logging.getLogger('scrapy.core.engine').setLevel(logging.ERROR)
logging.getLogger('scrapy.core.scraper').setLevel(logging.ERROR)

UA = 'Mozilla/5.0 (Windows NT 10.0;) Gecko/20100101 Firefox/57.0'


class MM131Spider(scrapy.Spider):

    name = "MM131"
    # allowed_domains = ["www.mm131.com"]

    start_urls = [
        # 'http://www.mm131.com/xinggan/',
        # 'http://www.mm131.com/qingchun/',
        # 'http://www.mm131.com/xiaohua/',
        # 'http://www.mm131.com/chemo/',
        'http://www.mm131.com/qipao/',
        # 'http://www.mm131.com/mingxing/'
    ]

    def parse(self, response):
        """
        列表页，带分页链接
        :param response:
        :return:
        """
        list = response.css(".list-left dd:not(.page)")
        for img in list:
            imgname = img.css("a::text").extract_first()
            imgurl = img.css("a::attr(href)").extract_first()
            imgurl2 = str(imgurl)
            # print imgurl2
            next_url = response.css(".page-en:nth-last-child(2)::attr(href)").extract_first()
            if next_url:
                # 下一页
                yield response.follow(next_url, callback=self.parse, headers={'Referer': response.url, 'User-Agent': UA})

            yield scrapy.Request(imgurl2, callback=self.content, headers={'Referer': response.url, 'User-Agent': UA})

    def content(self, response):
        """
        详细页
        :param response:
        :return:
        """
        item = PictureItem()
        item['name'] = response.css(".content h5::text").extract_first()
        item['img_url'] = response.css(".content-pic img::attr(src)").extract()
        item['headers'] = {
            'Referer': response.url,
            'User-Agent': UA.ch
        }
        store_path = response.url[21: -5]
        if store_path.find('_') > 0:
            store_path = store_path[:store_path.find('_')]

        item['store_path'] = store_path
        printf(item['store_path'])

        yield item

        # 提取图片,存入文件夹
        # print(item['ImgUrl'])
        next_url = response.css(".page-ch:last-child::attr(href)").extract_first()
        if next_url:
            # print 'next_url2: ' + next_url
            # 下一页
            yield response.follow(next_url, callback=self.content, headers={'Referer': response.url, 'User-Agent': UA})


class PictureItem(scrapy.Item):
    name = scrapy.Field()
    img_url = scrapy.Field()
    headers = scrapy.Field()
    image_paths = scrapy.Field()
    store_path = scrapy.Field()


class SpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    def process_request(self, request, spider):
        """
        这里可以进行设置 headers 和切换 Proxy 等处理
        """
        # proxy = '127.0.0.1:8888'
        # request.meta['proxy'] = "http://" + proxy
        # if request.meta and 'headers' in request.meta:
        #     request.headers = Headers(request.meta['headers'])

        printf('【REQUEST】: %s, %s', request.url, request.headers)
        return None


class ImagesPipeline(ImagesPipeline):

    def get_media_requests(self, item, info):
        for image_url in item['img_url']:
            yield Request(image_url, headers=item['headers'], meta={ 'item': item['name'],  'store_path': item['store_path'] })

    def file_path(self, request, response=None, info=None):
        name = request.meta['item']
        store_path = request.meta['store_path']
        name = re.sub(r'[？\\*|“<>:/()0123456789]', '', name)  # 过滤掉特殊字符
        image_guid = request.url.split('/')[-1]
        filename = u'{0}/{1}'.format(store_path, image_guid)
        parent_store_path = info.spider.settings.get('IMAGES_STORE')
        abs_dir_path = os.path.join(parent_store_path, store_path)
        if not os.path.exists(abs_dir_path):
            os.makedirs(abs_dir_path)
            # 写 README
            readme_text_file_path = os.path.join(abs_dir_path, u'{0}.txt'.format(name))
            open(readme_text_file_path, 'w').close()

        if os.path.exists(os.path.join(parent_store_path, filename)):
            printf('Resources already exist ')
            raise IgnoreRequest('Resources already exist ')
        else:
            printf('download ' + filename)

        return filename

    def item_completed(self, results, item, info):
        image_path = [x['path'] for ok, x in results if ok]
        if not image_path:
            raise DropItem('Item contains no images')
        item['image_paths'] = image_path
        return item


if __name__ == '__main__':
    customer_settings = {
        'IMAGES_STORE': 'e:/tmp/MM131',     # 下载图片保存的根路径（确保该目录存在）
        'CONCURRENT_REQUESTS': 40,           # 并发请求数量（具体因网络情况调制合适的值）
        'DOWNLOADER_MIDDLEWARES': {
            'spiders.MM131Spider.SpiderMiddleware': 1,
        },
        'ITEM_PIPELINES': {
            'spiders.MM131Spider.ImagesPipeline': 300,
        },
        'IMAGES_EXPIRES': 30,
        'DOWNLOAD_TIMEOUT': 8000,
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 0,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        },
        'SPIDER_MODULES': ['spiders'],
        'NEWSPIDER_MODULE': 'spiders',
    }
    settings = Settings()
    settings.setdict(customer_settings)
    printf(settings.getdict('DOWNLOADER_MIDDLEWARES'))
    configure_logging(settings)
    runner = CrawlerRunner(settings)
    runner.crawl(MM131Spider)

    # 采集结束后停止事件循环
    d = runner.join()
    d.addBoth(lambda _: reactor.stop())
    # 启动事件循环
    reactor.run()