from datetime import datetime
import mysql.connector, requests
from flask import Flask
from flask_slack import Slack
from flask_slack import SlackError
from slackclient import SlackClient
from random import randint
from threading import Thread
from flask import jsonify
import random
import fnmatch

from scoreboard_renderer import renderBitch
app = Flask(__name__)

email_blacklist = ['vivi@slackfu.com']

slack = Slack(app)
app.add_url_rule('/', view_func=slack.dispatch)
#gisdevs points xxxx team_id = 'xxxx'
#the spatial ones flaskpaw xxxx team_id='xxxx'
@slack.command('points', token='xxxx',
               team_id='xxxx', methods=['POST'])
def your_method(**kwargs):
    #get the kwargs
    text = kwargs.get('text')
    user_name = kwargs.get('user_name')
    user_id = kwargs.get('user_id')
    channel = kwargs.get("channel_name")
    channelID = kwargs.get("channel_id")
    responseURL = kwargs.get("response_url")
    #parse the natural language text kwarg and
    #deal with the returned dictionary.
    #dictionary keys dictate the action
    parameters = parse_validate_text_kwarg(text)
    _response_type = 'ephemeral'
    _attachments = ''
    for key in parameters:
        if key == "help":
            response_payload = return_help()[0]
        elif key == "points":
            response_payload = add_points(user_name,parameters[key][0],channel,parameters[key][1],parameters[key][2])
            _response_type = 'in_channel'
        elif key == "stats":
            response_payload= stat_query(parameters[key],user_name)
            _attachments = [renderBitch(response_payload)]
            response_payload=""
            print(_attachments)
        elif key == "error":
            response_payload = parameters[key]
        elif key == "rain":
            points = parameters[key]
            makeItRain(user_name,channelID,points,user_id,responseURL)
            response_payload = "And {0} makes it rain!!! http://i.giphy.com/y8Mz1yj13s3kI.gif".format(user_name)
            _response_type = 'in_channel'
        else:
            response_payload = "super crazy shit. call the Doctor"
    #final response from slack
    return slack.response(response_payload,response_type=_response_type,attachments=_attachments)
    #return slack.response("this is text")


# new natural language parameter parsing function
def parse_validate_text_kwarg(text):
    args_from_text = text.split(" ")
    args_from_text[2:]= [" ".join(args_from_text[2:])]
    if args_from_text[0] in ['me','top_5','low_5','givers','lasers','takers']:
        # found a valid statistic request return it
        return {"stats":args_from_text[0]}
    elif args_from_text[0].find("@",0)==0:
        #found an @ in the first position of the first split arg,
        #probably point allocation. test the 2nd arg for intiger correct if out
        #of bounds
        try:
            points = int(args_from_text[1])
            if points >100:
                points=100
            elif points < -100:
                points = -100
            else:
                points = points
        except:
            return {"error":"{0} is not a number Python can convert to an integer...Use /points ? for help....This is kinda awkward...".format(args_from_text[1])}
        getter = args_from_text[0]
        points = points
        reason = args_from_text[2]
        return {"points":[getter,points,reason]}
    elif args_from_text[0] in ["help","-h","?"]:
        return {"help":0}
    elif args_from_text[0] == "makeItRain":
        #Oooo someone is generious, found makeitrain in the first position of the first split arg,
        #test the 2nd arg for intiger correct if out
        #of bounds
        try:
            points = int(args_from_text[1])
            if points >100:
                points=100
            elif points < -100:
                points = -100
            else:
                points = points
        except:
            return {"error":"{0} is not a number Python can convert to an integer...Use /points ? for help....This is kinda awkward...".format(args_from_text[1])}
        return {"rain": points}
    else:
        # return a fuck you for trying to be a dick.
        return {"error":"ERROR: Parameters invalid please check your input:{0}. Use /points ? for help".format(text)}

#return help
def return_help():
    return ["/points @username(user to give points to) 50(points to give,"+
            "100 - -100) reason(optional)\n " +
            "/points me(your score)\n"+
            "/points top_5 (top 5 on the scoreboard)\n"+
            "/points low_5 (low 5 on the scoreboard)\n"+
            "/points givers (top 5 givers scoreboard)\n"+
            "/points takers (top 5 takers scoreboard)\n"]

