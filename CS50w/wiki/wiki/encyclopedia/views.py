from django.shortcuts import render, redirect
import markdown
import random
from . import util


def index(request):
    return render(request, "encyclopedia/index.html", {
        "entries": util.list_entries()
    })

def entry(request, title):
    
    entries = util.list_entries()
    
    actual_title = None
    
    for i in entries:
        if title.lower() == i.lower():
            actual_title = i
            break
    
    if actual_title is None:
        return render(request, "encyclopedia/error.html", {
            "message": "The requested page was not found",
            "code": "404",
        })
    
    content = util.get_entry(actual_title)
    
    html_content = markdown.markdown(content)
    
    return render(request, "encyclopedia/entry.html", {
        "title": title,
        "html_content": html_content,
    })
    
def random_page(request):
    entries = util.list_entries()
    
    random_title = random.choice(entries)
    
    return redirect("entry", title=random_title)