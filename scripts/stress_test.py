import sqlite3
import time

import faker
from faker.providers import misc

fake = faker.Faker()
fake.add_provider(misc)


if __name__ == '__main__':
    song_time = """One, two, three!
My baby don't mess around
'Cause she loves me so
This I know fo sho!
But does she really wanna
But can't stand to see me walk out tha door
Don't try to fight the feeling
Because the thought alone is killin' me right now
Thank God for Mom and Dad
For sticking to together
Like we don't know how
Hey ya! Hey ya!
Hey ya! Hey ya!
Hey ya! Hey ya!
Hey ya! Hey ya!
You think you've got it
Oh, you think you've got it
But got it just don't get it when there's nothin' at all
We get together
Oh, we get together
But separate's always better when there's feelings involved
Know what they say -its
Nothing lasts forever!
Then what makes it, then what makes it
Then what makes it, then what makes it
Then what makes love the exception?
So why, oh, why, oh
Why, oh, why, oh, why, oh
Are we still in denial when we know we're not happy here
Hey ya! (y'all don't want to here me, ya just want to dance) Hey ya!
Don't want to meet your daddy (oh ohh), just want you in my caddy (oh ohh)
Hey ya! (oh, oh!) Hey ya! (oh, oh!)
Don't want to meet your momma, just want to make you cum-a (oh, oh!)
I'm (oh, oh) I'm (oh, oh) I'm just being honest! (oh, oh)
I'm just being honest!
Hey! alright now! alright now, fellas!
Yea?
Now, what cooler than being cool?
Ice cold!
I can't hear ya! I say what's, what's cooler than being cool?
Ice cold!
Alright alright alright alright alright alright alright alright alright alright alright alright alright alright alright alright!
Okay, now ladies!
Yea?
Now we gonna break this thang down for just a few seconds
Now don't have me break this thang down for nothin'
I want to see you on your badest behavior!
Lend me some sugar, I am your neighbor!
Ah! Here we go now,
Shake it, shake it, shake it, shake it, shake it
Shake it, shake it, shake it, shake it
Shake it like a Polaroid picture! Hey ya!
Shake it, shake it, shake it, shake it, shake it
Shake it, shake it, shake it, suga!
Shake it like a Polaroid picture!
Now all the Beyonce's, and Lucy Lu's, and baby dolls
Get on tha floor get on tha floor!
Shake it like a Polaroid picture!
Oh, you! oh, you!
Hey ya!(oh, oh) Hey ya!(oh, oh)
Hey ya!(oh, oh) Hey ya!(oh, oh)
Hey ya!(oh, oh) Hey ya!(oh, oh)"""

    song = song_time.split('\n')
    claim_id = '2aa106927b733e2602ffb565efaccc78c2ed89df'
    run_len = [(fake.sha256(), song_time, claim_id, str(int(time.time()))) for k in range(5000)]

    conn = sqlite3.connect('database/default_test.db')
    with conn:
        curs = conn.executemany("""
        INSERT INTO COMMENT(CommentId, Body, LbryClaimId, Timestamp) VALUES (?, ?, ?, ?)
        """, run_len)
        print(f'rows changed: {curs.rowcount}')
