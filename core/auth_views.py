from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse

from core.mfa import mfa_enabled, mfa_required, user_has_confirmed_mfa


class PasswordLoginView(LoginView):
    """Password login with optional TOTP second step."""

    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()
        if mfa_enabled() and user_has_confirmed_mfa(user):
            self.request.session["mfa_pending_user_id"] = user.pk
            self.request.session["mfa_next"] = self.get_redirect_url()
            return redirect("mfa_verify")
        response = super().form_valid(form)
        if mfa_enabled() and mfa_required() and not user_has_confirmed_mfa(user):
            return redirect("mfa_setup")
        return response
