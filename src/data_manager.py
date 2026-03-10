import os

def ingest_article(file_path):

    os.makedirs("articles",exist_ok=True)

    name=os.path.basename(file_path)

    with open(file_path,"r",encoding="utf8") as f:
        content=f.read()

    with open(f"articles/{name}","w",encoding="utf8") as out:
        out.write(content)

    return "Article added to knowledge base"