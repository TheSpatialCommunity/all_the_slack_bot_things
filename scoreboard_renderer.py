import json, sys
from decimal import Decimal


SAMPLE_SCORE = [('@savagemat', Decimal(2147481970)), ('@robodonut', Decimal(637)), ('@johnny', Decimal(600)), ('other-daniel', Decimal(500)), ('@msavage', Decimal(300.0))]

class scoreboardObj(object):

    def __init__(self, title=None):
        self.fallback = "Required plain-text summary of the attachment."
        self.color = "#36a64f"
        self.author = "Score Board"
        self.title=title
        self.fields = []

    def setTitle(self):
        self.title += " {0}".format(self.returnCount())

    def returnCount(self):
        length = int(len(self.fields) / 2)

        return length

def returnScoreboard(scoreList=None,title=None):
    data = scoreboardObj(title=title)

    for i, item in enumerate(scoreList):
        user, score = item
        score = str(int(score))

        userDict = {"value": user, "short":True}
        scoreDict = {"value": score, "short":True}

        if i == 0:
            userDict["title"] = "User"
            scoreDict["title"] = "Score"

        data.fields.append(userDict)
        data.fields.append(scoreDict)

    data.setTitle()

    return data

def renderBitch(score):
    data = returnScoreboard(scoreList=score, title="Top")
    jsonData = json.dumps(data.__dict__)
    return data.__dict__

if __name__ == "__main__":
    renderBitch(sys.argv[1])
