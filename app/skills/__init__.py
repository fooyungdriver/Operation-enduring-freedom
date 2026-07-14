"""Claude-powered in-app skills for the Red Arc Ops Tool.

Each skill is a single, well-scoped Claude call (not an agent): the user
triggers it from the UI, reviews/edits the result, and only then saves it to
Zoho. Skills never write to Zoho directly.
"""
