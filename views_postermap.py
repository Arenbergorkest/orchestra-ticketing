"""Views for the postermap."""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Prefetch
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from django.contrib.auth import get_user_model
from .forms import PosterForm
from .models import Poster


@login_required
@user_passes_test(lambda u: u.is_active, login_url='/inactive')
def add_poster(request):
    """Register a poster."""
    form = PosterForm(request.POST or None, initial={
        'hanging_date': timezone.now().strftime('%Y-%m-%d %H:%M')})
    if request.POST and form.is_valid():
        poster = form.save(commit=False)
        poster.entered_by = request.user
        poster.entered_on = timezone.now()
        poster.save()
        form.save_m2m()
        return HttpResponseRedirect(reverse('tickets:posters'))
    return render(request, 'ticketing/postermap/add_poster.html',
                  {'form': form})


@login_required
@user_passes_test(lambda u: u.is_active, login_url='/inactive')
def posters(request):
    """Show all posters of active productions."""
    leaders, user_data = get_poster_leaders(request.user, 5)
    return render(request, 'ticketing/postermap/posters.html', {
        "posters": list(Poster.objects.filter(production__active=True)),
        "leaders": leaders, "user_data": user_data})


def get_poster_leaders(current_user, n):
    """
    Return scores for posters.

    Returns sorted list of the score of the n best users,
    and score of the given user.
    """
    leaders = []
    user_data = {'leader': current_user,
                 'num_locations': 0, 'num_posters': 0, 'score': 0, }
    posters_set = Poster.objects.filter(production__active=True)
    users = get_user_model().objects.all().prefetch_related(
        Prefetch('hung_posters', queryset=posters_set),
        Prefetch('entered_posters', queryset=posters_set))
    for user in users:
        # Get all posters hung/entered by user and filter out those
        # of inactive productions
        poster_locations = list(user.entered_posters.all()) + \
            list(user.hung_posters.all())
        # Add data
        num_locations = len(poster_locations)
        num_posters = sum([p.count for p in poster_locations])
        data = {
            'leader': user, 'num_locations': num_locations,
            'num_posters': num_posters,
            'score': 50 * num_locations + 10 * num_posters,
        }
        leaders.append(data)
        # If current user, keep the data too so it can be
        # shown on webpage posters.html
        if user == current_user:
            user_data = data
    # Sort and add ranking
    leaders = sorted(leaders, key=lambda entry: entry['score'], reverse=True)
    for i in range(len(leaders)):
        leaders[i]['rank'] = i + 1
    # Return leaders and user data
    return leaders[0:n], user_data
