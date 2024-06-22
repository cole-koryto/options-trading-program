from config import *
from private_keys import *
from IronCondor import *
import IV_Percentile_Web_Scraper
from td.client import TDClient
from datetime import date, timedelta
import pprint
import fileinput
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager  # pip3 install webdriver_manager

"""
 TD built in analysis uses MARKET price we use LAST price 
"""

# function to check if contract meets minimum delta and slippage
def checkContract(strikeData):
    return LOWEST_DELTA <= abs(float(strikeData[0]['delta'])) <= HIGHEST_DELTA and strikeData[0]['ask'] - strikeData[0][
        'bid'] \
           <= MAX_SLIPPAGE and strikeData[0]['totalVolume'] >= IDEAL_VOLUME and strikeData[0][
               'openInterest'] >= IDEAL_OPEN_INTEREST


# places an iron condor trade
def placeTrade(trade):

    # writes trade details to Trade Log file
    with open("Trade Log.txt", 'a') as outputFile:
        outputString = "%s,%s,%s,%s,%s,%s\n" % (
        str(date.today()), str(trade.putLongStrike['symbol']), str(trade.putShortStrike['symbol']),
        str(trade.callShortStrike['symbol']), str(trade.callLongStrike['symbol']), str(trade.credit))
        outputFile.write(outputString)

    # writes human readable trade details Human Readable Summary Trade Log file
    with open("Human Readable Summary Trade Log.txt", 'a') as outputFile:
        outputString = "%s,%s, Credit: %s, Max Loss: %s, Expected Value: %s, Chance to Win: %s\n" % (
        str(date.today()), str(trade.putLongStrike['symbol']), str(trade.credit), str(trade.maxLoss),
        str(trade.expectedValue), str(trade.chanceToWin))
        outputFile.write(outputString)

    """ TEMPORARY BLOCK """  #todo remove
    print("Adding Credit: " + str(trade.credit))

    # updates cash amount when placing trade
    with open("Cash Status.txt", "r") as inputFile:
        updatedCash = float(inputFile.readline())
        print("Before: " + str(updatedCash))
        with open("Cash Status.txt", "w") as outputFile:
            updatedCash = updatedCash + float(trade.credit)
            outputFile.write(str(updatedCash))
            print("After: " + str(updatedCash))
    """ TEMPORARY BLOCK """

# checks through all current positions and checks if they need to be closed
def checkAllPositions():
    adjustmentsMade = False
    tradesToRemove = []
    with open("Trade Log.txt", 'r+') as inputFile:

        # reads in current data for each running trade
        inputLines = inputFile.readlines()
        tradeCounter = 1
        for line in inputLines:
            tradeDate, putLong, putShort, callShort, callLong, credit = line.split(',')
            putDebit = (td_client.get_quotes(instruments=[putLong])[putLong]['lastPrice'] -
                        td_client.get_quotes(instruments=[putShort])[putShort]['lastPrice']) * 100
            callDebit = (td_client.get_quotes(instruments=[callLong])[callLong]['lastPrice'] -
                         td_client.get_quotes(instruments=[callShort])[callShort]['lastPrice']) * 100
            totalDebit = putDebit + callDebit
            currentProfit = round((float(credit) + totalDebit), 2)
            print("\nChecking position line #" + str(tradeCounter) + ":")
            print("Total debit: " + str(totalDebit))
            print("Max profit, 50%: " + str(credit) + ", " + str(float(credit)/2))
            print("Current profit: " + str(currentProfit))

            # checks if trade meets profitability requirements or is near expiration
            if currentProfit >= float(credit) / 2 or td_client.get_quotes(instruments=[putLong])[putLong][
                'daysToExpiration'] <= 3:
                tradesToRemove.append(tradeCounter)
                adjustmentsMade = True
                print("EXITING TRADE...")

                # writes completed trade stats to file
                with open("Completed Trades.txt", 'a') as outputFile:
                        outputString = "%s,%s,%s,%s,%s, Total Profit: %s, Chance To Win: Null, Original Credit: Null, Max Loss: Null, Expected Value: Null\n" % (
                        tradeDate, putLong, putShort, callShort, callLong, currentProfit)
                        # todo where is trade coming from WRONG VALUES
                        outputFile.write(outputString)

                # updates cash status
                with open("Cash Status.txt", "r") as inputFile:
                    updatedCash = float(inputFile.readline())
                    updatedCash = updatedCash + totalDebit
                with open("Cash Status.txt", "w") as outputFile:
                    outputFile.write(str(updatedCash))

            # increases trade counter
            tradeCounter += 1

    # removes trades from trade log and human readable if they were closed
    if len(tradesToRemove) > 0:
        with open("Trade Log.txt", "r") as fileRead:
            fileLines = fileRead.readlines()
            filePointer = 1
            with open("Trade Log.txt", "w") as fileWrite:
                for line in fileLines:

                    # removes line if it was a trade that has been closed
                    if filePointer not in tradesToRemove:
                        fileWrite.write(line)
                    filePointer += 1
        with open("Human Readable Summary Trade Log.txt", "r") as fileRead:
            fileLines = fileRead.readlines()
            filePointer = 1
            with open("Human Readable Summary Trade Log.txt", "w") as fileWrite:
                for line in fileLines:

                    # removes line if it was a trade that has been closed
                    if filePointer not in tradesToRemove:
                        fileWrite.write(line)
                    filePointer += 1
        print("Closed trades removed from logs")

            # prints to console if no trade adjustments were made
    if not adjustmentsMade:
        print("No adjustments made to current positions")


