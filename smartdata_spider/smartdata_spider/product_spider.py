import scrapy
import json
import os

class ProductSpider(scrapy.Spider):
    name = "product_spider"
    start_urls = ['https://example.com/products']

    def parse(self, response):
        products = []
        for product in response.css('div.product'):
            products.append({
                'name': product.css('h2::text').get(),
                'price': product.css('span.price::text').get(),
                'compliance': product.css('span.compliance::text').get(),
            })
        
        # Save data to a JSON file in the spidertest folder on the desktop
        self.save_to_file(products)

        next_page = response.css('a.next::attr(href)').get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)

    def save_to_file(self, products):
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'spidertest')
        file_path = os.path.join(desktop_path, 'products.json')

        with open(file_path, 'w') as f:
            json.dump(products, f, indent=4)

        self.log(f'Data saved to {file_path}')
