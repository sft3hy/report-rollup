from datetime import datetime
from pydantic import BaseModel

class Article(BaseModel):
    article_id: str
    title: str
    summary: str
    full_text: str
    url: str
    published_at: datetime