# converts any option symbol to a string date SYMBOLMMDDYY
def optionSymbolToKey(symbol):
    tempDate = symbol.split('_')[1]
    if tempDate.find('P') != -1:
        tempDate = tempDate.split('P')[0]
    elif tempDate.find('C') != -1:
        tempDate = tempDate.split('C')[0]
    tempDate = symbol.split('_')[0] + tempDate
    return tempDate


# runs the code for the auto options trader
if __name__ == "__main__":

    # creates new instances of TD client and logs in
    td_client = TDClient(client_id=CONSUMER_KEY, redirect_uri=REDIRECT_URI, credentials_path=JSON_PATH)
    td_client.login()
    print("Logged in to TD Client ...")

    # sets up main selenium driver
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.minimize_window()
    
    # gets IV percentile for each symbol and checks if it meets threshold
    viableSymbols = []
    for symbol in fileinput.input("symbols_list"):
        symbol = symbol.replace('\n', '')
        IVPercentile = IV_Percentile_Web_Scraper.runIVPerScraper(symbol, driver)
        if MIN_IV_PERCENT <= IVPercentile <= MAX_IV_PERCENT:
            print(symbol + " IV %: " + str(round(IVPercentile * 100, 2)) + "% Good IV %")
            viableSymbols.append(str(symbol))
        else:
            print(symbol + " IV %: " + str(round(IVPercentile * 100, 2)) + "% IV % too low")
    driver.quit()
    print("Checked stock's IV percentile ...")

    # calculates expiration dates 30 and 60 days out
    close_expiration = date.today() + timedelta(days=DAYS_OUT_MIN)
    far_expiration = date.today() + timedelta(days=DAYS_OUT_MAX)

    # makes all possible viable iron condor trades given the set of viable equity symbols
    for equity in viableSymbols:
        print("\n*** Checking " + equity + " ***\n")

        # gets option chain for equity
        option_chain_dict = {
            'symbol': equity,
            'contractType': 'ALL',
            'optionType': 'S',
            'range': 'ALL',
            'fromDate': close_expiration.strftime('%Y-%m-%d'),
            'toDate': far_expiration.strftime('%Y-%m-%d')
        }
        options_data = td_client.get_options_chain(option_chain=option_chain_dict)
        # pprint.pprint(options_data['callExpDateMap'])

        # gets current price quote
        currentQuote = td_client.get_quotes(instruments=[equity])[equity]['lastPrice']

        """ 
        finds the liquid option expiration ranges by checking at the money strike open interest and volume on call side, then
        if liquid call expiration is found, the put expiration is checked, if also valid, expiration is added to list
        """
        liquidExpirations = []
        previousStrike = ''
        for optionDate, strikeList in options_data['callExpDateMap'].items():
            # pprint.pprint(strikeList)
            print("Checking expiration: " + str(optionDate))
            for strike, strikeData in strikeList.items():
                # pprint.pprint(strikeData)
                # if strikeData[0]['inTheMoney'] == False:
                    # print(optionDate + str(strikeData[0]['openInterest']) + " " + str(strikeData[0]['totalVolume']))
                if strikeData[0]['inTheMoney'] == False and strikeData[0]['openInterest'] >= MIN_OPEN_INTEREST and \
                        strikeData[0]['totalVolume'] >= MIN_VOLUME:
                    # checks if put size is also liquid
                    if options_data['putExpDateMap'][optionDate][previousStrike][0]['openInterest'] >= MIN_OPEN_INTEREST and \
                            options_data['putExpDateMap'][optionDate][previousStrike][0]['totalVolume'] >= MIN_VOLUME:
                        print("Adding LIQUID expiration: " + optionDate)
                        liquidExpirations.append(optionDate)
                        break
                elif strikeData[0]['inTheMoney'] == False:
                    print("At the money option ILLIQUID: ")
                    print("Volume: " + str(strikeData[0]['totalVolume']))
                    print("Open interest: " + str(strikeData[0]['openInterest']))
                    break
                previousStrike = strike
        if len(liquidExpirations) == 0:
            print("No liquid expirations found for " + equity)
            continue

        print("Acquired most liquid expirations ...")
        # pprint.pprint(liquidExpirations)

        # makes list of short call and put strikes with delta between LOWEST_DELTA and HIGHEST_DELTA and with MAX_SLIPPAGE or less and finds their long pair with 5 width
        IronCondorList = []
        for optionDate in liquidExpirations:
            callShortStrikes = {}
            callLongStrikes = {}
            putShortStrikes = {}
            putLongStrikes = {}

            # goes through calls in liquid expirations and
            for strike, strikeData in options_data['callExpDateMap'][optionDate].items():
                # pprint.pprint(options_data['callExpDateMap'][optionDate])
                if float(strike) - float(int(float(strike))) != 0.0:
                    print("Unexpected floating point strike found: " + strike + " on " + equity)
                    continue
                if checkContract(strikeData):
                    # print("Short call strike is good: " + strike)
                    if str(float(strike) + IRON_CONDOR_WIDTH) in options_data['callExpDateMap'][optionDate]:
                        # print("Adding short call strike: " + strike)
                        callShortStrikes[strikeData[0]['symbol']] = strikeData[0]
                        # print("Adding long call strike: " + str(float(strike) + IRON_CONDOR_WIDTH))
                        longCallSymbol = equity + "_" + optionDate[5:7] + optionDate[8:10] + optionDate[2:4] + "C" + str(int(float(strike) + IRON_CONDOR_WIDTH))
                        callLongStrikes[longCallSymbol] = options_data['callExpDateMap'][optionDate][str(int(float(strike) + IRON_CONDOR_WIDTH)) + ".0"][0]

            # goes through puts in liquid expirations
            for strike, strikeData in options_data['putExpDateMap'][optionDate].items():
                if float(strike) - float(int(float(strike))) != 0.0:
                    print("Unexpected floating point strike found: " + strike + " on " + equity)
                    continue
                # pprint.pprint(options_data['putExpDateMap'][optionDate][strike])
                if checkContract(strikeData):
                    # print("Short put strike is good")
                    if str(float(strike) - IRON_CONDOR_WIDTH) in options_data['putExpDateMap'][optionDate]:
                        # print("Adding short put strike: " + strike)
                        putShortStrikes[strikeData[0]['symbol']] = strikeData[0]
                        # print("Adding long put strike: " + str(float(strike) - IRON_CONDOR_WIDTH))
                        longPutSymbol = equity + "_" + optionDate[5:7] + optionDate[8:10] + optionDate[2:4] + "P" + str(int(float(strike) - IRON_CONDOR_WIDTH))
                        putLongStrikes[longPutSymbol] = options_data['putExpDateMap'][optionDate][str(int(float(strike) - IRON_CONDOR_WIDTH)) + ".0"][0]
            print("Call and put spreads made ...")

            # raises exception if call or put spread pairs are not even
            if len(callShortStrikes) != len(callLongStrikes) or len(putShortStrikes) != len(putLongStrikes):
                print("Error: call or put spread pairs are not even")
                continue

            # creates iron condor trades by pairing each call pair with a put pair, calculates their expected value, and adds them to the list
            for i in range(len(callShortStrikes)):
                key, value = list(callShortStrikes.items())[i]
                newCShortDic = value
                key, value = list(callLongStrikes.items())[i]
                newCLongDic = value
                for j in range(len(putShortStrikes)):
                    key, value = list(putShortStrikes.items())[j]
                    newPShortDic = value
                    key, value = list(putLongStrikes.items())[j]
                    newPLongDic = value
                    # print("Pairing: " + newCShortDic['symbol'] + " " + newPShortDic['symbol'])
                    newIronCondor = IronCondor(newPLongDic, newPShortDic, newCShortDic, newCLongDic)
                    newIronCondor.calcExpectedValue()
                    IronCondorList.append(newIronCondor)

        # sorts iron condor trades by highest expected value
        IronCondorList.sort(key=lambda trade: trade.expectedValue, reverse=True)
        print("Iron Condors made and sorted by highest expected value ...")

        """
        print(repr(IronCondorList[0]) + "\n" + "Exp Value: " + str(IronCondorList[0].expectedValue))
        print("Put Long: ")
        pprint.pprint(IronCondorList[0].putLongStrike)
        print("Put Short: ")
        pprint.pprint(IronCondorList[0].putShortStrike)
        print("Call Short: ")
        pprint.pprint(IronCondorList[0].callShortStrike)
        print("Call Long: ")
        pprint.pprint(IronCondorList[0].callLongStrike)
        """

        for trade in IronCondorList:
            print(repr(trade) + "\n" + "Exp Value: " + str(trade.expectedValue))

        # gets amount of funds available for trading
        # cashAvailableForTrading = td_client.get_accounts()[0]['securitiesAccount']['currentBalances']['cashAvailableForTrading']
        """ TEMPORARY BLOCK """
        with open("Cash Status.txt") as fileIn:
            cashAvailableForTrading = float(fileIn.readline())
        """ TEMPORARY BLOCK """
        print("Cash for trading: " + str(cashAvailableForTrading))

        # takes the list of current trades to check that potential new trade is not in same expiration
        currentTradeKeys = []
        with open("Trade Log.txt", 'r+') as inObj:
            inputLines = inObj.readlines()
            for line in inputLines:
                tradeDate, putLong, putShort, callShort, callLong, credit = line.split(',')
                currentTradeKeys.append(optionSymbolToKey(putLong))

        # makes the highest expected value trade under max trade size

        if len(IronCondorList) == 0:
            print("No new trades to make")
        for trade in IronCondorList:

            # stops checking trades when there are none left with positive expected value
            print("Checking trade: " + str(trade.expectedValue))
            if trade.expectedValue < 0:
                print("No more possible trades with positive expected value")
                break

            # checks if trade can fit portfolio and that the potential trade has not already been made in this expiration
            if trade.maxLoss <= cashAvailableForTrading * MAX_TRADE_SIZE_PERCENT:
                if optionSymbolToKey(trade.putLongStrike['symbol']) in currentTradeKeys:
                    print("Trade already made for this symbol in this expiration")
                else:
                    placeTrade(trade)
                    print("TRADE MADE: " + repr(trade))
                    break

    # checks if any trades should be exited (50% profit+ or 3 days or less to expiration)
    checkAllPositions()

# todo
""" fix cash on hand """
