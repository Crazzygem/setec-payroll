from django.contrib.auth.decorators import login_required
from django.shortcuts import render


# Temporary placeholder — replaced by the real run list in Phase 3.
@login_required
def run_list(request):
    return render(request, 'payroll/run_list.html')
