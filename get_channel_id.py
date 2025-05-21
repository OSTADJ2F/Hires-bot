import asyncio, re, sys
from telegram import Bot
from telegram.request import HTTPXRequest

# on Windows, use the selector event loop to avoid ProactorBasePipeTransport __del__ errors
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 1) load TOKEN from credentials.txt (same format as post.py)
TOKEN = None
with open("credentials.txt","r") as f:
    for line in f.read().splitlines():
        if line.strip().upper().startswith("TOKEN="):
            TOKEN = line.split("=",1)[1].strip()
if not TOKEN:
    raise RuntimeError("TOKEN not found in credentials.txt")

async def main():
    request = HTTPXRequest()
    bot = Bot(token=TOKEN, request=request, local_mode=True)

    # discard any pending updates so we only catch new channel posts
    first_batch = await bot.get_updates(timeout=1)
    last_id = max((u.update_id for u in first_batch), default=0)

    print("Waiting for a new channel post… make a post in your private channel now.")
    while True:
        updates = await bot.get_updates(timeout=60, offset=last_id+1)
        for u in updates:
            last_id = max(last_id, u.update_id)
            if u.channel_post:
                print("PRIVATE_CHANNEL_ID =", u.channel_post.chat.id)
                return
        # loop again if no new channel_post

if __name__ == "__main__":
    asyncio.run(main())
