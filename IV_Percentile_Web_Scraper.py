from bs4 import BeautifulSoup


# sets up all needed object to scrape Market Chameleon for IV Percentile data
def runIVPerScraper(symbol, driver):
    # loads the contents of the page into BeautifulSoup
    symbol = symbol.upper()
    targetURL = "https://www.barchart.com/stocks/quotes/" + symbol + "/overview"
    driver.get(targetURL)
    pageContent = driver.page_source
    soup = BeautifulSoup(pageContent, features="html.parser")

    # gets IV rank content from page by looking for 'IV Percentile' and returns it
    IVRankElement = ""
    for tableElement in soup.find_all(attrs={'class': 'left'}):
        if tableElement.contents[0] == 'IV Percentile':
            percentStr = tableElement.find_next("span").contents[0].replace('%', '')
            return int(percentStr) / 100

    # raises exception in case of error
    raise Exception("No IV percentile could be found for " + symbol)
