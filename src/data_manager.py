import os
from utils import resource_path

articles_path = resource_path("articles")

def list_articles():
    return [f for f in os.listdir(articles_path) if f.endswith(".txt")]

def add_article(filename: str, content: str):
    file_path = os.path.join(articles_path, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)