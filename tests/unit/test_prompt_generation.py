import os
import sys
import pysrt

# Add the project root to the Python path to allow for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langflix.core.subtitle_parser import chunk_subtitles
from langflix.core.expression_analyzer import get_prompt_for_chunk

srt_content = """
1
00:00:21,565 --> 00:00:24,733
[Muffled chatter]

2
00:00:48,891 --> 00:00:50,192
[Knocking]

3
00:00:50,260 --> 00:00:51,327
Gerald Tate's here.

4
00:00:51,395 --> 00:00:52,729
He wants to know
what's happening to his deal.

5
00:00:52,797 --> 00:00:54,264
Go get Harvey.

6
00:00:55,793 --> 00:00:59,793
== sync, corrected by <font color="#00ff00">elderman</font> ==

7
00:01:04,080 --> 00:01:06,715
I check.

8
00:01:06,783 --> 00:01:07,949
Raise.

9
00:01:08,017 --> 00:01:10,151
5,000.

10
00:01:10,219 --> 00:01:12,219
I'm all-in.

11
00:01:15,991 --> 00:01:17,558
[Cell phone dings]

12
00:01:19,227 --> 00:01:21,761
You can pay me later.
I got to go.

13
00:01:22,721 --> 00:01:24,155
Gentlemen.

14
00:01:25,657 --> 00:01:27,826
I'm paying you millions,

15
00:01:27,893 --> 00:01:29,494
and you're telling me
I'm gonna get screwed?

16
00:01:29,561 --> 00:01:32,230
Jessica, have I come
at a bad time?

17
00:01:32,298 --> 00:01:36,501
Gerald, this is
Harvey Specter.

18
00:01:36,569 --> 00:01:37,895
He's our best closer.

19
00:01:37,896 --> 00:01:38,804
Well, if you're
the best closer,

20
00:01:38,805 --> 00:01:40,406
where the hell you been
for the last three hours?

21
00:01:40,474 --> 00:01:43,775
Well, Gerald, I specialize
in troubled situations,

22
00:01:43,776 --> 00:01:44,909
and when I left here
at 7:00 p.m.,

23
00:01:44,977 --> 00:01:46,812
this deal wasn't
in jeopardy,

24
00:01:46,880 --> 00:01:48,380
so I'm just trying to figure out
what happened in the interim.

25
00:01:48,448 --> 00:01:49,749
We keep offering more money.

26
00:01:49,817 --> 00:01:51,250
They keep rejecting it.

27
00:01:51,318 --> 00:01:52,985
It's last-minute
bad faith bullshit.

28
00:01:53,053 --> 00:01:55,021
Says here that Cooper
won't be staying on

29
00:01:55,089 --> 00:01:57,190
as honorary vice president.

30
00:01:57,258 --> 00:01:59,091
That's right.
I don't want him around.

31
00:01:59,159 --> 00:02:00,159
He wouldn't be around.

32
00:02:00,227 --> 00:02:01,461
It's an honorary position.

33
00:02:01,529 --> 00:02:02,662
I don't give a shit.

34
00:02:02,730 --> 00:02:04,530
Well, I think you do,

35
00:02:04,598 --> 00:02:06,365
because that's what's changed
since I left,

36
00:02:06,433 --> 00:02:08,800
which means it's you
who's been dealing in bad faith.

37
00:02:08,868 --> 00:02:11,002
Well, now that you've got
a grasp on what's happened

38
00:02:11,070 --> 00:02:12,570
in the goddamn interim,

39
00:02:12,638 --> 00:02:14,305
what are you
gonna do about it?

40
00:02:14,373 --> 00:02:15,973
Because he's not getting
that title.

41
00:02:16,041 --> 00:02:19,344
Well, let me make sure
I understand this, okay?

42
00:02:19,411 --> 00:02:21,946
We negotiated a deal that
gave you everything you wanted,

43
00:02:22,014 --> 00:02:24,750
Mr. Cooper signed it,
and now you won't close

44
00:02:24,817 --> 00:02:26,618
until we take away
the last shred of his dignity?

45
00:02:26,686 --> 00:02:28,788
- Bingo.
- Well, that's not gonna happen.

46
00:02:28,855 --> 00:02:31,090
- And why the hell not?
- Because I like Mr. Cooper,

47
00:02:31,158 --> 00:02:33,426
and my firm doesn't operate
in bad faith.

48
00:02:33,494 --> 00:02:36,329
Oh.
I see how it is.

49
00:02:36,397 --> 00:02:37,564
Instead of working Cooper,

50
00:02:37,632 --> 00:02:39,833
you're working me.

51
00:02:39,901 --> 00:02:42,235
Well, why don't you take
your pansy attitude

52
00:02:42,303 --> 00:02:44,838
back in there
and make him sign my deal?

53
00:02:44,906 --> 00:02:46,573
Or I'll pay someone else
your money

54
00:02:46,641 --> 00:02:49,109
to do it for me.
First of all, Gerald,

55
00:02:49,177 --> 00:02:50,944
if you think
anyone's gonna touch this deal

56
00:02:51,011 --> 00:02:53,880
after your bad faith,
you're mistaken.

57
00:02:53,947 --> 00:02:57,316
Second, the way
our agreement works is,

58
00:02:57,384 --> 00:02:58,951
the minute Cooper
signed the deal

59
00:02:59,019 --> 00:03:00,519
which gave you everything
you wanted,

60
00:03:00,587 --> 00:03:03,556
our fee was due and payable,
which is why at 7:30

61
00:03:03,623 --> 00:03:06,626
I received confirmation
of a wire transfer

62
00:03:06,694 --> 00:03:09,729
from escrow indicating payment
in full.

63
00:03:16,104 --> 00:03:17,605
So I'd say
the ball's in your court,

64
00:03:17,673 --> 00:03:20,207
but the truth is
your balls are in my fist.

65
00:03:20,275 --> 00:03:23,677
Now I apologize if that image
is too pansy for you,

66
00:03:23,745 --> 00:03:25,112
but I'm comfortable enough
with my manhood

67
00:03:25,179 --> 00:03:26,446
to put it out there.

68
00:03:26,514 --> 00:03:28,081
Now get your ass in there

69
00:03:28,149 --> 00:03:31,184
and close the goddamn deal.

70
00:03:31,252 --> 00:03:32,952
You gonna let him talk to me
like this?

71
00:03:33,019 --> 00:03:35,354
Harvey speaks for the firm.

72
00:03:46,332 --> 00:03:48,934
[Clears throat]

73
00:03:49,002 --> 00:03:51,971
We got paid
before Gerald signed the deal?

74
00:03:52,038 --> 00:03:53,405
What are you talking about?
This is a memo

75
00:03:53,473 --> 00:03:55,074
about some fire drill
on Tuesday.

76
00:03:55,142 --> 00:03:56,742
- Huh.
- You're the blue team captain.

77
00:03:56,810 --> 00:03:59,645
You get to wear a fire hat.

78
00:04:12,625 --> 00:04:14,725
Time's up.

79
00:04:14,793 --> 00:04:17,161
Pencils down.

80
00:04:17,229 --> 00:04:19,997
Excuse me.
Do I know you from somewhere?

81
00:04:20,065 --> 00:04:21,933
I don't think so.

82
00:04:22,001 --> 00:04:24,904
I have a pretty good memory
for faces.

83
00:04:24,971 --> 00:04:28,073
So do I.

84
00:04:28,141 --> 00:04:31,643
- Sorry.
- I got it.

85
00:04:43,623 --> 00:04:45,823
Hey.
Hey!

86
00:04:45,891 --> 00:04:47,325
Stop! You in the cap!

87
00:05:15,056 --> 00:05:18,556
<font color=#00ff00>♪ Suits 1x01 ♪</font>
<font color=#00ffff>Pilot</font>
Original Air Date on June 23, 2011

88
00:05:18,557 --> 00:05:19,877
[Knocking]

89
00:05:20,325 --> 00:05:22,326
What did you get me?

90
00:05:22,394 --> 00:05:23,928
What I said
I was gonna get you.

91
00:05:23,996 --> 00:05:26,997
A 158.
I told you I wanted a 175.

92
00:05:27,065 --> 00:05:28,299
And I told you
only 1 out of 100 people

93
00:05:28,366 --> 00:05:30,234
can score that.

94
00:05:30,301 --> 00:05:33,237
You're a B-minus student.
You got 1,000 on your SATs.

95
00:05:33,305 --> 00:05:34,873
If I get you a 175,
they'll know you cheated.

96
00:05:34,940 --> 00:05:37,775
So only a genius loser
can get a 175?

97
00:05:37,843 --> 00:05:40,311
Actually, no.
I would get a 180.

98
00:05:40,379 --> 00:05:42,747
Now can I have my money,
please?

99
00:05:48,754 --> 00:05:51,155
Whoa.
This is only half.

100
00:05:51,223 --> 00:05:52,657
Then why don't you
go call the police?

101
00:05:56,662 --> 00:06:00,165
I got to get my shit
together.

102
00:06:00,233 --> 00:06:02,167
That's the best cheeseburger
I've had in my life.

103
00:06:02,235 --> 00:06:05,705
It's from Monday, Trevor.

104
00:06:05,773 --> 00:06:07,006
Look, man, I'm serious.

105
00:06:07,074 --> 00:06:08,608
I almost got caught today.

106
00:06:08,676 --> 00:06:10,076
I've got
to stop getting stoned.

107
00:06:10,144 --> 00:06:11,377
I've got to get
my act together.

108
00:06:11,445 --> 00:06:12,912
Dude, look at me.

109
00:06:12,980 --> 00:06:15,415
You can burn bud
and still be a success.

110
00:06:15,483 --> 00:06:17,084
You sell pot for a living.

111
00:06:17,151 --> 00:06:19,052
Still saps the motivation.

112
00:06:19,120 --> 00:06:21,754
All I'm saying is,
you want in,

113
00:06:21,822 --> 00:06:23,222
you are in.

114
00:06:23,290 --> 00:06:25,224
You know,
that is word for word

115
00:06:25,292 --> 00:06:27,126
your offer before I got caught

116
00:06:27,194 --> 00:06:29,261
cheating on your math test
in the third grade.

117
00:06:29,329 --> 00:06:30,329
Goddamn memory.

118
00:06:30,397 --> 00:06:32,097
Stop.

119
00:06:32,165 --> 00:06:34,299
Look, no one's gonna suspect
you're a dealer.

120
00:06:34,367 --> 00:06:35,300
I mean, look at me.

121
00:06:35,368 --> 00:06:37,168
This is a $2,000 suit, Mike.

122
00:06:37,236 --> 00:06:38,636
I got, like, 12 of 'em.

123
00:06:38,704 --> 00:06:40,405
I take on
real software projects.

124
00:06:40,473 --> 00:06:45,110
I have clients who bring me
briefcases filled with cash,

125
00:06:45,178 --> 00:06:46,678
and I hand them
identical briefcases

126
00:06:46,746 --> 00:06:48,147
with vacuum-sealed bud.

127
00:06:48,215 --> 00:06:49,949
So what do you need me for?

128
00:06:50,017 --> 00:06:52,219
Well, I have a client
coming in from out of town,

129
00:06:52,287 --> 00:06:53,854
and I can't meet him,

130
00:06:53,922 --> 00:06:56,824
and I need someone I can trust
to make the drop.

131
00:06:56,892 --> 00:06:58,426
It's totally safe.

132
00:06:58,493 --> 00:07:00,161
Trevor, a person
is more likely to die

133
00:07:00,228 --> 00:07:01,595
while dealing drugs
than they would be

134
00:07:01,663 --> 00:07:03,863
on death row in Texas.

135
00:07:03,931 --> 00:07:05,331
Wait.
What are you talking about?

136
00:07:05,399 --> 00:07:06,666
It's from <i>Freakonomics.</i>

137
00:07:06,734 --> 00:07:07,833
Do you read anything
that I give you?

138
00:07:07,901 --> 00:07:09,702
It doesn't matter,

139
00:07:09,770 --> 00:07:11,337
because you have to find
somebody else.

140
00:07:11,404 --> 00:07:12,571
I'm not interested.

141
00:07:12,639 --> 00:07:14,740
Not interested in what?

142
00:07:14,807 --> 00:07:15,974
What are you doing here?
You said you were gonna stay

143
00:07:16,042 --> 00:07:16,975
at your place tonight.

144
00:07:17,043 --> 00:07:18,743
Hi, sweetie.

145
00:07:18,811 --> 00:07:20,212
What a pleasant surprise.

146
00:07:20,280 --> 00:07:22,114
I'm so glad you stopped by.
Yeah.

147
00:07:22,182 --> 00:07:23,349
We're in the middle
of something.

148
00:07:23,416 --> 00:07:25,384
What are you
in the middle of?

149
00:07:25,452 --> 00:07:27,253
Trevor's trying
to set me up.

150
00:07:27,321 --> 00:07:28,621
That's terrific.

151
00:07:28,689 --> 00:07:30,457
Who's the lucky girl?

152
00:07:30,524 --> 00:07:32,326
I'm trying to get him
to work for me.

153
00:07:32,393 --> 00:07:34,195
That's a great idea.

154
00:07:34,262 --> 00:07:35,729
It will take some stress
off Trevor,

155
00:07:35,797 --> 00:07:36,798
and you'll pick up
writing code

156
00:07:36,865 --> 00:07:38,767
like you do everything else.

157
00:07:38,834 --> 00:07:40,268
All right.
I got to go.

158
00:07:40,336 --> 00:07:42,003
I got go get up early
to see my grandmother

159
00:07:42,070 --> 00:07:43,104
and pay them another month.

160
00:07:43,172 --> 00:07:44,672
Oh.
[Grunting]

161
00:07:44,740 --> 00:07:46,507
[Giggles]

162
00:07:46,574 --> 00:07:47,574
- Good night.
- Bye.

163
00:07:50,378 --> 00:07:53,146
How did you know Gerald
wouldn't look at that memo?

164
00:07:53,213 --> 00:07:55,214
Because a charging bull
always looks at the red cape,

165
00:07:55,282 --> 00:07:56,749
not at the man
with the sword.

166
00:07:56,816 --> 00:07:58,884
By the way,
I've set up a meeting

167
00:07:58,951 --> 00:08:01,086
for you and John Dockery
next week.

168
00:08:01,154 --> 00:08:02,588
Dockery?
He's Skadden's biggest client.

169
00:08:02,655 --> 00:08:03,656
Not anymore.

170
00:08:03,723 --> 00:08:05,491
He's looking around.

171
00:08:05,559 --> 00:08:06,826
He plays tennis.
I want you to close him.

172
00:08:06,894 --> 00:08:08,261
Consider it done.

173
00:08:08,329 --> 00:08:11,298
Then you are
officially dismissed

174
00:08:11,366 --> 00:08:13,167
for the evening.

175
00:08:13,234 --> 00:08:14,835
Cheers.

176
00:08:14,903 --> 00:08:15,903
Well, you two seem
to be celebrating something.

177
00:08:15,971 --> 00:08:18,239
Mm-hmm.
We are.

178
00:08:18,307 --> 00:08:19,808
In fact, you are looking

179
00:08:19,876 --> 00:08:21,109
at the best closer
this city has ever seen.

180
00:08:21,177 --> 00:08:22,411
Closer, huh?

181
00:08:22,478 --> 00:08:23,811
Baseball?
Attorney.

182
00:08:23,879 --> 00:08:25,313
I close situations.

183
00:08:25,381 --> 00:08:27,216
Hmm.
So you only care about money?

184
00:08:27,283 --> 00:08:29,051
The truth is,
I do it for the children.

185
00:08:29,119 --> 00:08:30,920
[Chuckles]

186
00:08:30,988 --> 00:08:32,555
I'm Lisa.

187
00:08:32,623 --> 00:08:33,857
Harvey.

188
00:08:33,925 --> 00:08:36,927
Lisa, I don't normally do this,

189
00:08:36,995 --> 00:08:38,595
but since we are celebrating,

190
00:08:38,663 --> 00:08:40,497
what time do you get off
tonight?

191
00:08:40,565 --> 00:08:42,499
I'm glad you asked.

192
00:08:42,567 --> 00:08:46,804
I get off at ten past
"I'm never going out with you."

193
00:08:49,375 --> 00:08:53,477
I guess you're not the best
closer this city's ever seen.

194
00:08:53,545 --> 00:08:56,747
[Upbeat music]

195
00:08:56,815 --> 00:09:04,588
♪ ♪

196
00:09:07,426 --> 00:09:08,926
Good morning.

197
00:09:08,994 --> 00:09:10,561
Lisa, this was lovely,

198
00:09:10,629 --> 00:09:12,330
but I'm afraid
you have to go.

199
00:09:12,398 --> 00:09:14,065
- Aw.
- I hate to miss a workout,

200
00:09:14,133 --> 00:09:16,367
and I really need
to be in the office by 7:30.

201
00:09:16,435 --> 00:09:18,636
I can make you breakfast?

202
00:09:18,704 --> 00:09:20,138
You could eat it
off my stomach.

203
00:09:20,205 --> 00:09:21,405
I guess if I skip the gym,

204
00:09:21,473 --> 00:09:23,374
I can still get in by 9:00.

205
00:09:23,442 --> 00:09:24,809
[Giggles]

206
00:09:34,953 --> 00:09:37,855
I hear someone's
not taking their pills.

207
00:09:37,923 --> 00:09:40,524
Because they're trying
to poison me.

208
00:09:40,592 --> 00:09:42,726
Grammy, that's crazy.

209
00:09:42,793 --> 00:09:44,194
Dr. Shrager gave me her word

210
00:09:44,261 --> 00:09:46,695
she wouldn't poison you
until January.

211
00:09:46,763 --> 00:09:48,297
If she does it before then,
she can't count it

212
00:09:48,365 --> 00:09:50,499
towards next year's quota.

213
00:09:53,002 --> 00:09:55,670
Oh, what did I teach you?

214
00:09:55,738 --> 00:09:58,806
[Imitates explosion]

215
00:09:58,874 --> 00:10:02,376
Michael, I'm not gonna be
around forever.

216
00:10:02,444 --> 00:10:07,815
And I want you to stop
with that stuff.

217
00:10:07,883 --> 00:10:09,116
What stuff?

218
00:10:09,184 --> 00:10:11,685
I may be old,

219
00:10:11,753 --> 00:10:13,621
but I'm not an idiot.

220
00:10:13,689 --> 00:10:15,824
I know life has been hard
for you,

221
00:10:15,891 --> 00:10:17,325
but you're not a kid anymore,

222
00:10:17,393 --> 00:10:19,094
and I want you to promise

223
00:10:19,162 --> 00:10:21,497
you're gonna start living up
to your potential.

224
00:10:27,037 --> 00:10:28,771
I promise.

225
00:10:32,076 --> 00:10:34,044
I'm not saying that I haven't
been charmed by Harvey,

226
00:10:34,112 --> 00:10:35,879
but it's just so patronizing

227
00:10:35,947 --> 00:10:37,615
when you say
that he can handle those things

228
00:10:37,682 --> 00:10:39,149
and, "Louis,
you can only handle this."

229
00:10:39,217 --> 00:10:41,051
Jessica, I could have handled
Gerald Tate.

230
00:10:41,118 --> 00:10:42,385
And I told you
I disagree.

231
00:10:42,453 --> 00:10:44,287
- Why?
- Because when you put

232
00:10:44,355 --> 00:10:45,622
two bullies
in the same room together,

233
00:10:45,689 --> 00:10:47,623
things generally
don't go so well.

234
00:10:47,691 --> 00:10:49,091
It's 9:30.
Nice of you to show up

235
00:10:49,159 --> 00:10:50,959
two hours after we open
for business.

236
00:10:51,027 --> 00:10:52,994
And I see that you're also
trying to look like a pimp.

237
00:10:53,062 --> 00:10:55,863
My bad, Louis.
I was out late last night.

238
00:10:55,931 --> 00:10:56,797
And when I woke up,
this is the suit

239
00:10:56,865 --> 00:10:58,132
your wife picked out for me.

240
00:10:58,200 --> 00:10:59,767
And that would be funny

241
00:10:59,835 --> 00:11:01,569
if I'd actually been married.
Moving along.

242
00:11:01,637 --> 00:11:03,738
- You're not married?
- Recruiting. Harvey.

243
00:11:03,806 --> 00:11:05,440
Your interviews are set up
for tomorrow.

244
00:11:05,508 --> 00:11:06,942
What?
Why don't we just hire

245
00:11:07,010 --> 00:11:08,811
the Harvard summer associate
douche?

246
00:11:08,879 --> 00:11:10,980
I think if you listen
to the phrasing

247
00:11:11,048 --> 00:11:12,983
of that question,
you'll come up with an answer.

248
00:11:13,051 --> 00:11:14,785
We need people who think
on their feet,

249
00:11:14,853 --> 00:11:16,353
not another clone
with a rod up his ass.

250
00:11:16,421 --> 00:11:18,322
Harvey, the fact
that we only hire from Harvard

251
00:11:18,390 --> 00:11:20,257
gives us a cache
that's a little more valuable

252
00:11:20,325 --> 00:11:21,858
than hiring a kid
from Rutgers.

253
00:11:23,361 --> 00:11:25,629
You went to Harvard Law.

254
00:11:25,697 --> 00:11:27,531
I'm an exception.

255
00:11:27,599 --> 00:11:29,132
Find me another one.

256
00:11:29,200 --> 00:11:30,967
Can we please skip
the recruiting?

257
00:11:31,035 --> 00:11:32,669
I work better alone anyway.

258
00:11:32,736 --> 00:11:34,270
Well, I would, Harvey,

259
00:11:34,338 --> 00:11:36,306
except all senior partners
get an associate.

260
00:11:36,373 --> 00:11:38,174
It's just a rule.

261
00:11:38,242 --> 00:11:40,843
I'm sorry.
What?

262
00:11:40,911 --> 00:11:42,111
Jessica, I deserve
that promotion.

263
00:11:42,179 --> 00:11:43,879
My billables destroy his.

264
00:11:43,947 --> 00:11:46,348
And I'm here night and day
doing whatever's needed

265
00:11:46,416 --> 00:11:47,950
instead of swanning
in and out of here

266
00:11:48,018 --> 00:11:49,686
whenever I please.

267
00:11:49,753 --> 00:11:52,155
I must admit, he does make me
sound very swan-like.

268
00:11:52,222 --> 00:11:53,256
Harvey,

269
00:11:53,324 --> 00:11:55,124
shut up.

270
00:11:55,192 --> 00:11:58,061
Louis, this is how it is.

271
00:11:58,129 --> 00:12:01,398
All right,
now you two make nice.

272
00:12:01,465 --> 00:12:03,900
Louis, I apologize.
I was out of line.

273
00:12:03,968 --> 00:12:07,670
Now if you'll just let me text
your pretend wife

274
00:12:07,738 --> 00:12:10,941
that I just made senior partner,
I--what?

275
00:12:11,008 --> 00:12:12,942
Your grandmother's
getting worse.

276
00:12:13,010 --> 00:12:14,877
I need to move her
to full care

277
00:12:14,945 --> 00:12:16,912
or I'll have to transfer her
to the state facility.

278
00:12:16,980 --> 00:12:18,881
I won't put her
in a state facility.

279
00:12:18,949 --> 00:12:21,383
Then I'm afraid you'll have
to come up with $25,000.

280
00:12:21,451 --> 00:12:23,752
[Sighs]

281
00:12:23,820 --> 00:12:25,787
Trevor, I'm in.

282
00:12:25,855 --> 00:12:28,190
One-time deal.
I want 25.

283
00:12:28,257 --> 00:12:29,258
Take it or leave it.

284
00:12:29,325 --> 00:12:30,492
I'll take it.

285
00:12:30,560 --> 00:12:31,626
There's a briefcase in my room.

286
00:12:31,694 --> 00:12:32,794
Pick it up tomorrow,

287
00:12:32,862 --> 00:12:34,496
take it to room 2412

288
00:12:34,564 --> 00:12:35,963
at the Chilton Hotel.

289
00:12:36,031 --> 00:12:37,598
Now you can't go
to a luxury hotel

290
00:12:37,666 --> 00:12:39,467
looking like a delivery guy,
so shave,

291
00:12:39,534 --> 00:12:41,368
comb your hair,
buy a suit.

292
00:12:41,436 --> 00:12:43,103
That's a hell
of a lot to ask, man.

293
00:12:43,171 --> 00:12:45,538
Well, I'm not asking you.
I'm paying you $25,000.

294
00:12:45,606 --> 00:12:46,573
Okay?

295
00:12:46,641 --> 00:12:49,442
Yeah, he's in.

296
00:12:49,509 --> 00:12:50,810
Good.

297
00:12:50,877 --> 00:12:52,978
I'm gonna go take a piss.

298
00:12:58,651 --> 00:13:00,119
Key.

299
00:13:00,187 --> 00:13:01,321
24 hours, we'll know

300
00:13:01,388 --> 00:13:03,422
if this new buyer's a cop.

301
00:13:03,490 --> 00:13:04,724
Why didn't you tell Trevor
he might be sending

302
00:13:04,792 --> 00:13:06,292
his guy into a setup?

303
00:13:06,360 --> 00:13:07,293
Same reason
why I don't tell Gina

304
00:13:07,361 --> 00:13:08,528
I'm banging her sister.

305
00:13:08,596 --> 00:13:11,197
It'll only cause trouble.

306
00:13:11,265 --> 00:13:12,566
What's up?

307
00:13:12,634 --> 00:13:14,235
I'm just gonna take off.

308
00:13:14,302 --> 00:13:17,238
I don't think you should.

309
00:13:17,306 --> 00:13:19,274
Why don't you stay with us
till tomorrow?

310
00:13:19,341 --> 00:13:21,209
Now give me your cell phone.

311
00:13:21,276 --> 00:13:22,677
Give me your phone.

312
00:13:22,744 --> 00:13:27,013
Don't even think
about warning your boy.

313
00:13:27,081 --> 00:13:29,549
'Cause if these guys are cops,
whoever's holding that weed

314
00:13:29,617 --> 00:13:31,417
is going to jail
for a long time.

315
00:13:35,055 --> 00:13:37,022
[Knock at door]

316
00:13:37,090 --> 00:13:38,591
Hey.

317
00:13:38,658 --> 00:13:40,559
Hey. God, you scared the hell
out of me.

318
00:13:40,627 --> 00:13:41,594
Sorry.

319
00:13:41,662 --> 00:13:45,765
Look at you.

320
00:13:45,833 --> 00:13:47,367
You look great.
Thanks.

321
00:13:47,435 --> 00:13:48,936
Tell me you decided
to work with Trevor.

322
00:13:49,003 --> 00:13:51,772
Yeah.
Trial basis. Yeah.

323
00:13:53,977 --> 00:13:55,644
What are you doing here?

324
00:13:55,712 --> 00:13:58,347
My mom is coming
by my place later.

325
00:13:58,415 --> 00:13:59,482
And I don't want
to mess it up,

326
00:13:59,549 --> 00:14:01,417
so I'm hanging here.

327
00:14:01,485 --> 00:14:03,452
[Softly] Got to go.

328
00:14:03,520 --> 00:14:06,155
Hey.
Come here.

329
00:14:08,325 --> 00:14:10,526
Mm.

330
00:14:10,594 --> 00:14:12,528
You want to look perfect
on your first day.

331
00:14:12,596 --> 00:14:14,397
Yeah.

332
00:14:19,469 --> 00:14:21,037
I've got to go.

333
00:14:22,639 --> 00:14:23,906
Mm-hmm.

334
00:14:39,390 --> 00:14:41,491
Great. Thanks.

335
00:14:41,559 --> 00:14:44,528
Donna, we're gonna need
to streamline this.

336
00:14:44,596 --> 00:14:46,363
Give each guy a hard time.

337
00:14:46,431 --> 00:14:47,932
Before you send them back,

338
00:14:48,000 --> 00:14:49,533
give me a wink
if they say something clever.

339
00:14:49,601 --> 00:14:51,269
Cool?
Okay.

340
00:14:51,336 --> 00:14:52,336
What are you looking for?

341
00:14:52,404 --> 00:14:54,605
Another me.

342
00:15:06,718 --> 00:15:08,252
[Exhales]

343
00:15:10,355 --> 00:15:14,057
[Overlapping chatter]

344
00:15:18,096 --> 00:15:20,564
So, Chip,

345
00:15:20,632 --> 00:15:22,466
what makes you think

346
00:15:22,533 --> 00:15:24,067
that I'm gonna let
the whitest man

347
00:15:24,135 --> 00:15:26,269
that I have ever seen
interview for our firm?

348
00:15:26,337 --> 00:15:29,172
Because I have
an appointment.

349
00:15:29,240 --> 00:15:31,808
Hmm.

350
00:15:56,502 --> 00:15:57,970
You can do this.

351
00:16:13,218 --> 00:16:14,852
Kid, what is wrong with you?

352
00:16:14,919 --> 00:16:16,186
You look
like you're 11 years old.

353
00:16:16,254 --> 00:16:18,255
I was late to puberty.

354
00:16:21,592 --> 00:16:23,160
Harvey Specter.

355
00:16:48,389 --> 00:16:50,124
Uh, excuse me.

356
00:16:50,191 --> 00:16:52,259
I was thinking
about going for a swim.

357
00:16:52,327 --> 00:16:53,561
Are the pool facilities here
nice?

358
00:16:53,629 --> 00:16:54,796
Of course, sir.

359
00:16:54,863 --> 00:16:57,899
This is the Chilton Hotel.

360
00:17:00,569 --> 00:17:02,003
And do you have the time?

361
00:17:02,071 --> 00:17:05,072
Yes, uh...

362
00:17:05,140 --> 00:17:08,241
10:00.
Thanks.
"""


