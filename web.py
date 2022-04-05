from bs4 import BeautifulSoup
import requests

data = requests.get('https://www.ebay.de/sch/i.html?_nkw=lenovo+m92&_udhi=100.00&rt=nc&LH_PrefLoc=1')
soup = BeautifulSoup(data.text, 'html.parser')

# element = soup.find('div', { 'class': 's-item__info clearfix' })
# title = element.find('h3', { 'class': 's-item__title' })
# title_2 = soup.find_all('h3', { 'class': 's-item__title' })


listitems = soup.find_all('li', {'class': 's-item s-item__pl-on-bottom s-item--watch-at-corner'})
# infos = soup.find_all('div', { 'class': 's-item__info clearfix' })

for item in listitems:
    title = item.find('h3', {'class': 's-item__title'})
    price = item.find('span', {'class': 's-item__price'})
    purchase = item.find('span', {'class': 's-item__purchase-options-with-icon'})
    shipping = item.find('span', {'class': 's-item__shipping s-item__logisticsCost'})
    timeleft = item.find('span', {'class': 's-item__time-left'})
    time = item.find('span', {'class': 's-item__time-end'})
    bidCount = item.find('span', {'class': 's-item__bids s-item__bidCount'})
    link = item.find('a', {'class': 's-item__link'})

    # print(title.text, price.text,purchase.text,shipping.text,timeleft.text,time.text,bidCount.text)
    # print(title, price,purchase,shipping,timeleft,time,bidCount)
    float_price = float(price.text[4:].replace(',', '.'))
    if float_price < 100:
        if bidCount is not None:
            print(title.text, price.text, bidCount.text, shipping.text, timeleft.text)
            # this is a new comment on line 34

        else:
            print(title.text, price.text, purchase.text)
        print(link['href'])

# s-item__info clearfix
# print(title_2)

# for tr in tbody.find_all('tr'):
# place = tr.find_all('td')[0].text.strip()

# https://automatetheboringstuff.com/2e/chapter14/
# google spreadsheet integration
# print()
