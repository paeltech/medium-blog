from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from aiohttp import ClientSession
import feedparser
import ssl
import base64
import html
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Mount the static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

medium_username = "paulalan"

async def fetch_medium_feed(username: str):
    url = f'https://medium.com/feed/@{username}'
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with ClientSession() as session:
        async with session.get(url, ssl=ssl_context) as response:
            if response.status != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch Medium feed")
            return feedparser.parse(await response.text())

@app.get("/")
async def read_blog_list(request: Request):
    feed = await fetch_medium_feed(medium_username)
    posts = [
        {
            "guid": base64.urlsafe_b64encode(entry.guid.encode()).decode(),
            "title": entry.title,
            "content": html.unescape(entry.content[0].value.strip()) if entry.content else "",
            "category": entry.tags if "tags" in entry else []
        }
        for entry in feed.entries
    ]
    return templates.TemplateResponse("blog_list.html", {"request": request, "posts": posts})

@app.get("/blog/{encoded_guid}")
async def read_blog_detail(request: Request, encoded_guid: str):
    guid = base64.urlsafe_b64decode(encoded_guid.encode()).decode()
    feed = await fetch_medium_feed(medium_username)
    post = next((entry for entry in feed.entries if entry.guid == guid), None)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    content = html.unescape(post.content[0].value.strip()) if post.content else ""
    return templates.TemplateResponse("blog_detail.html", {"request": request, "post": {"title": post.title, "content": content}})

@app.get("/category/{category}")
async def read_category_list(request: Request, category: str):
    feed = await fetch_medium_feed(medium_username)
    posts = [
        {
            "guid": base64.urlsafe_b64encode(entry.guid.encode()).decode(),
            "title": entry.title,
            "content": html.unescape(entry.content[0].value.strip()) if entry.content else "",
            "category": entry.tags if "tags" in entry else []
        }
        for entry in feed.entries if "tags" in entry and any(tag.term == category for tag in entry.tags)
    ]
    return templates.TemplateResponse("category_list.html", {"request": request, "category": category, "posts": posts})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)