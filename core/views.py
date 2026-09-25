from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    """Home page. Stat cards are added once payroll data exists (Phase 3)."""
    return render(request, 'core/index.html')
