import urllib.request
import re
import json

url = 'https://www.autoscout24.at/lst/bmw/320?atype=C&cy=A&damaged_listing=exclude&desc=0&powertype=kw&sort=price&ustate=N%2CU&custtype=D'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    with open('test_autoscout.html', 'w', encoding='utf-8') as f:
        f.write(html)
    prices = re.findall(r'data-price="(\d+)"', html)
    if not prices:
        prices = re.findall(r'"price":(\d+)', html)
    print('Prices:', prices[:10])
except Exception as e:
    print('Error:', e)