def generate_test_prompt():
    """
    This test function generates a sample prompt from a real subtitle file
    that you can copy and paste directly into an LLM for testing.
    """
    # Use a sample subtitle file. Make sure the path is correct.
    # Note: The provided subtitles are in .en format, which might be plain text.
    # We need a .srt file for pysrt to work. Let's assume we have one.
    # If not, we'll need to create a dummy one.
    
    # Creating a dummy srt file for demonstration purposes
    
    dummy_srt_path = "tests/dummy_subtitle.srt"
    with open(dummy_srt_path, "w") as f:
        f.write(srt_content.strip())

    subs = pysrt.open(dummy_srt_path)
    
    # Chunk the subtitles (in this case, it will likely be one chunk)
    subtitle_chunks = chunk_subtitles(subs)

    if not subtitle_chunks:
        print("Could not create subtitle chunks.")
        return

    # Get the prompt for the first chunk
    prompt = get_prompt_for_chunk(subtitle_chunks[0])

    # Save the prompt to a file so it's easy to copy
    prompt_output_path = "tests/sample_prompt.txt"
    with open(prompt_output_path, "w") as f:
        f.write(prompt)

    print(f"Successfully generated a sample prompt.")
    print(f"You can find it here: {prompt_output_path}")
    print("\n--- Prompt Preview ---")
    print(prompt)
    print("----------------------")
    
    # Clean up the dummy file
    os.remove(dummy_srt_path)

if __name__ == "__main__":
    generate_test_prompt()
