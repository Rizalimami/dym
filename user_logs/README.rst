
Inactive Sessions Timeout
=========================

This module was developed to maintain user login and logout details and print User log report.
This module able to logout all inactive sessions since
a given delay. On each request the server checks if the session is yet valid
regarding the expiration delay. If not a clean logout is operated.

Configuration
=============

Two system parameters are available:

1- inactive_session_time_out_delay: validity of a session in seconds (default = 1 Hours)
2- inactive_session_time_out_ignored_url: technical urls where the check does not occur