#statistic functions
def stat_query(stat,user_name):
    # connect to database, determine the query to run, run that shit, return the rows.
    # NEED TO FORMAT THE RESPONSE AS AN ATTACHMENT. LOOK AT THE FIELDS ATTACHMENT PARAMETER IN THE SLACK API
    try:
        cnx = mysql.connector.connect(user='xxxx', password='xxxx', host ='xxxx', database='xxxx')
        cursor = cnx.cursor()
    except Exception as e:
        return "Error connecting to the SEGA database. " + str(e)
    if stat == "me":
        # return the me query.
        cursor.execute('select getter, sum(points) as points from points_raw where getter = "@{0}";'.format(user_name))
        #return "me stat"
    elif stat == "top_5":
        #return the top_5 query
        cursor.execute('select getter, sum(points) as points from points_raw where getter <> "@robodonut" group by getter order by points DESC limit 5;')
    elif stat == "low_5":
        #return the low 5 query
        cursor.execute('select getter, sum(points) as points from points_raw group by getter order by points ASC limit 5;')
    elif stat == "givers":
        #return the top 5 givers query
        cursor.execute('select giver, sum(points) as points from points_raw where points >0 group by giver order by points DESC limit 5;')
    elif stat == "takers":
        #return the low 5 givers query
        cursor.execute('select giver, sum(points) as points from points_raw where points <0 group by giver order by points ASC limit 5')
    elif stat == "lasers":
        return "http://i.giphy.com/xhbBLTLh9Ep8Y.gif"
    else:
        return "Crazy stats shit whent down"
    query_results = cursor.fetchall()
    cnx.commit()
    cnx.close()
    return query_results

#insert row containing points into database
def add_points(giver, getter, channel, points,reason):
    if points <0:
        verb = "deprived"
        verb2 = "of"
    elif points > 0:
        verb = "awarded"
        verb2 = ""
    else:
        return "https://www.youtube.com/watch?v=LQCU36pkH7c&feature=youtu.be&t=4s"
        #return "https://www.youtube.com/watch?v=M5QGkOGZubQ"
    if ("@"+giver) == getter:
        points = abs(points)*-1
        verb = "deprived"
        verb2 = "of"
    else:
        pass
    try:
        cnx = mysql.connector.connect(user='xxxx',
                              password='xxxx',
                              host ='xxxx',
                              database='xxxx')

        add_raw = ("INSERT INTO points_raw "
                    " (ID, giver, getter, channel_name, time, points, reason)"
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)")
        payload = (1,giver,getter,channel,datetime.now(),points, reason)
        cur = cnx.cursor()
        cur.execute(add_raw,payload)
        cnx.commit()
        cnx.close()
        return "{0} has {1} {2} {3} {4} points".format(giver,verb,getter,verb2,abs(points))
    except Exception as e:
        return "Sorry, I can't add points right now. " + str(e)

