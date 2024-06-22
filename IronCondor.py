class IronCondor:
    putLongStrike = {}
    putShortStrike = {}
    callShortStrike = {}
    callLongStrike = {}
    strikePrices = {}
    expiration = None       # stored in Epoch & Unix Timestamp, go to https://www.epochconverter.com/ to convert
    expectedValue = None
    credit = None
    maxLoss = None
    chanceToWin = None

    # initializes an Iron Condor with given calls and puts
    def __init__(self, putLongStrike, putShortStrike, callShortStrike, callLongStrike):
        self.putLongStrike = putLongStrike
        self.putShortStrike = putShortStrike
        self.callShortStrike = callShortStrike
        self.callLongStrike = callLongStrike
        self.parseStrikePrice()
        self.expiration = callShortStrike['expirationDate']

    # calculates the expected value of the iron condor
    def calcExpectedValue(self):
        putCredit = (self.putShortStrike['last'] - self.putLongStrike['last']) * 100
        callCredit = (self.callShortStrike['last'] - self.callLongStrike['last']) * 100
        totalCredit = putCredit + callCredit
        maxWidth = max(int(self.strikePrices['putShort']) - int(self.strikePrices['putLong']), int(self.strikePrices['callLong']) - int(self.strikePrices['callShort'])) * 100
        maxLoss = maxWidth - totalCredit
        chanceToLose = self.callShortStrike['delta'] + abs(self.putShortStrike['delta'])
        chanceToWin = 1 - chanceToLose
        expectedValue = totalCredit * chanceToWin - maxLoss * chanceToLose
        self.expectedValue = round(expectedValue, 3)
        self.credit = round(totalCredit, 3)
        self.maxLoss = round(maxLoss, 3)
        self.chanceToWin = chanceToWin
        return expectedValue

    # function to convert iron condor object to string
    def __repr__(self):
        return "Iron Condor: \n" + "Long Put: " + self.putLongStrike['symbol'] + " Short Put: " + \
               self.putShortStrike['symbol'] + " Short Call: " + self.callShortStrike['symbol'] + " Long Call: " + self.callLongStrike['symbol']

    # parses strike price from symbol name
    def parseStrikePrice(self):
        tempStrike = self.callShortStrike['symbol'].split('_')[-1]
        tempStrike = tempStrike[7:]
        self.strikePrices['callShort'] = tempStrike

        tempStrike = self.callLongStrike['symbol'].split('_')[-1]
        tempStrike = tempStrike[7:]
        self.strikePrices['callLong'] = tempStrike

        tempStrike = self.putShortStrike['symbol'].split('_')[-1]
        tempStrike = tempStrike[7:]
        self.strikePrices['putShort'] = tempStrike

        tempStrike = self.putLongStrike['symbol'].split('_')[-1]
        tempStrike = tempStrike[7:]
        self.strikePrices['putLong'] = tempStrike
