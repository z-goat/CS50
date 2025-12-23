from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages

from .models import User, Listing, Bid, Comment, Category
from .forms import ListingForm


def index(request):
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


@login_required 
def create_listing(request):
    if request.method == "POST":
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.owner = request.user
            listing.current_price = listing.starting_bid 
            listing.save()
            messages.success(request, "Listing created successfully!")
            return redirect("index")
    else:
        form = ListingForm()
    
    return render(request, "auctions/create.html", {
        "form": form
    })


def listing_page(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    comments = listing.comments.all()
    is_watched = False
    is_owner = False
    is_winner = False
    
    if request.user.is_authenticated:
        is_watched = listing.watchlist.filter(id=request.user.id).exists()
        is_owner = listing.owner == request.user
        
        # Check if user is the winner of a closed auction
        if not listing.is_active:
            highest_bid = listing.bids.order_by('-amount').first()
            if highest_bid and highest_bid.user == request.user:
                is_winner = True

    if request.method == "POST":
        if "place_bid" in request.POST:
            bid_amount = float(request.POST['bid_amount'])
            
            # Bid must be greater than current price
            if bid_amount > listing.current_price:
                listing.current_price = bid_amount
                listing.save()
                Bid.objects.create(user=request.user, listing=listing, amount=bid_amount)
                messages.success(request, "Bid placed successfully!")
                return redirect("listing", listing_id=listing.id)
            else:
                messages.error(request, "Bid must be higher than current price.")
                
        elif "watchlist_add" in request.POST:
            listing.watchlist.add(request.user)
            messages.success(request, "Added to watchlist!")
            return redirect("listing", listing_id=listing.id)
            
        elif "watchlist_remove" in request.POST:
            listing.watchlist.remove(request.user)
            messages.success(request, "Removed from watchlist!")
            return redirect("listing", listing_id=listing.id)

    bid_count = listing.bids.count()
    
    return render(request, "auctions/listing.html", {
        "listing": listing,
        "is_watched": is_watched,
        "is_owner": is_owner,
        "is_winner": is_winner,
        "comments": comments,
        "bid_count": bid_count
    })


@login_required
def close_listing(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    
    # Only owner can close
    if request.user == listing.owner:
        listing.is_active = False
        listing.save()
        messages.success(request, "Listing closed successfully!")
    else:
        messages.error(request, "You are not authorized to close this listing.")
    
    return redirect("listing", listing_id=listing_id)


@login_required
def add_comment(request, listing_id):
    if request.method == "POST":
        listing = get_object_or_404(Listing, pk=listing_id)
        content = request.POST.get("comment_content")
        
        if content:
            Comment.objects.create(
                user=request.user,
                listing=listing,
                content=content
            )
            messages.success(request, "Comment added!")
        else:
            messages.error(request, "Comment cannot be empty.")
    
    return redirect("listing", listing_id=listing_id)


@login_required
def watchlist(request):
    watched_listings = request.user.watched_items.all()
    return render(request, "auctions/watchlist.html", {
        "listings": watched_listings
    })


def categories(request):
    all_categories = Category.objects.all()
    return render(request, "auctions/categories.html", {
        "categories": all_categories
    })


def category(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    listings = Listing.objects.filter(category=category, is_active=True)
    return render(request, "auctions/category.html", {
        "category": category,
        "listings": listings
    })