def async(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()
    return wrapper

@async
def makeItRain(giver,channelID,points,user_id,responseURL):
    with app.app_context():
        token = "xxxx"
        sc = SlackClient(token)
        #sc.api_call("channels.info", channel=channelID)
        memberIDs = sc.api_call("channels.info", channel=channelID)['channel']['members']
        memberIDs.remove(user_id)
        points_array = moneyOnTheFloor(len(memberIDs),points)
        memberNames = ["@"+ sc.api_call("users.info",user = x)['user']['name'] for x  in memberIDs]
        #getter ="@"+sc.api_call("users.info",user = member)['user']['name']
        member_points_list = list(zip([1]*len(memberIDs),[giver]*len(memberIDs),memberNames,[channelID]*len(memberIDs),
                                    [datetime.now()]*len(memberIDs), points_array,["rain"]*len(memberIDs)))
        cnx = mysql.connector.connect(user='xxxx',
                                  password='xxxx',
                                  host ='xxxx',
                                  database='xxxx')

        add_raw = ("INSERT INTO points_raw "
                    " (ID, giver, getter, channel_name, time, points, reason)"
                    "VALUES (%s,%s,%s,%s,%s,%s,%s)")
        payload = member_points_list
        cur = cnx.cursor()
        cur.executemany(add_raw,payload)
        cnx.commit()
        cnx.close()
        #precipitate(member_points_list)
        #member_points_dict = dict(zip(memberIDs, points_array,))
        # we'll
        #for member in member_points_dict:
            #print(member)
            #getter ="@"+sc.api_call("users.info",user = member)['user']['name']
            #add_points(giver,getter,channelID,member_points_dict[member],"")
        #requests.post(responseURL, data = {"And {0} makes it rain!!! http://i.giphy.com/y8Mz1yj13s3kI.gif".format(giver),response_type="in_channel"})
        #return "And {0} makes it rain!!! http://i.giphy.com/y8Mz1yj13s3kI.gif".format(giver)

def moneyOnTheFloor(n, r):
    numbers = list()
    h = r
    while (h != 0):
        x = randint(0,h)
        numbers.append(x)
        h = h-x
    y = n - len(numbers)
    for i in range(y):
        numbers.append(0)
    return numbers

@slack.command('channels', token='xxxx',
               team_id='xxxx', methods=['POST'])
def channelGlob(**kwargs):
    '''
    Example of intended use:
    /channels loc-*
    #loc-africa (50 members)
    #loc-australia (43 members)

    https://api.slack.com/methods/channels.list
    https://api.slack.com/types/channel
    '''
    user_glob = kwargs.get('text')
    token = 'xxxx'
    bot_username = 'channel_globber'
    params = {
        'token': token,
        'exclude_archived': True,
        'exclude_members': True
    }
    channels_response = requests.get("https://slack.com/api/channels.list", params=params)
    if channels_response["ok"] != True:
        return slack.response("Globbiddy glob error, tell an admin?", response_type='ephemeral')
    channels_response['channels'] = fnmatch.filter(channels_response['channels'], user_glob)
    if len(channels_response['channels']) <= 0:
        # No channels match
        _response_type = 'ephemeral'
        response_payload = "Sorry, no channels match {glob}".format(glob=user_glob)
    else:
        # Got at least one channel
        # Sort them based on membership
        channels_response['channels'].sort(key=lambda c: c['num_members'], reverse=True)
        _response_type = 'in_channel'
        if len(channels_response) <= 5:
            # Short list
            format_func = lambda c: "#{channel} – {purpose} ({n} member{s})".format(channel=c['name'], purpose=c.get('purpose', {}).get('value', '🌍'), n=c['num_members'])
        else:
            # Longer list
            format_func = lambda c: "#{channel} ({n} member{s})".format(channel=c['name'], n=c['num_members'])
        response_payload = map(format_func, channels_response['channels']).join('\n')
    return slack.response(response_payload, response_type=_response_type)

@slack.command('tteesstt', token='xxxx',
               team_id='xxxx', methods=['POST'])
def bum(**kwargs):
    #get the kwargs
    text = kwargs.get('text')
    user_name = kwargs.get('user_name')
    user_id = kwargs.get('user_id')
    channel = kwargs.get("channel_name")

    #parse the natural language text kwarg and
    #deal with the returned dictionary.
    #dictionary keys dictate the action
    parameters = parse_validate_text_kwarg(text)
    _response_type = 'ephemeral'
    return slack.response("its working",response_type=_response_type)
    for key in parameters:
        if key == "help":
            response_payload = return_help()[0]
        elif key == "points":
            response_payload = add_points(user_name,parameters[key][0],channel,parameters[key][1],parameters[key][2])
            _response_type = 'in_channel'
        elif key == "stats":
            response_payload= stat_query.renderBitch(parameters[key],user_name)
        elif key == "error":
            response_payload = parameters[key]
        else:
            response_payload = "super crazy shit. call the Doctor"
    #final response from slack

    #return slack.response("this is text")

@slack.command('badgers', token='xxxx',
               team_id='xxxx', methods=['POST'])
def bum(**kwargs):
    #get the kwargs
    text = kwargs.get('text')
    user_name = kwargs.get('user_name')
    user_id = kwargs.get('user_id')
    channel = kwargs.get("channel_name")

    #parse the natural language text kwarg and
    #deal with the returned dictionary.
    #dictionary keys dictate the action
    parameters = parse_validate_text_kwarg(text)
    _response_type = 'ephemeral'
    return slack.response("https://www.youtube.com/watch?v=gx6TBrfCW54&feature=youtu.be&t=16s",response_type="in_channel")

@slack.command('thumbsup', token='xxxx',
               team_id='xxxx', methods=['POST'])
def sl4(**kwargs):
    return slack.response("https://imgur.com/uKL8tJg.gif",response_type='in_channel')

@slack.command('believe', token='xxxx',
               team_id='xxxx', methods=['POST'])
def sl5(**kwargs):
    return slack.response("https://youtu.be/YLO7tCdBVrA?t=2s",response_type='in_channel')

@slack.command('hi', token='xxxx',
               team_id='xxxx', methods=['POST'])
def sl6(**kwargs):
    return slack.response("https://media.giphy.com/media/SYhK02vJMUeL6/giphy.gif",response_type='in_channel')




@slack.command('deepthoughts', token='xxxx',
               team_id='xxxx', methods=['POST'])
def sl7(**kwargs):
    quotes = [
    "When you're riding in a time machine way far into the future, don't stick your elbow out the window, or it'll turn into a fossil.",
    "If you were a pirate, you know what would be the one thing that would really make you mad? Treasure chests with no handles. How the hell are you supposed to carry it?!",
    "Better not take a dog on the space shuttle, because if he sticks his head out when you're coming home his face might burn up.",
    "If you're a horse, and someone gets on you, and falls off, and then gets right back on you, I think you should buck him off right away.",
    "If a kid asks where rain comes from, I think a cute thing to tell him is \"God is crying.\" And if he asks why God is crying, another cute thing to tell him is \"Probably because of something you did.",
    "The first thing was, I learned to forgive myself. Then, I told myself, \"Go ahead and do whatever you want, it's okay by me.",
    "I remember how my Great Uncle Jerry would sit on the porch and whittle all day long. Once he whittled me a toy boat out of a larger toy boat I had. It was almost as good as the first one, except now it had bumpy whittle marks all over it. And no paint, because he had whittled off the paint.",
    "If I ever get real rich, I hope I'm not real mean to poor people, like I am now.",
    "I hope that after I die, people will say of me: \"That guy sure owed me a lot of money.",
    "Children need encouragement. So if a kid gets an answer right, tell him it was a lucky guess. That way, he develops a good, lucky feeling.",
    "I can picture in my mind a world without war, a world without hate. And I can picture us attacking that world, because they'd never expect it.",
    "It's easy to sit there and say you'd like to have more money. And I guess that's what I like about it. It's easy. Just sitting there, rocking back and forth, wanting that money.",
    "I wish I would have a real tragic love affair and get so bummed out that I'd just quit my job and become a bum for a few years, because I was thinking about doing that anyway.",
    "The face of a child can say it all, especially the mouth part of the face.",
    "To me, boxing is like a ballet, except there's no music, no choreography, and the dancers hit each other.",
    "Remember, kids in the backseat cause accidents; accidents in the backseat cause kids.",
    "If you're a cowboy and you're dragging a guy behind your horse, I bet it would really make you mad if you looked back and the guy was reading a magazine.",
    "I think people tend to forget that trees are living creatures. They're sort of like dogs. Huge, quiet, motionless dogs, with bark instead of fur.",
    "I think my new thing will be to try to be a real happy guy. I'll just walk around being real happy until some jerk says something stupid to me.",
    "If you lived in the Dark Ages and you were a catapult operator, I bet the most common question people would ask is, 'Can't you make it shoot farther?' 'No, I'm sorry. That's as far as it shoots.'",
    "Is there anything more beautiful than a beautiful, beautiful flamingo, flying across in front of a beautiful sunset? And he's carrying a beautiful rose in his beak, and also he's carrying a very beautiful painting with his feet. And also, you're drunk.",
    "What is it about a beautiful sunny afternoon, with the birds singing and the wind rustling through the leaves, that makes you want to get drunk?\" \"And after you're real drunk, maybe go down to the public park and stagger around and ask people for money, and then lay down and go to sleep.",
    "Here's a good thing to do if you go to a party and you don't know anybody: First take out the garbage. Then go around and collect any extra garbage that people might have, like a crumpled napkin, and take that out too. Pretty soon people will want to meet the busy garbage guy.",
    "If you get invited to your first orgy, don't just show up nude. That's a common mistake. You have to let nudity 'happen.'",
    "It takes a big man to cry, but it takes a bigger man to laugh at that man.",
    "One thing kids like is to be tricked. For instance, I was going to take my little nephew to Disneyland, but instead I drove him to an old burned-out warehouse. 'Oh, no,' I said. 'Disneyland burned down.' He cried and cried, but I think that deep down, he thought it was a pretty good joke. I started to drive over to the real Disneyland, but it was getting pretty late.",
    "Too bad you can't buy a voodoo globe so that you could make the earth spin real fast and freak everybody out.",
    "If you're a young Mafia gangster out on your first date, I bet it's real embarrassing if someone tries to kill you.",
    "You know what's probably a good thing to hang on your porch in the summertime, to keep mosquitos away from you and your guests? Just a big bag full of blood.",
    "I guess the hard thing for a lot of people to accept is why God would allow me to go running through their yards, yelling and spinning around.",
    "Don't ever get your speedometer confused with your clock, like I did once, because the faster you go the later you think you are.",
    "It makes me mad when people say I turned and ran like a scared rabbit. Maybe it was like an angry rabbit, who was going to fight in another fight, away from the first fight.",
    "I wish outer space guys would conquer the Earth and make people their pets, because I'd like to have one of those little beds with my name on it.",
    "I think a good product would be \"Baby Duck Hat\". It's a fake baby duck, which you strap on top of your head. Then you go swimming underwater until you find a mommy duck and her babies, and you join them. Then, all of a sudden, you stand up out of the water and roar like Godzilla. Man, those ducks really take off! Also, Baby Duck Hat is good for parties.",
    "I remember that one fateful day when Coach took me aside. I knew what was coming. \"You don't have to tell me,\" I said. \"I'm off the team, aren't I?\" \"Well,\" said Coach, \"you never were really ON the team. You made that uniform you're wearing out of rags and towels, and your helmet is a toy space helmet. You show up at practice and then either steal the ball and make us chase you to get it back, or you try to tackle people at inappropriate times.\" It was all true what he was saying. And yet, I thought something is brewing inside the head of this Coach. He sees something in me, some kind of raw talent that he can mold. But that's when I felt the handcuffs go on.",
    "Maybe in order to understand mankind, we have to look at the word itself: \"Mankind\". Basically, it's made up of two separate words - \"mank\" and \"ind\". What do these words mean? It's a mystery, and that's why so is mankind.",
    "Sometimes I think you have to march right in and demand your rights, even if you don't know what your rights are, or who the person is you're talking to. Then, on the way out, slam the door.",
    "A man doesn't automatically get my respect. He has to get down in the dirt and beg for it.",
    "I guess I kinda lost control, because in the middle of the play I ran up and lit the evil puppet villain on fire. No, I didn't. Just kidding. I just said that to help illustrate one of the human emotions, which is freaking out. Another emotion is greed, as when you kill someone for money, or something like that. Another emotion is generosity, as when you pay someone double what he paid for his stupid puppet.",
    "If you think a weakness can be turned into a strength, I hate to tell you this, but that's another weakness.",
    "If life deals you lemons, why not go kill someone with the lemons (maybe by shoving them down his throat).",
    "Why do there have to be rules for everything? It's gotten to the point that rules dominate just about every aspect of our lives. In fact, it might be said that rules have become the foot-long sticks of mankind.",
    "To me, it's always a good idea to always carry two sacks of something when you walk around. That way, if anybody says, \"Hey, can you give me a hand?,\" you can say, \"Sorry, got these sacks.\"",
    "I hate it when people say somebody has a \"speech impediment\" even if he does, because it could hurt his feelings. So instead, I call it a \"speech improvement\", and I go up to the guy and say, \"Hey, Bob, I like your speech improvement.\" I think this makes him feel better.",
    "I think there should be something in science called the \"reindeer effect.\" I don't know what it would be, but I think it'd be good to hear someone say, \"Gentlemen, what we have here is a terrifying example of the reindeer effect.",
    "I think somebody should come up with a way to breed a very large shrimp. That way, you could ride him, then after you camped at night, you could eat him. How about it, science?",
    "For mad scientists who keep brains in jars, here's a tip: Why not add a slice of lemon to each jar, for freshness.",
    "I hope they never find out that lightning has a lot of vitamins in it, because do you hide from it or not?",
    "If you had a school for professional fireworks people, I don't think you could cover fuses in just one class. It's just too rich a subject.",
    "He was the kind of man who was not ashamed to show affection. I guess that's what I hated about him.",
    "If you're a cowboy, and you're dragging a guy behind your horse, I bet it would really make you mad if you looked back and the guy was reading a magazine.",
    "It makes me mad when people say I turned and ran like a scared rabbit. Maybe it was like an angry rabbit, who was going to fight in another fight, away from the first fight.",
    "Why do the caterpillar and the ant have to be enemies? One eats leaves, and the other eats caterpillars. Oh, I see now.",
    "Love can sweep you off your feet and carry you along in a way you've never known before. But the ride always ends, and you end up feeling lonely and bitter. Wait. It's not love I'm describing. I'm thinking of a monorail.",
    "I bet it was pretty hard to pick up girls if you had the Black Death.",
    "I wish I would have a real tragic love affair and get so bummed out that I'd just quit my job and become a bum for a few years, because I was thinking about doing that anyway.",
    "What am I afraid of? I'll tell you: a feather. that's right, a feather. How could anyone be afraid of a feather, you say. That's an honest question, and I'll try to give it an honest answer. First of all, did I say it was a poison feather?",
    "If you're a circus clown, and you have a dog that you use in your act, I don't think it's a good idea to also dress the dog up like a clown, because people see that and they think, \"Forgive me, but that's just too much.",
    "Whenever I hear the sparrow chirping, watch the woodpecker chirp, catch a chirping trout, or listen to the sad howl of the chirp rat, I think: Oh boy! I'm going insane again.",
    "If you're ever stuck in some thick undergrowth, in your underwear, don't stop and think of what other words have \"under\" in them, because that's probably the first sign of jungle madness.",
    "When this girl at the art museum asked me whom I liked better, Monet or Manet, I said, \"I like mayonnaise.\" She just stared at me, so I said it again, louder. Then she left. I guess she went to try to find some mayonnaise for me.",
    "If I ever get real rich, I hope I'm not real mean to poor people, like I am now.",
    "You know one thing that will really make a woman mad? Just run up and kick her in the butt. (P.S. This also works with men.)",
    "I remember how the other kids used to say that old Mister Swenson was the meanest man in town. But I said I thought he was nice, that he just didn't know how to show it. The meanest man in town, I said, was the mean old guy who lived in the big white house. \"THAT'S MISTER SWENSON,\" they said. Oh, my mistake.",
    "Whenever you read a good book, it's like the author is right there, in the room, talking to you, which is why I don't like to read good books.",
    "Instead of studying for finals, what about just going to the Bahamas and catching some rays? Maybe you'll flunk, but you might have flunked anyway; that's my point.",
    "Instead of having \"answers\" on a math test, they should just call them \"impressions,\" and if you got a different \"impression,\" so what, can't we all be brothers?",
    "If you go flying back through time, and you see somebody else flying forward into the future, it's probably best to avoid eye contact.",
    "If they have moving sidewalks in the future, when you get on them, I think you should have to assume sort of a walking shape so as not to frighten the dogs.",
    "You know something that would really make me applaud? A guy gets stuck in quicksand, then sinks, then suddenly comes shooting out, riding on water skis! How do they do that?!",
    "Perhaps, if I am very lucky, the feeble efforts of my lifetime will someday be noticed, and maybe, in some small way, they will be acknowledged as the greatest works of genius ever created by Man.",
    "I'd like to see a nature film where an eagle swoops down and pulls a fish out of a lake, and then maybe he's flying along, low to the ground, and the fish pulls a worm out of the ground. Now that's a documentary!",
    "Instead of a trap door, what about a trap window? The guy looks out it, and if he leans too far, he falls out. Wait. I guess that's like a regular window.",
    "Like jewels in a crown, the precious stones glittered in the queen's round metal hat.",
    "I wish I had a dollar for every time I spent a dollar, because then, yahoo!, I'd have all my money back.",
    "If you ever drop your keys into a river of molten lava, let 'em go, because, man, they're gone.",
    "One thing a computer can do that most humans can't is be sealed up in a cardboard box and sit in a warehouse.",
    "Here's a good thing to do if you go to a party and you don't know anybody: First, take out the garbage. Then go around and collect any extra garbage that people might have, like a crumpled-up napkin, and take that out too. Pretty soon people will want to meet the busy garbage guy.",
    "If you want to be the popular one at a party, here's a good thing to do: Go up to some people who are talking and laughing and say, \"Well, technically that's illegal.\" It might fit in with what somebody just said. And even if it doesn't, so what, I hate this stupid party.",
    "How come the dove gets to be the peace symbol? How about the pillow? It has more feathers than the dove, and it doesn't have that dangerous beak.",
    "Whenever I need to \"get away,'' I just get away in my mind. I go to my imaginary spot, where the beach is perfect and the water is perfect and the weather is perfect. The only bad thing there are the flies. They're terrible!",
    "Even though he was an enemy of mine, I had to admit that what he had accomplished was a brilliant piece of strategy. First, he punched me, then he kicked me, then he punched me again.",
    "I can picture in my mind a world without war, a world without hate. And I can picture us attacking that world, because they'd never expect it.",
    "If I was the head of a country during a war and I had to sign a peace treaty, just as I was signing I'd glance over the treaty and then suddenly act surprised. \"Wait a minute! I thought WE won!\"",
    "If any man says he hates war more than I do, he better have a knife, that's all I have to say.",
    "I remember when I was in the army, we had the toughest drill sergeant in the world. He'd get right up next to your face and yell, and if you didn't have the right answers, mister, you'd be peeling potatoes or changing the latrine. Hey, wait. I wasn't in the army. Then who WAS that guy?!",
    "I think my new thing will be to try to be a real happy guy. I'll just walk around being real happy until some jerk says something stupid to me.",
    "I hope, when they die, cartoon characters have to answer for their sins.",
    "If I come back as an animal in my next lifetime, I hope it's some type of parasite, because this is the part where I take it EASY!",
    "When you die, if you go somewhere where they ask you a bunch of questions about your life and what you learned and all, I think a good way to get out of it is just to say, \"No speaka English.\"",
    "If I come back as a horsefly, I think my favorite thing would be to land on someone's lip. Even if they smash you, ick!, you're all over their lip!",
    "I think in one of my previous lives I was a mighty king, because I like people to do what I say.",
    "Here's a good trick: Get a job as a judge at the Olympics. Then, if some guy sets a world record, pretend that you didn't see it and go, \"Okay, is everybody ready to start now?\"",
    "Here's a good joke to do during an earthquake: Straddle a big crack in the ground, and if it opens wider, go \"Whoa! Whoa!\" and flail your arms around, like you're going to fall in.",
    "If I was a father in a waiting room, and the nurse came out and said, \"Congratulations, it's a girl,\" I think a good gag would be to get real mad and yell, \"A girl!? You must have me mixed up with THAT dork!\" and point to another father.",
    "If you wear a toupee, why not let your friends try it on for a while? Come on, we're not going to hurt it.",
    "A good way to keep a mob of peasants from killing your monster is when they break into your castle, make them be real quiet, then open a door and there's the monster, sound asleep.",
    "There should be a detective show called \"Johnny Monkey,\" because every week you could have a guy say \"I ain't gonna get caught by no MONKEY,\" but then he would, and I don't think I'd ever get tired of that.",
    "If you're ever selling your house, and some people come by, and a big rat comes out and he's dragging the rattrap because it didn't quite kill him, just tell the people he's your pet and that's a trick you taught him.",
    "I think there probably should be a rule that if you're talking about how many loaves of bread a bullet will go through, it's understood that you mean lengthwise loaves. Otherwise, it makes no sense.",
    "You know what's probably a good thing to hang on your porch in the summertime, to keep mosquitoes away from you and your guests? Just a big bag of blood.",
    "If I lived back in the Wild West days, instead of carrying a six-gun in my holster, I'd carry a soldering iron. That way, if some smart-aleck cowboy said something like, \"Hey look. He's carrying a soldering iron!\" and started laughing, and everybody else started laughing, I could just say, \"That's right, it's a soldering iron. The soldering iron of justice.\" Then everybody would get real quiet and ashamed, because they made fun of the soldering iron of justice, and I could probably hit them up for a free drink.",
    "If I was being executed by injection, I'd clean up my cell real neat. Then, when they came to get me, I'd say, \"Injection? I thought you said inspection'.\" They'd probably feel real bad, and maybe I could get out of it.",
    "I think a good novel would be where a bunch of men on a ship are looking for a whale. They look and look, but you know what? They never find him. And you know why they never find him? It doesn't say. The book leaves it up to you, the reader, to decide. Then, at the very end, there's a page you can lick and it tastes like Kool-Aid.",
    "I think a good way to get in a movie is to show up where they're making the movie, then stick a big cactus plant onto your buttocks and start yowling and running around. Everyone would think it was funny, and the head movie guy would say, \"Hey, let's put him in the movie.\"",
    "If I had a mine shaft, I don't think I would just abandon it. There's got to be a better way.",
    "Anytime I see something screech across a room and latch onto someone's neck, and the guy screams and tries to get it off, I have to laugh, because what IS that thing?!",
    "I hope that someday we will be able to put away our fears and prejudices and just laugh at people.",
    "Dad always thought laughter was the best medicine, which I guess is why several of us died of tuberculosis.",
    "It takes a big man to cry, but it takes a bigger man to laugh at that man.",
    "When you go ice-skating, try not to swing your arms too much, because that really annoys me.",
    "I think a new, different kind of bowling should be \"carpet bowling.\" It's just like regular bowling, only the lanes are carpet instead of wood. I don't know why we should do this, but my gosh, we've got to try something!",
    "In weightlifting, I don't think sudden, uncontrolled urination should automatically disqualify you.",
    "Do you know what happens when you slice a golf ball in half? Someone gets mad at you. I found this out the hard way.",
    "Some folks say it was a miracle. St. Francis suddenly appeared and knocked the next pitch clean over the fence. Other folks say it was just a lucky swing.",
    "If you're in a boxing match, try not to let the other guy's glove touch your lips, because you don't know where that glove has been.",
    "I hope that after I die, people will say of me: \"That guy sure owed me a lot of money.''",
    "It's easy to sit there and say you'd like to have more money. And I guess that's what I like about it. It's easy. Just sitting there, rocking back and forth, wanting that money.",
    "Whenever someone asks me to define love, I usually think for a minute, then I spin around and pin the guy's arm behind his back. NOW who's asking the questions?",
    "Most of the time it was probably real bad being stuck down in a dungeon. But some days, when there was a bad storm outside, you'd look out your little window and think, \"Boy, I'm glad I'm not out there.\"",
    "When I was a child, there were times when we had to entertain ourselves. And usually the best way to do that was to turn on the TV.",
    "If you were a gladiator in olden days, I bet the inefficiency of how the gladiator fights were organized and scheduled would just drive you up a wall.",
    "When the age of the Vikings came to a close, they must have sensed it. Probably, they gathered together one evening, slapped each other on the back and said, \"Hey, good job.\"",
    "During the Middle Ages, probably one of the biggest mistakes was not putting on your armor because you were \"just going down to the corner.\"",
    "If the Vikings were around today, they would probably be amazed at how much glow-in-the-dark stuff we have, and how we take so much of it for granted.",
    "It's funny that pirates were always going around searching for treasure, and they never realized that the real treasure was the fond memories they were creating.",
    "If you lived in the Dark Ages, and you were a catapult operator, I bet the most common question people would ask is, \"Can't you make it shoot farther?\" No. I'm sorry. That's as far as it shoots.",
    "Is there anything more beautiful than a beautiful, beautiful flamingo, flying across in front of a beautiful sunset? And he's carrying a beautiful rose in his beak, and also he's carrying a very beautiful painting with his feet. And also, you're drunk.",
    "People laugh when I say that I think a jellyfish is one of the most beautiful things in the world. What they don't understand is, I mean a jellyfish with long, blond hair.",
    "I saw on this nature show how the male elk douses himself with urine to smell sweeter to the opposite sex. What a coincidence!",
    "If you get invited to your first orgy, don't just show up nude. That's a common mistake. You have to let nudity \"happen.\"",
    "I don't think God put me on this planet to judge others. I think he put me on this planet to gather specimens and take them back to my home planet.",
    "If aliens from outer space ever come and we show them our civilization and they make fun of it, we should say we were just kidding, that this isn't really our civilization, but a gag we hoped they would like. Then we tell them to come back in twenty years to see our REAL civilization. After that, we start a crash program of coming up with an impressive new civilization. Either that, or just shoot down the aliens as they're waving good-bye.",
    "If Alien was my friend, I'd like to be with him when he went to the dentist. When they started drilling, he'd probably go nuts and start eating everybody. That Alien!",
    "People just naturally assume that dogs would be incapable of working together on some sort of construction project. But what about just a big field full of holes?",
    "Better not take a dog on the space shuttle, because if he sticks his head out when you're coming home, his face might burn up.",
    "I wonder if Dracula ever has ticks.",
    "If there was a terrible storm outside, but somehow this dog lived through the storm, and he showed up at your door when the storm was finally over, I think a good name for him would be Carl."
]
    return slack.response(random.choice(quotes),response_type='in_channel')

@slack.command('thisisfine', token='xxxx',
               team_id='xxxx', methods=['POST'])
def sl8(**kwargs):
    return slack.response('http://gph.is/1IPoO7R',response_type='in_channel')

@slack.command('iwritecode', token='xxxx',
               team_id='xxxx', methods=['POST'])
def sl9(**kwargs):
    return slack.response('http://resguru.com/wp-content/uploads/2011/05/angry-keyboard-user.gif',response_type='in_channel')

@slack.command('wtf', token='xxxx',
               team_id='xxxx', methods=['POST'])
def s20(**kwargs):
    return slack.response('http://media1.giphy.com/media/aZ3LDBs1ExsE8/giphy.gif',response_type='in_channel')

@slack.command('call_admin', token='xxxx',
               team_id='xxxx', methods=['POST'])
def s21(**kwargs):
    text = kwargs.get('text')
    user_name = kwargs.get('user_name')
    user_id = kwargs.get('user_id')
    from_channel = kwargs.get("channel_name")
    channel = 'admin_team'
    bot_token = 'xxxx'
    bot_username = 'admin_assistant'
    parameters = {'token':bot_token, 'text':"user: {0}, channel: {1}, message: {2}".format(user_name,from_channel, text), 'channel':channel,
                    'username':bot_username,'as_user':'true'}
    requests.get("https://slack.com/api/chat.postMessage",params=parameters)
    return slack.response('admin called',response_type='ephemeral')

@app.route('/dicks/<how_many_disks>')
def dicks(how_many_disks):
    d = "8====D"
    bag_of_dicks =[]
    for x in range(int(how_many_disks)):
        bag_of_dicks.append(d)
    string_dicks = ",".join(bag_of_dicks)
    return '{"dicks":{'+ string_dicks+'}}'


@app.route('/newuser/<email>')
def newuser(email):
    if email not in email_blacklist:
        try:
            channel = 'admin_team'
            bot_token = 'xxxx'
            bot_username = 'xxxx'
            parameters = {'token':bot_token, 'text':email, 'channel':channel,
                    'username':bot_username,'as_user':'true'}
            requests.get("https://slack.com/api/chat.postMessage",params=parameters)
            return jsonify({"status":200})
        except:
            return {"status": "well fuck"}
    else:
        return {"status": "EMAIL BLACKLISTED"}
    #requests.get("https://slack.com/api/chat.postMessage?token=xoxb-105417684083-kJyxsrt0bdFldkROAkfd31Ng&channel=admin_team&text={0}".format(email))
