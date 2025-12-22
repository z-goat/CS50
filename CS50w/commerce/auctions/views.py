from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse

from .models import User, Listing, Bid


def index(request):
    # Fetch only listings that haven't been closed
    listings = Listing.objects.filter(is_active=True)
    return render(request, "auctions/index.html", {
        "listings": listings
    })

def login_view(request):
    if request.method == "POST":

        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")
    
from django.contrib.auth.decorators import login_required
from .forms import ListingForm

@login_required 
def create_listing(request):
    if request.method == "POST":
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.current_price = listing.starting_bid 
            listing.save()
            return redirect("index")
    else:
        form = ListingForm()
    
    return render(request, "auctions/create.html", {
        "form": form
    })


def listing_page(request, listing_id):
    listing = Listing.objects.get(pk=listing_id)
    
    is_watched = False
    if request.user.is_authenticated:
        if listing.watchlist.filter(id=request.user.id).exists():
            is_watched = True

    if request.method == "POST":
        if "place_bid" in request.POST:
            bid_amount = float(request.POST['bid_amount'])
            
            if bid_amount > listing.current_price:
                listing.current_price = bid_amount
                listing.save()
                Bid.objects.create(user=request.user, listing=listing, amount=bid_amount)
                return redirect("listing", listing_id=listing.id)
            else:
                return render(request, "auctions/listing.html", {
                    "listing": listing,
                    "is_watched": is_watched,
                    "error": "Bid must be higher than current price."
                })
        if "watchlist_add" in request.POST:
            listing.watchlist.add(request.user)
            return redirect("listing", listing_id=listing.id)
        elif "watchlist_remove" in request.POST:
            listing.watchlist.remove(request.user)
            return redirect("listing", listing_id=listing.id)

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "is_watched": is_watched
    })