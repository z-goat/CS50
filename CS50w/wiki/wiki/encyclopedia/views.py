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

def search(request):
    query = request.GET.get("q", "")
    
    entries = util.list_entries()
    
    for entry in entries:
        if query.lower() == entry.lower():
            return redirect("entry", title=entry)
    
    matches = []
    
    for entry in entries:
        if query.lower() in entry.lower():
            matches.append(entry)
    
    return render(request, "encyclopedia/results.html", {
        "results": matches,
        "query": query, 
    })

def create(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")
        
        entries = util.list_entries()
        if any(title.lower() == entry.lower() for entry in entries):
            return render(request, "encyclopedia/error.html", {
                "message": "An entry with this title already exists.",
                "code": "409"
            })
        
        util.save_entry(title, content)
        return redirect("entry", title=title)
        
    return render(request, "encyclopedia/create.html")

def edit(request, title):
    if request.method == "POST":
        content = request.POST.get("content")
        util.save_entry(title, content)
        return redirect("entry", title=title)
    
    # GET request: load the existing content into the form
    content = util.get_entry(title)
    return render(request, "encyclopedia/edit.html", {
        "title": title,
        "content": content
    })